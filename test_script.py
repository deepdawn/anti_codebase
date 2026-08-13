import os
from datetime import datetime, timedelta

base_output_dir = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_active_user_segment"
end_date = datetime.now() - timedelta(days=1)
start_date = datetime.now() - timedelta(days=8)

curr_date = start_date
missing_dates = []
while curr_date <= end_date:
    dt_str = curr_date.strftime("%Y-%m-%d")
    file_path = os.path.join(base_output_dir, f"dt={dt_str}", f"rich_active_user_segment_{dt_str}.parquet")
    print(f"Checking {file_path} -> {os.path.exists(file_path)}")
    if not os.path.exists(file_path):
        missing_dates.append(dt_str)
        
    curr_date += timedelta(days=1)

print("missing_dates:", missing_dates)
