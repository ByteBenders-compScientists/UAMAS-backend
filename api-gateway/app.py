import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_talisman import Talisman

from api.routes import register_routes

# load environment variables immediately
load_dotenv()

# create the Flask app at import time
app = Flask(__name__)

Talisman(
    app,
    content_security_policy=None,
    force_https=False,
    frame_options="DENY"
)

CORS(
    app,
    resources={
        r"/api/v1/*": {
            "origins": [os.getenv('ORIGINS_URL'),'http://localhost:3000'],
            "methods": ["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
            "allow_headers": ["Authorization","Content-Type"],
            "supports_credentials": True
        }
    },
    automatic_options=True
)

register_routes(app)

if __name__ == '__main__':
    # only used for local debugging
    app.run(
        host=os.getenv('HOST', '127.0.0.1'),
        port=int(os.getenv('PORT', 8080)),
        debug=os.getenv('DEBUG', 'false').lower() == 'true'
    )
