import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta
import time
from sqlalchemy import text

# utils 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils.test_mysql_conn import get_engine

def extract_vehicle_statistics(target_date_str, engine):
    query = f"""
    SELECT
        date,
        high_region_name,
        middle_region_name,
        region_id,
        CASE
            WHEN type IN (15,17,18,22,24) THEN '자전거'
            WHEN type IN (9,10,11,12,13,16,19,23) THEN '킥보드'
            ELSE 'none'
        END AS "기기구분",
        SUM(deactivate_24h_count)/count(distinct hour) AS deactivate_24h_count,
        SUM(deactivate_48h_count)/count(distinct hour) AS deactivate_48h_count,
        SUM(deactivate_72h_count)/count(distinct hour) AS deactivate_72h_count,
        SUM(total_vehicle_count)/count(distinct hour) AS total_vehicle_count
    FROM gbike_smartops.vehicle_statistics_data
    WHERE date = '{target_date_str}'
    and (middle_region_name LIKE '%캠프%' OR middle_region_name LIKE '%루미%')
    and region_name like '%본사직영%'
    AND region_name NOT LIKE '%미사용%'
    GROUP BY 1,2,3,4,5
    """
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(text(query), connection)
        return df
    except Exception as e:
        print(f"Error extracting for {target_date_str}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='vehicle_statistics_data 일별 추출')
    parser.add_argument('start_date', nargs='?', type=str, help='시작 일자 (YYYY-MM-DD)')
    parser.add_argument('end_date', nargs='?', type=str, help='종료 일자 (YYYY-MM-DD)')
    parser.add_argument('--overwrite', action='store_true', help='이미 존재하는 파일 덮어쓰기')
    
    args, unknown = parser.parse_known_args()
    
    overwrite = args.overwrite
    if '--overwrite' in sys.argv or '--overwrite' in unknown:
        overwrite = True

    if args.start_date and args.end_date:
        start_date_str = args.start_date
        end_date = args.end_date
    else:
        # 날짜 인자가 없을 시 이번달 1일부터 어제자까지를 기본값
        target_dt = datetime.now() - timedelta(days=1)
        end_date = target_dt.strftime('%Y-%m-%d')
        curr_month_dt = datetime.now().replace(day=1)
        start_date_str = curr_month_dt.strftime('%Y-%m-%d')
        
    base_save_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike_smartops.vehicle_statistics_data"
    date_list = pd.date_range(start=start_date_str, end=end_date, freq='D')
    
    engine = get_engine()
    
    print(f"총 {len(date_list)}일 치 데이터 추출을 시작합니다.")
    print(f"저장 기본 경로: {base_save_path}")
    
    has_error = False
    for dt in date_list:
        target_date_str = dt.strftime('%Y-%m-%d')
        
        daily_folder_name = f"dt={target_date_str}"
        daily_folder_path = os.path.join(base_save_path, daily_folder_name)
        os.makedirs(daily_folder_path, exist_ok=True)
        
        file_path = os.path.join(daily_folder_path, f"vehicle_statistics_data_{target_date_str}.parquet")
        
        if os.path.exists(file_path) and not overwrite:
            print(f"[{target_date_str}] 파일이 이미 존재하여 스킵합니다: {file_path}")
            continue
            
        print(f"[{target_date_str}] 데이터 추출 중...")
        start_time = time.time()
        
        df = extract_vehicle_statistics(target_date_str, engine)
        
        if df is None:
            has_error = True
            continue
            
        try:
            df.to_parquet(file_path, engine='pyarrow', compression='snappy', index=False)
            elapsed_time = time.time() - start_time
            print(f"[{target_date_str}] 성공적으로 저장되었습니다. (건수: {len(df):,}, 소요시간: {elapsed_time:.2f}초)")
        except Exception as e:
            print(f"[{target_date_str}] 파일 저장 중 오류 발생: {e}")
            has_error = True
            
    if has_error:
        print("일부 날짜에서 오류가 발생했습니다. 로그를 확인하세요.")
        sys.exit(1)
    else:
        print("모든 작업이 성공적으로 완료되었습니다.")

if __name__ == '__main__':
    main()
