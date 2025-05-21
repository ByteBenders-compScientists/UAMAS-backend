# class Config
import os

from dotenv import load_dotenv

class Config():
    load_dotenv()
    SQLALCHEMY_DATABASE_URI=os.getenv('DB_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS=os.getenv('TRACK_MODIFICATIONS')
    JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY')
    SECRET_KEY=os.getenv('SECRET_KEY')
