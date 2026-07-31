import os
import sys
import polars as pl
from datetime import datetime

# 공통 유틸리티 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../utils')))
from read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic

def main():
    start_date = '2026-01-01'
    end_date = '2026-06-10'
    
    print(f"[{start_date} ~ {end_date}] 데이터를 로드하고 월별, 주별, 유저별 세분화 집계를 시작합니다...")

    columns = [
        'dt', 'user_id', 'pay_amount', 'out_of_area_charge', 'from_api', 'order_amount'
    ]
    df = load_rich_orders_polars(start_date, end_date, columns=columns)

    if df.is_empty():
        print("결과가 없습니다.")
        return

    # year_month와 year_week 추출
    # %V는 ISO 8601 기준 주차(월요일 시작)
    df = df.with_columns([
        pl.col('pay_amount').fill_null(0),
        pl.col('out_of_area_charge').fill_null(0),
        pl.col('order_amount').fill_null(0),
        pl.col('from_api').fill_null('none'),
        pl.col('dt').dt.strftime('%Y-%m').alias('year_month'),
        pl.col('dt').dt.strftime('%Y-W%V').alias('year_week')
    ])

    # 수수료 로직 반영 (실 매출 계산)
    df = apply_channel_fee_logic(df)
    
    # 총 매출 컬럼 생성
    df = df.with_columns(
        (pl.col('calculated_pay_amount') + pl.col('calculated_out_of_area_charge')).alias('revenue')
    )

    print("유저별, 월별, 주별 집계를 시작합니다...")

    # 유저별 & 월별 & 주별 집계
    user_weekly_agg = df.group_by(['user_id', 'year_month', 'year_week']).agg([
        pl.len().alias('actual_weekly_trips'),
        pl.col('revenue').sum().alias('actual_weekly_revenue')
    ])
    
    # 주별 1회 평균 단가 및 시뮬레이션 계산
    simulation_df = user_weekly_agg.with_columns([
        # 1회 운행당 평균 매출 (해당 주 기준)
        pl.when(pl.col('actual_weekly_trips') > 0)
          .then(pl.col('actual_weekly_revenue') / pl.col('actual_weekly_trips'))
          .otherwise(0).alias('revenue_per_trip')
    ]).with_columns([
        # 시뮬레이션: 해당 주의 운행 수 +0.7회
        (pl.col('actual_weekly_trips') + 0.7).alias('simulated_weekly_trips'),
        
        # 예상되는 추가 매출 = 0.7 * 해당 주 1회 평균 매출
        (0.7 * pl.col('revenue_per_trip')).alias('simulated_weekly_additional_revenue')
    ]).with_columns([
        # 시뮬레이션: 증가 후 주 총 매출
        (pl.col('actual_weekly_revenue') + pl.col('simulated_weekly_additional_revenue')).alias('simulated_weekly_revenue')
    ])

    # 정렬: year_month 오름차순, year_week 오름차순, 매출 내림차순
    simulation_df = simulation_df.sort(['year_month', 'year_week', 'actual_weekly_revenue'], descending=[False, False, True])

    # 결과 저장
    result_dir = "/Users/galaxy.jang/anti_codebase/results/user_simulation_26h1"
    os.makedirs(result_dir, exist_ok=True)
    
    output_path = os.path.join(result_dir, "user_revenue_simulation_weekly_result.csv")
    
    try:
        # Polars의 고속 CSV 저장 활용
        simulation_df.write_csv(output_path)
        print(f"세분화 분석 결과가 저장되었습니다 (총 {simulation_df.height:,}건): {output_path}")
    except Exception as e:
        print(f"파일 저장 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
