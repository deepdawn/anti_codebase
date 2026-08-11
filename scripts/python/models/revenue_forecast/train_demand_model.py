import os
import argparse
import polars as pl
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
import joblib
import json

def create_features(df):
    """시계열 지연 변수 및 추가 피처 생성 (배치존 단위)"""
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
    
    df = df.with_columns(
        pl.col('date').dt.weekday().alias('day_of_week'),
        pl.col('date').dt.month().alias('month')
    )
    
    df = df.drop_nulls(subset=['출루수_lag_7'])
    
    # Label encoding
    zones = df['배치존명'].unique().to_list()
    devices = df['기기구분'].unique().to_list()
    zone_map = {z: i for i, z in enumerate(zones)}
    device_map = {d: i for i, d in enumerate(devices)}
    
    df = df.with_columns(
        pl.col('배치존명').replace(zone_map).cast(pl.Int32).alias('배치존명_idx'),
        pl.col('기기구분').replace(device_map).cast(pl.Int32).alias('기기구분_idx')
    )
    
    return df, zone_map, device_map

def train_quantile_model(X_train, y_train, weights, quantiles=[0.5, 0.8]):
    models = {}
    for q in quantiles:
        print(f"  Training Quantile: {q}")
        try:
            model = xgb.XGBRegressor(
                objective='reg:quantileerror', 
                quantile_alpha=q,
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                tree_method='hist',
                random_state=42
            )
            model.fit(X_train, y_train, sample_weight=weights)
            models[f'q_{q}'] = model
        except Exception as e:
            print(f"XGBoost reg:quantileerror failed: {e}. Falling back to GradientBoostingRegressor.")
            from sklearn.ensemble import GradientBoostingRegressor
            model = GradientBoostingRegressor(loss='quantile', alpha=q, n_estimators=100, random_state=42)
            model.fit(X_train, y_train, sample_weight=weights)
            models[f'q_{q}'] = model
    return models

def main(data_path, output_dir):
    print(f"Loading feature mart from {data_path}...")
    df = pl.read_parquet(data_path)
    
    print("Creating features...")
    df, zone_map, device_map = create_features(df)
    df_pd = df.to_pandas()
    
    features = [
        '배치존명_idx', '기기구분_idx', 'day_of_week', 'month',
        '출루수_lag_1', '출루수_lag_7', '배치수_lag_1',
        '일 총 강수량', '일 평균 기온',
        '소지역_가동률', '소지역_기기당_출루수', '평균_출루소요시간',
        'Inflow_건수_lag_1', 'Outflow_건수_lag_1', '순유출입_건수_lag_1',
        'active_유저_비율_lag_1', '2030_유저_비율_lag_1'
    ]
    
    df_pd.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_pd[features] = df_pd[features].fillna(0)
    df_pd['출루수'] = df_pd['출루수'].fillna(0)
    
    dates = sorted(df_pd['date'].unique())
    split_date = dates[-14] # Last 14 days for test
    
    train_df = df_pd[df_pd['date'] < split_date].copy()
    test_df = df_pd[df_pd['date'] >= split_date].copy()
    
    print(f"Train set: {len(train_df)} rows, Test set: {len(test_df)} rows")
    
    # 잠재 수요 반영: 배치수가 1 이상이었던 날에 더 큰 가중치 부여
    train_weights = np.where(train_df['배치수'] >= 1, 1.0, 0.5)
    
    X_train = train_df[features]
    y_train = train_df['출루수']
    
    X_test = test_df[features]
    y_test = test_df['출루수']
    
    print("Training Demand Model (Trips) - Quantiles P50, P80...")
    trip_models = train_quantile_model(X_train, y_train, weights=train_weights, quantiles=[0.5, 0.8])
    
    # Evaluate P50 Model
    preds_p50 = trip_models['q_0.5'].predict(X_test)
    preds_p50 = np.maximum(0, preds_p50) # Remove negatives
    mae = mean_absolute_error(y_test, preds_p50)
    wape = np.sum(np.abs(y_test - preds_p50)) / np.sum(y_test) if np.sum(y_test) > 0 else 0
    
    print(f"Test MAE (P50 Deploy Zone Trips): {mae:.2f}")
    print(f"Test WAPE (P50 Deploy Zone Trips): {wape:.2%}")
    
    # Save Models
    os.makedirs(output_dir, exist_ok=True)
    joblib.dump(trip_models, os.path.join(output_dir, "deploy_zone_trip_quantile_models.joblib"))
    
    with open(os.path.join(output_dir, "zone_map.json"), "w") as f:
        json.dump(zone_map, f)
    with open(os.path.join(output_dir, "device_map.json"), "w") as f:
        json.dump(device_map, f)
        
    print(f"Models saved successfully to {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-path', type=str, default='/Users/galaxy/anti_codebase/base_data/primary_data/revenue_forecast/feature_mart.parquet')
    parser.add_argument('--output-dir', type=str, default='/Users/galaxy/anti_codebase/scripts/python/models/revenue_forecast/artifacts')
    args = parser.parse_args()
    
    main(args.data_path, args.output_dir)
