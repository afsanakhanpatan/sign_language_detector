// main.js - WebSocket-based sign-to-speech with throttling
document.addEventListener('DOMContentLoaded', () => {
    const videoFeed = document.getElementById('videoFeed');
    const predictionDiv = document.getElementById('prediction');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusIndicator = document.getElementById('statusIndicator');
    const lastPredictionsList = document.getElementById('lastPredictions');
    
    let isMonitoring = false;
    let ttsEnabled = true;
    let lastSpokenText = '';
    let lastPredictions = [];
    let socket;
    const MAX_PREDICTIONS = 5;
    
    // Throttling variables
    let lastSpokenTime = 0;
    const SPEECH_COOLDOWN = 2000; // 2 seconds between speech

    // Initialize WebSocket connection
    function initializeWebSocket() {
        socket = io();
        
        socket.on('connect', () => {
            console.log('✅ Connected to server via WebSocket');
            updatePredictionDisplay('Connected - Show hand signs');
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
            updateVoiceButton();
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
            updatePredictionDisplay('Connection lost');
        });
    }

    // Text-to-Speech function with throttling
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
            utterance.rate = 0.8;
            utterance.pitch = 1;
            utterance.volume = 1;
            
            utterance.onstart = () => {
                console.log("✅ TTS started speaking");
                lastSpokenTime = Date.now();
                if (predictionDiv) {
                    predictionDiv.classList.add('speaking');
                }
            };
            
            utterance.onend = () => {
                console.log("✅ TTS finished speaking");
                if (predictionDiv) {
                    predictionDiv.classList.remove('speaking');
                }
                lastSpokenText = text;
            };
            
            utterance.onerror = (event) => {
                console.error("❌ TTS error:", event);
                lastSpokenText = ''; // Reset on error
            };
            
            speechSynthesis.speak(utterance);
        } else {
            console.log("❌ Text-to-speech not supported in this browser");
            showTTSError();
        }
    }

    // Update prediction display
    function updatePredictionDisplay(prediction) {
        if (predictionDiv) {
            predictionDiv.textContent = prediction;
            predictionDiv.className = 'prediction-result ' + 
                (prediction.includes('No hand') || prediction.includes('Connected') || 
                 prediction.includes('stopped') || prediction.includes('lost') ? 'no-hand' : 'active');
        }
        
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator ' + 
                (prediction.includes('No hand') || prediction.includes('Connected') || 
                 prediction.includes('stopped') || prediction.includes('lost') ? 'status-inactive' : 'status-active');
        }
    }

    // Add prediction to recent list
    function addToRecentPredictions(prediction, timestamp = null) {
        const predictionTime = timestamp || new Date().toLocaleTimeString();
        lastPredictions.unshift({
            prediction,
            timestamp: predictionTime
        });
        
        // Keep only last 5 predictions
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
            const li = document.createElement('li');
            li.textContent = 'No predictions yet';
            li.className = 'no-predictions';
            lastPredictionsList.appendChild(li);
            return;
        }
        
        lastPredictions.forEach((item, index) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="prediction-text">${item.prediction}</span>
                <span class="timestamp">${item.timestamp}</span>
            `;
            lastPredictionsList.appendChild(li);
        });
    }

    // Speak if prediction is valid
    function speakIfValid(prediction, serverTTSEnabled = true) {
        const invalidPredictions = [
            'No hand detected', 'Prediction error', 'Connected', 'Connection lost',
            'Detection active', 'Detection stopped', 'Hand Detected'
        ];
        
        // Check if TTS is enabled both client-side and server-side
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

    // Show TTS error
    function showTTSError() {
        const controls = document.querySelector('.controls');
        if (controls) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'tts-warning';
            errorDiv.innerHTML = '❌ Text-to-speech not supported in this browser. Try Chrome.';
            controls.appendChild(errorDiv);
        }
    }

    // Update voice button appearance
    function updateVoiceButton() {
        const ttsToggleBtn = document.getElementById('ttsToggleBtn');
        if (ttsToggleBtn) {
            if (ttsEnabled) {
                ttsToggleBtn.innerHTML = '🔊 Voice ON';
                ttsToggleBtn.style.background = 'var(--success-color)';
            } else {
                ttsToggleBtn.innerHTML = '🔇 Voice OFF';
                ttsToggleBtn.style.background = 'var(--secondary-color)';
            }
        }
    }

    // Start monitoring
    function startMonitoring() {
        if (isMonitoring) return;
        
        isMonitoring = true;
        console.log('🎬 Starting sign-to-speech monitoring');
        
        if (startBtn) startBtn.disabled = true;
        if (stopBtn) stopBtn.disabled = false;
        
        updatePredictionDisplay('Detection active...');
        
        // Notify server
        if (socket) {
            socket.emit('start_detection');
            socket.emit('get_prediction');
        }
    }

    // Stop monitoring
    function stopMonitoring() {
        isMonitoring = false;
        console.log('⏹️ Stopping monitoring');
        
        if (startBtn) startBtn.disabled = false;
        if (stopBtn) stopBtn.disabled = true;
        
        updatePredictionDisplay('Detection stopped');
        
        // Stop any ongoing speech
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
        }
        
        // Notify server
        if (socket) {
            socket.emit('stop_detection');
        }
    }

    // Toggle voice
    function toggleVoice() {
        ttsEnabled = !ttsEnabled;
        if (socket) {
            socket.emit('toggle_voice', { enabled: ttsEnabled });
        }
        updateVoiceButton();
        
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

    // Test TTS
    function testTTS() {
        if (!ttsEnabled) {
            speakText("Voice is currently off. Enable voice first.");
            return;
        }
        console.log("🎤 Testing TTS");
        speakText("Voice is working! Show me hand signs now.");
    }

    // Create TTS controls
    function createTTSControls() {
        const controls = document.querySelector('.controls');
        if (!controls) return;
        
        // TTS toggle button
        const ttsToggleBtn = document.createElement('button');
        ttsToggleBtn.id = 'ttsToggleBtn';
        ttsToggleBtn.className = 'control-btn';
        ttsToggleBtn.innerHTML = '🔊 Voice ON';
        ttsToggleBtn.style.background = 'var(--success-color)';
        
        // Test TTS button
        const testTTSBtn = document.createElement('button');
        testTTSBtn.id = 'testTTSBtn';
        testTTSBtn.className = 'control-btn';
        testTTSBtn.innerHTML = '🎤 Test Voice';
        testTTSBtn.style.background = 'var(--accent-color)';
        
        // Clear predictions button
        const clearBtn = document.createElement('button');
        clearBtn.id = 'clearBtn';
        clearBtn.className = 'control-btn';
        clearBtn.innerHTML = '🗑️ Clear';
        clearBtn.style.background = 'var(--warning-color)';
        
        // Event listeners
        ttsToggleBtn.addEventListener('click', toggleVoice);
        testTTSBtn.addEventListener('click', testTTS);
        clearBtn.addEventListener('click', clearPredictions);
        
        controls.appendChild(ttsToggleBtn);
        controls.appendChild(testTTSBtn);
        controls.appendChild(clearBtn);
    }

    // Initialize everything
    function initialize() {
        // Initialize WebSocket
        initializeWebSocket();
        
        // Create controls
        createTTSControls();
        
        // Set up event listeners
        if (startBtn) {
            startBtn.addEventListener('click', startMonitoring);
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', stopMonitoring);
            stopBtn.disabled = true;
        }
        
        // Auto-start monitoring after short delay
        setTimeout(() => {
            startMonitoring();
        }, 1000);
        
        console.log("🚀 Sign-to-speech system ready!");
        console.log("🔊 TTS Support:", 'speechSynthesis' in window);
        console.log("⏱️ Speech cooldown:", SPEECH_COOLDOWN + "ms");
    }

    // Start initialization
    initialize();
});