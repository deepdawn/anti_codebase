import os
import argparse
import polars as pl
import pandas as pd
import numpy as np
import joblib
import json
import requests
from datetime import datetime, timedelta

def get_weather_forecast(lat, lon, start_date_str, end_date_str):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum,temperature_2m_mean&timezone=Asia%2FSeoul&start_date={start_date_str}&end_date={end_date_str}"
        resp = requests.get(url, timeout=5).json()
        if 'daily' in resp:
            df_w = pd.DataFrame({
                'date': resp['daily']['time'],
                '일 총 강수량': resp['daily']['precipitation_sum'],
                '일 평균 기온': resp['daily']['temperature_2m_mean']
            })
            return df_w
    except Exception as e:
        print(f"Weather API Error: {e}")
    
    # Fallback to defaults
    dates = [ (datetime.strptime(start_date_str, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((datetime.strptime(end_date_str, "%Y-%m-%d") - datetime.strptime(start_date_str, "%Y-%m-%d")).days + 1) ]
    return pd.DataFrame({'date': dates, '일 총 강수량': 0.0, '일 평균 기온': 20.0})

def predict_allocation(target_date_start, data_path, model_dir, output_path):
    print(f"Predicting optimal allocation from {target_date_start} to D+7...")
    
    trip_models = joblib.load(os.path.join(model_dir, "deploy_zone_trip_quantile_models.joblib"))
    with open(os.path.join(model_dir, "zone_map.json"), "r") as f:
        zone_map = json.load(f)
    with open(os.path.join(model_dir, "device_map.json"), "r") as f:
        device_map = json.load(f)
        
    # Load recent data to construct lags
    df = pl.read_parquet(data_path)
    df = df.sort(['배치존명', '기기구분', 'date'])
    
    df = df.with_columns(
        pl.col('출루수').shift(1).over(['배치존명', '기기구분']).alias('출루수_lag_1'),
        pl.col('출루수').shift(7).over(['배치존명', '기기구분']).alias('출루수_lag_7'),
        pl.col('배치수').shift(1).over(['배치존명', '기기구분']).alias('배치수_lag_1'),
        pl.col('Inflow_건수').shift(1).over(['배치존명', '기기구분']).alias('Inflow_건수_lag_1'),
        pl.col('Outflow_건수').shift(1).over(['배치존명', '기기구분']).alias('Outflow_건수_lag_1'),
        pl.col('순유출입_건수').shift(1).over(['배치존명', '기기구분']).alias('순유출입_건수_lag_1'),
        pl.col('active_유저_비율').shift(1).over(['배치존명', '기기구분']).alias('active_유저_비율_lag_1'),
        pl.col('2030_유저_비율').shift(1).over(['배치존명', '기기구분']).alias('2030_유저_비율_lag_1')
    )
    
    df_pd = df.to_pandas()
    df_pd['배치존명_idx'] = df_pd['배치존명'].map(zone_map).fillna(0).astype(int)
    df_pd['기기구분_idx'] = df_pd['기기구분'].map(device_map).fillna(0).astype(int)
    
    # Base state: The most recent row for each zone/device
    latest_df = df_pd.sort_values('date').groupby(['배치존명', '기기구분']).last().reset_index()
    
    # Get weather for the next 7 days (Seoul coordinates as proxy)
    start_dt = datetime.strptime(target_date_start, "%Y-%m-%d")
    end_dt = start_dt + timedelta(days=6)
    weather_df = get_weather_forecast(37.5665, 126.9780, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
    
    features = [
        '배치존명_idx', '기기구분_idx', 'day_of_week', 'month',
        '출루수_lag_1', '출루수_lag_7', '배치수_lag_1',
        '일 총 강수량', '일 평균 기온',
        '소지역_가동률', '소지역_기기당_출루수', '평균_출루소요시간',
        'Inflow_건수_lag_1', 'Outflow_건수_lag_1', '순유출입_건수_lag_1',
        'active_유저_비율_lag_1', '2030_유저_비율_lag_1'
    ]
    
    results = []
    
    for i in range(7):
        current_dt = start_dt + timedelta(days=i)
        current_date_str = current_dt.strftime("%Y-%m-%d")
        
        sim_df = latest_df.copy()
        sim_df['date_pred'] = current_date_str
        sim_df['day_of_week'] = current_dt.weekday()
        sim_df['month'] = current_dt.month
        
        # Merge weather
        w = weather_df[weather_df['date'] == current_date_str]
        if not w.empty:
            sim_df['일 총 강수량'] = w.iloc[0]['일 총 강수량']
            sim_df['일 평균 기온'] = w.iloc[0]['일 평균 기온']
        else:
            sim_df['일 총 강수량'] = 0.0
            sim_df['일 평균 기온'] = 20.0
            
        sim_df.replace([np.inf, -np.inf], np.nan, inplace=True)
        X = sim_df[features].fillna(0)
        
        preds_p50 = trip_models['q_0.5'].predict(X)
        preds_p80 = trip_models['q_0.8'].predict(X)
        
        sim_df['예상_출루수_P50'] = np.maximum(0, preds_p50)
        sim_df['예상_출루수_P80'] = np.maximum(0, preds_p80)
        
        # Calculate optimal allocation
        # 최적 대수 = 예상 출루수 / 소지역 단위 기기당 평균 출루수 (생산성)
        prod = np.clip(sim_df['소지역_기기당_출루수'].fillna(1.0), 0.1, 10.0)
        
        sim_df['최소_적정대수'] = np.ceil(sim_df['예상_출루수_P50'] / prod)
        sim_df['권장_적정대수'] = np.ceil(sim_df['예상_출루수_P80'] / prod)
        
        sim_df['증감_필요량'] = sim_df['권장_적정대수'] - sim_df['배치수']
        
        res_cols = [
            'date_pred', '중지역', '소지역', '배치존명', '기기구분', 
            '현재_배치수', '최소_적정대수', '권장_적정대수', '증감_필요량',
            '예상_출루수_P50', '예상_출루수_P80', '소지역_기기당_출루수', '일 총 강수량'
        ]
        sim_df['현재_배치수'] = sim_df['배치수']
        results.append(sim_df[res_cols])
        
        # In a real rolling forecast, we would update lags here.
        # But for an allocation plan, we assume current state is static or just use simple baseline.
        
    final_df = pd.concat(results, ignore_index=True)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_df.to_excel(output_path, index=False)
    
    print(f"Optimal allocation report (D+1 to D+7) saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--target-date-start', type=str, default=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))
    parser.add_argument('--data-path', type=str, default='/Users/galaxy/anti_codebase/base_data/primary_data/revenue_forecast/feature_mart.parquet')
    parser.add_argument('--model-dir', type=str, default='/Users/galaxy/anti_codebase/scripts/python/models/revenue_forecast/artifacts')
    parser.add_argument('--output-path', type=str, default='/Users/galaxy/anti_codebase/results/revenue_forecast/deploy_zone_allocation_report_7days.xlsx')
    
    args = parser.parse_args()
    
    predict_allocation(args.target_date_start, args.data_path, args.model_dir, args.output_path)
