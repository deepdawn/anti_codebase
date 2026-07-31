import sys
import os
import calendar
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(base_dir, '..')))
import test_db_conn

def main():
    # 2026-03-05 00:00:00 KST 로 시작점 잡기
    start_ts = calendar.timegm(datetime.datetime(2026, 3, 4, 15, 0, 0).timetuple())
    
    query = f"""
    WITH user_info AS (
        SELECT user_id, 
            CASE 
                WHEN r.age IS NULL THEN '알수없음'
                WHEN r.age >= 10 AND r.age < 20 THEN '10대'
                WHEN r.age >= 20 AND r.age < 30 THEN '20대'
                WHEN r.age >= 30 AND r.age < 40 THEN '30대'
                WHEN r.age >= 40 AND r.age < 50 THEN '40대'
                WHEN r.age >= 50 AND r.age < 60 THEN '50대'
                ELSE '기타' 
            END AS age_group,
            gender
        FROM (
            SELECT user_id,
                CASE 
                    WHEN gender IS NULL THEN '알수없음'
                    WHEN MOD(gender, 2) = 1 THEN '남자'
                    ELSE '여자'
                END AS gender,
                CASE
                    WHEN birthday IS NULL THEN NULL
                    ELSE FLOOR((EXTRACT(YEAR FROM CURRENT_DATE) * 10000 + EXTRACT(MONTH FROM CURRENT_DATE) * 100 + EXTRACT(DAY FROM CURRENT_DATE) - birthday) / 10000)
                END AS age
            FROM gbike.rich_user
        ) r
    )
    SELECT 
        o.order_id, o.user_id, o.distance, o.pay_amount, o.start_time, o.end_time,
        CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul') AS add_time_kst,
        ST_AsText(o.start_point) AS start_wkt,
        ST_AsText(o.end_point) AS end_wkt,
        ST_AsText(o.start_user_point) AS start_user_wkt,
        ST_AsText(o.end_user_point) AS end_user_wkt,
        u.age_group, u.gender
    FROM gbike.rich_orders o
    LEFT JOIN user_info u ON o.user_id = u.user_id
    WHERE o.region_id = 1360
      AND o.add_time >= {start_ts}
    """
    
    csv_path = os.path.join(base_dir, '../../../base_data/secondary_data/rumi_analysis_v2/rumi_deep_data.csv')
    print("Extracting deep analysis data for Rumi (region 1360)...")
    df = test_db_conn.run_query(query, save_csv_path=csv_path)
    
    if df is None or df.empty:
        print("Data extraction failed or empty dataframe returned.")
        return

    print(f"Data retrieved: {len(df)} rows.")
    
    results_dir = os.path.join(base_dir, '../../../results/rumi_analysis_v2/')
    os.makedirs(results_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")
    
    # 1. Feature Engineering
    df['duration_min'] = (df['end_time'] - df['start_time']) / 60.0
    df['duration_min'] = df['duration_min'].apply(lambda x: x if pd.notnull(x) and x >= 0 else 0)
    
    def pt_element(wkt, group_idx):
        if pd.isna(wkt): return np.nan
        m = re.search(r'POINT\(([-\d.]+) ([-\d.]+)\)', str(wkt))
        return float(m.group(group_idx)) if m else np.nan
        
    # Apply Fallback logic
    mask_start = (df['start_wkt'] == 'POINT(0 0)') | df['start_wkt'].isna()
    df.loc[mask_start, 'start_wkt'] = df.loc[mask_start, 'start_user_wkt']
    
    mask_end = (df['end_wkt'] == 'POINT(0 0)') | df['end_wkt'].isna()
    df.loc[mask_end, 'end_wkt'] = df.loc[mask_end, 'end_user_wkt']
    
    df['start_lon'] = df['start_wkt'].apply(lambda x: pt_element(x, 1))
    df['start_lat'] = df['start_wkt'].apply(lambda x: pt_element(x, 2))
    df['end_lon'] = df['end_wkt'].apply(lambda x: pt_element(x, 1))
    df['end_lat'] = df['end_wkt'].apply(lambda x: pt_element(x, 2))
    
    # Exclude POINT(0 0) invalid data points
    df = df[(df['start_lon'] != 0.0) & (df['start_lat'] != 0.0) & (df['end_lon'] != 0.0) & (df['end_lat'] != 0.0)].copy()

    df.to_csv(csv_path, index=False, encoding='utf-8-sig') # resave with fallback applied
    
    
    df['add_time_kst'] = pd.to_datetime(df['add_time_kst'])
    df['hour'] = df['add_time_kst'].dt.hour
    df['day_of_week'] = df['add_time_kst'].dt.day_name()
    
    df['age_group'] = df['age_group'].fillna('Unknown')
    df['gender'] = df['gender'].fillna('Unknown')
    
    age_map = {'10대': '10s', '20대': '20s', '30대': '30s', '40대': '40s', '50대': '50s', '기타': 'Other', '알수없음': 'Unknown'}
    gender_map = {'남자': 'Male', '여자': 'Female', '알수없음': 'Unknown'}
    df['age_group_en'] = df['age_group'].map(age_map).fillna(df['age_group'])
    df['gender_en'] = df['gender'].map(gender_map).fillna(df['gender'])

    # 2. Daily/Hourly/DOW Heatmap
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heat_data = df.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
    heat_data = heat_data.reindex(days_order)
    
    plt.figure(figsize=(12, 6))
    sns.heatmap(heat_data, cmap='YlGnBu', annot=False)
    plt.title('Daily & Hourly Trip Frequency Heatmap')
    plt.ylabel('Day of Week')
    plt.xlabel('Hour of Day')
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'heat_map.png'))
    plt.close()
    
    # 3. Demographics Bar (Pay Amount)
    demo_df = df.groupby(['age_group_en', 'gender_en'])['pay_amount'].sum().reset_index()
    
    plt.figure(figsize=(10, 6))
    sns.barplot(data=demo_df, x='age_group_en', y='pay_amount', hue='gender_en', 
                order=['10s','20s','30s','40s','50s','Other','Unknown'])
    plt.title('Total Revenue by Age and Gender')
    plt.ylabel('Total Pay Amount (KRW)')
    plt.xlabel('Age Group')
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'demographics_bar.png'))
    plt.close()
    
    # 3-2. Demographics Deep Dive (User Count, Avg Dist, Avg Dur, Avg Speed)
    df['speed_kmh'] = df['distance'] / 1000.0 / (df['duration_min'] / 60.0)
    df.loc[df['duration_min'] == 0, 'speed_kmh'] = 0.0
    
    custom_agg = df.groupby(['age_group_en', 'gender_en']).agg(
        unique_users=('user_id', 'nunique'),
        total_trips=('order_id', 'count'),
        avg_distance_m=('distance', 'mean'),
        avg_duration_min=('duration_min', 'mean'),
        avg_speed_kmh=('speed_kmh', lambda x: x[x < 50].mean()) # cap outliers above 50km/h
    ).reset_index().round(2)
    
    # Sort for report
    custom_agg = custom_agg.sort_values(by=['unique_users', 'total_trips'], ascending=[False, False])
    
    # 4. Duration vs Distance Scatter
    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=df, x='duration_min', y='distance', alpha=0.3, s=10)
    plt.title('Trip Duration vs Distance')
    plt.xlabel('Duration (Minutes)')
    plt.ylabel('Distance (Meters)')
    plt.xlim(0, 120) 
    plt.ylim(0, 15000) 
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'duration_scatter.png'))
    plt.close()
    
    # 5. Trips per user & Core Stats Export
    user_trips = df.groupby('user_id').size()
    with open(os.path.join(results_dir, 'analysis_report.txt'), 'w', encoding='utf-8') as f:
        f.write("=== User Trip Frequency (Global) ===\n")
        f.write(user_trips.describe().to_string())
        
        f.write("\n\n=== Demographic Insights (Count, Avg Dist, Avg Dur) ===\n")
        f.write(custom_agg.to_string(index=False))
        
        f.write("\n\n=== Global Distance & Duration Summary ===\n")
        f.write(df[['distance', 'duration_min', 'pay_amount']].describe().to_string())
        
        
    print("Deep analysis visualization complete.")

if __name__ == '__main__':
    main()
