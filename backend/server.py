from flask import Flask, request, jsonify
from utils import *
import json
import os
import google.genai as genai
import PyPDF2  

app = Flask(__name__)
GEMINI_API_KEY = "AIzaSyCBd_uKeyycsilepxqsJRQ40AhrpoM5wTE"

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
        client = genai.Client(api_key=GEMINI_API_KEY)
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
