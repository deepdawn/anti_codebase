import os
import sys
import argparse
import time
import pandas as pd
from datetime import datetime, timedelta

# utils 모듈 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils.test_mysql_conn import get_engine

def extract_deploy_used_time(target_date_str, engine):
    """지정된 날짜의 배치 및 출루까지 걸린 시간 관련 데이터 추출"""
    query = f"""
    SELECT 
        DATE(DATE_ADD(D.deployed_at, INTERVAL 9 HOUR)) AS `date`,
        CEIL((UNIX_TIMESTAMP(D.released_at) - UNIX_TIMESTAMP(D.deployed_at)) / 3600) AS `출루까지 시간`,
        D.deploy_type AS `배치 구분`,
        D.model_type AS `기종`,
        G.region_name AS `대지역`,
        E.region_name AS `중지역`,
        R.region_name AS `소지역`,
        S.name AS `배치존명`,
        S.lat AS `위도`,
        S.lng AS `경도`,
        COUNT(D.id) AS `배치수`
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
        LEFT JOIN rich_admin a ON a.admin_id = D.admin_id
        LEFT JOIN (
            SELECT DISTINCT model_id
            FROM rich_model_has_roles
            WHERE model_type = 'App\\Models\\Admin'
              AND role_id IN (34, 36, 77)
        ) mhr_maint ON mhr_maint.model_id = a.admin_id
    WHERE
        D.deployed_at >= CONVERT_TZ('{target_date_str} 00:00:00', 'Asia/Seoul', 'UTC')
        and D.deployed_at <= CONVERT_TZ('{target_date_str} 23:59:59', 'Asia/Seoul', 'UTC')
        and mhr_maint.model_id is null
        AND S.deleted_at IS NULL
        AND G.region_name in ('남부RS팀','RS그룹','서울RS팀','중앙RS팀','경상RS팀','강남RS팀','프로젝트_루미','가맹영업팀')
    GROUP BY 1 , 2 , 3 , 4 , 5 , 6 , 7 , 8 , 9 , 10
    """
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        print(f"Error extracting data for {target_date_str}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='rich_deploy_used_time 추출 스크립트')
    parser.add_argument('--start_date', type=str, help='시작 일자 (YYYY-MM-DD)', nargs='?')
    parser.add_argument('--end_date', type=str, help='종료 일자 (YYYY-MM-DD)', nargs='?')
    parser.add_argument('--overwrite', action='store_true', help='이미 존재하는 파일도 덮어쓰기')
    
    # sys.argv 호환성을 위한 처리 (기존 스크립트들이 --overwrite를 인자 위치 무관하게 사용)
    # argparse와 겹칠 수 있으므로 알려진 인자만 파싱하고 위치 인자도 고려
    args_list = sys.argv[1:]
    overwrite = False
    if '--overwrite' in args_list:
        overwrite = True
        args_list.remove('--overwrite')
        
    if len(args_list) >= 2:
        start_date_str = args_list[0]
        end_date_str = args_list[1]
    else:
        # 명시되지 않은 경우 디폴트로 D-5 부터 D-1 까지 추출
        today = datetime.now()
        start_date_dt = today - timedelta(days=5)
        end_date_dt = today - timedelta(days=1)
        
        start_date_str = start_date_dt.strftime('%Y-%m-%d')
        end_date_str = end_date_dt.strftime('%Y-%m-%d')
        
    date_list = pd.date_range(start=start_date_str, end=end_date_str, freq='D')
    base_save_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_deploy_used_time"
    
    
    print(f"작업 기간: {start_date_str} ~ {end_date_str} (총 {len(date_list)}일)")
    print(f"저장 기본 경로: {base_save_path}")
    
    engine = get_engine()
    has_error = False
    
    for dt in date_list:
        target_date_str = dt.strftime('%Y-%m-%d')
        
        daily_folder_name = f"dt={target_date_str}"
        daily_folder_path = os.path.join(base_save_path, daily_folder_name)
        
        # 하위 디렉토리(dt=YYYY-MM-DD) 생성
        if not os.path.exists(daily_folder_path):
            os.makedirs(daily_folder_path, exist_ok=True)
        
        file_path = os.path.join(daily_folder_path, f"rich_deploy_used_time_{target_date_str}.parquet")
        
        if os.path.exists(file_path) and not overwrite:
            print(f"[{target_date_str}] 파일이 이미 존재하여 스킵합니다: {file_path}")
            continue
            
        print(f"[{target_date_str}] 데이터 추출 중...")
        start_time = time.time()
        
        df = extract_deploy_used_time(target_date_str, engine)
        
        if df is not None and not df.empty:
            try:
                # pandas to_parquet 저장 시 date 타입 호환성 확보
                if 'date' in df.columns:
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
    else:
        print("모든 작업이 성공적으로 완료되었습니다.")

if __name__ == '__main__':
    main()
