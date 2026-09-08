#!/bin/bash

# 로그 파일 경로
LOG_FILE="$HOME/anti_codebase/scripts/python/maco_googlesheet/log/cron_run.log"

# 로그 디렉토리 생성 보장
mkdir -p "$(dirname "$LOG_FILE")"

# 로그 출력 함수
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "$LOG_FILE"
}

log_err() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "$LOG_FILE"
}

log "================ Maco Googlesheet Batch Start ================"

# 환경 변수 명시적 설정
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/local/sbin"
export LANG="ko_KR.UTF-8"
export LC_ALL="ko_KR.UTF-8"
export POLARS_NO_MMAP="1"

# 프로젝트 가상환경 활성화
VENV_PATH="$HOME/anti_codebase/.venv"
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    log "Virtual environment activated."
else
    log_err "Virtual environment not found at $VENV_PATH"
    exit 1
fi

SCRIPTS_DIR="$HOME/anti_codebase/scripts/python/maco_googlesheet"
UTILS_DIR="$HOME/anti_codebase/scripts/python/utils"
SLACK_CHANNEL="C0C04B1TH4N"

# 작업 시작 알림
python "$UTILS_DIR/send_slack_msg.py" --channel "$SLACK_CHANNEL" --msg "🚀 스프레드시트 자동 업데이트 프로세스 시작" >> "$LOG_FILE" 2>&1


# 실행할 스크립트 목록 (요청하신 7개 파일)
SCRIPTS=(
    "revenue.py"
    "week.py"
    "dayrv.py"
    "booster.py"
    "daybs.py"
    "reba.py"
    "complains.py"
)

for script in "${SCRIPTS[@]}"; do
    log "Running $script..."
    python "$SCRIPTS_DIR/$script" >> "$LOG_FILE" 2>&1
    STATUS=$?
    if [ $STATUS -ne 0 ]; then
        log_err "$script failed with exit code $STATUS"
        python "$UTILS_DIR/send_slack_msg.py" --channel "$SLACK_CHANNEL" --msg "❌ $script 구글시트 업데이트 스크립트 실패 (exit code: $STATUS)" >> "$LOG_FILE" 2>&1
    else
        log "$script completed successfully."
    fi
done

log "================ Maco Googlesheet Batch End ================"

# 작업 완료 알림
python "$UTILS_DIR/send_slack_msg.py" --channel "$SLACK_CHANNEL" --msg "✅ 스프레드시트 자동 업데이트 프로세스 완료" >> "$LOG_FILE" 2>&1
