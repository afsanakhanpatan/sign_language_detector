from flask import Flask, jsonify, render_template, url_for, redirect, flash, session, request, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask_socketio import SocketIO, emit
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, Email, EqualTo
from flask_bcrypt import Bcrypt
from datetime import datetime
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from flask_mail import Message, Mail
import random
import re
import pickle
import cv2
import mediapipe as mp
import numpy as np
import warnings
import time

# Suppress warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

CORS(app)  # Allow cross-origin requests for all routes
socketio = SocketIO(app, cors_allowed_origins="*")

# -------------------Encrypt Password using Hash Func-------------------
bcrypt = Bcrypt(app)

# -------------------Database Model Setup-------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'
serializer = Serializer(app.config['SECRET_KEY'])
db = SQLAlchemy(app)
app.app_context().push()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# -------------------mail configuration-------------------
app.config["MAIL_SERVER"] = 'smtp.gmail.com'
app.config["MAIL_PORT"] = 587
app.config["MAIL_USERNAME"] = 'handssignify@gmail.com'
app.config["MAIL_PASSWORD"] = 'ttbylakctxvvvnxe'
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
mail = Mail(app)
# --------------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------Database Model-------------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), nullable=False, unique=True)
    email = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(80), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
# ----------------------------------------------------

# -------------------Machine Learning Initialization-------------------
print("🔄 Loading machine learning model...")
model = None
current_prediction = "No hand detected"

# Global variables for prediction throttling
last_prediction_time = 0
prediction_cooldown = 2  # seconds between predictions
last_predicted_char = None
prediction_history = []
tts_enabled = True  # Global TTS control

try:
    # Try loading with compatibility fix
    with open('./model.p', 'rb') as f:
        model_dict = pickle.load(f)
    
    model = model_dict['model']
    print("✅ Model loaded successfully")
    
    # Fix compatibility issues
    if hasattr(model, 'estimators_'):
        for estimator in model.estimators_:
            if hasattr(estimator, 'monotonic_cst'):
                delattr(estimator, 'monotonic_cst')
    
    print("✅ Model compatibility fixes applied")
    
except Exception as e:
    print(f"❌ Error loading the model: {e}")
    print("🔧 Creating a dummy model for demonstration...")
    
    # Create a simple dummy model for testing
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    # Train on dummy data just to initialize
    X_dummy = np.random.rand(100, 42)
    y_dummy = np.random.randint(0, 33, 100)  # 33 classes for our labels
    model.fit(X_dummy, y_dummy)
    print("✅ Dummy model created for testing")

# Initialize MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

hands = mp_hands.Hands(static_image_mode=True, min_detection_confidence=0.3)

labels_dict = {
    0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I', 9: 'J', 
    10: 'K', 11: 'L', 12: 'M', 13: 'N', 14: 'O', 15: 'P', 16: 'Q', 17: 'R', 18: 'S', 
    19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X', 24: 'Y', 25: 'Z', 26: 'Hello', 
    27: 'Done', 28: 'Thank You', 29: 'I Love you', 30: 'Sorry', 31: 'Please', 
    32: 'You are welcome'
}
# ----------------------------------------------------

# -------------------WebSocket Handlers-------------------
@socketio.on('connect')
def handle_connect():
    print('✅ Client connected via WebSocket')
    emit('connection_response', {
        'status': 'connected', 
        'message': 'WebSocket connection established',
        'current_prediction': current_prediction,
        'history': prediction_history[-5:]  # Last 5 predictions
    })

@socketio.on('disconnect')
def handle_disconnect():
    print('❌ Client disconnected from WebSocket')

@socketio.on('get_prediction')
def handle_get_prediction():
    emit('current_prediction', {
        'prediction': current_prediction,
        'history': prediction_history[-5:]
    })

@socketio.on('toggle_voice')
def handle_toggle_voice(data):
    global tts_enabled
    tts_enabled = data.get('enabled', True)
    print(f"🔊 TTS {'enabled' if tts_enabled else 'disabled'}")
    emit('voice_status', {'enabled': tts_enabled})

@socketio.on('clear_predictions')
def handle_clear_predictions():
    global prediction_history
    prediction_history.clear()
    print("🗑️ Prediction history cleared")
    emit('predictions_cleared')

@socketio.on('start_detection')
def handle_start_detection():
    print("🎬 Detection started via WebSocket")
    emit('detection_status', {'status': 'started'})

@socketio.on('stop_detection')
def handle_stop_detection():
    global current_prediction
    current_prediction = "Detection stopped"
    print("⏹️ Detection stopped via WebSocket")
    emit('detection_status', {'status': 'stopped'})

# -------------------Welcome or Home Page-------------
@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
@app.route('/home.html', methods=['GET', 'POST'])
def home():
    session.clear()
    return render_template('home.html')
# ----------------------------------------------------

# -------------------feed back Page-----------------------
@app.route('/feed', methods=['GET', 'POST'])
@login_required
def feed():
    return render_template('feed.html')
# ----------------------------------------------------

# -------------------Discover More Page---------------
@app.route('/discover_more', methods=['GET', 'POST']) 
def discover_more():
    return render_template('discover_more.html')
# ----------------------------------------------------

# -------------------Guide Page-----------------------
@app.route('/guide', methods=['GET', 'POST'])
def guide():
    return render_template('guide.html')
# ----------------------------------------------------

# -------------------Login Page-------------------
class LoginForm(FlaskForm):
    username = StringField(label='username', validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(label='email', validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    password = PasswordField(label='password', validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if 'registered' in session and session['registered']:
        session.pop('registered', None)
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data) and User.query.filter_by(email=form.email.data).first():
            login_user(user)
            flash('Login successfully.', category='success')
            name = form.username.data
            session['name'] = name
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash(f'Login unsuccessful for {form.username.data}.', category='danger')
    return render_template('login.html', form=form)
# ----------------------------------------------------

# -------------------Dashboard or Logged Page-------------------
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if 'logged_in' in session and session['logged_in']:
        name = session.get('name')
        return render_template('dashboard.html', name=name)
    return redirect(url_for('login'))
# ----------------------------------------------------

# -------------------About Page-----------------------
@app.route('/about', methods=['GET', 'POST'])
def about():
    return render_template('about.html')
# ----------------------------------------------------

# -------------------Logged Out Page-------------------
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    session.clear()
    logout_user()
    flash('Account Logged out successfully.', category='success')
    return redirect(url_for('login'))
# ----------------------------------------------------

# -------------------Register Page-------------------
class RegisterForm(FlaskForm):
    username = StringField(label='username', validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(label='email', validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    password = PasswordField(label='password', validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    confirm_password = PasswordField(label='confirm_password', validators=[InputRequired(), EqualTo('password')], render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            flash('That Username already exists. Please choose a different one.', 'danger')
            raise ValidationError('That username already exists. Please choose a different one.')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        session['registered'] = True
        flash(f'Account Created for {form.username.data} successfully.', category='success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)
# ----------------------------------------------------

# -------------------Update or reset Email Page-------------------
class ResetMailForm(FlaskForm):
    username = StringField(label='username', validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(label='email', validators=[InputRequired(), Email()], render_kw={"placeholder": "Old Email"})
    new_email = StringField(label='new_email', validators=[InputRequired(), Email()], render_kw={"placeholder": "New Email"})
    password = PasswordField(label='password', validators=[InputRequired()], render_kw={"placeholder": "Password"})
    submit = SubmitField('Update Email')

@app.route('/reset_email', methods=['GET', 'POST'])
@login_required
def reset_email():
    form = ResetMailForm()
    if 'logged_in' in session and session['logged_in']:
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and bcrypt.check_password_hash(user.password, form.password.data) and User.query.filter_by(email=form.email.data).first():
                user.email = form.new_email.data
                db.session.commit()
                flash('Email reset successfully.', category='success')
                session.clear()
                return redirect(url_for('login'))
            else:
                flash('Invalid email, password, or combination.', category='danger')
        return render_template('reset_email.html', form=form)
    return redirect(url_for('login'))
# --------------------------------------------------------------

# -------------------Forgot Password With OTP-------------------
class ResetPasswordForm(FlaskForm):
    username = StringField(label='username', validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(label='email', validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    submit = SubmitField('Send OTP')

class ForgotPasswordForm(FlaskForm):
    username = StringField(label='username', validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(label='email', validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    new_password = PasswordField(label='new_password', validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "New Password"})
    confirm_password = PasswordField(label='confirm_password', validators=[InputRequired(), EqualTo('new_password')], render_kw={"placeholder": "Confirm Password"})
    otp = StringField(label='otp', validators=[InputRequired(), Length(min=6, max=6)], render_kw={"placeholder": "Enter OTP"})
    submit = SubmitField('Reset Password')

def send_mail(name, email, otp):
    msg = Message('Reset Email OTP Password', sender='handssignify@gmail.com', recipients=[email])
    msg.body = f"Hi {name},\n\nYour email OTP is: {otp}\n\nUse this OTP to reset your password."
    mail.send(msg)

def generate_otp():
    return random.randint(100000, 999999)

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    otp = generate_otp()
    session['otp'] = str(otp)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and User.query.filter_by(email=form.email.data).first():
            send_mail(form.username.data, form.email.data, otp)
            flash('Reset Request Sent. Check your mail.', 'success')
            return redirect(url_for('forgot_password'))
        else:
            flash('Email and username combination does not exist.', 'danger')
    return render_template('reset_password_request.html', form=form)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        otp = form.otp.data
        stored_otp = session.get('otp')
        
        if stored_otp and otp == stored_otp:
            user = User.query.filter_by(username=form.username.data).first()
            if user and User.query.filter_by(email=form.email.data).first():
                user.password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
                db.session.commit()
                session.pop('otp', None)
                flash('Password Changed Successfully.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Email and username combination does not exist.', 'danger')
        else:
            flash("OTP verification failed.", 'danger')
    return render_template('forgot_password.html', form=form)
# ---------------------------------------------------------------

# ------------------------- Update Password ---------------------
class UpdatePasswordForm(FlaskForm):
    username = StringField(label='username', validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(label='email', validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    new_password = PasswordField(label='new_password', validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "New Password"})
    confirm_password = PasswordField(label='confirm_password', validators=[InputRequired(), EqualTo('new_password')], render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField('Update Password')

@app.route('/update_password', methods=['GET', 'POST'])
@login_required
def update_password():
    form = UpdatePasswordForm()
    if form.validate_on_submit() and 'logged_in' in session and session['logged_in']:
        user = User.query.filter_by(username=form.username.data).first()
        if user and User.query.filter_by(email=form.email.data).first():
            user.password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            db.session.commit()
            flash('Password Changed Successfully.', 'success')
            session.clear()
            return redirect(url_for('login'))
        else:
            flash("Username and email combination does not exist.", 'danger')
    return render_template('update_password.html', form=form)
# -----------------------------  end  ---------------------------

# -------------------Machine Learning ------------------
def generate_frames():
    global current_prediction, last_prediction_time, last_predicted_char, prediction_history
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Could not open camera")
        return
    
    print("✅ Camera opened successfully")
    
    try:
        while True:
            data_aux = []
            x_ = []
            y_ = []

            ret, frame = cap.read()
            if not ret:
                break

            H, W, _ = frame.shape
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            results = hands.process(frame_rgb)
            current_prediction = "No hand detected"  # Reset prediction
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style())

                    # Process hand landmarks
                    data_aux = []
                    x_ = []
                    y_ = []

                    for i in range(len(hand_landmarks.landmark)):
                        x = hand_landmarks.landmark[i].x
                        y = hand_landmarks.landmark[i].y
                        x_.append(x)
                        y_.append(y)

                    for i in range(len(hand_landmarks.landmark)):
                        x = hand_landmarks.landmark[i].x
                        y = hand_landmarks.landmark[i].y
                        data_aux.append(x - min(x_))
                        data_aux.append(y - min(y_))

                    x1 = int(min(x_) * W) - 10
                    y1 = int(min(y_) * H) - 10
                    x2 = int(max(x_) * W) - 10
                    y2 = int(max(y_) * H) - 10

                    if model is not None and len(data_aux) == 42:
                        try:
                            prediction = model.predict([np.asarray(data_aux)])
                            predicted_character = labels_dict[int(prediction[0])]
                            current_prediction = predicted_character

                            current_time = time.time()
                            
                            # Only emit if enough time has passed AND prediction changed AND TTS is enabled
                            if (current_time - last_prediction_time > prediction_cooldown and 
                                predicted_character != last_predicted_char):
                                
                                print(f"✅ Predicted: {predicted_character}")
                                
                                # Add to history
                                timestamp = datetime.utcnow().strftime('%H:%M:%S')
                                prediction_history.append({
                                    'prediction': predicted_character,
                                    'timestamp': timestamp
                                })
                                
                                # Keep only last 10 predictions
                                if len(prediction_history) > 10:
                                    prediction_history.pop(0)
                                
                                # Emit the prediction via WebSocket
                                socketio.emit('new_prediction', {
                                    'prediction': predicted_character,
                                    'timestamp': timestamp,
                                    'history': prediction_history[-5:],  # Last 5 predictions
                                    'tts_enabled': tts_enabled
                                })
                                
                                last_prediction_time = current_time
                                last_predicted_char = predicted_character

                            # Always show prediction on video
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 4)
                            cv2.putText(frame, predicted_character, (x1, y1 - 10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3, cv2.LINE_AA)
                            
                        except Exception as e:
                            print(f"⚠️ Prediction error: {e}")
                            current_prediction = "Prediction error"
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 4)
                            cv2.putText(frame, "Hand Detected", (x1, y1 - 10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        cap.release()

@app.route('/video_feed')
@login_required
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/current_prediction')
def get_current_prediction():
    return jsonify({'prediction': current_prediction})

@app.route('/test_model')
def test_model():
    if model is None:
        return "❌ Model is not loaded"
    try:
        dummy_data = np.random.rand(42).reshape(1, -1)
        prediction = model.predict(dummy_data)
        return f"✅ Model test successful! Prediction: {prediction[0]}"
    except Exception as e:
        return f"❌ Model test failed: {str(e)}"

# -------------------Additional Routes for Navigation-------------------
@app.route('/welcome')
def welcome():
    return render_template('Welcome.html')

@app.route('/welcome2')
def welcome2():
    return render_template('Welcome2.html')

@app.route('/welcome3')
def welcome3():
    return render_template('Welcome3.html')

# -------------------Debug Route-------------------
@app.route('/debug-routes')
def debug_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify(routes)

# -------------------Video Page-----------------------
@app.route('/video', methods=['GET', 'POST'])
@login_required
def video():
    return render_template('video.html')

# -------------------Practice Page-------------------
@app.route('/practice', methods=['GET', 'POST'])
@login_required
def practice():
    return render_template('practice.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("\n" + "="*50)
    print("🚀 Flask Application Status:")
    print(f"📊 Model Status: {'✅ Loaded' if model else '❌ Not Loaded'}")
    print(f"🎥 MediaPipe: ✅ Initialized")
    print(f"🗄️  Database: ✅ Ready")
    print(f"🔌 WebSocket: ✅ Ready")
    print(f"📧 Mail Server: ✅ Configured")
    print(f"🔐 Authentication: ✅ Ready")
    print(f"🤖 ML Pipeline: ✅ Active")
    print(f"⏱️  Prediction Throttling: ✅ {prediction_cooldown}s cooldown")
    print("="*50)
    print("\n🌐 Starting Flask server with WebSocket support...")
    
    try:
        socketio.run(app, debug=True, host='127.0.0.1', port=5000, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        print("🔄 Trying alternative startup method...")
        app.run(debug=True, host='127.0.0.1', port=5000)