import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.test_mysql_conn import get_engine

def extract_deploy_count(target_date_str, engine):
    """지정된 날짜의 배치수 추출"""
    query = f"""
    SELECT
        DATE(DATE_ADD(D.created_at, INTERVAL 9 HOUR)) AS `date`,
        D.deploy_type AS `배치 구분`,
        D.model_type AS `기종`,
        G.region_name AS `대지역`,
        E.region_name AS `중지역`,
        R.region_name AS `소지역`,
        S.name AS `배치존명`,
        S.lat AS `위도`,
        S.lng AS `경도`,
        COUNT(DISTINCT D.id) AS `배치수`
    FROM
        gbike.rich_deploy_zone_usages D
            JOIN
        gbike.rich_release_spot S ON D.deploy_zone_id = S.id
            JOIN
        gbike.rich_region R ON S.region_id = R.region_id
            JOIN
        gbike.rich_region E ON R.parent_id = E.region_id
            JOIN
        gbike.rich_region G ON E.parent_id = G.region_id
    WHERE
        D.deployed_at >= CONVERT_TZ('{target_date_str} 00:00:00', 'Asia/Seoul', 'UTC')
        AND D.deployed_at <= CONVERT_TZ('{target_date_str} 23:59:59', 'Asia/Seoul', 'UTC')
        AND G.region_name in ('남부RS팀','RS그룹','서울RS팀','중앙RS팀','경상RS팀','강남RS팀','프로젝트_루미')
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
    """
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        print(f"Error extracting deploy count for {target_date_str}: {e}")
        return None

def extract_release_count(target_date_str, engine):
    """지정된 날짜의 출루수 추출"""
    # 쿼리2에서 GROUP BY가 누락되어 있어 추가 반영
    query = f"""
    SELECT
        DATE(DATE_ADD(D.released_at, INTERVAL 9 HOUR)) AS `date`,
        D.deploy_type AS `배치 구분`,
        D.model_type AS `기종`,
        G.region_name AS `대지역`,
        E.region_name AS `중지역`,
        R.region_name AS `소지역`,
        S.name AS `배치존명`,
        S.lat AS `위도`,
        S.lng AS `경도`,
        COUNT(DISTINCT D.id) AS `출루수`
    FROM
        gbike.rich_deploy_zone_usages D
            JOIN
        gbike.rich_release_spot S ON D.deploy_zone_id = S.id
            JOIN
        gbike.rich_region R ON S.region_id = R.region_id
            JOIN
        gbike.rich_region E ON R.parent_id = E.region_id
            JOIN
        gbike.rich_region G ON E.parent_id = G.region_id
    WHERE
        D.released_at >= CONVERT_TZ('{target_date_str} 00:00:00', 'Asia/Seoul', 'UTC')
        AND D.released_at <= CONVERT_TZ('{target_date_str} 23:59:59', 'Asia/Seoul', 'UTC')
        AND G.region_name in ('남부RS팀','RS그룹','서울RS팀','중앙RS팀','경상RS팀','강남RS팀','프로젝트_루미')
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
    """
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        print(f"Error extracting release count for {target_date_str}: {e}")
        return None

def merge_usages(df_deploy, df_release):
    """배치수와 출루수 데이터 병합"""
    if (df_deploy is None or df_deploy.empty) and (df_release is None or df_release.empty):
        return None
        
    if df_deploy is None or df_deploy.empty:
        return df_release.assign(배치수=0)
        
    if df_release is None or df_release.empty:
        return df_deploy.assign(출루수=0)
        
    # 조인 키 (위도, 경도 제외)
    join_keys = ['date', '배치 구분', '기종', '대지역', '중지역', '소지역', '배치존명']
    
    merged_df = pd.merge(df_deploy, df_release, on=join_keys, how='outer', suffixes=('_deploy', '_release'))
    
    # 위도, 경도 합치기
    if '위도_deploy' in merged_df.columns and '위도_release' in merged_df.columns:
        merged_df['위도'] = merged_df['위도_deploy'].fillna(merged_df['위도_release'])
        merged_df['경도'] = merged_df['경도_deploy'].fillna(merged_df['경도_release'])
        merged_df.drop(columns=['위도_deploy', '위도_release', '경도_deploy', '경도_release'], inplace=True)
    
    # NaN 결측치 0으로 처리 및 정수 변환
    merged_df['배치수'] = merged_df['배치수'].fillna(0).astype(int)
    merged_df['출루수'] = merged_df['출루수'].fillna(0).astype(int)
    
    return merged_df

def main():
    base_save_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_deploy_zone_usages"
    
    args = [arg for arg in sys.argv if arg != '--overwrite']
    
    if len(args) >= 3:
        start_date_str = args[1]
        end_date = args[2]
    else:
        # 인자가 없으면 이번 달 1일부터 전일자까지 추출
        target_dt = datetime.now() - timedelta(days=1)
        end_date = target_dt.strftime('%Y-%m-%d')
        
        curr_month_dt = datetime.now().replace(day=1)
        start_date_str = curr_month_dt.strftime('%Y-%m-%d')
        
    date_list = pd.date_range(start=start_date_str, end=end_date, freq='D')
    
    engine = get_engine()
    
    print(f"총 {len(date_list)}일 치 데이터 추출을 시작합니다.")
    print(f"저장 기본 경로: {base_save_path}")
    
    has_error = False
    for dt in date_list:
        target_date_str = dt.strftime('%Y-%m-%d')
        
        daily_folder_name = f"dt={target_date_str}"
        daily_folder_path = os.path.join(base_save_path, daily_folder_name)
        
        os.makedirs(daily_folder_path, exist_ok=True)
        
        file_path = os.path.join(daily_folder_path, f"rich_deploy_zone_usages_{target_date_str}.parquet")
        
        if os.path.exists(file_path) and '--overwrite' not in sys.argv:
            print(f"[{target_date_str}] 파일이 이미 존재하여 스킵합니다: {file_path}")
            continue
            
        print(f"[{target_date_str}] 데이터 추출 중...")
        start_time = time.time()
        
        df_deploy = extract_deploy_count(target_date_str, engine)
        df_release = extract_release_count(target_date_str, engine)
        
        df = merge_usages(df_deploy, df_release)
        
        if df is not None and not df.empty:
            try:
                # pandas to_parquet 저장 시 date 타입 호환성 확보
                df['date'] = pd.to_datetime(df['date']).dt.date
                df.to_parquet(file_path, index=False)
                elapsed_time = time.time() - start_time
                print(f"[{target_date_str}] 성공적으로 저장되었습니다. (건수: {len(df):,}, 소요시간: {elapsed_time:.2f}초)")
            except Exception as e:
                print(f"[{target_date_str}] 파일 저장 중 오류 발생: {e}")
                has_error = True
        else:
            print(f"[{target_date_str}] 추출된 데이터가 없습니다.")
            
    if has_error:
        print("경고: 하나 이상의 날짜 추출 또는 저장에 실패했습니다.")
        sys.exit(1)

if __name__ == '__main__':
    main()
