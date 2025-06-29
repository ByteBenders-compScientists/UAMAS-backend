"""
Blueprint for admin-related API routes.
Created by: https://github.com/ByteBenders-compScientists/UAMAS-backend
Actions: 
- Create, read, update, delete lecturers
"""

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
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403
    claims = get_jwt()
    if claims["role"] != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403

# --- CRUD: Lecturers ---
@admin_blueprint.route('/lecturers', methods=['POST'])
def create_lecturer():
    """Create a new lecturer.
    Requires: email, firstname, surname, othernames (optional)
    Returns: JSON response with lecturer details and temporary password or error
    """
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
    """List all lecturers.
    Returns: JSON response with list of lecturers
    """
    return jsonify([l.to_dict() for l in Lecturer.query.all()]), 200

@admin_blueprint.route('/lecturers/<id>', methods=['PUT'])
def update_lecturer(id):
    """Update a lecturer's details.
    Requires: id of the lecturer to update
    Returns: JSON response with updated lecturer details
    """
    l = Lecturer.query.get_or_404(id)
    data = request.get_json() or {}
    for f in ['firstname', 'surname', 'othernames']:
        if f in data:
            setattr(l, f, data[f])
    db.session.commit()
    return jsonify(l.to_dict()), 200

@admin_blueprint.route('/lecturers/<id>', methods=['DELETE'])
def delete_lecturer(id):
    """Delete a lecturer.
    Requires: id of the lecturer to delete
    Returns: JSON response with success message
    """
    l = Lecturer.query.get_or_404(id)
    # delete the user associated with the lecturer
    user = User.query.get(l.user_id)
    if user:
        db.session.delete(user)
    # delete the lecturer
    db.session.delete(l)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200

@admin_blueprint.route('/analytics', methods=['GET'])
def get_analytics():
    """Get analytics data for users and courses.
    Returns: JSON response with user and course statistics
    """
    # Count users by role
    user_counts = {
        'students': Student.query.count(),
        'lecturers': Lecturer.query.count(),
        'admins': User.query.filter_by(role='admin').count()
    }

    # Count courses and units
    course_counts = {
        'courses': Course.query.count(),
        'units': Unit.query.count()
    }

    return jsonify({
        'user_counts': user_counts,
        'course_counts': course_counts
    }), 200
