from flask_migrate import Migrate
from api import db
from app import create_app
from api.models import User
from api.utils import hashing_password

from dotenv import load_dotenv
import os

app = create_app()


with app.app_context():
    db.create_all()

migrate = Migrate(app, db)

if __name__ == "__main__":
    app.run(port=8000, debug=True)
