"""
Contain Utility functions for the UAMAS backend
Created by: https://github.com/ByteBenders-compScientists/UAMAS-backend
Actions:
- Create a comprehensive assessment based on user input
- Grade image answers using AI
- Grade text answers using AI
"""

from dotenv import load_dotenv
from openai import OpenAI
# from openai import AzureOpenAI
import requests
import os
import json
import re
import base64

load_dotenv()

# Azure OpenAI client setup
# endpoint = os.getenv('OPENAI_API_KEY_ENDPOINT')
# model_deployment_name = os.getenv('MODEL_DEPLOYMENT_NAME')
# subscription_key1 = os.getenv('OPENAI_API_KEY1')
# subscription_key2 = os.getenv('OPENAI_API_KEY2')
# api_version = os.getenv('API_VERSION')

# client = AzureOpenAI(
#     api_version=api_version,
#     azure_endpoint=endpoint,
#     api_key=subscription_key1
# )

# OpenAI client setup
openai_api_key = os.getenv('OPENAI_API_KEY')
model_deployment_name = os.getenv('GPT_MODEL')
openai_endpoint = os.getenv('GPT_ENDPOINT')
model_deployment_name_image = os.getenv('GPT_IMAGE_MODEL')

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_endpoint
)


def ai_create_assessment(data):
    '''
    Create a comprehensive assessment using AI based on the provided parameters.
    This function constructs a system prompt and a user prompt, then calls the Azure OpenAI API
    to generate the assessment. The response is expected to be in JSON format with a specific structure
    '''
    # Build the system + user prompts exactly as before…
    system_prompt = (
        "You are an expert in creating university-level assessments. "
        "Generate a comprehensive assessment based on the provided parameters. "
        "Ensure the assessment is engaging, challenging, and suitable for the specified unit and topic."
    )

    question_type_text = (
        "open-ended (requiring written explanations)"
        if data['questions_type'] == "open-ended"
        else f"close-ended ({data['close_ended_type']})"
        if data['questions_type'] == "close-ended" and data['close_ended_type'] is not None
        else "close-ended multiple choice with one answer"
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
                "correct_answer": ["Correct answer text here"], # list of correct answer/s
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

    return res


def grade_image_answer(filename, question_text, rubric, correct_answer, marks, image_url):
    """    
    Grade an image answer using AI.
    This function reads the image file, encodes it in base64, and constructs a prompt
    for the AI model to grade the image answer based on the provided question, rubric, and correct answer.
    It returns a JSON response with the score and feedback.
    """
    # file_path = os.path.join(upload_folder, filename)

    # with open(file_path, 'rb') as img_file:
    #     img_bytes = img_file.read()

    # image_tag = f"<img src='data:image/png;base64,{base64.b64encode(img_bytes).decode()}' />"
    image_url = image_url

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
        model=model_deployment_name_image,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",
             "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
             ]
            }
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
    """
    Grade a text answer using AI.
    This function constructs a prompt for the AI model to grade the text answer based on the provided
    question, rubric, and correct answer. It returns a JSON response with the score and feedback.
    """

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
