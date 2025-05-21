from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

import os
from dotenv import load_dotenv

from api import db
from config import Config
from api.routes import auth_blueprint

if __name__ == '__main__':
    load_dotenv()

    app = Flask(__name__)
    CORS(app)

    app.config.from_object(Config)
    JWTManager(app)

    db.init_app()

    with app.app_context():
        # from api.models import User, Lecturer, Student
        from api.models import User # import Lecturer & Student after creating their classes

        db.create_all()

    app.register_blueprint(auth_blueprint, url_prefix='/api/v1/auth')

    app.run(host=os.getenv('HOST'), port=os.getenv('PORT'), debug=os.getenv('DEBUG'))
