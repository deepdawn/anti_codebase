import os
import pandas as pd
import numpy as np

base_dir = os.path.dirname(os.path.abspath(__file__))
primary_data_dir = os.path.abspath(os.path.join(base_dir, '../../../base_data/primary_data/yoy_camp_revenue_analysis_v1'))
secondary_data_dir = os.path.abspath(os.path.join(base_dir, '../../../base_data/secondary_data'))
results_dir = os.path.abspath(os.path.join(base_dir, '../../../results/yoy_camp_revenue_analysis_v1'))

os.makedirs(results_dir, exist_ok=True)

print("Loading data files...")
orders_df = pd.read_excel(os.path.join(primary_data_dir, 'orders.xlsx'))
deployed_df = pd.read_excel(os.path.join(primary_data_dir, 'deployed.xlsx'))
allocated_df = pd.read_excel(os.path.join(secondary_data_dir, 'daily allocated number per camp.xlsx'))

print("Processing Allocated Data...")
allocated_df['date'] = pd.to_datetime(allocated_df['date'])
allocated_df = allocated_df[allocated_df['기종'] == '킥보드']

def get_period(d):
    if pd.Timestamp('2026-05-01') <= d <= pd.Timestamp('2026-05-18'):
        return 'CY'
    elif pd.Timestamp('2025-05-01') <= d <= pd.Timestamp('2025-05-18'):
        return 'PY'
    return None

allocated_df['period_type'] = allocated_df['date'].apply(get_period)
allocated_df = allocated_df.dropna(subset=['period_type'])
allocated_agg = allocated_df.groupby(['period_type', 'middle_region_name'])['할당대수'].sum().reset_index()
allocated_agg.rename(columns={'middle_region_name': 'camp_name'}, inplace=True)

print("Processing Deployed Data...")
deployed_df['date'] = pd.to_datetime(deployed_df['date'])
deployed_df['period_type'] = deployed_df['date'].apply(get_period)
deployed_df = deployed_df.dropna(subset=['period_type'])
deployed_agg = deployed_df.groupby(['period_type', '중지역'])[['배치수', '출루수']].sum().reset_index()
deployed_agg.rename(columns={'중지역': 'camp_name'}, inplace=True)

print("Processing Orders Data...")
orders_agg = orders_df.groupby(['period_type', 'camp_name']).agg(
    total_revenue=('net_revenue_krw', 'sum'),
    total_trips=('order_id', 'count')
).reset_index()

print("Merging Camp-level Summary...")
summary = pd.merge(orders_agg, allocated_agg, on=['period_type', 'camp_name'], how='left')
summary = pd.merge(summary, deployed_agg, on=['period_type', 'camp_name'], how='left')

# Calculate derived metrics
summary['Revenue_per_Asset'] = summary['total_revenue'] / summary['할당대수']
summary['Trips_per_Asset'] = summary['total_trips'] / summary['할당대수']
summary['Revenue_per_Trip'] = summary['total_revenue'] / summary['total_trips']
summary['Deployment_Usage_Rate(%)'] = (summary['출루수'] / summary['배치수']) * 100

# Demographics Analysis
demo_agg = orders_df.groupby(['period_type', 'camp_name', 'age_group', 'gender']).agg(
    revenue=('net_revenue_krw', 'sum'),
    trips=('order_id', 'count')
).reset_index()

# Time Analysis
time_agg = orders_df.groupby(['period_type', 'camp_name', 'day_type', 'hour_band']).agg(
    revenue=('net_revenue_krw', 'sum'),
    trips=('order_id', 'count')
).reset_index()

# Pivot Summary for YoY Comparison
pivot_summary = summary.pivot(index='camp_name', columns='period_type', 
                              values=['total_revenue', '할당대수', '배치수', '출루수', 'Revenue_per_Asset', 'Trips_per_Asset', 'Deployment_Usage_Rate(%)'])
pivot_summary.columns = [f"{col[0]}_{col[1]}" for col in pivot_summary.columns]
for metric in ['total_revenue', '할당대수', 'Revenue_per_Asset', 'Trips_per_Asset', 'Deployment_Usage_Rate(%)']:
    if f'{metric}_CY' in pivot_summary.columns and f'{metric}_PY' in pivot_summary.columns:
        pivot_summary[f'{metric}_YoY_Growth(%)'] = ((pivot_summary[f'{metric}_CY'] - pivot_summary[f'{metric}_PY']) / pivot_summary[f'{metric}_PY']) * 100

print("Saving Results...")
output_path = os.path.join(results_dir, 'YoY_Camp_Analysis.xlsx')
with pd.ExcelWriter(output_path) as writer:
    summary.to_excel(writer, sheet_name='Raw_Summary', index=False)
    pivot_summary.reset_index().to_excel(writer, sheet_name='YoY_Summary', index=False)
    demo_agg.to_excel(writer, sheet_name='Demographics', index=False)
    time_agg.to_excel(writer, sheet_name='Time_Bands', index=False)

print(f"Analysis saved to: {output_path}")
