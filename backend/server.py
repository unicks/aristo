from flask import Flask, request, jsonify
from utils import (
    extract_valid_json, save_table_to_latex, summarize_feedback, 
    extract_text_from_pdf, get_file_content, get_embedding, cosine_similarity
)
import json
import os
import google.genai as genai
import PyPDF2
import numpy as np
from typing import Dict, List

from flask import Flask, request, jsonify
import requests
import os

# --- Configuration ---
MOODLE_URL = "https://aristoplan.moodlecloud.com"
MOODLE_TOKEN = "c254f0acadf572f82f74dc03ea7ca156"
DOWNLOAD_DIR = "downloads"

app = Flask(__name__)
GEMINI_API_KEY = "AIzaSyCBd_uKeyycsilepxqsJRQ40AhrpoM5wTE"
client = genai.Client(api_key=GEMINI_API_KEY)

@app.route('/choose', methods=['POST'])
def choose_varied_files():
    """Endpoint to download submissions and find the two most different files."""
    try:
        assignment_id = request.json.get('exercise_id')
        if not assignment_id:
            return jsonify({"error": "exercise_id is required"}), 400

        # Download submissions for the given assignment_id
        try:
            print(f"Downloading submissions for assignment ID: {assignment_id}...")
            download_all_submissions(assignment_id)
            print(f"Submissions downloaded to: {MOODLE_DOWNLOAD_DIR}")
        except Exception as e:
            print(f"Error downloading submissions: {e}")
            return jsonify({"error": f"Failed to download submissions: {str(e)}"}), 500
        
        # Use the DOWNLOAD_DIR from moodle.py
        submissions_dir = MOODLE_DOWNLOAD_DIR 
        if not os.path.exists(submissions_dir):
            # This case should ideally be handled by download_all_submissions,
            # but check just in case.
            print(f"Submissions directory {submissions_dir} not found after download attempt.")
            return jsonify({"error": f"Submissions directory not found: {submissions_dir}"}), 404
            
        files = [os.path.join(submissions_dir, f) for f in os.listdir(submissions_dir) 
                 if os.path.isfile(os.path.join(submissions_dir, f)) and f.endswith(('.lyx', '.pdf'))]
        
        if len(files) < 2:
            return jsonify({"error": "At least two processable files (.lyx or .pdf) are required for comparison after download"}), 400

        # Get embeddings for all files
        file_embeddings: Dict[str, List[float]] = {}
        print(f"Processing {len(files)} files for embeddings...")
        for file_path in files:
            try:
                print(f"Getting content for {file_path}")
                content = get_file_content(file_path)
                if not content:
                    print(f"Warning: No content extracted from {file_path}. Skipping.")
                    continue
                print(f"Getting embedding for {file_path}")
                embedding = get_embedding(client, content)
                if embedding:
                    file_embeddings[file_path] = embedding
                else:
                    print(f"Warning: Could not get embedding for {file_path}. Skipping.")
            except Exception as e:
                print(f"Error processing file {file_path} for embedding: {e}. Skipping.")

        if len(file_embeddings) < 2:
            return jsonify({"error": f"Less than two files were successfully processed for embeddings. Processed: {len(file_embeddings)}"}), 400

        # Calculate similarity scores
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

        sorted_files = sorted(similarity_scores.items(), key=lambda item: item[1])
        
        if not sorted_files or len(sorted_files) < 2:
             return jsonify({"error": "Could not determine the two most different files from the processed submissions."}), 500

        most_varied_files = [file_path for file_path, _ in sorted_files[:2]]

        return jsonify({
            "files": most_varied_files,
            "message": f"Successfully found the two most different files from assignment {assignment_id}"
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

    def choose_varied_from_files(file_paths):
        """
        Given a list of file paths, process them as in /choose endpoint and return the two most different files.
        """
        # Get embeddings for all files
        file_embeddings = {}
        for file_path in file_paths:
            try:
                content = get_file_content(file_path)
                if not content:
                    continue
                embedding = get_embedding(client, content)
                if embedding:
                    file_embeddings[file_path] = embedding
            except Exception:
                continue

        if len(file_embeddings) < 2:
            raise ValueError("Less than two files were successfully processed for embeddings.")

        # Calculate similarity scores
        similarity_scores = {path: 0.0 for path in file_embeddings}
        file_paths_with_embeddings = list(file_embeddings.keys())

        for i in range(len(file_paths_with_embeddings)):
            for j in range(i + 1, len(file_paths_with_embeddings)):
                path1 = file_paths_with_embeddings[i]
                path2 = file_paths_with_embeddings[j]
                embedding1 = file_embeddings[path1]
                embedding2 = file_embeddings[path2]
                similarity = cosine_similarity(embedding1[0].values, embedding2[0].values)
                similarity_scores[path1] += similarity
                similarity_scores[path2] += similarity

        sorted_files = sorted(similarity_scores.items(), key=lambda item: item[1])
        if len(sorted_files) < 2:
            raise ValueError("Could not determine the two most different files.")

        return [file_path for file_path, _ in sorted_files[:2]]

def call_moodle_api(function, params=None):
    if params is None:
        params = {}
    params.update({
        'wstoken': MOODLE_TOKEN,
        'moodlewsrestformat': 'json',
        'wsfunction': function
    })
    response = requests.post(f"{MOODLE_URL}/webservice/rest/server.php", data=params)
    response.raise_for_status()
    return response.json()

@app.route('/courses/<int:userid>')
def list_courses(userid):
    try:
        courses = call_moodle_api('core_enrol_get_users_courses', {'userid': userid})
        return jsonify(courses)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/assignments/<int:courseid>')
def list_assignments(courseid):
    try:
        data = call_moodle_api('mod_assign_get_assignments', {'courseids[0]': courseid})
        return jsonify(data['courses'][0]['assignments'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/submissions/<int:assignid>')
def list_submissions(assignid):
    try:
        data = call_moodle_api('mod_assign_get_submissions', {'assignmentids[0]': assignid})
        return jsonify(data['assignments'][0]['submissions'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-submissions/<int:assignid>', methods=['POST'])
def download_all_submissions(assignid):
    try:
        data = call_moodle_api('mod_assign_get_submissions', {'assignmentids[0]': assignid})
        submissions = data['assignments'][0]['submissions']
        downloaded_files = []

        for submission in submissions:
            for plugin in submission.get('plugins', []):
                if plugin['type'] == 'file':
                    for filearea in plugin['fileareas']:
                        for file in filearea['files']:
                            fileurl = file['fileurl']
                            download_url = f"{fileurl}?token={MOODLE_TOKEN}"
                            filename = f"user_{submission['userid']}_{file['filename']}"
                            filepath = os.path.join(DOWNLOAD_DIR, filename)

                            response = requests.get(download_url, stream=True)
                            if response.status_code == 200:
                                with open(filepath, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        f.write(chunk)
                                downloaded_files.append(filename)
                            else:
                                print(f"Failed to download {filename} – status {response.status_code}")
        
        return jsonify({'status': 'done', 'files': downloaded_files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/users', methods=['GET'])
def get_all_users():
    try:
        users = call_moodle_api('core_user_get_users', {'criteria[0][key]': '', 'criteria[0][value]': ''})
        return jsonify(users.get('users', users))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
