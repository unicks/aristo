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

Required JSON format:
{
    "topics": ["topic1", "topic2"],
    "subjects": ["specific_subject1", "specific_subject2"],
    "difficulty": 3,
    "prerequisites": ["prerequisite1", "prerequisite2"]
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
        if result.startswith('```json'):
            result = result[7:]
        if result.endswith('```'):
            result = result[:-3]
            
        analysis = json.loads(result.strip())
        
        # Validate the response structure
        required_keys = ["topics", "subjects", "difficulty", "prerequisites"]
        if not all(key in analysis for key in required_keys):
            raise ValueError("Invalid response structure")
            
        if not isinstance(analysis["difficulty"], (int, float)) or not 1 <= analysis["difficulty"] <= 5:
            raise ValueError("Invalid difficulty value")
            
        return analysis
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
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
        
        # Analyze the content
        analysis = analyze_math_content(text_content)
        
        return jsonify({
            "filename": file.filename,
            "analysis": analysis
        })
        
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
                    
                # Extract and analyze content
                text_content = extract_text_from_pdf(file)
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