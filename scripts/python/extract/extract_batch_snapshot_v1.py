import os
import sys
import pandas as pd
import shutil
from datetime import datetime, timedelta

# 프로젝트 루트 및 유틸 경로 설정
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
utils_path = os.path.join(project_root, 'scripts/python/utils')
sys.path.append(utils_path)

from test_mysql_conn import run_query
from teams_email_mcp import send_email

def extract_batch_snapshot():
    print("=== [batch_snapshot_v1] Data Extraction Started ===")
    
    # 1. Snapshot Data (dataframe_bicycle_snapshot)
    # scripts/sql/reference/rich_bicycle.sql 파일 내용 기반
    snapshot_sql = """
    with region as (
    select	r.region_id,
    		r.region_name as '소지역',
    		rr.region_name as '중지역',
    		rrr.region_name as '대지역'
    from	gbike.rich_region r
    join	gbike.rich_region rr on r.parent_id = rr.region_id
    join	gbike.rich_region rrr on rr.parent_id = rrr.region_id
    where	1=1
    )
    select	date_sub(CURRENT_DATE(), interval 1 day) as base_date,
    		rb.bicycle_sn,
    		rb.bicycle_id,
    		rb.region_id, -- 소지역
    		r.`소지역`,
    		r.`중지역`,
    		r.`대지역`,
    		rb.current_speed_mode,
    		rb.pre_order_id,
    		rb.status,
    		CASE
    			when rb.type in (15,17,18,22,24) then 'Bicycle'
    			when rb.type in (9,10,11,12,13,16,19,23) then 'Scooter'
    		else 'none'	END as one_category,
    		CASE
    			when rb.type = 1 then 'none'
    			when rb.type = 2 then 'none'
    			when rb.type = 3 then '에어드레서'
    			when rb.type = 9 then 'SC_ES4'
    			when rb.type = 10 then 'SC_MAX'
    			when rb.type = 11 then 'SC_MAX Pro'
    			when rb.type = 12 then 'SC_GCOO-K1'
    			when rb.type = 13 then 'SC_Max Plus'
    			when rb.type = 14 then '슈드레서'
    			when rb.type = 15 then 'BI_OMNI bicycle'
    			when rb.type = 16 then 'SC_GCOO-K2'
    			when rb.type = 17 then 'BI_GCOO-B3'
    			when rb.type = 18 then 'BI_GCOO-B2'
    			when rb.type = 19 then 'SC_Max Plus X'
    			when rb.type = 22 then 'BI_GCOO-B4'
    			when rb.type = 23 then 'SC_GCOO-K3'
    			when rb.type = 24 then 'BI_A200P'
    		else 'none'	END as two_category,
    		case when regexp_like(rb.region_name, '임대|파트너') then 1 else 0 end as franchise_yn,
    		CONVERT_TZ(FROM_UNIXTIME(rb.add_time),'UTC','Asia/Seoul') as registerd_at,
    		CONVERT_TZ(FROM_UNIXTIME(rb.last_used_time),'UTC','Asia/Seoul') as last_used_at,
    		rb.speed_mode ->'$.low_speed_limit' AS low_speed,
    		rb.speed_mode ->'$.high_speed_limit' AS high_speed
    from gbike.rich_bicycle rb
    join region r on rb.region_id = r.region_id
    where is_activated = 1
    """
    
    print("Fetching Snapshot Data...")
    df_snapshot = run_query(snapshot_sql)
    if df_snapshot is None:
        print("Failed to fetch snapshot data.")
        return

    # 2. Trip Data (dataframe_bicycle_trip)
    # 사용자가 제공한 add_time 조건 반영
    trip_sql = """
    SELECT 
        bicycle_id,
        COUNT(*) as trip_count
    FROM gbike.rich_orders
    WHERE add_time >= UNIX_TIMESTAMP(CURDATE() - INTERVAL 1 DAY) - 9*60*60 
      AND add_time < UNIX_TIMESTAMP(CURDATE()) - 9*60*60
      AND order_state = 2
    GROUP BY bicycle_id
    """
    
    print("Fetching Trip Data...")
    df_trip = run_query(trip_sql)
    if df_trip is None:
        print("Failed to fetch trip data.")
        return

    # 3. Join Data
    print("Joining Snapshot and Trip Data...")
    df_merged = pd.merge(df_snapshot, df_trip, on='bicycle_id', how='left')
    df_merged['trip_count'] = df_merged['trip_count'].fillna(0)
    
    # 4. Aggregation
    print("Aggregating Results...")
    # 그룹핑 기준: base_date, 대지역, 중지역, one_category
    agg_result = df_merged.groupby(['base_date', '대지역', '중지역','소지역', 'one_category']).agg(
        기기_카운트=('bicycle_id', 'nunique'), # 캠프별 할당 대수 (중복 제거)
        운행_대수=('trip_count', lambda x: (x > 0).sum()), # 운행 데이터가 존재하는 고유 기기 수
        운행_수=('trip_count', 'sum') # 전체 트립 합계
    ).reset_index()
    
    # 컬럼명 정리
    agg_result.rename(columns={
        '기기_카운트': '기기 카운트 (할당)',
        '운행_대수': '운행 대수 (실제)',
        '운행_수': '운행 수'
    }, inplace=True)

    # 5. Save to Excel directly to OneDrive
    save_date = (datetime.now() - timedelta(days=1)).strftime('%y%m%d')
    file_name = f'batch_snapshot_v1_{save_date}.xlsx'
    
    onedrive_base = "/Users/galaxy/Library/CloudStorage/OneDrive-지바이크/서비스운영본부 - 현장데이터 개발센터/results/data_extract/batch_snapshot_v1"
    onedrive_dir = os.path.join(onedrive_base, save_date)
    
    if os.path.exists(onedrive_base):
        os.makedirs(onedrive_dir, exist_ok=True)
        onedrive_path = os.path.join(onedrive_dir, file_name)
        print(f"Saving Result directly to OneDrive: {onedrive_path}...")
        try:
            agg_result.to_excel(onedrive_path, index=False)
        except Exception as e:
            print(f"Failed to save to OneDrive: {e}")
            return None
    else:
        print(f"OneDrive path not found: {onedrive_base}")
        return None
    
    # 6. Teams Notification
    print("Sending Teams Notification...")
    total_allocated = agg_result['기기 카운트 (할당)'].sum()
    total_operated = agg_result['운행 대수 (실제)'].sum()
    total_trips = agg_result['운행 수'].sum()
    
    subject = f"[Batch] batch_snapshot_v1 완료 ({save_date})"
    body = f"""[batch_snapshot_v1] 처리가 완료되었습니다.

- 기준 일자: {agg_result['base_date'].iloc[0]}
- 총 할당 기기 수: {total_allocated:,.0f} 대
- 총 운행 기기 수: {total_operated:,.0f} 대
- 총 운행 수: {total_trips:,.0f} 건

상세 결과는 첨부파일 및 아래 경로를 확인하세요.
경로: {onedrive_path}
"""
    
    res = send_email(subject, body, onedrive_path)
    print(f"Teams Notification Result: {res}")
    
    print("=== [batch_snapshot_v1] Process Completed Successfully ===")
    return onedrive_path

if __name__ == "__main__":
    extract_batch_snapshot()
