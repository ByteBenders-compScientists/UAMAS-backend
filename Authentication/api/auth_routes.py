from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token
)
from .models import db, User
from .utils import hashing_password, compare_password, gen_password, send_password_reset_email

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

    # access = create_access_token(identity={'id': user.id, 'role': user.role}) # bug
    # access = create_access_token(identity=user.id) # 1st solution
    access = create_access_token(
        identity=user.id,
        additional_claims={"role": user.role}
    )
    return jsonify({'access_token': access, 'role': user.role}), 200

@auth_blueprint.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    email = data.get('email')
    new_password = data.get('new_password')
    if not email or not new_password:
        return jsonify({'error': 'Email and new password required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if len(new_password) < 8:
        return jsonify({'error': 'New password must be at least 8 characters long'}), 400
    if not any(char.isdigit() for char in new_password):
        return jsonify({'error': 'New password must contain at least one digit'}), 400
    if not any(char.isalpha() for char in new_password):
        return jsonify({'error': 'New password must contain at least one letter'}), 400
    if not any(char in '!@#$%^&*()-_=+[]{}|;:,.<>?/' for char in new_password):
        return jsonify({'error': 'New password must contain at least one special character'}), 400
    
    # Hash the new password
    user.password = hashing_password(new_password)
    db.session.commit()

    result = send_password_reset_email(
        to_email=user.email,
        reciever_fname=user.firstname,
        reciever_lname=user.surname
    )

    if not result:
        return jsonify({'error': 'Failed to send email. Please try again later.'}), 500

    return jsonify({'message': 'Password reset successfully. Check your email for the new password.'}), 200
