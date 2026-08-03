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
    
    # 🌟 [에러 해결 핵심 코드] 날짜/시간(Timestamp) 컬럼들을 구글 전송이 가능한 문자열(텍스트)로 강제 변환합니다.
    df_new['최초 인입 일시'] = df_new['최초 인입 일시'].astype(str)
    df_new['최근 인입 일시'] = df_new['최근 인입 일시'].astype(str)
    
    # 2. 구글 시트 전송 직전에 수치 및 통계 컬럼들을 실제 순수 숫자(정수형) 타입으로 강제 정의
    num_cols = ['high', 'normal', 'create (등록)', 'assign (배정)', 'assign_cancel (배정취소)', 'done (완료)', 'cancel (취소)', '주차민원 총 횟수']
    for col in num_cols:
        df_new[col] = pd.to_numeric(df_new[col], errors='coerce').fillna(0).astype(int)
    
    # 결측치 처리 (빈 값이 있으면 대시로 대체)
    df_new = df_new.fillna("-")
    
    # 3. 기존 시트 내용 완전히 전체 삭제
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
def get_mysql_complains_data():
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
        C.address AS `주소`,
        R.region_name AS `운영 지역명`,
        C.type AS `민원 유형`,
        MIN(C.complained_at) AS `최초 인입 일시`,
        MAX(C.complained_at) AS `최근 인입 일시`,
        COUNT(CASE WHEN C.priority = 'high' THEN 1 END) AS `high`,
        COUNT(CASE WHEN C.priority = 'normal' THEN 1 END) AS `normal`, 
        COUNT(CASE WHEN C.state = 'create' THEN 1 END) AS `create (등록)`,
        COUNT(CASE WHEN C.state = 'assign' THEN 1 END) AS `assign (배정)`,
        COUNT(CASE WHEN C.state = 'assign_cancel' THEN 1 END) AS `assign_cancel (배정취소)`,
        COUNT(CASE WHEN C.state = 'done' THEN 1 END) AS `done (완료)`,
        COUNT(CASE WHEN C.state = 'cancel' THEN 1 END) AS `cancel (취소)`,
        COUNT(*) AS `주차민원 총 횟수`
    FROM gbike.rich_complains C
    LEFT JOIN gbike.rich_region R ON C.region_id = R.region_id
    WHERE C.type = '주차민원' 
      AND C.address IS NOT NULL
    GROUP BY 
        C.address,
        R.region_name,
        C.type
    ORDER BY `주차민원 총 횟수` DESC;
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ==========================================
# 실제 실행부
# ==========================================
if __name__ == "__main__":
    TARGET_SHEET_URL = "https://docs.google.com/spreadsheets/d/1_I17FuVcntuV-zMpEAIHmFgDNs5H3oUrK0khufIPw9M/edit"
    TARGET_TAB_NAME = "complainsraw" 
    
    print("1. 회사 MySQL에서 주차민원 최신 통계 데이터를 추출하는 중입니다...")
    complains_df = get_mysql_complains_data()
    
    print("2. 구글 시트에 업데이트를 시작합니다...")
    update_google_sheet_overwrite(complains_df, TARGET_SHEET_URL, TARGET_TAB_NAME)
    
    print("🎉 프로세스가 성공적으로 끝났습니다!")