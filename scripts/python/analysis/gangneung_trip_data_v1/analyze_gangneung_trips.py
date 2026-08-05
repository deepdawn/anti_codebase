import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Mac 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

def safe_div(a, b):
    return np.where(b == 0, 0, a / b)

def analyze_gangneung():
    input_file = f'{os.path.expanduser("~")}/anti_codebase/base_data/secondary_data/gangneung_trip_data_v1/gangneung_trip_data_v1_processed.xlsx'
    output_dir = f'{os.path.expanduser("~")}/anti_codebase/results/gangneung_trip_data_v1/'
    os.makedirs(output_dir, exist_ok=True)
    
    print("Loading data...")
    df = pd.read_excel(input_file)
    
    print("Preprocessing data...")
    # 1. 외국인 및 unknown 연령 제외
    df = df[df['country_gubun'] != '외국인'].copy()
    df = df[df['age_group'] != 'unknown'].copy()
    
    # 2. 분석 모듈 1: 인구통계학적 세그먼트별 YoY 분석
    print("Running Module 1: Demographic YoY Analysis...")
    demo_grp = df.groupby(['year', 'age_group', 'one_category'])[['트립수', 'allocated_revenue', 'allocated_assigned_count']].sum().reset_index()
    
    demo_pivot = demo_grp.pivot_table(index=['age_group', 'one_category'], columns='year', values=['트립수', 'allocated_revenue', 'allocated_assigned_count']).reset_index()
    demo_pivot.columns = ['_'.join(map(str, col)).strip('_') for col in demo_pivot.columns.values]
    
    demo_pivot['trip_yoy'] = safe_div(demo_pivot['트립수_2026'] - demo_pivot['트립수_2025'], demo_pivot['트립수_2025'])
    demo_pivot['rev_yoy'] = safe_div(demo_pivot['allocated_revenue_2026'] - demo_pivot['allocated_revenue_2025'], demo_pivot['allocated_revenue_2025'])
    
    # 전체 YoY 관점 대당매출 추가 (부가세 제외: assigned_count * 1.1)
    demo_pivot['rev_per_asset_2025'] = safe_div(demo_pivot['allocated_revenue_2025'], demo_pivot['allocated_assigned_count_2025'] * 1.1)
    demo_pivot['rev_per_asset_2026'] = safe_div(demo_pivot['allocated_revenue_2026'], demo_pivot['allocated_assigned_count_2026'] * 1.1)
    demo_pivot['rev_per_asset_yoy'] = safe_div(demo_pivot['rev_per_asset_2026'] - demo_pivot['rev_per_asset_2025'], demo_pivot['rev_per_asset_2025'])
    
    # '16세 미만' 집중 분석 데이터
    under16_df = demo_pivot[demo_pivot['age_group'] == '16세 미만']
    
    # 3. 분석 모듈 2: 월별 기기/연령별 트립 수 추이 시각화
    print("Running Module 2: Monthly Trends Plotting...")
    monthly_grp = df.groupby(['year', 'month', 'one_category', 'age_group'])['트립수'].sum().reset_index()
    
    for category in ['Bicycle', 'Scooter']:
        plt.figure(figsize=(12, 6))
        cat_df = monthly_grp[(monthly_grp['one_category'] == category) & (monthly_grp['age_group'].isin(['16세 미만', '16~19세']))]
        ax = sns.lineplot(data=cat_df, x='month', y='트립수', hue='age_group', style='year', markers=True, dashes=False)
        
        # Add data labels
        for line in ax.lines:
            for x_val, y_val in zip(line.get_xdata(), line.get_ydata()):
                if pd.notna(y_val):
                    ax.annotate(f'{int(y_val):,}', xy=(x_val, y_val), xytext=(0, 5),
                                textcoords='offset points', ha='center', va='bottom', fontsize=8)
                                
        plt.title(f'Monthly Trips by Age Group (Teens) - {category}')
        plt.xlabel('Month')
        plt.ylabel('Total Trips')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'monthly_trips_{category.lower()}.png'))
        plt.close()
        
    # 4. 분석 모듈 3: 소지역별 전체 및 16세 미만 YoY 분석
    print("Running Module 3: Small Area YoY Analysis...")
    area_grp = df.groupby(['year', '소지역'])[['트립수', 'allocated_revenue', 'allocated_assigned_count']].sum().reset_index()
    area_pivot = area_grp.pivot_table(index='소지역', columns='year', values=['트립수', 'allocated_revenue', 'allocated_assigned_count']).reset_index()
    area_pivot.columns = ['_'.join(map(str, col)).strip('_') for col in area_pivot.columns.values]
    
    area_pivot['rev_per_asset_2025'] = safe_div(area_pivot['allocated_revenue_2025'], area_pivot['allocated_assigned_count_2025'] * 1.1)
    area_pivot['rev_per_asset_2026'] = safe_div(area_pivot['allocated_revenue_2026'], area_pivot['allocated_assigned_count_2026'] * 1.1)
    area_pivot['rev_per_asset_yoy'] = safe_div(area_pivot['rev_per_asset_2026'] - area_pivot['rev_per_asset_2025'], area_pivot['rev_per_asset_2025'])
    
    # 5. 분석 모듈 4: 25년/26년 기기별 세그먼트 파이 차트
    print("Running Module 4: Age Segment Distribution Pie Charts...")
    pie_grp = df.groupby(['year', 'one_category', 'age_group'])['트립수'].sum().reset_index()
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    for i, year in enumerate([2025, 2026]):
        for j, category in enumerate(['Bicycle', 'Scooter']):
            data = pie_grp[(pie_grp['year'] == year) & (pie_grp['one_category'] == category)]
            axes[i, j].pie(data['트립수'], labels=data['age_group'], autopct='%1.1f%%', startangle=90)
            axes[i, j].set_title(f'{year} {category} Trips Proportion')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'age_segment_proportions.png'))
    plt.close()
    
    # 6. 분석 모듈 5 & 6: 특이점(Anomaly) 탐지 및 시각화 (원본 통계 데이터 사용)
    print("Loading raw statistics data for accurate revenue analysis...")
    raw_stats_file = f'{os.path.expanduser("~")}/anti_codebase/base_data/primary_data/gangneung_trip_data_v1/redshift_rich_daily_statistics.xlsx'
    raw_stats_df = pd.read_excel(raw_stats_file)
    
    # 날짜 필터링 (2025년 1/1~5/13, 2026년 1/1~5/13)
    raw_stats_df['date'] = pd.to_datetime(raw_stats_df['date'])
    mask_2025 = (raw_stats_df['date'] >= '2025-01-01') & (raw_stats_df['date'] <= '2025-05-13')
    mask_2026 = (raw_stats_df['date'] >= '2026-01-01') & (raw_stats_df['date'] <= '2026-05-13')
    filtered_stats_df = raw_stats_df[mask_2025 | mask_2026].copy()
    filtered_stats_df['year'] = filtered_stats_df['date'].dt.year
    filtered_stats_df.rename(columns={'low_region_name': '소지역', 'vehicle_type': 'one_category'}, inplace=True)
    
    # --- Scooter Anomaly ---
    print("Running Module 5: Scooter Anomaly Detection (Raw Stats)...")
    scooter_stats = filtered_stats_df[filtered_stats_df['one_category'] == 'Scooter']
    scooter_area = scooter_stats.groupby(['year', '소지역'])[['revenue', 'assigned_count']].sum().reset_index()
    scooter_pivot = scooter_area.pivot_table(index='소지역', columns='year', values=['revenue', 'assigned_count']).reset_index()
    scooter_pivot.columns = ['_'.join(map(str, col)).strip('_') for col in scooter_pivot.columns.values]
    
    scooter_pivot['rev_per_asset_2025'] = safe_div(scooter_pivot['revenue_2025'], scooter_pivot['assigned_count_2025'] * 1.1)
    scooter_pivot['rev_per_asset_2026'] = safe_div(scooter_pivot['revenue_2026'], scooter_pivot['assigned_count_2026'] * 1.1)
    scooter_pivot['yoy_drop_pct'] = safe_div(scooter_pivot['rev_per_asset_2026'] - scooter_pivot['rev_per_asset_2025'], scooter_pivot['rev_per_asset_2025'])
    
    if not scooter_pivot.empty:
        plt.figure(figsize=(16, 6))
        plot_data = scooter_pivot[['소지역', 'rev_per_asset_2025', 'rev_per_asset_2026']].melt(id_vars='소지역', var_name='Year', value_name='Revenue per Asset')
        plot_data['Year'] = plot_data['Year'].apply(lambda x: '2025' if '2025' in x else '2026')
        
        ax = sns.barplot(data=plot_data, x='소지역', y='Revenue per Asset', hue='Year')
        
        for p in ax.patches:
            val = p.get_height()
            if pd.notna(val) and val > 0:
                ax.annotate(f'{int(val):,}', (p.get_x() + p.get_width() / 2., val),
                            ha='center', va='bottom', fontsize=8, xytext=(0, 3), textcoords='offset points')
                            
        plt.title('Scooter Revenue per Asset by Small Area (2025 vs 2026) - Raw Stats')
        plt.xlabel('Small Area')
        plt.ylabel('Revenue per Asset (KRW)')
        plt.xticks(rotation=45, ha='right')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'scooter_revenue_anomaly_drop.png'))
        plt.close()

    # --- Bicycle Anomaly ---
    print("Running Module 6: Bicycle Anomaly Detection (Raw Stats)...")
    bicycle_stats = filtered_stats_df[filtered_stats_df['one_category'] == 'Bicycle']
    bicycle_area = bicycle_stats.groupby(['year', '소지역'])[['revenue', 'assigned_count']].sum().reset_index()
    bicycle_pivot = bicycle_area.pivot_table(index='소지역', columns='year', values=['revenue', 'assigned_count']).reset_index()
    bicycle_pivot.columns = ['_'.join(map(str, col)).strip('_') for col in bicycle_pivot.columns.values]
    
    bicycle_pivot['rev_per_asset_2025'] = safe_div(bicycle_pivot['revenue_2025'], bicycle_pivot['assigned_count_2025'] * 1.1)
    bicycle_pivot['rev_per_asset_2026'] = safe_div(bicycle_pivot['revenue_2026'], bicycle_pivot['assigned_count_2026'] * 1.1)
    bicycle_pivot['yoy_drop_pct'] = safe_div(bicycle_pivot['rev_per_asset_2026'] - bicycle_pivot['rev_per_asset_2025'], bicycle_pivot['rev_per_asset_2025'])

    if not bicycle_pivot.empty:
        plt.figure(figsize=(16, 6))
        plot_data_bi = bicycle_pivot[['소지역', 'rev_per_asset_2025', 'rev_per_asset_2026']].melt(id_vars='소지역', var_name='Year', value_name='Revenue per Asset')
        plot_data_bi['Year'] = plot_data_bi['Year'].apply(lambda x: '2025' if '2025' in x else '2026')
        
        ax = sns.barplot(data=plot_data_bi, x='소지역', y='Revenue per Asset', hue='Year')
        
        for p in ax.patches:
            val = p.get_height()
            if pd.notna(val) and val > 0:
                ax.annotate(f'{int(val):,}', (p.get_x() + p.get_width() / 2., val),
                            ha='center', va='bottom', fontsize=8, xytext=(0, 3), textcoords='offset points')
                            
        plt.title('Bicycle Revenue per Asset by Small Area (2025 vs 2026) - Raw Stats')
        plt.xlabel('Small Area')
        plt.ylabel('Revenue per Asset (KRW)')
        plt.xticks(rotation=45, ha='right')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'bicycle_revenue_anomaly.png'))
        plt.close()

    # 7. 분석 모듈 7: 월별 기종별 대당 매출 라인 차트 (Raw Stats)
    print("Running Module 7: Monthly Revenue per Asset Line Chart (Raw Stats)...")
    filtered_stats_df['month'] = filtered_stats_df['date'].dt.month
    monthly_rev_grp = filtered_stats_df.groupby(['year', 'month', 'one_category'])[['revenue', 'assigned_count']].sum().reset_index()
    monthly_rev_grp['rev_per_asset'] = safe_div(monthly_rev_grp['revenue'], monthly_rev_grp['assigned_count'] * 1.1)
    
    for category in ['Bicycle', 'Scooter']:
        plt.figure(figsize=(10, 6))
        cat_df = monthly_rev_grp[monthly_rev_grp['one_category'] == category].copy()
        
        ax = sns.lineplot(data=cat_df, x='month', y='rev_per_asset', hue='year', style='year', markers=True, dashes=False, palette='Set2')
        
        # Add data labels
        for line in ax.lines:
            for x_val, y_val in zip(line.get_xdata(), line.get_ydata()):
                if pd.notna(y_val):
                    ax.annotate(f'{int(y_val):,}', xy=(x_val, y_val), xytext=(0, 5),
                                textcoords='offset points', ha='center', va='bottom', fontsize=8)
                                
        plt.title(f'Monthly Revenue per Asset (2025 vs 2026) - {category}')
        plt.xlabel('Month')
        plt.ylabel('Revenue per Asset (KRW, VAT excluded)')
        plt.xticks(sorted(cat_df['month'].unique()))
        
        # Only show legend once properly
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles=handles, labels=labels, title='Year')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'monthly_rev_per_asset_{category.lower()}.png'))
        plt.close()

    # 8. 결과 저장
    print("Saving summary tables...")
    with pd.ExcelWriter(os.path.join(output_dir, 'gangneung_analysis_summary.xlsx')) as writer:
        demo_pivot.to_excel(writer, sheet_name='Demographic_YoY', index=False)
        under16_df.to_excel(writer, sheet_name='Under_16_Focus', index=False)
        area_pivot.to_excel(writer, sheet_name='Small_Area_YoY', index=False)
        scooter_pivot.to_excel(writer, sheet_name='Scooter_Anomaly_Check', index=False)
        bicycle_pivot.to_excel(writer, sheet_name='Bicycle_Anomaly_Check', index=False)
        
    print("Analysis complete. Results saved in", output_dir)

if __name__ == '__main__':
    analyze_gangneung()
