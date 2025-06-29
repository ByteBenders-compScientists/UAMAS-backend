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

from flask import Blueprint, request, jsonify, current_app
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

    return jsonify([
        assessment.to_dict() for assessment in assessments
    ]), 200

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
            upload_folder=upload_dir
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

        submission_data = {
            'submission_id': submission.id,
            'assessment_id': submission.assessment_id,
            'graded': submission.graded,
            'total_marks': total_marks.total_marks if total_marks else 0,
            'results': results_data
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

    return jsonify([note.to_dict() for note in notes]), 200
