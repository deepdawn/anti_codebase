import os
import polars as pl
from datetime import datetime, timedelta

def load_segment_trend_for_dates(dates: list, base_path="/Users/galaxy/Google Drive/공유 드라이브/gbike.rich_user_segment"):
    """
    특정 날짜(문자열 'YYYY-MM-DD' 리스트)에 해당하는 rich_user_segment 데이터를 
    Polars로 읽어와서 일자별(dt) 세그먼트(segment)별 비중을 집계하여 반환합니다.
    """
    file_patterns = []
    for dt_str in dates:
        dir_path = os.path.join(base_path, f"dt={dt_str}")
        if os.path.exists(dir_path):
            file_patterns.append(os.path.join(dir_path, "*.parquet"))
        else:
            print(f"[{dt_str}] 세그먼트 데이터 폴더를 찾을 수 없습니다: {dir_path}")
            
    if not file_patterns:
        print("조회 기간에 해당하는 세그먼트 데이터가 없습니다.")
        return pl.DataFrame()
        
    try:
        lf = pl.scan_parquet(file_patterns, hive_partitioning=True, cast_options=pl.ScanCastOptions(integer_cast='allow-float'))
        agg_lf = (
            lf.group_by(["dt", "segment"])
            .agg(pl.len().alias("user_count"))
        )
        agg_lf = agg_lf.with_columns(
            pl.col("user_count").sum().over("dt").alias("daily_total_users")
        )
        agg_lf = agg_lf.with_columns(
            (pl.col("user_count") / pl.col("daily_total_users") * 100).alias("segment_ratio")
        )
        df = agg_lf.collect().sort(["dt", "segment"])
        return df
    except Exception as e:
        print(f"세그먼트 데이터 집계 중 오류 발생: {e}")
        return pl.DataFrame()

def load_segment_trend_polars(start_date: str, end_date: str, base_path="/Users/galaxy/Google Drive/공유 드라이브/gbike.rich_user_segment"):
    """
    지정된 시작일과 종료일 사이의 rich_user_segment 데이터를 
    Polars로 읽어와서 일자별(dt) 세그먼트(segment)별 비중을 집계하여 반환합니다.
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    file_patterns = []
    current_dt = start_dt
    while current_dt <= end_dt:
        dt_str = current_dt.strftime('%Y-%m-%d')
        dir_path = os.path.join(base_path, f"dt={dt_str}")
        if os.path.exists(dir_path):
            file_patterns.append(os.path.join(dir_path, "*.parquet"))
        else:
            # 폴더가 없는 경우 경고 출력
            print(f"[{dt_str}] 세그먼트 데이터 폴더를 찾을 수 없습니다: {dir_path}")
        current_dt += timedelta(days=1)
        
    if not file_patterns:
        print("조회 기간에 해당하는 세그먼트 데이터가 없습니다.")
        return pl.DataFrame()
        
    try:
        # hive_partitioning=True 옵션을 통해 폴더의 dt=... 부분을 컬럼으로 가져옵니다.
        lf = pl.scan_parquet(file_patterns, hive_partitioning=True, cast_options=pl.ScanCastOptions(integer_cast='allow-float'))
        
        # 전체 데이터에서 필요한 건 dt, segment, user_id(고유 여부 확인이나 갯수) 인데
        # row 1개가 1유저이므로 그냥 row count를 구합니다.
        
        agg_lf = (
            lf.group_by(["dt", "segment"])
            .agg(pl.len().alias("user_count"))
        )
        
        # 일자별 총 사용자 수 계산을 위해 윈도우 함수 사용
        agg_lf = agg_lf.with_columns(
            pl.col("user_count").sum().over("dt").alias("daily_total_users")
        )
        
        # 비중(%) 계산
        agg_lf = agg_lf.with_columns(
            (pl.col("user_count") / pl.col("daily_total_users") * 100).alias("segment_ratio")
        )
        
        df = agg_lf.collect().sort(["dt", "segment"])
        return df
    except Exception as e:
        print(f"세그먼트 데이터 집계 중 오류 발생: {e}")
        return pl.DataFrame()

def load_segment_ltv_for_date(date_str: str, base_path="/Users/galaxy/Google Drive/공유 드라이브/gbike.rich_user_segment"):
    """
    특정 날짜의 세그먼트 데이터를 읽어 세그먼트별 평균 LTV를 계산하여 반환합니다.
    """
    dir_path = os.path.join(base_path, f"dt={date_str}")
    if not os.path.exists(dir_path):
        print(f"[{date_str}] 세그먼트 데이터 폴더를 찾을 수 없습니다: {dir_path}")
        return pl.DataFrame()
        
    file_patterns = [os.path.join(dir_path, "*.parquet")]
    
    try:
        lf = pl.scan_parquet(file_patterns, cast_options=pl.ScanCastOptions(integer_cast='allow-float'))
        
        # ltv 컬럼명 확인 (대소문자 무관하게 처리하거나, 없으면 빈 데이터프레임 반환)
        columns = lf.columns
        ltv_col = None
        for col in columns:
            if col.lower() in ['ltv', 'cltv', 'user_ltv']:
                ltv_col = col
                break
                
        if not ltv_col:
            print(f"[{date_str}] 세그먼트 데이터에 LTV 컬럼이 존재하지 않습니다.")
            return pl.DataFrame()
            
        agg_lf = (
            lf.group_by("segment")
            .agg(pl.col(ltv_col).mean().alias("avg_ltv"))
        )
        df = agg_lf.collect().sort("segment")
        return df
    except Exception as e:
        print(f"LTV 집계 중 오류 발생: {e}")
        return pl.DataFrame()

if __name__ == '__main__':
    # Test script
    import time
    start_time = time.time()
    
    # 최근 14일 테스트
    end_date_str = datetime.now().strftime('%Y-%m-%d')
    start_date_str = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    
    print(f"{start_date_str} ~ {end_date_str} 데이터 로드 테스트...")
    df = load_segment_trend_polars(start_date_str, end_date_str)
    
    if not df.is_empty():
        print(f"집계 완료. 소요 시간: {time.time() - start_time:.2f}초")
        print(df.head(10))
    else:
        print("데이터 로드 실패.")
