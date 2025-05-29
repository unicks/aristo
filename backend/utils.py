import json
import re
import os
import numpy as np
from typing import Dict, List
from PyPDF2 import PdfReader # Added for PDF extraction

TABLE_OUTPUT_PATH = "graded_table.tex"

def escape_latex(text: str):
    return (text.replace('\\', r'\\')
                .replace('_', r'\_')
                .replace('%', r'\%')
                .replace('$', r'\$')
                .replace('&', r'\&')
                .replace('#', r'\#')
                .replace('{', r'\{')
                .replace('}', r'\}')
                .replace('^', r'\^{}')
                .replace('~', r'\~{}'))

def extract_valid_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[\s*{.*?}\s*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
        return None

def save_table_to_latex(structured_data, output_path=TABLE_OUTPUT_PATH):
    lines = [
        r"\documentclass{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{bidi}",
        r"\usepackage{geometry}",
        r"\geometry{margin=2.5cm}",
        r"\begin{document}",
        r"\section*{טבלת ציונים}",
        r"\begin{RTL}",
        r"\begin{tabular}{|c|c|c|p{10cm}|}",
        r"\hline",
        r"שאלה & סעיף & ציון & הערה \\",
        r"\hline"
    ]

    for item in structured_data:
        q = item.get("שאלה", "")
        s = item.get("סעיף", "")
        g = item.get("ציון", "")
        c = escape_latex(item.get("הערה", ""))
        lines.append(f"{q} & {s} & {g} & {c} \\\\ \\hline")

    lines += [r"\end{tabular}", r"\end{RTL}", r"\end{document}"]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def summarize_feedback(feedback: list) -> dict:
    '''
    Given a list of feedback items (each with ציון and הערה),
    returns a summary containing average grade and a master comment.
    '''
    feedback = feedback["feedback"]
    scores = [item.get("ציון", 0) for item in feedback if isinstance(item, dict)]
    average = sum(scores) / len(scores) if scores else 0

    if average == 100:
        comment = "הפתרון מושלם – כל הסעיפים נבדקו בהצלחה מלאה."
    elif average >= 85:
        comment = "הפתרון טוב מאוד עם כמה נקודות לשיפור."
    elif average >= 70:
        comment = "יש צורך בחיזוק בחלק מהסעיפים, אך יש הבנה כללית."
    else:
        comment = "נדרש שיפור משמעותי במענה על השאלות."

    return {
        "final_grade": round(average, 2),
        "master_comment": comment
    }

# Helper functions for the /choose endpoint
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file using PyPDF2."""
    try:
        reader = PdfReader(pdf_path)
        text_content = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_content.append(text)
        return '\n'.join(text_content)
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        return ""

def get_file_content(file_path: str) -> bytes:
    """Gets the content of a file, handling both .lyx and .pdf files."""
    if file_path.lower().endswith('.pdf'):
        text_content = extract_text_from_pdf(file_path)
        return text_content.encode('utf-8')
    else:
        with open(file_path, 'rb') as f:
            return f.read()

def get_embedding(client, content: bytes) -> List[float]: # Added client parameter
    """Gets embedding for content using Gemini API."""
    try:
        content_str = content.decode('utf-8', errors='replace')
        result = client.models.embed_content(
            model="embedding-001",
            contents=content_str
        )
        return result.embeddings
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two vectors."""
    v1_np = np.array(v1)
    v2_np = np.array(v2)
    return np.dot(v1_np, v2_np) / (np.linalg.norm(v1_np) * np.linalg.norm(v2_np))

