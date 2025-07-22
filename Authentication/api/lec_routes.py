"""
Blueprint for lecture-related API routes.
Created by: https://github.com/ByteBenders-compScientists/UAMAS-backend
Actions: 
- Add a new course
- Add units to a course
- Add students to a course
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from .models import db, User, Student, Lecturer, Unit, Course, student_courses
from .utils import hashing_password
import pandas as pd
import os
from sqlalchemy.orm import joinedload

# Create a blueprint for lecture routes
lec_blueprint = Blueprint('lectures', __name__)

'''
Only lecturers can call these routes
'''
@lec_blueprint.before_request
@jwt_required()
def check_lecturer():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role != 'lecturer':
        return jsonify({'error': 'Lecturer privileges required'}), 403
    claims = get_jwt()
    if claims["role"] != 'lecturer':
        return jsonify({'error': 'Lecturer privileges required'}), 403

# --- CRUD: Courses ---
@lec_blueprint.route('/courses', methods=['POST'])
def create_course():
    '''
    Create a new course.
    Requires: name, code, department, school
    Returns: JSON response with success message or error
    '''
    data = request.get_json() or {}
    # Validate required fields
    required_fields = ['name', 'code', 'department', 'school']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # check existing course code if had been created by the user
    user_id = get_jwt_identity()
    existing_course = Course.query.filter_by(code=data['code'], created_by=user_id).first()
    if existing_course:
        return jsonify({'error': 'Course with this code already exists'}), 400
    # Create course
    course = Course(
        name=data['name'],
        code=data['code'],
        department=data['department'],
        school=data['school'],
        created_by=user_id
    )
    db.session.add(course)
    db.session.commit()
    return jsonify({'message': 'Course created successfully', 'course_id': course.id}), 201

@lec_blueprint.route('/courses', methods=['GET'])
def get_courses():
    '''
    Get all courses created by the lecturer.
    Returns: JSON response with list of courses
    '''
    user_id = get_jwt_identity()
    courses = Course.query.filter_by(created_by=user_id).all()
    return jsonify([course.to_dict() for course in courses]), 200

@lec_blueprint.route('/courses/<string:course_id>', methods=['GET'])
def get_course(course_id):
    '''
    Get a specific course by ID.
    Returns: JSON response with course details or error if not found
    '''
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    return jsonify(course.to_dict()), 200

@lec_blueprint.route('/courses/<string:course_id>', methods=['PUT'])
def update_course(course_id):
    '''
    Update a course.
    Requires: name, code, department, school
    Returns: JSON response with updated course details or error if not found
    '''
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    data = request.get_json() or {}
    for field in ['name', 'code', 'department', 'school']:
        if field in data:
            setattr(course, field, data[field])
    
    db.session.commit()
    return jsonify(course.to_dict()), 200

@lec_blueprint.route('/courses/<string:course_id>', methods=['DELETE'])
def delete_course(course_id):
    '''
    Delete a course.
    Returns: JSON response with success message or error if not found
    '''
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    db.session.delete(course)
    db.session.commit()
    return jsonify({'message': 'Course deleted successfully'}), 200

# --- CRUD: Units ---
@lec_blueprint.route('/units', methods=['POST'])
def create_unit():
    '''
    Create a new unit.
    Requires: unit_code, unit_name, level, semester, course_id
    Returns: JSON response with success message or error
    '''
    data = request.get_json() or {}
    
    # Validate required fields
    required_fields = ['unit_code', 'unit_name', 'level', 'semester', 'course_id']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    course = Course.query.get(data['course_id'])
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Check if unit already exists
    existing_unit = Unit.query.filter_by(unit_code=data['unit_code'], course_id=course.id).first()
    if existing_unit:
        return jsonify({'error': 'Unit with this code already exists in the course'}), 400
    
    # Create unit
    unit = Unit(
        unit_code=data['unit_code'],
        unit_name=data['unit_name'],
        level=data['level'],
        semester=data['semester'],
        course=course
    )
    db.session.add(unit)
    db.session.commit()
    return jsonify({'message': 'Unit created successfully', 'unit_id': unit.id}), 201

@lec_blueprint.route('/units', methods=['GET'])
def get_units():
    '''
    Get all units created by the lecturer.
    Returns: JSON response with list of units
    '''
    user_id = get_jwt_identity()
    # get all courses created by the lecturer
    courses = Course.query.filter_by(created_by=user_id).all()
    if not courses:
        # return jsonify({'error': 'No courses found for this lecturer'}), 404 -> bug: not handled in the frontend
        return [], 200 # no courses registered yet
    # get all units for those courses (using course IDs)
    course_ids = [course.id for course in courses]
    units = Unit.query.filter(Unit.course_id.in_(course_ids)).all()
    # if not units: -> bug for 404 in frontend not handled
    #     return jsonify({'error': 'No units found for the lecturer\'s courses'}), 404
    # Return units as a list of dictionaries
    return jsonify([unit.to_dict() for unit in units]), 200

@lec_blueprint.route('/units/<string:unit_id>', methods=['GET'])
def get_unit(unit_id):
    '''
    Get a specific unit by ID.
    Returns: JSON response with unit details or error if not found
    '''
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    return jsonify(unit.to_dict()), 200

@lec_blueprint.route('/units/<string:unit_id>', methods=['PUT'])
def update_unit(unit_id):
    '''
    Update a unit.
    Requires: unit_code, unit_name, level, semester, course_id
    Returns: JSON response with updated unit details or error if not found
    '''
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    
    data = request.get_json() or {}
    for field in ['unit_code', 'unit_name', 'level', 'semester', 'course_id']:
        if field in data:
            setattr(unit, field, data[field])
    
    db.session.commit()
    return jsonify(unit.to_dict()), 200

@lec_blueprint.route('/units/<string:unit_id>', methods=['DELETE'])
def delete_unit(unit_id):
    '''
    Delete a unit.
    Returns: JSON response with success message or error if not found
    '''
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    
    db.session.delete(unit)
    db.session.commit()
    return jsonify({'message': 'Unit deleted successfully'}), 200

# --- CRUD: Students ---
@lec_blueprint.route('/students', methods=['POST'])
def add_student():
    """
    Add a new student to a course.
    Requires: email, reg_number, year_of_study, semester, firstname, surname, course_id, othernames (optional)
    Returns: JSON response with success message or error
    """
    data = request.get_json() or {}

    # Validate required fields
    required_fields = ['email', 'reg_number', 'year_of_study', 'semester',
                       'firstname', 'surname', 'course_id']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Ensure the course exists
    course = Course.query.get(data['course_id'])
    if not course:
        return jsonify({'error': 'Invalid course_id'}), 400

    # Try to find existing user
    user = User.query.filter_by(email=data['email']).first()

    if user:
        # If there's already a Student record for this user
        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({'error': 'User exists but is not a student'}), 400

        # Check if already enrolled in this course
        if course in student.courses:
            return jsonify({
                'error': 'Student is already registered for this course'
            }), 400

        # Enroll in new course
        student.courses.append(course)
        db.session.commit()
        return jsonify({
            'message': 'Existing student successfully enrolled in additional course',
            'student_id': student.id,
            'enrolled_courses': [
                {'id': c.id, 'name': c.name} for c in student.courses
            ]
        }), 200

    # Create user (password defaults to hashed reg_number)
    user = User(
        email=data['email'],
        password=hashing_password(data['reg_number']),
        role='student'
    )
    db.session.add(user)
    db.session.flush()  # assign user.id

    # Create student and link the one course
    student = Student(
        user_id=user.id,
        reg_number=data['reg_number'],
        year_of_study=data['year_of_study'],
        semester=data['semester'],
        firstname=data['firstname'],
        surname=data['surname'],
        othernames=data.get('othernames'),
    )
    student.courses.append(course)

    db.session.add(student)
    db.session.commit()

    return jsonify({
        'message': 'Student account created and enrolled successfully',
        'student_id': student.id,
        'enrolled_courses': [
            {'id': course.id, 'name': course.name}
        ]
    }), 201

@lec_blueprint.route('/students/bulk-upload', methods=['POST'])
def bulk_upload_students():
    """
    Bulk upload students from an Excel file.
    Expects a file upload with Excel containing columns:
    reg_number, year_of_study, semester, firstname, surname, email, course_name, othernames(optional)
    Returns: JSON response with success/error counts and details
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Validate extension
    if os.path.splitext(file.filename)[1].lower() not in ('.xlsx', '.xls'):
        return jsonify({'error': 'Invalid file format. Please upload Excel file (.xlsx or .xls)'}), 400

    try:
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip()

        # Required columns
        required = ['reg_number', 'year_of_study', 'semester',
                    'firstname', 'surname', 'email', 'course_name']
        missing = [c for c in required if c not in df.columns]
        if missing:
            return jsonify({'error': f'Missing required columns: {", ".join(missing)}'}), 400

        # Build course lookup by name/code
        courses = Course.query.all()
        name_map = {c.name.lower(): c for c in courses}
        code_map = {c.code.lower(): c for c in courses if c.code}

        success, errors = 0, []

        for idx, row in df.iterrows():
            row_num = idx + 2
            try:
                # skip blank
                if pd.isna(row['email']) or pd.isna(row['reg_number']) or pd.isna(row['course_name']):
                    continue

                email      = str(row['email']).strip().lower()
                reg        = str(row['reg_number']).strip()
                year       = int(row['year_of_study'])
                sem        = int(row['semester'])
                fname      = str(row['firstname']).strip()
                sname      = str(row['surname']).strip()
                other      = str(row.get('othernames', '')).strip() or None
                lookup_key = str(row['course_name']).strip().lower()

                # find course
                course = name_map.get(lookup_key) or code_map.get(lookup_key)
                if not course:
                    # fallback partial match
                    for nm, c in name_map.items():
                        if lookup_key in nm or nm in lookup_key:
                            course = c
                            break
                if not course:
                    errors.append(f'Row {row_num}: Course "{row["course_name"]}" not found.')
                    continue

                # basic email check
                if '@' not in email:
                    errors.append(f'Row {row_num}: Invalid email "{email}".')
                    continue

                # validate year/semester
                if not (1 <= year <= 6):
                    errors.append(f'Row {row_num}: year_of_study {year} (must 1–6).')
                    continue
                if not (1 <= sem <= 2):
                    errors.append(f'Row {row_num}: semester {sem} (must 1–2).')
                    continue

                # lookup existing user/student
                user    = User.query.filter_by(email=email).first()
                student = user and Student.query.filter_by(user_id=user.id).first()

                if student:
                    # already a student: enroll if needed
                    if course in student.courses:
                        errors.append(f'Row {row_num}: Already enrolled in "{course.name}".')
                    else:
                        student.courses.append(course)
                        success += 1

                elif user and not student:
                    errors.append(f'Row {row_num}: User exists but is not a student.')
                    continue

                else:
                    # brand‐new user+student
                    user = User(email=email,
                                password=hashing_password(reg),
                                role='student')
                    db.session.add(user)
                    db.session.flush()

                    student = Student(
                        user_id=user.id,
                        reg_number=reg,
                        year_of_study=year,
                        semester=sem,
                        firstname=fname,
                        surname=sname,
                        othernames=other,
                    )
                    student.courses.append(course)
                    db.session.add(student)
                    success += 1

            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
                continue

        # commit changes if any successes
        if success:
            db.session.commit()
        else:
            db.session.rollback()

        resp = {
            'message': 'Bulk upload completed',
            'success_count': success,
            'error_count': len(errors),
            'total_processed': success + len(errors)
        }
        if errors:
            resp['errors'] = errors[:10]
            if len(errors) > 10:
                resp['note'] = f'Showing first 10 errors of {len(errors)}.'

        return jsonify(resp), (201 if success else 400)

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process file: {e}'}), 500


@lec_blueprint.route('/students/<string:student_id>', methods=['GET'])
def get_student(student_id):
    """
    Get a specific student's details by ID.
    """
    student = (
        Student.query
               .options(joinedload(Student.courses))
               .get(student_id)
    )
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    return jsonify(student.to_dict()), 200


@lec_blueprint.route('/students', methods=['GET'])
def get_students():
    """
    Get all students in any course created by the lecturer.
    """
    lecturer_id = get_jwt_identity()

    # Join through the association table, filtering on courses.created_by
    students = (
        Student.query
               .join(student_courses, Student.id == student_courses.c.student_id)
               .join(Course, Course.id == student_courses.c.course_id)
               .filter(Course.created_by == lecturer_id)
               .options(joinedload(Student.courses))
               .all()
    )

    # If none, return empty list (200)
    return jsonify([s.to_dict() for s in students]), 200


@lec_blueprint.route('/students/<string:student_id>', methods=['PUT'])
def update_student(student_id):
    """
    Update a student's details.
    Accepts any of:
      - reg_number, year_of_study, semester, firstname, surname, othernames
      - email (updates the User.email)
      - course_ids: [<course_id>, ...]  (replaces existing enrollments)
    """
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    data = request.get_json() or {}

    if 'email' in data:
        user = User.query.get(student.user_id)
        if not user:
            return jsonify({'error': 'Associated user not found'}), 500
        user.email = data['email'].strip().lower()

    for fld in ('reg_number', 'year_of_study', 'semester', 'firstname', 'surname', 'othernames'):
        if fld in data:
            setattr(student, fld, data[fld])

    if 'course_ids' in data:
        if not isinstance(data['course_ids'], list):
            return jsonify({'error': 'course_ids must be a list'}), 400

        # Fetch & validate all provided courses
        new_courses = Course.query.filter(Course.id.in_(data['course_ids'])).all()
        found_ids   = {c.id for c in new_courses}
        missing     = set(data['course_ids']) - found_ids
        if missing:
            return jsonify({'error': f'Invalid course_ids: {missing}'}), 400

        # Replace the list
        student.courses = new_courses

    db.session.commit()
    return jsonify(student.to_dict()), 200


@lec_blueprint.route('/students/<string:student_id>', methods=['DELETE'])
def delete_student(student_id):
    """
    Delete a student and their user account.
    """
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    # delete user first (FK cascade on student → user?)
    user = User.query.get(student.user_id)
    if user:
        db.session.delete(user)

    # this will also clear student_courses rows via ON DELETE CASCADE
    db.session.delete(student)
    db.session.commit()

    return jsonify({'message': 'Student and user account deleted successfully'}), 200
