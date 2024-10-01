const micBtn = document.getElementById('micBtn');
const micBtnWrapper = document.getElementById('micBtnWrapper');
const video = document.getElementById('video');
let audioStream = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let shakeThreshold = 15;
let lastX = 0, lastY = 0, lastZ = 0;
let lastTapTime = 0;
let tapCount = 0;
let audioPlayer = null;

async function startApp() {
    try {
        console.log('Starting app...');

        await requestPermissions();
        console.log('Permissions requested successfully');

        await setupVideoStream();
        console.log('Video stream set up successfully');

        await setupGeolocation();
        console.log('Geolocation set up successfully');

        setupMotionDetection();
        console.log('Motion detection set up successfully');

        setupInteractionDetection();
        console.log('Interaction detection set up successfully');

        console.log('App started successfully');
    } catch (error) {
        console.error('Error starting app:', error);
        handleStartupError(error);
    }
}

async function requestPermissions() {
    const permissions = ['camera', 'microphone', 'geolocation'];
    for (const permission of permissions) {
        try {
            console.log(`Requesting permission for ${permission}...`);
            if (navigator.permissions && navigator.permissions.query) {
                const result = await navigator.permissions.query({name: permission});
                console.log(`Permission status for ${permission}: ${result.state}`);
                if (result.state === 'denied') {
                    throw new Error(`Permission for ${permission} was denied`);
                }
            } else {
                console.log(`Permissions API not available, assuming ${permission} permission is granted`);
            }
        } catch (error) {
            console.warn(`Error requesting ${permission} permission:`, error);
            throw error;
        }
    }
}

async function setupVideoStream() {
    try {
        const videoStream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: 'environment' },
            audio: false
        });
        video.srcObject = videoStream;
        await video.play();
        document.getElementById('cameraView').classList.remove('hidden');
    } catch (error) {
        console.error('Error setting up video stream:', error);
        document.getElementById('cameraView').classList.add('hidden');
        document.getElementById('fallbackView').classList.remove('hidden');
    }
}

async function setupGeolocation() {
    return new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject);
    });
}

function setupMotionDetection() {
    if (window.DeviceMotionEvent) {
        window.addEventListener('devicemotion', handleMotionEvent, true);
    } else {
        console.log('Device motion not supported');
    }
}

function handleMotionEvent(event) {
    if (event.accelerationIncludingGravity) {
        let acceleration = event.accelerationIncludingGravity;
        let curX = acceleration.x;
        let curY = acceleration.y;
        let curZ = acceleration.z;

        let change = Math.abs(curX + curY + curZ - lastX - lastY - lastZ);
        if (change > shakeThreshold) {
            toggleRecording();
        }

        lastX = curX;
        lastY = curY;
        lastZ = curZ;
    }
}

function handleStartupError(error) {
    let errorMessage = 'An error occurred while starting the app. ';
    if (error.name === 'NotAllowedError') {
        errorMessage += 'Please grant the necessary permissions and reload the page.';
    } else if (error.name === 'NotSupportedError') {
        errorMessage += 'Your device may not support all required features. Please try using a different device or browser.';
    } else if (error.name === 'NotFoundError') {
        errorMessage += 'Required hardware (camera or microphone) not found. Please check your device settings.';
    } else {
        errorMessage += 'Please check your device settings and try again. If the problem persists, try reloading the page.';
    }
    document.getElementById('errorMessage').textContent = errorMessage;
    document.getElementById('errorMessage').classList.remove('hidden');

    const reloadButton = document.createElement('button');
    reloadButton.textContent = 'Reload Page';
    reloadButton.className = 'bg-blue-500 text-white p-2 rounded mt-4';
    reloadButton.onclick = () => location.reload();
    document.getElementById('errorMessage').appendChild(reloadButton);
}

function setupInteractionDetection() {
    document.body.addEventListener('touchstart', handleTouch, { passive: false });
    document.body.addEventListener('mousedown', handleMouse);
}

function handleTouch(event) {
    event.preventDefault();
    handleInteraction();
}

function handleMouse(event) {
    handleInteraction();
}

function handleInteraction() {
    const currentTime = new Date().getTime();
    const tapLength = currentTime - lastTapTime;

    if (tapLength < 300 && tapLength > 50) {
        tapCount++;
        if (tapCount === 2) {
            stopAudioAndResetApp();
            tapCount = 0;
        }
    } else {
        tapCount = 1;
        toggleRecording();
    }

    lastTapTime = currentTime;

    setTimeout(() => {
        tapCount = 0;
    }, 300);

    if (navigator.vibrate) {
        navigator.vibrate(50);
    }
}

function stopAudioAndResetApp() {
    if (audioPlayer) {
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
    }
    stopRecording();
    console.log("App reset due to double tap");
    location.reload();
}

async function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    try {
        if (audioStream) {
            audioStream.getTracks().forEach(track => track.stop());
        }
        audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(audioStream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = sendAudioAndImageToBackend;

        mediaRecorder.start();
        isRecording = true;
        micBtnWrapper.classList.add('recording');
        micBtn.querySelector('i').classList.add('text-red-500');
        micBtn.querySelector('i').classList.remove('text-blue-500', 'hover:text-blue-600');
    } catch (error) {
        console.error('Error starting recording:', error);
    }
}

async function sendAudioAndImageToBackend() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const imageBlob = await captureImage();

    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    formData.append('image', imageBlob, 'capture.jpg');

    try {
        const response = await fetch('/process_audio_and_image', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (result.is_navigation) {
            playAudioResponse(result.audio);
            handleNavigation(result.location);
        } else if (result.audio) {
            playAudioResponse(result.audio);
        } else {
            throw new Error("Unexpected response format from server");
        }
    } catch (error) {
        console.error('Error processing request:', error);
    }
}

async function captureImage() {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    return new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg'));
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        micBtnWrapper.classList.remove('recording');
        micBtn.querySelector('i').classList.remove('text-red-500');
        micBtn.querySelector('i').classList.add('text-blue-500', 'hover:text-blue-600');
        if (audioStream) {
            audioStream.getTracks().forEach(track => track.stop());
            audioStream = null;
        }
    }
}

function handleNavigation(location) {
    console.log("Handling navigation for:", location);

    navigator.geolocation.getCurrentPosition((position) => {
        const { latitude, longitude } = position.coords;

        const googleMapsAppUrl = `comgooglemaps://?saddr=${latitude},${longitude}&daddr=${encodeURIComponent(location)}&directionsmode=walking&nav=1`;
        const appleMapsUrl = `maps://maps.apple.com/?saddr=${latitude},${longitude}&daddr=${encodeURIComponent(location)}&dirflg=w`;
        const googleMapsWebUrl = `https://www.google.com/maps/dir/?api=1&origin=${latitude},${longitude}&destination=${encodeURIComponent(location)}&travelmode=walking`;

        if (/iPhone|iPad|iPod/i.test(navigator.userAgent)) {
            window.location.href = googleMapsAppUrl;

            setTimeout(() => {
                window.location.href = appleMapsUrl;
            }, 1000);

            setTimeout(() => {
                window.open(googleMapsWebUrl, '_blank');
            }, 2000);
        } else if (/Android/i.test(navigator.userAgent)) {
            window.location.href = googleMapsAppUrl;

            setTimeout(() => {
                window.open(googleMapsWebUrl, '_blank');
            }, 1000);
        } else {
            window.open(googleMapsWebUrl, '_blank');
        }
    }, (error) => {
        console.error('Error getting location:', error);
        const fallbackUrl = `https://www.google.com/maps/search/${encodeURIComponent(location)}`;
        window.open(fallbackUrl, '_blank');
    });
}

function playAudioResponse(audioBase64) {
    const audioBlob = base64ToBlob(audioBase64, 'audio/mp3');
    const audioUrl = URL.createObjectURL(audioBlob);
    if (audioPlayer) {
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
    }
    audioPlayer = new Audio(audioUrl);
    audioPlayer.play();
}

function base64ToBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], {type: mimeType});
}

// Start the app when the page loads
window.addEventListener('load', startApp);