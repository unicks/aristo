from flask import Flask, request, jsonify
from utils import (
    extract_valid_json, save_table_to_latex, summarize_feedback, 
    extract_text_from_pdf, get_file_content, get_embedding, cosine_similarity
)
from moodle import download_all_submissions, DOWNLOAD_DIR as MOODLE_DOWNLOAD_DIR # Import Moodle utils
import json
import os
import google.genai as genai
import PyPDF2
import numpy as np
from typing import Dict, List
import base64 # Added for Base64 encoding
from moodle import call_moodle_api, grade_assignment
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
GEMINI_API_KEY = "AIzaSyCBd_uKeyycsilepxqsJRQ40AhrpoM5wTE"
client = genai.Client(api_key=GEMINI_API_KEY)


@app.route('/choose', methods=['POST'])
def choose_varied_files():
    """Endpoint to download submissions, find the N most different files, and return their content."""
    if request.method == "OPTIONS": return "", 200
    try:
        assignment_id_from_request = request.json.get('exercise_id')
        amount = int(request.json.get('amount', 2)) # Default to 2 if not provided

        if not isinstance(amount, int) or amount < 2:
            return jsonify({"error": "amount must be an integer greater than or equal to 2"}), 400

        if not assignment_id_from_request:
            return jsonify({"error": "exercise_id is required"}), 400

        # Ensure assignment_id is a string for path operations and moodle function
        assignment_id_str = str(assignment_id_from_request)

        try:
            print(f"Downloading submissions for assignment ID: {assignment_id_str}...")
            download_all_submissions(assignment_id_str) 
            print(f"Submissions downloaded to: {MOODLE_DOWNLOAD_DIR}/{assignment_id_str}")
        except Exception as e:
            print(f"Error downloading submissions for assignment {assignment_id_str}: {e}")
            return jsonify({"error": f"Failed to download submissions: {str(e)}"}), 500
        
        submissions_base_dir = MOODLE_DOWNLOAD_DIR 
        assignment_specific_dir = os.path.join(submissions_base_dir, assignment_id_str)

        if not os.path.exists(assignment_specific_dir):
            print(f"Assignment specific directory {assignment_specific_dir} not found after download attempt.")
            return jsonify({"error": f"Submissions directory for assignment {assignment_id_str} not found."}), 404
            
        files_in_assignment_dir = [
            os.path.join(assignment_specific_dir, f) 
            for f in os.listdir(assignment_specific_dir) 
            if os.path.isfile(os.path.join(assignment_specific_dir, f)) and f.endswith(('.lyx', '.pdf'))
        ]
        
        if len(files_in_assignment_dir) < amount:
            return jsonify({"error": f"At least {amount} processable files (.lyx or .pdf) found in {assignment_specific_dir} are required for comparison. Found: {len(files_in_assignment_dir)}"}), 400

        file_embeddings: Dict[str, List[float]] = {}
        print(f"Processing {len(files_in_assignment_dir)} files for embeddings from {assignment_specific_dir}...")
        for file_path in files_in_assignment_dir:
            try:
                print(f"Getting content for {file_path}")
                content_for_embedding = get_file_content(file_path) 
                if not content_for_embedding:
                    print(f"Warning: No content extracted for embedding from {file_path}. Skipping.")
                    continue
                print(f"Getting embedding for {file_path}")
                embedding = get_embedding(client, content_for_embedding)
                if embedding:
                    file_embeddings[file_path] = embedding
                else:
                    print(f"Warning: Could not get embedding for {file_path}. Skipping.")
            except Exception as e:
                print(f"Error processing file {file_path} for embedding: {e}. Skipping.")

        if len(file_embeddings) < amount:
            return jsonify({"error": f"Less than {amount} files were successfully processed for embeddings. Processed: {len(file_embeddings)}"}), 400

        similarity_scores: Dict[str, float] = {}
        file_paths_with_embeddings = list(file_embeddings.keys())

        for path in file_paths_with_embeddings:
            similarity_scores[path] = 0.0
        
        for i in range(len(file_paths_with_embeddings)):
            for j in range(i + 1, len(file_paths_with_embeddings)):
                path1 = file_paths_with_embeddings[i]
                path2 = file_paths_with_embeddings[j]
                embedding1 = file_embeddings[path1]
                embedding2 = file_embeddings[path2]

                similarity = cosine_similarity(embedding1[0].values, embedding2[0].values)
                similarity_scores[path1] += similarity
                similarity_scores[path2] += similarity

        sorted_file_paths_by_similarity = sorted(similarity_scores.items(), key=lambda item: item[1])
        
        if not sorted_file_paths_by_similarity or len(sorted_file_paths_by_similarity) < amount:
             return jsonify({"error": f"Could not determine the {amount} most different files from the processed submissions."}), 500

        most_varied_source_paths = [file_path for file_path, _ in sorted_file_paths_by_similarity[:amount]]
        
        returned_files_data = []
        for file_path in most_varied_source_paths:
            try:
                with open(file_path, 'rb') as f_raw:
                    raw_content_bytes = f_raw.read()
                encoded_content = base64.b64encode(raw_content_bytes).decode('utf-8')
                returned_files_data.append({
                    "filename": os.path.basename(file_path),
                    "content_base64": encoded_content
                })
            except FileNotFoundError:
                print(f"Error: File not found at {file_path} when preparing response. This file was selected as one of the most varied.")
                # This is a significant issue if a selected file is suddenly missing.
            except Exception as e:
                print(f"Error reading or encoding file {file_path} for response: {e}")
                # Optionally skip this file or handle error differently
                continue 
        
        # Ensure we actually have 'amount' files to return after attempting to read them
        if len(returned_files_data) < amount and len(most_varied_source_paths) >= amount:
             print(f"Warning: Expected to return {amount} files, but only {len(returned_files_data)} could be successfully read and encoded.")
             return jsonify({"error": "Failed to read/encode one or more of the selected files for the response."}), 500
        elif not returned_files_data and len(most_varied_source_paths) > 0:
             return jsonify({"error": "Selected files could not be prepared for the response."}), 500
        elif len(most_varied_source_paths) < amount: # Should be caught earlier, but as a safeguard
            return jsonify({"error": f"Not enough files to select the {amount} most varied."}), 500


        return jsonify({
            "files": returned_files_data,
            "message": f"Successfully found and prepared the {amount} most different files from assignment {assignment_id_str}"
        })

    except Exception as e:
        print(f"An unexpected error occurred in /choose endpoint: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/', methods=['GET'])
def index():
    return "LaTeX grading backend is running."

def grade_pdf_file(pdf_path, context_path=None):
    # --- Step 1: Extract LaTeX-like content from the PDF ---
    try:
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            latex = ""
            for page in pdf_reader.pages:
                latex += page.extract_text() or ""
    except Exception as e:
        raise RuntimeError(f"PDF extraction error: {str(e)}")

    # --- Step 2: Read optional context ---
    context_str = ""
    if context_path:
        try:
            if context_path.endswith(".json"):
                with open(context_path, "r", encoding="utf-8") as f:
                    context_data = json.load(f)
                context_str = json.dumps(context_data, ensure_ascii=False, indent=2)
            elif context_path.endswith(".txt"):
                with open(context_path, "r", encoding="utf-8") as f:
                    context_str = f.read()
            else:
                raise ValueError("Only .json or .txt context files are allowed")
        except Exception as e:
            raise RuntimeError(f"Context file error: {str(e)}")

    # --- Step 3: Compose prompt ---
    prompt = (
        "אתה בודק מתמטיקה שמעריך פתרונות PDF.\n"
        "בהתבסס על דוגמאות של בדיקות קודמות של מרצה (קונטקסט), "
        "בדוק את הפתרון הבא תוך ניסיון לחקות את סגנון ההערכה והציונים של המרצה.\n"
        "החזר JSON חוקי בלבד עם פירוט לפי השדות: שאלה, סעיף, ציון (0–100), הערה.\n"
        "הערות מפורטות מאוד שמסבירות מה הטעות.\n"
        "דוגמה: [{\"שאלה\": \"1\", \"סעיף\": \"א\", \"ציון\": 85, \"הערה\": \"ניסוח תקין, חסר נימוק\"}]\n\n"
        f"קונטקסט:\n{context_str}\n\n"
        f"פתרון לבדיקה:\n{latex}"
    )

    # --- Step 4: Query Gemini ---
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        json_text = response.text.strip()
        structured = extract_valid_json(json_text)

        if not structured:
            # Try fixing the response using Gemini
            fix_prompt = (
                "הטקסט הבא נראה כמו פלט לא תקין של JSON. "
                "תקן אותו והחזר רק JSON חוקי. "
                "אין להוסיף הסברים או טקסט מחוץ למבנה JSON.\n\n"
                f"פלט לתיקון:\n{json_text}"
            )

            fix_response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=fix_prompt
            )
            fixed_text = fix_response.text.strip()
            structured = extract_valid_json(fixed_text)

            if not structured:
                raise ValueError("Gemini response could not be fixed into valid JSON.")

        save_table_to_latex(structured)

        return {
            "feedback": structured,
        }

    except Exception as e:
        raise RuntimeError(f"Gemini error: {str(e)}")

@app.route('/grade_all', methods=['POST'])
def grade_all():
    try:
        # Get assignment ID from form, JSON, or query string
        assignid = request.form.get('assignid') or \
                   (request.json and request.json.get('assignid')) or \
                   request.args.get('assignid')

        if not assignid:
            return jsonify({"error": "Missing 'assignid' in request"}), 400

        context = request.form.get('context') or \
                   (request.json and request.json.get('context')) or \
                   request.args.get('context')

        if not context:
            context = ""

        # Collect all user files in the .temp directory
        temp_dir = os.path.join('.temp', str(assignid))
        if not os.path.exists(temp_dir):
            return jsonify({"error": f"Directory '{temp_dir}' does not exist"}), 400

        users = [f for f in os.listdir(temp_dir)]
        if not users:
            return jsonify({"error": "No user files found in .temp directory"}), 404

        results = []
        errors = []

        for user_file in users:
            user_path = os.path.join(temp_dir, user_file)
            try:
                feedback = grade_pdf_file(user_path)
                summary = summarize_feedback(feedback)
                user_id = int(user_file.split(".")[0])
                grade_assignment(assignid, user_id, summary["final_grade"], note=feedback)
                results.append({
                    "user": user_file,
                    "grade": summary["final_grade"],
                    "comment": summary["master_comment"]
                })
            except Exception as e:
                errors.append({
                    "user": user_file,
                    "error": str(e)
                })
        return jsonify({
            "message": f"Processed {len(results)} users for assignment {assignid}",
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
    app.run(host='0.0.0.0', port=5000, debug=False)

