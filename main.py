from fastapi import FastAPI, Request, File, UploadFile
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

DEFAULT_PROMPT = """
"I will ask questions in audio format. Please respond to my questions by following these rules:

1. Only when I explicitly ask, in any language, that is similar to : (what is in front of me, whether I can cross the road, or what an object is), should you analyze the provided image and give a concise description in the same language I used. Since I am blind, include any safety concerns where applicable. Do not provide any descriptions unless I ask for them explicitly. If I remain silent, do not initiate or describe anything unprompted.

2. For navigation-related queries in any language (e.g., 'How do I get to the nearest place like Walmart?' or 'Take me to...'), always respond with 'Opening Google Maps for {location}' in English, regardless of the language I am using.

3. For any other queries apart from these two cases (e.g., recipes, any particular guides, random questions), just reply in the same language i used  but don't use any special symbols or emojis.

4. At the end of each response, state the name of the language I used as a single word (e.g., 'English', 'Hindi', 'Spanish', 'Telugu', etc.)."
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
        language = text_response.split()[-1].lower()
        # Remove the language name from the text response
        text_response = ' '.join(text_response.split()[:-1])
        
        if text_response.lower().startswith("opening google maps for"):
            print("Triggering navigation")
            location = text_response.replace("Opening Google Maps for", "").strip()
            audio_content = synthesize_speech(text_response, language)
            return JSONResponse(content={"response": text_response, "audio": audio_content, "is_navigation": True, "location": location})
        else:
            print("Regular response")
            audio_content = synthesize_speech(text_response, language)
            return JSONResponse(content={"response": text_response, "audio": audio_content})
    except Exception as e:
        print(f"Error processing input: {str(e)}")
        error_message = "Sorry, there was an error processing your request. Please try again."
        error_audio = synthesize_speech(error_message, "english")
        return JSONResponse(content={"error": str(e), "response": error_message, "audio": error_audio}, status_code=500)

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