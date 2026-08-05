import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from statsmodels.tsa.holtwinters import ExponentialSmoothing

def main():
    result_dir = f"{os.path.expanduser('~')}/anti_codebase/results/JejuExtractTripData"
    data_file = os.path.join(result_dir, "20250101_20260430_jeju_camp_external_users.xlsx")
    
    # 1. Load Data
    print("[1/3] Loading Data...")
    try:
        df = pd.read_excel(data_file)
    except FileNotFoundError:
        print(f"Data file not found at {data_file}. Please ensure extraction is complete.")
        return

    # Create 3 Groups mapping based on regist_gubun and country_gubun
    def get_user_segment(row):
        if row['regist_gubun'] == '제주 가입자':
            return 'Jeju Local'
        elif row['country_gubun'] == '내국인':
            return 'Domestic Tourist'
        else:
            return 'Foreign Tourist'
            
    df['User_Segment'] = df.apply(get_user_segment, axis=1)

    # 2. Key Insights Generation (Head-First)
    print("\n" + "="*50)
    print("====== HEAD-FIRST: JEJU CAMP INSIGHTS ======")
    print("="*50)
    
    total_trips = df['트립수'].sum()
    total_revenue = df['합계결제금액'].sum()
    total_users = df['유저수_중복제거'].sum()
    
    segment_stats = df.groupby('User_Segment')[['트립수', '합계결제금액', '유저수_중복제거']].sum().reset_index()
    segment_stats['Trip_Share(%)'] = (segment_stats['트립수'] / total_trips * 100).round(1)
    segment_stats['Revenue_Share(%)'] = (segment_stats['합계결제금액'] / total_revenue * 100).round(1)
    segment_stats['User_Share(%)'] = (segment_stats['유저수_중복제거'] / total_users * 100).round(1)
    
    print("\n[Overview: Jeju Locals vs Domestic Tourists vs Foreign Tourists]")
    print(segment_stats.to_string(index=False))
    
    print("="*50 + "\n")
    
    # 3. Visualizations
    print("[2/3] Generating Visualizations...")
    
    # Set plotting style
    plt.style.use('ggplot')
    plt.rc('font', family='AppleGothic')
    plt.rcParams['axes.unicode_minus'] = False
    segment_colors = {'Jeju Local': '#3498db', 'Domestic Tourist': '#2ecc71', 'Foreign Tourist': '#e74c3c'}
    
    # Vis 1: Share of Trips, Revenue, and Users by User Segment
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    
    axes[0].pie(segment_stats['트립수'], labels=segment_stats['User_Segment'], autopct='%1.1f%%', 
                colors=[segment_colors[x] for x in segment_stats['User_Segment']])
    axes[0].set_title('Trip Share by User Segment')
    
    axes[1].pie(segment_stats['합계결제금액'], labels=segment_stats['User_Segment'], autopct='%1.1f%%', 
                colors=[segment_colors[x] for x in segment_stats['User_Segment']])
    axes[1].set_title('Revenue Share by User Segment')
    
    axes[2].pie(segment_stats['유저수_중복제거'], labels=segment_stats['User_Segment'], autopct='%1.1f%%', 
                colors=[segment_colors[x] for x in segment_stats['User_Segment']])
    axes[2].set_title('User (DAU sum) Share by User Segment')
    
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, '1_user_segment_share.png'))
    plt.close()
    
    # Vis 2: Demographics of Tourist Groups (Domestic vs Foreign)
    plt.figure(figsize=(12, 6))
    
    gender_eng_map = {'남자': 'Male', '여자': 'Female', 'unknown': 'Unknown'}
    age_eng_map = {'10대': '10s', '20대': '20s', '30대': '30s', '40대': '40s', '50대': '50s', '기타': 'Others', 'unknown': 'Unknown'}
    
    plot_df = df[df['User_Segment'].isin(['Domestic Tourist', 'Foreign Tourist'])].copy()
    plot_df['Gender'] = plot_df['gender'].map(gender_eng_map).fillna(plot_df['gender'])
    plot_df['Age_Group'] = plot_df['age_group'].map(age_eng_map).fillna(plot_df['age_group'])
    
    demo_agg = plot_df.groupby(['User_Segment', 'Age_Group', 'Gender'])['트립수'].sum().reset_index()
    
    g = sns.catplot(data=demo_agg, x='Age_Group', y='트립수', hue='Gender', col='User_Segment', 
                kind='bar', palette='viridis', order=['10s', '20s', '30s', '40s', '50s', 'Others', 'Unknown'], height=5, aspect=1.2)
    g.set_axis_labels('Age Group', 'Total Trips')
    
    for ax in g.axes.flat:
        for container in ax.containers:
            ax.bar_label(container, labels=[f"{x:,.0f}" if x > 0 else "" for x in container.datavalues], label_type='edge', fontsize=8, padding=2)
    
    plt.suptitle('Demographics of Tourists (Trips by Age & Gender)', y=1.05)
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, '2_tourist_demographics.png'))
    plt.close('all')
    
    # Vis 3: Bike Category Preferences
    plt.figure(figsize=(10, 6))
    cat_agg = df.groupby(['User_Segment', 'one_category'])['트립수'].sum().reset_index()
    
    # Normalize to 100% within each segment
    cat_totals = cat_agg.groupby('User_Segment')['트립수'].transform('sum')
    cat_agg['Percentage'] = (cat_agg['트립수'] / cat_totals) * 100
    
    ax = sns.barplot(data=cat_agg, x='User_Segment', y='Percentage', hue='one_category', palette='Set2')
    plt.title('Vehicle Category Preference by User Segment')
    plt.ylabel('Percentage of Trips (%)')
    plt.xlabel('User Segment')
    
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f%%', label_type='edge', fontsize=9, padding=2)
    plt.legend(title='Category')
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, '3_category_preference.png'))
    plt.close()

    # Vis 4: Monthly Trip Trend (Seasonality)
    plt.figure(figsize=(14, 7))
    
    df['dt'] = pd.to_datetime(df['dt'])
    df['is_weekend'] = df['dt'].dt.dayofweek >= 5
    df['Day_Type'] = df['is_weekend'].map({False: 'Weekday', True: 'Weekend'})
    df['Group'] = df['User_Segment'] + ' - ' + df['Day_Type']
    
    trend_df = df.groupby(['month', 'User_Segment'])['트립수'].mean().reset_index()

    ax = sns.lineplot(data=trend_df, x='month', y='트립수', hue='User_Segment', marker='o', 
                      palette=segment_colors, linewidth=2.5)
                 
    for index, row in trend_df.iterrows():
        plt.text(row['month'], row['트립수'], f"{row['트립수']:.1f}", color='black', ha='center', va='bottom', fontsize=8)
                 
    plt.title('Monthly Trip Trend by User Segment (Average Daily Trips)')
    plt.xlabel('Month (YYYY-MM)')
    plt.ylabel('Average Daily Trips')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, '4_monthly_trip_trend.png'))
    plt.close()
    
    # Vis 4-1: Monthly Trip Trend (6 segments: User Segment x Weekday/Weekend)
    plt.figure(figsize=(14, 7))
    
    trend_6seg_df = df.groupby(['month', 'Group'])['트립수'].mean().reset_index()
    
    # Create a custom palette for the 6 segments to distinguish them easily
    palette_6seg = {
        'Jeju Local - Weekday': '#3498db', 'Jeju Local - Weekend': '#2980b9',
        'Domestic Tourist - Weekday': '#2ecc71', 'Domestic Tourist - Weekend': '#27ae60',
        'Foreign Tourist - Weekday': '#e74c3c', 'Foreign Tourist - Weekend': '#c0392b'
    }
    
    ax = sns.lineplot(data=trend_6seg_df, x='month', y='트립수', hue='Group', style='Group',
                 markers=True, dashes=False, palette=palette_6seg, linewidth=2)
                 
    for index, row in trend_6seg_df.iterrows():
        plt.text(row['month'], row['트립수'], f"{row['트립수']:.1f}", color='black', ha='center', va='bottom', fontsize=7)
    plt.title('Monthly Trip Trend by 6 Segments (Weekday/Weekend)')
    plt.xlabel('Month (YYYY-MM)')
    plt.ylabel('Average Daily Trips')
    plt.xticks(rotation=45)
    plt.legend(title='Segment (Group - Day)', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, '4-1_monthly_trip_trend_6segments.png'))
    plt.close()
    
    # Vis 5: Time Series Forecasting (Holt-Winters) for all External (Tourists)
    print("\n[3/4] Forecasting Future Trips (Tourists)...")
    try:
        tourist_df = df[df['User_Segment'].isin(['Domestic Tourist', 'Foreign Tourist'])]
        total_monthly = tourist_df.groupby('month')['트립수'].sum().reset_index()
        total_monthly['month'] = pd.to_datetime(total_monthly['month'] + '-01')
        total_monthly = total_monthly.set_index('month')
        
        # Train Holt-Winters Model
        # Using seasonal_periods=12 with 16 data points can sometimes fail heuristic init. We will catch it.
        try:
            model = ExponentialSmoothing(total_monthly['트립수'], trend='add', seasonal='add', seasonal_periods=12, initialization_method="legacy-heuristic")
            fit_model = model.fit()
            forecast = fit_model.forecast(8)
        except ValueError:
            # Fallback to simple seasonal naive
            y2025_q1 = total_monthly.loc['2025-01-01':'2025-04-01', '트립수'].sum()
            y2026_q1 = total_monthly.loc['2026-01-01':'2026-04-01', '트립수'].sum()
            growth_rate = y2026_q1 / y2025_q1 if y2025_q1 > 0 else 1.0
            
            forecast_dates = pd.date_range(start='2026-05-01', end='2026-12-01', freq='MS')
            forecast_values = []
            for d in forecast_dates:
                past_month = d.replace(year=2025)
                if past_month in total_monthly.index:
                    val = total_monthly.loc[past_month, '트립수'] * growth_rate
                else:
                    val = total_monthly['트립수'].mean()
                forecast_values.append(val)
            forecast = pd.Series(forecast_values, index=forecast_dates)
            
        forecast_dates = pd.date_range(start='2026-05-01', end='2026-12-01', freq='MS')
        forecast.index = forecast_dates
        
        plt.figure(figsize=(10, 6))
        plt.plot(total_monthly.index, total_monthly['트립수'], marker='o', label='Actual Trips (2025.01 - 2026.04)', color='#2c3e50')
        plt.plot(forecast.index, forecast, marker='s', linestyle='--', label='Forecasted Trips (2026.05 - 2026.12)', color='#e74c3c')
        
        for d, val in zip(forecast.index, forecast):
            plt.text(d, val, f"{val/1000:.1f}k", color='#e74c3c', ha='center', va='bottom', fontsize=8)
            
        plt.title('Total Tourist Trip Forecast (Holt-Winters Method)')
        plt.xlabel('Date')
        plt.ylabel('Total Trips')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(result_dir, '5_forecast_trip_trend.png'))
        plt.close()
    except Exception as e:
        print(f"Forecasting failed: {e}")
        
    # Vis 6 & 7: Pricing Simulation
    print("\n[4/4] Running Pricing Simulation for Tourists on Peak Season Weekends...")
    try:
        peak_months = ['05', '09', '10']
        df['month_num'] = df['month'].str.split('-').str[1]
        
        target_mask = (df['User_Segment'].isin(['Domestic Tourist', 'Foreign Tourist'])) & (df['month_num'].isin(peak_months)) & (df['is_weekend'] == True)
        target_df = df[target_mask].copy()
        
        if len(target_df) > 0:
            total_trips = target_df['트립수'].sum()
            total_mins = target_df['합계운행시간(분)'].sum()
            current_revenue = target_df['합계결제금액'].sum()
            
            # Scenario A: Daytime Care +400, Per-min +20
            add_rev_A_minute = total_mins * 20
            add_rev_A_care = total_trips * 400 * 0.7
            total_add_A = add_rev_A_minute + add_rev_A_care
            rate_A = (total_add_A / current_revenue) * 100 if current_revenue > 0 else 0
            
            # Scenario B: Nighttime Care +200, Per-min unchanged
            add_rev_B_care = total_trips * 200 * 0.3
            total_add_B = add_rev_B_care
            rate_B = (total_add_B / current_revenue) * 100 if current_revenue > 0 else 0
            
            # Combined
            total_add_combined = total_add_A + total_add_B
            rate_combined = (total_add_combined / current_revenue) * 100 if current_revenue > 0 else 0
            
            print(f"\nTarget Trips (Domestic/Foreign Tourists, Peak Weekends): {total_trips:,.0f} trips")
            print(f"Current Revenue: ₩{current_revenue:,.0f}\n")
            
            monthly_sim = target_df.groupby('month').agg(
                Current_Revenue=('합계결제금액', 'sum'),
                Trip_Mins=('합계운행시간(분)', 'sum'),
                Trips=('트립수', 'sum')
            ).reset_index()
            
            monthly_sim['Scenario_A'] = monthly_sim['Current_Revenue'] + (monthly_sim['Trip_Mins'] * 20) + (monthly_sim['Trips'] * 400 * 0.7)
            monthly_sim['Scenario_B'] = monthly_sim['Current_Revenue'] + (monthly_sim['Trips'] * 200 * 0.3)
            monthly_sim['Combined'] = monthly_sim['Current_Revenue'] + (monthly_sim['Trip_Mins'] * 20) + (monthly_sim['Trips'] * 400 * 0.7) + (monthly_sim['Trips'] * 200 * 0.3)
            
            plot_df = monthly_sim.melt(id_vars='month', 
                                       value_vars=['Current_Revenue', 'Scenario_A', 'Scenario_B', 'Combined'], 
                                       var_name='Scenario', value_name='Revenue')
            label_map = {
                'Current_Revenue': 'Current',
                'Scenario_A': 'A: Day Care+400 & Min+20',
                'Scenario_B': 'B: Night Care+200',
                'Combined': 'A+B Combined'
            }
            plot_df['Scenario'] = plot_df['Scenario'].map(label_map)
            
            plt.figure(figsize=(12, 6))
            ax5 = sns.barplot(data=plot_df, x='month', y='Revenue', hue='Scenario', 
                              palette=['#95a5a6', '#e74c3c', '#f39c12', '#2ecc71'])
            
            for p in ax5.patches:
                val = p.get_height()
                if val > 0:
                    ax5.annotate(f"₩{val/1000000:,.1f}M", (p.get_x() + p.get_width() / 2., p.get_height()), 
                                 ha='center', va='bottom', fontsize=7, color='black', xytext=(0, 2), textcoords='offset points')
                    
            plt.title('Pricing Simulation: Peak Season Weekends (Tourists)')
            plt.xlabel('Peak Month')
            plt.ylabel('Revenue (Won)')
            plt.legend(title='Pricing Scenario', fontsize=8)
            plt.grid(axis='y')
            plt.tight_layout()
            plt.savefig(os.path.join(result_dir, '6_price_simulation_effect.png'))
            plt.close()
            
            categories = ['Current\nRevenue', 'A: Per-min\n(+20/min)', 'A: Day Care\n(+400)', 'B: Night Care\n(+200)', 'Total\nSimulated']
            values = [current_revenue, add_rev_A_minute, add_rev_A_care, add_rev_B_care, current_revenue + total_add_combined]
            colors = ['#95a5a6', '#e74c3c', '#e74c3c', '#f39c12', '#2ecc71']
            
            plt.figure(figsize=(10, 6))
            bars = plt.bar(categories, values, color=colors, edgecolor='white', width=0.6)
            
            for bar, val in zip(bars, values):
                plt.text(bar.get_x() + bar.get_width() / 2., bar.get_height(), 
                         f"₩{val/10000:,.1f}W", ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            plt.title('Revenue Breakdown: All Pricing Scenarios Combined (Tourists)')
            plt.ylabel('Revenue (Won)')
            plt.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(result_dir, '7_price_simulation_breakdown.png'))
            plt.close()
            
        else:
            print("No data matched the simulation target mask.")
            
    except Exception as e:
        print(f"Simulation failed: {e}")
    
    # Vis 8 & 9: Sub-region (소지역) Analysis
    print("\n[5/5] Generating Sub-region (소지역) Analysis...")
    try:
        # Vis 8: Distribution by Sub-region
        so_agg = df.groupby(['소지역', 'User_Segment'])['트립수'].sum().reset_index()
        so_pivot = so_agg.pivot(index='소지역', columns='User_Segment', values='트립수').fillna(0)
        so_pivot['Total'] = so_pivot.sum(axis=1)
        so_pivot = so_pivot.sort_values('Total', ascending=False).drop(columns='Total')
        
        so_pct = so_pivot.div(so_pivot.sum(axis=1), axis=0) * 100
        
        plt.figure(figsize=(14, 7))
        ax8 = so_pct.plot(kind='bar', stacked=True, figsize=(14, 7), 
                          color=[segment_colors.get(x, '#333333') for x in so_pct.columns])
        
        plt.title('User Segment Distribution by Sub-Region (소지역)')
        plt.ylabel('Percentage of Trips (%)')
        plt.xlabel('Sub-Region (소지역)')
        plt.xticks(rotation=45, ha='right')
        plt.legend(title='User Segment', bbox_to_anchor=(1.05, 1), loc='upper left')
        
        for container in ax8.containers:
            # Only add labels if the percentage is significant to avoid clutter
            labels = [f"{v.get_height():.1f}%" if v.get_height() > 2 else "" for v in container]
            ax8.bar_label(container, labels=labels, label_type='center', fontsize=8, color='white', fontweight='bold')
            
        plt.tight_layout()
        plt.savefig(os.path.join(result_dir, '8_subregion_segment_distribution.png'))
        plt.close()
        
        # Vis 9: Trend of Top 3 소지역 (Average Daily Trips by Month)
        top3_so = so_pivot.sum(axis=1).nlargest(3).index.tolist()
        top3_df = df[df['소지역'].isin(top3_so)]
        
        # Calculate daily total trips for each 소지역, then average by month
        daily_top3 = top3_df.groupby(['dt', 'month', '소지역'])['트립수'].sum().reset_index()
        top3_trend = daily_top3.groupby(['month', '소지역'])['트립수'].mean().reset_index()
        
        plt.figure(figsize=(12, 6))
        ax9 = sns.lineplot(data=top3_trend, x='month', y='트립수', hue='소지역', marker='o', linewidth=2.5)
        
        for index, row in top3_trend.iterrows():
            plt.text(row['month'], row['트립수'], f"{row['트립수']:.1f}", color='black', ha='center', va='bottom', fontsize=8)
            
        plt.title(f'Monthly Trip Trend for Top 3 Sub-Regions (Average Daily Trips)')
        plt.xlabel('Month (YYYY-MM)')
        plt.ylabel('Average Daily Trips')
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.legend(title='Sub-Region', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(os.path.join(result_dir, '9_top3_subregion_trend.png'))
        plt.close()
        
    except Exception as e:
        print(f"Sub-region analysis failed: {e}")
        
    print("\nAll scripts completed.")

if __name__ == "__main__":
    main()
