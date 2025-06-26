"""
Blueprint for Lecture-Assessments API routes.
Created by: https://github.com/ByteBenders-compScientists/UAMAS-backend
Actions:
- Create assessment(CAT, Case Study, Assignment): Manually or through AI
- Using AI to generate questions for assessments (Type topic, description, and number of questions etc) OR (Upload a document and AI will generate questions based on the content)
- Create questions manually
- Verify assessment questions and answers created by AI
- View and verify marked assessments by AI
- Update, delete, and view assessments
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from api import db
from api.utils import ai_create_assessment
from api.models import Assessment, Question, Submission, Answer, Result, TotalMarks, Course, Unit, Notes

import os
import uuid
import json
import re

load_dotenv()
lec_blueprint = Blueprint('lec', __name__)

'''
Before every request to verify if the user is a lecturer
'''
@lec_blueprint.before_request
@jwt_required(locations=['cookies', 'headers'])
def verify_lecturer():
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims.get('role') != 'lecturer':
        return jsonify({'error': 'Unauthorized access'}), 403

@lec_blueprint.route('/ai/generate-assessments', methods=['POST'])
def generate_assessments():
    """
    Generate an assessment using AI based on the provided parameters.
    This endpoint is accessible only to lecturers.
    """
    user_id = get_jwt_identity()
    # print(f"User ID: {user_id}")

    data = request.json or {}
    required_fields = [
        'title', 'description','week', 'type', 'unit_id',
        'questions_type', 'topic', 'total_marks',
        'difficulty', 'number_of_questions', 'blooms_level'
    ]
    # get course_id and unit_id from the payload
    unit = Unit.query.get(data['unit_id'])
    if not unit:
        return jsonify({'message': 'Unit not found.'}), 404

    data['course_id'] = unit.course_id
    data['unit_name'] = unit.unit_name

    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Invalid input data.'}), 400
    
    # check if the questions_type == close-ended then close_ended_type is required
    if data['questions_type'] == "close-ended" and 'close_ended_type' not in data:
        return jsonify({'message': 'close_ended_type is required for close-ended questions.'}), 400
    else:
        data['close_ended_type'] = data['close_ended_type']

    res = ai_create_assessment(data)

    if not hasattr(res, "choices") or len(res.choices) == 0:
        return jsonify({'message': 'No response from AI model.'}), 500

    first_choice = res.choices[0]
    if not (hasattr(first_choice, "message") and hasattr(first_choice.message, "content")):
        return jsonify({'message': 'Invalid response format from AI model.'}), 500

    generated = first_choice.message.content

    generated = re.sub(r'```json\s*', '', generated)
    generated = re.sub(r'\s*```', '', generated)
    
    # print(f"Cleaned assessment: {generated}")

    try:
        payload = json.loads(generated)
    except json.JSONDecodeError:
        return jsonify({'message': 'AI did not return valid JSON.'}), 500
    
    # print(f"Payload: {payload}")

    assessment = Assessment(
        creator_id       = user_id,
        title            = data['title'],
        week             = data['week'],  # Default to week 1 if not provided
        description      = data['description'],
        questions_type   = data['questions_type'],
        type             = data['type'],
        unit_id          = data['unit_id'],
        course_id        = data['course_id'],
        topic            = data['topic'],
        total_marks      = data['total_marks'],
        difficulty       = data['difficulty'],
        number_of_questions = data['number_of_questions'],
        deadline         = data.get('deadline', None),  # Optional field
        duration         = data.get('duration', None),  # Optional field
        blooms_level     = data.get('blooms_level', None),  # Optional field
        close_ended_type = data.get('close_ended_type', None)  # Optional field for close-ended questions
    )
    db.session.add(assessment)
    db.session.flush()   # so that assessment.id is set

    for key, q_obj in payload.items():

        # if 'choices' in q_obj:
        if 'choices' in q_obj and isinstance(q_obj['choices'], list):
            # If choices are provided, we assume it's a close-ended question
            question = Question(
                assessment_id = assessment.id,
                text          = q_obj.get('text', ''),
                marks         = float(q_obj.get('marks', 0)),
                type          = 'close-ended',
                rubric        = q_obj.get('rubric', ''),
                correct_answer= q_obj['correct_answer'],  # list of strings
                choices       = q_obj['choices']  # Store choices as a list
            )
        else:
            # Otherwise, it's an open-ended question
            question = Question(
                assessment_id = assessment.id,
                text          = q_obj.get('text', ''),
                marks         = float(q_obj.get('marks', 0)),
                type          = 'open-ended',
                rubric        = q_obj.get('rubric', ''),
                correct_answer= q_obj.get('correct_answer', [])
            )
        db.session.add(question)

    db.session.commit()

    return jsonify({
        'message'       : 'Assessment generated successfully.',
        'assessment_id' : assessment.id,
        'title'         : assessment.title
    }), 201

@lec_blueprint.route('/assessments/<assessment_id>/verify', methods=['GET'])
def verify_assessment(assessment_id):
    """
    Verify an assessment created by AI.
    This endpoint is accessible only to lecturers.
    """
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'message': 'Assessment not found.'}), 404
    
    # Check if the assessment is already verified
    if assessment.verified:
        return jsonify({'message': 'Assessment is already verified.'}), 400
    
    # Mark the assessment as verified
    assessment.verified = True
    db.session.commit()

    # TODO: Add email notification to the students about the created assessment

    return jsonify({
        'message': 'Assessment verified successfully.',
        'assessment_id': assessment.id,
        'title': assessment.title
    }), 200

@lec_blueprint.route('/generate-assessments', methods=['POST'])
def create_assessment():
    """
    Create an assessment manually.
    This endpoint is accessible only to lecturers.
    """
    user_id = get_jwt_identity()

    data = request.json or {}
    required_fields = [
        'title', 'description', 'week', 'type', 'unit_id',
        'questions_type', 'topic', 'total_marks',
        'difficulty', 'number_of_questions', 'blooms_level'
    ]
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Invalid input data.'}), 400
    
    # get course_id and unit_id from the payload
    unit = Unit.query.get(data['unit_id'])
    data['course_id'] = unit.course_id

    # optional set to None if = not provided or ""
    if data['deadline'] == "":
        data['deadline'] = None
    if data['duration'] == "":
        data['duration'] = None
    if data['blooms_level'] == "":
        data['blooms_level'] = None
    if data['close_ended_type'] == "":
        data['close_ended_type'] = None

    assessment = Assessment(
        creator_id       = user_id,
        title            = data['title'],
        week             = data['week'],  # Default to week 1 if not provided
        description      = data['description'],
        questions_type   = data['questions_type'],
        close_ended_type = data.get('close_ended_type', None),  # Optional field for close-ended questions
        type             = data['type'],
        unit_id          = data['unit_id'],
        course_id        = data.get('course_id'),
        topic            = data['topic'],
        total_marks      = data['total_marks'],
        difficulty       = data['difficulty'],
        number_of_questions = data['number_of_questions'],
        deadline         = data.get('deadline', None),  # Optional field
        duration         = data.get('duration', None),  # Optional field
        blooms_level     = data.get('blooms_level', None)  # Optional field
    )
    db.session.add(assessment)
    db.session.commit()

    # TODO: Add email notification to the target students about the created assessment
    
    return jsonify({
        'message': 'Assessment created successfully.',
        'assessment_id': assessment.id,
        'title': assessment.title
    }), 201

@lec_blueprint.route('/assessments/<assessment_id>', methods=['DELETE'])
def delete_assessment(assessment_id):
    """
    Delete an assessment.
    This endpoint is accessible only to lecturers.
    """
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'message': 'Assessment not found.'}), 404
    
    db.session.delete(assessment)
    db.session.commit()

    return jsonify({'message': 'Assessment deleted successfully.'}), 200

@lec_blueprint.route('/assessments/<assessment_id>/questions', methods=['POST'])
def add_question_to_assessment(assessment_id):
    """
    Add a question to an assessment.
    This endpoint is accessible only to lecturers.
    """
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'message': 'Assessment not found.'}), 404
    
    data = request.json or {}
    required_fields = ['text', 'marks', 'type', 'rubric', 'correct_answer']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Invalid input data.'}), 400
    
    # set to none if not provided or ""
    if data['choices'] == "":
        data['choices'] = None
    if data["correct_answer"] == "":
        data['correct_answer'] = None
    
    question = Question(
        assessment_id = assessment.id,
        text          = data['text'],
        marks         = float(data['marks']),
        type          = data['type'],  # 'open-ended' or 'close-ended'
        rubric        = data['rubric'],
        correct_answer= data['correct_answer'],
        choices       = data.get('choices', [])  # Optional field for close-ended questions
    )
    
    db.session.add(question)
    db.session.commit()

    return jsonify({
        'message': 'Question added successfully.',
        'question_id': question.id
    }), 201

@lec_blueprint.route('/assessments', methods=['GET'])
def get_lecturer_assessments():
    '''
    Get all assessments created by the lecturer.
    This endpoint is accessible only to lecturers.
    '''
    user_id = get_jwt_identity()
    assessments = Assessment.query.filter_by(creator_id=user_id).all()
    return jsonify([assessment.to_dict() for assessment in assessments]), 200

@lec_blueprint.route('/units/<unit_id>/notes', methods=['POST'])
def upload_notes(unit_id):
    """
    Upload notes for a specific unit.
    """
    user_id = get_jwt_identity()

    # Get course_id from the unit
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({'message': 'Unit not found.'}), 404
    course_id = unit.course_id
    
    # Check if file is present in request
    if 'file' not in request.files:
        return jsonify({'message': 'No file provided.'}), 400
    
    file = request.files['file']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'message': 'No file selected.'}), 400
    
    # Get additional form data
    title = request.form.get('title')
    description = request.form.get('description', '')
    
    if not title:
        return jsonify({'message': 'Title is required.'}), 400
    
    # Define allowed file extensions
    ALLOWED_EXTENSIONS = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'ppt': 'application/vnd.ms-powerpoint',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    }
    
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS.keys()
    
    if not allowed_file(file.filename):
        return jsonify({
            'message': 'Invalid file type. Allowed types: PDF, DOC, DOCX, PPT, PPTX'
        }), 400
    
    try:
        # Create secure filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}_{original_filename}"
        
        # Create notes directory structure
        notes_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'notes')
        course_dir = os.path.join(notes_dir, f"course_{course_id}")
        unit_dir = os.path.join(course_dir, f"unit_{unit_id}")
        
        # Create directories if they don't exist
        os.makedirs(unit_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(unit_dir, unique_filename)
        file.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Verify that the course and unit exist
        course = Course.query.get(course_id)
        if not course:
            os.remove(file_path)  # Clean up uploaded file
            return jsonify({'message': 'Course not found.'}), 404
            
        unit = Unit.query.get(unit_id)
        if not unit:
            os.remove(file_path)  # Clean up uploaded file
            return jsonify({'message': 'Unit not found.'}), 404
        
        # Verify unit belongs to the course
        if unit.course_id != course_id:
            os.remove(file_path)  # Clean up uploaded file
            return jsonify({'message': 'Unit does not belong to the specified course.'}), 400
        
        # Store file information in database
        note = Notes(
            lecturer_id=user_id,
            course_id=course_id,
            unit_id=unit_id,
            title=title,
            description=description,
            original_filename=original_filename,
            stored_filename=unique_filename,
            file_path=os.path.join('notes', f"course_{course_id}", f"unit_{unit_id}", unique_filename),
            file_size=file_size,
            file_type=file_extension,
            mime_type=ALLOWED_EXTENSIONS.get(file_extension)
        )
        
        db.session.add(note)
        db.session.commit()
        
        return jsonify({
            'message': 'Notes uploaded successfully.',
            'note_id': note.id,
            'file_info': {
                'title': title,
                'filename': original_filename,
                'file_type': file_extension,
                'file_size': file_size,
                'course_id': course_id,
                'unit_id': unit_id,
                'created_at': note.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return jsonify({
            'message': 'Failed to upload notes.',
            'error': str(e)
        }), 500

# Route to delete a note (only by the lecturer who uploaded it)
@lec_blueprint.route('/notes/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    user_id = get_jwt_identity()
    
    # Get note from database
    note = Notes.query.get(note_id)
    if not note:
        return jsonify({'message': 'Note not found.'}), 404
    
    # Check if the lecturer is the owner of the note
    if note.lecturer_id != user_id:
        return jsonify({'message': 'Access forbidden: You can only delete your own notes.'}), 403
    
    # Delete file from disk
    full_file_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), note.file_path)
    if os.path.exists(full_file_path):
        try:
            os.remove(full_file_path)
        except Exception as e:
            return jsonify({
                'message': 'Failed to delete file from disk.',
                'error': str(e)
            }), 500
    
    # Delete from database
    try:
        db.session.delete(note)
        db.session.commit()
        
        return jsonify({
            'message': 'Note deleted successfully.',
            'note_id': note_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'message': 'Failed to delete note from database.',
            'error': str(e)
        }), 500


# Route to get all notes uploaded by a specific lecturer
@lec_blueprint.route('/notes', methods=['GET'])
def get_lecturer_notes():
    user_id = get_jwt_identity()
    
    # Get all notes uploaded by this lecturer
    notes = Notes.query.filter_by(lecturer_id=user_id).order_by(Notes.created_at.desc()).all()
    
    return jsonify({
        'message': 'Lecturer notes retrieved successfully.',
        'notes': [note.to_dict() for note in notes]
    }), 200
