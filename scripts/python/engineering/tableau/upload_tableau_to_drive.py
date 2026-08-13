import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 인증 정보 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.abspath(os.path.join(current_dir, '..', '..', 'maco_googlesheet', 'credentials.json'))
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def find_shared_drive_id(service, drive_name):
    # 공유 드라이브 목록 조회
    results = service.drives().list(pageSize=100).execute()
    drives = results.get('drives', [])
    for drive in drives:
        if drive['name'] == drive_name:
            return drive['id']
    return None

def upload_file_to_drive(service, local_file_path, file_name, folder_id, drive_id):
    # 기존 파일이 있는지 확인
    query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        corpora='drive',
        driveId=drive_id,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields='files(id, name)'
    ).execute()
    files = results.get('files', [])
    
    # Chunk 단위로 업로드하는 MediaFileUpload 객체 생성
    media = MediaFileUpload(local_file_path, mimetype='text/csv', resumable=True)
    
    if files:
        # 기존 파일 덮어쓰기 (Update)
        file_id = files[0]['id']
        print(f"Updating existing file in Drive: {file_name} (ID: {file_id})")
        request = service.files().update(
            fileId=file_id,
            media_body=media,
            supportsAllDrives=True
        )
    else:
        # 새 파일 생성 (Create)
        print(f"Creating new file in Drive: {file_name}")
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        request = service.files().create(
            body=file_metadata,
            media_body=media,
            supportsAllDrives=True
        )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
    print(f"Upload Complete: {file_name}")

def process_upload(service, local_path, file_name, shared_drive_name):
    print(f"--- Processing {file_name} ---")
    drive_id = find_shared_drive_id(service, shared_drive_name)
    if not drive_id:
        print(f"Shared Drive '{shared_drive_name}' not found!")
        return
        
    # 신규 "tableau_data" 공유 드라이브의 최상단(root)에 바로 업로드
    upload_file_to_drive(service, local_path, file_name, drive_id, drive_id)

def main():
    service = get_drive_service()
    
    # 모두 동일한 공유 드라이브 "tableau_data" 로 업로드
    tasks = [
        {
            "local_path": "/Users/galaxy.jang/tableau_data/by_time(시간대별).csv",
            "file_name": "by_time(시간대별).csv",
            "drive_name": "tableau_data"
        },
        {
            "local_path": "/Users/galaxy.jang/tableau_data/used_time(출루까지시간).csv",
            "file_name": "used_time(출루까지시간).csv",
            "drive_name": "tableau_data"
        },
        {
            "local_path": "/Users/galaxy.jang/tableau_data/OBP(출루율).csv",
            "file_name": "OBP(출루율).csv",
            "drive_name": "tableau_data"
        }
    ]
    
    for task in tasks:
        if os.path.exists(task["local_path"]):
            try:
                process_upload(service, task["local_path"], task["file_name"], task["drive_name"])
            except Exception as e:
                print(f"Error uploading {task['file_name']}: {e}")
        else:
            print(f"File not found: {task['local_path']}")

if __name__ == '__main__':
    main()
