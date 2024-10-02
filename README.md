# Visionary - An Assistive Web Application for the Visually Impaired

Visionary is a web application designed to assist visually impaired individuals by providing real-time audio responses to voice queries and environmental inputs. The app leverages voice input, image capture, and location services to offer context-aware assistance. It integrates the Gemini 1.5 Flash model for processing voice and image data, uses Google Cloud Text-to-Speech (WaveNet) for generating voice responses in multiple languages, and incorporates the Perplexity API for real-time information retrieval.

## Features

### Voice Interaction
- **Initiate/Stop Recording:** Start or stop voice recording by tapping the microphone button or shaking the device.
- **Gesture-Based Controls:** Utilize single tap or shake gestures for intuitive interaction, and double-tap to cancel audio playback and reset the app.

### Image Analysis
- **Automatic Image Capture:** Captures an image using the device's rear camera upon specific voice commands.
- **Contextual Descriptions:** Sends the captured image to the Gemini 1.5 Flash model for analysis and provides concise descriptions, including relevant safety concerns, in the user's language.

### Real-Time Information Retrieval
- **Perplexity API Integration:** Uses the llama-3.1-sonar-small-128k-online model from Perplexity's Sonar family to fetch up-to-date information based on user queries.
- **Rate Limiting:** Implements a rate limit of 20 requests per minute to comply with Perplexity API usage guidelines.

### Navigation Assistance
- **Google Maps Integration:** Provides walking directions by integrating with Google Maps. Attempts to open native Google Maps applications on mobile devices, with a fallback to the web version if the native app is unavailable.
- **Location-Based Directions:** Uses the device's geolocation to determine the user's current position and provide accurate navigation assistance.

### Multilingual Support
- **Language Detection:** Detects the language of the user's query and responds in the same language using Google Cloud Text-to-Speech WaveNet voices.
- **WaveNet Voices:** Ensures natural-sounding audio responses tailored to the detected language.

### Feedback Mechanisms
- **Haptic and Auditory Cues:** Provides haptic feedback and auditory signals for all user interactions, enhancing accessibility without relying on visual input.

### Error Handling
- **Robust Management:** Handles API failures and connectivity issues gracefully, providing user-friendly audio notifications to maintain a seamless user experience.

### Audio Processing
- **Seamless Audio Playback:** Utilizes Pydub to combine multiple audio segments (e.g., "searching" + actual response) for a cohesive audio experience.

## Tech Stack

### Frontend
- HTML
- Tailwind CSS
- JavaScript

### Backend
- FastAPI (Python)

### APIs and Services
- Gemini 1.5 Flash Model (Voice and Image Processing)
- Perplexity API (llama-3.1-sonar-small-128k-online model)
- Google Cloud Text-to-Speech (WaveNet)
- Google Maps Geolocation API

## Requirements

Ensure you have the following installed to run the project:
- **Python 3.7+**
- **FFmpeg:** Required by Pydub for audio processing.

### Python Dependencies

Install the necessary Python packages using pip:


I apologize for the confusion. You're absolutely right, and I made a mistake in my previous response. Let me provide you with the correct Markdown format, including the proper use of # symbols for headings. Here's the corrected version:

# Setup and Installation

## Install Dependencies

To install the required dependencies, run the following command:

```bash
pip install -r requirements.txt
```

The `requirements.txt` file includes the following dependencies:

- fastapi
- uvicorn
- jinja2
- google-generativeai
- python-multipart
- python-dotenv
- google-cloud-texttospeech==2.14.1
- pydub
- requests

**Note:** If you plan to implement asynchronous HTTP requests in the future, consider adding `httpx` to your dependencies.

## FFmpeg Installation

Pydub relies on FFmpeg for audio processing. Install FFmpeg as follows:

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install ffmpeg
```

### macOS (using Homebrew)

```bash
brew install ffmpeg
```

### Windows

Download the FFmpeg binary and add the `bin` directory to your system's PATH.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd visionary-assistive-app
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory and add your API keys and credentials:

```makefile
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-cloud-credentials.json
PERPLEXITY_API_KEY=<your_perplexity_api_key>
GEMINI_API_KEY=<your_gemini_api_key>
```

**Environment Variables Explained:**
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your Google Cloud service account JSON file for Text-to-Speech.
- `PERPLEXITY_API_KEY`: Your Perplexity API key for accessing real-time information.
- `GEMINI_API_KEY`: Your Gemini 1.5 Flash model API key for processing voice and image data.

Ensure that the Google Cloud credentials file is located at the specified path.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Backend Server

```bash
uvicorn main:app --reload
```

### 5. Access the Frontend

Open the `index.html` file located in the `templates` directory in your preferred web browser to launch the application. Ensure that your browser has granted permissions for camera, microphone, and location services.

**Note:** For seamless audio playback, ensure that your browser allows autoplay of audio without user interaction.

# Usage

## Voice Interaction

- **Start Recording:** Tap the microphone button or shake your device to begin voice recording.
- **Stop Recording:** Tap the microphone button again or shake the device to stop recording.

## Image Analysis

- **Query Example:** Ask a question like "What is in front of me?"
- **Process:** The app captures an image using the device's rear camera and sends it to the Gemini 1.5 Flash model for analysis.
- **Response:** Provides a concise, language-specific description of the image, including any relevant safety concerns.

## Navigation Assistance

- **Query Example:** Ask "How do I get to the nearest Walmart?"
- **Process:** Responds with "Opening Google Maps for Walmart" and opens Google Maps with walking directions based on your current location.

## Real-Time Information Retrieval

- **Query Example:** Ask "What's the current stock price of Tesla?"
- **Process:** The app responds with "Searching What's the current stock price of Tesla?" and retrieves real-time information using the Perplexity API.
- **Response:** Converts the retrieved information into speech in the same language as the user's query.

# Troubleshooting

## Image Capture Issues

- Ensure that camera permissions are enabled in your browser settings.
- Verify that your device has a functioning rear camera.

## Voice Response Issues

- Check if the `PERPLEXITY_API_KEY` and `GEMINI_API_KEY` in your `.env` file are correct and active.
- Ensure that the Google Cloud Text-to-Speech service is properly configured and that your credentials are valid.

## Network Errors

- Confirm that your internet connection is stable.
- Verify that your API keys are correctly set up and have not exceeded their usage limits.
- Check the Perplexity API Status for any ongoing service issues.

## Permission Denied

- If the app is not capturing images or audio, ensure that permissions for camera, microphone, and location services are granted in your browser.
- Reload the page after granting permissions.

## Audio Processing Issues

- Ensure that FFmpeg is installed and correctly set up on your system.
- Verify that the Google Cloud Text-to-Speech API is functioning as expected.

## Rate Limiting

- If you encounter rate limit errors, ensure that your app is not exceeding 20 requests per minute to the Perplexity API.
- Monitor request counts and implement backoff strategies if necessary.

# Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes.

# License

This project is licensed under the MIT License. See the LICENSE file for details.

# Additional Notes

## Technical Implementation Details

### Backend (main.py)
- **FastAPI:** Serves as the backend framework for handling API requests.
- **Gemini 1.5 Flash Model:** Processes voice and image data to understand user queries.
- **Perplexity API:** Utilizes the llama-3.1-sonar-small-128k-online model for fetching real-time information based on user queries.
- **Rate Limiting:** Employs a deque to track and limit API requests to 20 per minute.
- **Text-to-Speech:** Converts text responses into speech using Google Cloud's WaveNet voices, tailored to the detected language.

### Frontend (static/js/app.js)
- **User Permissions:** Requests access to camera, microphone, and geolocation upon app launch.
- **Event Handling:** Listens for touch and motion events to manage recording states.
- **Audio Processing:** Captures audio, processes it, and plays synthesized responses.
- **Navigation Handling:** Integrates with Google Maps to provide location-based directions.

## Testing Multilingual Support

To ensure that Visionary handles multilingual queries effectively:

### English Query
- **User Question:** "What's the capital of France?"
- **Expected Response:** Brief answer in English.

### Spanish Query
- **User Question:** "¿Cuál es la capital de Francia?"
- **Expected Response:** Breve respuesta en español.

### Hindi Query
- **User Question:** "फ्रांस की राजधानी क्या है?"
- **Expected Response:** हिंदी में संक्षिप्त उत्तर।
