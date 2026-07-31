import os
import sys
import re
import polars as pl
import pandas as pd
import time
from datetime import datetime

# utils 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'utils')))
from read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic

def get_min_max_dates(base_path):
    """base_path 내의 dt=YYYY-MM-DD 폴더들을 탐색하여 최소/최대 날짜를 반환합니다."""
    dates = []
    pattern = re.compile(r"^dt=(\d{4}-\d{2}-\d{2})$")
    
    if not os.path.exists(base_path):
        return None, None
        
    for d in os.listdir(base_path):
        match = pattern.match(d)
        if match:
            dates.append(match.group(1))
            
    if not dates:
        return None, None
        
    dates.sort()
    return dates[0], dates[-1]

def main():
    base_path = "/Users/galaxy.jang/Google Drive/공유 드라이브/gbike.rich_orders"
    print("구글 드라이브 폴더 스캔 중...")
    
    start_date, end_date = get_min_max_dates(base_path)
    
    if not start_date or not end_date:
        print("데이터 폴더(dt=YYYY-MM-DD)를 찾을 수 없습니다.")
        return
        
    print(f"발견된 데이터 기간: {start_date} ~ {end_date}")
    
    selected_cols = ['dt', 'pay_amount', 'out_of_area_charge', 'order_amount', 'from_api']
    
    print("Polars: 전체 데이터 로드 및 수수료 정책 반영 중...")
    start_time = time.time()
    
    # 1. 데이터 로드
    df = load_rich_orders_polars(start_date, end_date, columns=selected_cols, base_path=base_path)
    
    if df.is_empty():
        print("해당 기간의 데이터를 로드하지 못했습니다.")
        return
        
    print(f"데이터 로드 완료. (총 {df.height:,} 건) - 소요시간: {time.time() - start_time:.2f}초")
    
    # 2. 채널 수수료 적용 및 파생 변수 생성
    df = apply_channel_fee_logic(df)
    
    df = df.with_columns(
        (pl.col("calculated_pay_amount") + pl.col("calculated_out_of_area_charge")).alias("total_revenue"),
        pl.col("dt").dt.strftime('%Y-%m').alias("year_month"),
        pl.col("dt").dt.strftime('%Y').alias("year")
    )
    
    # 3. 월별 통계 집계
    print("월별 통계 집계 중...")
    monthly_df = (
        df.group_by('year_month')
        .agg(
            pl.col('dt').count().alias('trip_count'),
            pl.col('total_revenue').sum().alias('total_revenue')
        )
        .sort('year_month')
    )
    
    # 4. 연별 통계 및 증감률(Trend) 집계
    print("연별 통계 및 트렌드 집계 중...")
    yearly_df = (
        df.group_by('year')
        .agg(
            pl.col('dt').count().alias('trip_count'),
            pl.col('total_revenue').sum().alias('total_revenue')
        )
        .sort('year')
    )
    
    # YoY 계산 (전년 대비 증감률)
    yearly_df = yearly_df.with_columns(
        ((pl.col('trip_count') / pl.col('trip_count').shift(1) - 1) * 100).round(1).alias('trip_yoy_pct'),
        ((pl.col('total_revenue') / pl.col('total_revenue').shift(1) - 1) * 100).round(1).alias('revenue_yoy_pct')
    )
    
    # 5. 채널별(from_api) 비중 변화 집계
    print("연도별 채널 비중 트렌드 집계 중...")
    channel_df = (
        df.group_by(['year', 'from_api'])
        .agg(pl.col('dt').count().alias('channel_trip_count'))
        .sort(['year', 'from_api'])
    )
    
    # 연도별 전체 트립수 계산 후 조인하여 비중(%) 산출
    year_totals = yearly_df.select(['year', 'trip_count']).rename({"trip_count": "yearly_total_trips"})
    channel_df = channel_df.join(year_totals, on='year', how='left')
    channel_df = channel_df.with_columns(
        ((pl.col('channel_trip_count') / pl.col('yearly_total_trips')) * 100).round(1).alias('channel_share_pct')
    )
    
    # 6. 엑셀 저장 (Pandas ExcelWriter 활용)
    save_dir = "/Users/galaxy.jang/anti_codebase/results/all_time_summary"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "all_time_stats_and_trends.xlsx")
    
    print("결과물 엑셀 저장 중...")
    with pd.ExcelWriter(save_path, engine='xlsxwriter') as writer:
        monthly_df.to_pandas().to_excel(writer, sheet_name='Monthly_Stats', index=False)
        yearly_df.to_pandas().to_excel(writer, sheet_name='Yearly_Stats_Trend', index=False)
        channel_df.to_pandas().to_excel(writer, sheet_name='Channel_Share_Trend', index=False)
        
    print(f"작업 완료! 파일이 저장되었습니다: {save_path}")

if __name__ == '__main__':
    main()
