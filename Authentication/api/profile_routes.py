from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from .models import db, User, Student, Lecturer, Unit, Course

profile_blueprint = Blueprint('profile', __name__)

@profile_blueprint.before_request
@jwt_required()
def check_profile_access():
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims["role"] not in ['student', 'lecturer']:
        return jsonify({'error': 'Access restricted to students and lecturers only'}), 403
    
@profile_blueprint.route('/profile', methods=['GET'])
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.role == 'student':
        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        return jsonify(student.to_dict()), 200
    
    elif user.role == 'lecturer':
        lecturer = Lecturer.query.filter_by(user_id=user.id).first()
        if not lecturer:
            return jsonify({'error': 'Lecturer profile not found'}), 404
        return jsonify(lecturer.to_dict()), 200
    
    return jsonify({'error': 'Invalid role'}), 400

@profile_blueprint.route('/profile', methods=['PUT'])
def update_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json() or {}
    
    if user.role == 'student':
        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        # Update student profile fields
        for key, value in data.items():
            if hasattr(student, key):
                setattr(student, key, value)
        
        db.session.commit()
        return jsonify(student.to_dict()), 200
    
    elif user.role == 'lecturer':
        lecturer = Lecturer.query.filter_by(user_id=user.id).first()
        if not lecturer:
            return jsonify({'error': 'Lecturer profile not found'}), 404
        
        # Update lecturer profile fields
        for key, value in data.items():
            if hasattr(lecturer, key):
                setattr(lecturer, key, value)
        
        db.session.commit()
        return jsonify(lecturer.to_dict()), 200
    
    return jsonify({'error': 'Invalid role'}), 400
