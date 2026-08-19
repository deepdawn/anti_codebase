import os
import sys
import time
import subprocess
import pyautogui
import pyotp
import pyperclip
from dotenv import load_dotenv

# 스크립트 실행 경로를 기준으로 .env 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))

VPN_ID = os.getenv("VPN_ID")
VPN_PW = os.getenv("VPN_PW")
VPN_TOTP_SECRET = os.getenv("VPN_TOTP_SECRET")
CONNECT_BTN_IMG = os.path.join(current_dir, "forticlient_connect_btn.png")

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def main():
    if not all([VPN_ID, VPN_PW, VPN_TOTP_SECRET]):
        log("오류: .env 파일에 VPN_ID, VPN_PW, VPN_TOTP_SECRET가 설정되지 않았습니다.")
        sys.exit(1)

    if not os.path.exists(CONNECT_BTN_IMG):
        log(f"오류: Connect 버튼 이미지({CONNECT_BTN_IMG})를 찾을 수 없습니다. 캡처본을 저장해주세요.")
        sys.exit(1)

    # 1. FortiClient 앱 활성화
    log("FortiClient 앱을 실행/활성화합니다.")
    subprocess.run(["open", "-a", "FortiClient"], check=True)
    time.sleep(3) # 앱이 완전히 뜨고 렌더링될 때까지 대기

    # 2. Connect 버튼 이미지 매칭 및 클릭
    log("Connect 버튼 위치를 찾고 있습니다...")
    try:
        connect_btn_location = pyautogui.locateCenterOnScreen(CONNECT_BTN_IMG, confidence=0.8)
        
        if connect_btn_location is not None:
            log(f"Connect 버튼 발견: {connect_btn_location}")
            click_x = int(connect_btn_location.x / 2)
            click_y = int(connect_btn_location.y / 2)
            
            log(f"마우스를 이동하여 클릭합니다: (x={click_x}, y={click_y})")
            pyautogui.moveTo(click_x, click_y, duration=0.5)
            pyautogui.click()
        else:
            log("Connect 버튼을 찾을 수 없습니다. 화면이 켜져 있는지 확인하세요.")
            sys.exit(1)
    except pyautogui.ImageNotFoundException:
        log("이미지 매칭 실패: 화면에서 Connect 버튼을 찾을 수 없습니다.")
        sys.exit(1)
    except Exception as e:
        log(f"버튼 탐색 중 예기치 않은 오류 발생: {e}")
        sys.exit(1)

    # 3. 브라우저 팝업 대기
    log("SSO 브라우저 팝업을 대기합니다 (5초)...")
    time.sleep(5)

    # 4. ID / PW 입력
    log("로그인 정보(ID/PW)를 입력합니다.")
    
    pyperclip.copy(VPN_ID)
    pyautogui.hotkey('command', 'v')
    time.sleep(0.3)
    pyautogui.press('tab')
    
    time.sleep(1)
    
    pyperclip.copy(VPN_PW)
    pyautogui.hotkey('command', 'v')
    time.sleep(0.3)
    pyautogui.press('enter')

    # 5. OTP (2FA) 입력
    log("2FA(OTP) 페이지 로딩 대기 (5초)...")
    time.sleep(2)
    
    log("OTP 코드를 생성하고 입력합니다.")
    totp = pyotp.TOTP(VPN_TOTP_SECRET)
    otp_code = totp.now()
    
    pyperclip.copy(otp_code)
    pyautogui.hotkey('command', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')

    # 6. 완료 대기
    log("로그인 완료 대기 (5초)...")
    time.sleep(5)
    
    log("VPN 자동 연결 스크립트 실행이 종료되었습니다.")

if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    main()
