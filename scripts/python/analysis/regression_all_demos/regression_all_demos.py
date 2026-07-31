import os
import sys
import requests
import numpy as np
import pandas as pd
import polars as pl
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

import statsmodels.api as sm
from sklearn.ensemble import RandomForestRegressor

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

sys.path.append('/Users/galaxy.jang/anti_codebase/scripts/python/utils')
from read_rich_orders_polars import load_rich_orders_polars

def fetch_weather_data(start_date, end_date):
    lat, lon = "37.65695122231786", "126.83317101598665"
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_mean,precipitation_sum&timezone=Asia%2FSeoul"
    
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            df = pd.DataFrame(data['daily'])
            df.rename(columns={'time': 'date', 'temperature_2m_mean': 'temp_mean', 'precipitation_sum': 'precip_sum'}, inplace=True)
            
            full_dates = pd.date_range(start_date, end_date).strftime('%Y-%m-%d')
            df_full = pd.DataFrame({'date': full_dates})
            df_full = df_full.merge(df, on='date', how='left')
            df_full['temp_mean'] = df_full['temp_mean'].fillna(df_full['temp_mean'].mean()).fillna(15.0)
            df_full['precip_sum'] = df_full['precip_sum'].fillna(0.0)
            return pl.from_pandas(df_full)
    except Exception as e:
        print(f"Weather API Error: {e}")
        
    full_dates = pd.date_range(start_date, end_date).strftime('%Y-%m-%d')
    return pl.DataFrame({'date': full_dates, 'temp_mean': 15.0, 'precip_sum': 0.0})

def main():
    base_drive = "/Users/galaxy.jang/Google Drive/공유 드라이브"
    orders_path = f"{base_drive}/gbike.rich_orders"
    region_path = f"{base_drive}/gbike.rich_region/rich_region_hierarchy.parquet"
    user_path = f"{base_drive}/gbike.rich_user/rich_user_all.parquet"
    
    results_dir = "/Users/galaxy.jang/anti_codebase/results/regression_all_demos"
    os.makedirs(results_dir, exist_ok=True)
    
    start_date, end_date = "2025-01-01", "2026-05-31"
    
    print("1. 파켓 데이터 로드 및 조인 (모든 데모그룹)...")
    region_df = pl.scan_parquet(region_path).filter(pl.col('중지역') == '고양2캠프').select(['region_id']).collect()
    
    user_cols = ['user_id', 'gender', 'age_group']
    user_df = pl.scan_parquet(user_path).select(user_cols).collect()
    
    orders_cols = ['dt', 'order_id', 'user_id', 'low_region_id', 'distance', 'duration_minutes', 'pay_amount', 'is_late_night_surcharge']
    orders_df = load_rich_orders_polars(start_date, end_date, columns=orders_cols, base_path=orders_path)
    
    df = orders_df.join(region_df, left_on='low_region_id', right_on='region_id', how='inner')
    df = df.join(user_df, on='user_id', how='left')
    
    df = df.with_columns([
        pl.col('gender').fill_null('Unknown'),
        pl.col('age_group').fill_null('Unknown')
    ])
    df = df.with_columns([
        (pl.col('age_group') + "_" + pl.col('gender')).alias('demo_group'),
        pl.col('dt').dt.strftime('%Y-%m-%d').alias('date')
    ])
    
    print("2. 일별/데모그룹별 파생변수 집계...")
    daily_df = df.group_by(['date', 'demo_group']).agg([
        pl.len().alias('order_count'),
        pl.col('distance').mean().alias('avg_distance'),
        pl.col('duration_minutes').mean().alias('avg_duration'),
        pl.col('pay_amount').mean().alias('avg_pay_amount'),
        (pl.col('is_late_night_surcharge').sum() / pl.len()).alias('late_night_ratio')
    ])
    
    weather_df = fetch_weather_data(start_date, end_date)
    daily_df = daily_df.join(weather_df, on='date', how='left')
    
    daily_df = daily_df.with_columns([
        pl.col('date').str.strptime(pl.Date, "%Y-%m-%d").dt.weekday().alias('day_of_week'),
        pl.col('date').str.strptime(pl.Date, "%Y-%m-%d").dt.month().alias('month')
    ])
    daily_df = daily_df.with_columns((pl.col('day_of_week') >= 6).cast(pl.Int32).alias('is_weekend'))
    
    pdf = daily_df.to_pandas()
    # Fill weather missing backward/forward per demo_group
    pdf = pdf.sort_values(by=['demo_group', 'date'])
    pdf['temp_mean'] = pdf.groupby('demo_group')['temp_mean'].ffill().bfill()
    pdf['precip_sum'] = pdf.groupby('demo_group')['precip_sum'].ffill().bfill()
    
    print("3. 주요 데모그룹별 회귀 및 변수 중요도 추출...")
    top_demos = pdf.groupby('demo_group')['order_count'].sum().sort_values(ascending=False).head(10).index.tolist()
    
    features = ['avg_distance', 'avg_duration', 'avg_pay_amount', 'late_night_ratio', 
                'temp_mean', 'precip_sum', 'is_weekend'] # time_trend excluded for simple cross-sectional comparison
    
    results = []
    
    for demo in top_demos:
        group_data = pdf[pdf['demo_group'] == demo].copy()
        group_data = group_data.sort_values('date').reset_index(drop=True)
        group_data['time_trend'] = np.arange(len(group_data))
        
        # Drop rows with NaN in features
        model_features = features + ['time_trend']
        group_data = group_data.dropna(subset=model_features + ['order_count'])
        
        if len(group_data) < 100: continue
            
        X = group_data[model_features]
        y = group_data['order_count']
        
        # OLS to get direction of pay_amount
        X_sm = sm.add_constant(X)
        ols_model = sm.OLS(y, X_sm).fit()
        pay_coef = ols_model.params.get('avg_pay_amount', 0)
        pay_pval = ols_model.pvalues.get('avg_pay_amount', 1)
        
        # RF for Importance
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=5)
        rf_model.fit(X, y)
        
        importance_dict = dict(zip(model_features, rf_model.feature_importances_))
        
        results.append({
            'Demo Group': demo,
            'Pay_Amount_Importance(%)': importance_dict.get('avg_pay_amount', 0) * 100,
            'Temp_Importance(%)': importance_dict.get('temp_mean', 0) * 100,
            'Precip_Importance(%)': importance_dict.get('precip_sum', 0) * 100,
            'Distance_Importance(%)': importance_dict.get('avg_distance', 0) * 100,
            'Pay_OLS_Coef': pay_coef,
            'Pay_OLS_Pval': pay_pval
        })
        
    res_df = pd.DataFrame(results).sort_values(by='Pay_Amount_Importance(%)', ascending=False)
    
    print("4. 결과 저장 및 시각화...")
    excel_path = os.path.join(results_dir, "all_demos_sensitivity_results.xlsx")
    res_df.to_excel(excel_path, index=False)
    
    plt.figure(figsize=(12, 7))
    sns.barplot(x='Pay_Amount_Importance(%)', y='Demo Group', data=res_df, palette='Reds_r')
    plt.title('결제 금액에 대한 민감도 (Random Forest 변수 중요도 %)', fontsize=15)
    plt.xlabel('결제 금액의 운행수 예측 기여도 (%)', fontsize=12)
    plt.ylabel('데모그라피 그룹', fontsize=12)
    
    # OLS 부호 추가 표기
    for index, row in res_df.iterrows():
        sign = "-" if row['Pay_OLS_Coef'] < 0 else "+"
        sig = "**" if row['Pay_OLS_Pval'] < 0.05 else ""
        plt.text(row['Pay_Amount_Importance(%)'] + 1, index, f"계수 부호: {sign}{sig}", va='center', fontsize=10)
        
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "pay_amount_sensitivity_comparison.png"), dpi=150)
    plt.close()
    
    print(f" - 분석 완료! 저장 경로: {results_dir}")

if __name__ == "__main__":
    main()
