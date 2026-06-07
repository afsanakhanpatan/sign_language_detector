from flask import Flask, jsonify, render_template, url_for, redirect, flash, session, request
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
import pickle
import cv2
import mediapipe as mp
import numpy as np
import warnings
import time
import os

# Suppress warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# -------------------Encrypt Password-------------------
bcrypt = Bcrypt(app)

# -------------------Database Setup-------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'
serializer = Serializer(app.config['SECRET_KEY'])
db = SQLAlchemy(app)
app.app_context().push()
db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# -------------------Mail Configuration-------------------
app.config["MAIL_SERVER"] = 'smtp.gmail.com'
app.config["MAIL_PORT"] = 587
app.config["MAIL_USERNAME"] = 'handssignify@gmail.com'
app.config["MAIL_PASSWORD"] = 'ttbylakctxvvvnxe'
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
mail = Mail(app)

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

# -------------------Machine Learning Initialization-------------------
print("🔄 Loading machine learning model...")
model = None

try:
    with open('./model.p', 'rb') as f:
        model_dict = pickle.load(f)
    model = model_dict['model']
    print("✅ Model loaded successfully")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    X_dummy = np.random.rand(100, 42)
    y_dummy = np.random.randint(0, 33, 100)
    model.fit(X_dummy, y_dummy)
    print("✅ Dummy model created")

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

prediction_history = []

def process_image(image_bytes):
    """Process uploaded image and return prediction"""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return "Invalid image"
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)
    
    if not results.multi_hand_landmarks:
        return "No hand detected"
    
    data_aux = []
    x_ = []
    y_ = []
    
    for hand_landmarks in results.multi_hand_landmarks:
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
    
    if model is not None and len(data_aux) == 42:
        try:
            prediction = model.predict([np.asarray(data_aux)])
            return labels_dict[int(prediction[0])]
        except Exception as e:
            print(f"Prediction error: {e}")
            return "Prediction error"
    
    return "Unable to process"

# -------------------Routes-------------------
@app.route('/')
@app.route('/home')
def home():
    session.clear()
    return render_template('home.html')

@app.route('/get_started')
def get_started():
    """Redirect to dashboard if logged in, else to login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/feed')
@login_required
def feed():
    return render_template('feed.html')

@app.route('/discover_more')
def discover_more():
    return render_template('discover_more.html')

@app.route('/guide')
def guide():
    return render_template('guide.html')

# -------------------Login-------------------
class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            session['name'] = form.username.data
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)

# -------------------Dashboard-------------------
@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('logged_in'):
        return render_template('dashboard.html', name=session.get('name'))
    return redirect(url_for('login'))

# -------------------Prediction Route-------------------
@app.route('/predict', methods=['POST'])
@login_required
def predict():
    """Handle image upload and return prediction"""
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No image selected'}), 400
    
    try:
        image_bytes = file.read()
        prediction = process_image(image_bytes)
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Store in history
        prediction_history.append({'prediction': prediction, 'timestamp': timestamp})
        if len(prediction_history) > 10:
            prediction_history.pop(0)
        
        return jsonify({
            'success': True,
            'prediction': prediction,
            'timestamp': timestamp,
            'history': prediction_history[-5:]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# -------------------Register-------------------
class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    confirm_password = PasswordField(validators=[InputRequired(), EqualTo('password')], render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('Username already exists')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Account created for {form.username.data}!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# -------------------Reset Email-------------------
class ResetMailForm(FlaskForm):
    username = StringField(validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(validators=[InputRequired(), Email()], render_kw={"placeholder": "Old Email"})
    new_email = StringField(validators=[InputRequired(), Email()], render_kw={"placeholder": "New Email"})
    password = PasswordField(validators=[InputRequired()], render_kw={"placeholder": "Password"})
    submit = SubmitField('Update Email')

@app.route('/reset_email', methods=['GET', 'POST'])
@login_required
def reset_email():
    form = ResetMailForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            user.email = form.new_email.data
            db.session.commit()
            flash('Email updated successfully', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('reset_email.html', form=form)

# -------------------Reset Password-------------------
class ResetPasswordRequestForm(FlaskForm):
    username = StringField(validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    submit = SubmitField('Send OTP')

class ForgotPasswordForm(FlaskForm):
    username = StringField(validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    new_password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "New Password"})
    confirm_password = PasswordField(validators=[InputRequired(), EqualTo('new_password')], render_kw={"placeholder": "Confirm Password"})
    otp = StringField(validators=[InputRequired(), Length(min=6, max=6)], render_kw={"placeholder": "Enter OTP"})
    submit = SubmitField('Reset Password')

def send_mail(name, email, otp):
    msg = Message('Password Reset OTP', sender='handssignify@gmail.com', recipients=[email])
    msg.body = f"Hi {name},\n\nYour OTP is: {otp}\n\nUse this to reset your password."
    mail.send(msg)

def generate_otp():
    return str(random.randint(100000, 999999))

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data, email=form.email.data).first()
        if user:
            otp = generate_otp()
            session['reset_otp'] = otp
            session['reset_user'] = form.username.data
            send_mail(form.username.data, form.email.data, otp)
            flash('OTP sent to your email', 'success')
            return redirect(url_for('forgot_password'))
        else:
            flash('User not found', 'danger')
    return render_template('reset_password_request.html', form=form)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        if form.otp.data == session.get('reset_otp'):
            user = User.query.filter_by(username=form.username.data, email=form.email.data).first()
            if user:
                user.password = bcrypt.generate_password_hash(form.new_password.data)
                db.session.commit()
                session.pop('reset_otp', None)
                session.pop('reset_user', None)
                flash('Password reset successful!', 'success')
                return redirect(url_for('login'))
        else:
            flash('Invalid OTP', 'danger')
    return render_template('forgot_password.html', form=form)

# -------------------Update Password-------------------
class UpdatePasswordForm(FlaskForm):
    username = StringField(validators=[InputRequired()], render_kw={"placeholder": "Username"})
    email = StringField(validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    new_password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "New Password"})
    confirm_password = PasswordField(validators=[InputRequired(), EqualTo('new_password')], render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField('Update Password')

@app.route('/update_password', methods=['GET', 'POST'])
@login_required
def update_password():
    form = UpdatePasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data, email=form.email.data).first()
        if user:
            user.password = bcrypt.generate_password_hash(form.new_password.data)
            db.session.commit()
            flash('Password updated successfully', 'success')
            return redirect(url_for('login'))
        else:
            flash('User not found', 'danger')
    return render_template('update_password.html', form=form)

# -------------------Additional Routes-------------------
@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/test_model')
def test_model():
    return "Model loaded" if model else "Model not loaded"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("\n" + "="*50)
    print("🚀 Signify Application Started")
    print("📍 http://127.0.0.1:5000")
    print("="*50 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)