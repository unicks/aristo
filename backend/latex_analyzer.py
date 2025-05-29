from flask import Blueprint, request, jsonify
import google.generativeai as genai
import os
import json
from typing import List, Dict, Any

# Create a Blueprint for the analyzer routes
analyzer_bp = Blueprint('analyzer', __name__)

def analyze_latex_content(latex_content: str) -> Dict[str, Any]:
    """Analyze a single LaTeX content using Gemini API."""
    
    prompt = """
    Analyze this LaTeX mathematical question and provide the following information in JSON format:
    1. Main mathematical topics covered (list)
    2. Specific subjects within those topics (list)
    3. Difficulty level (1-5, where 1 is easiest and 5 is hardest)
    4. Required prerequisites (list)
    
    Return only valid JSON in this format:
    {
        "topics": [],
        "subjects": [],
        "difficulty": 0,
        "prerequisites": []
    }
    
    LaTeX content to analyze:
    """
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt + latex_content)
        result = json.loads(response.text.strip())
        return result
    except Exception as e:
        raise Exception(f"Error analyzing LaTeX content: {str(e)}")

def validate_analysis_result(result: Dict[str, Any]) -> bool:
    """Validate the analysis result has the correct structure."""
    required_keys = ["topics", "subjects", "difficulty", "prerequisites"]
    if not all(key in result for key in required_keys):
        return False
    if not isinstance(result["difficulty"], (int, float)) or not 1 <= result["difficulty"] <= 5:
        return False
    if not all(isinstance(result[key], list) for key in ["topics", "subjects", "prerequisites"]):
        return False
    return True

@analyzer_bp.route('/analyze-batch', methods=['POST'])
def analyze_latex_batch():
    """
    Endpoint to analyze multiple LaTeX files.
    Expects multipart/form-data with multiple files with 'latex_files' as the field name.
    """
    if 'latex_files' not in request.files:
        return jsonify({"error": "No LaTeX files provided"}), 400
    
    files = request.files.getlist('latex_files')
    results = []
    
    for file in files:
        if not file.filename.endswith('.tex'):
            continue
            
        try:
            latex_content = file.read().decode('utf-8')
            analysis = analyze_latex_content(latex_content)
            
            if validate_analysis_result(analysis):
                results.append({
                    "filename": file.filename,
                    "analysis": analysis
                })
            else:
                results.append({
                    "filename": file.filename,
                    "error": "Invalid analysis result structure"
                })
                
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return jsonify({
        "total_files": len(files),
        "analyzed_files": len(results),
        "results": results
    })

@analyzer_bp.route('/analyze-single', methods=['POST'])
def analyze_single_latex():
    """
    Endpoint to analyze a single LaTeX file.
    Expects multipart/form-data with a single file with 'file' as the field name.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No LaTeX file provided"}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.tex'):
        return jsonify({"error": "Only .tex files are allowed"}), 400
    
    try:
        latex_content = file.read().decode('utf-8')
        analysis = analyze_latex_content(latex_content)
        
        if validate_analysis_result(analysis):
            return jsonify({
                "filename": file.filename,
                "analysis": analysis
            })
        else:
            return jsonify({
                "error": "Invalid analysis result structure"
            }), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500 