import os
import sys
import pandas as pd
import polars as pl

# 유틸리티 경로 추가
sys.path.append("/Users/galaxy.jang/anti_codebase/scripts/python/utils")
from read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic

def main():
    # 1. 결과 폴더 생성
    results_dir = "/Users/galaxy.jang/anti_codebase/results/daegu1_may_new_users"
    os.makedirs(results_dir, exist_ok=True)
    
    # 2. 엑셀 데이터 로드
    excel_path = "/Users/galaxy.jang/anti_codebase/base_data/primary_data/daegu1camp_registers.xlsx"
    print(f"Reading {excel_path}...")
    df_users_pd = pd.read_excel(excel_path)
    df_users = pl.from_pandas(df_users_pd)
    
    # 가입자 수 분포 확인
    df_user_dist = (
        df_users.group_by(['가입_소지역', 'age_group', 'gender'])
        .agg(pl.count().alias('가입자수'))
        .sort('가입_소지역')
    )
    
    # 3. 5월 트립 데이터 로드
    print("Loading rich_orders for May 2026...")
    columns = [
        'dt', 'user_id', 'vehicle_type', 'duration_minutes', 'distance', 
        'order_amount', 'pay_amount', 'out_of_area_charge', 'from_api'
    ]
    df_trips = load_rich_orders_polars('2026-05-01', '2026-05-31', columns=columns)
    
    if df_trips.height == 0:
        print("No trip data found.")
        return
    
    # 4. 필터링 및 조인: 신규 가입자(df_users)의 트립만 남기기
    unique_users = df_users.select('user_id').unique()
    df_trips = df_trips.join(unique_users, on='user_id', how='inner')
    
    # 5. 채널별 수수료 적용 및 총 매출 계산
    print("Applying channel fee logic...")
    df_trips = apply_channel_fee_logic(df_trips)
    df_trips = df_trips.with_columns(
        (pl.col('calculated_pay_amount') + pl.col('calculated_out_of_area_charge')).alias('total_revenue')
    )
    
    # 6. User_id 기준 집계
    print("Aggregating by user_id...")
    user_agg = (
        df_trips.group_by('user_id')
        .agg(
            pl.count().alias('총_트립수'),
            pl.col('total_revenue').sum().alias('총_매출'),
            pl.col('duration_minutes').mean().alias('평균_운행시간_분'),
            pl.col('distance').mean().alias('평균_운행거리_m')
        )
    )
    
    # User_id + Vehicle_type 기준 집계
    print("Aggregating by user_id and vehicle_type...")
    user_vehicle_agg = (
        df_trips.group_by(['user_id', 'vehicle_type'])
        .agg(
            pl.count().alias('총_트립수'),
            pl.col('total_revenue').sum().alias('총_매출'),
            pl.col('duration_minutes').mean().alias('평균_운행시간_분'),
            pl.col('distance').mean().alias('평균_운행거리_m')
        )
        .sort(['user_id', 'vehicle_type'])
    )
    
    # 7. 유저 데모 정보와 트립 데이터 조인
    print("Joining aggregations with user demographics...")
    df_user_trip_summary = df_users.join(user_agg, on='user_id', how='left')
    df_user_trip_summary = df_user_trip_summary.with_columns([
        pl.col('총_트립수').fill_null(0),
        pl.col('총_매출').fill_null(0),
        pl.col('평균_운행시간_분').fill_null(0.0),
        pl.col('평균_운행거리_m').fill_null(0.0)
    ])
    
    # 소지역/연령대/성별 기준 뷰
    df_region_summary = (
        df_user_trip_summary.group_by(['가입_소지역', 'age_group', 'gender'])
        .agg(
            pl.count().alias('가입자수'),
            pl.col('총_트립수').sum().alias('전체_트립수'),
            pl.col('총_매출').sum().alias('전체_매출'),
            (pl.col('총_트립수') > 0).sum().alias('실제_이용자수') # 1회 이상 이용한 유저 수
        )
        .with_columns(
            (pl.col('전체_트립수') / pl.col('가입자수')).alias('인당_평균_트립수'),
            (pl.col('전체_매출') / pl.col('가입자수')).alias('인당_평균_매출'),
            (pl.col('실제_이용자수') / pl.col('가입자수') * 100).alias('전환율(%)')
        )
        .sort(by=['전체_매출', '가입자수'], descending=[True, True])
    )
    
    # 소지역(Small Area) 오버뷰
    df_small_area_overview = (
        df_user_trip_summary.group_by('가입_소지역')
        .agg(
            pl.count().alias('가입자수'),
            pl.col('총_트립수').sum().alias('전체_트립수'),
            pl.col('총_매출').sum().alias('전체_매출'),
            (pl.col('총_트립수') > 0).sum().alias('실제_이용자수')
        )
        .with_columns(
            (pl.col('전체_트립수') / pl.col('가입자수')).alias('인당_평균_트립수'),
            (pl.col('전체_매출') / pl.col('가입자수')).alias('인당_평균_매출'),
            (pl.col('실제_이용자수') / pl.col('가입자수') * 100).alias('전환율(%)')
        )
        .sort(by='전체_매출', descending=True)
    )
    
    # 7-2. 연령대/성별 기준 요약 (분포 및 주문 전환율)
    df_age_gender_summary = (
        df_user_trip_summary.group_by(['age_group', 'gender'])
        .agg(
            pl.len().alias('가입자수'),
            pl.col('총_트립수').sum().alias('전체_트립수'),
            pl.col('총_매출').sum().alias('전체_매출'),
            (pl.col('총_트립수') > 0).sum().alias('실제_이용자수')
        )
        .with_columns(
            (pl.col('전체_트립수') / pl.col('가입자수')).alias('인당_평균_트립수'),
            (pl.col('전체_매출') / pl.col('가입자수')).alias('인당_평균_매출'),
            (pl.col('실제_이용자수') / pl.col('가입자수') * 100).alias('전환율(%)')
        )
        .sort(by=['age_group', 'gender'])
    )
    
    # 7-3. 연령대/성별 및 기기 종류별 트립 (기기 종류별 선호도)
    # 기존 user_vehicle_agg 를 활용하여 데모정보와 조인
    df_vehicle_demo = user_vehicle_agg.join(df_users.select(['user_id', 'age_group', 'gender']), on='user_id', how='inner')
    
    df_vehicle_preference = (
        df_vehicle_demo.group_by(['age_group', 'gender', 'vehicle_type'])
        .agg(
            pl.col('총_트립수').sum().alias('전체_트립수'),
            pl.col('총_매출').sum().alias('전체_매출')
        )
        .sort(by=['age_group', 'gender', '전체_트립수'], descending=[False, False, True])
    )

    # 전체 기기 종류별 선호도
    df_vehicle_overall = (
        df_trips.group_by('vehicle_type')
        .agg(
            pl.len().alias('전체_트립수'),
            pl.col('total_revenue').sum().alias('전체_매출')
        )
        .sort(by='전체_트립수', descending=True)
    )
    
    # 8. 결과 엑셀 저장
    output_excel_path = os.path.join(results_dir, "daegu1_new_users_analysis.xlsx")
    print(f"Saving results to {output_excel_path}...")
    
    with pd.ExcelWriter(output_excel_path) as writer:
        df_small_area_overview.to_pandas().to_excel(writer, sheet_name='소지역별_요약', index=False)
        df_region_summary.to_pandas().to_excel(writer, sheet_name='소지역_연령_성별_요약', index=False)
        df_age_gender_summary.to_pandas().to_excel(writer, sheet_name='연령_성별_요약', index=False)
        df_vehicle_preference.to_pandas().to_excel(writer, sheet_name='연령_성별_기기선호도', index=False)
        df_vehicle_overall.to_pandas().to_excel(writer, sheet_name='전체_기기선호도', index=False)
        df_user_dist.to_pandas().to_excel(writer, sheet_name='가입자수_분포', index=False)
        user_vehicle_agg.to_pandas().to_excel(writer, sheet_name='유저_기기유형별_트립', index=False)
        df_user_trip_summary.to_pandas().to_excel(writer, sheet_name='유저별_트립_매출', index=False)
        
    print("Analysis complete.")

if __name__ == "__main__":
    main()
