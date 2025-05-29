from flask import Flask, request, jsonify
from utils import *
import json
import os
import google.generativeai as genai

app = Flask(__name__)
GEMINI_API_KEY = "AIzaSyCBd_uKeyycsilepxqsJRQ40AhrpoM5wTE"

genai.configure(api_key=GEMINI_API_KEY)

@app.route('/', methods=['GET'])
def index():
    return "LaTeX grading backend is running."

@app.route('/grade', methods=['POST'])
def grade_latex_file():
    if 'file' not in request.files:
        return jsonify({"error": "No LaTeX file provided"}), 400
    file = request.files['file']
    if not file.filename.endswith('.tex'):
        return jsonify({"error": "Only .tex files are allowed"}), 400

    latex = file.read().decode('utf-8')

    # --- קובץ קונטקסט חובה ---
    context_str=""
    if 'context' in request.files:
        try:
            context_file = request.files['context']
            context_data = json.load(context_file)
            context_str = json.dumps(context_data, ensure_ascii=False, indent=2)
        except Exception as e:
            return jsonify({"error": f"Context file error: {str(e)}"}), 400

    # --- Prompt משולב ---
    prompt = (
        "אתה בודק מתמטיקה שמעריך פתרונות LaTeX.\n"
        "בהתבסס על דוגמאות של בדיקות קודמות של מרצה (קונטקסט), "
        "בדוק את הפתרון הבא תוך ניסיון לחקות את סגנון ההערכה והציונים של המרצה.\n"
        "החזר JSON חוקי בלבד עם פירוט לפי השדות: שאלה, סעיף, ציון (0–100), הערה.\n"
        "דוגמה: [{\"שאלה\": \"1\", \"סעיף\": \"א\", \"ציון\": 85, \"הערה\": \"ניסוח תקין, חסר נימוק\"}]\n\n"
        "קונטקסט:\n"
        f"{context_str}\n\n"
        "פתרון לבדיקה:\n"
        f"{latex}"
    )

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
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
