import os
import glob
import argparse
import polars as pl
from datetime import datetime, timedelta
import pandas as pd

def load_parquet_dataset(base_path, dataset_name, start_date, end_date):
    path = os.path.join(base_path, dataset_name)
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    file_paths = []
    for dt in pd.date_range(start_dt, end_dt):
        dt_str = dt.strftime("%Y-%m-%d")
        possible_paths = [
            os.path.join(path, f"dt={dt_str}", "*.parquet"),
            os.path.join(path, f"date={dt_str}", "*.parquet"),
            os.path.join(path, dt_str, "*.parquet")
        ]
        for p in possible_paths:
            matched = glob.glob(p)
            if matched:
                file_paths.extend(matched)
                break
                
    if not file_paths:
        # 3. Try to just load the whole thing if unpartitioned
        all_files = glob.glob(os.path.join(path, "**/*.parquet"), recursive=True)
        if all_files:
            return pl.scan_parquet(all_files, missing_columns='insert')
        return None
        
    return pl.scan_parquet(file_paths, missing_columns='insert')

def build_features(start_date, end_date, output_path):
    base_path = os.path.expanduser("~/Google Drive/공유 드라이브")
    
    print(f"Building features from {start_date} to {end_date}...")
    
    # 1. Master: Deploy Zone Usages
    print("Loading gbike.rich_deploy_zone_usages...")
    df_zone = load_parquet_dataset(base_path, "gbike.rich_deploy_zone_usages", start_date, end_date)
    if df_zone is None:
        raise ValueError("deploy_zone_usages not found.")
        
    df_zone = df_zone.select(['date', '중지역', '소지역', '배치존명', '기종', '배치수', '출루수'])
    # 기종 정제
    df_zone = df_zone.with_columns(
        pl.when(pl.col('기종').str.to_lowercase().str.contains('bicycle')).then(pl.lit('자전거'))
        .when(pl.col('기종').str.to_lowercase().str.contains('scooter|k1|k2|max')).then(pl.lit('킥보드'))
        .otherwise(pl.col('기종')).alias('기기구분')
    )
    
    # 2. Weather
    print("Loading gbike_smartops.weather_data...")
    df_weather = load_parquet_dataset(base_path, "gbike_smartops.weather_data", start_date, end_date)
    if df_weather is not None:
        df_weather = df_weather.rename({'high_region_name': '대지역', 'middle_region_name': '중지역'}).select(['date', '중지역', '일 평균 기온', '일 총 강수량'])
    
    # 3. Small Region Utilization (rich_daily_statistics + rich_region)
    print("Loading gbike.rich_daily_statistics & rich_region...")
    df_daily = load_parquet_dataset(base_path, "gbike.rich_daily_statistics", start_date, end_date)
    
    rich_region_files = glob.glob(os.path.join(base_path, "gbike.rich_region", "**/*.parquet"), recursive=True)
    if df_daily is not None and rich_region_files:
        df_region = pl.scan_parquet(rich_region_files[-1]).select(['region_id', '소지역'])
        
        # Calculate regional utilization
        df_daily = df_daily.join(df_region, on='region_id', how='left')
        df_util = df_daily.group_by(['date', '소지역', '기기구분']).agg(
            pl.col('할당대수').sum(),
            pl.col('운행대수').sum(),
            pl.col('운행수').sum()
        ).with_columns(
            (pl.col('운행대수') / pl.col('할당대수')).alias('소지역_가동률'),
            (pl.col('운행수') / pl.col('운행대수')).alias('소지역_기기당_출루수')
        )
    else:
        df_util = None
        
    # 4. Deploy Used Time
    print("Loading gbike.rich_deploy_used_time...")
    df_time = load_parquet_dataset(base_path, "gbike.rich_deploy_used_time", start_date, end_date)
    if df_time is not None:
        df_time = df_time.group_by(['date', '소지역', '배치존명']).agg(
            pl.col('출루까지 시간').mean().alias('평균_출루소요시간')
        )
        
    # 5. Join
    print("Joining features...")
    df = df_zone
    if df_weather is not None:
        df = df.join(df_weather, on=['date', '중지역'], how='left')
    if df_util is not None:
        df = df.join(df_util.select(['date', '소지역', '기기구분', '소지역_가동률', '소지역_기기당_출루수']), on=['date', '소지역', '기기구분'], how='left')
    if df_time is not None:
        df = df.join(df_time, on=['date', '소지역', '배치존명'], how='left')
        
    spatial_path = "/Users/galaxy/anti_codebase/base_data/primary_data/revenue_forecast/spatial_features.parquet"
    if os.path.exists(spatial_path):
        print("Loading spatial_features.parquet...")
        df_spatial = pl.scan_parquet(spatial_path)
        df = df.join(df_spatial, on=['date', '배치존명'], how='left')
        
    print("Executing query...")
    df_final = df.collect()
    
    # 6. Filters (미운영 / 1주일 미만 신규존 제외)
    print("Filtering inactive/new zones...")
    # Calculate total operation days per deploy zone
    zone_days = df_final.group_by('배치존명').agg(pl.len().alias('운영일수'))
    valid_zones = zone_days.filter(pl.col('운영일수') >= 7)['배치존명'].to_list()
    
    df_final = df_final.filter(
        pl.col('배치존명').is_in(valid_zones) &
        (pl.col('배치수') > 0) # 배치수 0인 날은 잠재 수요만 있으므로 일단 남겨둘 수도 있지만, 완전 미운영은 제외
    )
    
    print(f"Final shape: {df_final.shape}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_final.write_parquet(output_path, compression='snappy')
    print(f"Feature mart successfully saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # 최근 3개월 (5, 6, 7월)
    parser.add_argument('--start-date', type=str, default='2026-05-01')
    parser.add_argument('--end-date', type=str, default='2026-08-06')
    parser.add_argument('--output', type=str, default='/Users/galaxy/anti_codebase/base_data/primary_data/revenue_forecast/feature_mart.parquet')
    args = parser.parse_args()
    
    build_features(args.start_date, args.end_date, args.output)
