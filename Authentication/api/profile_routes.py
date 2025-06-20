from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from .models import db, User, Student, Lecturer, Unit, Course

profile_blueprint = Blueprint('profile', __name__)

@profile_blueprint.route('/student/details/units', methods=['GET'])
@jwt_required()
def get_student_units():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user = User.query.get(user_id)

    if not user or claims.get('role') != 'student':
        return jsonify({'error': 'Unauthorized access'}), 403

    student = Student.query.filter_by(user_id=user.id).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    units = student.units
    units_with_lecturers = []

    # print(units)
    
    for unit in units:
        lecturers = []
        for lecturer in unit.lecturers:
            lecturers.append({
                'id': lecturer.id,
                'name': f"{lecturer.firstname} {lecturer.surname}",
                'email': lecturer.user.email if lecturer.user else None
            })
        
        units_with_lecturers.append({
            'id': unit.id,
            'unit_code': unit.unit_code,
            'unit_name': unit.unit_name,
            'level': unit.level,
            'semester': unit.semester,
            'course_id': unit.course_id,
            'lecturers': lecturers
        })

    response = {
        'student_id': student.id,
        'reg_number': student.reg_number,
        'year_of_study': student.year_of_study,
        'semester': student.semester,
        'firstname': student.firstname,
        'surname': student.surname,
        'othernames': student.othernames,
        'course': {
            'id': student.course.id if student.course else None,
            'name': student.course.name if student.course else None
        },
        'units': units_with_lecturers
    }

    # print(response)  # Debugging line to check the response structure

    return jsonify(response), 200
