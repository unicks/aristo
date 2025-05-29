from drive_utils import *

def main():
    drive = authenticate_drive()

    print("🔍 Folders shared with you:\n")
    folders = list_shared_folders(drive)
    for folder in folders:
        print(f"📁 {folder['title']} | ID: {folder['id']}")

    # Choose a folder by ID
    FOLDER_ID = '0B4NFaiXelmmkelRNeFpRMHlVX2M'
    files = list_files_in_folder(drive, FOLDER_ID)

    for f in files:
        if f['mimeType'] == 'application/pdf':
            download_file(f, 'downloaded.pdf')
            break
if __name__ == "__main__":
    main()
