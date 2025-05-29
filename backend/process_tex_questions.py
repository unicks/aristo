import os
import requests
import json
import logging
from pathlib import Path
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tex_questions_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
API_URL = "http://localhost:5000"
QUESTIONS_DIR = "tex_questions"
RESULTS_DIR = "analysis_results"

def ensure_directory(directory):
    """Create directory if it doesn't exist."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def process_file(file_path):
    """Process a single PDF file through the analyzer API."""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{API_URL}/analyze/single", files=files)
            
        if response.status_code == 200:
            result = response.json()
            if "analysis" in result:
                return result["analysis"]
            else:
                logger.error(f"Invalid response format for {file_path}: {result}")
                return None
        else:
            logger.error(f"API request failed for {file_path}: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return None

def save_results(results, filename):
    """Save analysis results to a JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(RESULTS_DIR, f"{filename}_{timestamp}.json")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving results to {output_file}: {str(e)}")

def main():
    """Main function to process all PDF files."""
    try:
        # Ensure directories exist
        ensure_directory(QUESTIONS_DIR)
        ensure_directory(RESULTS_DIR)
        
        # Get list of PDF files
        pdf_files = [f for f in os.listdir(QUESTIONS_DIR) if f.endswith('.pdf')]
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Process each file
        for pdf_file in pdf_files:
            file_path = os.path.join(QUESTIONS_DIR, pdf_file)
            logger.info(f"Processing {pdf_file}")
            
            try:
                # Process the file
                result = process_file(file_path)
                print(result)
                if result:
                    # Extract question text and analysis values
                    questions = []
                    
                    # Process each question in the analysis
                    for question_key, question_data in result.items():
                        if not question_key.startswith('question'):
                            continue
                            
                        if not isinstance(question_data, dict):
                            logger.error(f"Invalid question data format for {question_key}")
                            continue
                            
                        if 'values' not in question_data:
                            logger.error(f"Missing 'values' field in {question_key}")
                            continue
                            
                        values = question_data['values']
                        required_fields = ['topics', 'subjects', 'difficulty', 'prerequisites']
                        
                        # Validate required fields
                        if not all(field in values for field in required_fields):
                            logger.error(f"Missing required fields in {question_key}")
                            continue
                            
                        # Validate field types
                        if not isinstance(values['topics'], list) or not values['topics']:
                            logger.error(f"Invalid topics format in {question_key}")
                            continue
                        if not isinstance(values['subjects'], list) or not values['subjects']:
                            logger.error(f"Invalid subjects format in {question_key}")
                            continue
                        if not isinstance(values['difficulty'], (int, float)) or not 1 <= values['difficulty'] <= 5:
                            logger.error(f"Invalid difficulty value in {question_key}")
                            continue
                        if not isinstance(values['prerequisites'], list):
                            logger.error(f"Invalid prerequisites format in {question_key}")
                            continue
                            
                        # Add valid question to results
                        questions.append({
                            'question_text': question_key,
                            'topics': values['topics'],
                            'subjects': values['subjects'],
                            'difficulty': values['difficulty'],
                            'prerequisites': values['prerequisites']
                        })
                    
                    # Save results if we have valid questions
                    if questions:
                        save_results({
                            'filename': pdf_file,
                            'questions': questions
                        }, pdf_file)
                        logger.info(f"Successfully processed {pdf_file} with {len(questions)} questions")
                    else:
                        logger.warning(f"No valid questions found in {pdf_file}")
                else:
                    logger.error(f"Failed to process {pdf_file}")
                    
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {str(e)}")
                logger.error(traceback.format_exc())
                
        logger.info("Processing completed")
        
    except Exception as e:
        logger.error(f"Main process error: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 