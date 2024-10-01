# Blind Assistance Web App

This web app provides assistance to visually impaired users by capturing voice inputs, analyzing images using the Gemini Flash 1.5 model, and providing navigation assistance using Google Maps. The app supports multiple languages and interacts with the user through voice responses.

## Features

- Voice interaction using the device's microphone (tap or shake gesture to start/stop recording).
- Captures an image from the camera when requested by the user and sends it for analysis.
- Provides voice responses for image analysis and navigation assistance.
- Uses the Google Cloud Text-to-Speech API for voice output.
- Integrates Google Maps for navigation assistance based on the user's query.

## Tech Stack

- **Frontend**: HTML, Tailwind CSS, JavaScript
- **Backend**: FastAPI
- **APIs**: 
  - Gemini Flash 1.5 Model
  - Google Cloud Text-to-Speech
  - Google Maps Geolocation API

## Requirements

The following dependencies are required to run the project:

fastapi, uvicorn, jinja2, google-generativeai, python-multipart, python-dotenv, google-cloud-texttospeech


To install the dependencies, run:

```bash
pip install -r requirements.txt
Setup Instructions

Clone the repository:
bash
Copy code
git clone <repository-url>
cd blind-assistance-app
Set up environment variables:
Create a .env file in the root directory and add your API keys:
env
Copy code
GOOGLE_CLOUD_TTS_API_KEY=<your_google_cloud_api_key>
GEMINI_FLASH_API_KEY=<your_gemini_flash_api_key>
Run the backend server:
bash
Copy code
uvicorn main:app --reload


Access the frontend:
Open index.html in your browser to start the application.
Make sure your browser allows permissions for camera, microphone, and location.


Usage:-

Voice Interaction:
Tap the microphone button or shake your device to start voice recording.
The app will listen for your voice commands and process them.

Image Analysis:
If you ask a question like "What's in front of me?", the app will capture an image using the device's camera and send it to the Gemini Flash model for analysis.

Navigation:
For navigation queries (e.g., "How do I get to Walmart?"), the app will open Google Maps and provide directions based on your current location.
Troubleshooting

If the app is not capturing images, ensure that camera permissions are enabled for the browser.
If the voice response is not played, check your Google Cloud Text-to-Speech API key.
For any network errors, ensure that your API keys are valid and that the necessary environment variables are set up correctly.

License

This project is licensed under the MIT License. See the LICENSE file for details.
