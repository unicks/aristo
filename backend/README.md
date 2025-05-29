# Math Question PDF Analyzer

A Flask-based service that analyzes mathematical questions from PDF files, providing topic classification, difficulty assessment, and prerequisite identification.

## Features

- ✨ Analyze single or multiple PDF math questions
- 🏷️ Extract mathematical topics and subjects
- 📊 Assess difficulty level (1-5 scale)
- 📝 Identify prerequisites
- 🔄 Batch processing support
- ✅ Input validation and error handling

## Setup

### Prerequisites

- Python 3.8+
- Flask
- Google Generative AI (Gemini)
- PDF processing libraries (pdfplumber, PyPDF2)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your Gemini API key:
   - Get your API key from Google AI Studio
   - The key is currently configured in `server.py` but for production, you should use environment variables:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

## Usage

### Starting the Server

```bash
python server.py
```

The server will start on `http://localhost:5000`

### API Endpoints

#### 1. Analyze a Single PDF File
- **Endpoint**: `/analyzer/analyze-single`
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Request**:
  ```bash
  curl -X POST -F "file=@your_question.pdf" http://localhost:5000/analyzer/analyze-single
  ```
- **Response**:
  ```json
  {
    "filename": "example.pdf",
    "analysis": {
      "topics": ["Calculus", "Linear Algebra"],
      "subjects": ["Integration", "Matrix Operations"],
      "difficulty": 3,
      "prerequisites": ["Basic Calculus", "Vector Spaces"]
    }
  }
  ```

#### 2. Analyze Multiple PDF Files
- **Endpoint**: `/analyzer/analyze-batch`
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Request**:
  ```bash
  curl -X POST \
    -F "pdf_files=@file1.pdf" \
    -F "pdf_files=@file2.pdf" \
    http://localhost:5000/analyzer/analyze-batch
  ```
- **Response**:
  ```json
  {
    "total_files": 2,
    "analyzed_files": 2,
    "results": [
      {
        "filename": "file1.pdf",
        "analysis": {
          "topics": ["..."],
          "subjects": ["..."],
          "difficulty": 4,
          "prerequisites": ["..."]
        }
      },
      {
        "filename": "file2.pdf",
        "analysis": {
          "topics": ["..."],
          "subjects": ["..."],
          "difficulty": 2,
          "prerequisites": ["..."]
        }
      }
    ]
  }
  ```

#### 3. Grade PDF Solutions
- **Endpoint**: `/grade`
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Parameters**:
  - `file`: PDF file to grade
  - `context` (optional): JSON file with grading context
- **Request**:
  ```bash
  curl -X POST \
    -F "file=@solution.pdf" \
    -F "context=@context.json" \
    http://localhost:5000/grade
  ```

## Error Handling

The API returns appropriate HTTP status codes:
- 200: Successful operation
- 400: Bad request (invalid input)
- 500: Server error

Error responses include a descriptive message:
```json
{
  "error": "Description of what went wrong"
}
```

## Difficulty Scale

The difficulty assessment uses a 1-5 scale:
1. Basic - Fundamental concepts
2. Easy - Simple application of concepts
3. Moderate - Multiple concepts, some problem-solving
4. Challenging - Complex problem-solving
5. Advanced - Advanced concepts, sophisticated reasoning

## Project Structure

```
.
├── README.md
├── server.py           # Main Flask application
├── latex_analyzer.py   # PDF analysis functionality
└── utils.py           # Utility functions
```

## Security Considerations

- The API key should be stored as an environment variable in production
- Input validation is implemented for all endpoints
- File size limits should be configured in production
- CORS policies should be configured based on deployment needs
- PDF files are validated before processing

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 