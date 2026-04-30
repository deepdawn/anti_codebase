import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
import urllib.parse
import os
import sys
from datetime import datetime, timedelta

# 1. 추출 기간 설정
file_name = 'test_data_extract.csv'
start_date = datetime(2026, 4, 27)
end_limit = datetime(2026, 4, 27) + timedelta(days=1)

def get_engine():
    host = 'live.st.rds.gbility.io'
    user = 'gbikemarketing'
    password = urllib.parse.quote_plus('gbikemkt0514$@#!')
    port = 3306
    database = 'gbike'
    try:
        engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
        return engine
    except Exception as e:
        print(f"Engine creation failed: {e}")
        sys.exit(1)

def main(file_name, start_date, end_limit):
    # 규칙 5번 준수: 하위 폴더명 입력 받기 및 생성
    print("규칙 5번에 따라 저장할 하위 폴더명을 입력해야 합니다.")
    subfolder_name = input("결과를 저장할 하위 폴더명을 입력해주세요 (예: daily_report): ")
    
    result_dir = os.path.join("/Users/galaxy/codebase/results/data_extract", subfolder_name)
    os.makedirs(result_dir, exist_ok=True)

    # 2. 파일 이름 동적 생성
    prefix = f"{start_date.strftime('%m%d')}_{end_limit.strftime('%m%d')}"
    result_file = os.path.join(result_dir, f"{prefix}_{file_name}")

    engine = get_engine()

    query = f"""
    select o.user_id, o.from_api, count(o.order_id) as ord_cnt
    from gbike.rich_orders o
    where 1=1
    AND o.add_time >= UNIX_TIMESTAMP('{start_date}') - 32400
    AND o.add_time < UNIX_TIMESTAMP('{end_limit}') - 32400
    and o.order_state = 2
    group by o.user_id, o.from_api
    """
    
    print(f"데이터 추출 중: {start_date.strftime('%Y-%m-%d')} ~ {end_limit.strftime('%Y-%m-%d')}")
    with engine.connect() as connection:    
        df = pd.read_sql(query, connection) 
    
    # 규칙 10번 준수: utf-8-sig 인코딩 사용
    df.to_csv(result_file, index=False, encoding='utf-8-sig')
    print(f"최종 파일이 저장되었습니다: {result_file} (총 {len(df)} 행)")

if __name__ == "__main__":
    main(file_name, start_date, end_limit)
