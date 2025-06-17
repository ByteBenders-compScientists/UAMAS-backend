from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager

from config import Config
from api import db
# from api.nvidia_routes import bd_blueprint
from api.routes import bd_blueprint

import os
import re


load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
with app.app_context():
    from api.models import Assessment, Question, Submission, Answer, Result, TotalMarks, User, Course, Unit
    db.create_all()

JWTManager(app)

CORS(app,
        origins=os.getenv('CORS_ORIGINS', 'http://localhost:3000'),
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        supports_credentials=True,
        expose_headers=["Content-Type", "Authorization"]
)

# Register blueprints
app.register_blueprint(bd_blueprint, url_prefix='/api/v1/bd')
