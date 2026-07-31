#!/bin/bash

# 로그 파일 경로
LOG_FILE="/Users/galaxy.jang/anti_codebase/scripts/python/extract/log/cron_run.log"

# 로그 디렉토리 생성 보장
mkdir -p "$(dirname "$LOG_FILE")"

# 로그 출력 함수
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "$LOG_FILE"
}

log_err() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "$LOG_FILE"
}

log "================ Daily Cron Batch Start ================"

# 환경 변수 명시적 설정 (crontab 대응)
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

# 사용자 정의 배치 스크립트 실행
log "Running run_daily_batch.py..."
python /Users/galaxy.jang/anti_codebase/scripts/python/extract/run_daily_batch.py >> "$LOG_FILE" 2>&1
BATCH_STATUS=$?

if [ $BATCH_STATUS -ne 0 ]; then
    log_err "run_daily_batch.py failed with exit code $BATCH_STATUS"
    exit $BATCH_STATUS
fi
log "run_daily_batch.py completed successfully."

log "================ Daily Cron Batch End ================"
