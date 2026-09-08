import os
import sys
import argparse
import json

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    print("slack_sdk 라이브러리가 설치되어 있지 않습니다. 아래 명령어로 설치해주세요.")
    print("pip install slack_sdk")
    sys.exit(1)

def load_slack_tokens(creds_path):
    """지정된 경로의 JSON 파일에서 슬랙 토큰을 불러옵니다."""
    if not os.path.exists(creds_path):
        print(f"토큰 파일이 존재하지 않습니다: {creds_path}")
        return None, None
    with open(creds_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            return data.get("SLACK_BOT_TOKEN"), data.get("SLACK_APP_TOKEN")
        except json.JSONDecodeError:
            print("토큰 파일의 JSON 형식이 올바르지 않습니다.")
            return None, None

def send_slack_message(creds_path, channel, text_message, image_path=None):
    """Slack API를 사용하여 메시지와 이미지를 전송합니다."""
    bot_token, app_token = load_slack_tokens(creds_path)
    if not bot_token:
        return False
        
    client = WebClient(token=bot_token)
    
    try:
        if image_path:
            if not os.path.exists(image_path):
                print(f"이미지 파일이 존재하지 않습니다: {image_path}")
                return False
                
            # 이미지 파일 업로드 (files.upload_v2 권장)
            # 파일과 함께 initial_comment로 텍스트 메시지를 보냅니다.
            result = client.files_upload_v2(
                channel=channel,
                initial_comment=text_message,
                file=image_path
            )
            print(f"이미지 및 메시지 전송 성공 (File ID: {result.get('file', {}).get('id')})")
        else:
            # 텍스트 메시지만 전송
            result = client.chat_postMessage(
                channel=channel,
                text=text_message
            )
            print(f"메시지 전송 성공 (TS: {result['ts']})")
        return True
    except SlackApiError as e:
        print(f"메시지 전송 실패: {e.response['error']}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Slack 메신저 알림 전송 스크립트")
    parser.add_argument("--channel", required=True, help="채널명 또는 채널 ID (예: #general 또는 C123456)")
    parser.add_argument("--msg", required=True, help="전송할 텍스트 메시지")
    parser.add_argument("--image", required=False, help="전송할 이미지 파일 경로 (옵션)")
    args = parser.parse_args()
    
    # 공통 인증 파일 경로
    creds_file = f"{os.path.expanduser('~')}/anti_codebase/.etc/slack_token.json"
    
    send_slack_message(creds_file, args.channel, args.msg, args.image)
