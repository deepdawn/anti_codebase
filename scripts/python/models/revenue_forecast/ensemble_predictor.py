import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from prophet import Prophet
import xgboost as xgb

from models.revenue_forecast.data_loader import prepare_training_data

def add_time_features(df):
    df['dt'] = pd.to_datetime(df['date_str'])
    df['day_of_week'] = df['dt'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['month'] = df['dt'].dt.month
    return df

def train_prophet_baseline(df_train, target_col):
    df_p = df_train[['date_str', target_col]].rename(columns={'date_str': 'ds', target_col: 'y'})
    
    # 공휴일 효과 추가
    holidays = df_train[df_train['is_holiday'] == 1][['date_str']].rename(columns={'date_str': 'ds'})
    holidays['holiday'] = 'kr_holiday'
    
    m = Prophet(holidays=holidays, yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
    m.fit(df_p)
    return m

def train_xgb_residual(df_train, prophet_model, target_col):
    df_p = df_train[['date_str']].rename(columns={'date_str': 'ds'})
    forecast = prophet_model.predict(df_p)
    
    df_train['prophet_pred'] = forecast['yhat'].values
    df_train['residual'] = df_train[target_col] - df_train['prophet_pred']
    
    features = ['precip', 'temp', 'is_holiday', 'day_of_week', 'is_weekend', 'month']
    X = df_train[features]
    y = df_train['residual']
    
    xgb_model = xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
    xgb_model.fit(X, y)
    
    return xgb_model

def _predict_month_end_target(target_col, apply_conservative_factor=False, last_actual_date=None, fixed_start_date=None):
    if last_actual_date is None:
        last_actual_date = datetime.now() - timedelta(days=1)
        
    if fixed_start_date is None:
        # 고정 시작일 (2024년 1월 1일)
        start_date = '2024-01-01'
    else:
        start_date = fixed_start_date.strftime('%Y-%m-%d')
        
    # 이번 달 말일 (last_actual_date가 속한 달 기준)
    next_month = last_actual_date.replace(day=28) + timedelta(days=4)
    end_of_month = next_month - timedelta(days=next_month.day)
    end_date_str = end_of_month.strftime('%Y-%m-%d')
    
    import time
    start_time = time.time()
    
    df_all = prepare_training_data(start_date, end_date_str)
    df_all = add_time_features(df_all)
    
    # Train: start_date ~ last_actual_date
    df_train = df_all[df_all['dt'] <= pd.to_datetime(last_actual_date.strftime('%Y-%m-%d'))].copy()
    
    # 누락된 날짜 제거 (XGBoost 오류 방지)
    df_train = df_train.dropna(subset=[target_col]).copy()
    
    # Predict: last_actual_date 다음날 ~ end_of_month
    future_start_dt = last_actual_date + timedelta(days=1)
    df_future = df_all[(df_all['dt'] >= pd.to_datetime(future_start_dt.strftime('%Y-%m-%d'))) & 
                       (df_all['dt'] <= pd.to_datetime(end_date_str))].copy()
    
    # MTD 계산
    month_start = last_actual_date.replace(day=1).strftime('%Y-%m-%d')
    df_mtd = df_train[df_train['dt'] >= pd.to_datetime(month_start)]
    mtd_val = df_mtd[target_col].sum()
    
    # 1. Prophet Baseline
    prophet_model = train_prophet_baseline(df_train, target_col)
    
    # 2. XGBoost Residuals
    xgb_model = train_xgb_residual(df_train, prophet_model, target_col)
    
    # df_train에 대해서도 과거 예측값 생성
    features = ['precip', 'temp', 'is_holiday', 'day_of_week', 'is_weekend', 'month']
    train_residuals = xgb_model.predict(df_train[features])
    df_train['final_pred'] = df_train['prophet_pred'] + train_residuals
    df_train['final_pred'] = df_train['final_pred'].clip(lower=0)
    
    if apply_conservative_factor:
        df_train['conservative_pred'] = df_train['final_pred'] * 0.98
    
    # 3. Predict Future
    if not df_future.empty:
        df_future_p = df_future[['date_str']].rename(columns={'date_str': 'ds'})
        future_forecast = prophet_model.predict(df_future_p)
        df_future['prophet_pred'] = future_forecast['yhat'].values
        
        future_residuals = xgb_model.predict(df_future[features])
        
        df_future['final_pred'] = df_future['prophet_pred'] + future_residuals
        
        # 음수 보정
        df_future['final_pred'] = df_future['final_pred'].clip(lower=0)
    else:
        df_future['prophet_pred'] = []
        df_future['final_pred'] = []
    
    future_val = df_future['final_pred'].sum()
    total_val = mtd_val + future_val
    
    conservative_total_val = None
    if apply_conservative_factor:
        if not df_future.empty:
            df_future['conservative_pred'] = df_future['final_pred'] * 0.98
        else:
            df_future['conservative_pred'] = []
            
        conservative_future_val = df_future['conservative_pred'].sum()
        conservative_total_val = mtd_val + conservative_future_val
        
    elapsed_time = time.time() - start_time
    
    return mtd_val, future_val, total_val, conservative_total_val, elapsed_time, df_train, df_future

def predict_month_end_revenue(last_actual_date=None, fixed_start_date=None):
    return _predict_month_end_target('daily_revenue', apply_conservative_factor=True, last_actual_date=last_actual_date, fixed_start_date=fixed_start_date)

def predict_month_end_trips(last_actual_date=None, fixed_start_date=None):
    return _predict_month_end_target('daily_trips', apply_conservative_factor=False, last_actual_date=last_actual_date, fixed_start_date=fixed_start_date)

if __name__ == '__main__':
    print("=== 월말 예측 모델 테스트 ===")
    mtd, future, total, cons_total, elapsed, df_train, df_future = predict_month_end_revenue()
    print(f"현재 MTD 매출: {mtd:,.0f}원")
    print(f"남은 기간 예측: {future:,.0f}원")
    print(f"월말 최종 마감 예측: {total:,.0f}원")
    print(f"소요 시간: {elapsed:.2f}초")
    
    mtd_t, future_t, total_t, _, elapsed_t, _, _ = predict_month_end_trips()
    print(f"현재 MTD 트립: {mtd_t:,.0f}건")
    print(f"남은 기간 트립 예측: {future_t:,.0f}건")
    print(f"월말 최종 트립 예측: {total_t:,.0f}건")
    print(f"소요 시간: {elapsed_t:.2f}초")
