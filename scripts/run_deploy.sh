#!/bin/bash

# 로그 파일 경로
LOG_FILE="/Users/galaxy.jang/anti_codebase/scripts/python/extract/log/run_deploy.log"

# 로그 디렉토리 생성 보장
mkdir -p "$(dirname "$LOG_FILE")"

# 로그 출력 함수
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "$LOG_FILE"
}

log_err() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "$LOG_FILE"
}

log "================ Daily Deploy Batch Start ================"

# 환경 변수 명시적 설정 (launchd 대응)
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/local/sbin"
export LANG="ko_KR.UTF-8"
export LC_ALL="ko_KR.UTF-8"
export POLARS_NO_MMAP="1"

# 프로젝트 가상환경 활성화
VENV_PATH="/Users/galaxy.jang/anti_codebase/.venv"
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    log "Virtual environment activated."
else
    log_err "Virtual environment not found at $VENV_PATH"
    exit 1
fi

# 1. extract_rich_deploy_zone_usages.py 실행
log "Running extract_rich_deploy_zone_usages.py..."
python /Users/galaxy.jang/anti_codebase/scripts/python/extract/extract_rich_deploy_zone_usages.py >> "$LOG_FILE" 2>&1
EXTRACT_STATUS=$?

if [ $EXTRACT_STATUS -ne 0 ]; then
    log_err "extract_rich_deploy_zone_usages.py failed with exit code $EXTRACT_STATUS"
    exit $EXTRACT_STATUS
fi
log "extract_rich_deploy_zone_usages.py completed successfully."

# 1.3 extract_rich_deploy_used_time.py 실행
log "Running extract_rich_deploy_used_time.py..."
python /Users/galaxy.jang/anti_codebase/scripts/python/extract/extract_rich_deploy_used_time.py >> "$LOG_FILE" 2>&1
USED_TIME_STATUS=$?

if [ $USED_TIME_STATUS -ne 0 ]; then
    log_err "extract_rich_deploy_used_time.py failed with exit code $USED_TIME_STATUS"
    exit $USED_TIME_STATUS
fi
log "extract_rich_deploy_used_time.py completed successfully."

# 1.4 extract_rich_deploy_by_time.py 실행
log "Running extract_rich_deploy_by_time.py..."
python /Users/galaxy.jang/anti_codebase/scripts/python/extract/extract_rich_deploy_by_time.py >> "$LOG_FILE" 2>&1
BY_TIME_STATUS=$?

if [ $BY_TIME_STATUS -ne 0 ]; then
    log_err "extract_rich_deploy_by_time.py failed with exit code $BY_TIME_STATUS"
    exit $BY_TIME_STATUS
fi
log "extract_rich_deploy_by_time.py completed successfully."

# 1.5 update_tableau_obp_csv.py 실행 (Tableau CSV 증분 업데이트)
log "Running update_tableau_obp_csv.py..."
python /Users/galaxy.jang/anti_codebase/scripts/python/extract/update_tableau_obp_csv.py >> "$LOG_FILE" 2>&1
UPDATE_CSV_STATUS=$?

if [ $UPDATE_CSV_STATUS -ne 0 ]; then
    log_err "update_tableau_obp_csv.py failed with exit code $UPDATE_CSV_STATUS"
    exit $UPDATE_CSV_STATUS
fi
log "update_tableau_obp_csv.py completed successfully."

# 1.6 update_tableau_used_time_csv.py 실행
log "Running update_tableau_used_time_csv.py..."
python /Users/galaxy.jang/anti_codebase/scripts/python/extract/update_tableau_used_time_csv.py >> "$LOG_FILE" 2>&1
UPDATE_USED_TIME_STATUS=$?

if [ $UPDATE_USED_TIME_STATUS -ne 0 ]; then
    log_err "update_tableau_used_time_csv.py failed with exit code $UPDATE_USED_TIME_STATUS"
    exit $UPDATE_USED_TIME_STATUS
fi
log "update_tableau_used_time_csv.py completed successfully."

# 1.7 update_tableau_by_time_csv.py 실행
log "Running update_tableau_by_time_csv.py..."
python /Users/galaxy.jang/anti_codebase/scripts/python/extract/update_tableau_by_time_csv.py >> "$LOG_FILE" 2>&1
UPDATE_BY_TIME_STATUS=$?

if [ $UPDATE_BY_TIME_STATUS -ne 0 ]; then
    log_err "update_tableau_by_time_csv.py failed with exit code $UPDATE_BY_TIME_STATUS"
    exit $UPDATE_BY_TIME_STATUS
fi
log "update_tableau_by_time_csv.py completed successfully."

# 2. send_daily_deploy_report.py 실행
log "Running send_daily_deploy_report.py..."
python /Users/galaxy.jang/anti_codebase/scripts/python/report_daily_deploy_v1/send_daily_deploy_report.py >> "$LOG_FILE" 2>&1
REPORT_STATUS=$?

if [ $REPORT_STATUS -ne 0 ]; then
    log_err "send_daily_deploy_report.py failed with exit code $REPORT_STATUS"
    exit $REPORT_STATUS
fi
log "send_daily_deploy_report.py completed successfully."

log "================ Daily Deploy Batch End ================"
