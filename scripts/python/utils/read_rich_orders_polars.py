import os
import polars as pl
# import pandas as pd
from datetime import datetime, timedelta

def load_rich_orders_polars(start_date_str, end_date_str, columns=None, base_path="/Users/galaxy/Google Drive/공유 드라이브/gbike.rich_orders", filter_expr=None):
    """
    지정된 기간 동안 구글 드라이브에 저장된 rich_orders Parquet 파일들을 Polars를 이용해 
    빠르게 읽어와서 하나의 Polars DataFrame으로 반환합니다.
    
    Args:
        start_date_str (str): 시작 날짜 (YYYY-MM-DD)
        end_date_str (str): 종료 날짜 (YYYY-MM-DD)
        columns (list, optional): 불러올 컬럼 리스트
        base_path (str): Parquet 파일이 저장된 기본 경로
        filter_expr (pl.Expr, optional): 로드 시 적용할 필터 조건 (메모리 절약)
        
    Returns:
        pl.DataFrame: 병합된 Polars 데이터프레임
    """
    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    # 순수 파이썬 내장 모듈을 이용해 날짜 리스트 생성
    file_paths = []
    
    current_dt = start_dt
    while current_dt <= end_dt:
        target_date_str = current_dt.strftime('%Y-%m-%d')
        daily_folder_name = f"dt={target_date_str}"
        file_path = os.path.join(base_path, daily_folder_name, f"rich_orders_{target_date_str}.parquet")
        
        if os.path.exists(file_path):
            file_paths.append(file_path)
        else:
            print(f"[{target_date_str}] 파일이 존재하지 않습니다: {file_path}")
            
        current_dt += timedelta(days=1)
            
    if not file_paths:
        print("해당 기간 내 읽어올 수 있는 데이터가 없습니다.")
        return pl.DataFrame()
        
    try:
        # Polars의 Lazy API(scan_parquet)를 활용하여 최적화된 파일 읽기 수행
        lf = pl.scan_parquet(file_paths, missing_columns='insert', extra_columns='ignore')
        if columns:
            lf = lf.select(columns)
            
        if filter_expr is not None:
            lf = lf.filter(filter_expr)
            
        # 연산을 실행하고 메모리에 올림 (collect)
        df = lf.collect()
        return df
    except Exception as e:
        print(f"파일 읽기 및 병합 중 오류 발생: {e}")
        return pl.DataFrame()

def apply_channel_fee_logic(df: pl.DataFrame) -> pl.DataFrame:
    """
    채널별 수수료 정책을 반영하여 실제 수령액 기준의 매출(calculated_pay_amount, calculated_out_of_area_charge) 컬럼을 생성합니다.
    tmap: 9.9%, kakaot: 10%, tmoney: 8.5%, 기타: 수수료 없음
    """
    if "from_api" not in df.columns or "order_amount" not in df.columns or "pay_amount" not in df.columns or "out_of_area_charge" not in df.columns:
        return df

    calc_pay = (
        pl.when(pl.col("from_api") == "tmap").then((pl.col("order_amount") * 0.901).floor())
        .when(pl.col("from_api") == "kakaot").then((pl.col("order_amount") * 0.9).floor())
        .when(pl.col("from_api") == "tmoney").then((pl.col("order_amount") * 0.915).floor())
        .otherwise(pl.col("pay_amount"))
    )
    
    calc_out = (
        pl.when(pl.col("from_api") == "tmap").then((pl.col("out_of_area_charge") * 0.901).floor())
        .when(pl.col("from_api") == "kakaot").then((pl.col("out_of_area_charge") * 0.9).floor())
        .when(pl.col("from_api") == "tmoney").then((pl.col("out_of_area_charge") * 0.915).floor())
        .otherwise(pl.col("out_of_area_charge"))
    )

    return df.with_columns(
        calc_pay.alias("calculated_pay_amount"),
        calc_out.alias("calculated_out_of_area_charge")
    )


if __name__ == '__main__':
    # 예시: 2023년 전체 로드 후 Polars를 이용한 집계 테스트
    print("=== Polars: rich_orders 로드 및 집계 테스트 ===")
    start = '2023-01-01'
    end = '2023-12-31'
    
    selected_cols = ['dt', 'pay_amount', 'duration_minutes']
    
    # 시간 측정용
    import time
    start_time = time.time()
    
    df = load_rich_orders_polars(start, end, columns=selected_cols)
    
    if not df.is_empty():
        print(f"\n데이터 로드 완료. 총 건수: {df.height:,}건")
        
        # dt 컬럼은 Parquet 로드 시 이미 Datetime 타입이므로 곧바로 포맷팅
        agg_df = (
            df.with_columns(
                pl.col('dt').dt.strftime('%Y-%m').alias('year_month')
            )
            .group_by('year_month')
            .agg(
                pl.col('pay_amount').sum().alias('total_pay_amount'),
                pl.col('pay_amount').count().alias('order_count')
            )
            .sort('year_month')
        )
        
        elapsed_time = time.time() - start_time
        print(f"로드 및 집계 소요 시간: {elapsed_time:.2f}초\n")
        
        print("=== 2023년 월별 집계 결과 (Polars) ===")
        # Polars의 출력 포맷을 판다스처럼 보기 좋게 설정
        pl.Config.set_tbl_rows(15)
        print(agg_df)
    else:
        print("집계할 데이터가 없습니다.")
