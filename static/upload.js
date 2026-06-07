// Signify - Image Upload Handler

document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('uploadArea');
    const imageInput = document.getElementById('imageInput');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    const uploadPrediction = document.getElementById('uploadPrediction');
    
    let ttsEnabled = true;
    let lastSpokenText = '';
    let lastSpokenTime = 0;
    const SPEECH_COOLDOWN = 2000;

    // Text-to-Speech function
    function speakText(text) {
        if (!ttsEnabled) return;
        
        const currentTime = Date.now();
        if (currentTime - lastSpokenTime < SPEECH_COOLDOWN) {
            console.log("⏱️ Speech throttled");
            return;
        }
        
        if (text === lastSpokenText) {
            console.log("🔁 Same prediction - not speaking again");
            return;
        }
        
        console.log("🔊 Speaking:", text);
        
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            utterance.pitch = 1;
            utterance.volume = 1;
            
            utterance.onstart = () => {
                lastSpokenTime = Date.now();
                if (uploadPrediction) {
                    uploadPrediction.classList.add('speaking-animation');
                }
            };
            
            utterance.onend = () => {
                if (uploadPrediction) {
                    uploadPrediction.classList.remove('speaking-animation');
                }
                lastSpokenText = text;
            };
            
            utterance.onerror = (event) => {
                console.error("❌ TTS error:", event);
                lastSpokenText = '';
            };
            
            speechSynthesis.speak(utterance);
        }
    }

    // Upload and predict function
    async function uploadAndPredict(file) {
        const formData = new FormData();
        formData.append('image', file);
        
        uploadPrediction.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        
        try {
            const response = await fetch('/predict', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                const prediction = data.prediction;
                uploadPrediction.innerHTML = prediction;
                
                const invalidPredictions = ['No hand detected', 'Prediction error', 'Unable to process'];
                if (!invalidPredictions.includes(prediction)) {
                    speakText(prediction);
                }
            } else {
                uploadPrediction.innerHTML = 'Error: ' + (data.error || 'Failed to process');
            }
        } catch (error) {
            console.error('Upload error:', error);
            uploadPrediction.innerHTML = 'Error processing image';
        }
    }

    // Handle file selection
    function handleFile(file) {
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
        
        uploadAndPredict(file);
    }

    // Click to upload
    if (uploadArea) {
        uploadArea.addEventListener('click', () => {
            imageInput.click();
        });
    }
    
    if (imageInput) {
        imageInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });
    }
    
    // Drag and drop
    if (uploadArea) {
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });
    }
    
    // TTS toggle for upload mode
    const uploadTtsToggle = document.getElementById('uploadTtsToggle');
    if (uploadTtsToggle) {
        uploadTtsToggle.addEventListener('click', () => {
            ttsEnabled = !ttsEnabled;
            const icon = uploadTtsToggle.querySelector('i');
            const text = uploadTtsToggle.querySelector('span');
            if (ttsEnabled) {
                icon.className = 'fas fa-volume-up';
                text.textContent = 'Voice ON';
                uploadTtsToggle.classList.remove('off');
                speakText("Voice on");
            } else {
                icon.className = 'fas fa-volume-mute';
                text.textContent = 'Voice OFF';
                uploadTtsToggle.classList.add('off');
                if ('speechSynthesis' in window) {
                    speechSynthesis.cancel();
                }
            }
        });
    }
});