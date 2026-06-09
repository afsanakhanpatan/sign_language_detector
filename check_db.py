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
    print(f'Total users in DB: {len(users)}')
    for u in users:
        print(f'  Username: {u.username}')
        print(f'  Email: {u.email}')
        print(f'  Password type: {type(u.password)}')
        print(f'  Password value: {repr(u.password[:30])}')
        print()
