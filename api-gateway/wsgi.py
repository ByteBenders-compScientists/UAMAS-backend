from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_talisman import Talisman
from api.routes import register_routes
import os

# Load env before anything
load_dotenv()

app = Flask(__name__)

Talisman(
    app,
    content_security_policy=None,
    force_https=False,
    frame_options="DENY"
)

CORS(
    app,
    resources={r"/api/v1/*": {"origins": [os.getenv('ORIGINS_URL')]}}
)

register_routes(app)
