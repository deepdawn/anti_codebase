import pandas as pd
import numpy as np
import os

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon1 - lon2)
    a = np.sin(dphi / 2)**2 + \
        np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def generate_recommendations(input_path, output_dir):
    print(f"Loading analysis results from {input_path}...")
    df = pd.read_csv(input_path)
    
    recommendations = []
    
    for model in df['기종'].unique():
        model_df = df[df['기종'] == model].copy()
        coldspots = model_df[model_df['demand_grade'] == 'Low'].reset_index(drop=True)
        hotspots = model_df[model_df['demand_grade'] == 'Very High'].reset_index(drop=True)
        
        # 만약 Very High가 없으면 High까지 확장
        if hotspots.empty:
            hotspots = model_df[model_df['demand_grade'] == 'High'].reset_index(drop=True)
            
        if coldspots.empty or hotspots.empty:
            continue
            
        for _, cold in coldspots.iterrows():
            hotspots['dist'] = hotspots.apply(
                lambda hot: haversine(cold['lat'], cold['lon'], hot['lat'], hot['lon']), axis=1
            )
            best_match = hotspots.loc[hotspots['dist'].idxmin()]
            
            recommendations.append({
                'model': model,
                'from_zone': cold['배치존명'],
                'to_zone': best_match['배치존명'],
                'distance_km': round(best_match['dist'], 2),
                'from_demand': cold['demand_grade'],
                'to_demand': best_match['demand_grade'],
                'from_lat': cold['lat'],
                'from_lon': cold['lon'],
                'to_lat': best_match['lat'],
                'to_lon': best_match['lon']
            })
            
    recom_df = pd.DataFrame(recommendations)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "rebalance_recommendations.csv")
    recom_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Recommendations complete! Saved to {output_path}")

if __name__ == "__main__":
    INPUT_PATH = "/Users/galaxy/anti_codebase/results/deployed_zone_analysis_v1/demand_analysis_results.csv"
    OUTPUT_DIR = "/Users/galaxy/anti_codebase/results/deployed_zone_analysis_v1"
    generate_recommendations(INPUT_PATH, OUTPUT_DIR)
