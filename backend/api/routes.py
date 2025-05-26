from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# from openai import OpenAI
import requests

from api import db
from api.models import Assessment, Question, Submission, Answer, Result, TotalMarks

import os
import uuid
import json
import re
import base64

load_dotenv()
bd_blueprint = Blueprint('bd', __name__)

# api_token = os.getenv('LLAMA_API_KEY')
nvidia_key = os.getenv('NVIDIA_API_KEY')

# client = OpenAI(
#     api_key=api_token,
#     base_url="https://api.llmapi.com/"
# )

# health check endpoint
@bd_blueprint.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'API is running'}), 200

# generate assessment using llama-3.2-90b-vision-instruct AI
@bd_blueprint.route('/ai/generate-assessments', methods=['POST'])
@jwt_required()
def generate_assessments():
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims['role'] != 'lecturer':
        return jsonify({'message': 'Access forbidden: Only lecturers can generate assessments.'}), 403
    
    data = request.json
    if not data or 'title' not in data or 'description' not in data or 'type' not in data or 'unit' not in data or 'questions_type'\
        not in data or 'topic' not in data or 'total_marks' not in data or 'difficulty' not in data or 'number_of_questions' not in data:
        return jsonify({'message': 'Invalid input data.'}), 400
    
    question_type_text = "open-ended (requiring written explanations)" if data['questions_type'] == "open-ended" else "close-ended (e.g. multiple choice, true/false)"

    prompt = (
        f"Generate a {data['difficulty']} level {data['type']} for the topic '{data['topic']}' in unit '{data['unit']}' "
        f"with {data['number_of_questions']} {question_type_text} questions totaling {data['total_marks']} marks. "
        f"""Return the assessment response in JSON format with the following structure:\n
        {{
            "question_n": {{
                "text": "Question text here",
                "marks": 5,
                "type": "{data['questions_type']}",
                "rubric": "Rubric for grading the question",
                "correct_answer": "Correct answer or explanation here"
            }}
        }}"""
        f"Each question should include a marking scheme and a rubric for grading."
        f" The assessment should be suitable for a {data['unit']} course and should be engaging and challenging for students."
    )

    headers = {
        "Authorization": f"Bearer {nvidia_key}",
        "Accept": "application/json"
    }
    payload = {
        "model": "meta/llama-3.2-90b-vision-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.7,
        "top_p": 1.0,
        "stream": False
    }
    res = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload)

    # check errors in the response
    if res.status_code != 200:
        return jsonify({'message': 'Error generating assessment: ' + res.text}), 500
    if 'choices' not in res.json() or len(res.json()['choices']) == 0:
        return jsonify({'message': 'No response from AI model.'}), 500
    if 'message' not in res.json()['choices'][0] or 'content' not in res.json()['choices'][0]['message']:
        return jsonify({'message': 'Invalid response format from AI model.'}), 500
    
    # Extract the generated content
    generated = res.json()['choices'][0]['message']['content']

    # Create the assessment in the database
    assessment = Assessment(
        creator_id=user_id,
        title=data['title'],
        description=data['description'],
        questions_type=data['questions_type'],
        type=data['type'],
        unit_id=data['unit'],
        course_id=data.get('course_id'),
        topic=data['topic'],
        total_marks=data['total_marks'],
        difficulty=data['difficulty'],
        number_of_questions=data['number_of_questions']
    )
    db.session.add(assessment)
    db.session.flush()

    # Parse the generated questions and add them to the assessment
    questions = re.findall(r'"question_(\d+)":\s*{([^}]+)}', generated)
    for q_num, q_data in questions:
        q_data = dict(re.findall(r'"(\w+)":\s*"([^"]+)"', q_data))
        question = Question(
            assessment_id=assessment.id,
            text=q_data.get('text', ''),
            marks=float(q_data.get('marks', 0)),
            type=q_data.get('type', 'open-ended'),
            rubric=q_data.get('rubric', ''),
            correct_answer=q_data.get('correct_answer', '')
        )
        db.session.add(question)

    # TODO: Add email notification to the lecturer about the generated assessment for review

    db.session.commit()
    return jsonify({
        'message': 'Assessment generated successfully.',
        'assessment_id': assessment.id,
        'title': assessment.title
    }), 201

# lecturer endpoint to verify an assessment generated by AI
@bd_blueprint.route('/lecturer/assessments/<assessment_id>/verify', methods=['GET'])
@jwt_required()
def verify_assessment(assessment_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims['role'] != 'lecturer':
        return jsonify({'message': 'Access forbidden: Only lecturers can verify assessments.'}), 403
    
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

# endpoint for lecturers to create an assessment
@bd_blueprint.route('/lecturer/generate-assessments', methods=['POST'])
@jwt_required()
def create_assessment():
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims['role'] != 'lecturer':
        return jsonify({'message': 'Access forbidden: Only lecturers can create assessments.'}), 403
    
    data = request.json
    if not data or 'title' not in data or 'description' not in data or 'type' not in data or 'unit' not in data or 'questions_type'\
        not in data or 'topic' not in data or 'total_marks' not in data or 'difficulty' not in data or 'number_of_questions' not in data:
        return jsonify({'message': 'Invalid input data.'}), 400
    
    assessment = Assessment(
        creator_id=user_id,
        title=data['title'],
        description=data['description'],
        questions_type=data['questions_type'],
        type=data['type'],
        unit_id=data['unit'],
        course_id=data.get('course_id'),
        topic=data['topic'],
        total_marks=data['total_marks'],
        difficulty=data['difficulty'],
        number_of_questions=data['number_of_questions'],
        verified=True  # Default to not verified
    )
    
    db.session.add(assessment)
    db.session.commit()

    # TODO: Add email notification to the target students about the created assessment
    
    return jsonify({
        'message': 'Assessment created successfully.',
        'assessment_id': assessment.id,
        'title': assessment.title
    }), 201

# endpoint for lecturers to add questions to an assessment
@bd_blueprint.route('/lecturer/assessments/<assessment_id>/questions', methods=['POST'])
@jwt_required()
def add_question_to_assessment(assessment_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims['role'] != 'lecturer':
        return jsonify({'message': 'Access forbidden: Only lecturers can add questions.'}), 403
    
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'message': 'Assessment not found.'}), 404
    
    data = request.json
    if not data or 'text' not in data or 'marks' not in data or 'type' not in data or 'rubric' not in data or 'correct_answer' not in data:
        return jsonify({'message': 'Invalid input data.'}), 400
    
    question = Question(
        assessment_id=assessment.id,
        text=data['text'],
        marks=float(data['marks']),
        type=data['type'],
        rubric=data['rubric'],
        correct_answer=data['correct_answer']
    )
    
    db.session.add(question)
    db.session.commit()
    
    return jsonify({
        'message': 'Question added successfully.',
        'question_id': question.id
    }), 201

# endpoint for lecturers to get all assessments for created by him/her
@bd_blueprint.route('/lecturer/assessments', methods=['GET'])
@jwt_required()
def get_lecturer_assessments():
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims['role'] != 'lecturer':
        return jsonify({'message': 'Access forbidden: Only lecturers can view their assessments.'}), 403
    
    assessments = Assessment.query.filter_by(creator_id=user_id).all()
    return jsonify([assessment.to_dict() for assessment in assessments]), 200

# endpoint for students to get all assessments available to them (status: open(if not started), in-progress, completed) -> filter by course_id
@bd_blueprint.route('/student/<course_id>/assessments', methods=['GET'])
@jwt_required()
def get_student_assessments(course_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims['role'] != 'student':
        return jsonify({'message': 'Access forbidden: Only students can view assessments.'}), 403
    
    # filter only verified == True
    if course_id:
        assessments = Assessment.query.filter_by(course_id=course_id, verified=True).all()
    else:
        assessments = Assessment.query.filter_by(verified=True).all()

    if not assessments:
        return jsonify({'message': 'No assessments found for this course.'}), 404
    
    '''status mapping: start(if assessment not in the student's submissions), 
    in-progress(if assessment is not in the student's submissions but some questions are answered(in the Answer table)),
    submitted(if assessment is in the student's submissions but not graded),
    completed(if assessment is in the student's submissions and graded)
    '''
    for assessment in assessments:
        submission = Submission.query.filter_by(assessment_id=assessment.id, student_id=user_id).first()
        if submission:
            assessment.status = 'submitted' if not submission.graded else 'completed'
        else:
            answered_questions = Answer.query.filter_by(assessment_id=assessment.id, student_id=user_id).count()
            assessment.status = 'in-progress' if answered_questions > 0 else 'open'
    assessments_dicts = []
    for assessment in assessments:
        a_dict = assessment.to_dict()
        a_dict['status'] = assessment.status  # Copy status from model attribute to the dict
        assessments_dicts.append(a_dict)

    return jsonify(assessments_dicts), 200

# endpoint for students & lecturers to get questions of an assessment
@bd_blueprint.route('/assessments/<assessment_id>/questions', methods=['GET'])
@jwt_required()
def get_assessment_questions(assessment_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'message': 'Assessment not found.'}), 404
    
    # Check if the user has access to the assessment
    if claims['role'] != 'lecturer' or claims['role'] == 'student' and assessment.course_id not in claims.get('courses', []):
        return jsonify({'message': 'Access forbidden: You are not enrolled in this course.'}), 403
    
    questions = Question.query.filter_by(assessment_id=assessment.id).all()
    return jsonify([question.to_dict() for question in questions]), 200

@bd_blueprint.route('/assessments/<assessment_id>/questions/<question_id>/answer', methods=['POST'])
@jwt_required()
def submit_answer(assessment_id, question_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims['role'] != 'student':
        return jsonify({'message': 'Access forbidden: Only students can submit answers.'}), 403

    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        return jsonify({'message': 'Assessment not found.'}), 404

    question = Question.query.get(question_id)
    if not question or question.assessment_id != assessment.id:
        return jsonify({'message': 'Question not found in this assessment.'}), 404

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
        upload_dir  = current_app.config['UPLOAD_FOLDER']
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
            marks=question.marks
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


def grade_image_answer(filename, question_text, rubric, correct_answer, marks):
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, filename)

        # print(f"Grading image answer: {file_path}") # Debugging line

        with open(file_path, 'rb') as img_file:
            raw = img_file.read()
        image_base64 = base64.b64encode(raw).decode('ascii')
        assert len(image_base64) < 1_000_000, "Image size exceeds the 1MB limit"

        # print(f"Image base64 length: {len(image_base64)}") # Debugging line

        prompt = (
            f"Grade the following image answer for the question: {question_text}\n"
            f"Rubric: {rubric}\nCorrect Answer: {correct_answer}\nMarks: {marks}\n\n"
            "Provide a detailed explanation of the grading and the score out of the total marks.\n"
            "Return strictly JSON:\n"
            "{ \"score\": <score_awarded>, \"feedback\": \"...\" }"
        )
        payload = {
            "model": "meta/llama-3.2-90b-vision-instruct",
            "messages": [
                {"role": "user", "content": prompt + f"\n<img src='data:image/png;base64,{image_base64}' />"}
            ],
            "max_tokens": 512,
            "temperature": 0.7
        }

        res = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {nvidia_key}",
                "Accept": "application/json"
            },
            json=payload
        )

        # print(f"Response status code: {res.status_code}") # Debugging line
        # print(f"Response content: {res.text}") # Debugging line
        res.raise_for_status()

        content = res.json()['choices'][0]['message']['content']
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in model response.")
        grading_result = json.loads(match.group(0))

        score = float(grading_result.get('score', -1))
        if score < 0 or score > marks:
            raise ValueError(f"Score {score} out of bounds (0–{marks}).")
        
        print(f"Grading result: {grading_result}") # Debugging line

        return grading_result, 200

    except AssertionError as ae:
        return {"error": "validation_error", "detail": str(ae)}, 400
    except requests.HTTPError as he:
        current_app.logger.error("Image grading failed: %s", he.response.text)
        return {"error": "grading_service_error", "detail": he.response.text}, he.response.status_code
    except Exception as e:
        current_app.logger.exception("Unexpected error grading image")
        return {"error": "internal_error", "detail": str(e)}, 500


def grade_text_answer(text_answer, question_text, rubric, correct_answer, marks):
    system_prompt = "You are a university examiner. Grade student responses using the rubric provided. Give a numerical score and a short, helpful feedback."

    user_prompt = (
        f"Grade the following text answer for the question: {question_text}\n"
        f"Rubric: {rubric}\nCorrect Answer: {correct_answer}\nMarks: {marks}\n\n"
        f"Answer: {text_answer}\n\n"
        "Provide a detailed explanation of the grading and the score out of the total marks.\n"
        """Return the response in strict JSON format:
        {
            "score": <score_awarded>,
            "feedback": "Explanation of how the answer matches the rubric."
        }"""
    )

    headers = {
        "Authorization": f"Bearer {nvidia_key}",
        "Accept": "application/json"
    }

    payload = {
        "model": "meta/llama-3.2-90b-vision-instruct",
        "messages": [
            {
                "role": "user",
                "content": f"{system_prompt}\n\n{user_prompt}"
            }
        ],
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 1.0,
        "stream": False
    }

    try:
        res = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload)
        res.raise_for_status()

        content = res.json()['choices'][0]['message']['content']
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in model response.")
        grading_result = json.loads(match.group(0))

        score = float(grading_result.get('score', -1))
        if score < 0 or score > marks:
            raise ValueError(f"Score {score} out of bounds (0–{marks}).")

        return grading_result, 200
    except AssertionError as ae:
        return {"error": "validation_error", "detail": str(ae)}, 400
    except requests.HTTPError as he:
        current_app.logger.error("Text grading failed: %s", he.response.text)
        return {"error": "grading_service_error", "detail": he.response.text}, he.response.status_code


# final submission endpoint for students to submit an assessment (populate the Submission and total_marks table)
@bd_blueprint.route('/assessments/<assessment_id>/submit', methods=['POST'])
@jwt_required()
def finalize(assessment_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims['role'] != 'student':
        return jsonify({'message': 'Access forbidden: Only students can submit assessments.'}), 403

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

    # Calculate total marks for the submission
    total_marks = db.session.query(db.func.sum(Result.score['marks_awarded'])).filter_by(submission_id=submission.id).scalar() or 0.0

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
