import os
import sys
import pandas as pd
import time
from datetime import datetime

# utils 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.test_mysql_conn import get_engine

def main():
    base_save_path = "/Users/galaxy.jang/Google Drive/공유 드라이브/gbike.extract_deploy_spot_info"
    os.makedirs(base_save_path, exist_ok=True)
    
    file_path = os.path.join(base_save_path, "deploy_spot_info.parquet")
    
    query = """
    select rrr.region_name as high_region_name,rr.region_name as mid_region_name,r.region_name as low_region_name,
           rs.name as '배치존명',rs.location,rs.is_show,rs.bicycle_count,rs.created_at,rs.updated_at,rs.deleted_at,
           rs.id as deploy_zone_id,rs.bicycle_count as "설정대수",
           rr.region_id as middle_region_id
    from gbike.rich_release_spot rs
    join gbike.rich_region r on rs.region_id = r.region_id
    join gbike.rich_region rr on rr.region_id = r.parent_id
    join gbike.rich_region rrr on rrr.region_id = rr.parent_id
    """
    
    engine = get_engine()
    
    print(f"[{datetime.now()}] 배치존 마스터 정보 추출 시작...")
    start_time = time.time()
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
            
        # Parquet으로 덮어쓰기 저장
        df.to_parquet(file_path, engine='pyarrow', compression='snappy', index=False)
        elapsed_time = time.time() - start_time
        print(f"[{datetime.now()}] 성공적으로 저장되었습니다. (건수: {len(df):,}, 소요시간: {elapsed_time:.2f}초)")
        print(f"저장 경로: {file_path}")
    except Exception as e:
        print(f"[{datetime.now()}] 추출 또는 저장 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
