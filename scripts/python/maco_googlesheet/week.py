import psycopg2  # Redshift 연결용 라이브러리
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
        # 처음 적재할 때도 데이터 전송 직전 수치들을 숫자 타입으로 정제
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
    
    # 3. 데이터 업데이트 로직 실행 (A~I열 기준 키 매칭)
    key_columns = list(df_new.columns[:9]) 
    
    # 기존 데이터(df_old)에서 새로운 데이터(df_new)와 기준(A~I)이 겹치는 행은 삭제합니다.
    df_old_filtered = df_old[~df_old[key_columns].isin(df_new[key_columns].to_dict('list')).all(axis=1)]
    
    # 필터링된 기존 데이터와 새로운 데이터를 결합합니다.
    df_final = pd.concat([df_old_filtered, df_new], ignore_index=False)
    
    # 기준 컬럼 순서대로 다시 이쁘게 정렬
    df_final = df_final.sort_values(by=key_columns).reset_index(drop=True)

    # 🌟 구글 시트 전송 직전에 수치 및 매출 컬럼들을 실제 순수 숫자 타입으로 강제 재정의
    df_final['할당대수'] = pd.to_numeric(df_final['할당대수'], errors='coerce').fillna(0).astype(int)
    df_final['배치수'] = pd.to_numeric(df_final['배치수'], errors='coerce').fillna(0).astype(int)
    df_final['운행수'] = pd.to_numeric(df_final['운행수'], errors='coerce').fillna(0).astype(int)
    df_final['revenue'] = pd.to_numeric(df_final['revenue'], errors='coerce').fillna(0).astype(float)
    
    # 4. 최종 정제된 데이터를 구글 시트에 복사
    worksheet.clear()
    
    # 순수 자료형(int, float)을 유지한 상태로 리스트화하여 구글 시트 전송
    header = df_final.columns.tolist()
    rows = df_final.to_numpy().tolist()
    data_to_upload = [header] + rows
    
    worksheet.update(values=data_to_upload, range_name='A1')
    print(f"[{worksheet_name}] 데이터 비교 및 업데이트 완료! (최종 {len(df_final)}행 적재됨)")

# ==========================================
# 회사 Redshift 데이터베이스 추출 함수
# ==========================================
def get_redshift_regional_data():
    conn = psycopg2.connect(
        host='live-redshift-cluster-gbike.comng6zxlpsm.ap-northeast-2.redshift.amazonaws.com',
        port=5439,
        user='rmteam',
        password='Gbike@rmteam@20230510!',
        dbname='gbike'
    )
    
    # 🌟 [쿼리 수정] 월과 주 컬럼을 CAST(... AS INT)로 감싸서 앞의 0을 완전히 제거합니다.
    query = """
    SELECT 
        date AS "일자",                                       -- 1
        LEFT(date, 4) AS "연도",                               -- 2
        CAST(SUBSTRING(date, 6, 2) AS INT) AS "월",            -- 3 (01 -> 1 형변환)
        CAST(TO_CHAR(CAST(date AS DATE), 'IW') AS INT) AS "주", -- 4 (01 -> 1 형변환)
        CASE EXTRACT(DOW FROM CAST(date AS DATE))             -- 5
            WHEN 1 THEN '월'
            WHEN 2 THEN '화'
            WHEN 3 THEN '수'
            WHEN 4 THEN '목'
            WHEN 5 THEN '금'
            WHEN 6 THEN '토'
            WHEN 0 THEN '일'
        END AS "요일",
        high_region_name AS "대지역",                          -- 6
        middle_region_name AS "중지역",                        -- 7
        CASE                                                 -- 8
            WHEN model IN ('OMNI BICYCLE', 'GCOO-B3', 'GCOO-B2', 'GCOO-B4', 'A200P') THEN 'bicycle'
            WHEN model IN ('ES4', 'Max', 'Max Pro', 'GCOO-K1', 'Max Plus', 'GCOO-K2', 'Max Plus X', 'GCOO-K3') THEN 'scooter'
            ELSE 'none'
        END AS "기기구분",
        SUM(assigned_count) AS "할당대수",
        SUM(deployed_count) AS "배치수",
        SUM(order_count) AS "운행수",
        SUM((calculated_pay_amount + calculated_out_of_area_charge) / 1.1) AS "revenue"
    FROM gbike.rich_daily_statistics
    WHERE date BETWEEN '2025-01-01' AND '2026-12-31'
    AND high_region_name NOT IN ('East','North', 'Central', 'South', '미국법인', '괌 대지역','유테크','서울본사','서울시견인대지역','vietnam','본사직영_안산R&D 대지역','ghana')
    AND middle_region_name NOT IN ('폐기/정비 킥보드_파트너사','폐기킥보드_경기남부운영팀','폐기킥보드_전남운영팀','폐기킥보드_서울운영팀','폐기킥보드_충청운영팀','RS그룹')
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 8
    ORDER BY 1, 2, 3, 4, 5, 6, 7, 8, 8;
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ==========================================
# 실제 실행부
# ==========================================
if __name__ == "__main__":
    # 🌟 타겟 구글 시트 주소와 탭 이름을 입력하세요.
    TARGET_SHEET_URL = "https://docs.google.com/spreadsheets/d/1lSTkF_FH-QqACfpHJXbkLM2-QYl06wtJqLxukWhNjjA/edit?pli=1&gid=129441416#gid=129441416"
    TARGET_TAB_NAME = "weekraw" 
    
    print("1. 회사 Redshift에서 일별 지역 통계 데이터를 추출하는 중입니다...")
    regional_df = get_redshift_regional_data()
    
    print("2. 구글 시트의 기존 데이터와 비교하여 업데이트를 시작합니다...")
    update_google_sheet_upsert(regional_df, TARGET_SHEET_URL, TARGET_TAB_NAME)
    
    print("🎉 프로세스가 성공적으로 끝났습니다!")