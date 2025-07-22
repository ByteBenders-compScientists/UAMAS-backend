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
import os
import json
import re

import io
import PyPDF2

load_dotenv()

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
    to generate the assessment. The response is expected to be in JSON format with a specific structure.
    '''
    # System prompt: set the role and expectations
    system_prompt = (
        "You are an expert instructional designer and university lecturer. "
        "Your task is to create a rigorous, engaging, and well-structured assessment following Bloom's taxonomy. "
        "The assessment must align with the specified unit learning outcomes and include detailed marking rubrics."
    )

    # Determine question type phrasing
    if data['questions_type'] == "open-ended":
        question_type_label = "open-ended (written response)"
    elif data['questions_type'] == "close-ended" and data.get('close_ended_type'):
        question_type_label = f"close-ended ({data['close_ended_type']})"
    else:
        question_type_label = "close-ended multiple choice (single best answer)"

    # User prompt: supply all parameters and ask for JSON
    user_prompt = (
        f"Create a {data['difficulty']} level assessment for the unit '{data['unit_name']}' "
        f"on the topic '{data['topic']}'. "
        f"Include the following description/context: {data['description']}. "
        f"Use Bloom's taxonomy level '{data['blooms_level']}', "
        f"with {data['number_of_questions']} {question_type_label} questions totaling {data['total_marks']} marks.\n"
        "Structure the output strictly as JSON with this template for each question key (e.g., 'question_1'): \n"
        """[
            {
                "text": "Question text",
                "marks": integer,
                "type": "open-ended" or "close-ended",
                "blooms_level": "cognitive level",
                "rubric": "Detailed grading rubric",
                "correct_answer": ["..."],  # list of correct response(s)
                "choices": ["Choice A", "Choice B", "Choice C"]  # only for close-ended
            },
        ...
        ]"""
        "\nInclude a clear marking scheme and rubric for each question. "
        "Respond ONLY with the JSON object; do not include any additional commentary or explanation."
    )

    # Call the LLM
    res = client.chat.completions.create(
        model=model_deployment_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        max_tokens=10000,
        temperature=0.7,
        top_p=1.0,
        stream=False
    )

    return res


def ai_create_assessment_from_pdf(data, pdf_path):
    '''
    Create an AI-generated assessment based on the content of a PDF document, manually extracting text and using GPT-4.1.
    '''
    # Read and extract text from the PDF file
    with open(pdf_path, 'rb') as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        text = []
        for page in reader.pages:
            text.append(page.extract_text() or "")
    document_text = "\n".join(text)

    # Construct prompts
    system_prompt = (
        "You are an expert instructional designer and university lecturer. "
        "Your task is to create a rigorous, engaging, and well-structured assessment following Bloom's taxonomy. "
        "The assessment must align with the specified unit learning outcomes and include detailed marking rubrics."
    )

    if data['questions_type'] == "open-ended":
        question_type_label = "open-ended (written response)"
    elif data['questions_type'] == "close-ended" and data.get('close_ended_type'):
        question_type_label = f"close-ended ({data['close_ended_type']})"
    else:
        question_type_label = "close-ended multiple choice (single best answer)"

    user_prompt = (
        f"Using the following document content, generate a {data['difficulty']} level assessment for the unit '{data['unit_name']}' "
        f"on the topic '{data['topic']}'. Context:\n{document_text}\n"
        f"Include the following description/context: {data['description']}. "
        f"Use Bloom's taxonomy level '{data['blooms_level']}', with {data['number_of_questions']} {question_type_label} questions totaling {data['total_marks']} marks. "
        "Structure the output strictly as JSON as specified; include detailed rubrics and correct answers.\n"
        """[
            {
                "text": "Question text",
                "marks": integer,
                "type": "open-ended" or "close-ended",
                "blooms_level": "cognitive level",
                "rubric": "Detailed grading rubric",
                "correct_answer": ["..."],  # list of correct response(s)
                "choices": ["Choice A", "Choice B", "Choice C"]  # only for close-ended
            },
        ...
        ]"""
        "\nInclude a clear marking scheme and rubric for each question. "
        "Respond ONLY with the JSON object; do not include any additional commentary or explanation."
    )

    response = client.chat.completions.create(
        model=model_deployment_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        max_tokens=50000,
        temperature=0.7,
        top_p=1.0,
        stream=False
    )

    return response


def grade_image_answer(filename, question_text, rubric, correct_answer, marks, image_url):
    """    
    Grade an image answer using AI.
    This function reads the image file, encodes it in base64, and constructs a prompt
    for the AI model to grade the image answer based on the provided question, rubric, and correct answer.
    It returns a JSON response with the score and feedback.
    """
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
