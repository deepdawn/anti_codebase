#!/bin/bash
# run_weekly.sh
cd /Users/galaxy.jang/anti_codebase

LOG_FILE="/Users/galaxy.jang/anti_codebase/scripts/python/extract/log/run_weekly.log"
DATE=$(date "+%Y-%m-%d %H:%M:%S")

echo "$DATE [INFO] ================ Weekly Extract Batch Start ================" >> $LOG_FILE

echo "$DATE [INFO] Running extract_rich_daily_statistics.py..." >> $LOG_FILE
/Users/galaxy.jang/anti_codebase/.venv/bin/python scripts/python/extract/extract_rich_daily_statistics.py >> $LOG_FILE 2>&1

echo "$DATE [INFO] Running extract_deploy_spot_info.py..." >> $LOG_FILE
/Users/galaxy.jang/anti_codebase/.venv/bin/python scripts/python/extract/extract_deploy_spot_info.py >> $LOG_FILE 2>&1

echo "$DATE [INFO] Running extract_vehicle_statistics.py..." >> $LOG_FILE
/Users/galaxy.jang/anti_codebase/.venv/bin/python scripts/python/extract/extract_vehicle_statistics.py >> $LOG_FILE 2>&1

echo "$DATE [INFO] Running extract_rich_task_statistics.py..." >> $LOG_FILE
/Users/galaxy.jang/anti_codebase/.venv/bin/python scripts/python/extract/extract_rich_task_statistics.py >> $LOG_FILE 2>&1

DATE=$(date "+%Y-%m-%d %H:%M:%S")
echo "$DATE [INFO] ================ Weekly Extract Batch End ================" >> $LOG_FILE
