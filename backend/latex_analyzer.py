from flask import Blueprint, request, jsonify
import google.generativeai as genai
import os
import json
from typing import List, Dict, Any
import pdfplumber
import PyPDF2

# Create a Blueprint for the analyzer routes
analyzer_bp = Blueprint('analyzer', __name__)

def extract_text_from_pdf(pdf_file) -> str:
    """Extract text content from a PDF file using pdfplumber."""
    text_content = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text_content += page.extract_text() + "\n"
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")
    return text_content

def analyze_math_content(content: str) -> Dict[str, Any]:
    """Analyze mathematical content using Gemini API."""
    
    prompt = """
    Analyze this mathematical question and provide the following information in JSON format:
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
    
    Content to analyze:
    """
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt + content)
        result = json.loads(response.text.strip())
        return result
    except Exception as e:
        raise Exception(f"Error analyzing content: {str(e)}")

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

def validate_pdf_file(file) -> bool:
    """Validate if the file is a PDF."""
    try:
        PyPDF2.PdfReader(file)
        return True
    except:
        return False

@analyzer_bp.route('/analyze-batch', methods=['POST'])
def analyze_pdf_batch():
    """
    Endpoint to analyze multiple PDF files.
    Expects multipart/form-data with multiple files with 'pdf_files' as the field name.
    """
    if 'pdf_files' not in request.files:
        return jsonify({"error": "No PDF files provided"}), 400
    
    files = request.files.getlist('pdf_files')
    results = []
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            continue
            
        try:
            if not validate_pdf_file(file):
                results.append({
                    "filename": file.filename,
                    "error": "Invalid PDF file"
                })
                continue

            # Reset file pointer after validation
            file.seek(0)
            content = extract_text_from_pdf(file)
            analysis = analyze_math_content(content)
            
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
def analyze_single_pdf():
    """
    Endpoint to analyze a single PDF file.
    Expects multipart/form-data with a single file with 'file' as the field name.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No PDF file provided"}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "Only PDF files are allowed"}), 400
    
    try:
        if not validate_pdf_file(file):
            return jsonify({"error": "Invalid PDF file"}), 400

        # Reset file pointer after validation
        file.seek(0)
        content = extract_text_from_pdf(file)
        analysis = analyze_math_content(content)
        
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