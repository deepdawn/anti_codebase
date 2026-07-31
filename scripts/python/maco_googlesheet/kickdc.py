import pymysql
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def update_google_sheet_overwrite(df_new, spreadsheet_url, worksheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('scripts/python/maco_googlesheet/credentials.json', scope)
    client = gspread.authorize(creds)
    
    doc = client.open_by_url(spreadsheet_url)
    worksheet = doc.worksheet(worksheet_name)
    
    print(f"[{worksheet_name}] 탭의 기존 데이터를 비우고 추출 데이터 적재를 시작합니다...")
    
    # 데이터 전송 오류 방지용 포맷 정제
    df_new['usage_month'] = df_new['usage_month'].astype(str)
    
    # 통계/카운트 수치 컬럼들을 구글 시트가 숫자로 인식하도록 강제 변환
    num_cols = ['transfer_order_cnt', 'normal_order_cnt', 'total_order_cnt', 
                'transfer_user_cnt', 'normal_user_cnt', 'total_user_cnt']
    for col in num_cols:
        df_new[col] = pd.to_numeric(df_new[col], errors='coerce').fillna(0).astype(int)
        
    worksheet.clear()
    
    header = df_new.columns.tolist()
    rows = df_new.to_numpy().tolist()
    data_to_upload = [header] + rows
    
    worksheet.update(values=data_to_upload, range_name='A1')
    print(f"🎉 [{worksheet_name}] 추출 결과 적재 성공! (총 {len(df_new)}행 덮어씀)")

def get_mysql_heavy_data():
    conn = pymysql.connect(
        host='live.st.rds.gbility.io',
        port=3306,
        user='gbikemarketing',
        password='gbikemkt0514$@#!',
        database='gbike',
        charset='utf8mb4'
    )
    
    query = """
SELECT 
    YEAR(CONVERT_TZ(FROM_UNIXTIME(O.start_time), 'UTC', 'Asia/Seoul')) AS usage_year,
    MONTH(CONVERT_TZ(FROM_UNIXTIME(O.start_time), 'UTC', 'Asia/Seoul')) AS usage_month,
    E.region_name,
    M.model_type AS device_type,      
    CASE 
        WHEN LEFT(U.birthday, 4) > '2009' THEN '16세 미만'
        WHEN LEFT(U.birthday, 4) BETWEEN '2007' AND '2009' THEN '16~18세'
        WHEN LEFT(U.birthday, 4) BETWEEN '2001' AND '2006' THEN '19~24세'
        WHEN LEFT(U.birthday, 4) BETWEEN '1996' AND '2000' THEN '25~29세'
        WHEN LEFT(U.birthday, 4) BETWEEN '1986' AND '1995' THEN '30~39세'
        WHEN LEFT(U.birthday, 4) BETWEEN '1976' AND '1985' THEN '40~49세'
        WHEN LEFT(U.birthday, 4) <= '1975' THEN '50세 이상'
        ELSE '연령 미상'
    END AS age_group,
    -- [주문 수 카운트]
    COUNT(DISTINCT CASE WHEN D.type = 'gcooter_transfer' THEN O.order_id END) AS transfer_order_cnt,
    COUNT(DISTINCT O.order_id) - COUNT(DISTINCT CASE WHEN D.type = 'gcooter_transfer' THEN O.order_id END) AS normal_order_cnt,
    COUNT(DISTINCT O.order_id) AS total_order_cnt,
    -- [유저 수 카운트]
    COUNT(DISTINCT CASE WHEN D.type = 'gcooter_transfer' THEN U.user_id END) AS transfer_user_cnt,
    COUNT(DISTINCT U.user_id) - COUNT(DISTINCT CASE WHEN D.type = 'gcooter_transfer' THEN U.user_id END) AS normal_user_cnt,
    COUNT(DISTINCT U.user_id) AS total_user_cnt
FROM gbike.rich_orders O
LEFT JOIN gbike.rich_order_discounts D ON O.order_id = D.order_id 
JOIN gbike.rich_region R ON O.region_id = R.region_id
JOIN gbike.rich_region E ON R.parent_id = E.region_id
JOIN gbike.rich_bicycle_models M ON O.bicycle_type = M.type
LEFT JOIN gbike.rich_user U ON O.user_id = U.user_id
WHERE E.region_id = 209
  AND O.order_state = 2
  AND M.model_type = 'scooter'
  AND O.is_limit_free = 0
  AND O.start_time BETWEEN UNIX_TIMESTAMP(CONVERT_TZ('2025-01-01 00:00:00', 'Asia/Seoul', 'UTC')) 
                       AND UNIX_TIMESTAMP(CONVERT_TZ('2026-05-31 23:59:59', 'Asia/Seoul', 'UTC'))
GROUP BY 1, 2, 3, 4, 5
ORDER BY 1 ASC, 2 ASC, 5;
    """
    
    print("🚀 DB 연산을 시작합니다. 대용량 집계이므로 완료까지 1~2분 정도 묵묵히 기다려주세요...")
    df = pd.read_sql(query, conn)
    conn.close()
    return df

if __name__ == "__main__":
    # 🌟 원하시는 구글 시트 링크와 결과물을 뽑을 탭 이름을 적어주세요.
    TARGET_SHEET_URL = "https://docs.google.com/spreadsheets/d/1D0N_XWCaSq5pZVmF4kyuilQjG7240grR3LY42JnuHM4/edit?gid=0#gid=0"
    TARGET_TAB_NAME = "DB"
    
    result_df = get_mysql_heavy_data()
    update_google_sheet_overwrite(result_df, TARGET_SHEET_URL, TARGET_TAB_NAME)