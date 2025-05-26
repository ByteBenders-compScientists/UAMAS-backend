from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager

from config import Config
from api import db
from api.routes import bd_blueprint

import os
import re


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure the upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    with app.app_context():
        db.create_all()

    JWTManager(app)

    CORS(app,
         resources={r"/api/*": {"origins": "*"}},
         supports_credentials=True)

    # Register blueprints
    app.register_blueprint(bd_blueprint, url_prefix='/api/v1/bd')

    return app


if __name__ == '__main__':
    host = os.getenv('HOST')
    port = os.getenv('PORT')
    debug = os.getenv('DEBUG')

    app = create_app()
    app.run(host=host, port=int(port), debug=debug)
