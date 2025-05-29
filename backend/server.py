from flask import Flask, request, jsonify
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

