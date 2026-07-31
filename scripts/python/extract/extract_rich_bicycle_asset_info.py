import os
import sys
import pandas as pd
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.test_mysql_conn import get_engine

def extract_rich_bicycle_asset_info():
    # SQL 파일 경로 설정
    sql_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sql', 'rich_bicycle_asset_info.sql'))
    
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            query = f.read()
    except Exception as e:
        print(f"SQL 파일을 읽는 중 오류 발생: {e}")
        return None
    
    engine = get_engine()
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        print(f"Error extracting bicycle asset info data: {e}")
        return None

def main():
    # 구글 공유 드라이브 경로 설정
    base_save_path = "/Users/galaxy.jang/Google Drive/공유 드라이브/gbike.rich_bicycle"
    
    print(f"저장 기본 경로: {base_save_path}")
    
    # 폴더가 없으면 생성
    os.makedirs(base_save_path, exist_ok=True)
    
    # 분석 편의성을 위해 parquet과 csv 두 가지 포맷으로 저장
    file_path = os.path.join(base_save_path, "rich_bicycle_asset_info.parquet")
    csv_file_path = os.path.join(base_save_path, "rich_bicycle_asset_info.csv")
    
    print("데이터 추출 중...")
    start_time = time.time()
    
    df = extract_rich_bicycle_asset_info()
    
    if df is not None and not df.empty:
        try:
            # parquet으로 저장. index 제외.
            df.to_parquet(file_path, index=False)
            # csv로 저장. 한글 깨짐 방지를 위해 utf-8-sig 인코딩 사용
            df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
            
            elapsed_time = time.time() - start_time
            print(f"성공적으로 저장되었습니다. (건수: {len(df):,}, 소요시간: {elapsed_time:.2f}초)")
            print(f"Parquet 파일 위치: {file_path}")
            print(f"CSV 파일 위치: {csv_file_path}")
        except Exception as e:
            print(f"파일 저장 중 오류 발생: {e}")
    elif df is not None and df.empty:
        print("해당하는 데이터가 없습니다.")
    else:
        print("추출 실패.")

if __name__ == '__main__':
    main()
