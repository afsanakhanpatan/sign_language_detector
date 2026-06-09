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
    users = db.session.execute(db.select(User)).scalars().all()
    print(f'Total users: {len(users)}')
    for u in users:
        pwd = u.password
        print(f'\nUsername: {u.username}')
        print(f'Password stored as: {type(pwd)}')
        
        # Try to check password with a known test value
        try:
            # Try with string
            if isinstance(pwd, bytes):
                result = bcrypt.check_password_hash(pwd.decode('utf-8'), 'wrongpassword')
            else:
                result = bcrypt.check_password_hash(pwd, 'wrongpassword')
            print(f'Hash check works: True (result={result})')
        except Exception as e:
            print(f'Hash check ERROR: {e}')
            
    # Now delete all users and recreate with correct string storage
    print('\n--- FIXING: Clearing old bad data and resetting DB ---')
    for u in users:
        if isinstance(u.password, bytes):
            # Fix: re-store as proper string
            u.password = u.password.decode('utf-8')
    db.session.commit()
    print('All passwords fixed to string format!')
    
    # Verify
    users2 = db.session.execute(db.select(User)).scalars().all()
    for u in users2:
        print(f'  {u.username}: password now {type(u.password)}')
