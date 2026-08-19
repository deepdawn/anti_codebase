import os
import sys
import argparse
from datetime import datetime, timedelta
import polars as pl
import h3

def process_h3_grid_stats(target_date_str):
    target_date_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    print(f"[{target_date_str}] H3 그리드 집계를 시작합니다.")
    
    # 1. 경로 설정
    base_dir = os.path.expanduser("~/Google Drive/공유 드라이브")
    orders_path = os.path.join(base_dir, f"gbike.rich_orders/dt={target_date_str}/rich_orders_{target_date_str}.parquet")
    segment_path = os.path.join(base_dir, f"gbike.rich_user_segment/dt={target_date_str}/rich_user_segment_{target_date_str}.parquet")
    region_path = os.path.join(base_dir, "gbike.rich_region/rich_region_hierarchy.parquet")
    
    if not os.path.exists(orders_path):
        print(f"운행 기록 파케이 파일이 존재하지 않습니다: {orders_path}")
        return
        
    if not os.path.exists(segment_path):
        print(f"유저 세그먼트 파케이 파일이 존재하지 않습니다: {segment_path}")
        return
        
    if not os.path.exists(region_path):
        print(f"지역 마스터 파일이 존재하지 않습니다: {region_path}")
        return
        
    # 2. 데이터 로드
    df_orders = pl.read_parquet(orders_path)
    df_segment = pl.read_parquet(segment_path)
    df_region = pl.read_parquet(region_path)
    
    # 3. 유저 세그먼트 가공 (demo_group 생성)
    # gender: "남자" -> "남성", "여자" -> "여성"
    df_segment = df_segment.with_columns(
        pl.col("gender").str.replace("남자", "남성").str.replace("여자", "여성").alias("gender_formatted")
    ).with_columns(
        (pl.col("age_group") + pl.lit(" ") + pl.col("gender_formatted")).alias("demo_group")
    )
    
    # 4. orders 데이터 가공 (시간대, H3 등)
    # hour 추출 및 time_slot 파생
    df_orders = df_orders.with_columns(
        pl.col("st_dt").dt.hour().alias("hour")
    ).with_columns(
        pl.when(pl.col("hour") < 7).then(pl.lit("심야(0~7)"))
        .when(pl.col("hour") < 11).then(pl.lit("출근(7~11)"))
        .when(pl.col("hour") < 16).then(pl.lit("낮(11~16)"))
        .when(pl.col("hour") < 20).then(pl.lit("퇴근(16~20)"))
        .otherwise(pl.lit("저녁(20~24)")).alias("time_slot")
    )
    
    # H3 변환 (Resolution 9)
    # H3 라이브러리(v4) 함수 latlng_to_cell 사용. Polars에서 빠르게 적용하기 위해 Series로 변환
    def apply_h3(lat_series, lng_series):
        lat_list = lat_series.to_list()
        lng_list = lng_series.to_list()
        # 유효하지 않은 좌표 방어 로직 추가
        h3_cells = []
        for lat, lng in zip(lat_list, lng_list):
            if lat is not None and lng is not None and -90 <= lat <= 90:
                try:
                    h3_cells.append(h3.latlng_to_cell(lat, lng, 9))
                except:
                    h3_cells.append(None)
            else:
                h3_cells.append(None)
        return pl.Series(h3_cells)
    
    start_h3_series = apply_h3(df_orders["start_lat"], df_orders["start_lng"])
    end_h3_series = apply_h3(df_orders["end_lat"], df_orders["end_lng"])
    
    df_orders = df_orders.with_columns([
        start_h3_series.alias("start_h3"),
        end_h3_series.alias("end_h3")
    ])
    
    # 빈 H3가 있는 row 제거
    df_orders = df_orders.drop_nulls(subset=["start_h3", "end_h3"])
    
    # 5. 조인 (Orders + User Segment + Region)
    # User Segment와 Join
    df_joined = df_orders.join(df_segment.select(["user_id", "demo_group"]), on="user_id", how="left")
    
    # Region과 Join (low_region_id = region_id)
    # null인 부분 방지 처리 (unknown)
    df_joined = df_joined.join(
        df_region.select(["region_id", "대지역", "중지역", "소지역"]), 
        left_on="low_region_id", 
        right_on="region_id", 
        how="left"
    )
    
    df_joined = df_joined.with_columns([
        pl.col("대지역").fill_null("알수없음"),
        pl.col("중지역").fill_null("알수없음"),
        pl.col("소지역").fill_null("알수없음"),
        pl.col("demo_group").fill_null("알수없음")
    ])
    
    # "가맹영업팀" 제외 처리
    df_joined = df_joined.filter(pl.col("대지역") != "가맹영업팀")
    
    # 6. 출발지 집계 (Departures)
    group_cols = [pl.lit(target_date_str).alias("dt"), "time_slot", "대지역", "중지역", "소지역", "vehicle_type"]
    
    df_departures = df_joined.group_by(group_cols + ["start_h3"]).agg([
        pl.len().alias("departure_count"),
        pl.col("duration_minutes").mean().alias("avg_duration_minutes")
    ]).rename({"start_h3": "h3_index"})
    
    # 7. 도착지 집계 (Arrivals)
    df_arrivals = df_joined.group_by(group_cols + ["end_h3"]).agg([
        pl.len().alias("arrival_count")
    ]).rename({"end_h3": "h3_index"})
    
    # 7.5. 출발+도착 통합 최빈 유저 그룹 산출 ("알수없음" 제외)
    df_start_users = df_joined.select(group_cols + ["start_h3", "demo_group"]).rename({"start_h3": "h3_index"})
    df_end_users = df_joined.select(group_cols + ["end_h3", "demo_group"]).rename({"end_h3": "h3_index"})
    
    df_all_users = pl.concat([df_start_users, df_end_users])
    
    # 알수없음 및 null h3 제외
    df_valid_users = df_all_users.drop_nulls(subset=["h3_index"]).filter(pl.col("demo_group") != "알수없음")
    
    # 그리드별 최빈 유저 그룹 산출
    df_user_mode = df_valid_users.group_by(group_cols + ["h3_index"]).agg([
        pl.col("demo_group").mode().first().alias("main_user_group")
    ])
    
    # 8. 출발/도착 데이터 결합 및 최빈값 병합 (Outer Join)
    join_keys = ["dt", "time_slot", "대지역", "중지역", "소지역", "vehicle_type", "h3_index"]
    
    df_final = df_departures.join(df_arrivals, on=join_keys, how="full", coalesce=True)
    df_final = df_final.join(df_user_mode, on=join_keys, how="left")
    
    # NULL 값 0으로 채우고 Int32로 캐스팅 (Kepler.gl Arrow 호환성)
    df_final = df_final.with_columns([
        pl.col("departure_count").fill_null(0).cast(pl.Int32),
        pl.col("arrival_count").fill_null(0).cast(pl.Int32),
        pl.col("main_user_group").fill_null("알수없음")
    ])
    
    # 9. 결과 저장 (Kepler.gl 연동 호환성을 위해 fastparquet 엔진 사용)
    # fastparquet는 Arrow 메타데이터를 일절 남기지 않아 Kepler.gl의 파서 버그(Eoe)를 원천적으로 방지합니다.
    output_dir = os.path.join(base_dir, f"gbike.rich_h3_grid_stats/dt={target_date_str}")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"rich_h3_grid_stats_{target_date_str}.parquet")
    
    df_pd = df_final.to_pandas()
    # 명시적으로 string/object 컬럼을 기본 문자열 타입으로 보정
    for col in df_pd.select_dtypes(include=['string', 'object']).columns:
        df_pd[col] = df_pd[col].astype(str)
        
    df_pd.to_parquet(output_path, engine='fastparquet', compression='snappy')
    print(f"[{target_date_str}] 성공적으로 집계 및 저장 완료: {output_path} (총 {df_final.height}개 그리드)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-date", type=str, default=None, help="특정 일자 처리 (예: 2026-08-12)")
    parser.add_argument("--start-date", type=str, default=None, help="백필 시작 일자 (예: 2026-01-01)")
    parser.add_argument("--end-date", type=str, default=None, help="백필 종료 일자 (예: 2026-08-12)")
    args = parser.parse_args()
    
    if args.target_date:
        process_h3_grid_stats(args.target_date)
    elif args.start_date and args.end_date:
        print(f"{args.start_date} 부터 {args.end_date} 까지 명시적 백필(Backfill)을 진행합니다.")
        start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        
        curr_dt = start_dt
        while curr_dt <= end_dt:
            dt_str = curr_dt.strftime("%Y-%m-%d")
            try:
                process_h3_grid_stats(dt_str)
            except Exception as e:
                print(f"[{dt_str}] 처리 중 오류 발생: {e}")
            curr_dt += timedelta(days=1)
    else:
        print("명시적 인자가 없습니다. 최근 8일치 누락본 자동 보완(Backfill)을 진행합니다.")
        base_output_dir = os.path.expanduser("~/Google Drive/공유 드라이브/gbike.rich_h3_grid_stats")
        
        today_date = datetime.now().date()
        end_date = today_date - timedelta(days=1)
        start_date = today_date - timedelta(days=8)
        
        curr_date = start_date
        missing_dates = []
        while curr_date <= end_date:
            dt_str = curr_date.strftime("%Y-%m-%d")
            file_path = os.path.join(base_output_dir, f"dt={dt_str}", f"rich_h3_grid_stats_{dt_str}.parquet")
            
            if not os.path.exists(file_path):
                missing_dates.append(dt_str)
                
            curr_date += timedelta(days=1)
            
        if not missing_dates:
            print(f"{start_date.strftime('%Y-%m-%d')} 부터 {end_date.strftime('%Y-%m-%d')} 까지 파일이 모두 존재합니다.")
        else:
            print(f"총 {len(missing_dates)}일치의 누락 데이터를 추출합니다: {missing_dates}")
            for dt_str in missing_dates:
                process_h3_grid_stats(dt_str)
