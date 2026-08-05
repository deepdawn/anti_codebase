import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.test_mysql_conn import get_engine

def extract_rich_orders_for_date(target_date_str, engine):
    """지정된 날짜(YYYY-MM-DD)의 데이터를 추출"""
    
    # query_date: target_date_str (e.g., '2026-05-25')
    query = f"""
    SELECT
        CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul') as dt,
        CONVERT_TZ(FROM_UNIXTIME(o.start_time), 'UTC', 'Asia/Seoul') as st_dt,
        CONVERT_TZ(FROM_UNIXTIME(o.end_time), 'UTC', 'Asia/Seoul') as end_dt,
        (o.end_time - o.start_time) / 60 AS duration_minutes,
        distance,
        order_id,
        user_id,
        bicycle_sn,
        bicycle_type,
        country_code,
        CASE
            when bicycle_type in (15,17,18,22,24) then 'Bicycle'
            when bicycle_type in (9,10,11,12,13,16,19,23) then 'Scooter'
            else 'none'
        END as vehicle_type,
        region_id as low_region_id,
        region_name as low_region_name,
        order_amount,
        pay_amount,
        out_of_area_charge,
        coupon_id,
        is_late_night_surcharge,
        is_limit_free,
        from_api,
        ST_X(ST_GeomFromText(ST_AsText(start_point), 0)) as `start_lng`,
        ST_Y(ST_GeomFromText(ST_AsText(start_point), 0)) as `start_lat`,
        ST_X(ST_GeomFromText(ST_AsText(end_point), 0)) as `end_lng`,
        ST_Y(ST_GeomFromText(ST_AsText(end_point), 0)) as `end_lat`,
        ST_AsText(start_point) as start_point,
        ST_AsText(end_point) as end_point,
        ST_AsText(start_user_point) as start_user_point,
        ST_AsText(end_user_point) as end_user_point,
        order_info,
        case
            when order_info -> '$.riding_fee_type' = 'time' then '분당요금제'
            when order_info -> '$.riding_fee_type' = 'odometer' then '거리요금제'
        else '알수없음' end AS riding_fee_type
    FROM gbike.rich_orders o
    WHERE o.order_state = 2
      AND o.add_time >= UNIX_TIMESTAMP('{target_date_str} 00:00:00') - 32400
      AND o.add_time <= UNIX_TIMESTAMP('{target_date_str} 23:59:59') - 32400
      AND o.country_code = 'kr'
    """
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        print(f"Error extracting data for {target_date_str}: {e}")
        return None

def main():
    base_save_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_orders"
    
    args = [arg for arg in sys.argv if arg != '--overwrite']
    
    if len(args) >= 3:
        start_date_str = args[1]
        end_date = args[2]
    else:
        # 인자가 없으면 이번 달 1일부터 전일자까지 추출
        target_dt = datetime.now() - timedelta(days=1)
        end_date = target_dt.strftime('%Y-%m-%d')
        
        # 이번 달 1일 계산
        curr_month_dt = datetime.now().replace(day=1)
        start_date_str = curr_month_dt.strftime('%Y-%m-%d')
        
    # date_range 생성
    date_list = pd.date_range(start=start_date_str, end=end_date, freq='D')
    
    engine = get_engine()
    
    print(f"총 {len(date_list)}일 치 데이터 추출을 시작합니다.")
    print(f"저장 기본 경로: {base_save_path}")
    
    has_error = False
    for dt in date_list:
        target_date_str = dt.strftime('%Y-%m-%d')
        
        # 빅쿼리 파티셔닝을 고려한 폴더명: dt=YYYY-MM-DD
        daily_folder_name = f"dt={target_date_str}"
        daily_folder_path = os.path.join(base_save_path, daily_folder_name)
        
        # 폴더 생성
        os.makedirs(daily_folder_path, exist_ok=True)
        
        file_path = os.path.join(daily_folder_path, f"rich_orders_{target_date_str}.parquet")
        
        # 파일이 이미 존재하면 건너뜀 (이어서 받기 기능)
        if os.path.exists(file_path) and '--overwrite' not in sys.argv:
            print(f"[{target_date_str}] 파일이 이미 존재하여 스킵합니다: {file_path}")
            continue
            
        print(f"[{target_date_str}] 데이터 추출 중...")
        start_time = time.time()
        
        df = extract_rich_orders_for_date(target_date_str, engine)
        
        if df is not None and not df.empty:
            try:
                # parquet으로 저장. index 제외.
                df.to_parquet(file_path, index=False)
                elapsed_time = time.time() - start_time
                print(f"[{target_date_str}] 성공적으로 저장되었습니다. (건수: {len(df):,}, 소요시간: {elapsed_time:.2f}초)")
            except Exception as e:
                print(f"[{target_date_str}] 파일 저장 중 오류 발생: {e}")
                has_error = True
        elif df is not None and df.empty:
            print(f"[{target_date_str}] 해당하는 데이터가 없습니다.")
        else:
            print(f"[{target_date_str}] 추출 실패. 다음 날짜로 넘어갑니다.")
            has_error = True
            
    if has_error:
        print("경고: 하나 이상의 날짜 추출 또는 저장에 실패했습니다.")
        sys.exit(1)

if __name__ == '__main__':
    main()
