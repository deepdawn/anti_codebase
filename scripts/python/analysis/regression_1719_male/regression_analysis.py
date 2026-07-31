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
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

sys.path.append('/Users/galaxy/anti_codebase/scripts/python/utils')
from read_rich_orders_polars import load_rich_orders_polars

def fetch_weather_data(start_date, end_date):
    """
    Open-Meteo API를 통해 고양시청 좌표 기준 일별 날씨 데이터 수집
    """
    lat, lon = "37.65695122231786", "126.83317101598665"
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_mean,precipitation_sum&timezone=Asia%2FSeoul"
    
    print(" - 날씨 데이터(Open-Meteo) 수집 중...")
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            df = pd.DataFrame(data['daily'])
            df.rename(columns={'time': 'date', 'temperature_2m_mean': 'temp_mean', 'precipitation_sum': 'precip_sum'}, inplace=True)
            
            # 누락된 날짜가 있을 경우를 대비하여 보간
            full_dates = pd.date_range(start_date, end_date).strftime('%Y-%m-%d')
            df_full = pd.DataFrame({'date': full_dates})
            df_full = df_full.merge(df, on='date', how='left')
            df_full['temp_mean'] = df_full['temp_mean'].fillna(df_full['temp_mean'].mean()).fillna(15.0)
            df_full['precip_sum'] = df_full['precip_sum'].fillna(0.0)
            print(f" - 날씨 데이터 수집 완료 (건수: {len(df_full)})")
            return pl.from_pandas(df_full)
        else:
            print(f" - API 응답 오류: {r.status_code}. Mock 데이터 반환")
    except Exception as e:
        print(f" - API 호출 오류: {e}. Mock 데이터 반환")
        
    full_dates = pd.date_range(start_date, end_date).strftime('%Y-%m-%d')
    return pl.DataFrame({'date': full_dates, 'temp_mean': 15.0, 'precip_sum': 0.0})

def calculate_vif(X):
    """VIF 계산"""
    vif_data = pd.DataFrame()
    vif_data["feature"] = X.columns
    vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(len(X.columns))]
    return vif_data

def main():
    base_drive = "/Users/galaxy/Google Drive/공유 드라이브"
    orders_path = f"{base_drive}/gbike.rich_orders"
    region_path = f"{base_drive}/gbike.rich_region/rich_region_hierarchy.parquet"
    user_path = f"{base_drive}/gbike.rich_user/rich_user_all.parquet"
    
    results_dir = "/Users/galaxy/anti_codebase/results/regression_1719_male"
    os.makedirs(results_dir, exist_ok=True)
    
    start_date, end_date = "2025-01-01", "2026-05-31"
    
    # 1. 데이터 로드 및 조인
    print("1. 파켓 데이터 로드 및 조인...")
    region_df = pl.scan_parquet(region_path).filter(pl.col('중지역') == '고양2캠프').select(['region_id']).collect()
    
    # 타겟 그룹만 로드
    user_df = pl.scan_parquet(user_path).filter(
        (pl.col('age_group') == '17~19세') & (pl.col('gender') == '남자')
    ).select(['user_id']).collect()
    
    orders_cols = ['dt', 'order_id', 'user_id', 'low_region_id', 'distance', 'duration_minutes', 'pay_amount', 'is_late_night_surcharge']
    orders_df = load_rich_orders_polars(start_date, end_date, columns=orders_cols, base_path=orders_path)
    
    # Inner Join 
    df = orders_df.join(region_df, left_on='low_region_id', right_on='region_id', how='inner')
    df = df.join(user_df, on='user_id', how='inner')
    
    # 2. 일별 집계 (Aggregation)
    print("2. 일별 데이터 파생변수 생성 및 집계...")
    df = df.with_columns(pl.col('dt').dt.strftime('%Y-%m-%d').alias('date'))
    
    daily_df = df.group_by('date').agg([
        pl.len().alias('order_count'),
        pl.col('distance').mean().alias('avg_distance'),
        pl.col('duration_minutes').mean().alias('avg_duration'),
        pl.col('pay_amount').mean().alias('avg_pay_amount'),
        (pl.col('is_late_night_surcharge').sum() / pl.len()).alias('late_night_ratio')
    ]).sort('date')
    
    # 3. 날씨 데이터 결합 및 시간 변수 추가
    weather_df = fetch_weather_data(start_date, end_date)
    daily_df = daily_df.join(weather_df, on='date', how='left')
    
    daily_df = daily_df.with_columns([
        pl.col('date').str.strptime(pl.Date, "%Y-%m-%d").dt.weekday().alias('day_of_week'), # 1(Mon) ~ 7(Sun)
        pl.col('date').str.strptime(pl.Date, "%Y-%m-%d").dt.month().alias('month')
    ])
    
    # 주말 여부 (토, 일)
    daily_df = daily_df.with_columns(
        (pl.col('day_of_week') >= 6).cast(pl.Int32).alias('is_weekend')
    )
    
    # 결측치 보간
    daily_df = daily_df.fill_null(strategy='forward').fill_null(strategy='backward')
    
    pdf = daily_df.to_pandas()
    # 시간 추세 변수 (지속적인 하락세를 반영하기 위함)
    pdf['time_trend'] = np.arange(len(pdf))
    
    print(f" - 집계 완료 (총 {len(pdf)}일)")
    
    # 4. 모델링 준비
    print("3. 통계적 가정 검증 및 다중 선형 회귀 분석(OLS) 수행...")
    features = ['avg_distance', 'avg_duration', 'avg_pay_amount', 'late_night_ratio', 
                'temp_mean', 'precip_sum', 'is_weekend', 'time_trend']
    X = pdf[features]
    y = pdf['order_count']
    
    # 다중공선성(VIF) 확인
    vif_res = calculate_vif(X.assign(const=1))
    print("\n[VIF 결과]")
    print(vif_res)
    
    # OLS 적용
    X_sm = sm.add_constant(X)
    ols_model = sm.OLS(y, X_sm).fit()
    print(ols_model.summary())
    
    # 자기상관성(Durbin-Watson)은 summary에 포함됨
    
    # 5. 랜덤 포레스트 앙상블 모델 (비선형 특징 및 중요도 파악)
    print("4. Random Forest 회귀 분석 및 변수 중요도 추출...")
    rf_model = RandomForestRegressor(n_estimators=200, random_state=42, max_depth=5)
    rf_model.fit(X, y)
    
    rf_importance = pd.DataFrame({
        'Feature': features,
        'Importance': rf_model.feature_importances_
    }).sort_values(by='Importance', ascending=False)
    
    pdf['predicted_rf'] = rf_model.predict(X)
    pdf['predicted_ols'] = ols_model.predict(X_sm)
    
    # 6. 결과 엑셀 저장
    print("5. 결과 저장 및 시각화...")
    excel_path = os.path.join(results_dir, "regression_analysis_results.xlsx")
    with pd.ExcelWriter(excel_path) as writer:
        # 1. 요약
        summary_data = {
            'Metric': ['R-squared (OLS)', 'Adj R-squared (OLS)', 'Durbin-Watson', 'RF R-squared'],
            'Value': [ols_model.rsquared, ols_model.rsquared_adj, sm.stats.stattools.durbin_watson(ols_model.resid), rf_model.score(X, y)]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Model_Metrics', index=False)
        
        # 2. OLS Coefficients
        coef_df = pd.DataFrame({
            'Feature': ols_model.params.index,
            'Coefficient': ols_model.params.values,
            'P-value': ols_model.pvalues.values
        })
        coef_df.to_excel(writer, sheet_name='OLS_Coefficients', index=False)
        
        # 3. RF Feature Importance
        rf_importance.to_excel(writer, sheet_name='RF_Importance', index=False)
        
        # 4. Raw Aggregated Data
        pdf.to_excel(writer, sheet_name='Daily_Dataset', index=False)
        
    # 시각화 1: Random Forest Feature Importance
    plt.figure(figsize=(10, 6))
    sns.barplot(x='Importance', y='Feature', data=rf_importance, palette='viridis')
    plt.title('Random Forest Feature Importance (17~19세 남성 운행수 예측)', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "rf_feature_importance.png"), dpi=150)
    plt.close()
    
    # 시각화 2: 실제 vs 예측 (RF)
    plt.figure(figsize=(14, 6))
    plt.plot(pdf['date'], pdf['order_count'], label='Actual Order Count', color='black', alpha=0.6)
    plt.plot(pdf['date'], pdf['predicted_rf'], label='RF Predicted', color='red', alpha=0.8, linestyle='--')
    plt.title('Actual vs Predicted Daily Orders (17~19 Male, Random Forest)', fontsize=15)
    plt.xlabel('Date')
    plt.ylabel('Order Count')
    plt.xticks(pdf['date'][::30], rotation=45) # 30일 간격
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "actual_vs_predicted_rf.png"), dpi=150)
    plt.close()
    
    print(f" - 분석 완료! 결과물 저장 디렉토리: {results_dir}")

if __name__ == "__main__":
    main()
