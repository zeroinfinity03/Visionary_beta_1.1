from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import google.generativeai as genai
from google.cloud import texttospeech_v1 as texttospeech
from google.oauth2 import service_account
from dotenv import load_dotenv
import os
import base64
from pathlib import Path
import io
from pydub import AudioSegment
import requests
import json
import asyncio
import time
from requests.exceptions import RequestException
from collections import deque

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Configure Text-to-Speech client
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if credentials_path is None:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")

credentials_path = Path(credentials_path)
if not credentials_path.exists():
    raise FileNotFoundError(f"Credentials file not found at {credentials_path}")

credentials = service_account.Credentials.from_service_account_file(str(credentials_path))
tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

# Configure Perplexity API
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
if not PERPLEXITY_API_KEY:
    raise ValueError("PERPLEXITY_API_KEY is not set in the environment variables")

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 20
request_timestamps = deque(maxlen=MAX_REQUESTS_PER_MINUTE)


DEFAULT_PROMPT = """

I will ask questions in audio format. Please respond following these specific rules:

1. If I ask in any language a question like "What is in front of me?", "Can I cross the road?", or "What is this object?", analyze the provided image and give a concise description in the same language as the question (e.g., Hindi, Spanish, etc.). Since I am blind, include any relevant safety concerns.
Restrictions: Do not describe anything unless explicitly requested. Remain silent if I do not ask for a description.

2. For questions such as "How do I get to the nearest Walmart?" or commands like "Take me to...", respond with: "Opening Google Maps for {location}" in English, regardless of the user's language.

3. Recent Information Queries like whats happening in the world, or something like that in any language just say searching and repeat the question in the same language.
Example:
User Question: "¿Cuál es el precio actual de las acciones de Tesla?"
Response: "searching ¿Cuál es el precio actual de las acciones de Tesla?"

4. For questions other than these 3 like recipes, guides, how are u? , wts up, etc reply in the same language as the question, avoiding any special symbols or emojis.

5. At the end of each response, mention the language used by the user as a single word.
Example: "English", "Hindi", "Spanish", etc.

"""




@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/process_audio_and_image")
async def process_audio_and_image(audio: UploadFile = File(...), image: UploadFile = File(...)):
    try:
        # Process audio and image
        audio_content = await audio.read()
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        image_content = await image.read()
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        
        # Send both audio and image to Gemini
        response = model.generate_content([
            DEFAULT_PROMPT,
            "Process this audio input and image:",
            {"mime_type": audio.content_type, "data": audio_base64},
            {"mime_type": image.content_type, "data": image_base64}
        ])
        
        text_response = response.text if response.text else "I'm sorry, I couldn't process the input."
        print(f"Gemini response: {text_response}")
        
        # Extract language from the response
        parts = text_response.rsplit(None, 1)
        language = parts[-1].lower() if len(parts) > 1 else "english"
        text_response = parts[0] if len(parts) > 1 else text_response
        
        if text_response.lower().startswith("opening google maps for"):
            print("Triggering navigation")
            location = text_response.replace("Opening Google Maps for", "").strip()
            audio_content = synthesize_speech(text_response, language)
            return JSONResponse(content={
                "response": text_response, 
                "audio": audio_content, 
                "is_navigation": True, 
                "location": location
            })
        elif text_response.lower().startswith("searching"):
            print("Handling recent information query")
            search_query = text_response[len("searching"):].strip()
            
            searching_audio = synthesize_speech("searching", language)
            print(f"Sending query to Perplexity API: {search_query}")
            search_result = await search_perplexity(search_query)
            print(f"Received result from Perplexity API: {search_result}")
            result_audio = synthesize_speech(search_result, language)
            combined_audio = combine_audio(searching_audio, result_audio)
            
            return JSONResponse(content={
                "response": f"searching. {search_result}",
                "audio": combined_audio,
                "is_searching": True
            })
        else:
            print("Regular response")
            audio_content = synthesize_speech(text_response, language)
            return JSONResponse(content={
                "response": text_response, 
                "audio": audio_content
            })
    except Exception as e:
        print(f"Error processing input: {str(e)}")
        error_message = "Sorry, there was an error processing your request. Please try again."
        error_audio = synthesize_speech(error_message, "english")
        return JSONResponse(content={
            "error": str(e), 
            "response": error_message, 
            "audio": error_audio
        }, status_code=500)

async def search_perplexity(query: str):
    global request_timestamps
    current_time = time.time()
    
    # Remove timestamps older than 1 minute
    while request_timestamps and current_time - request_timestamps[0] > 60:
        request_timestamps.popleft()
    
    # If we've made 20 requests in the last minute, wait
    if len(request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        wait_time = 60 - (current_time - request_timestamps[0])
        if wait_time > 0:
            await asyncio.sleep(wait_time)
    
    # Add current timestamp to the queue
    request_timestamps.append(time.time())

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.1-sonar-small-128k-online",  # Corrected model name
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that provides brief, concise answers."},
            {"role": "user", "content": f"Provide a brief answer to: {query}"}
        ],
        "max_tokens": 100
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            answer = result['choices'][0]['message']['content']
            return answer.strip()
        else:
            return "I'm sorry, I couldn't find that information."
    except Exception as e:
        print(f"Error querying Perplexity API: {str(e)}")
        return "I'm sorry, but there was a problem connecting to my knowledge source. Please try again later."

def combine_audio(audio1, audio2):
    # Decode base64 strings to bytes
    audio1_bytes = base64.b64decode(audio1)
    audio2_bytes = base64.b64decode(audio2)

    # Create AudioSegment objects from the bytes
    sound1 = AudioSegment.from_mp3(io.BytesIO(audio1_bytes))
    sound2 = AudioSegment.from_mp3(io.BytesIO(audio2_bytes))

    # Concatenate the two audio segments
    combined = sound1 + sound2

    # Export the combined audio to a bytes buffer
    buffer = io.BytesIO()
    combined.export(buffer, format="mp3")
    buffer.seek(0)

    # Encode the combined audio back to base64
    combined_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return combined_base64

def synthesize_speech(text, language):
    input_text = texttospeech.SynthesisInput(text=text)
    
    # Map of language codes to appropriate Wavenet voices
    language_voices = {
        'english': ('en-US', ['en-US-Wavenet-D', 'en-US-Wavenet-A', 'en-US-Wavenet-B', 'en-US-Wavenet-C']),
        'hindi': ('hi-IN', ['hi-IN-Wavenet-D', 'hi-IN-Wavenet-A', 'hi-IN-Wavenet-B', 'hi-IN-Wavenet-C']),
        'spanish': ('es-ES', ['es-ES-Wavenet-B', 'es-ES-Wavenet-A', 'es-ES-Wavenet-C', 'es-ES-Wavenet-D']),
        'french': ('fr-FR', ['fr-FR-Wavenet-C', 'fr-FR-Wavenet-A', 'fr-FR-Wavenet-B', 'fr-FR-Wavenet-D']),
        'german': ('de-DE', ['de-DE-Wavenet-F', 'de-DE-Wavenet-A', 'de-DE-Wavenet-B', 'de-DE-Wavenet-C']),
        'kannada': ('kn-IN', ['kn-IN-Wavenet-A']),
        'telugu': ('te-IN', ['te-IN-Wavenet-B', 'te-IN-Wavenet-A']),
        'tamil': ('ta-IN', ['ta-IN-Wavenet-D', 'ta-IN-Wavenet-A', 'ta-IN-Wavenet-B', 'ta-IN-Wavenet-C']),
        'malayalam': ('ml-IN', ['ml-IN-Wavenet-D', 'ml-IN-Wavenet-A', 'ml-IN-Wavenet-B', 'ml-IN-Wavenet-C']),
        'bengali': ('bn-IN', ['bn-IN-Wavenet-A']),
        'gujarati': ('gu-IN', ['gu-IN-Wavenet-A']),
        'marathi': ('mr-IN', ['mr-IN-Wavenet-A']),
        'japanese': ('ja-JP', ['ja-JP-Wavenet-D', 'ja-JP-Wavenet-A', 'ja-JP-Wavenet-B', 'ja-JP-Wavenet-C']),
        'korean': ('ko-KR', ['ko-KR-Wavenet-D', 'ko-KR-Wavenet-A', 'ko-KR-Wavenet-B', 'ko-KR-Wavenet-C']),
        'chinese': ('cmn-CN', ['cmn-CN-Wavenet-D', 'cmn-CN-Wavenet-A', 'cmn-CN-Wavenet-B', 'cmn-CN-Wavenet-C']),
        'arabic': ('ar-XA', ['ar-XA-Wavenet-B', 'ar-XA-Wavenet-A', 'ar-XA-Wavenet-C', 'ar-XA-Wavenet-D']),
        'russian': ('ru-RU', ['ru-RU-Wavenet-D', 'ru-RU-Wavenet-A', 'ru-RU-Wavenet-B', 'ru-RU-Wavenet-C']),
        'portuguese': ('pt-BR', ['pt-BR-Wavenet-B', 'pt-BR-Wavenet-A', 'pt-BR-Wavenet-C', 'pt-BR-Wavenet-D']),
        'italian': ('it-IT', ['it-IT-Wavenet-D', 'it-IT-Wavenet-A', 'it-IT-Wavenet-B', 'it-IT-Wavenet-C']),
        'dutch': ('nl-NL', ['nl-NL-Wavenet-E', 'nl-NL-Wavenet-A', 'nl-NL-Wavenet-B', 'nl-NL-Wavenet-C']),
        'polish': ('pl-PL', ['pl-PL-Wavenet-E', 'pl-PL-Wavenet-A', 'pl-PL-Wavenet-B', 'pl-PL-Wavenet-C']),
        'swedish': ('sv-SE', ['sv-SE-Wavenet-A', 'sv-SE-Wavenet-B', 'sv-SE-Wavenet-C']),
        'turkish': ('tr-TR', ['tr-TR-Wavenet-E', 'tr-TR-Wavenet-A', 'tr-TR-Wavenet-B', 'tr-TR-Wavenet-C']),
        'vietnamese': ('vi-VN', ['vi-VN-Wavenet-D', 'vi-VN-Wavenet-A', 'vi-VN-Wavenet-B', 'vi-VN-Wavenet-C']),
        'indonesian': ('id-ID', ['id-ID-Wavenet-D', 'id-ID-Wavenet-A', 'id-ID-Wavenet-B', 'id-ID-Wavenet-C']),
        'thai': ('th-TH', ['th-TH-Wavenet-C', 'th-TH-Wavenet-A', 'th-TH-Wavenet-B']),
        'punjabi': ('pa-IN', ['pa-IN-Wavenet-A', 'pa-IN-Wavenet-B', 'pa-IN-Wavenet-C', 'pa-IN-Wavenet-D']),
    }
    
    # Default to English if language not supported
    language_code, voice_names = language_voices.get(language, ('en-US', ['en-US-Wavenet-D']))
    
    for voice_name in voice_names:
        try:
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            response = tts_client.synthesize_speech(
                input=input_text, voice=voice, audio_config=audio_config
            )
            return base64.b64encode(response.audio_content).decode('utf-8')
        except Exception as e:
            print(f"Error with Wavenet voice {voice_name} for {language_code}: {str(e)}")
    
    # Fallback to Standard voice if no Wavenet voice is available
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=f"{language_code}-Standard-A"
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    response = tts_client.synthesize_speech(
        input=input_text, voice=voice, audio_config=audio_config
    )
    
    return base64.b64encode(response.audio_content).decode('utf-8')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
