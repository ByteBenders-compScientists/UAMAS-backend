from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
    set_access_cookies, set_refresh_cookies, unset_jwt_cookies,
    JWTManager
)

from datetime import datetime, timedelta, timezone

from .models import db, User, Student, Lecturer, Unit, Course, EmailVerification
from .utils import (
    hashing_password, compare_password, is_valid_institution_email,
    send_account_creation_email, send_password_reset_email, add_revoked_token,
    generate_numeric_code, send_verification_email
)
from sqlalchemy.orm import joinedload

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/register/request-code', methods=['POST'])
def request_verification_code():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    role = data.get('role')

    if not email or role not in ['student', 'lecturer']:
        return jsonify({'error': 'Email and role (student or lecturer) are required'}), 400

    if not is_valid_institution_email(email):
        return jsonify({'error': 'Email must be a valid institutional email address'}), 400

    # Prevent duplicate accounts
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'A user with this email already exists'}), 400

    # Generate code and send email BEFORE database operations to avoid race conditions
    code = generate_numeric_code(6)
    
    try:
        if not send_verification_email(email, code):
            return jsonify({'error': 'Failed to send verification email. Please try again later.'}), 500
    except Exception as e:
        print(f"Unexpected error sending verification email: {e}")
        return jsonify({'error': 'Failed to send verification email. Please try again later.'}), 500

    # Only create/update verification entry AFTER email is successfully sent
    # This prevents storing codes for emails that never received the message
    try:
        EmailVerification.query.filter_by(email=email, role=role).delete()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        verification = EmailVerification(
            email=email,
            role=role,
            code=code,
            data={},
            expires_at=expires_at
        )
        db.session.add(verification)
        db.session.commit()
    except Exception as e:
        print(f"Database error while saving verification code: {e}")
        return jsonify({'error': 'An error occurred. Please try again later.'}), 500

    return jsonify({'message': 'Verification code sent successfully.'}), 200

@auth_blueprint.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')
    role = data.get('role')
    verification_code = (data.get('verification_code') or '').strip()

    if not email or not password or role not in ['student', 'lecturer'] or not verification_code:
        return jsonify({'error': 'Email, password, role (student or lecturer), and verification_code are required'}), 400

    if not is_valid_institution_email(email):
        return jsonify({'error': 'Email must be a valid institutional email address'}), 400

    # Ensure email is not already registered
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'A user with this email already exists'}), 400

    # Validate verification code
    verification = (
        EmailVerification.query
            .filter_by(email=email, role=role)
            .order_by(EmailVerification.created_at.desc())
            .first()
    )
    if not verification or verification.code != verification_code:
        return jsonify({'error': 'Invalid verification code'}), 400

    now = datetime.now(timezone.utc)
    # Ensure verification.expires_at is timezone-aware for comparison
    expires_at_aware = verification.expires_at.replace(tzinfo=timezone.utc) if verification.expires_at.tzinfo is None else verification.expires_at
    if expires_at_aware < now:
        return jsonify({'error': 'Verification code has expired'}), 400

    reciever_fname = None
    reciever_lname = None

    if role == 'student':
        reg_number = data.get('reg_number')
        firstname = data.get('firstname')
        surname = data.get('surname')
        othernames = data.get('othernames')
        unit_join_code = (data.get('unit_join_code') or '').strip() if data.get('unit_join_code') else None

        if not reg_number or not firstname or not surname:
            return jsonify({'error': 'reg_number, firstname, and surname are required for student registration'}), 400

        # Ensure reg_number is unique
        if Student.query.filter_by(reg_number=reg_number).first():
            return jsonify({'error': 'A student with this registration number already exists'}), 400

        unit = None
        if unit_join_code:
            unit = Unit.query.filter_by(unique_join_code=unit_join_code).first()
            if not unit:
                return jsonify({'error': 'Invalid unit join code'}), 400

        user = User(
            email=email,
            password=hashing_password(password),
            role='student'
        )
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id,
            reg_number=reg_number,
            firstname=firstname,
            surname=surname,
            othernames=othernames
        )
        if unit is not None and unit not in student.units:
            student.units.append(unit)
        db.session.add(student)

        reciever_fname = firstname
        reciever_lname = surname

    elif role == 'lecturer':
        firstname = data.get('firstname')
        surname = data.get('surname')
        othernames = data.get('othernames')

        if not firstname or not surname:
            return jsonify({'error': 'firstname and surname are required for lecturer registration'}), 400

        user = User(
            email=email,
            password=hashing_password(password),
            role='lecturer'
        )
        db.session.add(user)
        db.session.flush()

        lecturer = Lecturer(
            user_id=user.id,
            firstname=firstname,
            surname=surname,
            othernames=othernames
        )
        db.session.add(lecturer)

        reciever_fname = firstname
        reciever_lname = surname

    else:
        return jsonify({'error': 'Unsupported role'}), 400

    # Invalidate used verification codes
    EmailVerification.query.filter_by(email=email, role=role).delete()
    db.session.commit()

    if reciever_fname and reciever_lname:
        # Best-effort notification; do not fail registration if email sending fails
        try:
            send_account_creation_email(
                to_email=email,
                reciever_fname=reciever_fname,
                reciever_lname=reciever_lname
            )
        except Exception:
            pass

    return jsonify({'message': 'Account created successfully. You can now log in.'}), 201

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
                   .options(joinedload(Student.units).joinedload(Unit.course))
                   .filter_by(user_id=user.id)
                   .first()
        )
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        # build a simple list of distinct course dicts based on the student's units
        courses_by_id = {}
        for u in student.units:
            if u.course and u.course.id not in courses_by_id:
                courses_by_id[u.course.id] = {'id': u.course.id, 'name': u.course.name}
        course_list = list(courses_by_id.values())

        return jsonify({
            'id'           : user.id,
            'email'        : user.email,
            'role'         : claims.get('role'),
            'reg_number'   : student.reg_number,
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

@auth_blueprint.route('/join-unit', methods=['POST'])
@jwt_required()
def join_unit_by_code():
    claims = get_jwt()
    if claims.get('role') != 'student':
        return jsonify({'error': 'Only students can join units using a join code'}), 403

    user_id = get_jwt_identity()
    data = request.get_json() or {}
    join_code = (data.get('join_code') or '').strip()

    if not join_code:
        return jsonify({'error': 'join_code is required'}), 400

    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'error': 'Student profile not found'}), 404

    unit = Unit.query.filter_by(unique_join_code=join_code).first()
    if not unit:
        return jsonify({'error': 'Invalid or unknown unit join code'}), 404

    if unit in student.units:
        return jsonify({'error': 'Student is already registered for this unit'}), 400

    student.units.append(unit)
    db.session.commit()

    return jsonify({
        'message': 'Successfully joined unit',
        'unit': unit.to_dict()
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

@auth_blueprint.route('/student/hobbies', methods=['PUT'])
@jwt_required()
def update_student_hobbies():
    """Update hobbies for the authenticated student."""
    user_id = get_jwt_identity()
    claims = get_jwt()

    # Verify user is a student
    if claims.get('role') != 'student':
        return jsonify({'error': 'Only students can update hobbies'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    student = Student.query.filter_by(user_id=user.id).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    # Get hobbies from request
    data = request.get_json() or {}
    hobbies = data.get('hobbies')

    if hobbies is None:
        return jsonify({'error': 'hobbies field is required'}), 400

    # Validate hobbies is a list
    if not isinstance(hobbies, list):
        return jsonify({'error': 'hobbies must be a list'}), 400

    # Update student's hobbies
    student.hobbies = hobbies
    db.session.commit()

    return jsonify({
        'message': 'Hobbies updated successfully',
        'hobbies': student.hobbies
    }), 200
  