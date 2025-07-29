from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
    set_access_cookies, set_refresh_cookies, unset_jwt_cookies,
    JWTManager
)

from .models import db, User, Student, Lecturer, Unit, Course
from .utils import (
    hashing_password, compare_password, gen_password,
    send_password_reset_email, add_revoked_token
)
from sqlalchemy.orm import joinedload

auth_blueprint = Blueprint('auth', __name__)

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

    access_token = create_access_token(
        identity=user.id,
        additional_claims={"role": user.role}
    )
    refresh_token = create_refresh_token(identity=user.id)

    response = jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'role': user.role
    })
    # set cookies if you're using cookie-based auth:
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)

    return response, 200


@auth_blueprint.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    claims  = get_jwt()
    user    = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if claims.get('role') == 'student':
        student = (
            Student.query
                   .options(joinedload(Student.courses))
                   .filter_by(user_id=user.id)
                   .first()
        )
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        # build a simple list of course dicts
        course_list = [
            {'id': c.id, 'name': c.name}
            for c in student.courses
        ]

        return jsonify({
            'id'           : user.id,
            'email'        : user.email,
            'role'         : claims.get('role'),
            'reg_number'   : student.reg_number,
            'year_of_study': student.year_of_study,
            'semester'     : student.semester,
            'name'         : student.firstname,
            'surname'      : student.surname,
            'othernames'   : student.othernames,
            'courses'      : course_list,
            # units property on Student already filters by year/sem
            'units'        : [u.to_dict() for u in student.units]
        }), 200

    elif claims.get('role') == 'lecturer':
        lecturer = Lecturer.query.filter_by(user_id=user.id).first()
        if not lecturer:
            return jsonify({'error': 'Lecturer not found'}), 404

        courses = Course.query.filter_by(created_by=user.id).all()
        return jsonify({
            'id'         : user.id,
            'email'      : user.email,
            'role'       : claims.get('role'),
            'name'       : lecturer.firstname,
            'surname'    : lecturer.surname,
            'othernames' : lecturer.othernames,
            'courses'    : [c.to_dict() for c in courses]
        }), 200

    return jsonify({
        'id'    : user.id,
        'email' : user.email,
        'role'  : claims.get('role')
    }), 200

@auth_blueprint.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    new_access_token = create_access_token(
        identity=identity,
        additional_claims={"role": user.role}
    )
    response = jsonify({'access_token': new_access_token})
    set_access_cookies(response, new_access_token)
    return response, 200


@auth_blueprint.route('/logout', methods=['GET'])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    add_revoked_token(jti)

    response = jsonify({'message': 'Successfully logged out'})
    unset_jwt_cookies(response)
    return response, 200


@auth_blueprint.route('/reset-password', methods=['POST'])
@jwt_required()
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

    # Hash and save the new password
    user.password = hashing_password(new_password)
    db.session.commit()

    # send confirmation email to the students and lecturers only
    if user.role in ['student', 'lecturer']:
        if user.role == 'student':
            user_details = Student.query.filter_by(user_id=user.id).first()
        else:
            user_details = Lecturer.query.filter_by(user_id=user.id).first()

        if not user_details:
            return jsonify({'error': 'User details not found'}), 404

        # Send password reset confirmation email

        sent = send_password_reset_email(
            to_email=user.email,
            reciever_fname=user_details.firstname,
            reciever_lname=user_details.surname
        )
        if not sent:
            return jsonify({'error': 'Failed to send email. Please try again later.'}), 500

    return jsonify({'message': 'Password reset successfully. Check your email.'}), 200
  