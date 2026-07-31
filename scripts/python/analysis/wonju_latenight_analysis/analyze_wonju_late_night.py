import pandas as pd
import os
import numpy as np

def main():
    base_dir = "/Users/galaxy/anti_codebase"
    in_file = os.path.join(base_dir, "results/wonju_latenight_analysis/wonju_orders_filtered.parquet")
    alloc_file = os.path.join(base_dir, "base_data/secondary_data/wonju_allocated_vehicle_count.xlsx")
    out_file = os.path.join(base_dir, "results/wonju_latenight_analysis/wonju_latenight_analysis_final_summary.xlsx")
    
    print(f"중간 파일 읽는 중: {in_file}")
    df = pd.read_parquet(in_file)
    
    # 파생 변수 생성
    df['dt_obj'] = pd.to_datetime(df['dt'])
    df['ride_month'] = df['dt_obj'].dt.strftime('%Y-%m')
    df['ride_week'] = df['dt_obj'].dt.strftime('%Y-%W')
    df['year'] = df['dt_obj'].dt.year.astype(str)
    df['month_only'] = df['dt_obj'].dt.month.astype(str).str.zfill(2)
    
    df['hour_type'] = np.where(df['is_late_night_surcharge'] == 1, '심야', '주간')
    df['net_revenue'] = (df['calculated_pay_amount'].fillna(0) + df['calculated_out_of_area_charge'].fillna(0)) / 1.1
    
    print("기본 집계 중...")
    # 월별, 소지역별, 기기종류별, 시간대별 집계
    monthly_agg = df.groupby(['ride_month', '소지역', 'vehicle_type', 'hour_type']).agg(
        trip_cnt=('order_id', 'count'),
        device_cnt=('bicycle_sn', 'nunique'),
        net_revenue=('net_revenue', 'sum')
    ).reset_index()
    
    # 할당 대수 로드
    try:
        alloc_df = pd.read_excel(alloc_file)
        alloc_df['month'] = pd.to_datetime(alloc_df['month']).dt.strftime('%Y-%m')
    except Exception as e:
        print(f"할당대수 데이터 로드 실패: {e}")
        return
        
    # 할당 대수와 병합
    merged_df = pd.merge(
        monthly_agg,
        alloc_df[['month', 'region_name', 'vehicle_type', 'hh_type', 'avg_total_vehicle_count']],
        left_on=['ride_month', '소지역', 'vehicle_type', 'hour_type'],
        right_on=['month', 'region_name', 'vehicle_type', 'hh_type'],
        how='left'
    )
    
    # 피벗을 위해 컬럼 정리 (hour_type 기준으로 열을 나눔)
    pivot_df = merged_df.pivot_table(
        index=['ride_month', '소지역'], 
        columns='hour_type', 
        values=['trip_cnt', 'device_cnt', 'net_revenue', 'avg_total_vehicle_count'], 
        aggfunc='sum',
        fill_value=0
    )
    pivot_df.columns = [f"{col[0]}_{col[1]}" for col in pivot_df.columns]
    pivot_df.reset_index(inplace=True)
    
    # 필수 컬럼 보정
    required_cols = [
        'trip_cnt_심야', 'trip_cnt_주간', 
        'device_cnt_심야', 'device_cnt_주간',
        'net_revenue_심야', 'net_revenue_주간',
        'avg_total_vehicle_count_심야', 'avg_total_vehicle_count_주간'
    ]
    for col in required_cols:
        if col not in pivot_df.columns:
            pivot_df[col] = 0
            
    # 지표 계산
    pivot_df['총_매출'] = pivot_df['net_revenue_심야'] + pivot_df['net_revenue_주간']
    pivot_df['총_트립수'] = pivot_df['trip_cnt_심야'] + pivot_df['trip_cnt_주간']
    
    pivot_df['심야_탑승률(%)'] = pivot_df.apply(
        lambda row: (row['device_cnt_심야'] / row['avg_total_vehicle_count_심야'] * 100) if row['avg_total_vehicle_count_심야'] > 0 else 0, 
        axis=1
    )
    pivot_df['심야_매출_비중(%)'] = pivot_df.apply(
        lambda row: (row['net_revenue_심야'] / row['총_매출'] * 100) if row['총_매출'] > 0 else 0,
        axis=1
    )
    
    # 대당매출 (Revenue per Asset = Net Revenue / Allocated Vehicles)
    pivot_df['심야_대당매출'] = pivot_df.apply(
        lambda row: (row['net_revenue_심야'] / row['avg_total_vehicle_count_심야']) if row['avg_total_vehicle_count_심야'] > 0 else 0,
        axis=1
    )
    pivot_df['주간_대당매출'] = pivot_df.apply(
        lambda row: (row['net_revenue_주간'] / row['avg_total_vehicle_count_주간']) if row['avg_total_vehicle_count_주간'] > 0 else 0,
        axis=1
    )
    
    # 필요한 컬럼만 정리
    monthly_result = pivot_df[[
        'ride_month', '소지역', 
        'trip_cnt_심야', '총_트립수',
        'device_cnt_심야', 'avg_total_vehicle_count_심야', '심야_탑승률(%)',
        'net_revenue_심야', '총_매출', '심야_매출_비중(%)',
        '심야_대당매출', '주간_대당매출'
    ]].copy()
    
    # === YoY 비교 (월별 전체 기준) ===
    # 소지역+월(01~12) 기준으로 2025 vs 2026 비교
    df_yoy = df.groupby(['year', 'month_only', '소지역']).agg(
        총_매출=('net_revenue', 'sum'),
        심야_매출=('net_revenue', lambda x: x[df.loc[x.index, 'hour_type'] == '심야'].sum())
    ).reset_index()
    
    # 2025년과 2026년을 컬럼으로 피벗
    yoy_pivot = df_yoy.pivot_table(
        index=['소지역', 'month_only'],
        columns='year',
        values=['총_매출', '심야_매출'],
        fill_value=0
    )
    yoy_pivot.columns = [f"{col[1]}_{col[0]}" for col in yoy_pivot.columns]
    yoy_pivot.reset_index(inplace=True)
    
    # 성장률 계산
    if '2025_총_매출' in yoy_pivot.columns and '2026_총_매출' in yoy_pivot.columns:
        yoy_pivot['총_매출_YoY_Growth(%)'] = ((yoy_pivot['2026_총_매출'] - yoy_pivot['2025_총_매출']) / yoy_pivot['2025_총_매출'].replace(0, np.nan)) * 100
        yoy_pivot['심야_매출_YoY_Growth(%)'] = ((yoy_pivot['2026_심야_매출'] - yoy_pivot['2025_심야_매출']) / yoy_pivot['2025_심야_매출'].replace(0, np.nan)) * 100
        yoy_pivot.fillna(0, inplace=True)
    
    # === 주간 트렌드 (원주캠프 통합) ===
    weekly_agg = df.groupby(['ride_week', 'hour_type']).agg(
        net_revenue=('net_revenue', 'sum')
    ).reset_index()
    
    weekly_pivot = weekly_agg.pivot(index='ride_week', columns='hour_type', values='net_revenue').fillna(0)
    for col in ['심야', '주간']:
        if col not in weekly_pivot.columns:
            weekly_pivot[col] = 0
            
    weekly_pivot['총_매출'] = weekly_pivot['심야'] + weekly_pivot['주간']
    weekly_pivot['심야_매출_비중(%)'] = (weekly_pivot['심야'] / weekly_pivot['총_매출']) * 100
    weekly_pivot.fillna(0, inplace=True)
    weekly_result = weekly_pivot.reset_index()
    
    # 엑셀 시트 분리 저장
    print(f"최종 결과 엑셀 작성 중: {out_file}")
    with pd.ExcelWriter(out_file) as writer:
        monthly_result.to_excel(writer, sheet_name="월간_요약", index=False)
        yoy_pivot.to_excel(writer, sheet_name="YoY_비교", index=False)
        weekly_result.to_excel(writer, sheet_name="주간_트렌드", index=False)
        
    print("분석 작업 완료!")

if __name__ == '__main__':
    main()
