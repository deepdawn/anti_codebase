import os
import sys
import time
import polars as pl
from datetime import datetime

# sys.path 설정하여 utils 모듈을 import 할 수 있도록 합니다.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))

try:
    from read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic
except ImportError:
    try:
        from utils.read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic
    except ImportError as e:
        print(f"모듈 임포트 에러: {e}")
        sys.exit(1)

def main():
    # 26년도 전체
    start_date = '2026-01-01'
    end_date = '2026-05-31'
    
    cols = [
        'dt', 'low_region_id', 'from_api', 'vehicle_type', 'bicycle_sn', 
        'order_amount', 'pay_amount', 'out_of_area_charge'
    ]
    
    print("1. rich_orders 데이터를 로드합니다...")
    start_time = time.time()
    
    df_orders = load_rich_orders_polars(start_date, end_date, columns=cols)
    
    if df_orders.is_empty():
        print("데이터를 불러오지 못했습니다.")
        return
        
    print(f"rich_orders 로드 완료: {df_orders.height:,} 건, 소요시간: {time.time() - start_time:.2f}초")
    
    # 수수료 정책 적용
    df_orders = apply_channel_fee_logic(df_orders)
    
    # 매출 계산 (calculated_pay_amount + calculated_out_of_area_charge)
    df_orders = df_orders.with_columns(
        (pl.col('calculated_pay_amount') + pl.col('calculated_out_of_area_charge')).alias('revenue')
    )
    
    print("2. rich_region_hierarchy 데이터를 로드합니다...")
    region_path = "/Users/galaxy.jang/Google Drive/공유 드라이브/gbike.rich_region/rich_region_hierarchy.parquet"
    if not os.path.exists(region_path):
        print(f"경로를 찾을 수 없습니다: {region_path}")
        return
        
    df_region = pl.read_parquet(region_path).filter(pl.col('country_code') == 'kr')
    
    print("3. 데이터 병합 및 전처리...")
    # 소지역(low_region_id) 기준으로 조인
    df_joined = df_orders.join(df_region, left_on='low_region_id', right_on='region_id', how='inner')
    
    # dt가 datetime 타입일 경우 date 타입으로 변환 (일별 집계를 위함)
    df_joined = df_joined.with_columns([
        pl.col("dt").cast(pl.Date)
    ])
    
    print("4. 데이터 집계...")
    # 차원: 일별(dt), 대지역, 중지역, 소지역, from_api, vehicle_type
    # 메트릭: 운행 수(count), 운행 기기 수(n_unique), 매출(sum)
    agg_df = (
        df_joined.group_by(['dt', '대지역', '중지역', '소지역', 'from_api', 'vehicle_type'])
        .agg(
            pl.len().alias('운행 수'),
            pl.col('bicycle_sn').n_unique().alias('운행 기기 수 (유니크)'),
            pl.col('revenue').sum().alias('매출')
        )
        .sort(['dt', '대지역', '중지역', '소지역'])
    )
    
    print("5. 결과 저장...")
    result_dir = "/Users/galaxy.jang/anti_codebase/results/yealy_trip_count_v1"
    os.makedirs(result_dir, exist_ok=True)
    
    output_path = os.path.join(result_dir, "yealy_trip_count_v1.xlsx")
    
    # polars write_excel을 사용하여 저장 (매우 빠르고 메모리 효율적)
    try:
        agg_df.write_excel(output_path)
        print(f"작업 완료! 결과가 {output_path} 에 저장되었습니다.")
    except Exception as e:
        print(f"Excel 저장 중 오류 발생: {e}")
        # 오류 발생 시 csv로 대체 저장 시도
        alt_path = output_path.replace('.xlsx', '.csv')
        agg_df.write_csv(alt_path)
        print(f"대신 CSV 포맷으로 저장되었습니다: {alt_path}")

if __name__ == '__main__':
    main()
