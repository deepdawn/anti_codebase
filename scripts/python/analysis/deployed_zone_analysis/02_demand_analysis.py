import pandas as pd
import os

def analyze_demand(input_path, output_dir):
    print(f"Loading preprocessed data from {input_path}...")
    df = pd.read_csv(input_path)
    
    # aggregations
    agg_funcs = {
        '출루까지 시간': ['count', 'mean', lambda x: (x <= 1).sum(), lambda x: (x <= 24).sum()],
        '위도': 'first',
        '경도': 'first',
        '대지역': 'first',
        '중지역': 'first',
        '소지역': 'first'
    }
    
    analysis = df.groupby(['배치존명', '기종']).agg(agg_funcs).reset_index()
    analysis.columns = [
        '배치존명', '기종', 'total_deployments', 'avg_outbound_time', 
        'very_high_demand_count', 'high_demand_count', 
        'lat', 'lon', 'large_area', 'mid_area', 'small_area'
    ]
    
    # ratios
    analysis['very_high_demand_ratio'] = analysis['very_high_demand_count'] / analysis['total_deployments']
    analysis['high_demand_ratio'] = analysis['high_demand_count'] / analysis['total_deployments']
    
    # grade logic
    def get_demand_grade(row):
        if row['very_high_demand_ratio'] >= 0.3: 
            return 'Very High'
        elif row['high_demand_ratio'] >= 0.6:
            return 'High'
        else:
            return 'Low'
            
    analysis['demand_grade'] = analysis.apply(get_demand_grade, axis=1)
    
    # save result
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "demand_analysis_results.csv")
    analysis.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"Demand analysis complete! Results saved to {output_path}")
    
    # summary
    print("\n[Demand Grade Distribution]")
    print(analysis.groupby(['기종', 'demand_grade']).size())

if __name__ == "__main__":
    INPUT_PATH = f"{os.path.expanduser('~')}/anti_codebase/base_data/secondary_data/deployed_zone_analysis_v1_preprocessed.csv"
    OUTPUT_DIR = f"{os.path.expanduser('~')}/anti_codebase/results/deployed_zone_analysis_v1"
    analyze_demand(INPUT_PATH, OUTPUT_DIR)
