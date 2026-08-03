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
        # 🌟 처음 적재할 때도 데이터 전송 직전 수치들을 숫자 타입으로 정제
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
    
    # 3. 데이터 업데이트 로직 실행 (A~B열 기준 키 매칭)
    # 쿼리 결과의 앞 2개 컬럼: 일자, 기기구분
    key_columns = list(df_new.columns[:2]) 
    
    # 기존 데이터(df_old)에서 새로운 데이터(df_new)와 기준(A~B)이 겹치는 행은 삭제합니다.
    df_old_filtered = df_old[~df_old[key_columns].isin(df_new[key_columns].to_dict('list')).all(axis=1)]
    
    # 필터링된 기존 데이터와 새로운 데이터를 결합합니다.
    df_final = pd.concat([df_old_filtered, df_new], ignore_index=False)
    
    # 기준 컬럼 순서대로 다시 이쁘게 정렬
    df_final = df_final.sort_values(by=key_columns).reset_index(drop=True)

    # 🌟 [핵심 수정] 구글 시트 전송 직전에 수치 및 매출 컬럼들을 실제 순수 숫자 타입으로 강제 재정의
    df_final['할당대수'] = pd.to_numeric(df_final['할당대수'], errors='coerce').fillna(0).astype(int)
    df_final['배치수'] = pd.to_numeric(df_final['배치수'], errors='coerce').fillna(0).astype(int)
    df_final['운행수'] = pd.to_numeric(df_final['운행수'], errors='coerce').fillna(0).astype(int)
    df_final['revenue'] = pd.to_numeric(df_final['revenue'], errors='coerce').fillna(0).astype(float)
    
    # 4. 최종 정제된 데이터를 구글 시트에 복사
    worksheet.clear()
    
    # 🌟 [핵심 변경] 전체가 문자로 강제 변환되는 현상을 막기 위해 순수 자료형(int, float)을 유지한 상태로 리스트화
    header = df_final.columns.tolist()
    rows = df_final.to_numpy().tolist()
    data_to_upload = [header] + rows
    
    worksheet.update(values=data_to_upload, range_name='A1')
    print(f"[{worksheet_name}] 데이터 비교 및 업데이트 완료! (최종 {len(df_final)}행 적재됨)")

# ==========================================
# 회사 Redshift 데이터베이스 추출 함수
# ==========================================
def get_redshift_daily_data():
    conn = psycopg2.connect(
        host='live-redshift-cluster-gbike.comng6zxlpsm.ap-northeast-2.redshift.amazonaws.com',
        port=5439,
        user='rmteam',
        password='Gbike@rmteam@20230510!',
        dbname='gbike'
    )
    
    # 요청하신 일별 기기구분 쿼리문
    query = """
  SELECT 
    date AS "일자",
    high_region_name AS "대지역", -- 🌟 [추가] 대지역 컬럼 추가
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
WHERE date BETWEEN '2026-01-01' AND '2026-12-31'
  -- 🌟 [추가] 요청하신 7개 특정 RS팀/영업팀 데이터만 필터링합니다.
  AND high_region_name IN ('강남RS팀', '경상RS팀', '남부RS팀', '서울RS팀', '중앙RS팀', '프로젝트_루미', '가맹영업팀', 'RS그룹')
  AND middle_region_name NOT LIKE '%폐기%'
GROUP BY 1, 2, 3  -- 🌟 [수정] 일자, 대지역, 기기구분 기준으로 그룹화 (3번째 열까지 확대)
ORDER BY 1, 2, 3; -- 🌟 [수정] 동일한 순서로 정렬
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ==========================================
# 실제 실행부
# ==========================================
if __name__ == "__main__":
    # 지정하신 타겟 구글 시트 주소와 탭 이름(dayraw)으로 세팅 완료했습니다.
    TARGET_SHEET_URL = "https://docs.google.com/spreadsheets/d/1lSTkF_FH-QqACfpHJXbkLM2-QYl06wtJqLxukWhNjjA/edit?pli=1&gid=1316866828#gid=1316866828"
    TARGET_TAB_NAME = "dayraw" 
    
    print("1. 회사 Redshift에서 일별 통계 데이터를 추출하는 중입니다...")
    daily_df = get_redshift_daily_data()
    
    print("2. 구글 시트의 기존 데이터와 비교하여 업데이트를 시작합니다...")
    update_google_sheet_upsert(daily_df, TARGET_SHEET_URL, TARGET_TAB_NAME)
    
    print("🎉 프로세스가 성공적으로 끝났습니다!")