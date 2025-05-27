from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from .utils import is_token_revoked

db = SQLAlchemy()

jwt = JWTManager()
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    """
    Check if the token is revoked by its jti (JWT ID).
    """
    jti = jwt_payload['jti']
    return is_token_revoked(jti)
