import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def main():
    result_dir = "/Users/galaxy/codebase/results/pohang_extract_trip_data"
    data_file = os.path.join(result_dir, "20250101_20260430_pohang_camp_external_users.xlsx")
    
    # 1. Load Data
    print("[1/3] Loading Data...")
    df = pd.read_excel(data_file)
    
    # 2. Key Insights Generation (Head-First)
    print("\n" + "="*50)
    print("====== HEAD-FIRST: POHANG CAMP INSIGHTS ======")
    print("="*50)
    
    total_trips = df['트립수'].sum()
    total_revenue = df['합계결제금액'].sum()
    
    gubun_stats = df.groupby('gubun')[['트립수', '합계결제금액']].sum().reset_index()
    gubun_stats['Trip_Share(%)'] = (gubun_stats['트립수'] / total_trips * 100).round(1)
    gubun_stats['Revenue_Share(%)'] = (gubun_stats['합계결제금액'] / total_revenue * 100).round(1)
    
    print("\n[Overview: Internal vs External Users]")
    print(gubun_stats.to_string(index=False))
    
    external_df = df[df['gubun'] == '타지역 가입자']
    top_external_demo = external_df.groupby(['age_group', 'gender'])['트립수'].sum().reset_index()
    top_external_demo = top_external_demo.sort_values(by='트립수', ascending=False)
    
    print("\n[All Demographics for External Users (by Trips)]")
    print(top_external_demo.to_string(index=False))
    
    print("="*50 + "\n")
    
    # 3. Visualizations
    print("[2/3] Generating Visualizations...")
    
    # Set plotting style
    plt.style.use('ggplot')
    
    # Vis 1: Share of Trips and Revenue by User Type
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    
    # Translating Korean to English for the plot (Rule 11)
    gubun_eng_map = {'포항 가입자': 'Internal Users', '타지역 가입자': 'External Users'}
    gubun_stats['User_Type'] = gubun_stats['gubun'].map(gubun_eng_map)
    
    axes[0].pie(gubun_stats['트립수'], labels=gubun_stats['User_Type'], autopct='%1.1f%%', colors=['#3498db', '#e74c3c'])
    axes[0].set_title('Trip Share by User Type')
    
    axes[1].pie(gubun_stats['합계결제금액'], labels=gubun_stats['User_Type'], autopct='%1.1f%%', colors=['#3498db', '#e74c3c'])
    axes[1].set_title('Revenue Share by User Type')
    
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, '1_user_type_share.png'))
    plt.close()
    
    # Vis 2: Demographics of External Users
    plt.figure(figsize=(10, 6))
    
    # English translation mapping for gender and age
    gender_eng_map = {'남자': 'Male', '여자': 'Female'}
    age_eng_map = {'10대': '10s', '20대': '20s', '30대': '30s', '40대': '40s', '50대': '50s', '기타': 'Others'}
    
    ext_plot_df = external_df.copy()
    ext_plot_df['Gender'] = ext_plot_df['gender'].map(gender_eng_map).fillna(ext_plot_df['gender'])
    ext_plot_df['Age_Group'] = ext_plot_df['age_group'].map(age_eng_map).fillna(ext_plot_df['age_group'])
    
    demo_agg = ext_plot_df.groupby(['Age_Group', 'Gender'])['트립수'].sum().reset_index()
    
    sns.barplot(data=demo_agg, x='Age_Group', y='트립수', hue='Gender', palette='viridis', 
                order=['10s', '20s', '30s', '40s', '50s', 'Others'])
    plt.title('External Users: Trip Counts by Age and Gender')
    plt.xlabel('Age Group')
    plt.ylabel('Total Trips')
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, '2_external_user_demographics.png'))
    plt.close()
    
    # Vis 3: Monthly Trip Trend (Seasonality)
    plt.figure(figsize=(12, 6))
    
    df['dt'] = pd.to_datetime(df['dt'])
    df['is_weekend'] = df['dt'].dt.dayofweek >= 5
    df['Day_Type'] = df['is_weekend'].map({False: 'Weekday', True: 'Weekend'})
    df['User_Type'] = df['gubun'].map(gubun_eng_map)
    df['Group'] = df['User_Type'] + ' - ' + df['Day_Type']
    
    trend_df = df.groupby(['month', 'Group'])['트립수'].mean().reset_index()
    
    # Distinct colors for 4 groups
    group_palette = {
        'Internal Users - Weekday': '#1f77b4', # Blue
        'Internal Users - Weekend': '#ff7f0e', # Orange
        'External Users - Weekday': '#2ca02c', # Green
        'External Users - Weekend': '#d62728'  # Red
    }
    
    ax = sns.lineplot(data=trend_df, x='month', y='트립수', hue='Group', marker='o', 
                 palette=group_palette)
                 
    for index, row in trend_df.iterrows():
        plt.text(row['month'], row['트립수'], f"{row['트립수']:.1f}", color='black', ha='center', va='bottom', fontsize=8)
                 
    plt.title('Monthly Trip Trend by User Type & Day Type (Average Daily Trips)')
    plt.xlabel('Month (YYYY-MM)')
    plt.ylabel('Average Daily Trips')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(result_dir, '3_monthly_trip_trend.png'))
    plt.close()
    
    # Vis 4: Time Series Forecasting (Seasonal Naive with Trend)
    print("\n[4/4] Forecasting Future Trips...")
    try:
        total_monthly = df.groupby('month')['트립수'].sum().reset_index()
        total_monthly['month'] = pd.to_datetime(total_monthly['month'] + '-01')
        total_monthly = total_monthly.set_index('month')
        
        # Calculate Growth Rate: (2026 Jan-Apr) / (2025 Jan-Apr)
        y2025_q1 = total_monthly.loc['2025-01-01':'2025-04-01', '트립수'].sum()
        y2026_q1 = total_monthly.loc['2026-01-01':'2026-04-01', '트립수'].sum()
        growth_rate = y2026_q1 / y2025_q1 if y2025_q1 > 0 else 1.0
        
        # Forecast May 2026 - Dec 2026
        forecast_dates = pd.date_range(start='2026-05-01', end='2026-12-01', freq='MS')
        forecast_values = []
        for d in forecast_dates:
            # Get corresponding 2025 month
            past_month = d.replace(year=2025)
            if past_month in total_monthly.index:
                val = total_monthly.loc[past_month, '트립수'] * growth_rate
            else:
                val = total_monthly['트립수'].mean() # Fallback
            forecast_values.append(val)
            
        forecast = pd.Series(forecast_values, index=forecast_dates)
        
        print(f"\n[Forecast Assumption: Applied Year-over-Year Q1 Growth Rate = {growth_rate:.2f}x]")
        
        print("\n[Forecast: Next 8 Months Total Trips]")
        forecast_df = forecast.reset_index()
        forecast_df.columns = ['Forecast_Month', 'Expected_Trips']
        forecast_df['Expected_Trips'] = forecast_df['Expected_Trips'].astype(int)
        forecast_df['Forecast_Month'] = forecast_df['Forecast_Month'].dt.strftime('%Y-%m')
        print(forecast_df.to_string(index=False))
        
        plt.figure(figsize=(10, 6))
        plt.plot(total_monthly.index, total_monthly['트립수'], marker='o', label='Actual Trips (2025.01 - 2026.04)', color='#2c3e50')
        plt.plot(forecast.index, forecast, marker='s', linestyle='--', label='Forecasted Trips (2026.05 - 2026.12)', color='#e74c3c')
        
        for d, val in zip(forecast.index, forecast):
            plt.text(d, val, f"{val/1000:.1f}k", color='#e74c3c', ha='center', va='bottom', fontsize=8)
            
        plt.title('Total Trip Forecast (Seasonal Naive with YoY Trend)')
        plt.xlabel('Date')
        plt.ylabel('Total Trips')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(result_dir, '4_forecast_trip_trend.png'))
        plt.close()
    except Exception as e:
        print(f"Forecasting failed: {e}")
        
    # Vis 5 & 6: Pricing Simulation (Phase 4)
    print("\n[5/6] Running Pricing Simulation for External Users on Peak Season Weekends...")
    try:
        # Define Peak Season and Target Data
        peak_months = ['05', '09', '10']
        
        # Extract month number (YYYY-MM)
        df['month_num'] = df['month'].str.split('-').str[1]
        
        # Mask for target trips: External Users AND Peak Season AND Weekend
        target_mask = (df['gubun'] == '타지역 가입자') & (df['month_num'].isin(peak_months)) & (df['is_weekend'] == True)
        target_df = df[target_mask].copy()
        
        if len(target_df) > 0:
            total_trips = target_df['트립수'].sum()
            total_mins = target_df['합계운행시간(분)'].sum()
            current_revenue = target_df['합계결제금액'].sum()
            
            # === Scenario A: Daytime Care +400, Per-min +20 ===
            add_rev_A_minute = total_mins * 20
            add_rev_A_care = total_trips * 400 * 0.7  # 70% daytime
            total_add_A = add_rev_A_minute + add_rev_A_care
            rate_A = (total_add_A / current_revenue) * 100 if current_revenue > 0 else 0
            
            # === Scenario B: Nighttime Care +200, Per-min unchanged ===
            add_rev_B_care = total_trips * 200 * 0.3  # 30% nighttime
            total_add_B = add_rev_B_care
            rate_B = (total_add_B / current_revenue) * 100 if current_revenue > 0 else 0
            
            # === Combined (A + B) ===
            total_add_combined = total_add_A + total_add_B
            rate_combined = (total_add_combined / current_revenue) * 100 if current_revenue > 0 else 0
            
            print(f"\nTarget Trips (External, Peak Weekends): {total_trips:,.0f} trips")
            print(f"Current Revenue: ₩{current_revenue:,.0f}\n")
            
            print("[Scenario A] Daytime Care 800→1200 (+400) & Per-min 180→200 (+20)")
            print(f"  Additional Revenue: +₩{total_add_A:,.0f} (+{rate_A:.1f}%)")
            print(f"    └ Per-min rate (+20/min): +₩{add_rev_A_minute:,.0f}")
            print(f"    └ Daytime care (+400, 70%): +₩{add_rev_A_care:,.0f}")
            
            print(f"\n[Scenario B] Nighttime Care 1200→1400 (+200), Per-min unchanged")
            print(f"  Additional Revenue: +₩{total_add_B:,.0f} (+{rate_B:.1f}%)")
            print(f"    └ Nighttime care (+200, 30%): +₩{add_rev_B_care:,.0f}")
            
            print(f"\n[Combined A+B] Both Scenarios Applied Together")
            print(f"  Total Additional Revenue: +₩{total_add_combined:,.0f} (+{rate_combined:.1f}%)")
            print(f"  Simulated Revenue: ₩{current_revenue + total_add_combined:,.0f}")
            
            # --- Vis 5: Monthly Comparison Bar Chart (3 scenarios) ---
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
                    
            plt.title('Pricing Simulation: Peak Season Weekends (External Users)')
            plt.xlabel('Peak Month')
            plt.ylabel('Revenue (Won)')
            plt.legend(title='Pricing Scenario', fontsize=8)
            plt.grid(axis='y')
            plt.tight_layout()
            plt.savefig(os.path.join(result_dir, '5_price_simulation_effect.png'))
            plt.close()
            print("\nVisualization saved: 5_price_simulation_effect.png")
            
            # --- Vis 6: Waterfall-style summary of revenue components ---
            categories = ['Current\nRevenue', 'A: Per-min\n(+20/min)', 'A: Day Care\n(+400)', 'B: Night Care\n(+200)', 'Total\nSimulated']
            values = [current_revenue, add_rev_A_minute, add_rev_A_care, add_rev_B_care, current_revenue + total_add_combined]
            colors = ['#95a5a6', '#e74c3c', '#e74c3c', '#f39c12', '#2ecc71']
            
            plt.figure(figsize=(10, 6))
            bars = plt.bar(categories, values, color=colors, edgecolor='white', width=0.6)
            
            for bar, val in zip(bars, values):
                plt.text(bar.get_x() + bar.get_width() / 2., bar.get_height(), 
                         f"₩{val/10000:,.0f}W", ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            plt.title('Revenue Breakdown: All Pricing Scenarios Combined (External Users, Peak Weekends)')
            plt.ylabel('Revenue (Won)')
            plt.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(result_dir, '6_price_simulation_breakdown.png'))
            plt.close()
            print("Visualization saved: 6_price_simulation_breakdown.png")
        else:
            print("No data matched the simulation target mask.")
            
    except Exception as e:
        print(f"Simulation failed: {e}")
    
    print("\n[6/6] All scripts completed.")

if __name__ == "__main__":
    main()
