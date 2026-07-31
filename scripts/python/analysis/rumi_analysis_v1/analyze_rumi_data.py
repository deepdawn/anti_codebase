import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
import os

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    primary_data_path = os.path.join(base_dir, '../../../base_data/primary_data/yongsan_rumi_trip_data.csv')
    secondary_data_path = os.path.join(base_dir, '../../../base_data/secondary_data/rumi_analysis_v1/rumi_data_processed.csv')
    results_dir = os.path.join(base_dir, '../../../results/rumi_analysis_v1/')
    
    df = pd.read_csv(primary_data_path)
    
    # Data type conversion
    df['date'] = pd.to_datetime(df['date'], format='%Y.%m.%d', errors='coerce')
    # Use alternative format if previous failed
    if df['date'].isnull().any():
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
    df = df.sort_values('date')
    
    # Metric Calculation
    df['utilization_rate'] = df['deployed_count'] / df['assigned_count']
    total_revenue_numerator = df['calculated_out_of_area_charge'] + df['calculated_pay_amount']
    df['revenue_per_asset'] = total_revenue_numerator / (df['assigned_count'] * 1.1)

    # Save to secondary data with utf-8-sig
    df.to_csv(secondary_data_path, index=False, encoding='utf-8-sig')
    
    # Statistical Analysis Report
    with open(os.path.join(results_dir, 'statistical_summary.txt'), 'w', encoding='utf-8') as f:
        f.write("=== Descriptive Statistics ===\n")
        f.write(df[['trip_count', 'deployed_count', 'utilization_rate', 'revenue_per_asset']].describe().to_string())
        f.write("\n\n")
        
        f.write("=== Correlation Analysis ===\n")
        corr = df[['trip_count', 'deployed_count', 'assigned_count', 'revenue_per_asset', 'utilization_rate']].corr(numeric_only=True)
        f.write(corr.to_string())
        f.write("\n\n")
        
        f.write("=== Linear Regression: Trip Count vs Deployed Count ===\n")
        X = df['deployed_count']
        y = df['trip_count']
        X = sm.add_constant(X)
        model = sm.OLS(y, X).fit()
        f.write(model.summary().as_text())
        f.write("\n")

    # Visualization
    sns.set_theme(style="whitegrid")
    
    # 1. Time Series Plot
    plt.figure(figsize=(10, 5))
    plt.plot(df['date'], df['trip_count'], marker='o', label='Trips')
    plt.plot(df['date'], df['deployed_count'], marker='s', label='Deployed Assets')
    plt.xlabel('Date (Year-Month-Day)')
    plt.ylabel('Count')
    plt.title('Daily Volume: Trips and Deployed Assets over Time')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'time_series_volume.png'))
    plt.close()
    
    # 2. Revenue Plot
    plt.figure(figsize=(10, 5))
    plt.plot(df['date'], df['revenue_per_asset'], color='green', marker='^', label='Revenue per Asset')
    plt.xlabel('Date (Year-Month-Day)')
    plt.ylabel('KRW (Estimated)')
    plt.title('Daily Revenue per Asset')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'time_series_revenue.png'))
    plt.close()
    
    # 3. Correlation Heatmap
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f")
    plt.title('Variables Correlation Matrix')
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'correlation_heatmap.png'))
    plt.close()
    
    print("Analysis script finished successfully.")

if __name__ == '__main__':
    main()
