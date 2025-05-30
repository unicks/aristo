from flask import Flask, request, jsonify, send_file
from utils import *
import json
import os
import google.generativeai as genai
import logging
import traceback
import sys
from glob import glob

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

app = Flask(__name__)
app.config['DEBUG'] = True

from utils import (
    extract_valid_json, save_table_to_latex, summarize_feedback, 
    extract_text_from_pdf, get_file_content, get_embedding, cosine_similarity
)
from moodle import download_all_submissions, DOWNLOAD_DIR as MOODLE_DOWNLOAD_DIR # Import Moodle utils
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import json
import os
import google.genai as genai
import PyPDF2
import numpy as np
from typing import Dict, List
import base64 # Added for Base64 encoding
from moodle import call_moodle_api, grade_assignment
from flask_cors import CORS
import re
import time
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.enums import TA_RIGHT
import arabic_reshaper
from bidi.algorithm import get_display
from xml.sax.saxutils import escape
import subprocess


app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = "AIzaSyCBd_uKeyycsilepxqsJRQ40AhrpoM5wTE"
client = genai.Client(api_key=GEMINI_API_KEY)

MAX_THREADS = 20
MAX_PROCESSES = 20
def compute_similarity(i, j, file_paths, file_embeddings):
    path1 = file_paths[i]
    path2 = file_paths[j]
    sim = cosine_similarity(
        file_embeddings[path1][0].values,
        file_embeddings[path2][0].values
    )
    return (path1, path2, sim)

def extract_and_embed(file_path, client):
    try:
        content = get_file_content(file_path)
        if not content:
            return None
        embedding = get_embedding(client, content)
        return (file_path, embedding) if embedding else None
    except Exception as e:
        print(f"Failed processing {file_path}: {e}")
        return None

def encode_file(path):
    try:
        with open(path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
            return {"filename": os.path.basename(path), "content_base64": encoded}
    except Exception as e:
        print(f"Failed encoding {path}: {e}")
        return None

@app.route('/choose', methods=['POST'])
def choose_varied_files():
    if request.method == "OPTIONS":
        return "", 200

    try:
        assignment_id = request.json.get('exercise_id')
        amount = int(request.json.get('amount', 2))

        if not assignment_id:
            return jsonify({"error": "exercise_id is required"}), 400
        if amount < 2:
            return jsonify({"error": "amount must be >= 2"}), 400

        assignment_id_str = str(assignment_id)
        assignment_dir = os.path.join(MOODLE_DOWNLOAD_DIR, assignment_id_str)

        # ✅ Skip downloading if files already exist
        if not os.path.exists(assignment_dir) or not any(
            f.endswith(('.lyx', '.pdf')) for f in os.listdir(assignment_dir)
        ):
            print(f"Downloading submissions for assignment {assignment_id_str}...")
            download_all_submissions(assignment_id_str)
        else:
            print(f"Using existing files in {assignment_dir}")

        files = [
            os.path.join(assignment_dir, f)
            for f in os.listdir(assignment_dir)
            if os.path.isfile(os.path.join(assignment_dir, f)) and f.endswith(('.lyx', '.pdf'))
        ]

        if len(files) < amount:
            return jsonify({"error": f"Need at least {amount} files. Found {len(files)}"}), 400

        # ✅ Step 1: Extract content + embeddings concurrently
        file_embeddings: Dict[str, List[float]] = {}
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = [executor.submit(extract_and_embed, f, client) for f in files]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    path, emb = result
                    file_embeddings[path] = emb

        if len(file_embeddings) < amount:
            return jsonify({"error": f"Only {len(file_embeddings)} files could be processed."}), 400

        file_paths = list(file_embeddings.keys())
        similarity_scores = {path: 0.0 for path in file_paths}

        # ✅ Step 2: Compute pairwise cosine similarity concurrently
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = [
                executor.submit(compute_similarity, i, j, file_paths, file_embeddings)
                for i in range(len(file_paths)) for j in range(i + 1, len(file_paths))
            ]
            for future in as_completed(futures):
                path1, path2, sim = future.result()
                similarity_scores[path1] += sim
                similarity_scores[path2] += sim

        # ✅ Step 3: Select least similar (lowest score)
        sorted_files = sorted(similarity_scores.items(), key=lambda x: x[1])
        selected_paths = [path for path, _ in sorted_files[:amount]]

        # ✅ Step 4: Encode files concurrently
        returned_files_data = []
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = [executor.submit(encode_file, p) for p in selected_paths]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    returned_files_data.append(result)

        if len(returned_files_data) < amount:
            return jsonify({"error": "Failed to prepare selected files."}), 500

        return jsonify({
            "files": returned_files_data,
            "message": f"Successfully returned {amount} most different files."
        })

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": f"Unexpected error: {e}"}), 500

@app.errorhandler(Exception)
def handle_error(error):
    error_msg = f"Unhandled error: {str(error)}"
    stack_trace = traceback.format_exc()
    logging.error(error_msg)
    logging.error(stack_trace)
    return jsonify({
        "error": error_msg,
        "stack_trace": stack_trace
    }), 500

@app.route('/', methods=['GET'])
def index():
    return "LaTeX grading backend is running."

def grade_pdf_file(pdf_path, context=""):
    # --- Step 1: Extract LaTeX-like content from the PDF ---
    try:
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            latex = ""
            for page in pdf_reader.pages:
                latex += page.extract_text() or ""
    except Exception as e:
        raise RuntimeError(f"PDF extraction error: {str(e)}")

    # --- Step 2: Compose prompt ---
    prompt = (
        "אתה בודק מתמטיקה שמעריך פתרונות PDF.\n"
        "בהתבסס על דוגמאות של בדיקות קודמות של מרצה (קונטקסט), "
        "בדוק את הפתרון הבא תוך ניסיון לחקות את סגנון ההערכה והציונים של המרצה.\n"
        "החזר JSON חוקי בלבד עם פירוט לפי השדות: שאלה, סעיף, ציון (0–100), הערה.\n"
        "הערות מפורטות מאוד שמסבירות מה הטעות.\n"
        "דוגמה: [{\"שאלה\": \"1\", \"סעיף\": \"א\", \"ציון\": 85, \"הערה\": \"ניסוח תקין, חסר נימוק\"}]\n\n"
        f"קונטקסט:\n{context}\n\n"
        f"פתרון לבדיקה:\n{latex}"
    )

    def extract_json_with_fallbacks(text):
        # Try primary extractor
        structured = extract_valid_json(text)
        if structured:
            return structured

        # Try Gemini fix attempt 1
        fix_prompt = (
            "הטקסט הבא נראה כמו פלט לא תקין של JSON. "
            "תקן אותו והחזר רק JSON חוקי. "
            "אין להוסיף הסברים או טקסט מחוץ למבנה JSON.\n\n"
            f"פלט לתיקון:\n{text}"
        )
        try:
            fix_response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=fix_prompt
            )
            fixed = extract_valid_json(fix_response.text.strip())
            if fixed:
                return fixed
        except:
            pass

        # Try regex as last resort
        try:
            json_candidate = re.search(r'\[.*\]', text, re.DOTALL)
            if json_candidate:
                return extract_valid_json(json_candidate.group())
        except:
            pass

        raise ValueError("Gemini response could not be parsed into valid JSON.")

    # --- Step 3: Query Gemini ---
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        json_text = response.text.strip()
        structured = extract_json_with_fallbacks(json_text)

        save_table_to_latex(structured)

        return {
            "feedback": structured,
        }

    except Exception as e:
        raise RuntimeError(f"Gemini error: {str(e)}")

def process_user_file(user_path, user_file, assignid, context_str):
    try:
        feedback = grade_pdf_file(user_path, context_str)
        summary = summarize_feedback(feedback)
        user_id = int(user_file.split(".")[0])
        grade_assignment(assignid, user_id, summary["final_grade"], feedback=feedback)
        return {
            "success": True,
            "user": user_file,
            "grade": summary["final_grade"],
            "comment": summary["master_comment"]
        }
    except Exception as e:
        return {
            "success": False,
            "user": user_file,
            "error": str(e)
        }

@app.route('/grade_all', methods=['POST'])
def grade_all():
    try:
        start_time = time.time()

        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400

        assignid = data.get('assignid')
        context = data.get('context', "")
        context_str = str(context) if context else ""

        if not assignid:
            return jsonify({"error": "Missing 'assignid' in request body"}), 400

        temp_dir = os.path.join('.temp', str(assignid))
        if not os.path.exists(temp_dir):
            return jsonify({"error": f"Directory '{temp_dir}' does not exist"}), 400

        users = [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]
        if not users:
            return jsonify({"error": "No user files found in .temp directory"}), 404

        results = []
        errors = []

        max_workers = min(len(users), 16)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            for user_file in users:
                graded_json_path = os.path.join(temp_dir, user_file.replace('.pdf', '.graded.json'))
                if os.path.exists(graded_json_path):
                    continue  # דלג אם כבר נבדק

                future = executor.submit(
                    process_user_file,
                    os.path.join(temp_dir, user_file),
                    user_file,
                    assignid,
                    context_str
                )
                futures.append(future)

            for future in as_completed(futures):
                result = future.result()
                if result["success"]:
                    results.append({
                        "user": result["user"],
                        "grade": result["grade"],
                        "comment": result["comment"]
                    })
                else:
                    errors.append({
                        "user": result["user"],
                        "error": result["error"]
                    })

        total_time = time.time() - start_time

        return jsonify({
            "message": f"Processed {len(results)} users for assignment {assignid} in {total_time:.2f} seconds",
            "graded": results,
            "errors": errors
        }), 200

    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500
         
@app.route('/courses', methods=['GET'])
def get_courses():
    try:
        # You may want to get userid from query params or session
        userid = request.args.get('userid', default=2, type=int)
        courses = call_moodle_api('core_enrol_get_users_courses', {'userid': userid})
        course_list = [
            {"id": course['id'], "fullname": course['fullname']}
            for course in courses
        ]
        return jsonify({"courses": course_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/assignments', methods=['GET'])
def get_assignments():
    try:
        courseid = request.args.get('courseid', type=int)
        if not courseid:
            return jsonify({"error": "Missing courseid parameter"}), 400
        data = call_moodle_api('mod_assign_get_assignments', {'courseids[0]': courseid})
        assignments = []
        for course in data.get('courses', []):
            for assign in course.get('assignments', []):
                assignments.append({"id": assign['id'], "name": assign['name']})
        return jsonify({"assignments": assignments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def reshape_hebrew_text(text):
    # לא נוגעים באנגלית/נוסחאות שמכילות אותיות לטיניות או סוגריים מתמטיים
    # אבל כן משחזרים את הטקסט העברי כדי שיהיה מוצג נכון ב-RTL
    tokens = re.split(r'(\s+)', text)  # שמור על רווחים
    reshaped_tokens = []

    for token in tokens:
        if re.search(r'[a-zA-Z0-9()/*=+_\[\]{}<>-]', token):
            reshaped_tokens.append(token)  # אל תיגע באנגלית או מתמטיקה
        else:
            reshaped_token = arabic_reshaper.reshape(token)
            reshaped_tokens.append(reshaped_token)

    reshaped_text = ''.join(reshaped_tokens)
    return get_display(reshaped_text)


def safe_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# פונקציה להמרת sub/sup וסימנים מתמטיים
SUPERSCRIPT_MAP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
SUBSCRIPT_MAP = str.maketrans("0123456789+-=()n", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₙ")

def convert_html_math(text: str) -> str:
    def replace_sup(match):
        return match.group(1).translate(SUPERSCRIPT_MAP)

    def replace_sub(match):
        return match.group(1).translate(SUBSCRIPT_MAP)

    # HTML tags
    text = re.sub(r'<sup>(.*?)</sup>', replace_sup, text)
    text = re.sub(r'<sub>(.*?)</sub>', replace_sub, text)

    # Math replacements
    replacements = {
        "!=": "≠",
        "<=": "≤",
        ">=": "≥",
        "->": "→",
        "=>": "⇒",
        "<-": "←",
        "<=>": "⇔",
        "sqrt(": "√(",
        "inf": "∞",
        "infinity": "∞",
        "integral": "∫",
        "sum": "∑",
        "pi": "π",
        "theta": "θ",
        "alpha": "α",
        "beta": "β",
        "gamma": "γ",
        "+-": "±",
        "degree": "°",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    return text

# === מיפויים ל־superscript ו־subscript ===
SUPERSCRIPT_MAP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
SUBSCRIPT_MAP = str.maketrans("0123456789+-=()n", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₙ")

# === זיהוי סימנים מתמטיים ותבניות נפוצות ===
def convert_html_math(text: str) -> str:
    # HTML-style superscripts/subscripts
    text = re.sub(r'<sup>(.*?)</sup>', lambda m: m.group(1).translate(SUPERSCRIPT_MAP), text)
    text = re.sub(r'<sub>(.*?)</sub>', lambda m: m.group(1).translate(SUBSCRIPT_MAP), text)

    # סימנים מתמטיים רגילים
    replacements = {
        "!=": "≠", "<=": "≤", ">=": "≥", "+-": "±",
        "->": "→", "=>": "⇒", "<-": "←", "<=>": "⇔",
        "inf": "∞", "infinity": "∞",
        "sqrt(": "√(",
        "integral": "∫", "sum": "∑",
        "pi": "π", "theta": "θ", "alpha": "α",
        "beta": "β", "gamma": "γ", "degree": "°"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # x^2 → x²
    text = re.sub(r'(\w)\^([0-9n])', lambda m: m.group(1) + m.group(2).translate(SUPERSCRIPT_MAP), text)

    # x_1 → x₁
    text = re.sub(r'(\w)_([0-9n])', lambda m: m.group(1) + m.group(2).translate(SUBSCRIPT_MAP), text)

    # lim x->0 → lim x→0
    text = re.sub(r'lim\s+([a-zA-Z])\s*->\s*([0-9a-zA-Z∞\-\+]+)', r'lim \1→\2', text)

    return text

# === הגנה על HTML מבלי לפגוע במתמטיקה ===
def safe_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def latex_to_pdf(latex_code: str, output_dir: str = "tmp", filename: str = "questions_latex"):
    os.makedirs(output_dir, exist_ok=True)

    tex_path = os.path.join(output_dir, f"{filename}.tex")

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex_code)

    return tex_path if os.path.exists(tex_path) else None

@app.route('/generate-questions', methods=['POST'])
def generate_questions():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        if not prompt:
            return jsonify({'error': 'Missing prompt'}), 400

        directory_path = 'analysis_results'
        all_questions = []

        for filename in os.listdir(directory_path):
            if filename.endswith('.json'):
                file_path = os.path.join(directory_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    for entry in json_data.get("results", []):
                        question = entry.get("question", "").strip()
                        if question and '(cid:' not in question and len(question) > 5:
                            all_questions.append(question)

        if not all_questions:
            return jsonify({'error': 'No valid questions found in files'}), 400

        combined_questions = "\n".join(all_questions)
        final_prompt = f"\n\nשאלות מתוך קבצים:\n{combined_questions}"

        gemini_prompt = (
            f"הפק שאלות תרגול במתמטיקה לפי ההנחיות של המשתמש:\n\n"
            f"{prompt}\n\n"
            "חשוב מאוד:\n"
            "- כתוב את השאלות בעברית.\n"
            "- את הנוסחאות המתמטיות כתוב ב־LaTeX (הקף כל נוסחה בסימן דולר $ כמו $x^2$).\n"
            "- כתוב כל שאלה בשורה חדשה.\n"
            "- החזר רק את כמות השאלות שהתבקשת, לא יותר ולא פחות.\n"
            "- המספור של השאלות יהיה בצורת 1. 2. 3. וכן הלאה.\n"
        )

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=gemini_prompt
        )
        questions_text = response.text.strip() if hasattr(response, 'text') else str(response)
        questions = [q.strip() for q in questions_text.split('\n') if q.strip()]

        latex_questions = "\n".join([f"\\item {q}" for q in questions])

        latex_doc = rf"""
        \documentclass[12pt]{{article}}
        \usepackage[utf8]{{inputenc}}
        \usepackage[hebrew,english]{{babel}}
        \usepackage{{amsmath, amssymb, enumitem, geometry}}
        \geometry{{margin=1in}}
        \setlength{{\parindent}}{{0pt}}

        \begin{{document}}
        \selectlanguage{{hebrew}}
        \begin{{enumerate}}
        {latex_questions}
        \end{{enumerate}}
        \end{{document}}
        """

        pdf_path = latex_to_pdf(latex_doc)
        if not pdf_path:
            return jsonify({'error': 'Failed to compile LaTeX to PDF'}), 500

        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='generated_questions.pdf'
        )

    except Exception as e:
        logging.exception("Error in /generate-questions")
        return jsonify({'error': str(e)}), 500


    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

