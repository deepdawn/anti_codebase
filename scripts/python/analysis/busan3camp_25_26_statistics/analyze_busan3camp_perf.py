import pandas as pd
import matplotlib.pyplot as plt
import os
import matplotlib.ticker as ticker

# 한글 폰트 설정 (Mac OS)
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False

def main():
    base_dir = '/Users/galaxy/anti_codebase'
    input_path = os.path.join(base_dir, 'base_data/secondary_data/260526_busan3camp_assigned_vehicle.xlsx')
    output_dir = os.path.join(base_dir, 'results/busan3camp_25_26_statistics')
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading data from {input_path}...")
    df = pd.read_excel(input_path)
    
    df = df.dropna(subset=['assigned_count'])
    df = df[df['assigned_count'] != '']
    df['assigned_count'] = pd.to_numeric(df['assigned_count'], errors='coerce')
    df = df.dropna(subset=['assigned_count'])
    
    df['revenue'] = df['revenue'].fillna(0)
    df['trip_count'] = df['trip_count'].fillna(0)
    
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.strftime('%Y')
    df['month'] = df['date'].dt.strftime('%Y-%m')
    
    iso_cal = df['date'].dt.isocalendar()
    df['week_year'] = iso_cal.year.astype(str)
    df['week_num'] = iso_cal.week
    
    print("Calculating monthly metrics...")
    monthly_agg = df.groupby(['year', 'month']).agg({
        'revenue': 'sum',
        'trip_count': 'sum',
        'assigned_count': 'sum'
    }).reset_index()
    monthly_agg['revenue_per_asset'] = monthly_agg['revenue'] / (monthly_agg['assigned_count'] * 1.1)
    monthly_agg['trips_per_asset'] = monthly_agg['trip_count'] / monthly_agg['assigned_count']
    
    print("Calculating weekly metrics...")
    weekly_agg = df.groupby(['week_year', 'week_num']).agg({
        'revenue': 'sum',
        'trip_count': 'sum',
        'assigned_count': 'sum'
    }).reset_index()
    weekly_agg['revenue_per_asset'] = weekly_agg['revenue'] / (weekly_agg['assigned_count'] * 1.1)
    weekly_agg['trips_per_asset'] = weekly_agg['trip_count'] / weekly_agg['assigned_count']
    
    print("Calculating small area weekly metrics...")
    small_area_weekly = df.groupby(['low_region_name', 'week_year', 'week_num']).agg({
        'revenue': 'sum',
        'trip_count': 'sum',
        'assigned_count': 'sum'
    }).reset_index()
    small_area_weekly['revenue_per_asset'] = small_area_weekly['revenue'] / (small_area_weekly['assigned_count'] * 1.1)
    
    max_week = df['week_num'].max()
    if pd.isna(max_week):
        max_week = 21

    def plot_chart(data, title, filename):
        plt.figure(figsize=(12, 6))
        
        df_2025 = data[data['week_year'] == '2025'].sort_values('week_num')
        if not df_2025.empty:
            plt.plot(df_2025['week_num'], df_2025['revenue_per_asset'], marker='o', color='red', label='2025', linewidth=2)
            for x, y in zip(df_2025['week_num'], df_2025['revenue_per_asset']):
                plt.text(x, y + 150, f'{y:,.0f}', color='red', ha='center', va='bottom', fontsize=9)
            
        df_2026 = data[data['week_year'] == '2026'].sort_values('week_num')
        if not df_2026.empty:
            plt.plot(df_2026['week_num'], df_2026['revenue_per_asset'], marker='o', color='blue', label='2026', linewidth=2)
            for x, y in zip(df_2026['week_num'], df_2026['revenue_per_asset']):
                plt.text(x, y - 150, f'{y:,.0f}', color='blue', ha='center', va='top', fontsize=9)
            
        plt.title(title, fontsize=14, pad=20)
        plt.xlabel('Week Number (ISO)', fontsize=12)
        plt.ylabel('Revenue per Asset (KRW)', fontsize=12)
        plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        plt.xticks(range(1, int(max(max_week, 21)) + 1))
        plt.legend(title='Year')
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=300)
        plt.close()
        return filepath

    # Plot overall revenue trend
    rev_chart_path = plot_chart(weekly_agg, 'Weekly Revenue per Asset (YoY Comparison) - Overall', 'weekly_revenue_per_asset_trend.png')
    
    # Generate charts for each small area
    print("Generating charts for small areas...")
    small_areas = small_area_weekly['low_region_name'].unique()
    small_area_chart_paths = []
    
    charts_dir = os.path.join(output_dir, 'small_area_charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    for area in small_areas:
        area_data = small_area_weekly[small_area_weekly['low_region_name'] == area]
        safe_area_name = str(area).replace('/', '_').replace('\\', '_')
        filepath = plot_chart(area_data, f'Weekly Revenue per Asset (YoY) - {area}', f'small_area_charts/{safe_area_name}_revenue_trend.png')
        small_area_chart_paths.append((area, filepath))

    # Plot Trips per Asset (overall)
    plt.figure(figsize=(12, 6))
    df_2025_trip = weekly_agg[weekly_agg['week_year'] == '2025'].sort_values('week_num')
    if not df_2025_trip.empty:
        plt.plot(df_2025_trip['week_num'], df_2025_trip['trips_per_asset'], marker='o', color='red', label='2025', linewidth=2)
        for x, y in zip(df_2025_trip['week_num'], df_2025_trip['trips_per_asset']):
            plt.text(x, y + 0.05, f'{y:.2f}', color='red', ha='center', va='bottom', fontsize=9)
            
    df_2026_trip = weekly_agg[weekly_agg['week_year'] == '2026'].sort_values('week_num')
    if not df_2026_trip.empty:
        plt.plot(df_2026_trip['week_num'], df_2026_trip['trips_per_asset'], marker='o', color='blue', label='2026', linewidth=2)
        for x, y in zip(df_2026_trip['week_num'], df_2026_trip['trips_per_asset']):
            plt.text(x, y - 0.05, f'{y:.2f}', color='blue', ha='center', va='top', fontsize=9)
            
    plt.title('Weekly Trips per Asset (YoY Comparison)', fontsize=14, pad=20)
    plt.xlabel('Week Number (ISO)', fontsize=12)
    plt.ylabel('Trips per Asset', fontsize=12)
    plt.xticks(range(1, int(max(max_week, 21)) + 1))
    plt.legend(title='Year')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    trips_chart_path = os.path.join(output_dir, 'weekly_trips_per_asset_trend.png')
    plt.savefig(trips_chart_path, dpi=300)
    plt.close()

    # Save to Excel and insert images
    summary_excel_path = os.path.join(output_dir, 'busan3camp_metrics_summary.xlsx')
    print(f"Saving summary and embedding charts to {summary_excel_path}...")
    
    try:
        with pd.ExcelWriter(summary_excel_path, engine='xlsxwriter') as writer:
            monthly_agg.to_excel(writer, sheet_name='Monthly_Summary', index=False)
            weekly_agg.to_excel(writer, sheet_name='Weekly_Summary', index=False)
            
            # Insert Overall Chart
            worksheet_weekly = writer.sheets['Weekly_Summary']
            worksheet_weekly.insert_image('G2', rev_chart_path, {'x_scale': 0.6, 'y_scale': 0.6})
            
            # Create new sheet for Small Area Charts
            worksheet_small_areas = writer.book.add_worksheet('Small_Area_Charts')
            
            row = 2
            for i, (area, img_path) in enumerate(small_area_chart_paths):
                worksheet_small_areas.write(row - 1, 1, area)
                worksheet_small_areas.insert_image(row, 1, img_path, {'x_scale': 0.6, 'y_scale': 0.6})
                row += 20  # Add space between charts
    except ImportError:
        print("xlsxwriter not found. Please pip install xlsxwriter to embed charts. Saving without charts...")
        with pd.ExcelWriter(summary_excel_path) as writer:
            monthly_agg.to_excel(writer, sheet_name='Monthly_Summary', index=False)
            weekly_agg.to_excel(writer, sheet_name='Weekly_Summary', index=False)
            
    print("Analysis and visualization completed successfully.")

if __name__ == '__main__':
    main()
