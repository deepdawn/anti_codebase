import os
import sys
import time
import requests
import numpy as np
import pandas as pd
import polars as pl
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.ensemble import RandomForestRegressor

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

sys.path.append('/Users/galaxy/anti_codebase/scripts/python/utils')
from read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic

def fetch_weather_data(lat, lon, start_date, end_date):
    """
    Open-Meteo API를 통해 위/경도 기반 날씨 데이터를 수집
    """
    if lat > 90:
        lat, lon = lon, lat
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_mean,precipitation_sum&timezone=Asia%2FSeoul"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            df = pd.DataFrame(data['daily'])
            df.rename(columns={'time': 'date', 'temperature_2m_mean': 'temp_mean', 'precipitation_sum': 'precip_sum'}, inplace=True)
            
            # 결측 일자 방지 보간
            full_dates = pd.date_range(start_date, end_date).strftime('%Y-%m-%d')
            df_full = pd.DataFrame({'date': full_dates})
            df_full = df_full.merge(df, on='date', how='left')
            df_full['temp_mean'] = df_full['temp_mean'].fillna(df_full['temp_mean'].mean()).fillna(15.0)
            df_full['precip_sum'] = df_full['precip_sum'].fillna(0.0)
            return pl.from_pandas(df_full)
    except Exception as e:
        print(f"  - Weather API Error: {e}")
        
    full_dates = pd.date_range(start_date, end_date).strftime('%Y-%m-%d')
    return pl.DataFrame({'date': full_dates, 'temp_mean': 15.0, 'precip_sum': 0.0})

def main():
    base_drive = "/Users/galaxy/Google Drive/공유 드라이브"
    orders_path = f"{base_drive}/gbike.rich_orders"
    region_path = f"{base_drive}/gbike.rich_region/rich_region_hierarchy.parquet"
    
    results_dir = "/Users/galaxy/anti_codebase/results/regression_large_area"
    os.makedirs(results_dir, exist_ok=True)
    
    start_date, end_date = "2024-01-01", "2026-05-31"
    
    print("1. 파켓 데이터 로드 및 지역(대지역) 필터링...")
    # 'RS팀'이 포함된 직영 대지역만 추출
    region_df = pl.scan_parquet(region_path).filter(
        pl.col('대지역').str.contains('RS팀')
    ).select(['region_id', '대지역']).collect()
    
    rs_region_ids = region_df['region_id'].to_list()
    
    orders_cols = ['dt', 'order_id', 'low_region_id', 'distance', 'duration_minutes', 'start_lat', 'start_lng', 'pay_amount', 'out_of_area_charge', 'order_amount', 'from_api']
    print(f" - Orders 파켓 스캔 중... (기간: {start_date} ~ {end_date})")
    orders_df = load_rich_orders_polars(start_date, end_date, columns=orders_cols, base_path=orders_path)
    print(f" - 스캔된 총 데이터 건수: {orders_df.height:,}")
    
    # 조인
    df = orders_df.join(region_df, left_on='low_region_id', right_on='region_id', how='inner')
    
    # 채널 수수료 로직 적용하여 실 수령액(매출) 컬럼 생성
    df = apply_channel_fee_logic(df)
    
    print(f" - 직영 대지역(RS팀) 매핑 완료 건수: {df.height:,}")
    
    print("2. 대지역별 대표 좌표(Median Lat/Lng) 도출...")
    coord_df = df.group_by('대지역').agg([
        pl.col('start_lat').drop_nulls().median().alias('med_lat'),
        pl.col('start_lng').drop_nulls().median().alias('med_lon'),
        pl.len().alias('order_cnt')
    ]).sort('order_cnt', descending=True)
    
    # 트래픽 기준 상위 5개~7개 대지역 선정 (가용 데이터 건수에 따름)
    top_n = min(7, coord_df.height)
    coord_pdf = coord_df.head(top_n).to_pandas()
    target_large_areas = coord_pdf['대지역'].tolist()
    
    print(f" - 분석 대상 대지역(Top {top_n}): {target_large_areas}")
    print(coord_pdf)
    
    print("\n3. 대지역별 맞춤 날씨 API 수집 및 변수 집계...")
    # 대상 대지역으로 필터
    df = df.filter(pl.col('대지역').is_in(target_large_areas))
    df = df.with_columns(pl.col('dt').dt.strftime('%Y-%m-%d').alias('date'))
    
    daily_df = df.group_by(['대지역', 'date']).agg([
        pl.len().alias('order_count'),
        pl.col('distance').mean().alias('avg_distance'),
        pl.col('duration_minutes').mean().alias('avg_duration'),
        pl.col('calculated_pay_amount').mean().alias('avg_pay'),
        pl.col('calculated_out_of_area_charge').mean().alias('avg_out_charge'),
        (pl.col('calculated_pay_amount').fill_null(0).sum() + pl.col('calculated_out_of_area_charge').fill_null(0).sum()).alias('daily_revenue')
    ])
    
    final_dfs = []
    # 각 지역별 중심 좌표로 날씨 호출
    for _, row in coord_pdf.iterrows():
        l_area = row['대지역']
        lat, lon = row['med_lat'], row['med_lon']
        
        if pd.isna(lat) or pd.isna(lon):
            print(f"  - [{l_area}] 좌표 누락으로 날씨 수집 불가. 스킵합니다.")
            continue
            
        print(f"  - [{l_area}] 날씨 API 쿼리 (Lat: {lat:.4f}, Lon: {lon:.4f})")
        w_df = fetch_weather_data(lat, lon, start_date, end_date)
        
        area_daily = daily_df.filter(pl.col('대지역') == l_area)
        area_daily = area_daily.join(w_df, on='date', how='left')
        
        # 시간 파생변수
        area_daily = area_daily.with_columns([
            pl.col('date').str.strptime(pl.Date, "%Y-%m-%d").dt.weekday().alias('day_of_week')
        ])
        area_daily = area_daily.with_columns((pl.col('day_of_week') >= 6).cast(pl.Int32).alias('is_weekend'))
        
        final_dfs.append(area_daily)
        time.sleep(1) # API 보호용 딜레이
        
    master_df = pl.concat(final_dfs)
    pdf = master_df.to_pandas()
    
    print("\n4. Random Forest 지역별 개별 모델 학습 및 특징 기여도(Feature Importance) 추출...")
    features = ['avg_distance', 'avg_duration', 'avg_pay', 'avg_out_charge', 'temp_mean', 'precip_sum', 'is_weekend']
    importances = []
    
    for l_area in target_large_areas:
        group_data = pdf[pdf['대지역'] == l_area].copy().dropna(subset=features + ['daily_revenue'])
        if len(group_data) < 50:
            continue
            
        X = group_data[features]
        y = group_data['daily_revenue']
        
        rf = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=5)
        rf.fit(X, y)
        
        imp_dict = dict(zip(features, rf.feature_importances_))
        imp_dict['대지역'] = l_area
        imp_dict['R_squared'] = rf.score(X, y)
        importances.append(imp_dict)
        
    imp_df = pd.DataFrame(importances)
    for f in features:
        imp_df[f] = imp_df[f] * 100 # 퍼센티지로 변환
        
    print("\n5. 엑셀 결과 저장 및 Heatmap 시각화...")
    excel_path = os.path.join(results_dir, "large_area_regression_results.xlsx")
    with pd.ExcelWriter(excel_path) as writer:
        imp_df.to_excel(writer, sheet_name='Feature_Importance', index=False)
        coord_pdf.to_excel(writer, sheet_name='Coordinates', index=False)
        pdf.to_excel(writer, sheet_name='Daily_Dataset', index=False)
        
    # Heatmap
    plt.figure(figsize=(10, 6))
    heatmap_data = imp_df.set_index('대지역')[features]
    
    # 시각화 용이성을 위한 한글명 매핑
    feature_korean = {
        'avg_distance': '주행 거리',
        'avg_duration': '주행 시간',
        'avg_pay': '결제 금액',
        'avg_out_charge': '외곽 반납 비용',
        'temp_mean': '기온(날씨)',
        'precip_sum': '강수량(날씨)',
        'is_weekend': '주말 여부'
    }
    heatmap_data.rename(columns=feature_korean, inplace=True)
    
    sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="YlGnBu", linewidths=.5)
    plt.title('대지역(RS팀)별 일 매출 결정 요인 비중 (Feature Importance, %)', fontsize=15)
    plt.ylabel('대지역', fontsize=12)
    plt.xlabel('영향 요인', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "feature_importance_heatmap.png"), dpi=150)
    plt.close()
    
    print(f" - 처리 완료! 모든 분석 결과와 시각화가 저장되었습니다: {results_dir}")

if __name__ == "__main__":
    main()
