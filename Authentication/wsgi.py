# wsgi.py
import os
from dotenv import load_dotenv

from flask import Flask
from flask_cors import CORS

from api import db, jwt
from api.models import User
from api.auth_routes import auth_blueprint
from api.admin_routes import admin_blueprint
from api.utils import hashing_password
from config import Config

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
CORS(
    app,
    origins=os.getenv('CORS_ORIGINS', 'http://localhost:3000'),
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    supports_credentials=True,
    expose_headers=["Content-Type", "Authorization"]
)

# App configuration
app.config.from_object(Config)

# Initialize extensions
jwt.init_app(app)
db.init_app(app)

# Register blueprints
app.register_blueprint(auth_blueprint, url_prefix='/api/v1/auth')
app.register_blueprint(admin_blueprint, url_prefix='/api/v1/admin')

# Setup database and default admin user
with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='admin').first():
        password = os.getenv("SUPER_ADMIN_PASSWORD")
        super_admin = User(
            email=os.getenv("SUPER_ADMIN_MAIL"),
            password=hashing_password(password),
            role="admin"
        )
        db.session.add(super_admin)
        db.session.commit()
