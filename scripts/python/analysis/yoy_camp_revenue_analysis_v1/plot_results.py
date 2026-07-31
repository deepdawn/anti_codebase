import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Korean font support for Mac
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

base_dir = os.path.dirname(os.path.abspath(__file__))
results_dir = os.path.abspath(os.path.join(base_dir, '../../../results/yoy_camp_revenue_analysis_v1'))
file_path = os.path.join(results_dir, 'YoY_Camp_Analysis.xlsx')

print("Loading data...")
demo_df = pd.read_excel(file_path, sheet_name='Demographics')
time_df = pd.read_excel(file_path, sheet_name='Time_Bands')

camps = sorted(demo_df['camp_name'].unique())

def plot_yoy_subplots(df, x_col, y_col, hue_col, filename, title_prefix, order=None):
    fig, axes = plt.subplots(1, 5, figsize=(25, 5), sharey=True)
    fig.suptitle(f"{title_prefix} YoY 매출 변화", fontsize=20, fontweight='bold', y=1.05)
    
    for i, camp in enumerate(camps):
        camp_data = df[df['camp_name'] == camp]
        if order is None:
            local_order = sorted(camp_data[x_col].unique())
        else:
            local_order = order
            
        sns.barplot(data=camp_data, x=x_col, y=y_col, hue=hue_col, ax=axes[i], order=local_order, palette='Set2')
        axes[i].set_title(camp, fontsize=15)
        axes[i].set_xlabel('')
        axes[i].set_ylabel('매출 (KRW)' if i == 0 else '')
        axes[i].tick_params(axis='x', rotation=45)
        
        # Add bar labels
        for container in axes[i].containers:
            axes[i].bar_label(container, fmt='{:,.0f}', padding=3, fontsize=9)
            
        # Format y axis
        axes[i].get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))

    plt.tight_layout()
    out_path = os.path.join(results_dir, filename)
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"Saved {filename}")

# 1. Demographics (Age Group)
age_agg = demo_df.groupby(['camp_name', 'period_type', 'age_group'])['revenue'].sum().reset_index()
age_order = ['10대', '20대', '30대', '40대', '50대', '알수없음', '기타']
plot_yoy_subplots(age_agg, 'age_group', 'revenue', 'period_type', 'demographics_age_yoy.png', '연령대별', order=age_order)

# 2. Demographics (Gender)
gender_agg = demo_df.groupby(['camp_name', 'period_type', 'gender'])['revenue'].sum().reset_index()
plot_yoy_subplots(gender_agg, 'gender', 'revenue', 'period_type', 'demographics_gender_yoy.png', '성별')

# 3. Time (Day Type)
day_agg = time_df.groupby(['camp_name', 'period_type', 'day_type'])['revenue'].sum().reset_index()
plot_yoy_subplots(day_agg, 'day_type', 'revenue', 'period_type', 'time_daytype_yoy.png', '평일/주말')

# 4. Time (Hour Band)
hour_agg = time_df.groupby(['camp_name', 'period_type', 'hour_band'])['revenue'].sum().reset_index()
hour_order = ['00-05', '06-10', '11-16', '17-21', '22-23']
plot_yoy_subplots(hour_agg, 'hour_band', 'revenue', 'period_type', 'time_hourband_yoy.png', '시간대별', order=hour_order)

print("Plotting complete.")
