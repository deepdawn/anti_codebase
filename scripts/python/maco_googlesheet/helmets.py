import pymysql
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# 1. MySQL 데이터베이스에서 데이터 가져오는 함수
# ==========================================
def get_mysql_data():
    # 본인의 실제 MySQL 접속 정보로 변경하세요 (따옴표 유지)
    conn = pymysql.connect(
        host='live.st.rds.gbility.io',     # 예: '192.168.0.1' 또는 'db.company.com'
        port=3306,                  # 회사 MySQL 포트가 다르면 수정 (보통 3306)
        user='gbikemarketing',       # 예: 'kyungjun'
        password='gbikemkt0514$@#!',   # 예: 'password123!'
        database='gbike',     # 접속할 스키마/데이터베이스 이름
        charset='utf8mb4'
    )
    
    # 회사에서 평소에 쓰시던 SQL 추출 쿼리문을 적어주세요.
    # 주의: 쿼리문 끝에 세미콜론(;)은 빼고 적으시는 것이 안전합니다.
    query = """select *
from rich_complains
where type in ('주차민원','지자체민원','상습민원')
order by created_at desc
limit 100"""
    
    # pandas(pd)가 쿼리를 실행해 표(DataFrame) 형태로 데이터를 가져옵니다.
    df = pd.read_sql(query, conn)
    
    # 데이터 가져오기가 끝났으니 DB 연결을 닫습니다.
    conn.close()
    return df

# ==========================================
# 2. 구글 시트를 업데이트하는 함수
# ==========================================
def update_google_sheet(df, spreadsheet_url, worksheet_name):
    # 구글 인증
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('scripts/python/maco_googlesheet/credentials.json', scope)
    client = gspread.authorize(creds)
    
    doc = client.open_by_url(spreadsheet_url)
    worksheet = doc.worksheet(worksheet_name)
    
    worksheet.clear()
    
    # 🌟 [이 부분 수정] 날짜 데이터(Timestamp)를 구글이 읽을 수 있는 문자열(str)로 통째로 변환합니다.
    df_clean = df.astype(str)
    
    # 최신 gspread 버전에 맞게 데이터 구조를 생성합니다.
    data_to_upload = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
    
    # 🌟 [이 부분 수정] 경고가 나지 않도록 최신 문법(values= 데이터, range_name= 범위)으로 변경했습니다.
    worksheet.update(values=data_to_upload, range_name='A1')
    print(f"[{worksheet_name}] 탭에 업데이트 완료했습니다!")

# ==========================================
# 3. 프로그램 실제 실행부
# ==========================================
if __name__ == "__main__":
    # 데이터가 채워질 구글 시트의 전체 URL 주소를 입력하세요.
    TARGET_SHEET_URL = "https://docs.google.com/spreadsheets/d/1lSTkF_FH-QqACfpHJXbkLM2-QYl06wtJqLxukWhNjjA/edit?pli=1&gid=0#gid=0"
    
    # 데이터를 밀어 넣을 구글 시트의 '탭 이름'을 정확히 적어주세요.
    TARGET_TAB_NAME = "raw" 
    
    print("1. 회사 MySQL에서 데이터를 추출하는 중입니다...")
    mysql_data_df = get_mysql_data()
    
    print("2. 구글 시트로 데이터를 전송하는 중입니다...")
    update_google_sheet(mysql_data_df, TARGET_SHEET_URL, TARGET_TAB_NAME)
    
    print("모든 프로세스가 성공적으로 끝났습니다!")

