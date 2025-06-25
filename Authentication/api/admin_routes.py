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

    # check the lecturer exists
    if not Lecturer.query.get(id):
        return jsonify({'error': 'Lecturer not found'}), 404

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
