import os
import sys
import pandas as pd
import time

# 공용 유틸리티 경로 추가
sys.path.append("/Users/galaxy/anti_codebase/scripts/python/utils")
from read_rich_orders_pandas import load_rich_orders, apply_channel_fee_logic

def main():
    script_dir = "/Users/galaxy/anti_codebase/scripts/python/wonju_latenight_analysis"
    result_dir = "/Users/galaxy/anti_codebase/results/wonju_latenight_analysis"
    os.makedirs(script_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)

    out_file = os.path.join(result_dir, "wonju_orders_filtered.parquet")
    
    # 1. 지역 계층 정보 로드
    region_file = "/Users/galaxy/Google Drive/공유 드라이브/gbike.rich_region/rich_region_hierarchy.parquet"
    print(f"지역 계층 정보 로드 중: {region_file}")
    try:
        region_df = pd.read_parquet(region_file)
    except Exception as e:
        print(f"지역 계층 정보 로드 실패: {e}")
        return

    # 원주캠프 소지역 ID 추출
    wonju_regions = region_df[region_df['중지역'] == '원주캠프']
    wonju_region_ids = wonju_regions['region_id'].tolist()
    print(f"원주캠프 소속 소지역 수: {len(wonju_region_ids)}개")
    
    if not wonju_region_ids:
        print("원주캠프에 해당하는 소지역이 없습니다. 스크립트를 종료합니다.")
        return

    # 2. 로드할 기간 설정 (25년, 26년 동기간)
    periods = [
        ('2025-01-01', '2025-05-19'),
        ('2026-01-01', '2026-05-19')
    ]
    
    selected_cols = [
        'dt', 'is_late_night_surcharge', 'low_region_id', 'vehicle_type', 
        'bicycle_sn', 'order_amount', 'pay_amount', 'out_of_area_charge', 
        'from_api', 'order_id'
    ]
    
    all_filtered_dfs = []
    
    for start_date, end_date in periods:
        print(f"[{start_date} ~ {end_date}] 데이터 로드 시작...")
        start_time = time.time()
        
        # rich_orders 로드
        df = load_rich_orders(start_date, end_date, columns=selected_cols)
        
        if df.empty:
            print(f"[{start_date} ~ {end_date}] 데이터가 없습니다.")
            continue
            
        print(f"[{start_date} ~ {end_date}] 총 로드 건수: {len(df):,}건, 필터링 진행 중...")
        
        # 원주캠프 소지역 필터링
        filtered_df = df[df['low_region_id'].isin(wonju_region_ids)].copy()
        
        if filtered_df.empty:
            print(f"[{start_date} ~ {end_date}] 원주캠프에 해당하는 주문 건이 없습니다.")
            continue
            
        # 채널별 수수료 로직 적용 (calculated_pay_amount, calculated_out_of_area_charge 생성)
        filtered_df = apply_channel_fee_logic(filtered_df)
        
        # 지역 정보 조인 (소지역명 가져오기 위함)
        filtered_df = pd.merge(
            filtered_df,
            wonju_regions[['region_id', '소지역', '중지역']],
            left_on='low_region_id',
            right_on='region_id',
            how='left'
        )
        
        all_filtered_dfs.append(filtered_df)
        elapsed_time = time.time() - start_time
        print(f"[{start_date} ~ {end_date}] 원주캠프 추출 건수: {len(filtered_df):,}건 (소요시간: {elapsed_time:.2f}초)")
        
    if not all_filtered_dfs:
        print("추출된 원주캠프 데이터가 없습니다.")
        return
        
    # 최종 병합 및 저장
    final_df = pd.concat(all_filtered_dfs, ignore_index=True)
    
    print(f"최종 병합 완료. 총 추출 건수: {len(final_df):,}건")
    final_df.to_parquet(out_file, index=False)
    print(f"중간 파일 저장 완료: {out_file}")

if __name__ == '__main__':
    main()
