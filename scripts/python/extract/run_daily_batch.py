import os
import sys
import os
os.environ["POLARS_NO_MMAP"] = "1"
import subprocess
from datetime import datetime, timedelta
import glob
import traceback

# 프로젝트 및 스크립트 경로 정의
BASE_DIR = "/Users/galaxy.jang/anti_codebase"
PYTHON_BIN = os.path.join(BASE_DIR, ".venv", "bin", "python")
EXTRACT_SCRIPT = os.path.join(BASE_DIR, "scripts", "python", "extract", "extract_rich_orders_daily.py")
MONTHLY_USER_SCRIPT = os.path.join(BASE_DIR, "scripts", "python", "extract", "extract_rich_user_monthly.py")
USER_SEGMENT_SCRIPT = os.path.join(BASE_DIR, "scripts", "python", "extract", "extract_rich_user_segment.py")
REPORT_SCRIPT = os.path.join(BASE_DIR, "scripts", "python", "report_daily_ststs_v1", "send_weekly_report.py")

LOG_FILE = os.path.join(BASE_DIR, "scripts", "python", "extract", "log", "cron_run.log")
MARKER_DIR = os.path.join(BASE_DIR, "scripts", "python", "extract", "log")

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} [{level}] {message}\n"
    print(log_line, end="")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        sys.stderr.write(f"Failed to write log: {e}\n")

def cleanup_old_markers(today_str):
    """오늘 날짜 이전의 모든 마커 파일을 안전하게 삭제합니다."""
    try:
        marker_pattern = os.path.join(MARKER_DIR, ".daily_success_*")
        for file_path in glob.glob(marker_pattern):
            filename = os.path.basename(file_path)
            # 오늘 날짜 마커 파일이 아닌 경우에만 삭제
            if today_str not in filename:
                os.remove(file_path)
                log(f"Removed old marker file: {filename}")
    except Exception as e:
        log(f"Error during cleanup of old marker files: {e}", level="ERROR")

def run_subprocess(script_path, args=None):
    """외부 파이썬 스크립트를 가상환경 인터프리터로 실행합니다."""
    cmd = [PYTHON_BIN, script_path]
    if args:
        cmd.extend(args)
    
    log(f"Starting execution of: {os.path.basename(script_path)} {' '.join(args or [])}")
    try:
        # 가상환경의 python 바이너리를 사용해 실행
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        # 실행 결과 로그 기록
        if result.stdout:
            log(f"\n--- {os.path.basename(script_path)} STDOUT ---\n{result.stdout}\n-------------------")
        return True
    except subprocess.CalledProcessError as e:
        log(f"Error running {os.path.basename(script_path)} (Exit code: {e.returncode})", level="ERROR")
        if e.stdout:
            log(f"STDOUT:\n{e.stdout}", level="ERROR")
        if e.stderr:
            log(f"STDERR:\n{e.stderr}", level="ERROR")
        return False
    except Exception as e:
        log(f"Unexpected error running {os.path.basename(script_path)}: {e}", level="ERROR")
        log(traceback.format_exc(), level="ERROR")
        return False

def main():
    today_str = datetime.now().strftime("%Y%m%d")
    marker_file = os.path.join(MARKER_DIR, f".daily_success_{today_str}")
    
    log(f"================ Daily Batch Run Attempt ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ================")
    
    # 1. 중복 실행 확인
    if os.path.exists(marker_file):
        log("오늘 배치 작업이 이미 성공적으로 완료되었습니다. 실행을 생략합니다.")
        log("================ Daily Batch Run Skip ================\n")
        sys.exit(0)
        
    # 2. 필수 범위 내 파케이 파일 누락 체크
    # 리포트 스크립트가 로드하는 데이터의 범위: min(어제 기준 당월 1일, 최근 14일 이전) ~ 어제
    end_dt = datetime.now() - timedelta(days=1)
    month_start = datetime(end_dt.year, end_dt.month, 1)
    fourteen_days_ago = end_dt - timedelta(days=13)
    start_dt = min(month_start, fourteen_days_ago)
    
    log(f"필수 데이터 검사 범위: {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")
    
    curr_dt = start_dt
    missing_dates = []
    while curr_dt <= end_dt:
        dt_str = curr_dt.strftime("%Y-%m-%d")
        file_path = f"/Users/galaxy.jang/Google Drive/공유 드라이브/gbike.rich_orders/dt={dt_str}/rich_orders_{dt_str}.parquet"
        if not os.path.exists(file_path):
            missing_dates.append(dt_str)
        curr_dt += timedelta(days=1)
        
    # 3. 누락된 날짜 데이터 강제 추출
    if missing_dates:
        log(f"누락 데이터 존재 감지: {missing_dates}")
        for dt_str in missing_dates:
            log(f"누락 날짜 데이터 강제 추출 시도: {dt_str}")
            if not run_subprocess(EXTRACT_SCRIPT, [dt_str, dt_str]):
                log(f"{dt_str} 데이터 추출 단계에서 오류가 발생하여 배치 실행을 중단합니다.", level="ERROR")
                log("================ Daily Batch Run Failed ================\n")
                sys.exit(1)
    else:
        log("모든 필수 날짜의 데이터 파케이 파일이 존재합니다. 추가 추출 단계를 생략합니다.")
        
    # 4. 월간 유저 지표 추출
    if not run_subprocess(MONTHLY_USER_SCRIPT):
        log("월간 유저 지표 추출 단계에서 오류가 발생하여 배치 실행을 중단합니다.", level="ERROR")
        log("================ Daily Batch Run Failed ================\n")
        sys.exit(1)
        
    # 5. 유저 세그먼트 데이터 추출
    if not run_subprocess(USER_SEGMENT_SCRIPT):
        log("유저 세그먼트 데이터 추출 단계에서 오류가 발생하여 배치 실행을 중단합니다.", level="ERROR")
        log("================ Daily Batch Run Failed ================\n")
        sys.exit(1)

    # 6. 리포트 전송
    if not run_subprocess(REPORT_SCRIPT):
        log("리포트 발송 단계에서 오류가 발생하여 배치 실행을 중단합니다.", level="ERROR")
        log("================ Daily Batch Run Failed ================\n")
        sys.exit(1)
        
    # 7. 성공 마커 생성
    try:
        with open(marker_file, "w") as f:
            f.write(f"Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log("금일 배치 작업이 모두 정상 종료되었습니다. 성공 마커 파일을 기록합니다.")
    except Exception as e:
        log(f"성공 마커 파일 생성 실패: {e}", level="ERROR")
        
    # 8. 이전 마커 정리
    cleanup_old_markers(today_str)
    
    log("================ Daily Batch Run Completed ================\n")

if __name__ == "__main__":
    main()
