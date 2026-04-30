import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
import urllib.parse
import os
import sys
from datetime import datetime, timedelta

def get_engine():
    host = 'live.st.rds.gbility.io'
    user = 'gbikemarketing'
    password = urllib.parse.quote_plus('gbikemkt0514$@#!')
    port = 3306
    database = 'gbike'
    try:
        engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
        return engine
    except Exception as e:
        print(f"Engine creation failed: {e}")
        sys.exit(1)

def main():
    base_dir = "/Users/galaxy/codebase"
    result_dir = "/Users/galaxy/codebase/results/data_extract"
    os.makedirs(result_dir, exist_ok=True)

    # 1. 추출 기간 설정 (2026-01-01 ~ 2026-02-28)
    start_date = datetime(2026, 1, 1)
    end_limit = datetime(2026, 2, 28) + timedelta(days=1)
    
    # 2. 파일 이름 동적 생성 (예: 0101_0228_gbike_revenue_extract.xlsx)
    prefix = f"{start_date.strftime('%m%d')}_{end_limit.strftime('%m%d')}"
    result_file = os.path.join(result_dir, f"{prefix}_gbike_revenue_extract.xlsx")

    # 4일 단위로 기간 생성
    date_ranges = []
    current_start = start_date
    while current_start < end_limit:
        current_end = min(current_start + timedelta(days=4), end_limit)
        date_ranges.append((current_start.strftime('%Y-%m-%d %H:%M:%S'), current_end.strftime('%Y-%m-%d %H:%M:%S')))
        current_start = current_end

    engine = get_engine()
    all_dfs = []

    for start, end in date_ranges:
        print(f"Extracting: {start} ~ {end}...")
        
        query = f"""
        SELECT
            DATE(FROM_UNIXTIME(O.add_time + 32400)) AS kst_date,
            G.region_name AS depth1_region,
            E.region_name AS depth2_region,
            R.region_name AS depth3_region,
            O.from_api,
            CASE O.bicycle_type
                WHEN 1 THEN 'GCOO-B1' WHEN 2 THEN 'UNKNOWN' WHEN 3 THEN '에어드레서'
                WHEN 9 THEN 'ES4' WHEN 10 THEN 'Max' WHEN 11 THEN 'Max Pro'
                WHEN 12 THEN 'GCOO-K1' WHEN 13 THEN 'Max Plus' WHEN 14 THEN '슈드레서'
                WHEN 15 THEN 'OMNI BICYCLE' WHEN 16 THEN 'GCOO-K2' WHEN 17 THEN 'GCOO-B3'
                WHEN 18 THEN 'GCOO-B2' WHEN 19 THEN 'Max Plus X' WHEN 22 THEN 'GCOO-B4'
                WHEN 23 THEN 'GCOO-K3' WHEN 24 THEN 'A200P'
                ELSE CONCAT('기타(', IFNULL(O.bicycle_type, 'NULL'), ')')
            END AS model_name,
            SUM((CASE WHEN O.from_api = 'gcooter' THEN O.pay_amount ELSE O.order_amount END + O.out_of_area_charge) / 1.1) AS net_revenue
        FROM gbike.rich_orders O
        JOIN gbike.rich_region R ON O.region_id = R.region_id
        JOIN gbike.rich_region E ON R.parent_id = E.region_id
        JOIN gbike.rich_region G ON E.parent_id = G.region_id
        WHERE O.order_state = 2 AND O.currency_code = 'krw' AND G.country_code = 'kr'
          AND O.add_time >= UNIX_TIMESTAMP('{start}') - 32400
          AND O.add_time <  UNIX_TIMESTAMP('{end}') - 32400
        GROUP BY kst_date, depth1_region, depth2_region, depth3_region, O.from_api, model_name
        """
        
        try:
            with engine.connect() as connection:
                df_chunk = pd.read_sql(query, connection)
                if not df_chunk.empty:
                    all_dfs.append(df_chunk)
                print(f"Chunk complete: {len(df_chunk)} rows")
        except Exception as e:
            print(f"Error during chunk extraction ({start}): {e}")
            return

    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        # 같은 그룹 데이터 합산
        final_df = final_df.groupby(['kst_date', 'depth1_region', 'depth2_region', 'depth3_region', 'from_api', 'model_name']).sum(numeric_only=True).reset_index()
        
        final_df.to_excel(result_file, index=False, engine='openpyxl')
        print(f"Final file saved: {result_file} (Total: {len(final_df)} rows)")

if __name__ == "__main__":
    main()
