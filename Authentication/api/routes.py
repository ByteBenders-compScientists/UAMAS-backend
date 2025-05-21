# routes using Blueprint
from flask import Blueprint, request, jsonify

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/health', methods=['GET'])
def check_auth_routes_health():
    return jsonify({
        'message': 'Reached the auth routes successfully'
    }), 200
