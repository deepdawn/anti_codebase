import pymysql
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# 구글 시트 데이터 초기화 후 새로 쓰기(Overwrite) 함수
# ==========================================
def update_google_sheet_overwrite(df_new, spreadsheet_url, worksheet_name):
    # 1. 구글 인증 및 시트 열기
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('scripts/python/maco_googlesheet/credentials.json', scope)
    client = gspread.authorize(creds)
    
    doc = client.open_by_url(spreadsheet_url)
    worksheet = doc.worksheet(worksheet_name)
    
    print(f"[{worksheet_name}] 탭의 기존 데이터를 비우고 새로 적재를 시작합니다...")
    
    # 2. 데이터 전송 오류 방지를 위한 정제 작업
    # 문자가 섞이거나 비어있을 수 있는 텍스트성 컬럼들의 결측치 처리
    str_cols = ['년도', '대분류', '중분류', '기기타입']
    for col in str_cols:
        if col in df_new.columns:
            df_new[col] = df_new[col].astype(str).fillna("-")
            
    # 수치/통계 컬럼들을 실제 순수 숫자(정수형) 타입으로 명확히 정제
    num_cols = ['월', '월의_일수', '작업자_수', '실교체_배터리_건수', '유효_재배치_건수']
    for col in num_cols:
        if col in df_new.columns:
            df_new[col] = pd.to_numeric(df_new[col], errors='coerce').fillna(0).astype(int)
    
    # 3. 기존 시트 내용 완전히 전체 삭제 (Overwrite 준비)
    worksheet.clear()
    
    # 4. 최신 데이터 전송 (자료형 유지)
    header = df_new.columns.tolist()
    rows = df_new.to_numpy().tolist()
    data_to_upload = [header] + rows
    
    worksheet.update(values=data_to_upload, range_name='A1')
    print(f"🎉 [{worksheet_name}] 최신 데이터 적재 완료! (총 {len(df_new)}행 새로 덮어씀)")

# ==========================================
# 회사 MySQL 데이터베이스 추출 함수
# ==========================================
def get_mysql_task_data():
    conn = pymysql.connect(
        host='live.st.rds.gbility.io',
        port=3306,
        user='gbikemarketing',
        password='gbikemkt0514$@#!',
        database='gbike',
        charset='utf8mb4'
    )
    
    # 🌟 [수정 포인트] DATE_FORMAT 대신 YEAR() 함수를 사용하여 파이썬 % 기호 충돌을 원천 차단했습니다.
    query = """
SELECT
    YEAR(DATE_ADD(T.ended_at, INTERVAL 9 HOUR))                 AS '년도',
    MONTH(DATE_ADD(T.ended_at, INTERVAL 9 HOUR))                AS '월',
    CASE
        WHEN YEAR(DATE_ADD(T.ended_at, INTERVAL 9 HOUR)) = YEAR(DATE_ADD(NOW(), INTERVAL 9 HOUR))
         AND MONTH(DATE_ADD(T.ended_at, INTERVAL 9 HOUR)) = MONTH(DATE_ADD(NOW(), INTERVAL 9 HOUR))
        THEN DAY(DATE_SUB(CAST(DATE_ADD(NOW(), INTERVAL 9 HOUR) AS DATE), INTERVAL 1 DAY))
        ELSE DAY(LAST_DAY(DATE_ADD(T.ended_at, INTERVAL 9 HOUR)))
    END AS '나눌_일수',
    G.region_name                    AS '대분류',
    E.region_name                    AS '중분류',
    T.model_type                     AS '기기타입',
    COUNT(DISTINCT T.admin_id)       AS '작업자_수',
    COUNT(CASE WHEN T.type = 'BATTERY'    THEN 1 END) AS '실교체_배터리_건수',
    COUNT(CASE WHEN T.type = 'RELOCATION' THEN 1 END) AS '유효_재배치_건수',
    -- 📌 [변경] 일평균 건수 계산 시에도 분모를 '어제 일자' 기준으로 동일하게 맞춤
    ROUND(COUNT(CASE WHEN T.type = 'BATTERY' THEN 1 END) /
          NULLIF(CASE
              WHEN YEAR(DATE_ADD(T.ended_at, INTERVAL 9 HOUR)) = YEAR(DATE_ADD(NOW(), INTERVAL 9 HOUR))
               AND MONTH(DATE_ADD(T.ended_at, INTERVAL 9 HOUR)) = MONTH(DATE_ADD(NOW(), INTERVAL 9 HOUR))
              THEN DAY(DATE_SUB(CAST(DATE_ADD(NOW(), INTERVAL 9 HOUR) AS DATE), INTERVAL 1 DAY))
              ELSE DAY(LAST_DAY(DATE_ADD(T.ended_at, INTERVAL 9 HOUR)))
          END, 0), 2) AS '일평균_배터리_건수',
    ROUND(COUNT(CASE WHEN T.type = 'RELOCATION' THEN 1 END) /
          NULLIF(CASE
              WHEN YEAR(DATE_ADD(T.ended_at, INTERVAL 9 HOUR)) = YEAR(DATE_ADD(NOW(), INTERVAL 9 HOUR))
               AND MONTH(DATE_ADD(T.ended_at, INTERVAL 9 HOUR)) = MONTH(DATE_ADD(NOW(), INTERVAL 9 HOUR))
              THEN DAY(DATE_SUB(CAST(DATE_ADD(NOW(), INTERVAL 9 HOUR) AS DATE), INTERVAL 1 DAY))
              ELSE DAY(LAST_DAY(DATE_ADD(T.ended_at, INTERVAL 9 HOUR)))
          END, 0), 2) AS '일평균_재배치_건수'
FROM gbike.rich_tasks T
         JOIN gbike.rich_region R ON T.region_id = R.region_id
         JOIN gbike.rich_region E ON R.parent_id = E.region_id
         JOIN gbike.rich_region G ON E.parent_id = G.region_id
WHERE T.type IN ('BATTERY', 'RELOCATION')
  AND T.result = 1
  AND R.country_code = 'kr'
  AND T.ended_at < DATE_SUB(CAST(DATE_ADD(NOW(), INTERVAL 9 HOUR) AS DATE), INTERVAL 9 HOUR)
  AND T.ended_at >= DATE_SUB('2026-07-01 00:00:00', INTERVAL 9 HOUR)
GROUP BY
    YEAR(DATE_ADD(T.ended_at, INTERVAL 9 HOUR)),
    MONTH(DATE_ADD(T.ended_at, INTERVAL 9 HOUR)),
    G.region_name,
    E.region_name,
    T.model_type
ORDER BY
    년도 DESC,
    월 DESC,
    대분류,
    중분류,
    기기타입;
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ==========================================
# 실제 실행부
# ==========================================
if __name__ == "__main__":
    TARGET_SHEET_URL = "https://docs.google.com/spreadsheets/d/1lSTkF_FH-QqACfpHJXbkLM2-QYl06wtJqLxukWhNjjA/edit"
    TARGET_TAB_NAME = "relomonthraw2" 
    
    print("1. 회사 MySQL에서 월별 작업 통계 데이터를 추출하는 중입니다...")
    task_df = get_mysql_task_data()
    
    print("2. 구글 시트에 업데이트를 시작합니다...")
    update_google_sheet_overwrite(task_df, TARGET_SHEET_URL, TARGET_TAB_NAME)
    
    print("🎉 모든 프로세스가 성공적으로 완료되었습니다!")