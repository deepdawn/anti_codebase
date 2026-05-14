import sys
import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# 환경 변수 설정 (보안을 위해 파일에서 읽어옴)
ENV_FILE = os.path.join(os.path.dirname(__file__), "../../../.env.teams")

def load_env():
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    env[key] = value
    return env

config = load_env()
SENDER_EMAIL = config.get("SENDER_EMAIL")
SENDER_PASSWORD = config.get("SENDER_PASSWORD")
TEAMS_EMAIL = config.get("TEAMS_EMAIL")
SMTP_SERVER = config.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(config.get("SMTP_PORT", 587))

def send_email(subject, body, attachment_path=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = TEAMS_EMAIL
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return {"status": "success", "message": f"Email sent successfully to {TEAMS_EMAIL}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def list_tools():
    return {
        "tools": [
            {
                "name": "send_to_teams",
                "description": "분석 결과와 인사이트를 MS Teams 채널로 전송합니다.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string", "description": "메일 제목 (추출된 핵심 인사이트 등)"},
                        "body": {"type": "string", "description": "메일 본문 (상세 분석 결과)"},
                        "attachment_path": {"type": "string", "description": "첨부할 파일 경로 (CSV, 이미지 등)"}
                    },
                    "required": ["subject", "body"]
                }
            }
        ]
    }

def main():
    # 간단한 JSON-RPC 형태의 MCP stdio 커뮤니케이션 모사
    # 실제로는 mcp 라이브러리를 사용하지만, 여기서는 기본 통신 로직을 구현합니다.
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            request = json.loads(line)
            
            # MCP 프로토콜 처리 (Initialize, ListTools, CallTool 등)
            if request.get("method") == "initialize":
                response = {"jsonrpc": "2.0", "id": request.get("id"), "result": {"protocolVersion": "2024-11-05", "capabilities": {}}}
            elif request.get("method") == "tools/list":
                response = {"jsonrpc": "2.0", "id": request.get("id"), "result": list_tools()}
            elif request.get("method") == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "send_to_teams":
                    result = send_email(**arguments)
                    response = {"jsonrpc": "2.0", "id": request.get("id"), "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
                else:
                    response = {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32601, "message": "Method not found"}}
            else:
                response = {"jsonrpc": "2.0", "id": request.get("id"), "result": {}}

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except EOFError:
            break
        except Exception as e:
            error_response = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
