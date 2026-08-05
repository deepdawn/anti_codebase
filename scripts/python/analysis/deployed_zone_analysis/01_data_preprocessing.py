import pandas as pd
import os

def preprocess_data(input_path, output_path):
    print(f"Loading data from {input_path}...")
    # Read CSV with considering potential encoding issues
    try:
        df = pd.read_csv(input_path)
    except UnicodeDecodeError:
        df = pd.read_csv(input_path, encoding='cp949')
    
    print("Pre-processing '출루까지 시간'...")
    # Convert '출루까지 시간' to numeric, handling '[NULL]'
    # User requested to treat NULL as low demand, so we'll fill with 168 hours (1 week)
    df['출루까지 시간'] = pd.to_numeric(df['출루까지 시간'].replace('[NULL]', 168), errors='coerce')
    df['출루까지 시간'] = df['출루까지 시간'].fillna(168)
    
    # Save the preprocessed data
    print(f"Saving preprocessed data to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8-sig') # Rule 9: utf-8-sig
    print("Preprocessing complete!")

if __name__ == "__main__":
    PRIMARY_DATA_PATH = f"{os.path.expanduser('~')}/anti_codebase/base_data/primary_data/deploy_usage.csv"
    SECONDARY_DATA_PATH = f"{os.path.expanduser('~')}/anti_codebase/base_data/secondary_data/deployed_zone_analysis_v1_preprocessed.csv"
    preprocess_data(PRIMARY_DATA_PATH, SECONDARY_DATA_PATH)
