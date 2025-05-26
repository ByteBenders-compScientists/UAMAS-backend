from flask import Blueprint, request, jsonify
from flask_jwt_extended import  create_access_token , create_refresh_token, jwt_required, get_jwt_identity, get_jwt

from .models import db, User, Student, Lecturer, Unit, Course
from .utils import hashing_password, compare_password, gen_password, add_revoked_token

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

    refresh = create_refresh_token(identity=user.id)
    return jsonify({
        'access_token': access,
        'refresh_token': refresh,
        'role': user.role}), 200


@auth_blueprint.route("/refresh", methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    new_access_token = create_access_token(
        identity=identity,                                 
        additional_claims= {"role": user.role}
        )
    return jsonify({
        'access_token': new_access_token
    }),200

@auth_blueprint.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    add_revoked_token(jti)
    return jsonify({'message': 'Successfully logged out'}), 200