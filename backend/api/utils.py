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
from pypdf import PdfReader

load_dotenv()

# Allowed question type values expected from the UI
ALLOWED_QUESTION_TYPES = [
    "open-ended",
    "close-ended-multiple-single",
    "close-ended-multiple-multiple",
    "close-ended-bool",
    "close-ended-matching",
    "close-ended-ordering",
    "close-ended-drag-drop",
]

# OpenAI client setup
openai_api_key = os.getenv('OPENAI_API_KEY')
model_deployment_name = os.getenv('GPT_MODEL')
openai_endpoint = os.getenv('GPT_ENDPOINT')
model_deployment_name_image = os.getenv('GPT_IMAGE_MODEL')

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_endpoint
)


def _normalize_question_types(raw_types):
    """Return a cleaned list constrained to ALLOWED_QUESTION_TYPES."""
    qtypes = raw_types if isinstance(raw_types, (list, tuple)) else [raw_types]
    cleaned = []
    for qt in qtypes:
        if qt is None:
            continue
        s = str(qt).strip()
        if s and s in ALLOWED_QUESTION_TYPES:
            cleaned.append(s)
    return cleaned or ["open-ended"]


def ai_create_assessment(data):
    '''
    Create a comprehensive assessment using AI based on the provided parameters.
    This function constructs a system prompt and a user prompt, then calls the Azure OpenAI API
    to generate the assessment. The response is expected to be in JSON format with a specific structure.
    '''
    # System prompt: set the role and expectations
    system_prompt = (
        "You are an expert instructional designer and university lecturer. "
        "Create rigorous, engaging, and well-structured assessments aligned to university-level standards. "
        "Follow Bloom's taxonomy when mapping cognitive levels, and produce clear marking rubrics for each question. "
        "Be concise and strictly follow the JSON schema provided in the user message. "
        "Do not include any explanations, commentary, or extra text outside of the requested JSON."
    )

    # Determine question type phrasing (supports list of values from the UI)
    question_types = _normalize_question_types(data.get('questions_type', []))

    if len(question_types) == 1:
        question_type_label = question_types[0]
    else:
        question_type_label = ", ".join(question_types)

    # User prompt: supply all parameters and ask for JSON
    user_prompt = (
        f"Create a {data['difficulty']} level assessment for the unit '{data['unit_name']}' "
        f"on the topic '{data['topic']}'. "
        f"Include the following description/context: {data['description']}. "
        f"Use Bloom's taxonomy level '{data['blooms_level']}', "
        f"with {data['number_of_questions']} questions using types: {question_type_label}, totaling {data['total_marks']} marks.\n"
        "Structure the output strictly as a JSON array of question objects with EXACTLY this shape (no extra fields):\n"
        """[
            {
                "text": "Question text",
                "marks": integer,
                "type": "open-ended" | "close-ended-multiple-single" | "close-ended-multiple-multiple" | "close-ended-bool" | "close-ended-matching" | "close-ended-ordering" | "close-ended-drag-drop",
                "blooms_level": "cognitive level",
                "rubric": "Detailed grading rubric",
                "correct_answer": ["..."],
                "choices": null OR array
            }
        ]
        Rules for choices:
        - open-ended: choices must be null
        - close-ended-bool: choices = ["True","False"] (or similar)
        - close-ended-multiple-single: choices is a flat array of options; exactly one correct_answer
        - close-ended-multiple-multiple: choices is a flat array of options; correct_answer is an array of one or more correct options
        - close-ended-ordering: choices is a flat array to be ordered; correct_answer reflects the correct order
        - close-ended-matching: choices is an array of pairs or two parallel arrays (sources and targets) that clearly encode matching
        - close-ended-drag-drop: choices is an array representing draggable items and targets (keep concise and machine-readable)
        """
        "Include a clear marking scheme and rubric for each question. "
        f"Every question's type must be exactly one of: {', '.join(ALLOWED_QUESTION_TYPES)}. "
        "Respond ONLY with the JSON array; do not include any additional commentary or explanation."
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
        reader = PdfReader(pdf_file)
        text = []
        for page in reader.pages:
            text.append(page.extract_text() or "")
    document_text = "\n".join(text)

    system_prompt = (
        "You are an expert instructional designer and university lecturer. "
        "Create rigorous, engaging, and well-structured assessments aligned to university-level standards. "
        "Follow Bloom's taxonomy when mapping cognitive levels, and produce clear marking rubrics for each question. "
        "Be concise and strictly follow the JSON schema provided in the user message. "
        "Do not include any explanations, commentary, or extra text outside of the requested JSON."
    )

    question_types = _normalize_question_types(data.get('questions_type', []))

    if len(question_types) == 1:
        question_type_label = question_types[0]
    else:
        question_type_label = ", ".join(question_types)

    user_prompt = (
        f"Using the following document content, generate a {data['difficulty']} level assessment for the unit '{data['unit_name']}' "
        f"on the topic '{data['topic']}'. Context:\n{document_text}\n"
        f"Include the following description/context: {data['description']}. "
        f"Use Bloom's taxonomy level '{data['blooms_level']}', with {data['number_of_questions']} questions using types: {question_type_label}, totaling {data['total_marks']} marks. "
        "Structure the output strictly as a JSON array of question objects with EXACTLY this shape (no extra fields):\n"
        """[
            {
                "text": "Question text",
                "marks": integer,
                "type": "open-ended" | "close-ended-multiple-single" | "close-ended-multiple-multiple" | "close-ended-bool" | "close-ended-matching" | "close-ended-ordering" | "close-ended-drag-drop",
                "blooms_level": "cognitive level",
                "rubric": "Detailed grading rubric",
                "correct_answer": ["..."],
                "choices": null OR array
            }
        ]
        Rules for choices:
        - open-ended: choices must be null
        - close-ended-bool: choices = ["True","False"] (or similar)
        - close-ended-multiple-single: choices is a flat array of options; exactly one correct_answer
        - close-ended-multiple-multiple: choices is a flat array of options; correct_answer is an array of one or more correct options
        - close-ended-ordering: choices is a flat array to be ordered; correct_answer reflects the correct order
        - close-ended-matching: choices is an array of pairs or two parallel arrays (sources and targets) that clearly encode matching
        - close-ended-drag-drop: choices is an array representing draggable items and targets (keep concise and machine-readable)
        """
        "Include a clear marking scheme and rubric for each question. "
        f"Every question's type must be exactly one of: {', '.join(ALLOWED_QUESTION_TYPES)}. "
        "Respond ONLY with the JSON array; do not include any additional commentary or explanation."
    )

    response = client.chat.completions.create(
        model=model_deployment_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        max_tokens=32000,
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
