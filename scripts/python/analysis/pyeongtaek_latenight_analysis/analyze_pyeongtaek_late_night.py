import pandas as pd
import os

def main():
    # 1. 추출된 트립 데이터 로드
    trip_file_path = "/Users/galaxy/anti_codebase/results/pyeongtaek_latenight_analysis/20260101_20260519_pyeongtaek_late_night.xlsx"
    trip_df = pd.read_excel(trip_file_path)

    # 2. 할당대수 데이터 로드
    alloc_file_path = "/Users/galaxy/anti_codebase/base_data/secondary_data/pyeongtaek_allocated_vehicle_count.xlsx"
    alloc_df = pd.read_excel(alloc_file_path)
    
    # 조인을 위해 alloc_df의 month를 'YYYY-MM' 형식으로 변환
    alloc_df['month'] = pd.to_datetime(alloc_df['month']).dt.strftime('%Y-%m')
    
    # 3. 데이터 병합 (Merge)
    # 키: month <-> ride_month, region_name <-> small_region, vehicle_type <-> device_type, hh_type <-> hour_type
    merged_df = pd.merge(
        trip_df,
        alloc_df[['month', 'region_name', 'vehicle_type', 'hh_type', 'avg_total_vehicle_count']],
        left_on=['ride_month', 'small_region', 'device_type', 'hour_type'],
        right_on=['month', 'region_name', 'vehicle_type', 'hh_type'],
        how='left'
    )
    
    # 4. 소지역별 데이터 집계
    pivot_df = merged_df.pivot_table(
        index='small_region', 
        columns='hour_type', 
        values=['trip_cnt', 'device_cnt', 'net_revenue', 'avg_total_vehicle_count'], 
        aggfunc='sum',
        fill_value=0
    )
    
    # 멀티인덱스 평탄화
    pivot_df.columns = [f"{col[0]}_{col[1]}" for col in pivot_df.columns]
    
    # 필요한 컬럼이 있는지 확인하고 0으로 채우기
    required_cols = [
        'trip_cnt_심야', 'trip_cnt_주간', 
        'device_cnt_심야', 'device_cnt_주간',
        'net_revenue_심야', 'net_revenue_주간',
        'avg_total_vehicle_count_심야', 'avg_total_vehicle_count_주간'
    ]
    for col in required_cols:
        if col not in pivot_df.columns:
            pivot_df[col] = 0

    # 총합 계산
    pivot_df['total_trip_cnt'] = pivot_df['trip_cnt_심야'] + pivot_df['trip_cnt_주간']
    pivot_df['total_net_revenue'] = pivot_df['net_revenue_심야'] + pivot_df['net_revenue_주간']
    
    # 탑승률 = 탑승기기수(device_cnt) / 할당대수(avg_total_vehicle_count)
    # 0으로 나누기 방지
    pivot_df['late_night_utilization'] = pivot_df.apply(
        lambda row: (row['device_cnt_심야'] / row['avg_total_vehicle_count_심야'] * 100) if row['avg_total_vehicle_count_심야'] > 0 else 0, 
        axis=1
    )
    pivot_df['day_utilization'] = pivot_df.apply(
        lambda row: (row['device_cnt_주간'] / row['avg_total_vehicle_count_주간'] * 100) if row['avg_total_vehicle_count_주간'] > 0 else 0, 
        axis=1
    )
    
    # 대당회전수 = 트립수(trip_cnt) / 할당대수(avg_total_vehicle_count)
    pivot_df['late_night_trips_per_vehicle'] = pivot_df.apply(
        lambda row: (row['trip_cnt_심야'] / row['avg_total_vehicle_count_심야']) if row['avg_total_vehicle_count_심야'] > 0 else 0, 
        axis=1
    )
    pivot_df['day_trips_per_vehicle'] = pivot_df.apply(
        lambda row: (row['trip_cnt_주간'] / row['avg_total_vehicle_count_주간']) if row['avg_total_vehicle_count_주간'] > 0 else 0, 
        axis=1
    )
    
    # 매출 비중 계산
    pivot_df['late_night_revenue_ratio'] = (pivot_df['net_revenue_심야'] / pivot_df['total_net_revenue']) * 100
    
    pivot_df.fillna(0, inplace=True)

    # 정리된 결과
    result_df = pivot_df[[
        'device_cnt_심야', 'avg_total_vehicle_count_심야', 'late_night_utilization', 'late_night_trips_per_vehicle',
        'device_cnt_주간', 'avg_total_vehicle_count_주간', 'day_utilization', 'day_trips_per_vehicle',
        'net_revenue_심야', 'total_net_revenue', 'late_night_revenue_ratio'
    ]].copy()
                          
    result_df.columns = [
        '심야 탑승기기수', '심야 할당대수', '심야 탑승률(%)', '심야 대당회전수',
        '주간 탑승기기수', '주간 할당대수', '주간 탑승률(%)', '주간 대당회전수',
        '심야 매출', '총 매출', '심야 매출 비중(%)'
    ]
                         
    result_df = result_df.sort_values(by='심야 매출 비중(%)', ascending=False)
    
    print("=== 소지역별 심야요금제 성과 최종 분석 (평택캠프) ===")
    print(result_df)
    
    out_dir = "/Users/galaxy/anti_codebase/results/pyeongtaek_latenight_analysis"
    out_path = os.path.join(out_dir, "pyeongtaek_late_night_analysis_final_summary.xlsx")
    result_df.to_excel(out_path)
    print(f"\n최종 분석 요약 파일 저장 완료: {out_path}")

if __name__ == "__main__":
    main()
