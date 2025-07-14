"""
Blueprint for Student-Assessments API routes.
Created by: https://github.com/ByteBenders-compScientists/UAMAS-backend
Actions:
- Get all assessments for a student
- Get a specific assessment by ID
- Get all questions for a specific assessment
- Submit an answer for a specific question in an assessment
- Submit an assessment
- Get all submissions for a student (including completed and in-progress)
"""

from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from api import db
from api.models import Assessment, Question, Submission, Answer, Result, TotalMarks, Course, Unit, Notes, User, Lecturer, Student
from api.utils import grade_text_answer, grade_image_answer

import os
import uuid

load_dotenv()
student_blueprint = Blueprint('student', __name__)

@student_blueprint.before_request
@jwt_required(locations=['cookies', 'headers'])
def verify_jwt():
    """
    Verify the JWT token and ensure the user is a student.
    """
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims['role'] != 'student':
        return jsonify({"msg": "Access forbidden: Students only"}), 403
    
@student_blueprint.route('/assessments', methods=['GET'])
def get_student_assessments():
    """
    Get all assessments for a specific course.
    """
    user_id = get_jwt_identity()

    # get year_of_study and semester from the user: Student model
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'message': 'Student not found.'}), 404
    
    # filter only verified == True
    assessments = Assessment.query.filter_by(course_id=student.course_id, verified=True).all()
    if not assessments:
        return jsonify({'message': 'No assessments found for this course.'}), 404
    # Filter assessments by year and semester if provided
    if student.year_of_study is not None and student.semester is not None:
        assessments = [a for a in assessments if a.level == student.year_of_study and a.semester == student.semester]
    elif student.year_of_study is not None:
        assessments = [a for a in assessments if a.level == student.year_of_study]
    elif student.semester is not None:
        assessments = [a for a in assessments if a.semester == student.semester]

    # status: start (no submission and no questions answered), in-progress (no submission but part questions answered (in the answer table)) and completed (if its submission exists(for this assessment))
    assessments_data = []
    for assessment in assessments:
        # Check if the student has submitted this assessment
        submission = Submission.query.filter_by(assessment_id=assessment.id, student_id=user_id).first()
        if submission:
            status = 'completed'
        else:
            # Check if the student has answered any questions in this assessment
            answered_questions = Answer.query.filter_by(assessment_id=assessment.id, student_id=user_id).first()
            if answered_questions:
                status = 'in-progress'
            else:
                status = 'start'

        assessments_data.append({
            'id': assessment.id,
            'topic': assessment.topic,
            'creator_id': assessment.creator_id,
            'week': assessment.week,
            'title': assessment.title,
            'description': assessment.description,
            'questions_type': assessment.questions_type,
            'type': assessment.type,
            'unit_id': assessment.unit_id,
            'course_id': assessment.course_id,
            'topic': assessment.topic,
            'total_marks': assessment.total_marks,
            'number_of_questions': assessment.number_of_questions,
            'difficulty': assessment.difficulty,
            'verified': assessment.verified,
            'created_at': assessment.created_at.isoformat(),
            'level': assessment.level,
            'semester': assessment.semester,
            'deadline': assessment.deadline.isoformat() if assessment.deadline else None,
            'duration': assessment.duration,
            'blooms_level': assessment.blooms_level,
            'close_ended_type': assessment.close_ended_type,
            'questions': [q.to_dict() for q in assessment.questions] if assessment.questions else [],
            'status': status
        })
    
    # foreach question, append status to the existing question dict
    for assessment in assessments_data:
        for question in assessment['questions']:
            # Check if the student has answered this question
            answered = Answer.query.filter_by(question_id=question['id'], student_id=user_id).first()
            if answered:
                question['status'] = 'answered'
            else:
                question['status'] = 'not answered'

    return jsonify(assessments_data), 200

@student_blueprint.route('/questions/<question_id>/answer', methods=['POST'])
def submit_answer(question_id):
    """
    Submit an answer for a specific question in an assessment.
    """
    user_id = get_jwt_identity()

    # get the assessment_id from the question_id
    question = Question.query.get(question_id)
    if not question:
        return jsonify({'message': 'Question not found.'}), 404

    assessment = Assessment.query.get(question.assessment_id)
    if not assessment:
        return jsonify({'message': 'Assessment not found.'}), 404

    if not question or question.assessment_id != assessment.id:
        return jsonify({'message': 'Question not found in this assessment.'}), 404
    
    # CHECK IF THE STUDENT HAS ALREADY SUBMITTED AN ANSWER FOR THIS QUESTION
    existing_answer = Answer.query.filter_by(question_id=question.id, student_id=user_id).first()
    if existing_answer:
        return jsonify({'message': 'You have already submitted an answer for this question.'}), 400

    data = request.form
    answer_type = data.get('answer_type')
    if answer_type not in ['text', 'image']:
        return jsonify({'message': 'Invalid answer type. Must be "text" or "image".'}), 400

    text_answer = None
    image_path  = None
    image_url   = None

    if answer_type == 'image':
        if 'image' not in request.files:
            return jsonify({'message': 'Image file is required for image answers.'}), 400

        image_file = request.files['image']
        ext = image_file.filename.rsplit('.', 1)[-1].lower()
        allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'png','jpg','jpeg'})
        if ext not in allowed:
            return jsonify({'message': f'Invalid image type. Allowed: {", ".join(allowed)}'}), 400

        filename    = f"{uuid.uuid4()}_{secure_filename(image_file.filename)}"
        upload_dir  = os.path.join(current_app.config['UPLOAD_FOLDER'], 'student_answers')
        os.makedirs(upload_dir, exist_ok=True)
        file_path   = os.path.join(upload_dir, filename)
        image_file.save(file_path)
        image_path  = filename
        image_url = f"https://api.waltertayarg.me/api/v1/bd/uploads/student_answers/{filename}"
        # print(image_url)
    else:
        text_answer = data.get('text_answer')

    # Save the raw answer first
    answer = Answer(
        question_id=   question.id,
        assessment_id= assessment.id,
        student_id=    user_id,
        text_answer=   text_answer,
        image_path=    image_path,
    )
    db.session.add(answer)
    db.session.commit()

    # Grade via AI
    if text_answer:
        (grading_result, status) = grade_text_answer(
            text_answer=text_answer,
            question_text=question.text,
            rubric=question.rubric,
            correct_answer=question.correct_answer,
            marks=question.marks
        )
    else:
        (grading_result, status) = grade_image_answer(
            filename=image_path,
            question_text=question.text,
            rubric=question.rubric,
            correct_answer=question.correct_answer,
            marks=question.marks,
            image_url=image_url
        )

    # If grading service returned an error code, propagate it
    if status != 200:
        return jsonify(grading_result), status

    # Persist the Result
    result = Result(
        question_id=   question.id,
        assessment_id= assessment.id,
        student_id=    user_id,
        score=         grading_result['score'],
        feedback=      grading_result['feedback']
    )
    db.session.add(result)
    db.session.commit()

    return jsonify({
        'message':       'Answer submitted successfully.',
        'question_id':   question.id,
        'assessment_id': assessment.id,
        'score':         grading_result['score'],
        'feedback':      grading_result['feedback']
    }), 201

@student_blueprint.route('/assessments/<assessment_id>/submit', methods=['GET'])
def submit_assessment(assessment_id):
    """
    Submit an assessment.
    This endpoint allows a student to submit an assessment after answering all questions.
    It checks if the student has already submitted the assessment and calculates total marks.
    Only students can access this endpoint.
    The submission is considered graded by default.
    """
    user_id = get_jwt_identity()

    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'message': 'Assessment not found.'}), 404

    # Check if the student has already submitted this assessment
    existing_submission = Submission.query.filter_by(assessment_id=assessment.id, student_id=user_id).first()
    if existing_submission:
        return jsonify({'message': 'You have already submitted this assessment.'}), 400

    # Create a new submission
    submission = Submission(
        assessment_id=assessment.id,
        student_id=user_id,
        graded=True,  # Assume submission is graded by default
    )
    
    db.session.add(submission)
    db.session.commit()

    # Calculate total marks in Python
    results = Result.query.filter_by(
        student_id=user_id,
        assessment_id=assessment.id
    ).all()

    total_marks = 0.0
    for result in results:
        # Check if score is a dict with 'marks_awarded' key, or just a float/number
        if result.score:
            if isinstance(result.score, dict) and 'marks_awarded' in result.score:
                total_marks += float(result.score['marks_awarded'])
            elif isinstance(result.score, (int, float)):
                # If score is already a number, use it directly
                total_marks += float(result.score)
            else:
                # Handle other cases - log for debugging
                print(f"Unexpected score format: {type(result.score)} - {result.score}")

    total_marks_entry = TotalMarks(
        student_id=user_id,
        assessment_id=assessment.id,
        submission_id=submission.id,
        total_marks=total_marks
    )
    
    db.session.add(total_marks_entry)
    db.session.commit()

    return jsonify({
        'message': 'Assessment submitted successfully.',
        'submission_id': submission.id,
        'total_marks': total_marks
    }), 201

@student_blueprint.route('/submissions', methods=['GET'])
def get_student_submissions():
    """
    Get all submissions for a student.
    This endpoint returns all submissions made by the student, including completed and in-progress ones.
    """
    user_id = get_jwt_identity()

    submissions = Submission.query.filter_by(student_id=user_id).all()
    if not submissions:
        return jsonify({'message': 'No submissions found for this student.'}), 404

    # combined the submissions with their total marks and results
    submissions_data = []
    for submission in submissions:
        total_marks = TotalMarks.query.filter_by(submission_id=submission.id).first()
        # include results alongside with corresponding question (take question_id from Result)
        results = Result.query.filter_by(assessment_id=submission.assessment_id, student_id=user_id).all()

        results_data = []
        for result in results:
            result_dict = result.to_dict()
            # Get the question for this result
            question = Question.query.get(result.question_id)
            result_dict['question_text'] = question.text if question else None
            result_dict['marks'] = question.marks if question else None
            result_dict['rubric'] = question.rubric if question else None
            result_dict['correct_answer'] = question.correct_answer if question else None
            results_data.append(result_dict)
        
        # assessment topic, number_of_questions, difficulty, deadline, duration, blooms_level, created_at
        assessment = Assessment.query.get(submission.assessment_id)
        if assessment:
            submission_data = {
                'assessment_id': assessment.id,
                'topic': assessment.topic,
                'number_of_questions': assessment.number_of_questions,
                'difficulty': assessment.difficulty,
                'deadline': assessment.deadline.isoformat() if assessment.deadline else None,
                'duration': assessment.duration,
                'blooms_level': assessment.blooms_level,
                'created_at': assessment.created_at.isoformat(),
            }
        else:
            submission_data = {
                'assessment_id': submission.assessment_id,
                'topic': None,
                'number_of_questions': None,
                'difficulty': None,
                'deadline': None,
                'duration': None,
                'blooms_level': None,
                'created_at': None,
            }

        submission_data = {
            'submission_id': submission.id,
            'assessment_id': submission.assessment_id,
            'graded': submission.graded,
            'total_marks': total_marks.total_marks if total_marks else 0,
            'results': results_data,
            **submission_data
        }
        submissions_data.append(submission_data)

    return jsonify(submissions_data), 200

@student_blueprint.route('/notes', methods=['GET'])
def get_student_notes():
    """
    Get all notes for a student.
    This endpoint returns all notes available for the student's course.
    """
    user_id = get_jwt_identity()

    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'message': 'Student not found.'}), 404

    # Get all notes for the student's course
    notes = Notes.query.filter_by(course_id=student.course_id).all()
    if not notes:
        return jsonify({'message': 'No notes found for this course.'}), 404

    # add course name and unit name (use the course_id and unit_id from Notes model)
    notes_data = []
    for note in notes:
        course = Course.query.get(note.course_id)
        unit = Unit.query.get(note.unit_id)
        note_dict = note.to_dict()
        note_dict['course_name'] = course.name if course else None
        note_dict['unit_name'] = unit.unit_name if unit else None
        notes_data.append(note_dict)

    return jsonify(notes_data), 200
