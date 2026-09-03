import os
import sys
import pandas as pd
import time
from sqlalchemy import text

# utils 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils.test_mysql_conn import get_engine

def extract_repair_statistics(engine):
    query = """
    SELECT
        C.team_name,
        C.camp_name,
        CASE
            when rb.type in (15,17,18,22,24) then 'Bicycle'
            when rb.type in (9,10,11,12,13,16,19,23) then 'Scooter'
        else 'none' END as vehicle_type,
        case
            when R.state in ('접 수','정비중') then '정비대기'
            when R.state in ('정비완료','출고완료') then '정비완료'
        else R.state end as state,
        date(DATE_ADD(R.registered_at,INTERVAL 9 HOUR)) as registerd_date,
        date(DATE_ADD(R.completed_at,INTERVAL 9 HOUR)) as completed_date,
        count(R.vehicle_sn) as `수량`,
        sum(R.amount) `비용`
    FROM
        gbike_maintenance.maintenance_wizard_repairs R
            JOIN
        gbike_maintenance.camps C ON R.camp_id = C.id
        join gbike.rich_bicycle rb on rb.bicycle_sn = R.vehicle_sn
    WHERE
        R.camp_id != 1
    group by 1,2,3,4,5,6
    """
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(text(query), connection)
        return df
    except Exception as e:
        print(f"Error extracting data: {e}")
        return None

def main():
    base_save_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike_maintenance.repair_statistics"
    save_path = os.path.join(base_save_path, "repair_statistics.parquet")
    
    engine = get_engine()
    
    print("전체 정비 통계 데이터 추출을 시작합니다.")
    start_time = time.time()
    
    df = extract_repair_statistics(engine)
    
    if df is not None:
        os.makedirs(base_save_path, exist_ok=True)
        df.to_parquet(save_path, index=False)
        elapsed = time.time() - start_time
        print(f"성공적으로 저장되었습니다. (건수: {len(df):,}, 소요시간: {elapsed:.2f}초)")
        print(f"저장 경로: {save_path}")
    else:
        print("데이터 추출 실패")

if __name__ == '__main__':
    main()
