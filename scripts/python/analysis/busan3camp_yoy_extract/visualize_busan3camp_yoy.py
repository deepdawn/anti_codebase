import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib.ticker as ticker

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
    input_path = os.path.join(base_dir, 'results/busan3camp_yoy_extract/busan3camp_analyzed.xlsx')
    output_img_path = os.path.join(base_dir, 'results/busan3camp_yoy_extract/weekly_revenue_trend.png')
    output_summary_path = os.path.join(base_dir, 'results/busan3camp_yoy_extract/busan3camp_summary.xlsx')
    
    # Ensure output dir exists
    os.makedirs(os.path.dirname(output_img_path), exist_ok=True)
    
    # Load data
    df = pd.read_excel(input_path)
    
    # 0. Filter out rows where assigned_count is null or empty
    df = df.dropna(subset=['assigned_count'])
    df = df[df['assigned_count'] != '']
    
    # Pre-extract year and month
    df['year'] = df['month_str'].str.slice(0, 4)
    df['month'] = df['month_str'].str.slice(5, 7)
    df['week_year'] = df['week_str'].str.slice(0, 4)
    df['week_num'] = df['week_str'].str.slice(6, 8).astype(int)
    
    # 1. Monthly YoY Comparison
    monthly_summary = df.groupby(['year', 'month'])[['revenue_per_asset', 'trips_per_asset']].mean().reset_index()
    
    # 2. Notable Fluctuation Analysis (Common Small Areas)
    areas_2025 = set(df[df['year'] == '2025']['small_area'].unique())
    areas_2026 = set(df[df['year'] == '2026']['small_area'].unique())
    common_areas = areas_2025.intersection(areas_2026)
    
    # Filter for common areas
    df_common = df[df['small_area'].isin(common_areas)]
    
    # Calculate weekly revenue per asset for each small area
    weekly_area_summary = df_common.groupby(['small_area', 'week_str'])['revenue_per_asset'].mean().reset_index()
    
    # Calculate fluctuation (Std Dev and Max-Min difference) per small area
    fluctuation_df = weekly_area_summary.groupby('small_area')['revenue_per_asset'].agg(['std', 'mean', 'max', 'min']).reset_index()
    fluctuation_df['max_min_diff'] = fluctuation_df['max'] - fluctuation_df['min']
    
    # Sort by Std Dev to find the most volatile areas
    volatile_areas = fluctuation_df.sort_values(by='std', ascending=False).head(10)
    
    # Save both summaries to a single Excel file with multiple tabs
    with pd.ExcelWriter(output_summary_path) as writer:
        monthly_summary.to_excel(writer, sheet_name='Monthly_Summary', index=False)
        volatile_areas.to_excel(writer, sheet_name='Volatile_Small_Areas', index=False)
    print("Summaries saved to Excel with multiple tabs.")
    
    # 3. Weekly Trend Line Chart (Excludes null assigned_count as df was filtered in step 0)
    weekly_summary = df.groupby(['week_year', 'week_num'])['revenue_per_asset'].mean().reset_index()
    
    plt.figure(figsize=(12, 6))
    
    # Filter and plot 2025 (Red)
    df_2025 = weekly_summary[weekly_summary['week_year'] == '2025'].sort_values('week_num')
    plt.plot(df_2025['week_num'], df_2025['revenue_per_asset'], marker='o', color='red', label='2025', linewidth=2)
    
    # Add data labels for 2025
    for x, y in zip(df_2025['week_num'], df_2025['revenue_per_asset']):
        plt.text(x, y + 100, f'{y:,.0f}', color='red', ha='center', va='bottom', fontsize=9)
        
    # Filter and plot 2026 (Blue)
    df_2026 = weekly_summary[weekly_summary['week_year'] == '2026'].sort_values('week_num')
    plt.plot(df_2026['week_num'], df_2026['revenue_per_asset'], marker='o', color='blue', label='2026', linewidth=2)
    
    # Add data labels for 2026
    for x, y in zip(df_2026['week_num'], df_2026['revenue_per_asset']):
        plt.text(x, y - 100, f'{y:,.0f}', color='blue', ha='center', va='top', fontsize=9)
    
    # Formatting
    plt.title('Weekly Revenue per Asset (YoY Comparison)', fontsize=14, pad=20)
    plt.xlabel('Week Number', fontsize=12)
    plt.ylabel('Revenue per Asset (KRW)', fontsize=12)
    
    # Y-axis format (#,##0)
    plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    
    plt.xticks(range(1, 22))  # Assuming up to week 21
    plt.legend(title='Year')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    plt.savefig(output_img_path, dpi=300)
    print(f"Chart saved to {output_img_path}")

if __name__ == '__main__':
    main()
