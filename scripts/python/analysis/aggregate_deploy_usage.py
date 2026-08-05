import os
import sys
import pandas as pd

# 유틸리티 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))
from read_rich_deploy_zone_usages import load_rich_deploy_zone_usages

def main():
    start_date = '2025-09-19'
    end_date = '2026-07-21'
    
    print(f"{start_date} ~ {end_date} 데이터 로딩 시작...")
    df = load_rich_deploy_zone_usages(start_date, end_date)
    
    if df.empty:
        print("데이터가 없습니다.")
        return
        
    print(f"데이터 로딩 완료. 총 행수: {len(df):,}건")
    
    # date 컬럼을 바탕으로 YYYY-MM 형태의 월 컬럼 생성
    print("월별 집계 변환 중...")
    df['year_month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
    
    # 집계 기준 컬럼 (date 대신 year_month 사용, 기존 속성 모두 유지)
    group_cols = ['year_month', '배치 구분', '기종', '대지역', '중지역', '소지역', '배치존명', '위도', '경도']
    
    # 합산 집계
    agg_df = df.groupby(group_cols, as_index=False).agg({
        '배치수': 'sum',
        '출루수': 'sum'
    })
    
    print(f"집계 완료. 집계 후 행수: {len(agg_df):,}건")
    
    # 저장 경로 설정
    save_dir = f"{os.path.expanduser('~')}/anti_codebase/results/deploy_usage_all"
    os.makedirs(save_dir, exist_ok=True)
    
    save_path = os.path.join(save_dir, "deploy_usage_monthly.xlsx")
    
    print(f"엑셀 파일 저장 중... ({save_path})")
    # 엑셀 저장
    try:
        agg_df.to_excel(save_path, index=False)
        print("저장 성공!")
    except Exception as e:
        print(f"엑셀 저장 중 오류 발생: {e}")

if __name__ == '__main__':
    main()
