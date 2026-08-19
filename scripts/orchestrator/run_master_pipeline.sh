#!/bin/bash
# run_master_pipeline.sh
# 단일 마스터 스크립트로 분산된 Gbike 추출/배치 파이프라인을 순차 실행합니다.

cd $HOME/anti_codebase

LOG_FILE="$HOME/anti_codebase/scripts/python/engineering/log/run_master_pipeline.log"
MARKER_DIR="$HOME/anti_codebase/scripts/python/engineering/log"
TODAY_STR=$(date '+%Y%m%d')
MARKER_FILE="$MARKER_DIR/.daily_success_$TODAY_STR"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "$LOG_FILE"
}
log_err() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "$LOG_FILE"
}

# 마커 체크 (오늘 이미 성공적으로 돌았다면 패스)
if [ -f "$MARKER_FILE" ]; then
    log "오늘 배치 작업이 이미 성공적으로 완료되었습니다. 실행을 생략합니다."
    exit 0
fi

log "================ Master Batch Pipeline Start ================"

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
    local script_args="${@:2}"
    log "Running $script_path $script_args ..."
    python "$script_path" $script_args >> "$LOG_FILE" 2>&1
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
# Phase 1: 1차 원천 데이터 추출 (Extraction)
# ---------------------------------------------------------
PHASE="Phase 1 (Extraction)"
log "--- $PHASE ---"
FAILED_EXTRACT=0

# 지역 정보와 기기 정보, 유저 마스터 정보 업데이트
run_python "scripts/python/engineering/extract/extract_rich_region_hierarchy.py" || FAILED_EXTRACT=1
run_python "scripts/python/engineering/extract/extract_rich_bicycle_asset_info.py" || FAILED_EXTRACT=1
run_python "scripts/python/engineering/extract/extract_rich_user_recent.py" || FAILED_EXTRACT=1

# 운행 기록, 누락 체크 및 스캔 (Python 내부 스크립트 위임)
run_python "scripts/python/engineering/extract/extract_rich_orders_daily.py" || FAILED_EXTRACT=1

# 통계 및 집계 자료, 기상 데이터 추출
run_python "scripts/python/engineering/extract/extract_rich_daily_statistics.py" || FAILED_EXTRACT=1
run_python "scripts/python/engineering/extract/extract_deploy_spot_info.py" || FAILED_EXTRACT=1
run_python "scripts/python/engineering/extract/extract_vehicle_statistics.py" || FAILED_EXTRACT=1
run_python "scripts/python/engineering/extract/extract_rich_task_statistics.py" || FAILED_EXTRACT=1
run_python "scripts/python/engineering/extract/extract_rich_battery_data.py" || FAILED_EXTRACT=1
run_python "scripts/python/engineering/extract/extract_rich_deploy_zone_usages.py" || FAILED_EXTRACT=1
run_python "scripts/python/engineering/extract/extract_rich_deploy_used_time.py" || FAILED_EXTRACT=1
run_python "scripts/python/engineering/extract/extract_rich_deploy_by_time.py" || FAILED_EXTRACT=1
run_python "scripts/python/engineering/extract/extract_smartops_weather_data.py" || FAILED_EXTRACT=1

if [ $FAILED_EXTRACT -eq 0 ]; then
    send_chat "✅ $PHASE 완료"
else
    send_chat "❌ $PHASE 중 일부 실패 (진행은 계속됨)"
fi

# ---------------------------------------------------------
# Phase 2: 2차 데이터 가공 (Processing)
# ---------------------------------------------------------
PHASE="Phase 2 (Processing)"
log "--- $PHASE ---"
FAILED_PROCESS=0

# 유저 세그먼트 및 활동 유저 세그먼트 데이터 가공 및 적재
run_python "scripts/python/engineering/processing/processing_rich_user_segment.py" || FAILED_PROCESS=1
run_python "scripts/python/engineering/processing/processing_rich_active_user_segment.py" || FAILED_PROCESS=1
run_python "scripts/python/engineering/processing/processing_rich_h3_grid_stats.py" || FAILED_PROCESS=1
run_python "scripts/python/utils/gen_operation_region_polygon.py" || FAILED_PROCESS=1

if [ $FAILED_PROCESS -eq 0 ]; then
    send_chat "✅ $PHASE 완료"
else
    send_chat "❌ $PHASE 중 일부 실패 (진행은 계속됨)"
fi

# ---------------------------------------------------------
# Phase 3: 데이터 마트 및 시각화 연동 (Tableau)
# ---------------------------------------------------------
PHASE="Phase 3 (Tableau & Data Mart)"
log "--- $PHASE ---"
FAILED_TABLEAU=0

run_python "scripts/python/engineering/tableau/update_tableau_obp_csv.py" || FAILED_TABLEAU=1
run_python "scripts/python/engineering/tableau/update_tableau_used_time_csv.py" || FAILED_TABLEAU=1
run_python "scripts/python/engineering/tableau/update_tableau_by_time_csv.py" || FAILED_TABLEAU=1
run_python "scripts/python/engineering/tableau/upload_tableau_to_drive.py" || FAILED_TABLEAU=1

if [ $FAILED_TABLEAU -eq 0 ]; then
    send_chat "✅ $PHASE 완료"
else
    send_chat "❌ $PHASE 중 일부 실패 (진행은 계속됨)"
fi

# ---------------------------------------------------------
# Phase 4: GEMS Dashboard ETL
# ---------------------------------------------------------
PHASE="Phase 4 (Dashboard ETL)"
log "--- $PHASE ---"
if run_bash "$HOME/gems_build_dashboard/deploy/run_etl.sh"; then
    send_chat "✅ $PHASE 완료"
else
    send_chat "❌ $PHASE 실패 (진행은 계속됨)"
fi

# ---------------------------------------------------------
# Phase 5: 리포트 통합 발송
# ---------------------------------------------------------
PHASE="Phase 5 (Reports)"
log "--- $PHASE ---"
if run_python "scripts/python/report_daily_ststs_v1/send_weekly_report.py"; then
    send_chat "✅ $PHASE 완료"
else
    send_chat "❌ $PHASE 실패 (진행은 계속됨)"
fi

# ---------------------------------------------------------
# 마커 기록 및 오래된 마커 정리
# ---------------------------------------------------------
echo "Completed at $(date '+%Y-%m-%d %H:%M:%S')" > "$MARKER_FILE"
log "금일 배치 작업이 종료되었습니다. 성공 마커 파일을 기록합니다: $MARKER_FILE"

find "$MARKER_DIR" -name ".daily_success_*" ! -name ".daily_success_$TODAY_STR" -type f -delete 2>/dev/null
log "오래된 마커 파일들을 정리했습니다."

send_chat "🎉 Master Batch Pipeline 전체 프로세스 종료."
log "================ Master Batch Pipeline End ================"
