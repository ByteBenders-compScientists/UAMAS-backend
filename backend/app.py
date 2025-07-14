from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager

from config import Config
from api import db
# from api.nvidia_routes import bd_blueprint
from api.routes import bd_blueprint
from api.lec_routes import lec_blueprint
from api.student_routes import student_blueprint

import os
import re


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize the database with the app
    db.init_app(app)

    # Ensure the upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    JWTManager(app)
    # allow CORS for all origins

    CORS(app,
         origins='https://intelli-mark-swart.vercel.app',
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         allow_headers=["Authorization", "Content-Type", "Accept"],
         supports_credentials=True,
         expose_headers=["Content-Type", "Authorization"]
    )

    # Health check route
    @app.route('/api/v1/bd/health', methods=['GET'])
    def health_check():
        return {"status": "ok"}, 200

    # Register blueprints
    app.register_blueprint(bd_blueprint, url_prefix='/api/v1/bd')
    app.register_blueprint(lec_blueprint, url_prefix='/api/v1/bd/lecturer')
    app.register_blueprint(student_blueprint, url_prefix='/api/v1/bd/student')

    return app

app = create_app()

if __name__ == '__main__':
    host = os.getenv('HOST')
    port = os.getenv('PORT')
    debug = os.getenv('DEBUG')

    app.run(host=host, port=int(port), debug=debug)
