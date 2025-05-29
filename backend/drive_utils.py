import os
import io
from typing import List, Dict
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from PyPDF2 import PdfReader

# Path to your client_secrets.json
CLIENT_SECRETS_PATH = r'C:\Users\maork\aristo\backend\client_secrets.json'

def authenticate_drive(client_secrets_path: str = CLIENT_SECRETS_PATH) -> GoogleDrive:
    """
    Authenticates the user with Google Drive and returns a GoogleDrive object.
    """
    GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = client_secrets_path
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Opens browser for authentication
    return GoogleDrive(gauth)

def list_shared_folders(drive: GoogleDrive) -> List[Dict]:
    """
    Lists folders shared with the authenticated user.
    """
    return drive.ListFile({
        'q': "mimeType='application/vnd.google-apps.folder' and sharedWithMe"
    }).GetList()

def list_files_in_folder(drive: GoogleDrive, folder_id: str) -> List[Dict]:
    """
    Lists all non-trashed files in a specified folder.
    """
    return drive.ListFile({
        'q': f"'{folder_id}' in parents and trashed=false"
    }).GetList()

def download_file(drive_file, save_path: str):
    """
    Downloads a file to the local file system.
    """
    drive_file.GetContentFile(save_path)

def extract_first_page_text(drive_file) -> str:
    """
    Extracts text from the first page of a PDF file stored in Drive.
    """
    content = drive_file.GetContentString(encoding='ISO-8859-1')
    pdf_stream = io.BytesIO(content.encode('ISO-8859-1'))
    reader = PdfReader(pdf_stream)

    if reader.pages:
        return reader.pages[0].extract_text()
    return "No pages found."
