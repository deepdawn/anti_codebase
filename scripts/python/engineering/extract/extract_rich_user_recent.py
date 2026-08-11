import os
import sys
import pandas as pd
import time
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils.test_mysql_conn import get_engine
from utils.read_rich_orders_polars import load_rich_orders_polars

def extract_rich_user_recent(start_date_str, end_date_str, engine):
    """지정된 날짜 범위의 유저 데이터를 추출"""
    
    query = f"""
    select *,
            case
                when r.execute_age is null then '알수없음'
                when r.execute_age >= 10 and r.execute_age < 17 then '10~16세'
                when r.execute_age >= 17 and r.execute_age < 20 then '17~19세'
                when r.execute_age >= 20 and r.execute_age < 30 then '20대'
                when r.execute_age >= 30 and r.execute_age < 40 then '30대'
                when r.execute_age >= 40 and r.execute_age < 50 then '40대'
                when r.execute_age >= 50 and r.execute_age < 60 then '50대'
            else '기타' end as age_group
    from (
            select date(CONVERT_TZ(FROM_UNIXTIME(add_time), 'UTC', 'Asia/Seoul')) as register_dt,
                   date(CONVERT_TZ(FROM_UNIXTIME(login_time), 'UTC', 'Asia/Seoul')) as last_login_dt,
                   user_id,nickname,region_id,mobile,first_order_id,latest_order_id,register_region_id,
                   birthday,
                CASE
                    WHEN r.gender IS NULL THEN '알수없음'
                    WHEN MOD(r.gender, 2) = 1 THEN '남자'
                    ELSE '여자'
                END AS gender,
                CASE
                    WHEN r.birthday IS NULL THEN null
                    ELSE
                        FLOOR(
                            (EXTRACT(YEAR FROM CURRENT_DATE) * 10000 + EXTRACT(MONTH FROM CURRENT_DATE) * 100 + EXTRACT(DAY FROM CURRENT_DATE)
                            - r.birthday) / 10000
                        )
                END AS execute_age
            from gbike.rich_user r
            where add_time >= UNIX_TIMESTAMP('{start_date_str} 00:00:00') - 32400
              and add_time <= UNIX_TIMESTAMP('{end_date_str} 23:59:59') - 32400
              and country_code = 'kr'
    ) r
    """
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection)
        return df
    except Exception as e:
        print(f"Error extracting data: {e}")
        return None

def extract_rich_user_by_ids(user_ids, engine):
    """지정된 user_id 리스트에 해당하는 유저 데이터를 추출 (청크 분할)"""
    chunk_size = 10000
    all_dfs = []
    
    for i in range(0, len(user_ids), chunk_size):
        chunk = user_ids[i:i+chunk_size]
        id_list = ",".join(map(str, chunk))
        
        query = f"""
        select *,
                case
                    when r.execute_age is null then '알수없음'
                    when r.execute_age >= 10 and r.execute_age < 17 then '10~16세'
                    when r.execute_age >= 17 and r.execute_age < 20 then '17~19세'
                    when r.execute_age >= 20 and r.execute_age < 30 then '20대'
                    when r.execute_age >= 30 and r.execute_age < 40 then '30대'
                    when r.execute_age >= 40 and r.execute_age < 50 then '40대'
                    when r.execute_age >= 50 and r.execute_age < 60 then '50대'
                else '기타' end as age_group
        from (
                select date(CONVERT_TZ(FROM_UNIXTIME(add_time), 'UTC', 'Asia/Seoul')) as register_dt,
                       date(CONVERT_TZ(FROM_UNIXTIME(login_time), 'UTC', 'Asia/Seoul')) as last_login_dt,
                       user_id,nickname,region_id,mobile,first_order_id,latest_order_id,register_region_id,
                       birthday,
                    CASE
                        WHEN r.gender IS NULL THEN '알수없음'
                        WHEN MOD(r.gender, 2) = 1 THEN '남자'
                        ELSE '여자'
                    END AS gender,
                    CASE
                        WHEN r.birthday IS NULL THEN null
                        ELSE
                            FLOOR(
                                (EXTRACT(YEAR FROM CURRENT_DATE) * 10000 + EXTRACT(MONTH FROM CURRENT_DATE) * 100 + EXTRACT(DAY FROM CURRENT_DATE)
                                - r.birthday) / 10000
                            )
                    END AS execute_age
                from gbike.rich_user r
                where user_id IN ({id_list})
        ) r
        """
        try:
            with engine.connect() as connection:
                df = pd.read_sql(query, connection)
                all_dfs.append(df)
        except Exception as e:
            print(f"Error extracting data chunk: {e}")
            
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return None

def main():
    base_save_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_user"
    folder_name = "rich_user_recent"
    folder_path = os.path.join(base_save_path, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    file_path = os.path.join(folder_path, "rich_user_recent.parquet")
    
    # 최근 7일(어제 포함) 가입/변경 유저 추출
    now = datetime.now()
    target_end_dt = now - timedelta(days=1)
    end_date_str = target_end_dt.strftime('%Y-%m-%d')
    
    target_start_dt = target_end_dt - timedelta(days=6)
    start_date_str = target_start_dt.strftime('%Y-%m-%d')
    
    engine = get_engine()
    
    print(f"추출 기간: {start_date_str} ~ {end_date_str}")
    print(f"저장 경로: {file_path}")
    
    print("데이터 추출 중...")
    start_time = time.time()
    
    df = extract_rich_user_recent(start_date_str, end_date_str, engine)
    
    # 대안 C: 어제 기준 운행 이력이 있는 유저 중 누락된 유저(Anti-Join) 추출
    RUN_ACTIVE_USER_EXTRACTION = True
    
    if RUN_ACTIVE_USER_EXTRACTION:
        print(f"어제({end_date_str}) 운행 유저 중 과거(마스터 파일 누락) 유저를 탐색하여 보완합니다...")
        df_orders = load_rich_orders_polars(end_date_str, end_date_str, columns=["user_id"])
        if df_orders is not None and not df_orders.is_empty():
            all_file_path = os.path.join(base_save_path, "rich_user_all.parquet")
            existing_user_ids = set()
            
            if os.path.exists(all_file_path):
                import polars as pl
                existing_user_ids = set(pl.scan_parquet(all_file_path).select("user_id").collect().to_series().to_list())
                
            active_user_ids = set(df_orders.select("user_id").unique().to_series().to_list())
            missing_user_ids = list(active_user_ids - existing_user_ids)
            
            print(f"어제 운행한 유저 수: {len(active_user_ids):,}명 / 기존 마스터에 누락된 유저 수: {len(missing_user_ids):,}명")
            
            if missing_user_ids:
                df_active = extract_rich_user_by_ids(missing_user_ids, engine)
                if df_active is not None and not df_active.empty:
                    print(f"누락 유저 데이터 추가 추출 완료 (건수: {len(df_active):,})")
                    # 기존 df와 합치기
                    if df is not None and not df.empty:
                        df = pd.concat([df, df_active], ignore_index=True)
                    else:
                        df = df_active
    
    if df is not None and not df.empty:
        try:
            # 덮어쓰기 로직이므로 바로 저장 (기존 파일 있어도 덮어씀)
            df.to_parquet(file_path, index=False)
            elapsed_time = time.time() - start_time
            print(f"성공적으로 덮어쓰기 완료되었습니다. (건수: {len(df):,}, 소요시간: {elapsed_time:.2f}초)")
            
            # rich_user_all.parquet 에 업데이트 (Upsert)
            all_file_path = os.path.join(base_save_path, "rich_user_all.parquet")
            if os.path.exists(all_file_path):
                print("rich_user_all.parquet 파일 병합(Upsert)을 시작합니다...")
                import polars as pl
                
                # 기존 all 파일과 이번에 추출된 파일을 동시에 스캔
                # integer_cast='allow-float' 옵션을 주어 데이터 타입 충돌 방지
                lf = pl.scan_parquet(
                    [all_file_path, file_path],
                    cast_options=pl.ScanCastOptions(integer_cast='allow-float')
                )
                
                # user_id 기준으로 중복 제거하되, 가장 마지막(이번 달 추출본) 데이터를 유지(keep='last')
                df_upserted = lf.collect().unique(subset=["user_id"], keep="last")
                df_upserted.write_parquet(all_file_path)
                
                print(f"rich_user_all.parquet 업데이트 완료! (최종 유저 수: {df_upserted.height:,})")
            else:
                print("rich_user_all.parquet 파일이 존재하지 않아 병합은 생략합니다.")
                
        except Exception as e:
            print(f"파일 저장 중 오류 발생: {e}")
    elif df is not None and df.empty:
        print(f"해당하는 데이터가 없습니다.")
    else:
        print(f"추출 실패.")

if __name__ == '__main__':
    main()
