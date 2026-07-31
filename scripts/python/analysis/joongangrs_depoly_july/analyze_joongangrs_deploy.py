import os
import sys
import pandas as pd
from datetime import datetime

# utils 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'utils')))
from read_rich_deploy_zone_usages import load_rich_deploy_zone_usages

def main():
    start_date = "2026-04-01"
    end_date = "2026-07-31"
    
    print(f"[{datetime.now()}] 1. 데이터 로드 중 ({start_date} ~ {end_date})...")
    df = load_rich_deploy_zone_usages(start_date, end_date)
    
    if df.empty:
        print("해당 기간의 데이터가 없습니다.")
        return
        
    print(f"[{datetime.now()}] 2. 데이터 필터링 및 집계 준비...")
    # '중앙RS팀' 필터
    df = df[df['대지역'] == '중앙RS팀'].copy()
    
    # date 컬럼을 날짜 타입으로 변환 후 월 추출
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.month
    
    # 숫자형 컬럼으로 확실히 변환
    df['배치수'] = pd.to_numeric(df['배치수'], errors='coerce').fillna(0)
    df['출루수'] = pd.to_numeric(df['출루수'], errors='coerce').fillna(0)
    
    dims = ['대지역', '중지역', '배치존명']
    
    print(f"[{datetime.now()}] 3. 월별 총 배치수, 출루수 및 출루율 계산 중...")
    # 월별 출루율 및 총량 계산
    month_agg = df.groupby(dims + ['month']).agg(
        m_배치수=('배치수', 'sum'),
        m_출루수=('출루수', 'sum')
    ).reset_index()
    
    month_agg['obp'] = month_agg['m_출루수'] / month_agg['m_배치수']
    month_agg['obp'] = month_agg['obp'].fillna(0)
    
    print(f"[{datetime.now()}] 4. 전체 기간 평균(월별 평균) 출루 수, 배치 수, 전체 출루율 계산 중...")
    # 4~7월 전체 집계 (월별 합계의 평균)
    overall = month_agg.groupby(dims).agg(
        avg_배치수=('m_배치수', 'mean'),
        avg_출루수=('m_출루수', 'mean'),
        sum_배치수=('m_배치수', 'sum'),
        sum_출루수=('m_출루수', 'sum')
    ).reset_index()
    
    # 전체 평균 출루율 = 총 출루수 / 총 배치수
    overall['평균 출루율'] = overall['sum_출루수'] / overall['sum_배치수']
    overall['평균 출루율'] = overall['평균 출루율'].fillna(0)
    
    # 피벗해서 월별 컬럼으로 분리
    obp_pivot = month_agg.pivot(index=dims, columns='month', values='obp').reset_index()
    
    # 컬럼 이름 변경
    rename_dict = {
        4: '4월 평균 출루율',
        5: '5월 평균 출루율',
        6: '6월 평균 출루율',
        7: '7월 평균 출루율'
    }
    obp_pivot = obp_pivot.rename(columns=rename_dict)
    
    # 병합
    result = pd.merge(overall, obp_pivot, on=dims, how='left')
    
    # 혹시 없는 달이 있으면 0으로 채움
    for col in rename_dict.values():
        if col not in result.columns:
            result[col] = 0.0
            
    print(f"[{datetime.now()}] 5. 엑셀 저장용 포맷 적용 중...")
    # 필요한 컬럼만 추출 및 이름 변경
    final_cols = dims + [
        'avg_출루수', 'avg_배치수', 'sum_출루수', 'sum_배치수', '평균 출루율',
        '4월 평균 출루율', '5월 평균 출루율', '6월 평균 출루율', '7월 평균 출루율'
    ]
    result = result[final_cols]
    result = result.rename(columns={
        'avg_출루수': '4~7월 평균 출루 수',
        'avg_배치수': '4~7월 평균 배치 수',
        'sum_출루수': '4~7월 총 출루 수',
        'sum_배치수': '4~7월 총 배치 수'
    })
    
    # 포맷 씌우기 (Rule 14: #,##0 for quantities, %.1f%% for ratios)
    result['4~7월 평균 출루 수'] = result['4~7월 평균 출루 수'].apply(lambda x: f"{x:,.0f}")
    result['4~7월 평균 배치 수'] = result['4~7월 평균 배치 수'].apply(lambda x: f"{x:,.0f}")
    result['4~7월 총 출루 수'] = result['4~7월 총 출루 수'].apply(lambda x: f"{x:,.0f}")
    result['4~7월 총 배치 수'] = result['4~7월 총 배치 수'].apply(lambda x: f"{x:,.0f}")
    result['평균 출루율'] = result['평균 출루율'].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "0.0%")
    
    for c in rename_dict.values():
        result[c] = result[c].apply(lambda x: f"{x*100:.1f}%" if pd.notnull(x) else "0.0%")
        
    out_dir = "/Users/galaxy.jang/anti_codebase/results/joongangrs_depoly_july"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "joongangrs_deploy_analysis.xlsx")
    
    result.to_excel(out_path, index=False)
    print(f"[{datetime.now()}] 작업 완료! 결과물이 다음 경로에 저장되었습니다: {out_path}")

if __name__ == '__main__':
    main()
