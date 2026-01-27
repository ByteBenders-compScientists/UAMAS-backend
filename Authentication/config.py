import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DB_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('TRACK_MODIFICATIONS', 'False').lower() == 'true'

    # Secrets
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    SECRET_KEY = os.getenv('SECRET_KEY')

    # JWT Settings
    JWT_ACCESS_TOKEN_EXPIRES    = timedelta(days=7)
    JWT_REFRESH_TOKEN_EXPIRES   = timedelta(minutes=15)
    JWT_TOKEN_LOCATION          = ['cookies']
    JWT_ACCESS_COOKIE_PATH      = "/"
    JWT_REFRESH_COOKIE_PATH     = "/"

    # Correct cookie cross-site settings
    JWT_COOKIE_SECURE           = True           # required for HTTPS
    JWT_COOKIE_SAMESITE         = "None"         # must be string "None" for cross-site cookies
    JWT_COOKIE_HTTPONLY         = True
    JWT_COOKIE_CSRF_PROTECT     = False          # optional

    JWT_BLACKLIST_ENABLED       = True
    JWT_BLACKLIST_TOKEN_CHECKS  = ['access', 'refresh']

    # Mail Settings
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1", "t")
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False").lower() in ("true", "1", "t")
    MAIL_DEBUG = os.getenv("MAIL_DEBUG", "False").lower() in ("true", "1", "t")
