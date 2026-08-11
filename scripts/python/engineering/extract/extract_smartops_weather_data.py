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

def extract_weather_data(target_date_str, engine):
    # 요청하신 쿼리에서 date 조건을 특정 일자로 고정하여 일별 추출이 가능하도록 수정했습니다.
    query = f"""
    SELECT
        w.date,
        rrr.region_name AS high_region_name,
        rr.region_name AS middle_region_name,
        sum(w.temperature) / count(distinct w.hour) as `일 평균 기온`,
        case when SUM(w.precipitation) < 0 then 0 else SUM(w.precipitation) end AS `일 총 강수량`,
        case when SUM(w.precipitation) < 0 then 0 else SUM(w.precipitation) / COUNT(DISTINCT w.hour) end AS `시간당 평균 강수량`
    FROM gbike_smartops.weather_data w
    JOIN gbike.rich_region r ON r.region_id = w.region_id
    JOIN gbike.rich_region rr ON rr.region_id = r.parent_id
    JOIN gbike.rich_region rrr ON rrr.region_id = rr.parent_id
    WHERE w.date = '{target_date_str}'
    GROUP BY 
        w.date, 
        rrr.region_name, 
        rr.region_name
    """
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(text(query), connection)
        return df
    except Exception as e:
        print(f"Error extracting for {target_date_str}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='smartops_weather_data 일별 추출')
    parser.add_argument('start_date', nargs='?', type=str, help='시작 일자 (YYYY-MM-DD)')
    parser.add_argument('end_date', nargs='?', type=str, help='종료 일자 (YYYY-MM-DD)')
    parser.add_argument('--overwrite', action='store_true', help='이미 존재하는 파일 덮어쓰기')
    
    args, unknown = parser.parse_known_args()
    
    overwrite = args.overwrite
    if '--overwrite' in sys.argv or '--overwrite' in unknown:
        overwrite = True

    if args.start_date and args.end_date:
        start_date_str = args.start_date
        end_date_str = args.end_date
    else:
        # 이번 달 1일부터 어제까지 (기본 동작)
        today = datetime.now()
        start_date = today.replace(day=1)
        end_date = today - timedelta(days=1)
        if start_date > end_date:
            start_date = end_date
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

    target_start = datetime.strptime(start_date_str, "%Y-%m-%d")
    target_end = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    date_list = []
    current = target_start
    while current <= target_end:
        date_list.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
        
    print(f"총 {len(date_list)}일 치 날씨 데이터 추출을 시작합니다.")
    
    engine = get_engine()
    
    # 사용자님께서 요청하신 경로를 사용합니다.
    base_save_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike_smartops.weather_data"
    os.makedirs(base_save_path, exist_ok=True)
    print(f"저장 기본 경로: {base_save_path}")
    
    has_error = False
    
    for target_date_str in date_list:
        daily_folder_name = f"dt={target_date_str}"
        daily_folder_path = os.path.join(base_save_path, daily_folder_name)
        os.makedirs(daily_folder_path, exist_ok=True)
        
        file_path = os.path.join(daily_folder_path, f"smartops_weather_data_{target_date_str}.parquet")
        
        if os.path.exists(file_path) and not overwrite:
            print(f"[{target_date_str}] 파일이 이미 존재하여 스킵합니다: {file_path}")
            continue
            
        print(f"[{target_date_str}] 데이터 추출 중...")
        start_time = time.time()
        
        df = extract_weather_data(target_date_str, engine)
        
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
        print("모든 날씨 데이터 추출 작업이 성공적으로 완료되었습니다.")

if __name__ == '__main__':
    main()
