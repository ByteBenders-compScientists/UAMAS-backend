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
from api.models import Assessment, Question, Submission, Answer, Result, TotalMarks, Course, Unit, Notes, User, Lecturer, Student, AttemptAssessment
from api.utils import grade_text_answer, grade_image_answer
from sqlalchemy.orm import joinedload

import os
import uuid
from datetime import datetime, timedelta

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
    Get all assessments for the courses the student is enrolled in.
    """
    user_id = get_jwt_identity()

    # load student + their courses in one go
    student = (
        Student.query
               .options(joinedload(Student.courses))
               .filter_by(user_id=user_id)
               .first()
    )
    if not student:
        return jsonify({'message': 'Student not found.'}), 404

    # collect all course_ids
    course_ids = [c.id for c in student.courses]
    if not course_ids:
        return jsonify({'message': 'Student is not enrolled in any course.'}), 404

    # fetch all verified assessments for any of these courses
    assessments = Assessment.query \
        .filter(Assessment.course_id.in_(course_ids), Assessment.verified.is_(True)) \
        .all()

    if not assessments:
        return jsonify({'message': 'No assessments found for your courses.'}), 404

    # further filter by year/level & semester
    def matches(a):
        if student.year_of_study is not None and student.semester is not None:
            return a.level == student.year_of_study and a.semester == student.semester
        if student.year_of_study is not None:
            return a.level == student.year_of_study
        if student.semester is not None:
            return a.semester == student.semester
        return True

    assessments = [a for a in assessments if matches(a)]

    # build the payload
    payload = []
    for a in assessments:
        # has the student submitted?
        submission = Submission.query.filter_by(
            assessment_id=a.id,
            student_id=user_id
        ).first()

        if submission:
            status = 'completed'
        else:
            # any answered questions?
            ans = Answer.query.filter_by(
                assessment_id=a.id,
                student_id=user_id
            ).first()
            status = 'in-progress' if ans else 'start'

        payload.append({
            'id': a.id,
            'topic': a.topic,
            'creator_id': a.creator_id,
            'week': a.week,
            'title': a.title,
            'description': a.description,
            'questions_type': a.questions_type,
            'type': a.type,
            'unit_id': a.unit_id,
            'course_id': a.course_id,
            'total_marks': a.total_marks,
            'number_of_questions': a.number_of_questions,
            'difficulty': a.difficulty,
            'verified': a.verified,
            'created_at': a.created_at.isoformat(),
            'level': a.level,
            'semester': a.semester,
            'deadline': a.deadline.isoformat() if a.deadline else None,
            'duration': a.duration,
            'blooms_level': a.blooms_level,
            'close_ended_type': a.close_ended_type,
            'questions': [q.to_dict() for q in a.questions] if a.questions else [],
            'status': status
        })

    # tag each question with answered/not answered
    for asses in payload:
        for q in asses['questions']:
            answered = Answer.query.filter_by(
                question_id=q['id'],
                student_id=student.id
            ).first()
            q['status'] = 'answered' if answered else 'not answered'

    return jsonify(payload), 200

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
    Get all notes for the courses a student is enrolled in.
    """
    user_id = get_jwt_identity()

    student = (
        Student.query
               .options(joinedload(Student.courses))
               .filter_by(user_id=user_id)
               .first()
    )
    if not student:
        return jsonify({'message': 'Student not found.'}), 404

    course_ids = [c.id for c in student.courses]
    if not course_ids:
        return jsonify({'message': 'Student is not enrolled in any course.'}), 404

    notes = (
        Notes.query
             .filter(Notes.course_id.in_(course_ids))
             .all()
    )
    if not notes:
        return jsonify({'message': 'No notes found for your courses.'}), 404

    course_map = {c.id: c.name for c in student.courses}
    unit_ids   = {n.unit_id for n in notes if n.unit_id}
    units      = Unit.query.filter(Unit.id.in_(unit_ids)).all()
    unit_map   = {u.id: u.unit_name for u in units}

    notes_data = []
    for note in notes:
        nd = note.to_dict()
        nd['course_name'] = course_map.get(note.course_id)
        nd['unit_name']   = unit_map.get(note.unit_id)
        notes_data.append(nd)

    return jsonify(notes_data), 200


# handle timing(duration) for the assessment at the frontend
@student_blueprint.route('/start_assessment/<assessment_id>', methods=['POST'])
def start_assessment(assessment_id):
    """
    Record the start of an assessment attempt for a student.
    This endpoint creates an AttemptAssessment entry to track when the student started the assessment.
    """
    user_id = get_jwt_identity()

    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'message': 'Assessment not found.'}), 404

    # Check if the student has already started this assessment
    existing_attempt = AttemptAssessment.query.filter_by(assessment_id=assessment.id, student_id=user_id).first()
    if existing_attempt:
        # return jsonify({'message': 'You have already started this assessment.'}), 400

        # fetch time attempt details
        return jsonify({
            'message': 'Assessment attempt started successfully.',
            'attempt_id': existing_attempt.id,
            'start_time': existing_attempt.started_at.isoformat()
        }), 201

    # Create a new attempt record
    attempt = AttemptAssessment(
        assessment_id=assessment.id,
        student_id=user_id,
        duration=assessment.duration  # in minutes
    )
    
    db.session.add(attempt)
    db.session.commit()

    return jsonify({
        'message': 'Assessment attempt started successfully.',
        'attempt_id': attempt.id,
        'start_time': attempt.started_at.isoformat()
    }), 201

@student_blueprint.route('/time_remaining/<assessment_id>', methods=['GET'])
def get_time_remaining(assessment_id):
    """
    Get the remaining time for an ongoing assessment attempt.
    """
    user_id = get_jwt_identity()

    attempt = AttemptAssessment.query.filter_by(assessment_id=assessment_id, student_id=user_id).first()
    if not attempt:
        return jsonify({'message': 'No ongoing assessment found.'}), 404

    # Calculate the time remaining
    time_elapsed = (datetime.utcnow() - attempt.started_at).total_seconds() / 60  # in minutes
    time_remaining = attempt.duration - time_elapsed

    # auto-submit if time is up and not yet submitted
    if time_remaining <= 0 and not attempt.submitted:
        # mark as submitted
        submission = Submission(
            assessment_id=assessment_id,
            student_id=user_id,
            graded=True
        )
        db.session.add(submission)
        db.session.commit()
        attempt.submitted = True
        db.session.commit()
        return jsonify({'message': 'Time is up. Assessment has been auto-submitted.'}), 200

    return jsonify({
        'assessment_id': assessment_id,
        'time_remaining': max(0, time_remaining)
    }), 200
