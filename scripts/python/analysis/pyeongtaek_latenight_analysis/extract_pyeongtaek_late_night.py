import pandas as pd
import os
import sys
import calendar
from datetime import datetime

# 공용 유틸리티에서 DB 연결 함수 가져오기
sys.path.append("/Users/galaxy/anti_codebase/scripts/python/utils")
from test_mysql_conn import get_engine

def main():
    subfolder_name = "pyeongtaek_latenight_analysis" 
    
    script_dir = f"/Users/galaxy/anti_codebase/scripts/python/{subfolder_name}"
    result_dir = f"/Users/galaxy/anti_codebase/results/{subfolder_name}"
    os.makedirs(script_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)

    # 1. 추출 기간 설정 (2026-01-01 ~ 2026-05-19)
    start_date = datetime(2026, 1, 1)
    end_limit = datetime(2026, 5, 19, 23, 59, 59)
    
    # 2. 파일 이름 동적 생성
    prefix = f"{start_date.strftime('%Y%m%d')}_{end_limit.strftime('%Y%m%d')}"
    result_file = os.path.join(result_dir, f"{prefix}_pyeongtaek_late_night.xlsx")

    # 1달 단위로 기간 생성
    date_ranges = []
    current_start = start_date
    while current_start <= end_limit:
        last_day = calendar.monthrange(current_start.year, current_start.month)[1]
        current_end = datetime(current_start.year, current_start.month, last_day, 23, 59, 59)
        if current_end > end_limit:
            current_end = end_limit
            
        date_ranges.append((current_start.strftime('%Y-%m-%d 00:00:00'), current_end.strftime('%Y-%m-%d 23:59:59')))
        
        # 다음 달로 이동
        if current_start.month == 12:
            current_start = datetime(current_start.year + 1, 1, 1)
        else:
            current_start = datetime(current_start.year, current_start.month + 1, 1)

    # test_mysql_conn.py 의 get_engine 활용
    engine = get_engine()
    all_dfs = []

    for start, end in date_ranges:
        print(f"Extracting: {start} ~ {end}...")
        
        query = f"""
        SELECT
            DATE_FORMAT(CONVERT_TZ(FROM_UNIXTIME(O.add_time), 'UTC', 'Asia/Seoul'), '%%Y-%%m') AS ride_month,
            CASE WHEN O.is_late_night_surcharge = 1 THEN '심야' ELSE '주간' END AS hour_type,
            R.region_name AS small_region,
            CASE
                WHEN B.type IN (15,17,18,22,24) THEN 'Bicycle'
                WHEN B.type IN (9,10,11,12,13,16,19,23) THEN 'Scooter'
                ELSE 'none'
            END AS device_type,
            
            COUNT(O.order_id) AS trip_cnt,
            COUNT(DISTINCT O.bicycle_id) AS device_cnt,
            SUM((O.pay_amount + O.out_of_area_charge) / 1.1) AS net_revenue
            
        FROM gbike.rich_orders O
        JOIN gbike.rich_region R ON O.region_id = R.region_id
        JOIN gbike.rich_region E ON R.parent_id = E.region_id
        JOIN gbike.rich_bicycle B ON O.bicycle_id = B.bicycle_id
        WHERE O.add_time BETWEEN UNIX_TIMESTAMP(CONVERT_TZ('{start}', 'Asia/Seoul', 'UTC')) 
                             AND UNIX_TIMESTAMP(CONVERT_TZ('{end}', 'Asia/Seoul', 'UTC'))
          AND E.region_name = '평택캠프'
          AND O.order_state = 2
        GROUP BY 
            ride_month,
            hour_type,
            small_region,
            device_type
        """
        
        try:
            with engine.connect() as connection:
                df_chunk = pd.read_sql(query, connection)
                if not df_chunk.empty:
                    all_dfs.append(df_chunk)
                print(f"Chunk complete: {len(df_chunk)} rows")
        except Exception as e:
            print(f"Error during chunk extraction ({start}): {e}")
            return

    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df = final_df.sort_values(by=['ride_month', 'small_region', 'device_type', 'hour_type'])
        final_df.to_excel(result_file, index=False, engine='openpyxl')
        print(f"Final file saved: {result_file} (Total: {len(final_df)} rows)")
    else:
        print("No data extracted.")

if __name__ == "__main__":
    main()
