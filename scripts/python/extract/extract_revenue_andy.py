import os
import sys
import polars as pl

# Utils 경로 추가
utils_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils'))
if utils_path not in sys.path:
    sys.path.append(utils_path)

from read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic

def main():
    # 1. & 2. 25년 1월부터 26년 6월 22일까지 rich_orders 로드
    start_date = '2025-01-01'
    end_date = '2026-06-22'
    cols_orders = [
        'dt', 'low_region_id', 'from_api', 'vehicle_type', 
        'bicycle_sn', 'order_id', 'order_amount', 'pay_amount', 'out_of_area_charge'
    ]
    
    print(f"[{start_date} ~ {end_date}] rich_orders 로딩 중...")
    df_orders = load_rich_orders_polars(start_date, end_date, columns=cols_orders)
    if df_orders.is_empty():
        print("rich_orders 데이터가 존재하지 않습니다.")
        return
        
    print("채널별 수수료 정책 적용 중...")
    df_orders = apply_channel_fee_logic(df_orders)
    
    # 매출 = 수수료 차감 후 pay_amount + 수수료 차감 후 out_of_area_charge
    df_orders = df_orders.with_columns(
        (pl.col('calculated_pay_amount').fill_null(0) + pl.col('calculated_out_of_area_charge').fill_null(0)).alias('revenue')
    )
    
    # 3. rich_region 로드
    print("rich_region 로딩 중...")
    region_path = f'{os.path.expanduser("~")}/Google Drive/공유 드라이브/gbike.rich_region/rich_region_hierarchy.parquet'
    df_region = pl.read_parquet(region_path)
    
    # 4. low_region_id 기준으로 조인 (대, 중, 소지역 정보 획득)
    print("orders와 region 조인 중...")
    df_joined = df_orders.join(df_region, left_on='low_region_id', right_on='region_id', how='inner')
    
    # 5. 집계 기준 일자(dt) 생성 로직
    # 25년 6월, 26년 6월은 일별, 나머지는 월별
    print("날짜 집계 기준(일별/월별) 생성 중...")
    df_joined = df_joined.with_columns(
        pl.col('dt').dt.strftime('%Y-%m-%d').alias('dt_str'),
        pl.col('dt').dt.strftime('%Y-%m').alias('month_str')
    )
    
    df_joined = df_joined.with_columns(
        pl.when(pl.col('month_str').is_in(['2025-06', '2026-06']))
        .then(pl.col('dt_str'))
        .otherwise(pl.col('month_str'))
        .alias('dt_agg')
    )
    
    # 6. 지정된 차원과 메트릭으로 집계
    print("데이터 집계 중...")
    agg_df = (
        df_joined.group_by(['dt_agg', '대지역', '중지역', '소지역', 'from_api', 'vehicle_type'])
        .agg(
            pl.col('order_id').count().alias('운행 수'),
            pl.col('bicycle_sn').n_unique().alias('운행 기기수(유니크)'),
            pl.col('revenue').sum().alias('매출')
        )
        # 결과물의 가독성을 위해 정렬 (선택 사항)
        .sort(['dt_agg', '대지역', '중지역', '소지역'])
    )
    
    # 7. 결과 저장
    # 폴더가 없으면 생성, 결과는 .xlsx로 저장
    out_dir = f'{os.path.expanduser("~")}/anti_codebase/results/extract_revenue_andy'
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'extract_revenue_andy.xlsx')
    
    print(f"결과를 파일로 저장 중: {out_path}...")
    agg_df.write_excel(out_path)
    print("추출이 완료되었습니다.")

if __name__ == '__main__':
    main()
