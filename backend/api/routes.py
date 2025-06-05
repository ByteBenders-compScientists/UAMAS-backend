from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from openai import AzureOpenAI
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

endpoint = os.getenv('OPENAI_API_KEY_ENDPOINT')
model_deployment_name = os.getenv('MODEL_DEPLOYMENT_NAME')
subscription_key1 = os.getenv('OPENAI_API_KEY1')
subscription_key2 = os.getenv('OPENAI_API_KEY2')
api_version = os.getenv('API_VERSION')

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key1
)

# health check endpoint
@bd_blueprint.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'API is running'}), 200

# endpoint for lecturers to generate assessments using AI
@bd_blueprint.route('/ai/generate-assessments', methods=['POST'])
@jwt_required(locations= ['cookies', 'headers'])
def generate_assessments():
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims.get('role') != 'lecturer':
        return jsonify({'message': 'Access forbidden: Only lecturers can generate assessments.'}), 403

    data = request.json or {}
    required_fields = [
        'title', 'description', 'type', 'unit_id', 'course_id',
        'questions_type', 'topic', 'total_marks', 'unit_name',
        'difficulty', 'number_of_questions'
    ]
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Invalid input data.'}), 400

    # Build the system + user prompts exactly as before…
    system_prompt = (
        "You are an expert in creating university-level assessments. "
        "Generate a comprehensive assessment based on the provided parameters. "
        "Ensure the assessment is engaging, challenging, and suitable for the specified unit and topic."
    )

    question_type_text = (
        "open-ended (requiring written explanations)"
        if data['questions_type'] == "open-ended"
        else "close-ended (e.g. multiple choice, true/false)"
    )

    user_prompt = (
        f"Generate a {data['difficulty']} level {data['type']} for the topic '{data['topic']}' "
        f"in unit '{data['unit_name']}' with {data['number_of_questions']} "
        f"{question_type_text} questions totaling {data['total_marks']} marks. "
        "Return the assessment response in JSON format with the following structure:\n"
        """{
            "question_n": {
                "text": "Question text here",
                "marks": 5,
                "type": "%s",
                "rubric": "Rubric for grading the question",
                "correct_answer": "Correct answer or explanation here"
            }
        }""" % data['questions_type'] +
        " Each question should include a marking scheme and a rubric for grading the question. "
        "The assessment should be suitable for a {unit} course and should be engaging and challenging."
    )

    # Call the LLM
    res = client.chat.completions.create(
        model = model_deployment_name,
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        max_tokens = 4096,
        temperature = 1.0,
        top_p = 1.0,
        stream = False
    )

    if not hasattr(res, "choices") or len(res.choices) == 0:
        return jsonify({'message': 'No response from AI model.'}), 500

    first_choice = res.choices[0]
    if not (hasattr(first_choice, "message") and hasattr(first_choice.message, "content")):
        return jsonify({'message': 'Invalid response format from AI model.'}), 500

    generated = first_choice.message.content

    # print(f"Generated assessment: {generated}")
    # remove markdown ```json``` around the JSON response
    generated = re.sub(r'```json\s*', '', generated)
    generated = re.sub(r'\s*```', '', generated)
    
    # print(f"Cleaned assessment: {generated}")

    try:
        payload = json.loads(generated)
    except json.JSONDecodeError:
        return jsonify({'message': 'AI did not return valid JSON.'}), 500

    assessment = Assessment(
        creator_id       = user_id,
        title            = data['title'],
        description      = data['description'],
        questions_type   = data['questions_type'],
        type             = data['type'],
        unit_id          = data['unit_id'],
        course_id        = data.get('course_id'),
        topic            = data['topic'],
        total_marks      = data['total_marks'],
        difficulty       = data['difficulty'],
        number_of_questions = data['number_of_questions']
    )
    db.session.add(assessment)
    db.session.flush()   # so that assessment.id is set

    for key, q_obj in payload.items():
        # key is something like "question_1", "question_2", …
        question = Question(
            assessment_id = assessment.id,
            text          = q_obj.get('text', ''),
            marks         = float(q_obj.get('marks', 0)),
            type          = q_obj.get('type', 'open-ended'),
            rubric        = q_obj.get('rubric', ''),
            correct_answer= q_obj.get('correct_answer', '')
        )
        db.session.add(question)

    db.session.commit()

    return jsonify({
        'message'       : 'Assessment generated successfully.',
        'assessment_id' : assessment.id,
        'title'         : assessment.title
    }), 201

# lecturer endpoint to verify an assessment generated by AI
@bd_blueprint.route('/lecturer/assessments/<assessment_id>/verify', methods=['GET'])
@jwt_required(locations=['cookies', 'headers'])
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
@jwt_required(locations= ['cookies', 'headers'])
def create_assessment():
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims['role'] != 'lecturer':
        return jsonify({'message': 'Access forbidden: Only lecturers can create assessments.'}), 403
    
    data = request.json
    if not data or 'title' not in data or 'description' not in data or 'type' not in data or 'unit_id' not in data or 'questions_type'\
        not in data or 'topic' not in data or 'total_marks' not in data or 'difficulty' not in data or 'number_of_questions' not in data:
        return jsonify({'message': 'Invalid input data.'}), 400
    
    assessment = Assessment(
        creator_id=user_id,
        title=data['title'],
        description=data['description'],
        questions_type=data['questions_type'],
        type=data['type'],
        unit_id=data['unit_id'],
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
@jwt_required(locations=['cookies','headers'])
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
@jwt_required(locations=['cookies', 'headers'])
def get_lecturer_assessments():
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims['role'] != 'lecturer':
        return jsonify({'message': 'Access forbidden: Only lecturers can view their assessments.'}), 403
    
    assessments = Assessment.query.filter_by(creator_id=user_id).all()
    return jsonify([assessment.to_dict() for assessment in assessments]), 200

# endpoint for students to get all assessments available to them (status: open(if not started), in-progress, completed) -> filter by course_id
@bd_blueprint.route('/student/<course_id>/assessments', methods=['GET'])
@jwt_required(locations=['cookies', 'headers'])
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
@jwt_required(locations=['cookies', 'headers'])
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
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)

    with open(file_path, 'rb') as img_file:
        img_bytes = img_file.read()

    image_tag = f"<img src='data:image/png;base64,{base64.b64encode(img_bytes).decode()}' />"

    system_prompt = (
        "You are an expert in grading university-level assessments. "
        "Grade student responses using the rubric provided. "
        "Give a numerical score and a short, helpful feedback."
    )

    user_prompt = (
        f"Grade the following image answer for the question: {question_text}\n"
        f"Rubric: {rubric}\nCorrect Answer: {correct_answer}\nMarks: {marks}\n\n"
        "Provide a detailed explanation of the grading and the score out of the total marks.\n"
        "Return strictly JSON:\n"
        "{ \"score\": <score_awarded>, \"feedback\": \"...\" }"
    )
    
    response = client.chat.completions.create(
        model=model_deployment_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_prompt}\n\n{image_tag}"}
        ],
        max_tokens=512,
        temperature=0.7,
        top_p=1.0,
        stream=False
    )

    if not hasattr(response, "choices") or len(response.choices) == 0:
        return {"error": "no_response", "detail": "No response from AI model."}, 500

    first_choice = response.choices[0]
    if not (hasattr(first_choice, "message") and hasattr(first_choice.message, "content")):
        return {"error": "invalid_response_format",
                "detail": "AI model did not return a properly formatted message."}, 500

    content = first_choice.message.content

    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'\s*```', '', content)

    match = re.search(r'\{.*\}', content, re.DOTALL)
    if not match:
        return {"error": "no_json_object",
                "detail": "No JSON object found in model response."}, 500

    json_text = match.group(0)
    try:
        grading_result = json.loads(json_text)
    except json.JSONDecodeError:
        return {"error": "invalid_json", "detail": "Unable to parse JSON from model response."}, 500

    score = grading_result.get('score')

    try:
        score = float(score)
    except (TypeError, ValueError):
        return {"error": "non_numeric_score",
                "detail": f"Score '{grading_result.get('score')}' is not a valid number."}, 400

    if score < 0 or score > marks:
        return {"error": "score_out_of_bounds",
                "detail": f"Score {score} out of bounds (0–{marks})."}, 400

    return grading_result, 200

def grade_text_answer(text_answer, question_text, rubric, correct_answer, marks):
    system_prompt = "You are a university examiner. Grade student responses using the rubric provided. Give a numerical score and a short, helpful feedback."

    user_prompt = (
        f"Grade the following text answer for the question:\n"
        f"{question_text}\n\n"
        f"Rubric: {rubric}\n"
        f"Correct Answer: {correct_answer}\n"
        f"Marks: {marks}\n\n"
        f"Answer: {text_answer}\n\n"
        "Provide a detailed explanation of the grading and the score out of the total marks. "
        """Return the response in strict JSON format:
        {
            "score": <score_awarded>,
            "feedback": "Explanation of how the answer matches the rubric."
        }"""
    )

    response = client.chat.completions.create(
        model=model_deployment_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        max_tokens=512,
        temperature=0.7,
        top_p=1.0,
        stream=False
    )

    if not hasattr(response, "choices") or len(response.choices) == 0:
        return {"error": "no_response", "detail": "No response from AI model."}, 500

    first_choice = response.choices[0]
    if not (hasattr(first_choice, "message") and hasattr(first_choice.message, "content")):
        return {"error": "invalid_response_format",
                "detail": "AI model did not return a properly formatted message."}, 500

    content = first_choice.message.content

    # print(f"Raw model response: {content}")

    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'\s*```', '', content)

    # print(f"Cleaned model response: {content}")

    match = re.search(r'\{.*\}', content, re.DOTALL)
    if not match:
        return {"error": "no_json_object",
                "detail": "No JSON object found in model response."}, 500
    
    # print(f"Extracted JSON: {match.group(0)}")

    json_text = match.group(0)

    # print(f"JSON text to parse: {json_text}")
    try:
        grading_result = json.loads(json_text)
    except json.JSONDecodeError:
        return {"error": "invalid_json", "detail": "Unable to parse JSON from model response."}, 500

    score = grading_result.get('score')

    # print(f"Parsed grading result: {grading_result}")
    try:
        score = float(score)
    except (TypeError, ValueError):
        return {"error": "non_numeric_score",
                "detail": f"Score '{grading_result.get('score')}' is not a valid number."}, 400

    if score < 0 or score > marks:
        return {"error": "score_out_of_bounds",
                "detail": f"Score {score} out of bounds (0–{marks})."}, 400

    return grading_result, 200

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
