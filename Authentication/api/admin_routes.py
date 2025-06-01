from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required, get_jwt_identity, get_jwt
)
from .models import db, User, Student, Lecturer, Unit, Course
from .utils import hashing_password, gen_password, send_email

admin_blueprint = Blueprint('admin', __name__)

# Only admin can call these
@admin_blueprint.before_request
@jwt_required()
def check_admin():
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims["role"] != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403


# --- CRUD: Students ---
@admin_blueprint.route('/students', methods=['POST'])
def create_student():
    data = request.get_json() or {}
    # Validate required fields
    required_fields = ['email', 'reg_number', 'year_of_study', 'firstname', 'surname', 'course_id']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    existing_student = Student.query.filter_by(reg_number=data['reg_number']).first()
    if existing_student:
        return jsonify({'error': 'Student with this registration number already exists'}), 400
    
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'error': 'User with this email already exists'}), 400
    
    course = Course.query.get(data['course_id'])
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # create user
    reg = data['reg_number']
    user = User(
        email=data['email'],
        password=hashing_password(reg),
        role='student'
    )
    db.session.add(user)
    db.session.flush()

    # assign student to course
    student = Student(
        user_id=user.id,
        reg_number=reg,
        year_of_study=data['year_of_study'],
        firstname=data['firstname'],
        surname=data['surname'],
        othernames=data.get('othernames'),
        course_id=data['course_id']
    )
    db.session.add(student)
    db.session.commit()
    return jsonify({'student': student.to_dict()}), 201

@admin_blueprint.route('/students', methods=['GET'])
def list_students():
    students = Student.query.all()
    return jsonify([s.to_dict() for s in students]), 200

@admin_blueprint.route('/students/<id>', methods=['GET'])
def get_student(id):
    s = Student.query.get_or_404(id)
    return jsonify(s.to_dict()), 200

@admin_blueprint.route('/students/<id>', methods=['PUT'])
def update_student(id):
    s = Student.query.get_or_404(id)
    data = request.get_json() or {}
    # allow updating of profile and year of study or course
    for field in ['firstname', 'surname', 'othernames', 'year_of_study', 'course_id']:
        if field in data:
            setattr(s, field, data[field])
    db.session.commit()
    return jsonify(s.to_dict()), 200

@admin_blueprint.route('/students/<id>', methods=['DELETE'])
def delete_student(id):
    s = Student.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200

# --- CRUD: Lecturers ---
@admin_blueprint.route('/lecturers', methods=['POST'])
def create_lecturer():
    data = request.get_json() or {}

    # Validate required fields
    required_fields = ['email', 'firstname', 'surname']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    temp_pass = gen_password()
    user = User(
        email=data['email'],
        password=hashing_password(temp_pass),
        role='lecturer'
    )
    result = send_email(
        to_email=data['email'],
        reciever_fname=data['firstname'],
        reciever_lname=data['surname'],
        temp_password=temp_pass
    )
    
    if not result:
        return jsonify({'error': 'Failed to send email notification'}), 500

    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'error': 'User with this email already exists'}), 400
    
    db.session.add(user)
    db.session.flush()

    lec = Lecturer(
        user_id=user.id,
        firstname=data['firstname'],
        surname=data['surname'],
        othernames=data.get('othernames')
    )
    db.session.add(lec)
    db.session.commit()
    return jsonify({'lecturer': lec.to_dict(), 'temp_password': temp_pass}), 201

@admin_blueprint.route('/lecturers', methods=['GET'])
def list_lecturers():
    return jsonify([l.to_dict() for l in Lecturer.query.all()]), 200

@admin_blueprint.route('/lecturers/<id>', methods=['PUT'])
def update_lecturer(id):
    l = Lecturer.query.get_or_404(id)
    data = request.get_json() or {}
    for f in ['firstname', 'surname', 'othernames']:
        if f in data:
            setattr(l, f, data[f])
    db.session.commit()
    return jsonify(l.to_dict()), 200

@admin_blueprint.route('/lecturers/<id>', methods=['DELETE'])
def delete_lecturer(id):
    l = Lecturer.query.get_or_404(id)
    db.session.delete(l)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200

# Assign units to lecturer
@admin_blueprint.route('/lecturers/<id>/units', methods=['POST'])
def assign_units(id):
    data = request.get_json() or {}

    # Validate required field
    if 'unit_ids' not in data:
        return jsonify({'error': 'Missing required field: unit_ids'}), 400

    # Validate unit_ids
    if not isinstance(data['unit_ids'], list):
        return jsonify({'error': 'unit_ids must be a list'}), 400
    if not all(isinstance(uid, str) for uid in data['unit_ids']):
        return jsonify({'error': 'unit_ids must contain string IDs'}), 400

    lec = Lecturer.query.get_or_404(id)
    unit_ids = data.get('unit_ids', [])
    units = Unit.query.filter(Unit.id.in_(unit_ids)).all()
    lec.units = units
    db.session.commit()
    return jsonify({'units': [u.to_dict() for u in lec.units]}), 200

# --- CRUD: Courses ---
@admin_blueprint.route('/courses', methods=['POST'])
def create_course():
    data = request.get_json() or {}

    # Validate required fields
    required_fields = ['code', 'name', 'department', 'school']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    existing_course = Course.query.filter_by(code=data['code']).first()
    if existing_course:
        return jsonify({'error': 'Course with this code already exists'}), 400

    # Create the course
    c = Course(**{k: data[k] for k in ['code', 'name', 'department', 'school']})
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201

@admin_blueprint.route('/courses', methods=['GET'])
def list_courses():
    return jsonify([c.to_dict() for c in Course.query.all()]), 200

@admin_blueprint.route('/courses/<id>', methods=['PUT'])
def update_course(id):
    c = Course.query.get_or_404(id)
    data = request.get_json() or {}
    for f in ['code', 'name', 'department', 'school']:
        if f in data:
            setattr(c, f, data[f])
    db.session.commit()
    return jsonify(c.to_dict()), 200

@admin_blueprint.route('/courses/<id>', methods=['DELETE'])
def delete_course(id):
    c = Course.query.get_or_404(id)
    db.session.delete(c)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200

# --- CRUD: Units ---
@admin_blueprint.route('/units', methods=['POST'])
def create_unit():
    data = request.get_json() or {}

    # Validate required fields
    required_fields = ['unit_code', 'unit_name', 'level', 'semester']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    if 'course_id' in data:
        course = Course.query.get(data['course_id'])
        if not course:
            return jsonify({'error': 'Course not found'}), 404

    existing_unit = Unit.query.filter_by(unit_code=data['unit_code']).first()
    if existing_unit:
        return jsonify({'error': 'Unit with this code already exists'}), 400

    # Create the unit
    u = Unit(
        unit_code=data['unit_code'],
        unit_name=data['unit_name'],
        level=data['level'],
        semester=data['semester'],
        course_id=data.get('course_id')
    )
    db.session.add(u)
    db.session.commit()
    return jsonify(u.to_dict()), 201

@admin_blueprint.route('/units', methods=['GET'])
def list_units():
    return jsonify([u.to_dict() for u in Unit.query.all()]), 200

@admin_blueprint.route('/units/<id>', methods=['PUT'])
def update_unit(id):
    u = Unit.query.get_or_404(id)
    data = request.get_json() or {}
    for f in ['unit_code', 'unit_name', 'level', 'course_id']:
        if f in data:
            setattr(u, f, data[f])
    db.session.commit()
    return jsonify(u.to_dict()), 200

@admin_blueprint.route('/units/<id>', methods=['DELETE'])
def delete_unit(id):
    u = Unit.query.get_or_404(id)
    db.session.delete(u)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200
