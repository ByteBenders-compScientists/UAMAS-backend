from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

import os
from api.routes import auth_blueprint

if __name__ == '__main__':
    load_dotenv()

    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(auth_blueprint, url_prefix='/api/v1/auth')

    app.run(host=os.getenv('HOST'), port=os.getenv('PORT'), debug=os.getenv('DEBUG'))
