// Signify - Main WebSocket Client

document.addEventListener('DOMContentLoaded', () => {
    const videoFeed = document.getElementById('videoFeed');
    const predictionDiv = document.getElementById('prediction');
    const lastPredictionsList = document.getElementById('lastPredictions');
    const ttsToggle = document.getElementById('ttsToggle');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    
    let isMonitoring = true;
    let ttsEnabled = true;
    let lastSpokenText = '';
    let lastPredictions = [];
    let socket;
    const MAX_PREDICTIONS = 10;
    
    let lastSpokenTime = 0;
    const SPEECH_COOLDOWN = 2000;

    // Initialize WebSocket connection
    function initializeWebSocket() {
        socket = io();
        
        socket.on('connect', () => {
            console.log('✅ Connected to server via WebSocket');
            updatePredictionDisplay('Ready - Show hand signs');
        });
        
        socket.on('connection_response', (data) => {
            console.log('🔌 Server response:', data.message);
            if (data.history && data.history.length > 0) {
                lastPredictions = data.history;
                updateRecentPredictionsList();
            }
        });
        
        socket.on('new_prediction', (data) => {
            console.log('🎯 New prediction received:', data.prediction);
            updatePredictionDisplay(data.prediction);
            addToRecentPredictions(data.prediction, data.timestamp);
            speakIfValid(data.prediction, data.tts_enabled);
        });
        
        socket.on('current_prediction', (data) => {
            console.log('📊 Current prediction:', data.prediction);
            updatePredictionDisplay(data.prediction);
            if (data.history && data.history.length > 0) {
                lastPredictions = data.history;
                updateRecentPredictionsList();
            }
        });
        
        socket.on('voice_status', (data) => {
            ttsEnabled = data.enabled;
            updateTTSToggle();
            console.log(`🔊 Voice ${ttsEnabled ? 'enabled' : 'disabled'}`);
        });
        
        socket.on('detection_status', (data) => {
            console.log(`🎬 Detection ${data.status}`);
            if (data.status === 'stopped') {
                updatePredictionDisplay('Detection stopped');
            }
        });
        
        socket.on('disconnect', () => {
            console.log('❌ Disconnected from server');
            updatePredictionDisplay('Connection lost - reconnecting...');
            setTimeout(initializeWebSocket, 3000);
        });
    }

    // Text-to-Speech function
    function speakText(text) {
        if (!ttsEnabled) return;
        
        const currentTime = Date.now();
        if (currentTime - lastSpokenTime < SPEECH_COOLDOWN) {
            console.log("⏱️ Speech throttled - too soon");
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
                console.log("✅ TTS started speaking");
                lastSpokenTime = Date.now();
                if (predictionDiv) {
                    predictionDiv.classList.add('speaking-animation');
                }
            };
            
            utterance.onend = () => {
                console.log("✅ TTS finished speaking");
                if (predictionDiv) {
                    predictionDiv.classList.remove('speaking-animation');
                }
                lastSpokenText = text;
            };
            
            utterance.onerror = (event) => {
                console.error("❌ TTS error:", event);
                lastSpokenText = '';
            };
            
            speechSynthesis.speak(utterance);
        } else {
            console.log("❌ Text-to-speech not supported in this browser");
        }
    }

    // Update prediction display
    function updatePredictionDisplay(prediction) {
        if (predictionDiv) {
            const statusSpan = predictionDiv.querySelector('#statusIndicator');
            if (statusSpan) {
                const isActive = !prediction.includes('No hand') && 
                                !prediction.includes('Ready') && 
                                !prediction.includes('stopped') && 
                                !prediction.includes('lost');
                statusSpan.className = `status-indicator ${isActive ? 'status-active' : 'status-inactive'}`;
            }
            
            const predictionText = predictionDiv.cloneNode(true);
            predictionText.querySelectorAll('#statusIndicator, .tts-control').forEach(el => el.remove());
            const textNode = document.createTextNode(prediction);
            predictionDiv.innerHTML = '';
            predictionDiv.appendChild(statusSpan || document.createElement('span'));
            predictionDiv.appendChild(textNode);
        }
    }

    // Add prediction to recent list
    function addToRecentPredictions(prediction, timestamp = null) {
        const predictionTime = timestamp || new Date().toLocaleTimeString();
        lastPredictions.unshift({
            prediction,
            timestamp: predictionTime
        });
        
        if (lastPredictions.length > MAX_PREDICTIONS) {
            lastPredictions.pop();
        }
        
        updateRecentPredictionsList();
    }

    // Update recent predictions list
    function updateRecentPredictionsList() {
        if (!lastPredictionsList) return;
        
        lastPredictionsList.innerHTML = '';
        
        if (lastPredictions.length === 0) {
            const item = document.createElement('div');
            item.className = 'history-item';
            item.innerHTML = '<span class="history-prediction">No predictions yet</span>';
            lastPredictionsList.appendChild(item);
            return;
        }
        
        lastPredictions.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = 'history-item';
            div.innerHTML = `
                <span class="history-prediction">${item.prediction}</span>
                <span class="history-time">${item.timestamp}</span>
            `;
            lastPredictionsList.appendChild(div);
        });
    }

    // Speak if prediction is valid
    function speakIfValid(prediction, serverTTSEnabled = true) {
        const invalidPredictions = [
            'No hand detected', 'Prediction error', 'Ready', 'Connection lost',
            'Detection active', 'Detection stopped', 'Hand Detected'
        ];
        
        if (!ttsEnabled || !serverTTSEnabled) {
            console.log("🔇 TTS disabled - not speaking");
            return;
        }
        
        if (!invalidPredictions.includes(prediction)) {
            console.log("🎯 Speaking valid prediction:", prediction);
            speakText(prediction);
        } else {
            console.log("🚫 Invalid prediction - not speaking:", prediction);
        }
    }

    // Update TTS toggle button
    function updateTTSToggle() {
        if (ttsToggle) {
            const icon = ttsToggle.querySelector('i');
            const text = ttsToggle.querySelector('span');
            if (ttsEnabled) {
                icon.className = 'fas fa-volume-up';
                text.textContent = 'Voice ON';
                ttsToggle.classList.remove('off');
            } else {
                icon.className = 'fas fa-volume-mute';
                text.textContent = 'Voice OFF';
                ttsToggle.classList.add('off');
            }
        }
    }

    // Toggle voice
    function toggleVoice() {
        ttsEnabled = !ttsEnabled;
        if (socket) {
            socket.emit('toggle_voice', { enabled: ttsEnabled });
        }
        updateTTSToggle();
        
        if (ttsEnabled) {
            speakText("Voice on");
        } else {
            if ('speechSynthesis' in window) {
                speechSynthesis.cancel();
            }
        }
    }

    // Clear predictions
    function clearPredictions() {
        lastPredictions = [];
        updateRecentPredictionsList();
        if (socket) {
            socket.emit('clear_predictions');
        }
        console.log("🗑️ Predictions cleared");
    }

    // Event listeners
    if (ttsToggle) {
        ttsToggle.addEventListener('click', toggleVoice);
    }
    
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearPredictions);
    }

    // Initialize everything
    function initialize() {
        initializeWebSocket();
        console.log("🚀 Signify system ready!");
        console.log("🔊 TTS Support:", 'speechSynthesis' in window);
    }

    initialize();
});