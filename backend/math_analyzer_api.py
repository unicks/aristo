from flask import Flask, request, jsonify
import google.generativeai as genai
import pdfplumber
import logging
import traceback
from typing import Dict, Any, List
import os
from werkzeug.utils import secure_filename
import tempfile
import json
import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyCBd_uKeyycsilepxqsJRQ40AhrpoM5wTE"
genai.configure(api_key=GEMINI_API_KEY)

# List available models
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            logger.info(f"Available model: {m.name}")
except Exception as e:
    logger.error(f"Error listing models: {str(e)}")

def extract_text_from_pdf(pdf_file) -> str:
    """Extract text content from a PDF file."""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            text_content = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
            
            full_text = "\n".join(text_content)
            if not full_text.strip():
                raise ValueError("No text content extracted from PDF")
            
            return full_text
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
        raise

def analyze_math_content(content: str) -> Dict[str, Any]:
    """Analyze mathematical content using Gemini API."""
    prompt = """You are a mathematical content analyzer. Analyze the following mathematical question(s) and provide detailed tags.

Rules:
1. Return ONLY valid JSON
2. Be specific with topic names
3. Rate difficulty from 1-5 (1=easiest)
4. List ALL relevant prerequisites
5. Separate each question and provide the analysis for each question. all in one json file. name the questions as question1, question2, question3, etc.

Required JSON format:
{
    "question1": {
        "values": {
            "topics": ["topic1", "topic2"],
            "subjects": ["specific_subject1", "specific_subject2"],
            "difficulty": 3,
            "prerequisites": ["prerequisite1", "prerequisite2"]
        }
    },
    "question2": {
        "values": {
            "topics": ["topic1", "topic2"],
            "subjects": ["specific_subject1", "specific_subject2"],
            "difficulty": 3,
            "prerequisites": ["prerequisite1", "prerequisite2"]
        }
    }
}

Content to analyze:
"""

    try:
        model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
        response = model.generate_content(
            prompt + content,
            generation_config={
                "temperature": 0.3,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
        )
        
        # Clean and parse the response
        result = response.text.strip()
        logger.debug(f"Raw response: {result}")
        
        if result.startswith('```json'):
            result = result[7:]
        if result.endswith('```'):
            result = result[:-3]
            
        try:
            analysis = json.loads(result.strip())
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            logger.error(f"Failed to parse response: {result}")
            raise ValueError("Invalid JSON response from AI model")
        
        logger.debug(f"Parsed analysis: {json.dumps(analysis, indent=2)}")
        
        # Validate the response structure
        if not isinstance(analysis, dict):
            logger.error(f"Response is not a dictionary: {type(analysis)}")
            raise ValueError("Response must be a JSON object")
            
        # Check if there's at least one question
        question_keys = [key for key in analysis.keys() if key.startswith('question')]
        if not question_keys:
            logger.error(f"No question keys found in response. Keys: {list(analysis.keys())}")
            raise ValueError("Response must contain at least one question")
            
        # Sort question keys to ensure consistent order
        try:
            question_keys.sort(key=lambda x: int(x.replace('question', '')))
        except ValueError:
            # If sorting fails, just use the keys in their original order
            pass
        
        # Create a new dictionary with properly ordered questions
        ordered_analysis = {}
        for i, key in enumerate(question_keys, 1):
            new_key = f"question{i}"
            ordered_analysis[new_key] = analysis[key]
        
        # Validate each question
        for question_key, question_data in ordered_analysis.items():
            if not isinstance(question_data, dict):
                logger.error(f"Question data is not a dictionary for {question_key}: {type(question_data)}")
                raise ValueError(f"'{question_key}' must be an object")
                
            if "values" not in question_data:
                logger.error(f"Missing 'values' field in {question_key}")
                raise ValueError(f"'{question_key}' must contain 'values' field")
                
            values = question_data["values"]
            required_fields = ["topics", "subjects", "difficulty", "prerequisites"]
            for field in required_fields:
                if field not in values:
                    logger.error(f"Missing required field '{field}' in {question_key}")
                    raise ValueError(f"Values must contain '{field}' field")
                    
            # Validate field types
            if not isinstance(values["topics"], list):
                logger.error(f"'topics' is not a list in {question_key}: {type(values['topics'])}")
                raise ValueError("'topics' must be an array")
            if not isinstance(values["subjects"], list):
                logger.error(f"'subjects' is not a list in {question_key}: {type(values['subjects'])}")
                raise ValueError("'subjects' must be an array")
            if not isinstance(values["prerequisites"], list):
                logger.error(f"'prerequisites' is not a list in {question_key}: {type(values['prerequisites'])}")
                raise ValueError("'prerequisites' must be an array")
            if not isinstance(values["difficulty"], (int, float)) or not 1 <= values["difficulty"] <= 5:
                logger.error(f"Invalid difficulty value in {question_key}: {values['difficulty']}")
                raise ValueError("'difficulty' must be a number between 1 and 5")
                
            # Validate content
            if not values["topics"]:
                logger.error(f"Empty topics array in {question_key}")
                raise ValueError("'topics' array cannot be empty")
            if not values["subjects"]:
                logger.error(f"Empty subjects array in {question_key}")
                raise ValueError("'subjects' array cannot be empty")
            
        return ordered_analysis
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise

@app.route('/analyze/single', methods=['POST'])
def analyze_single():
    """
    Analyze a single PDF file containing math questions.
    
    Request: multipart/form-data with 'file' field containing the PDF
    Response: JSON with analysis results
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if not file.filename.endswith('.pdf'):
            return jsonify({"error": "Only PDF files are allowed"}), 400

        # Extract text from PDF
        text_content = extract_text_from_pdf(file)
        
        try:
            analysis = analyze_math_content(text_content)
            return jsonify({
                "filename": file.filename,
                "analysis": analysis
            })
        except Exception as e:
            return jsonify({
                "error": f"Failed to analyze content: {str(e)}",
                "content": text_content
            }), 500
            
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/analyze/batch', methods=['POST'])
def analyze_batch():
    """
    Analyze multiple PDF files containing math questions.
    
    Request: multipart/form-data with 'files' field containing multiple PDFs
    Response: JSON with analysis results for each file
    """
    try:
        if 'files' not in request.files:
            return jsonify({"error": "No files provided"}), 400
            
        files = request.files.getlist('files')
        if not files:
            return jsonify({"error": "No files provided"}), 400
            
        results = []
        for file in files:
            try:
                if not file.filename.endswith('.pdf'):
                    results.append({
                        "filename": file.filename,
                        "error": "Not a PDF file"
                    })
                    continue
                    
                text_content = extract_text_from_pdf(file)
                try:
                    analysis = analyze_math_content(text_content)
                    results.append({
                        "filename": file.filename,
                        "analysis": analysis
                    })
                except Exception as e:
                    results.append({
                        "filename": file.filename,
                        "error": str(e)
                    })
                    
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "error": str(e)
                })
                
        return jsonify({
            "total_files": len(files),
            "successful": len([r for r in results if "analysis" in r]),
            "results": results
        })
        
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    """Root endpoint to check if API is running."""
    return jsonify({
        "status": "active",
        "message": "Math Analyzer API is running",
        "endpoints": {
            "/status": "Check API health",
            "/analyze/single": "Analyze a single PDF file",
            "/analyze/batch": "Analyze multiple PDF files"
        }
    })

@app.route('/status', methods=['GET'])
def status():
    """Check API health and dependencies."""
    try:
        # Test Gemini
        model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
        response = model.generate_content("Test")
        gemini_ok = bool(response and response.text)
        
        # Test PDF processing
        with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
            try:
                with pdfplumber.open(tmp.name) as pdf:
                    pdf_ok = True
            except:
                pdf_ok = False
                
        return jsonify({
            "status": "healthy" if (gemini_ok and pdf_ok) else "degraded",
            "services": {
                "api": True,
                "gemini": gemini_ok,
                "pdf_processing": pdf_ok
            },
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000) 