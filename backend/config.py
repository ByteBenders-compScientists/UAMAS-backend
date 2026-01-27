import os
from datetime import timedelta
from dotenv import load_dotenv

class Config():
    load_dotenv()
    SQLALCHEMY_DATABASE_URI=os.getenv('DB_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS=os.getenv('TRACK_MODIFICATIONS')
    JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY')
    SECRET_KEY=os.getenv('SECRET_KEY')
    
    # JWT Cookie Settings
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_ACCESS_COOKIE_PATH = "/"
    JWT_REFRESH_COOKIE_PATH = "/"
    # Only require secure cookies in production (HTTPS). Set to False for HTTP or mixed environments.
    JWT_COOKIE_SECURE = os.getenv('JWT_COOKIE_SECURE', 'True').lower() == 'true'
    JWT_COOKIE_SAMESITE = os.getenv('JWT_COOKIE_SAMESITE', 'None')
    JWT_COOKIE_CSRF_PROTECT = False
    
    UPLOAD_FOLDER=os.getenv('UPLOAD_FOLDER')
    MAX_CONTENT_LENGTH=int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # Default to 16MB
    ALLOWED_EXTENSIONS=os.getenv('ALLOWED_EXTENSIONS', 'png,jpg,jpeg').split(',')
