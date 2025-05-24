import os
from dotenv import load_dotenv

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

from api import db
from api.models import User, Student, Lecturer, Unit, Course
from api.auth_routes import auth_blueprint
from api.admin_routes import admin_blueprint
from api.utils import hashing_password
from config import Config

def create_app():
    load_dotenv()

    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)
    JWTManager(app)
    db.init_app(app)

    # Register Blueprints with prefixes
    app.register_blueprint(auth_blueprint, url_prefix='/api/v1/auth')
    app.register_blueprint(admin_blueprint, url_prefix='/api/v1/admin')

    with app.app_context():
        db.create_all()

        # If no admin exists, create one now
        if not User.query.filter_by(role='admin').first():
            super_admin = User(
                email="admin@gmail.com",
                password=hashing_password("super-admin"),
                role="admin"
            )
            db.session.add(super_admin)
            db.session.commit()
            app.logger.info("✅ Created default super-admin: admin@gmail.com / super-admin")

    return app

if __name__ == "__main__":
    host = os.getenv('HOST')
    port = int(os.getenv('PORT'))
    debug = os.getenv('DEBUG')

    app = create_app()

    app.run(host=host, port=port, debug=debug)
