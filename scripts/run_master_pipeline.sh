#!/bin/bash
# run_master_pipeline.sh
# 단일 마스터 스크립트로 분산된 Gbike 추출/배치 파이프라인을 순차 실행합니다.

cd $HOME/anti_codebase

LOG_FILE="$HOME/anti_codebase/scripts/python/extract/log/run_master_pipeline.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "$LOG_FILE"
}
log_err() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "$LOG_FILE"
}

log "================ Master Batch Pipeline Start ================"

# 환경 변수 명시적 설정 (launchd 대응)
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

run_python() {
    local script_path=$1
    log "Running $script_path..."
    python "$script_path" >> "$LOG_FILE" 2>&1
    local status=$?
    if [ $status -ne 0 ]; then
        log_err "$script_path failed with exit code $status"
        return $status
    fi
    log "$script_path completed successfully."
    return 0
}

run_bash() {
    local script_path=$1
    log "Running $script_path..."
    bash "$script_path" >> "$LOG_FILE" 2>&1
    local status=$?
    if [ $status -ne 0 ]; then
        log_err "$script_path failed with exit code $status"
        return $status
    fi
    log "$script_path completed successfully."
    return 0
}

send_chat() {
    local msg=$1
    python scripts/python/utils/send_google_chat_msg.py --space "AAQAf0HeYv0" --msg "$msg" >> "$LOG_FILE" 2>&1
}

send_chat "🚀 Master Batch Pipeline 시작합니다."

# ---------------------------------------------------------
# Phase 1: 기초 메타데이터 추출 (Metadata)
# ---------------------------------------------------------
PHASE="Phase 1 (Metadata)"
log "--- $PHASE ---"
if run_python "scripts/python/extract/extract_rich_region_hierarchy.py" && \
   run_python "scripts/python/extract/extract_rich_bicycle_asset_info.py"; then
    send_chat "✅ $PHASE 완료"
else
    send_chat "❌ $PHASE 실패"
    exit 1
fi

# ---------------------------------------------------------
# Phase 2: 핵심 트랜잭션 및 유저 데이터 추출 (Core Data)
# ---------------------------------------------------------
PHASE="Phase 2 (Core Data)"
log "--- $PHASE ---"
if run_python "scripts/python/extract/run_daily_batch.py"; then
    send_chat "✅ $PHASE 완료"
else
    send_chat "❌ $PHASE 실패"
    exit 1
fi

# ---------------------------------------------------------
# Phase 3: 현장 운영 및 배치 데이터 추출 (Operations & Deploy)
# ---------------------------------------------------------
PHASE="Phase 3 (Operations & Deploy)"
log "--- $PHASE ---"
if run_python "scripts/python/extract/extract_rich_deploy_zone_usages.py" && \
   run_python "scripts/python/extract/extract_rich_deploy_used_time.py" && \
   run_python "scripts/python/extract/extract_rich_deploy_by_time.py" && \
   run_python "scripts/python/extract/update_tableau_obp_csv.py" && \
   run_python "scripts/python/extract/update_tableau_used_time_csv.py" && \
   run_python "scripts/python/extract/update_tableau_by_time_csv.py"; then
    send_chat "✅ $PHASE 완료"
else
    send_chat "❌ $PHASE 실패"
    exit 1
fi

# ---------------------------------------------------------
# Phase 4: 집계 마트 및 통계 (Aggregation)
# ---------------------------------------------------------
PHASE="Phase 4 (Aggregation)"
log "--- $PHASE ---"
if run_python "scripts/python/extract/extract_rich_daily_statistics.py" && \
   run_python "scripts/python/extract/extract_deploy_spot_info.py" && \
   run_python "scripts/python/extract/extract_vehicle_statistics.py" && \
   run_python "scripts/python/extract/extract_rich_task_statistics.py" && \
   run_python "scripts/python/extract/extract_rich_battery_data.py" && \
   run_python "scripts/python/extract/extract_smartops_weather_data.py"; then
    send_chat "✅ $PHASE 완료"
else
    send_chat "❌ $PHASE 실패"
    exit 1
fi

# ---------------------------------------------------------
# Phase 5: GEMS Dashboard ETL
# ---------------------------------------------------------
PHASE="Phase 5 (Dashboard ETL)"
log "--- $PHASE ---"
if run_bash "$HOME/gems_build_dashboard/deploy/run_etl.sh"; then
    send_chat "✅ $PHASE 완료"
else
    send_chat "❌ $PHASE 실패"
    exit 1
fi

# ---------------------------------------------------------
# Phase 6: 리포트 통합 발송 (가장 나중 순서)
# ---------------------------------------------------------
PHASE="Phase 6 (Reports)"
log "--- $PHASE ---"
if run_python "scripts/python/report_daily_ststs_v1/send_weekly_report.py" && \
   run_python "scripts/python/report_daily_deploy_v1/send_daily_deploy_report.py"; then
    send_chat "✅ $PHASE 완료"
else
    send_chat "❌ $PHASE 실패"
    exit 1
fi

send_chat "🎉 Master Batch Pipeline 전체 성공 종료!"
log "================ Master Batch Pipeline End ================"
