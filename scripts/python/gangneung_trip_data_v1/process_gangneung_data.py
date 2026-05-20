import pandas as pd
import os

def main():
    # 1. 파일 경로 설정
    extracted_file = '/Users/galaxy/anti_codebase/base_data/primary_data/gangneung_trip_data_v1/gangneung_trip_data_v1_total.xlsx'
    stats_file = '/Users/galaxy/anti_codebase/base_data/primary_data/gangneung_trip_data_v1/redshift_rich_daily_statistics.xlsx'
    output_file = '/Users/galaxy/anti_codebase/base_data/secondary_data/gangneung_trip_data_v1/gangneung_trip_data_v1_processed.xlsx'
    
    # 디렉토리 생성
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print("Loading data files...")
    df_ext = pd.read_excel(extracted_file)
    df_stats = pd.read_excel(stats_file)
    
    # 2. 전처리
    # 날짜 형식 통일
    df_ext['dt'] = pd.to_datetime(df_ext['dt'])
    df_stats['date'] = pd.to_datetime(df_stats['date'])
    
    # 컬럼명 매핑용 임시 컬럼 생성 또는 이름 변경
    # df_ext: dt, 소지역, one_category
    # df_stats: date, low_region_name, vehicle_type
    
    # 3. 그룹별 총 트립 수 계산 (일자, 소지역, 기종별)
    print("Calculating trip ratios...")
    group_cols = ['dt', '소지역', 'one_category']
    df_group_total = df_ext.groupby(group_cols)['트립수'].sum().reset_index()
    df_group_total.rename(columns={'트립수': 'group_total_trips'}, inplace=True)
    
    # 원본 데이터에 총 트립 수 결합
    df_ext = pd.merge(df_ext, df_group_total, on=group_cols, how='left')
    
    # 비율 계산 (트립수 비율)
    df_ext['trip_ratio'] = df_ext['트립수'] / df_ext['group_total_trips']
    # 0으로 나누기 방지
    df_ext['trip_ratio'] = df_ext['trip_ratio'].fillna(0)
    
    # 4. 통계 데이터와 결합
    print("Joining with statistics data...")
    # stats 데이터에서 필요한 컬럼만 선택
    stats_cols = ['date', 'low_region_name', 'vehicle_type', 'assigned_count', 'revenue']
    df_stats_subset = df_stats[stats_cols].copy()
    
    # Join을 위해 컬럼명 일치
    df_stats_subset.rename(columns={
        'date': 'dt',
        'low_region_name': '소지역',
        'vehicle_type': 'one_category'
    }, inplace=True)
    
    # Left Join
    df_final = pd.merge(df_ext, df_stats_subset, on=['dt', '소지역', 'one_category'], how='left')
    
    # 5. 비율에 따라 배분
    print("Allocating assigned_count and revenue...")
    # 결측치 처리 (Join 실패 시 0)
    df_final['assigned_count'] = df_final['assigned_count'].fillna(0)
    df_final['revenue'] = df_final['revenue'].fillna(0)
    
    # 비율 곱하기
    df_final['allocated_assigned_count'] = df_final['assigned_count'] * df_final['trip_ratio']
    df_final['allocated_revenue'] = df_final['revenue'] * df_final['trip_ratio']
    
    # 6. 결과 저장
    print(f"Saving processed data to {output_file}...")
    df_final.to_excel(output_file, index=False, engine='openpyxl')
    
    print("Data processing complete!")
    print(f"Total rows: {len(df_final)}")
    
    # 검증: 배분된 값의 합이 원본 통계 값과 일치하는지 샘플 체크
    orig_rev = df_stats[df_stats['middle_region_name'] == '강릉캠프']['revenue'].sum()
    final_rev = df_final['allocated_revenue'].sum()
    print(f"Validation - Original Revenue (Total Stats): {orig_rev:,.0f}")
    print(f"Validation - Final Allocated Revenue: {final_rev:,.0f}")

if __name__ == '__main__':
    main()
