import os
import sys
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def send_google_chat_message(creds_path, space_name, text_message, image_path=None):
    """Google Chat API를 사용하여 메시지와 이미지를 전송합니다."""
    SCOPES = ['https://www.googleapis.com/auth/chat.messages.create']
    creds = None
    token_path = os.path.join(os.path.dirname(creds_path), 'token_chat.json')
    
    try:
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
                
        chat = build('chat', 'v1', credentials=creds)
        
        message = {'text': text_message}
        parent_space = space_name if space_name.startswith('spaces/') else f"spaces/{space_name}"
        
        if image_path:
            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload(image_path, mimetype='image/png')
            attachment_resp = chat.media().upload(
                parent=parent_space,
                body={'filename': os.path.basename(image_path)},
                media_body=media
            ).execute()
            
            if 'attachmentDataRef' in attachment_resp:
                message['attachment'] = [{'attachmentDataRef': attachment_resp['attachmentDataRef']}]
            elif attachment_resp.get('resourceName'):
                message['attachment'] = [{'attachmentDataRef': {'resourceName': attachment_resp['resourceName']}}]
        
        result = chat.spaces().messages().create(
            parent=parent_space,
            body=message
        ).execute()
        
        print(f"메시지 전송 성공: {result.get('name')}")
        return True
        
    except Exception as e:
        print(f"메시지 전송 실패: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Chat 메신저 알림 전송 스크립트")
    parser.add_argument("--space", required=True, help="구글 스페이스 ID (예: AAQAf0HeYv0)")
    parser.add_argument("--msg", required=True, help="전송할 텍스트 메시지")
    args = parser.parse_args()
    
    # 공통 인증 파일 경로
    creds_file = "/Users/galaxy.jang/anti_codebase/.etc/workspace_desktop_chat_galaxy.json"
    
    send_google_chat_message(creds_file, args.space, args.msg)
