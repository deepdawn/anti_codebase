import pandas as pd
from datetime import datetime, timedelta
import calendar
import sys
import os

# scripts/python 경로를 sys.path에 추가하여 utils 모듈을 불러올 수 있게 함
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from scripts.python.utils.test_db_conn import run_query

def get_month_partitions(start_year, start_month, end_year, end_month):
    """
    KST 기준 월별 시작/종료 UTC 타임스탬프 리스트를 생성합니다.
    """
    partitions = []
    curr_year, curr_month = start_year, start_month
    while (curr_year < end_year) or (curr_year == end_year and curr_month <= end_month):
        start_dt = datetime(curr_year, curr_month, 1)
        _, last_day = calendar.monthrange(curr_year, curr_month)
        end_dt = datetime(curr_year, curr_month, last_day, 23, 59, 59)
        
        # DB가 UTC 기준이므로 KST(UTC+9) 시간을 UTC로 변환 (9시간 차감)
        start_ts = int((start_dt - timedelta(hours=9)).timestamp())
        end_ts = int((end_dt - timedelta(hours=9)).timestamp())
        
        partitions.append({
            'ym': f"{curr_year}-{curr_month:02d}",
            'start_ts': start_ts,
            'end_ts': end_ts
        })
        
        if curr_month == 12:
            curr_month, curr_year = 1, curr_year + 1
        else:
            curr_month += 1
    return partitions

def extract_abnormal_trips_chunked(start_year, start_month, end_year, end_month, camp_name='서초캠프'):
    """
    월별로 분할하여 이상 거리가 발생한 트립 데이터를 추출하고 통합 집계합니다.
    """
    partitions = get_month_partitions(start_year, start_month, end_year, end_month)
    all_abnormal_trips = []

    for p in partitions:
        print(f"[{p['ym']}] 데이터 추출 중... (UTC Range: {p['start_ts']} ~ {p['end_ts']})")
        
        # 각 월별로 이상 거리(100m 이상)가 발생한 로우만 추출하는 최적화 쿼리
        query = f"""
        SELECT user_id, 
               '{p['ym']}' as ym,
               dist_m
        FROM (
            SELECT O.user_id,
                   ST_Distance_Sphere(O.end_point, 
                                      LEAD(O.start_point) OVER (PARTITION BY O.bicycle_sn ORDER BY O.add_time)) AS dist_m
            FROM gbike.rich_orders O
            JOIN gbike.rich_region R ON O.region_id = R.region_id
            JOIN gbike.rich_region E ON R.parent_id = E.region_id
            WHERE O.order_state = 2
              AND E.region_name = '{camp_name}'
              AND O.add_time BETWEEN {p['start_ts']} AND {p['end_ts']}
              AND O.bicycle_type IN (15, 17, 18, 22, 24)
        ) t
        WHERE dist_m >= 100
        """
        
        df_month = run_query(query)
        if df_month is not None and not df_month.empty:
            all_abnormal_trips.append(df_month)
            print(f" -> {len(df_month)}건 추출 완료")
        else:
            print(f" -> 해당 월 데이터 없음")

    if not all_abnormal_trips:
        print("최종적으로 추출된 데이터가 없습니다.")
        return None

    # 1. 전체 기간 데이터 통합
    df_total = pd.concat(all_abnormal_trips)

    # 2. Heavy User 식별 (전체 기간 동안 이상 트립 10회 이상 발생한 유저)
    user_counts = df_total.groupby('user_id').size()
    heavy_user_ids = user_counts[user_counts >= 10].index
    print(f"총 {len(heavy_user_ids)}명의 Heavy User 식별됨 (이상 트립 10회 이상)")

    # 3. Heavy User의 월별 이상 트립 수 집계
    result = df_total[df_total['user_id'].isin(heavy_user_ids)]
    final_summary = result.groupby('ym').size().reset_index(name='monthly_abnormal_count')
    
    return final_summary

if __name__ == "__main__":
    # 1. 기간 설정 (의사결정 결과 반영: 25년 1월 ~ 26년 4월)
    START_Y, START_M = 2025, 1
    END_Y, END_M = 2026, 4
    CAMP = '서초캠프'
    
    # 2. 결과 저장 경로 설정 (사용자로부터 폴더명을 확인받은 후 실행할 예정)
    # 현재는 스크립트 구조 확인을 위해 임시 경로를 주석 처리해 둡니다.
    # SUBFOLDER_NAME = "seocho_abnormal_analysis"
    # OUTPUT_DIR = f"/Users/galaxy/codebase/results/{SUBFOLDER_NAME}"
    # os.makedirs(OUTPUT_DIR, exist_ok=True)
    # FILE_PATH = os.path.join(OUTPUT_DIR, f"abnormal_user_summary_{START_Y}{START_M:02d}_{END_Y}{END_M:02d}.xlsx")
    
    print(f"--- {CAMP} 이상 유저 월별 분석 시작 (기간: {START_Y}-{START_M:02d} ~ {END_Y}-{END_M:02d}) ---")
    summary = extract_abnormal_trips_chunked(START_Y, START_M, END_Y, END_M, CAMP)
    
    if summary is not None:
        print("\n[월별 집계 결과]")
        print(summary)
        
        # 엑셀 파일 저장 로직 추가
        # summary.to_excel(FILE_PATH, index=False)
        # print(f"\n결과가 엑셀 파일로 저장되었습니다: {FILE_PATH}")
    else:
        print("분석 결과가 생성되지 않았습니다.")
