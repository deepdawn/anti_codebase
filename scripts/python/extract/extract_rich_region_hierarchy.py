import os
import sys
import pandas as pd
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.test_mysql_conn import get_engine

def extract_rich_region_hierarchy():
    query = """
    select	r.region_id,
            r.region_name as '소지역',
            rr.region_name as '중지역',
            rrr.region_name as '대지역',
            r.country_code
    from	gbike.rich_region r
    join	gbike.rich_region rr on r.parent_id = rr.region_id
    join	gbike.rich_region rrr on rr.parent_id = rrr.region_id
    where   r.country_code = 'kr'
    """
    
    engine = get_engine()
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
            
        # 행정구역 정보 추가 (left join)
        target_excel_path = "/Users/galaxy.jang/Library/CloudStorage/OneDrive-지바이크/서비스운영본부 - 현장데이터 개발센터/국내 소지역 행정구역 매칭.xlsx"
        if os.path.exists(target_excel_path):
            excel_df = pd.read_excel(target_excel_path, sheet_name='ETL_USED')[['소지역명', '행정구역']]
            # 소지역명을 기준으로 left join
            df = pd.merge(df, excel_df, left_on='소지역', right_on='소지역명', how='left')
            # 소지역명 컬럼은 소지역 컬럼과 중복되므로 제거
            if '소지역명' in df.columns:
                df = df.drop(columns=['소지역명'])
        else:
            print(f"경고: 행정구역 매칭 엑셀 파일을 찾을 수 없습니다. 경로: {target_excel_path}")
            
        return df
    except Exception as e:
        print(f"Error extracting region hierarchy data: {e}")
        return None

def main():
    # 구글 공유 드라이브 경로 설정
    base_save_path = "/Users/galaxy.jang/Google Drive/공유 드라이브/gbike.rich_region"
    
    print(f"저장 기본 경로: {base_save_path}")
    
    # 폴더가 없으면 생성
    os.makedirs(base_save_path, exist_ok=True)
    
    # 분석 편의성을 위해 parquet과 csv 두 가지 포맷으로 저장
    file_path = os.path.join(base_save_path, "rich_region_hierarchy.parquet")
    csv_file_path = os.path.join(base_save_path, "rich_region_hierarchy.csv")
    
    print("데이터 추출 중...")
    start_time = time.time()
    
    df = extract_rich_region_hierarchy()
    
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
