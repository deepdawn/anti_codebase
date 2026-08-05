import os
import polars as pl
from datetime import datetime

def load_rich_user_polars(years=None, base_path=f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_user"):
    """
    지정된 연도의 rich_user Parquet 파일들을 Polars를 이용해 
    빠르게 읽어와서 하나의 Polars DataFrame으로 반환합니다.
    """
    file_paths = []
    
    if not years:
        years = ['2025', '2026'] # 기본값
        
    for target_year in years:
        year_folder_name = f"year={target_year}"
        file_path = os.path.join(base_path, year_folder_name, f"rich_user_{target_year}.parquet")
        
        if os.path.exists(file_path):
            file_paths.append(file_path)
        else:
            print(f"[{target_year}] 파일이 존재하지 않습니다: {file_path}")
            
    if not file_paths:
        print("해당 연도의 데이터를 찾을 수 없습니다.")
        return pl.DataFrame()
        
    try:
        # Polars Lazy API를 활용하여 파일 읽기 (Float/Int 자동 캐스팅 허용)
        lf = pl.scan_parquet(file_paths, cast_options=pl.ScanCastOptions(integer_cast='allow-float'))
        df = lf.collect()
        return df
    except Exception as e:
        print(f"파일 읽기 중 오류 발생: {e}")
        return pl.DataFrame()

def apply_actual_age_logic(df: pl.DataFrame) -> pl.DataFrame:
    """
    birthday 컬럼을 기반으로 스크립트 실행 시점(now)의 실제 나이(now_age) 및 
    연령대 그룹(now_age_group)을 새롭게 계산하여 추가합니다.
    """
    if "birthday" not in df.columns:
        print("경고: birthday 컬럼이 존재하지 않아 now_age를 계산할 수 없습니다.")
        return df
        
    # 현재 날짜 가져오기
    now = datetime.now()
    current_date_num = now.year * 10000 + now.month * 100 + now.day
    
    # now_age 계산: (현재 날짜(YYYYMMDD) - birthday(YYYYMMDD)) // 10000
    calc_now_age = pl.when(pl.col("birthday").is_not_null()).then(
        ((current_date_num - pl.col("birthday").cast(pl.Int32, strict=False)) / 10000).floor().cast(pl.Int32)
    ).otherwise(None)
    
    # now_age_group 계산 (now_age 컬럼 생성 후 실행되어야 하므로 with_columns를 분리)
    calc_now_age_group = (
        pl.when(pl.col("now_age").is_null()).then(pl.lit("알수없음"))
        .when(pl.col("now_age") < 10).then(pl.lit("기타"))
        .when((pl.col("now_age") >= 10) & (pl.col("now_age") < 17)).then(pl.lit("10~16세"))
        .when((pl.col("now_age") >= 17) & (pl.col("now_age") < 20)).then(pl.lit("17~19세"))
        .when((pl.col("now_age") >= 20) & (pl.col("now_age") < 30)).then(pl.lit("20대"))
        .when((pl.col("now_age") >= 30) & (pl.col("now_age") < 40)).then(pl.lit("30대"))
        .when((pl.col("now_age") >= 40) & (pl.col("now_age") < 50)).then(pl.lit("40대"))
        .when((pl.col("now_age") >= 50) & (pl.col("now_age") < 60)).then(pl.lit("50대"))
        .otherwise(pl.lit("기타"))
    )

    return df.with_columns(
        calc_now_age.alias("now_age")
    ).with_columns(
        calc_now_age_group.alias("now_age_group")
    )

if __name__ == '__main__':
    print("=== Polars: rich_user 로드 및 실제 나이 계산 테스트 ===")
    import time
    start_time = time.time()
    
    df = load_rich_user_polars(['2022', '2023', '2024', '2025', '2026'])
    
    if not df.is_empty():
        df = apply_actual_age_logic(df)
        print(f"\n데이터 로드 완료. 총 건수: {df.height:,}건")
        
        # 간단한 집계 테스트 (now_age_group 별 카운트)
        agg_df = (
            df.group_by("now_age_group")
            .agg(pl.len().alias("user_count"))
            .sort("now_age_group")
        )
        
        elapsed_time = time.time() - start_time
        print(f"로드 및 집계 소요 시간: {elapsed_time:.2f}초\n")
        
        print("=== 연령대별 등록 유저 수 (Polars) ===")
        pl.Config.set_tbl_rows(15)
        print(agg_df)
    else:
        print("데이터가 없습니다.")
