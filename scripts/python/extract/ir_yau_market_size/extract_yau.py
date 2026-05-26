import sys
import os
import time
import pandas as pd
from datetime import datetime

root_dir = '/Users/galaxy/anti_codebase'
sys.path.append(os.path.join(root_dir, 'scripts/python/utils'))
from test_mysql_conn import run_query

def extract_yau_data():
    date_chunks = [
        ('2023-01-01 00:00:00', '2023-07-01 00:00:00'),
        ('2023-07-01 00:00:00', '2024-01-01 00:00:00'),
        ('2024-01-01 00:00:00', '2024-07-01 00:00:00'),
        ('2024-07-01 00:00:00', '2025-01-01 00:00:00'),
        ('2025-01-01 00:00:00', '2025-07-01 00:00:00'),
        ('2025-07-01 00:00:00', '2026-01-01 00:00:00')
    ]

    all_data = []

    for idx, (start_date, end_date) in enumerate(date_chunks, 1):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Chunk {idx}/6 데이터 추출 중... ({start_date} ~ {end_date})")
        
        query = f"""
        WITH region_info AS (
            SELECT 
                r.region_id,
                r.region_name AS small_region,
                rr.region_name AS mid_region,
                rrr.region_name AS large_region
            FROM gbike.rich_region r
            LEFT JOIN gbike.rich_region rr ON r.parent_id = rr.region_id
            LEFT JOIN gbike.rich_region rrr ON rr.parent_id = rrr.region_id
        ),
        base_data AS (
            SELECT
                EXTRACT(YEAR FROM CONVERT_TZ(FROM_UNIXTIME(O.add_time), 'UTC', 'Asia/Seoul')) AS `연도`,
                CASE 
                    WHEN O.bicycle_type IN (15, 17, 18, 22, 24) THEN '자전거'
                    ELSE '킥보드'
                END AS `기기`,
                CASE 
                    WHEN r.small_region LIKE '%%서울%%' OR r.large_region LIKE '%%서울%%' THEN '서울'
                    WHEN r.small_region LIKE '%%경기%%' OR r.small_region LIKE '%%인천%%' 
                         OR r.large_region LIKE '%%경기%%' OR r.large_region LIKE '%%인천%%' THEN '경인'
                    ELSE '지방'
                END AS `지역`,
                (CAST(EXTRACT(YEAR FROM CONVERT_TZ(FROM_UNIXTIME(O.add_time), 'UTC', 'Asia/Seoul')) AS SIGNED) 
                 - CAST(SUBSTRING(U.birthday, 1, 4) AS SIGNED)) AS age,
                O.user_id
            FROM gbike.rich_orders O FORCE INDEX (IDX_ADD_TIME_START_LAT_START_LNG)
            JOIN gbike.rich_user U ON O.user_id = U.user_id
            JOIN region_info r ON O.region_id = r.region_id
            WHERE O.order_state = 2 
              AND O.add_time >= UNIX_TIMESTAMP(CONVERT_TZ('{start_date}', 'Asia/Seoul', 'UTC'))
              AND O.add_time < UNIX_TIMESTAMP(CONVERT_TZ('{end_date}', 'Asia/Seoul', 'UTC'))
              AND U.birthday IS NOT NULL 
              AND LENGTH(U.birthday) >= 4
        )
        SELECT DISTINCT
            `연도`,
            `기기`,
            `지역`,
            CASE 
                WHEN age >= 10 AND age < 20 THEN '10대'
                WHEN age >= 20 AND age < 30 THEN '20대'
                WHEN age >= 30 AND age < 40 THEN '30대'
                WHEN age >= 40 THEN '40대 이상'
                ELSE '기타/알수없음'
            END AS `연령`,
            user_id
        FROM base_data
        WHERE age >= 10 AND age <= 100
        """
        
        df_chunk = run_query(query)
        
        if df_chunk is not None and not df_chunk.empty:
            all_data.append(df_chunk)
        
        if idx < len(date_chunks):
            print("DB 부하 완화를 위해 10초간 대기합니다...\n")
            time.sleep(10)
            
    print("\n모든 청크 데이터 추출 완료. 병합 및 YAU 집계 시작...")
    
    if not all_data:
        print("추출된 데이터가 없습니다.")
        return
        
    df_merged = pd.concat(all_data, ignore_index=True)
    
    # 엑셀의 최대 row 한계치(1,048,576)를 넘을 수 있는 원천 row 데이터이므로 raw 저장은 생략하고, 
    # 분석된 집계 결과를 results 폴더에 저장합니다.
    print(f"Total raw distinct users before dedup: {len(df_merged)}")
    df_merged = df_merged.drop_duplicates(subset=['연도', '기기', '지역', '연령', 'user_id'])
    print(f"Total pure YAU users after dedup: {len(df_merged)}")
    
    df_final = df_merged.groupby(['연도', '기기', '지역', '연령']).size().reset_index(name='유저수')
    df_final = df_final.sort_values(by=['연도', '기기', '지역', '연령']).reset_index(drop=True)
    
    # 결과물 폴더
    result_dir = os.path.join(root_dir, 'results', 'ir_yau_market_size')
    os.makedirs(result_dir, exist_ok=True)
    
    save_path = os.path.join(result_dir, 'yau_analysis_2023_2025.xlsx')
    df_final.to_excel(save_path, index=False)
    
    print(f"\n[성공] YAU 집계 완료! 파일 저장 위치: {save_path}")
    print(df_final)

if __name__ == "__main__":
    extract_yau_data()
