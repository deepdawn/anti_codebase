import os
import sys
import pandas as pd

# Add utils path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))
from test_db_conn import run_query

base_dir = os.path.dirname(os.path.abspath(__file__))
sql_dir = os.path.abspath(os.path.join(base_dir, '../../sql/yoy_camp_revenue_analysis_v1'))
out_dir = os.path.abspath(os.path.join(base_dir, '../../../base_data/primary_data/yoy_camp_revenue_analysis_v1'))

os.makedirs(out_dir, exist_ok=True)

def extract_and_save_excel(sql_filename, out_filename):
    sql_path = os.path.join(sql_dir, sql_filename)
    out_path = os.path.join(out_dir, out_filename)
    
    with open(sql_path, 'r', encoding='utf-8') as f:
        query = f.read()
        
    print(f"Extracting {sql_filename}...")
    df = run_query(query)
    
    if df is not None:
        df.to_excel(out_path, index=False)
        print(f"Data saved to: {out_path}")
    else:
        print(f"Failed to extract data for {sql_filename}")

if __name__ == "__main__":
    extract_and_save_excel('extract_orders.sql', 'orders.xlsx')
    extract_and_save_excel('extract_deployed.sql', 'deployed.xlsx')
    print("Extraction complete.")
