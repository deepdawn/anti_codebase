import psycopg2
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def update_google_sheet_upsert(df_new, spreadsheet_url, worksheet_name):
    # 1. 구글 인증 및 시트 열기
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('scripts/python/maco_googlesheet/credentials.json', scope)
    client = gspread.authorize(creds)
    
    doc = client.open_by_url(spreadsheet_url)
    worksheet = doc.worksheet(worksheet_name)
    
    # 새로 가져온 데이터의 컬럼 타입을 문자로 통일 (비교를 위해)
    df_new = df_new.astype(str)

    # '월' 컬럼의 왼쪽 '0'을 완전히 제거합니다. (06 -> 6)
    df_new['월'] = df_new['월'].str.lstrip('0')
    
    # 2. 구글 시트에 이미 적재되어 있는 기존 데이터 가져오기
    existing_data = worksheet.get_all_values()
    
    # 시트가 완전히 비어있다면 그냥 새로 뽑은 데이터 통째로 넣고 종료
    if not existing_data or len(existing_data) <= 1:
        df_new['할당대수'] = pd.to_numeric(df_new['할당대수'], errors='coerce').fillna(0).astype(int)
        df_new['배치수'] = pd.to_numeric(df_new['배치수'], errors='coerce').fillna(0).astype(int)
        df_new['운행수'] = pd.to_numeric(df_new['운행수'], errors='coerce').fillna(0).astype(int)
        df_new['revenue'] = pd.to_numeric(df_new['revenue'], errors='coerce').fillna(0).astype(float)
        
        data_to_upload = [df_new.columns.values.tolist()] + df_new.values.tolist()
        worksheet.update(values=data_to_upload, range_name='A1')
        print(f"[{worksheet_name}] 시트가 비어있어 데이터를 처음으로 채웠습니다.")
        return

    # 기존 시트 데이터를 파이썬 표(DataFrame) 형태로 변환
    df_old = pd.DataFrame(existing_data[1:], columns=existing_data[0])
    
    # 3. 데이터 업데이트 로직 실행 (A~E열 기준)
    key_columns = list(df_new.columns[:5]) 
    
    # 기존 데이터(df_old)에서 새로운 데이터(df_new)와 기준(A~E)이 겹치는 행은 지워버립니다.
    df_old_filtered = df_old[~df_old[key_columns].isin(df_new[key_columns].to_dict('list')).all(axis=1)]
    
    # 필터링된 기존 데이터와 새로운 데이터를 하나로 합칩니다.
    df_final = pd.concat([df_old_filtered, df_new], ignore_index=False)
    
    # 원래 쿼리 순서대로 이쁘게 다시 정렬
    df_final = df_final.sort_values(by=key_columns).reset_index(drop=True)

    # 🌟 [보완] 수치 및 매출 컬럼들을 구글 시트 전송 직전에 실제 순수 숫자 타입으로 강제 재정의
    df_final['할당대수'] = pd.to_numeric(df_final['할당대수'], errors='coerce').fillna(0).astype(int)
    df_final['배치수'] = pd.to_numeric(df_final['배치수'], errors='coerce').fillna(0).astype(int)
    df_final['운행수'] = pd.to_numeric(df_final['운행수'], errors='coerce').fillna(0).astype(int)
    df_final['revenue'] = pd.to_numeric(df_final['revenue'], errors='coerce').fillna(0).astype(float)
    
    # 4. 최종 정제된 데이터를 구글 시트에 덮어쓰기
    worksheet.clear()
    
    # 🌟 [핵심 변경] 리스트화 과정에서 텍스트형 따옴표 강제 적용을 방지
    header = df_final.columns.tolist()
    rows = df_final.to_numpy().tolist()
    data_to_upload = [header] + rows
    
    worksheet.update(values=data_to_upload, range_name='A1')
    print(f"[{worksheet_name}] 데이터 비교 및 업데이트 완료! (최종 {len(df_final)}행 적재됨)")

# ==========================================
# Redshift 데이터 추출 함수
# ==========================================
def get_redshift_data():
    conn = psycopg2.connect(
        host='live-redshift-cluster-gbike.comng6zxlpsm.ap-northeast-2.redshift.amazonaws.com',
        port=5439,
        user='rmteam',
        password='Gbike@rmteam@20230510!',
        dbname='gbike'
    )
    
    query = """
    SELECT 
        LEFT(date, 4) AS "연도",
        SUBSTRING(date, 6, 2) AS "월",
        high_region_name,
        middle_region_name, 
        CASE
            WHEN model IN ('OMNI BICYCLE', 'GCOO-B3', 'GCOO-B2', 'GCOO-B4', 'A200P') THEN 'bicycle'
            WHEN model IN ('ES4', 'Max', 'Max Pro', 'GCOO-K1', 'Max Plus', 'GCOO-K2', 'Max Plus X', 'GCOO-K3') THEN 'scooter'
            ELSE 'none'
        END AS "기기구분",
        SUM(assigned_count) AS "할당대수",
        SUM(deployed_count) AS "배치수",
        SUM(order_count) AS "운행수",
        SUM((calculated_pay_amount + calculated_out_of_area_charge) / 1.1) AS "revenue"
    FROM gbike.rich_daily_statistics
    WHERE date >= '2026-08-01' 
    AND middle_region_name NOT LIKE '%폐기%'
    GROUP BY 1, 2, 3, 4, 5
    ORDER BY 1, 2, 3, 4, 5;
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

if __name__ == "__main__":
    REDSHIFT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1lSTkF_FH-QqACfpHJXbkLM2-QYl06wtJqLxukWhNjjA/edit?pli=1&gid=1437564469#gid=1437564469"
    REDSHIFT_TAB_NAME = "raw2"
    
    print("1. Redshift에서 최신 데이터를 추출합니다...")
    new_df = get_redshift_data()
    
    print("2. 구글 시트의 기존 데이터와 비교하여 업데이트를 시작합니다...")
    update_google_sheet_upsert(new_df, REDSHIFT_SHEET_URL, REDSHIFT_TAB_NAME)