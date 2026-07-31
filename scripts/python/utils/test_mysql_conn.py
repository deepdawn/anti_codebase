import pandas as pd
import pymysql
from sqlalchemy import create_engine
import urllib.parse
import sys
import os

def get_engine():
    host = 'live.st.rds.gbility.io'
    user = 'gbikemarketing'
    password = urllib.parse.quote_plus('gbikemkt0514$@#!')
    port = 3306
    # gbike.rich_user 등 기본 db 타겟팅을 위해 설정
    database = 'gbike'

    try:
        engine = create_engine(
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}",
            pool_pre_ping=True,
            pool_recycle=3600
        )
        return engine
    except Exception as e:
        print("Engine creation failed:", e)
        sys.exit(1)

def run_query(query, save_csv_path=None):
    engine = get_engine()
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
        
        print("=== Database Connection Successful ===")
        if save_csv_path:
            os.makedirs(os.path.dirname(save_csv_path), exist_ok=True)
            df.to_csv(save_csv_path, index=False, encoding='utf-8-sig')
            print(f"Data saved to: {save_csv_path}")
            
        return df
    except Exception as e:
        print("Error during database connection or query execution:")
        print(e)
        return None

def main():
    # 기본 테스트 동작을 예전거 그대로 보존
    query = "select 1 as col1"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, '../../../base_data/primary_data/raw_data.csv')
    
    df = run_query(query, csv_path)
    if df is not None:
        print(df)

if __name__ == '__main__':
    main()
