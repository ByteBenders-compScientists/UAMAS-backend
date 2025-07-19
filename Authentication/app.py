import os
from dotenv import load_dotenv

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from api import db
from api.models import User, Student, Lecturer, Unit, Course
from api.auth_routes import auth_blueprint
from api.admin_routes import admin_blueprint
from api.lec_routes import lec_blueprint
from api.utils import hashing_password
from config import Config
from api import jwt

def create_app():
    load_dotenv()

    app = Flask(__name__)
    CORS(app,
         origins=['https://intelli-mark-swart.vercel.app', 'http://localhost:3000'],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         allow_headers=["Authorization", "Content-Type", "Accept"],
         supports_credentials=True,
         expose_headers=["Content-Type", "Authorization"]
    )
    app.config.from_object(Config)
    jwt.init_app(app)
    db.init_app(app)

    # /healthcheck endpoint
    @app.route('/api/v1/auth/health', methods=['GET'])
    def health_check():
        """Health check endpoint to verify if the API is running."""
        return jsonify({"status": "ok", "message": "API is running"}), 200

    # Register Blueprints with prefixes
    app.register_blueprint(auth_blueprint, url_prefix='/api/v1/auth')
    app.register_blueprint(admin_blueprint, url_prefix='/api/v1/admin')
    app.register_blueprint(lec_blueprint, url_prefix='/api/v1/auth/lecturer')

    return app

app = create_app()

if __name__ == "__main__":
    host = os.getenv('HOST')
    port = int(os.getenv('PORT'))
    debug = os.getenv('DEBUG')

    app.run(host=host, port=port, debug=debug)
