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
from moodle import call_moodle_api
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
GEMINI_API_KEY = "AIzaSyCBd_uKeyycsilepxqsJRQ40AhrpoM5wTE"
client = genai.Client(api_key=GEMINI_API_KEY)

@app.route('/choose', methods=['POST'])
def choose_varied_files():
    """Endpoint to download submissions, find the two most different files, and return their content."""
    try:
        assignment_id_from_request = request.json.get('exercise_id')
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
        
        if len(files_in_assignment_dir) < 2:
            return jsonify({"error": f"At least two processable files (.lyx or .pdf) found in {assignment_specific_dir} are required for comparison. Found: {len(files_in_assignment_dir)}"}), 400

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

        if len(file_embeddings) < 2:
            return jsonify({"error": f"Less than two files were successfully processed for embeddings. Processed: {len(file_embeddings)}"}), 400

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
        
        if not sorted_file_paths_by_similarity or len(sorted_file_paths_by_similarity) < 2:
             return jsonify({"error": "Could not determine the two most different files from the processed submissions."}), 500

        most_varied_source_paths = [file_path for file_path, _ in sorted_file_paths_by_similarity[:2]]
        
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
        
        # Ensure we actually have two files to return after attempting to read them
        if len(returned_files_data) < 2 and len(most_varied_source_paths) >= 2:
             print(f"Warning: Expected to return 2 files, but only {len(returned_files_data)} could be successfully read and encoded.")
             return jsonify({"error": "Failed to read/encode one or more of the selected files for the response."}), 500
        elif not returned_files_data and len(most_varied_source_paths) > 0:
             return jsonify({"error": "Selected files could not be prepared for the response."}), 500
        elif len(most_varied_source_paths) < 2: # Should be caught earlier, but as a safeguard
            return jsonify({"error": "Not enough files to select the two most varied."}), 500


        return jsonify({
            "files": returned_files_data,
            "message": f"Successfully found and prepared the two most different files from assignment {assignment_id_str}"
        })

    except Exception as e:
        print(f"An unexpected error occurred in /choose endpoint: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/', methods=['GET'])
def index():
    return "LaTeX grading backend is running."

@app.route('/grade', methods=['POST'])
def grade_latex_file(): 
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    filename = file.filename

    if filename.endswith('.tex'):   
        latex = file.read().decode('utf-8')
    elif filename.endswith('.pdf'):
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            latex = ""
            for page in pdf_reader.pages:
                latex += page.extract_text() or ""
        except Exception as e:
            return jsonify({"error": f"PDF extraction error: {str(e)}"}), 400
    else:
        return jsonify({"error": "Only .tex or .pdf files are allowed"}), 400

    # --- קובץ קונטקסט חובה ---
    context_str=""
    if 'context' in request.files:
        try:
            context_file = request.files['context']
            if context_file.filename.endswith('.json'):
                context_data = json.load(context_file)
                context_str = json.dumps(context_data, ensure_ascii=False, indent=2)
            elif context_file.filename.endswith('.txt'):
                context_str = context_file.read().decode('utf-8')
            else:
                return jsonify({"error": "Only .json or .txt context files are allowed"}), 400
        except Exception as e:
            return jsonify({"error": f"Context file error: {str(e)}"}), 400

    # --- Prompt משולב ---
    prompt = (
        "אתה בודק מתמטיקה שמעריך פתרונות LaTeX או PDF.\n"
        "בהתבסס על דוגמאות של בדיקות קודמות של מרצה (קונטקסט), "
        "בדוק את הפתרון הבא תוך ניסיון לחקות את סגנון ההערכה והציונים של המרצה.\n"
        "החזר JSON  חוקי בלבד עם פירוט לפי השדות: שאלה, סעיף, ציון (0–100), הערה. הערות מפורטות מאוד שמסבירות מה הטעות \n"
        "דוגמה: [{\"שאלה\": \"1\", \"סעיף\": \"א\", \"ציון\": 85, \"הערה\": \"ניסוח תקין, חסר נימוק\"}]\n\n"
        "קונטקסט:\n"
        f"{context_str}\n\n"
        "פתרון לבדיקה:\n"
        f"{latex}"
    )

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        json_text = response.text.strip()
        structured = extract_valid_json(json_text)

        if not structured:
            return jsonify({
                "error": "Gemini did not return valid JSON",
                "raw_response": json_text
            }), 500

        save_table_to_latex(structured)

        return jsonify({
            "feedback": structured,
            "message": f"הטבלה נשמרה כ־{TABLE_OUTPUT_PATH}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/summary', methods=['POST'])
def summary_from_feedback():
    '''
    מקבל feedback מהבקשה (בפורמט JSON) ומחזיר ציון סופי והערה מסכמת.
    '''
    try:
        data = request.get_json()
        feedback = data.get("feedback", [])

        if not isinstance(feedback, list):
            return jsonify({"error": "'feedback' must be a list"}), 400

        summary = summarize_feedback(feedback)

        return jsonify(summary)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    app.run(host="0.0.0.0", port=5000)
