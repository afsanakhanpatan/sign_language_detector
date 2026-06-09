// Signify - Dashboard JavaScript with Working Camera and Upload

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const captureBtn = document.getElementById('captureBtn');
    const predictionDiv = document.getElementById('prediction');
    const lastPredictionsList = document.getElementById('lastPredictions');
    const ttsToggle = document.getElementById('ttsToggle');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    const uploadTtsToggle = document.getElementById('uploadTtsToggle');
    
    // Upload elements
    const uploadArea = document.getElementById('uploadArea');
    const imageInput = document.getElementById('imageInput');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    const uploadPrediction = document.getElementById('uploadPrediction');
    
    // Mode switching
    const cameraMode = document.getElementById('cameraMode');
    const uploadMode = document.getElementById('uploadMode');
    const cameraBtn = document.getElementById('cameraModeBtn');
    const uploadBtn = document.getElementById('uploadModeBtn');
    
    // Variables
    let stream = null;
    let ttsEnabled = true;
    let lastSpokenText = '';
    let lastSpokenTime = 0;
    let lastPredictions = [];
    const SPEECH_COOLDOWN = 2000;
    const MAX_PREDICTIONS = 10;

    // ==================== TEXT TO SPEECH ====================
    function speakText(text) {
        if (!ttsEnabled) return;
        
        const currentTime = Date.now();
        if (currentTime - lastSpokenTime < SPEECH_COOLDOWN) return;
        if (text === lastSpokenText) return;
        
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            utterance.pitch = 1;
            utterance.volume = 1;
            utterance.onstart = () => {
                lastSpokenTime = Date.now();
                if (predictionDiv) predictionDiv.classList.add('speaking-animation');
                if (uploadPrediction) uploadPrediction.classList.add('speaking-animation');
            };
            utterance.onend = () => {
                if (predictionDiv) predictionDiv.classList.remove('speaking-animation');
                if (uploadPrediction) uploadPrediction.classList.remove('speaking-animation');
                lastSpokenText = text;
            };
            speechSynthesis.speak(utterance);
        }
    }

    // Update TTS button
    function updateTTSToggle() {
        const elements = [ttsToggle, uploadTtsToggle];
        elements.forEach(el => {
            if (el) {
                const icon = el.querySelector('i');
                const span = el.querySelector('span');
                if (ttsEnabled) {
                    icon.className = 'fas fa-volume-up';
                    span.textContent = 'Voice ON';
                    el.classList.remove('off');
                } else {
                    icon.className = 'fas fa-volume-mute';
                    span.textContent = 'Voice OFF';
                    el.classList.add('off');
                }
            }
        });
    }

    function toggleVoice() {
        ttsEnabled = !ttsEnabled;
        updateTTSToggle();
        if (ttsEnabled) speakText("Voice on");
        else if ('speechSynthesis' in window) speechSynthesis.cancel();
    }

    // ==================== PREDICTION HISTORY ====================
    function addToRecentPredictions(prediction, timestamp) {
        lastPredictions.unshift({ prediction, timestamp });
        if (lastPredictions.length > MAX_PREDICTIONS) lastPredictions.pop();
        updateRecentPredictionsList();
    }

    function updateRecentPredictionsList() {
        if (!lastPredictionsList) return;
        lastPredictionsList.innerHTML = '';
        if (lastPredictions.length === 0) {
            lastPredictionsList.innerHTML = '<div class="history-item"><span class="history-prediction">No translations yet</span></div>';
            return;
        }
        lastPredictions.forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-item';
            div.innerHTML = `<span class="history-prediction">${item.prediction}</span><span class="history-time">${item.timestamp}</span>`;
            lastPredictionsList.appendChild(div);
        });
    }

    function clearPredictions() {
        lastPredictions = [];
        updateRecentPredictionsList();
        if (predictionDiv) predictionDiv.innerHTML = '<span class="status-indicator status-inactive"></span>Ready to capture';
        if (uploadPrediction) uploadPrediction.innerHTML = 'Waiting for upload...';
        speakText("History cleared");
    }

    // ==================== CAMERA MODE ====================
    async function initCamera() {
        try {
            if (stream) stopCamera();

            // Show "requesting" state
            if (predictionDiv) predictionDiv.innerHTML = '<span class="status-indicator status-active"></span>Requesting camera...';

            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }
            });
            video.srcObject = stream;
            await video.play();

            // Hide any permission overlay
            const overlay = document.getElementById('camera-permission-overlay');
            if (overlay) overlay.style.display = 'none';

            if (predictionDiv) predictionDiv.innerHTML = '<span class="status-indicator status-active"></span>Camera ready — Click capture';
        } catch (err) {
            console.error("Camera error:", err.name, err.message);
            showCameraPermissionUI(err);
        }
    }

    function showCameraPermissionUI(err) {
        // Show overlay with instructions
        let overlay = document.getElementById('camera-permission-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'camera-permission-overlay';
            overlay.style.cssText = `
                position:absolute; inset:0; background:rgba(15,20,35,0.97);
                display:flex; flex-direction:column; align-items:center;
                justify-content:center; gap:20px; border-radius:16px; z-index:10; padding:32px; text-align:center;
            `;
            const videoWrapper = document.querySelector('.video-wrapper');
            if (videoWrapper) videoWrapper.appendChild(overlay);
        }

        const isDenied = err && (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError');
        overlay.innerHTML = `
            <div style="font-size:48px;">📷</div>
            <h4 style="color:#fff; margin:0; font-size:18px; font-weight:700;">
                ${isDenied ? 'Camera Access Blocked' : 'Camera Not Found'}
            </h4>
            <p style="color:#94a3b8; margin:0; font-size:14px; max-width:280px; line-height:1.6;">
                ${isDenied
                    ? 'Click the <strong style="color:#fff">🔒 lock icon</strong> in your browser address bar → Site Settings → Allow Camera'
                    : 'No camera detected. Please connect a webcam and try again.'
                }
            </p>
            <button onclick="window.retryCamera()" style="
                background: linear-gradient(135deg,#6366f1,#4f46e5);
                color:#fff; border:none; border-radius:12px;
                padding:12px 28px; font-size:15px; font-weight:600;
                cursor:pointer; margin-top:8px; box-shadow:0 4px 16px rgba(99,102,241,0.4);
                transition:transform 0.2s;
            " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                🔄 Try Again
            </button>
        `;
        overlay.style.display = 'flex';

        if (predictionDiv) predictionDiv.innerHTML = '<span class="status-indicator status-inactive"></span>Camera blocked';
    }


    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
            video.srcObject = null;
        }
    }

    async function captureAndPredict() {
        if (!video.srcObject) {
            predictionDiv.innerHTML = "Camera not ready - please wait";
            return;
        }
        
        predictionDiv.innerHTML = '<span class="status-indicator status-active"></span>Processing... <span class="processing-spinner"></span>';
        
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        canvas.toBlob(async (blob) => {
            const formData = new FormData();
            formData.append('image', blob, 'capture.jpg');
            
            try {
                const response = await fetch('/predict', { method: 'POST', body: formData });
                const data = await response.json();
                
                if (data.success) {
                    predictionDiv.innerHTML = `<span class="status-indicator status-active"></span>${data.prediction}`;
                    addToRecentPredictions(data.prediction, data.timestamp);
                    const invalid = ['No hand detected', 'Prediction error', 'Unable to process'];
                    if (!invalid.includes(data.prediction)) speakText(data.prediction);
                } else {
                    predictionDiv.innerHTML = `<span class="status-indicator status-inactive"></span>${data.error || 'Prediction failed'}`;
                }
            } catch (error) {
                console.error(error);
                predictionDiv.innerHTML = '<span class="status-indicator status-inactive"></span>Error processing image';
            }
        }, 'image/jpeg');
    }

    // ==================== UPLOAD MODE ====================
    async function uploadAndPredict(file) {
        if (!file) return;
        
        if (!file.type.match('image.*')) {
            alert('Please select an image file (JPG, PNG, JPEG)');
            return;
        }
        
        if (file.size > 16 * 1024 * 1024) {
            alert('File size must be less than 16MB');
            return;
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            imagePreview.style.display = 'block';
        };
        reader.readAsDataURL(file);
        
        uploadPrediction.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        
        const formData = new FormData();
        formData.append('image', file);
        
        try {
            const response = await fetch('/predict', { method: 'POST', body: formData });
            const data = await response.json();
            
            if (data.success) {
                uploadPrediction.innerHTML = data.prediction;
                addToRecentPredictions(data.prediction, data.timestamp);
                const invalid = ['No hand detected', 'Prediction error', 'Unable to process'];
                if (!invalid.includes(data.prediction)) speakText(data.prediction);
            } else {
                uploadPrediction.innerHTML = data.error || 'Prediction failed';
            }
        } catch (error) {
            console.error(error);
            uploadPrediction.innerHTML = 'Error processing image';
        }
    }

    function handleFile(file) {
        if (file) uploadAndPredict(file);
    }

    // ==================== MODE SWITCHING ====================
    function switchToCamera() {
        cameraMode.style.display = 'block';
        uploadMode.style.display = 'none';
        cameraBtn.classList.add('active');
        uploadBtn.classList.remove('active');
        initCamera();
    }

    function switchToUpload() {
        cameraMode.style.display = 'none';
        uploadMode.style.display = 'block';
        uploadBtn.classList.add('active');
        cameraBtn.classList.remove('active');
        stopCamera();
    }

    // ==================== EVENT LISTENERS ====================
    if (captureBtn) captureBtn.addEventListener('click', captureAndPredict);
    if (ttsToggle) ttsToggle.addEventListener('click', toggleVoice);
    if (uploadTtsToggle) uploadTtsToggle.addEventListener('click', toggleVoice);
    if (clearHistoryBtn) clearHistoryBtn.addEventListener('click', clearPredictions);
    
    if (cameraBtn) cameraBtn.addEventListener('click', switchToCamera);
    if (uploadBtn) uploadBtn.addEventListener('click', switchToUpload);
    
    // Upload area events
    if (uploadArea) {
        uploadArea.addEventListener('click', () => imageInput.click());
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
        });
    }
    
    if (imageInput) {
        imageInput.addEventListener('change', (e) => {
            if (e.target.files.length) handleFile(e.target.files[0]);
        });
    }

    // Initialize
    initCamera();
    updateTTSToggle();
    console.log("Dashboard ready!");
});

// Global retry function accessible from HTML onclick
window.retryCamera = async function() {
    const overlay = document.getElementById('camera-permission-overlay');
    if (overlay) {
        overlay.innerHTML = '<div style="color:#94a3b8;font-size:15px;">Requesting camera access...</div>';
    }
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        const video = document.getElementById('video');
        const predictionDiv = document.getElementById('prediction');
        video.srcObject = stream;
        await video.play();
        if (overlay) overlay.style.display = 'none';
        if (predictionDiv) predictionDiv.innerHTML = '<span class="status-indicator status-active"></span>Camera ready — Click capture';
    } catch (err) {
        if (overlay) {
            overlay.innerHTML = `
                <div style="font-size:48px;">📷</div>
                <h4 style="color:#fff;margin:0;font-size:18px;font-weight:700;">Still Blocked</h4>
                <p style="color:#94a3b8;margin:0;font-size:13px;max-width:280px;line-height:1.6;">
                    In Chrome: Click the <strong style="color:#fff">🔒 lock</strong> in the address bar
                    → Camera → <strong style="color:#fff">Allow</strong> → Reload the page
                </p>
                <button onclick="window.retryCamera()" style="background:linear-gradient(135deg,#6366f1,#4f46e5);color:#fff;border:none;border-radius:12px;padding:12px 28px;font-size:15px;font-weight:600;cursor:pointer;margin-top:8px;">
                    🔄 Try Again
                </button>
            `;
        }
    }
};