import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Rule 10: Axis labels in English.
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

def generate_report(results_path, recommendations_path, output_dir):
    print("Loading data for visualization...")
    df_results = pd.read_csv(results_path)
    df_recom = pd.read_csv(recommendations_path)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Demand Distribution
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df_results, x='demand_grade', hue='기종', order=['Very High', 'High', 'Low'])
    plt.title('Demand Grade Distribution by Model', fontsize=15)
    plt.xlabel('Demand Grade', fontsize=12)
    plt.ylabel('Count', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig(os.path.join(output_dir, "demand_distribution.png"), dpi=300)
    plt.close()
    
    # 2. Zone Map
    plt.figure(figsize=(12, 8))
    sns.scatterplot(
        data=df_results, x='lon', y='lat', hue='demand_grade', style='기종',
        palette={'Very High': 'red', 'High': 'orange', 'Low': 'blue'},
        alpha=0.6, s=100
    )
    plt.title('Zone Demand Map', fontsize=15)
    plt.xlabel('Longitude', fontsize=12)
    plt.ylabel('Latitude', fontsize=12)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.savefig(os.path.join(output_dir, "zone_demand_map.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Summary Text
    summary_path = os.path.join(output_dir, "analysis_summary.txt")
    with open(summary_path, 'w', encoding='utf-8-sig') as f:
        f.write("=== Deployed Zone Analysis Summary ===\n\n")
        f.write(f"Total Zones Analyzed: {len(df_results)}\n")
        f.write(f"Total Coldspots identified: {len(df_recom)}\n\n")
        f.write("[Top 5 Rebalance Recommendations - Bicycle]\n")
        f.write(df_recom[df_recom['model'] == 'bicycle'].sort_values('distance_km').head(5)[['from_zone', 'to_zone', 'distance_km']].to_string(index=False))
        f.write("\n\n[Top 5 Rebalance Recommendations - Scooter]\n")
        f.write(df_recom[df_recom['model'] == 'scooter'].sort_values('distance_km').head(5)[['from_zone', 'to_zone', 'distance_km']].to_string(index=False))
    print(f"Report generated in {output_dir}")

if __name__ == "__main__":
    RESULTS_PATH = f"{os.path.expanduser('~')}/anti_codebase/results/deployed_zone_analysis_v1/demand_analysis_results.csv"
    RECOM_PATH = f"{os.path.expanduser('~')}/anti_codebase/results/deployed_zone_analysis_v1/rebalance_recommendations.csv"
    OUTPUT_DIR = f"{os.path.expanduser('~')}/anti_codebase/results/deployed_zone_analysis_v1"
    generate_report(RESULTS_PATH, RECOM_PATH, OUTPUT_DIR)
