import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.test_mysql_conn import get_engine

def extract_delta_out_of_area(target_date_str, engine):
    """지정된 날짜의 order_id와 추가 델타 컬럼만 추출"""
    query = f"""
    SELECT
        order_id,
        bicycle_type,
        country_code,
        coupon_id
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
        print(f"Error extracting delta for {target_date_str}: {e}")
        return None

def main():
    base_save_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_orders"
    start_date_str = '2022-01-01'
    end_date_str = '2022-12-31'
    
    date_list = pd.date_range(start=start_date_str, end=end_date_str, freq='D')
    engine = get_engine()
    
    print(f"총 {len(date_list)}일 치 델타 데이터 추출 및 병합 작업을 시작합니다.")
    
    for dt in date_list:
        target_date_str = dt.strftime('%Y-%m-%d')
        daily_folder_name = f"dt={target_date_str}"
        file_path = os.path.join(base_save_path, daily_folder_name, f"rich_orders_{target_date_str}.parquet")
        
        if not os.path.exists(file_path):
            print(f"[{target_date_str}] 대상 파케이 파일이 존재하지 않아 건너뜁니다: {file_path}")
            continue
            
        print(f"[{target_date_str}] 델타 처리 중...")
        start_time = time.time()
        
        # 1. DB에서 누락된 컬럼 추출
        delta_df = extract_delta_out_of_area(target_date_str, engine)
        
        if delta_df is not None and not delta_df.empty:
            try:
                # 2. 기존 파케이 로드
                original_df = pd.read_parquet(file_path)
                
                # 이미 컬럼이 존재하는지 방어 로직
                for col in ['bicycle_type', 'country_code', 'coupon_id']:
                    if col in original_df.columns:
                        original_df = original_df.drop(columns=[col])
                
                # 3. 조인 (order_id 기준 left join)
                merged_df = pd.merge(original_df, delta_df, on='order_id', how='left')
                
                # 4. 덮어쓰기
                merged_df.to_parquet(file_path, index=False)
                
                elapsed_time = time.time() - start_time
                print(f"[{target_date_str}] 병합 완료 (원본 {len(original_df)}건 -> 병합 후 {len(merged_df)}건). 소요시간: {elapsed_time:.2f}초")
                
            except Exception as e:
                print(f"[{target_date_str}] 병합 중 오류 발생: {e}")
        elif delta_df is not None and delta_df.empty:
             print(f"[{target_date_str}] DB에 해당 날짜의 델타 데이터가 없습니다.")

if __name__ == '__main__':
    main()
