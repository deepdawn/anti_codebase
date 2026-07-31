#!/bin/bash
start_date="2025-01-01"
end_date="2026-06-24"

current_date="$start_date"
while [ "$current_date" != "$(date -I -d "$end_date + 1 day")" ]; do
  out_file="/Users/galaxy/Google Drive/공유 드라이브/gbike.rich_user_segment/dt=${current_date}/rich_user_segment_${current_date}.parquet"
  if [ ! -f "$out_file" ]; then
    echo "Processing $current_date..."
    python3 scripts/python/extract/extract_rich_user_segment.py --target-date "$current_date"
  else
    echo "Skipping $current_date, file exists."
  fi
  current_date=$(date -I -d "$current_date + 1 day")
done
