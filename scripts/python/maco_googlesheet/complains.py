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
    
    # 2. 날짜/시간 컬럼 서식 지정 및 문자열 변환 (JSON 변환 에러 방지)
    # 🌟 요청하신 '2026-06-20 09:54:00' 형태로 포맷팅합니다. 데이터가 없는(NaT/None) 칸은 빈 문자열로 처리합니다.
    time_cols = ['등록일시', '할당일시', '처리완료일시']
    for col in time_cols:
        if col in df_new.columns:
            df_new[col] = pd.to_datetime(df_new[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S').fillna("")

    # 3. 수치/통계 컬럼들을 실제 순수 숫자(정수형) 타입으로 명확히 정제
    num_cols = ['민원ID', '예상처리시간(분)']
    for col in num_cols:
        if col in df_new.columns:
            df_new[col] = pd.to_numeric(df_new[col], errors='coerce').fillna(0).astype(int)
            
    # 나머지 텍스트 컬럼들의 결측치 처리
    df_new = df_new.fillna("")
    
    # 4. 기존 시트 내용 완전히 전체 삭제 (Overwrite)
    worksheet.clear()
    
    # 5. 최신 데이터 전송 (자료형 유지)
    header = df_new.columns.tolist()
    rows = df_new.to_numpy().tolist()
    data_to_upload = [header] + rows
    
    worksheet.update(values=data_to_upload, range_name='A1')
    print(f"🎉 [{worksheet_name}] 최신 데이터 적재 완료! (총 {len(df_new)}행 새로 덮어씀)")

# ==========================================
# 회사 MySQL 데이터베이스 추출 함수
# ==========================================
def get_mysql_complains_db():
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
    C.address                    AS `주소`,
    R.region_name                AS `운영지역명`,
    C.id                         AS `민원ID`,
    C.bicycle_sn                 AS `기기번호`,
    C.type                       AS `민원유형(type)`,
    C.priority                   AS `우선순위`,
    C.state                      AS `상태`,
    C.content                    AS `민원내용`,
    C.expected_process_time      AS `예상처리시간(분)`,
    DATE_ADD(C.created_at, INTERVAL 9 HOUR)    AS `등록일시`,
    DATE_ADD(C.assigned_at, INTERVAL 9 HOUR)   AS `할당일시`,
    DATE_ADD(C.processed_at, INTERVAL 9 HOUR)  AS `처리완료일시`,
    C.memo                       AS `처리메모`
FROM gbike.rich_complains C
LEFT JOIN gbike.rich_region R ON C.region_id = R.region_id
WHERE C.type IN ('주차민원', '상습민원')
  AND C.created_at >= DATE_SUB('2026-01-01 00:00:00', INTERVAL 9 HOUR)
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ==========================================
# 실제 실행부
# ==========================================
if __name__ == "__main__":
    # 제공해주신 구글 시트 URL 및 탭 이름 반영
    TARGET_SHEET_URL = "https://docs.google.com/spreadsheets/d/1dU1v5YUyADOC3IgRhGBsxyq8mQAyEwXDcNt3MQSb1Ns/edit?gid=1538439944#gid=1538439944"
    TARGET_TAB_NAME = "DB2" 
    
    print("1. 회사 MySQL에서 민원 상세 데이터를 추출하는 중입니다...")
    complains_df = get_mysql_complains_db()
    
    print("2. 구글 시트에 업데이트를 시작합니다...")
    update_google_sheet_overwrite(complains_df, TARGET_SHEET_URL, TARGET_TAB_NAME)
    
    print("🎉 모든 프로세스가 성공적으로 완료되었습니다!")