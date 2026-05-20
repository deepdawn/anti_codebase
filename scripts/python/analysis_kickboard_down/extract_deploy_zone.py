import os
import sys
import pandas as pd

# test_db_conn.py 모듈 연동
base_dir = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.join(base_dir, '../utils')
sys.path.append(utils_dir)
from test_db_conn import run_query

def extract_deploy_zone_data():
    sql_path = os.path.join(base_dir, '../../sql/analysis_kickboard_down/extract_w19_w20_deploy_zone.sql')
    excel_path = os.path.join(base_dir, '../../../base_data/primary_data/analysis_kickboard_down/deploy_zone_w19_w20.xlsx')
    
    if os.path.exists(excel_path):
        print(f"Data already extracted: {excel_path}")
        return pd.read_excel(excel_path)
    
    with open(sql_path, 'r', encoding='utf-8') as f:
        query = f.read()
        
    print("Executing query to fetch deploy zone data...")
    df = run_query(query)
    
    if df is not None:
        os.makedirs(os.path.dirname(excel_path), exist_ok=True)
        print("Saving to Excel...")
        df.to_excel(excel_path, index=False)
        print(f"Data successfully saved to {excel_path}")
        
    return df

def main():
    df = extract_deploy_zone_data()
    if df is None or df.empty:
        print("No data extracted.")
        return

    print("Data Overview:")
    print(df.head())
    print("\nData Shape:", df.shape)

if __name__ == '__main__':
    main()
