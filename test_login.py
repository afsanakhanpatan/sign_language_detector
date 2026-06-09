"""Quick test: Register a test user and verify login works"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), nullable=False, unique=True)
    email = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(256), nullable=False)

with app.app_context():
    db.create_all()
    
    # 1. Check current users
    users = db.session.execute(db.select(User)).scalars().all()
    print(f"Current users in DB: {len(users)}")
    for u in users:
        print(f"  - {u.username} | password type: {type(u.password).__name__}")

    # 2. Create a test user exactly like the register route does
    test_username = "testuser123"
    test_password = "testpass123"
    
    existing = User.query.filter_by(username=test_username).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
    
    hashed = bcrypt.generate_password_hash(test_password).decode('utf-8')
    new_user = User(username=test_username, email="test@test.com", password=hashed)
    db.session.add(new_user)
    db.session.commit()
    print(f"\nRegistered test user: {test_username}")
    
    # 3. Try to login exactly like the login route does
    user = User.query.filter_by(username=test_username).first()
    if user:
        result = bcrypt.check_password_hash(user.password, test_password)
        print(f"Login check result: {result}")
        if result:
            print("SUCCESS: Login works correctly!")
        else:
            print("FAILED: Password check failed")
    else:
        print("FAILED: User not found")
    
    # 4. Clean up test user
    db.session.delete(user)
    db.session.commit()
    print(f"\nTest user removed. Ready for you to register!")
