import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys

def send_teams_summary():
    sender_email = "deepdawn108@gmail.com"
    sender_password = "gycusrnitwstqtej"
    teams_email = "a3fe7a69.gbike.io@kr.teams.ms"
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = teams_email
    msg['Subject'] = "[보고] gbike 매출 데이터 추출 완료 (0101_0228)"

    body = """
[gbike 데이터 추출 완료 보고]

사용자 요청에 따라 1~2월 gbike 매출 데이터를 성공적으로 추출하였습니다.

1. 추출 기간: 2026-01-01 ~ 2026-02-28
2. 데이터 규모: 총 103,740행
3. 저장 경로: /Users/galaxy/anti_codebase/results/data_extract/0101_0228_gbike_revenue_extract.xlsx
4. 주요 작업 내용:
   - 파일명 자동 생성 로직 적용 (기간 prefix 추가)
   - 4일 단위 분할 추출을 통한 DB 안정성 확보
   - 데이터 병합 및 Excel 파일 변환 완료

수석 데이터 사이언티스트 Antigravity 드림
"""
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Successfully sent summary to Teams: {teams_email}")
    except Exception as e:
        print(f"Failed to send message: {e}")

if __name__ == "__main__":
    send_teams_summary()
