from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token
)
from .models import db, User, Student, Lecturer, Unit, Course
from .utils import hashing_password, compare_password, gen_password

auth_blueprint = Blueprint('auth', __name__)


@auth_blueprint.route('/health', methods=['GET'])
def check_auth_routes_health():
    return jsonify({'message': 'Auth routes online'}), 200

@auth_blueprint.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not compare_password(user.password, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    access = create_access_token(identity={'id': user.id, 'role': user.role})
    return jsonify({'access_token': access, 'role': user.role}), 200
