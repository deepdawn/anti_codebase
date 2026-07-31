import os
import sys
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from data_loader import prepare_training_data
from ensemble_predictor import add_time_features, train_prophet_baseline, train_xgb_residual

def backtest_may(start_date="2024-05-01", max_depth=5, reg_lambda=1.0, reg_alpha=0.0):
    # 과거 데이터 기간: start_date ~ 2026-04-30
    end_date_str = "2026-05-31"
    
    # 5월 전체 데이터 로드
    df_all = prepare_training_data(start_date, end_date_str)
    df_all = add_time_features(df_all)
    
    # Train: start_date ~ 2026-04-30
    df_train = df_all[df_all['date_str'] <= "2026-04-30"].copy()
    
    # Test (Future): 2026-05-01 ~ 2026-05-31
    df_test = df_all[df_all['date_str'] >= "2026-05-01"].copy()
    
    # 실제 5월 총 매출
    actual_may_revenue = df_test['daily_revenue'].sum()
    
    # Prophet 학습
    prophet_model = train_prophet_baseline(df_train)
    
    # XGBoost 학습
    import xgboost as xgb
    df_p = df_train[['date_str']].rename(columns={'date_str': 'ds'})
    forecast = prophet_model.predict(df_p)
    df_train['prophet_pred'] = forecast['yhat'].values
    df_train['residual'] = df_train['daily_revenue'] - df_train['prophet_pred']
    
    features = ['precip', 'temp', 'is_holiday', 'day_of_week', 'is_weekend', 'month']
    X = df_train[features]
    y = df_train['residual']
    
    xgb_model = xgb.XGBRegressor(
        n_estimators=100, 
        max_depth=max_depth, 
        learning_rate=0.1, 
        reg_lambda=reg_lambda,
        reg_alpha=reg_alpha,
        random_state=42
    )
    xgb_model.fit(X, y)
    
    # 예측
    df_test_p = df_test[['date_str']].rename(columns={'date_str': 'ds'})
    test_forecast = prophet_model.predict(df_test_p)
    df_test['prophet_pred'] = test_forecast['yhat'].values
    
    test_residuals = xgb_model.predict(df_test[features])
    df_test['final_pred'] = df_test['prophet_pred'] + test_residuals
    df_test['final_pred'] = df_test['final_pred'].clip(lower=0)
    
    predicted_may_revenue = df_test['final_pred'].sum()
    
    diff = predicted_may_revenue - actual_may_revenue
    diff_pct = (diff / actual_may_revenue) * 100 if actual_may_revenue > 0 else 0
    
    years = 2 if start_date == "2024-05-01" else 3
    print(f"--- [데이터 기간: {years}년 ({start_date} ~), max_depth={max_depth}] ---")
    print(f"실제 5월 마감 매출: {actual_may_revenue:,.0f}원")
    print(f"예측 5월 마감 매출: {predicted_may_revenue:,.0f}원")
    print(f"차이: {diff:,.0f}원 ({diff_pct:+.2f}%)")
    
if __name__ == '__main__':
    print("=== 학습 데이터 증감 비교 (2년 vs 3년) ===")
    # 2년 치 데이터 (2024-05-01)
    backtest_may(start_date="2024-05-01", max_depth=5)
    # 3년 치 데이터 (2023-05-01)
    backtest_may(start_date="2023-05-01", max_depth=5)
