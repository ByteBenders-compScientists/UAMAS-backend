from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from dotenv import load_dotenv

from api import db
from api.models import Assessment, Question, Submission, Answer, Result, TotalMarks, Course, Unit, Notes

import os

load_dotenv()
bd_blueprint = Blueprint('bd', __name__)

endpoint = os.getenv('OPENAI_API_KEY_ENDPOINT')
model_deployment_name = os.getenv('MODEL_DEPLOYMENT_NAME')
subscription_key1 = os.getenv('OPENAI_API_KEY1')
subscription_key2 = os.getenv('OPENAI_API_KEY2')
api_version = os.getenv('API_VERSION')

# endpoint for students & lecturers to get questions of an assessment
@bd_blueprint.route('/assessments/<assessment_id>/questions', methods=['GET'])
@jwt_required(locations=['cookies', 'headers'])
def get_assessment_questions(assessment_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'message': 'Assessment not found.'}), 404
    
    # Check if the user has access to the assessment: => Role: lecturer or student
    if claims['role'] != 'lecturer' and claims['role'] != 'student':
        return jsonify({'message': 'Access forbidden: Only lecturers or students can view assessment questions.'}), 403

    questions = Question.query.filter_by(assessment_id=assessment.id).all()
    return jsonify([question.to_dict() for question in questions]), 200

# Route to download a specific note file
@bd_blueprint.route('/notes/<note_id>/download', methods=['GET'])
@jwt_required(locations=['cookies', 'headers'])
def download_note(note_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    
    # Both students and lecturers can download notes
    if claims.get('role') not in ['student', 'lecturer']:
        return jsonify({'message': 'Access forbidden.'}), 403
    
    from api.models import Notes
    from flask import send_file
    
    # Get note from database
    note = Notes.query.get(note_id)
    if not note:
        return jsonify({'message': 'Note not found.'}), 404
    
    # Construct full file path
    full_file_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), note.file_path)
    
    # Check if file exists
    if not os.path.exists(full_file_path):
        return jsonify({'message': 'File not found on disk.'}), 404
    
    try:
        return send_file(
            full_file_path,
            as_attachment=True,
            download_name=note.original_filename,
            mimetype=note.mime_type
        )
    except Exception as e:
        return jsonify({
            'message': 'Failed to download file.',
            'error': str(e)
        }), 500

# Additional route to get notes for a specific course and unit
@bd_blueprint.route('/courses/<course_id>/units/<unit_id>/notes', methods=['GET'])
@jwt_required(locations=['cookies', 'headers'])
def get_notes(course_id, unit_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    
    # Both students and lecturers can view notes
    if claims.get('role') not in ['student', 'lecturer']:
        return jsonify({'message': 'Access forbidden.'}), 403
    
    from api.models import Notes, Course, Unit
    
    # Verify course and unit exist
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'message': 'Course not found.'}), 404
        
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({'message': 'Unit not found.'}), 404
    
    # Verify unit belongs to the course
    if unit.course_id != course_id:
        return jsonify({'message': 'Unit does not belong to the specified course.'}), 400
    
    # Query notes from database
    notes = Notes.query.filter_by(course_id=course_id, unit_id=unit_id).order_by(Notes.created_at.desc()).all()
    
    return jsonify({
        'message': 'Notes retrieved successfully.',
        'course': {
            'id': course.id,
            'name': course.name,
            'code': course.code
        },
        'unit': {
            'id': unit.id,
            'name': unit.unit_name,
            'code': unit.unit_code
        },
        'notes': [note.to_dict() for note in notes]
    }), 200
