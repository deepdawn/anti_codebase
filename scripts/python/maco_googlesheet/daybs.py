import pymysql
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# 구글 시트 데이터 비교 및 교체(Upsert) 함수
# ==========================================
def update_google_sheet_upsert(df_new, spreadsheet_url, worksheet_name):
    # 1. 구글 인증 및 시트 열기
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('scripts/python/maco_googlesheet/credentials.json', scope)
    client = gspread.authorize(creds)
    
    doc = client.open_by_url(spreadsheet_url)
    worksheet = doc.worksheet(worksheet_name)
    
    # 새로 가져온 데이터의 컬럼 타입을 문자로 통일 (비교를 위해)
    df_new = df_new.astype(str)
    
    # 2. 구글 시트에 이미 적재되어 있는 기존 데이터 가져오기
    existing_data = worksheet.get_all_values()
    
    # 시트가 완전히 비어있다면 그냥 새로 뽑은 데이터 통째로 넣고 종료
    if not existing_data or len(existing_data) <= 1:
        # 처음 적재할 때도 데이터 전송 직전 금액 수치들을 숫자(정수) 타입으로 정제
        df_new['판매금액'] = pd.to_numeric(df_new['판매금액'], errors='coerce').fillna(0).astype(int)
        df_new['환불금액'] = pd.to_numeric(df_new['환불금액'], errors='coerce').fillna(0).astype(int)
        df_new['순매출'] = pd.to_numeric(df_new['순매출'], errors='coerce').fillna(0).astype(int)
        
        data_to_upload = [df_new.columns.values.tolist()] + df_new.values.tolist()
        worksheet.update(values=data_to_upload, range_name='A1')
        print(f"[{worksheet_name}] 시트가 비어있어 데이터를 처음으로 채웠습니다.")
        return

    # 기존 시트 데이터를 파이썬 표(DataFrame) 형태로 변환
    df_old = pd.DataFrame(existing_data[1:], columns=existing_data[0])
    
    # 3. 데이터 업데이트 로직 실행 (A~C열 기준 키 매칭)
    # 🌟 [수정] 컬럼 변경에 맞춰 쿼리 결과의 앞 3개 컬럼(일자, 판매 부스터, 결제통화)을 기준 키로 잡습니다.
    key_columns = list(df_new.columns[:3]) 
    
    # 기존 데이터(df_old)에서 새로운 데이터(df_new)와 기준(A~C)이 겹치는 행은 삭제합니다.
    df_old_filtered = df_old[~df_old[key_columns].isin(df_new[key_columns].to_dict('list')).all(axis=1)]
    
    # 필터링된 기존 데이터와 새로운 데이터를 결합합니다.
    df_final = pd.concat([df_old_filtered, df_new], ignore_index=False)
    
    # 기준 컬럼 순서대로 다시 이쁘게 정렬
    df_final = df_final.sort_values(by=key_columns).reset_index(drop=True)

    # 🌟 [핵심 수정] 구글 시트 전송 직전에 금액 컬럼들을 실제 순수 숫자(정수형) 타입으로 강제 재정의
    df_final['판매금액'] = pd.to_numeric(df_final['판매금액'], errors='coerce').fillna(0).astype(int)
    df_final['환불금액'] = pd.to_numeric(df_final['환불금액'], errors='coerce').fillna(0).astype(int)
    df_final['순매출'] = pd.to_numeric(df_final['순매출'], errors='coerce').fillna(0).astype(int)
    
    # 4. 최종 정제된 데이터를 구글 시트에 복사
    worksheet.clear()
    
    # 파이썬 고유의 자료형(int)을 그대로 유지하며 리스트화하여 구글 시트가 숫자로 강제 인식하게 합니다.
    header = df_final.columns.tolist()
    rows = df_final.to_numpy().tolist()
    data_to_upload = [header] + rows
    
    worksheet.update(values=data_to_upload, range_name='A1')
    print(f"[{worksheet_name}] 데이터 비교 및 업데이트 완료! (최종 {len(df_final)}행 적재됨)")

# ==========================================
# 회사 MySQL 데이터베이스 추출 함수
# ==========================================
def get_mysql_boosters_data():
    conn = pymysql.connect(
        host='live.st.rds.gbility.io',
        port=3306,
        user='gbikemarketing',
        password='gbikemkt0514$@#!',
        database='gbike',
        charset='utf8mb4'
    )
    
    # 일자 단위 포맷팅 및 컬럼 축소 쿼리문 반영
    query = """
    SELECT 
        DATE_FORMAT(CONVERT_TZ(b.created_at, 'UTC', 'Asia/Seoul'), '%Y-%m-%d') AS "일자",
        a.title AS "판매 부스터",
        b.currency_code AS "결제통화",
        SUM(b.price) AS "판매금액",
        IFNULL(SUM(r.total_refund_amount), 0) AS "환불금액",
        SUM(b.price) - IFNULL(SUM(r.total_refund_amount), 0) AS "순매출"
    FROM gbike.rich_boosters a         
    JOIN gbike.rich_booster_orders b ON a.id = b.booster_id 
    LEFT JOIN (
        SELECT 
            booster_order_id, 
            SUM(refund_amount) AS total_refund_amount
        FROM gbike.rich_booster_refunds
        WHERE deleted_at IS NULL  
        GROUP BY booster_order_id
    ) r ON b.id = r.booster_order_id 
    WHERE b.payment_success = 1  
      AND b.created_at BETWEEN CONVERT_TZ('2026-01-01 00:00:00', 'Asia/Seoul', 'UTC') 
                           AND CONVERT_TZ('2026-12-31 23:59:59', 'Asia/Seoul', 'UTC')
      AND a.country_code = 'kr'
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3;
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ==========================================
# 실제 실행부
# ==========================================
if __name__ == "__main__":
    # 타겟 주소와 탭 이름은 그대로 유지해 두었습니다.
    TARGET_SHEET_URL = "https://docs.google.com/spreadsheets/d/1lSTkF_FH-QqACfpHJXbkLM2-QYl06wtJqLxukWhNjjA/edit?pli=1&gid=1437564469#gid=1437564469"
    TARGET_TAB_NAME = "daybs raw" 
    
    print("1. 회사 MySQL에서 부스터 판매/환불 데이터를 추출하는 중입니다...")
    boosters_df = get_mysql_boosters_data()
    
    print("2. 구글 시트의 기존 데이터와 비교하여 업데이트를 시작합니다...")
    update_google_sheet_upsert(boosters_df, TARGET_SHEET_URL, TARGET_TAB_NAME)
    
    print("🎉 프로세스가 성공적으로 끝났습니다!")