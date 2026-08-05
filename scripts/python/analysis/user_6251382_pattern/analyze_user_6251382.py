import os
import sys
import polars as pl
from datetime import datetime

# sys.path 설정하여 utils 모듈을 import 할 수 있도록 함
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from scripts.python.utils.read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic

def main():
    user_id = 6251382
    start_date = '2026-01-01'
    end_date = '2026-07-07' # 어제 날짜
    
    output_dir = '/Users/galaxy/anti_codebase/results/user_6251382_pattern'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f'user_{user_id}_pattern_analysis.xlsx')
    
    print(f"[{datetime.now()}] Loading data for user {user_id}...")
    
    cols = [
        'dt', 'st_dt', 'user_id', 'distance', 'vehicle_type', 
        'from_api', 'order_amount', 'pay_amount', 'out_of_area_charge'
    ]
    
    # 필터 조건을 push down 하여 메모리 효율적으로 로드
    df = load_rich_orders_polars(
        start_date_str=start_date,
        end_date_str=end_date,
        columns=cols,
        filter_expr=(pl.col('user_id') == user_id)
    )
    
    if df.is_empty():
        print("해당 기간 내 사용자의 운행 데이터가 없습니다.")
        return
        
    print(f"[{datetime.now()}] Data loaded. Total trips: {df.height}")
    
    # 수수료 정책을 반영하여 실제 매출(calculated_pay_amount 등) 계산
    df = apply_channel_fee_logic(df)
    
    # 매출 컬럼 생성: calculated_pay_amount + calculated_out_of_area_charge
    df = df.with_columns(
        (pl.col('calculated_pay_amount').fill_null(0) + pl.col('calculated_out_of_area_charge').fill_null(0)).alias('revenue')
    )
    
    # st_dt가 문자열일 경우 Datetime으로 변환
    if df.schema['st_dt'] == pl.Utf8:
        df = df.with_columns(pl.col('st_dt').str.strptime(pl.Datetime, format="%Y-%m-%d %H:%M:%S", strict=False).alias('st_dt_dt'))
    else:
        df = df.with_columns(pl.col('st_dt').alias('st_dt_dt'))
        
    # 주(week)와 시간(hour) 추출
    # truncate("1w")는 해당 주의 시작일(월요일)을 반환함
    df = df.with_columns(
        pl.col('st_dt_dt').dt.truncate("1w").alias('week'),
        pl.col('st_dt_dt').dt.hour().alias('hour')
    )
    
    # 1. 주별 총 운행 수 및 매출액 집계
    weekly_stats = df.group_by('week').agg([
        pl.len().alias('trip_count'),
        pl.col('revenue').sum().alias('total_revenue')
    ]).sort('week')
    
    print("\n--- Weekly Stats ---")
    print(weekly_stats)
    
    # 2. 주로 탑승하는 시간대 파악
    hour_stats = df.group_by('hour').agg(pl.len().alias('trip_count')).sort('trip_count', descending=True)
    print("\n--- Most Frequent Ride Hour ---")
    print(hour_stats.head(5))
    
    # 3. 평균 및 최대 운행 거리 파악
    distance_stats = df.select([
        pl.col('distance').mean().alias('avg_distance'),
        pl.col('distance').max().alias('max_distance')
    ])
    print("\n--- Distance Stats ---")
    print(distance_stats)
    
    # 4. 선호 기기 타입 확인
    device_stats = df.group_by('vehicle_type').agg(pl.len().alias('trip_count')).sort('trip_count', descending=True)
    print("\n--- Preferred Device Type ---")
    print(device_stats.head(5))
    
    # 결과를 Excel 파일로 저장
    print(f"\n[{datetime.now()}] Saving results to {output_file}...")
    import pandas as pd
    
    # Convert week to string for Excel compatibility if necessary
    weekly_stats = weekly_stats.with_columns(pl.col('week').dt.strftime('%Y-%m-%d'))
    
    with pd.ExcelWriter(output_file) as writer:
        weekly_stats.to_pandas().to_excel(writer, sheet_name='Weekly_Stats', index=False)
        hour_stats.to_pandas().to_excel(writer, sheet_name='Hourly_Stats', index=False)
        distance_stats.to_pandas().to_excel(writer, sheet_name='Distance_Stats', index=False)
        device_stats.to_pandas().to_excel(writer, sheet_name='Device_Stats', index=False)
        
    print("Done!")

if __name__ == "__main__":
    main()
