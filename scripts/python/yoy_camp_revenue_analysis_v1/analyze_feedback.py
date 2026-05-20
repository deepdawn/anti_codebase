import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

base_dir = os.path.dirname(os.path.abspath(__file__))
primary_data_dir = os.path.abspath(os.path.join(base_dir, '../../../base_data/primary_data/yoy_camp_revenue_analysis_v1'))
results_dir = os.path.abspath(os.path.join(base_dir, '../../../results/yoy_camp_revenue_analysis_v1'))
file_path = os.path.join(results_dir, 'YoY_Camp_Analysis.xlsx')

print("Loading data...")
orders_df = pd.read_excel(os.path.join(primary_data_dir, 'orders.xlsx'))
deployed_df = pd.read_excel(os.path.join(primary_data_dir, 'deployed.xlsx'))

def get_period(d):
    d = pd.to_datetime(d)
    if pd.Timestamp('2026-05-01') <= d <= pd.Timestamp('2026-05-18'):
        return 'CY'
    elif pd.Timestamp('2025-05-01') <= d <= pd.Timestamp('2025-05-18'):
        return 'PY'
    return None

orders_df['period_type'] = orders_df['period_type'].fillna('Unknown')
deployed_df['date'] = pd.to_datetime(deployed_df['date'])
deployed_df['period_type'] = deployed_df['date'].apply(get_period)

# -------------------------------------------------------------
# 1. 대구 캠프: 1건 당 매출, 평균 이용 거리
# -------------------------------------------------------------
daegu_camps = ['대구1캠프', '대구2캠프']
daegu_orders = orders_df[orders_df['camp_name'].isin(daegu_camps)].copy()

daegu_metrics = daegu_orders.groupby(['camp_name', 'period_type']).agg(
    avg_revenue_per_trip=('net_revenue_krw', 'mean'),
    avg_distance_per_trip=('distance', 'mean')
).reset_index()

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
sns.barplot(data=daegu_metrics, x='camp_name', y='avg_revenue_per_trip', hue='period_type', ax=axes[0], palette='Set2')
axes[0].set_title('대구 캠프 건당 평균 매출 (KRW)')
axes[0].set_ylabel('건당 매출 (KRW)')
axes[0].get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
for container in axes[0].containers:
    axes[0].bar_label(container, fmt='{:,.0f}', padding=3, fontsize=9)

sns.barplot(data=daegu_metrics, x='camp_name', y='avg_distance_per_trip', hue='period_type', ax=axes[1], palette='Set2')
axes[1].set_title('대구 캠프 건당 평균 이용 거리 (m)')
axes[1].set_ylabel('거리 (m)')
axes[1].get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
for container in axes[1].containers:
    axes[1].bar_label(container, fmt='{:,.0f}', padding=3, fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(results_dir, 'feedback_daegu.png'))
plt.close()

# -------------------------------------------------------------
# 2. 부산 캠프: 배치존 별 출루율 (배치수 대비 출루수)
# -------------------------------------------------------------
busan_camps = ['부산2캠프', '부산3캠프']
busan_deployed = deployed_df[deployed_df['중지역'].isin(busan_camps)].copy()
# Aggregate by zone and period
zone_agg = busan_deployed.groupby(['중지역', '배치존명', 'period_type'])[['배치수', '출루수']].sum().reset_index()
zone_agg['usage_rate'] = zone_agg['출루수'] / zone_agg['배치수'] * 100

# Plot density or boxplot of usage rates across zones
fig, axes = plt.subplots(1, 1, figsize=(8, 6))
sns.boxplot(data=zone_agg, x='중지역', y='usage_rate', hue='period_type', ax=axes, palette='Set2')
axes.set_title('부산 캠프 배치존 별 가동률(출루율) 분포')
axes.set_ylabel('출루율 (%)')
plt.tight_layout()
plt.savefig(os.path.join(results_dir, 'feedback_busan.png'))
plt.close()

# Save the list to the existing Excel file
with pd.ExcelWriter(file_path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
    zone_agg.sort_values(by=['중지역', 'usage_rate'], ascending=[True, False]).to_excel(writer, sheet_name='Busan_Zone_Usage', index=False)
print("Saved Busan_Zone_Usage to Excel.")

# -------------------------------------------------------------
# 3. 원주 캠프: 지표 심층 변화
# -------------------------------------------------------------
# Load summary YoY to extract Wonju metrics
yoy_summary = pd.read_excel(file_path, sheet_name='Raw_Summary')
wonju_metrics = yoy_summary[yoy_summary['camp_name'] == '원주캠프']

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
sns.barplot(data=wonju_metrics, x='period_type', y='Trips_per_Asset', ax=axes[0], palette='pastel')
axes[0].set_title('원주캠프 대당 회전수')
for container in axes[0].containers:
    axes[0].bar_label(container, fmt='{:,.1f}', padding=3, fontsize=9)

sns.barplot(data=wonju_metrics, x='period_type', y='Revenue_per_Trip', ax=axes[1], palette='pastel')
axes[1].set_title('원주캠프 건당 매출')
for container in axes[1].containers:
    axes[1].bar_label(container, fmt='{:,.0f}', padding=3, fontsize=9)

sns.barplot(data=wonju_metrics, x='period_type', y='Deployment_Usage_Rate(%)', ax=axes[2], palette='pastel')
axes[2].set_title('원주캠프 배치존 가동률(%)')
for container in axes[2].containers:
    axes[2].bar_label(container, fmt='{:,.1f}', padding=3, fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(results_dir, 'feedback_wonju.png'))
plt.close()

print("Feedback analysis plotting complete.")

# Print some hard numbers to the console for the walkthrough
print("=== DAEGU ===")
print(daegu_metrics)

print("=== WONJU ===")
print(wonju_metrics[['period_type', 'Trips_per_Asset', 'Revenue_per_Trip', 'Revenue_per_Asset', 'Deployment_Usage_Rate(%)']])

print("=== BUSAN ===")
# Zero usage zones count
zero_usage = zone_agg[zone_agg['usage_rate'] == 0].groupby(['중지역', 'period_type'])['배치존명'].count()
total_zones = zone_agg.groupby(['중지역', 'period_type'])['배치존명'].count()
print("Zero usage zones:\n", zero_usage)
print("Total zones:\n", total_zones)
