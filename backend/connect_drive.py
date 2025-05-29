import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import io
from PyPDF2 import PdfReader

# Authenticate and create the PyDrive client
gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # Opens browser for authentication
drive = GoogleDrive(gauth)

# List all shared files (files shared with you)
file_list = drive.ListFile({'q': "'me' in owners or sharedWithMe = true and mimeType = 'application/pdf' and trashed=false"}).GetList()

print("PDF files shared with you:")
for file in file_list:
    print(f"Title: {file['title']}, ID: {file['id']}")
    # Download the file content into memory
    file_content = file.GetContentString(encoding='ISO-8859-1')
    pdf_stream = io.BytesIO(file_content.encode('ISO-8859-1'))
    reader = PdfReader(pdf_stream)
    print("First page text:")
    if reader.pages:
        print(reader.pages[0].extract_text())
    print("-" * 40)