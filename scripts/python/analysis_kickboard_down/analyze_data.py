import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def set_korean_font():
    plt.rc('font', family='AppleGothic')
    plt.rcParams['axes.unicode_minus'] = False

def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, '../../../base_data/primary_data/analysis_kickboard_down/trip_data_w19_w20.xlsx')
    df = pd.read_excel(excel_path)
    return df

def load_allocated_units():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, '../../../base_data/secondary_data/Number of allocated units per camp.xlsx')
    df = pd.read_excel(excel_path)
    df = df[df['기종'] == '킥보드']
    # 'week' 컬럼 값을 W19, W20 포맷으로 변환
    df['week_num'] = df['week'].apply(lambda x: 'W19' if '19' in str(x) else ('W20' if '20' in str(x) else x))
    grouped = df.groupby(['middle_region_name', 'week_num'])['할당대수'].sum().reset_index()
    grouped.rename(columns={'middle_region_name': 'camp_name', '할당대수': 'allocated_units'}, inplace=True)
    return grouped

def load_deploy_zone_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, '../../../base_data/primary_data/analysis_kickboard_down/deploy_zone_w19_w20.xlsx')
    if not os.path.exists(excel_path):
        return None
    df = pd.read_excel(excel_path)
    df['date'] = pd.to_datetime(df['date'])
    df['week_num'] = np.where(df['date'] <= '2026-05-10', 'W19', 'W20')
    return df

def analyze_camp_metrics(df, allocated_units):
    grouped = df.groupby(['camp_name', 'week_num']).agg(
        trip_count=('order_id', 'count'),
        deployed_units=('bicycle_sn', 'nunique'),
        total_revenue=('net_revenue', 'sum'),
        avg_duration=('duration_min', 'mean')
    ).reset_index()
    
    # 할당 대수 머지
    grouped = pd.merge(grouped, allocated_units, on=['camp_name', 'week_num'], how='left')
    
    # 신규 수식 적용
    grouped['revenue_per_asset'] = grouped['total_revenue'] / (grouped['allocated_units'] * 1.1)
    grouped['trips_per_asset'] = grouped['trip_count'] / grouped['allocated_units']
    grouped['revenue_per_trip'] = grouped['total_revenue'] / grouped['trip_count']
    
    pivot = grouped.pivot(index='camp_name', columns='week_num', values=[
        'trip_count', 'allocated_units', 'total_revenue', 
        'revenue_per_asset', 'trips_per_asset', 'revenue_per_trip', 'avg_duration'
    ])
    pivot.columns = [f'{col[0]}_{col[1]}' for col in pivot.columns]
    
    # 변동률 계산
    pivot['trip_drop_pct'] = (pivot['trip_count_W20'] - pivot['trip_count_W19']) / pivot['trip_count_W19'] * 100
    pivot['rev_per_asset_drop_pct'] = (pivot['revenue_per_asset_W20'] - pivot['revenue_per_asset_W19']) / pivot['revenue_per_asset_W19'] * 100
    
    return pivot.reset_index()

def analyze_demographics(df):
    demo_grp = df.groupby(['camp_name', 'age_group', 'week_num']).size().unstack(fill_value=0).reset_index()
    for w in ['W19', 'W20']:
        if w not in demo_grp.columns: demo_grp[w] = 0
    demo_grp['drop_count'] = demo_grp['W20'] - demo_grp['W19']
    demo_grp['drop_pct'] = (demo_grp['drop_count'] / demo_grp['W19'].replace(0, np.nan)) * 100
    return demo_grp

def analyze_locations(df):
    loc_grp = df.groupby(['camp_name', 'small_region_name', 'week_num']).size().unstack(fill_value=0).reset_index()
    for w in ['W19', 'W20']:
        if w not in loc_grp.columns: loc_grp[w] = 0
    loc_grp['drop_count'] = loc_grp['W20'] - loc_grp['W19']
    loc_grp['drop_pct'] = (loc_grp['drop_count'] / loc_grp['W19'].replace(0, np.nan)) * 100
    return loc_grp.sort_values(['camp_name', 'drop_count'])

def analyze_deploy_zone(df):
    if df is None: return pd.DataFrame()
    grouped = df.groupby(['중지역', '배치존명', 'week_num']).agg(
        배치수=('배치수', 'sum'),
        출루수=('출루수', 'sum')
    ).reset_index()
    grouped['출루율'] = grouped['출루수'] / grouped['배치수'].replace(0, np.nan)
    
    pivot = grouped.pivot(index=['중지역', '배치존명'], columns='week_num', values=['배치수', '출루수', '출루율'])
    pivot.columns = [f'{col[0]}_{col[1]}' for col in pivot.columns]
    
    pivot['출루수_drop'] = pivot['출루수_W20'] - pivot['출루수_W19']
    pivot['출루율_drop'] = pivot['출루율_W20'] - pivot['출루율_W19']
    
    return pivot.reset_index().sort_values(['중지역', '출루수_drop'])

def save_results(camp_metrics, demo_metrics, loc_metrics, deploy_zone_metrics):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    result_dir = os.path.join(base_dir, '../../../results/analysis_kickboard_down')
    os.makedirs(result_dir, exist_ok=True)
    result_path = os.path.join(result_dir, 'w19_w20_drop_analysis.xlsx')
    
    with pd.ExcelWriter(result_path, engine='openpyxl') as writer:
        camp_metrics.to_excel(writer, sheet_name='Camp_Metrics', index=False)
        demo_metrics.to_excel(writer, sheet_name='Demographics_Drop', index=False)
        loc_metrics.to_excel(writer, sheet_name='Location_Drop', index=False)
        if not deploy_zone_metrics.empty:
            deploy_zone_metrics.to_excel(writer, sheet_name='Deploy_Zone_Drop', index=False)
    print(f"Results saved to: {result_path}")
    
    # 시각화 저장
    plt.figure(figsize=(12, 6))
    sns.barplot(data=demo_metrics, x='camp_name', y='drop_count', hue='age_group')
    plt.title('W19 vs W20 Trip Drop Count by Age Group and Camp')
    plt.ylabel('Drop in Trip Count')
    plt.xlabel('Camp')
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, 'age_group_drop.png'))
    plt.close()

def main():
    set_korean_font()
    df = load_data()
    allocated_units = load_allocated_units()
    deploy_zone_df = load_deploy_zone_data()
    
    camp_metrics = analyze_camp_metrics(df, allocated_units)
    demo_metrics = analyze_demographics(df)
    loc_metrics = analyze_locations(df)
    deploy_zone_metrics = analyze_deploy_zone(deploy_zone_df)
    
    print("\n[Camp Level Analysis]")
    print(camp_metrics[['camp_name', 'trips_per_asset_W19', 'trips_per_asset_W20', 'revenue_per_asset_W19', 'revenue_per_asset_W20']])
    
    save_results(camp_metrics, demo_metrics, loc_metrics, deploy_zone_metrics)

if __name__ == '__main__':
    main()
