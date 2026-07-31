import os
import sys
import requests
import polars as pl
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils.read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic

def load_historical_revenue(start_date_str, end_date_str):
    """
    지정된 날짜 기간의 순매출을 일별로 집계하여 반환
    """
    # OOM 방지를 위해 집계에 필요한 최소한의 컬럼만 로드
    cols = ['dt', 'pay_amount', 'out_of_area_charge', 'order_amount', 'from_api']
    df_raw = load_rich_orders_polars(start_date_str, end_date_str, columns=cols)
    if df_raw.is_empty():
        return pl.DataFrame()
        
    df_fee = apply_channel_fee_logic(df_raw)
    
    df_agg = (
        df_fee.with_columns(
            ((pl.col("calculated_pay_amount").fill_null(0) + pl.col("calculated_out_of_area_charge").fill_null(0)) / 1.1).alias("net_revenue"),
            pl.col("dt").dt.strftime("%Y-%m-%d").alias("date_str")
        )
        .group_by("date_str")
        .agg(
            pl.col("net_revenue").sum().alias("daily_revenue"),
            pl.col("net_revenue").count().alias("daily_trips")
        )
        .sort("date_str")
    )
    return df_agg

def get_weather_data(start_date_str, end_date_str):
    """과거 날씨 및 예보 데이터 수집 (강수량, 기온)"""
    lat, lon = 37.5665, 126.9780
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    yesterday_str = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    
    weather_list = []
    
    # 1. Archive 데이터 (과거)
    if start_date_str <= yesterday_str:
        archive_end = min(end_date_str, yesterday_str)
        try:
            url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date_str}&end_date={archive_end}&daily=precipitation_sum,temperature_2m_mean&timezone=Asia%2FSeoul"
            resp = requests.get(url, timeout=10).json()
            if 'daily' in resp:
                for d, p, t in zip(resp['daily']['time'], resp['daily']['precipitation_sum'], resp['daily']['temperature_2m_mean']):
                    weather_list.append({"date_str": d, "precip": p if p else 0.0, "temp": t if t else 0.0})
        except Exception as e:
            print(f"Archive 날씨 정보 로드 실패: {e}")

    # 2. Forecast 데이터 (미래)
    if end_date_str >= today_str:
        try:
            # past_days=0 (오늘부터), forecast_days=16 (최대 16일)
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum,temperature_2m_mean&timezone=Asia%2FSeoul&past_days=0&forecast_days=16"
            resp = requests.get(url, timeout=10).json()
            if 'daily' in resp:
                for d, p, t in zip(resp['daily']['time'], resp['daily']['precipitation_sum'], resp['daily']['temperature_2m_mean']):
                    if today_str <= d <= end_date_str:
                        weather_list.append({"date_str": d, "precip": p if p else 0.0, "temp": t if t else 0.0})
        except Exception as e:
            print(f"Forecast 날씨 정보 로드 실패: {e}")
            
    if not weather_list:
        return pl.DataFrame({"date_str": [], "precip": [], "temp": []})
        
    df_weather = pl.DataFrame(weather_list).unique(subset=['date_str'], keep='last')
    return df_weather

def get_holidays_data(years):
    import holidays
    kr_holidays = holidays.KR(years=years)
    holiday_list = [{"date_str": str(date), "is_holiday": 1} for date, name in kr_holidays.items()]
    if not holiday_list:
        return pl.DataFrame({"date_str": [], "is_holiday": []})
    return pl.DataFrame(holiday_list)

def prepare_training_data(start_date_str, end_date_str):
    """
    학습 및 예측을 위한 마스터 데이터프레임 생성
    매출 + 날씨 + 휴일 결합
    """
    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    # 1. 뼈대가 되는 날짜 데이터프레임 생성
    dates = []
    curr = start_dt
    while curr <= end_dt:
        dates.append({"date_str": curr.strftime('%Y-%m-%d')})
        curr += timedelta(days=1)
    df_dates = pl.DataFrame(dates)
    
    # 2. 과거 매출 데이터 로드 (과거에만 존재)
    now = datetime.now()
    yesterday_str = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    rev_end_date = min(end_date_str, yesterday_str)
    
    df_rev = load_historical_revenue(start_date_str, rev_end_date)
    
    # 3. 날씨 데이터 로드
    df_weather = get_weather_data(start_date_str, end_date_str)
    
    # 4. 휴일 데이터 로드
    years = list(range(start_dt.year, end_dt.year + 1))
    df_holidays = get_holidays_data(years)
    
    # JOIN
    df_merged = df_dates.join(df_rev, on="date_str", how="left")
    df_merged = df_merged.join(df_weather, on="date_str", how="left")
    df_merged = df_merged.join(df_holidays, on="date_str", how="left")
    
    # 결측치 및 피처 처리
    df_merged = df_merged.with_columns([
        pl.col("is_holiday").fill_null(0),
        pl.col("precip").fill_null(0.0),
        pl.col("temp").fill_null(strategy="forward") # 과거 데이터 기반 ffill
    ])
    
    # 판다스로 변환하여 반환 (Prophet 및 scikit-learn 호환)
    return df_merged.to_pandas()

if __name__ == '__main__':
    print("데이터 로더 단위 테스트 (최근 7일 ~ 내일)")
    now = datetime.now()
    start = (now - timedelta(days=7)).strftime('%Y-%m-%d')
    end = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    df = prepare_training_data(start, end)
    print(df)
