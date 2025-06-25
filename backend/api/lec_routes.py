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

from openai import AzureOpenAI
import requests

from api import db
from api.models import Assessment, Question, Submission, Answer, Result, TotalMarks
from api.models import Course, Unit, Notes

import os
import uuid
import json
import re
import base64

load_dotenv()
lec_blueprint = Blueprint('lec', __name__)

# Azure OpenAI client setup
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

'''
Before every request to verify if the user is a lecturer
'''
@lec_blueprint.before_request
@jwt_required()
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
    claims = get_jwt()
    if claims.get('role') != 'lecturer':
        return jsonify({'message': 'Access forbidden: Only lecturers can generate assessments.'}), 403

    data = request.json or {}
    required_fields = [
        'title', 'description','week', 'type', 'unit_id', 'course_id',
        'questions_type', 'topic', 'total_marks', 'unit_name',
        'difficulty', 'number_of_questions', 'deadline', 'duration', 'blooms_level'
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
        f"Generate a {data['difficulty']} level {data['type']} blooms level {data['blooms_level']} assessment for the topic '{data['topic']}' "
        f"in unit '{data['unit_name']}' with {data['number_of_questions']} "
        f"{question_type_text} questions totaling {data['total_marks']} marks. "
        "Return the assessment response in JSON format with the following structure:\n"
        """{
            "question_n": {
                "text": "Question text here",
                "marks": 5,
                "type": "%s",
                "rubric": "Rubric for grading the question",
                "correct_answer": "Correct answer or explanation here",
                "choices": ["Choice 1", "Choice 2", "Choice 3"]  # Only for close-ended questions
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
    
    print(f"Cleaned assessment: {generated}")

    try:
        payload = json.loads(generated)
    except json.JSONDecodeError:
        return jsonify({'message': 'AI did not return valid JSON.'}), 500
    
    print(f"Payload: {payload}")

    assessment = Assessment(
        creator_id       = user_id,
        title            = data['title'],
        week             = data['week'],  # Default to week 1 if not provided
        description      = data['description'],
        questions_type   = data['questions_type'],
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
                correct_answer= q_obj.get('correct_answer', ''),
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
                correct_answer= q_obj.get('correct_answer', '')
            )
        db.session.add(question)

    db.session.commit()

    return jsonify({
        'message'       : 'Assessment generated successfully.',
        'assessment_id' : assessment.id,
        'title'         : assessment.title
    }), 201
