import pandas as pd
from sqlalchemy import create_engine
import urllib.parse
import sys
import os

def get_redshift_engine():
    host = 'live-redshift-cluster-gbike.comng6zxlpsm.ap-northeast-2.redshift.amazonaws.com'
    user = 'rmteam'
    password = urllib.parse.quote_plus('Gbike@rmteam@20230510!')
    port = 5439
    database = 'gbike'

    try:
        # sqlalchemy-redshift 및 psycopg2를 사용한 연결
        engine = create_engine(f"redshift+psycopg2://{user}:{password}@{host}:{port}/{database}")
        return engine
    except Exception as e:
        print("Redshift Engine creation failed:", e)
        sys.exit(1)

def run_redshift_query(query, save_path=None):
    engine = get_redshift_engine()
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
        
        print("=== Redshift Database Connection Successful ===")
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Rule 7: 기본적으로 엑셀 파일(.xlsx)로 저장
            if save_path.endswith('.xlsx'):
                df.to_excel(save_path, index=False)
            elif save_path.endswith('.csv'):
                df.to_csv(save_path, index=False, encoding='utf-8-sig')
            else:
                save_path = save_path + '.xlsx'
                df.to_excel(save_path, index=False)
                
            print(f"Data saved to: {save_path}")
            
        return df
    except Exception as e:
        print("Error during Redshift database connection or query execution:")
        print(e)
        return None

def main():
    query = "SELECT 1 AS col1;"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    excel_path = os.path.abspath(os.path.join(base_dir, '../../../base_data/primary_data/redshift_test_result.xlsx'))
    
    df = run_redshift_query(query, excel_path)
    if df is not None:
        print(df)

if __name__ == '__main__':
    main()
