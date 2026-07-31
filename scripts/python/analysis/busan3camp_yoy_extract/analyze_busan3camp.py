import pandas as pd
import os

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
    
    # Define file paths
    raw_data_path = os.path.join(base_dir, 'base_data/primary_data/busan3camp_yoy_extract/busan3camp_raw.xlsx')
    assigned_vehicle_path = os.path.join(base_dir, 'base_data/secondary_data/260526_busan3camp_assigned_vehicle.xlsx')
    output_path = os.path.join(base_dir, 'results/busan3camp_yoy_extract/busan3camp_analyzed.xlsx')
    
    print("Loading data...")
    df_raw = pd.read_excel(raw_data_path)
    df_assigned = pd.read_excel(assigned_vehicle_path)
    
    # Format date columns to string
    df_raw['date_str'] = pd.to_datetime(df_raw['date_str']).dt.strftime('%Y-%m-%d')
    df_assigned['date'] = pd.to_datetime(df_assigned['date']).dt.strftime('%Y-%m-%d')
    
    # Merge data
    print("Merging data...")
    df_merged = pd.merge(
        df_raw, 
        df_assigned[['date', 'low_region_name', 'assigned_count']],
        left_on=['date_str', 'small_area'],
        right_on=['date', 'low_region_name'],
        how='left'
    )
    
    # Drop redundant columns
    df_merged = df_merged.drop(columns=['date', 'low_region_name'])
    
    # Calculate per asset metrics
    print("Calculating metrics...")
    
    df_merged['revenue_per_asset'] = df_merged.apply(
        lambda row: row['net_revenue_krw'] / row['assigned_count'] if pd.notnull(row['assigned_count']) and row['assigned_count'] > 0 else 0, 
        axis=1
    )
    
    df_merged['trips_per_asset'] = df_merged.apply(
        lambda row: row['trip_count'] / row['assigned_count'] if pd.notnull(row['assigned_count']) and row['assigned_count'] > 0 else 0, 
        axis=1
    )
    
    # 3. Add 'is_not_in_now' column
    print("Identifying obsolete small areas (is_not_in_now)...")
    areas_2025 = set(df_merged[df_merged['date_str'].str.startswith('2025')]['small_area'].unique())
    areas_2026 = set(df_merged[df_merged['date_str'].str.startswith('2026')]['small_area'].unique())
    areas_only_2025 = areas_2025 - areas_2026
    
    df_merged['is_not_in_now'] = df_merged['small_area'].isin(areas_only_2025)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save the final result
    print(f"Saving analyzed data to {output_path}...")
    df_merged.to_excel(output_path, index=False)
    print("Analysis complete.")

if __name__ == '__main__':
    main()
