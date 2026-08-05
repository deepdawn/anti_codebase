import os
import sys
import pandas as pd
import polars as pl
from datetime import datetime, timedelta
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.test_mysql_conn import get_engine

def load_order_ids_from_parquet(target_date_str):
    """
    미리 추출된 rich_orders 파케이 파일에서 해당 날짜의 order_id 목록을 가져옵니다.
    """
    base_orders_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_orders"
    file_path = os.path.join(base_orders_path, f"dt={target_date_str}", f"rich_orders_{target_date_str}.parquet")
    
    if not os.path.exists(file_path):
        print(f"  [오류] 기준이 되는 rich_orders 파일이 없습니다: {file_path}")
        return None
        
    try:
        # Polars로 order_id 컬럼만 빠르게 로드
        lf = pl.scan_parquet(file_path, missing_columns='insert', extra_columns='ignore')
        df = lf.select(['order_id']).collect()
        
        # null 제거 및 고유값만 리스트로 반환 (혹시 모를 중복 방지)
        order_ids = df.drop_nulls().unique().to_series().to_list()
        return order_ids
    except Exception as e:
        print(f"  [오류] rich_orders 파일 읽기 실패: {e}")
        return None

def extract_discounts_for_chunk(order_id_chunk, engine):
    """
    주어진 order_id 리스트(chunk)에 대해 DB 쿼리를 실행하여 할인데이터를 가져옵니다.
    """
    if not order_id_chunk:
        return None
        
    # 리스트를 콤마로 구분된 문자열로 변환
    order_ids_str = ",".join(map(str, order_id_chunk))
    
    query = f"""
    SELECT 
        order_id,
        user_id,
        amount,
        type,
        discount_applied_info,
        created_at,
        updated_at
    FROM gbike.rich_order_discounts
    WHERE order_id IN ({order_ids_str})
    """
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        print(f"    [오류] Chunk 데이터 추출 실패: {e}")
        return None

def main():
    base_save_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_order_discounts"
    
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
        
    date_list = pd.date_range(start=start_date_str, end=end_date, freq='D')
    engine = get_engine()
    
    print(f"총 {len(date_list)}일 치 할인 데이터 추출을 시작합니다.")
    print(f"저장 기본 경로: {base_save_path}")
    
    has_error = False
    chunk_size = 20000  # 2만 건씩 청킹
    
    for dt in date_list:
        target_date_str = dt.strftime('%Y-%m-%d')
        
        daily_folder_name = f"dt={target_date_str}"
        daily_folder_path = os.path.join(base_save_path, daily_folder_name)
        os.makedirs(daily_folder_path, exist_ok=True)
        
        file_path = os.path.join(daily_folder_path, f"rich_order_discounts_{target_date_str}.parquet")
        
        if os.path.exists(file_path) and '--overwrite' not in sys.argv:
            print(f"[{target_date_str}] 파일이 이미 존재하여 스킵합니다: {file_path}")
            continue
            
        print(f"[{target_date_str}] 데이터 추출 시작...")
        start_time = time.time()
        
        # 1. order_id 로드
        order_ids = load_order_ids_from_parquet(target_date_str)
        if order_ids is None:
            has_error = True
            continue
            
        if len(order_ids) == 0:
            print(f"  [{target_date_str}] 추출할 order_id가 없습니다. (트립 0건)")
            # 빈 DataFrame 저장
            empty_df = pd.DataFrame(columns=['order_id', 'user_id', 'amount', 'type', 'discount_applied_info', 'created_at', 'updated_at'])
            empty_df.to_parquet(file_path, index=False)
            continue
            
        print(f"  - 대상 order_id 총 {len(order_ids):,}건 로드 완료.")
        
        # 2. Chunk 분할 및 DB 조회
        chunk_dfs = []
        total_chunks = (len(order_ids) + chunk_size - 1) // chunk_size
        
        for i in range(total_chunks):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(order_ids))
            chunk = order_ids[start_idx:end_idx]
            
            df_chunk = extract_discounts_for_chunk(chunk, engine)
            
            if df_chunk is not None and not df_chunk.empty:
                chunk_dfs.append(df_chunk)
            elif df_chunk is None:
                has_error = True
                
        # 3. 데이터 병합 및 저장
        if chunk_dfs:
            final_df = pd.concat(chunk_dfs, ignore_index=True)
        else:
            final_df = pd.DataFrame(columns=['order_id', 'user_id', 'amount', 'type', 'discount_applied_info', 'created_at', 'updated_at'])
            
        try:
            final_df.to_parquet(file_path, index=False)
            elapsed_time = time.time() - start_time
            print(f"[{target_date_str}] 성공적으로 저장되었습니다. (추출 할인건수: {len(final_df):,}, 소요시간: {elapsed_time:.2f}초)")
        except Exception as e:
            print(f"[{target_date_str}] 파일 저장 중 오류 발생: {e}")
            has_error = True
            
    if has_error:
        print("경고: 하나 이상의 날짜 추출 또는 저장에 실패했습니다.")
        sys.exit(1)

if __name__ == '__main__':
    main()
