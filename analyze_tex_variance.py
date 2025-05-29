import os
import google.genai as genai
import numpy as np
from typing import Dict, List
import sys
from PyPDF2 import PdfReader

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file using PyPDF2."""
    try:
        # Create a PDF reader object
        reader = PdfReader(pdf_path)
        
        # Extract text from all pages
        text_content = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_content.append(text)
        
        # Join all text content with newlines
        return '\n'.join(text_content)
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        return ""

def get_file_content(file_path: str) -> bytes:
    """Gets the content of a file, handling both .lyx and .pdf files."""
    if file_path.lower().endswith('.pdf'):
        # Extract text from PDF
        text_content = extract_text_from_pdf(file_path)
        return text_content.encode('utf-8')
    else:
        # Read .lyx file as binary
        with open(file_path, 'rb') as f:
            return f.read()

def get_embedding(api_key: str, content: bytes) -> List[float]:
    """Gets embedding for content using Gemini API."""
    client = genai.Client(api_key=api_key)
    try:
        # Convert bytes to string, preserving encoding
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

def main():
    if len(sys.argv) < 4:
        print("Usage: python analyze_tex_variance.py API_KEY NUM_VARIED_FILES FILE1 [FILE2 ...]")
        print("Example: python analyze_tex_variance.py YOUR_API_KEY 2 file1.lyx file2.lyx file3.lyx")
        return

    api_key = sys.argv[1]
    try:
        num_varied_files = int(sys.argv[2])
    except ValueError:
        print("Error: Number of varied files must be an integer.")
        return

    files = sys.argv[3:]

    if len(files) < 2:
        print("Error: At least two files are required for comparison.")
        return

    if num_varied_files <= 0:
        print("Error: Number of varied files (Y) must be positive.")
        return

    if num_varied_files > len(files):
        print("Warning: Number of varied files (Y) is greater than the total number of input files. "
              "Will return all files sorted by variance.")
        num_varied_files = len(files)

    # Get embeddings for all files
    print("Getting embeddings for all files...")
    file_embeddings: Dict[str, List[float]] = {}
    
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"Warning: File not found: {file_path}. Skipping.")
            continue
        try:
            content = get_file_content(file_path)
            print(f"Processing {file_path}...")
            embedding = get_embedding(api_key, content)
            if embedding:
                file_embeddings[file_path] = embedding
            else:
                print(f"Skipping {file_path} due to embedding error.")
        except Exception as e:
            print(f"Error processing file {file_path}: {e}. Skipping.")

    if len(file_embeddings) < 2:
        print("Error: Less than two files were successfully processed. Cannot perform comparison.")
        return

    # Calculate dissimilarity scores using cosine similarity
    print("\nCalculating similarity scores...")
    similarity_scores: Dict[str, float] = {}
    file_paths = list(file_embeddings.keys())

    # Initialize scores for all files
    for path in file_paths:
        similarity_scores[path] = 0.0
    
    # Calculate pairwise similarities
    for i in range(len(file_paths)):
        for j in range(i + 1, len(file_paths)):
            path1 = file_paths[i]
            path2 = file_paths[j]
            embedding1 = file_embeddings[path1]
            embedding2 = file_embeddings[path2]

            # Get cosine similarity (ranges from -1 to 1, where 1 means identical)
            similarity = cosine_similarity(embedding1[0].values, embedding2[0].values)
            
            # Add similarity scores to both files
            similarity_scores[path1] += similarity
            similarity_scores[path2] += similarity

    # Sort files by their total similarity score in ascending order
    # (lower similarity means more different from others)
    sorted_files = sorted(similarity_scores.items(), key=lambda item: item[1])

    print(f"\nTop {num_varied_files} most varied files (lowest similarity scores):")
    for i in range(min(num_varied_files, len(sorted_files))):
        file_path, score = sorted_files[i]
        print(f"- {file_path} (Total Similarity: {score:.4f})")

if __name__ == "__main__":
    main() 