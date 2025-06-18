from flask import Flask
from flask_cors import CORS
from flask_talisman import Talisman

from api.routes import register_routes

import os
from dotenv import load_dotenv


if __name__ == '__main__':
    load_dotenv()

    app = Flask(__name__)

    Talisman( # xss config
        app,
        content_security_policy=None,
        force_https=False,
        frame_options="DENY"
    )

    CORS( # CORS config
        app,
        resources={
            r"/api/v1/*": {
                "origins": [os.getenv('ORIGINS_URL'),'http://localhost:3000'],
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Authorization", "Content-Type"],
                "supports_credentials": True
            }
        },
        automatic_options=False
    )

    register_routes(app)

    app.run(host=os.getenv('HOST'), port=os.getenv('PORT'), debug=os.getenv('DEBUG'))
