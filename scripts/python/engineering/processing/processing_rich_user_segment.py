import os
import sys
import argparse
from datetime import datetime, timedelta
import polars as pl

# utils 패키지 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../utils'))
from read_rich_orders_polars import load_rich_orders_polars

def calculate_user_segments(target_date_str):
    target_date_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    
    # 운행 이력은 최근 365일치만 스캔하면 모든 세그먼트 조건을 판별할 수 있습니다.
    start_date_dt = target_date_dt - timedelta(days=365)
    start_date_str = start_date_dt.strftime("%Y-%m-%d")
    
    print(f"[{target_date_str} 기준] 유저 세그먼트 계산을 시작합니다.")
    print(f"운행 이력 로드 기간: {start_date_str} ~ {target_date_str}")
    
    # 1. rich_orders 로드
    # user_id, dt(운행일시), vehicle_type, pay_amount, out_of_area_charge 컬럼이 필요합니다.
    df_orders = load_rich_orders_polars(start_date_str, target_date_str, columns=["user_id", "dt", "vehicle_type", "pay_amount", "out_of_area_charge"])
    
    if df_orders.is_empty():
        print("해당 기간의 운행 기록이 존재하지 않아 스크립트를 종료합니다.")
        return
        
    # dt 컬럼을 확실히 Datetime 타입으로 통일
    df_orders = df_orders.with_columns(pl.col("dt").cast(pl.Datetime))
    
    # 2. user별 운행 요약 통계 집계
    print("유저별 운행 통계를 집계합니다...")
    target_date_polars_lit = pl.lit(target_date_dt)
    thirty_days_ago_lit = pl.lit(target_date_dt - timedelta(days=30))
    
    df_orders_grouped = df_orders.group_by("user_id").agg(
        pl.col("dt").max().alias("last_ride_dt"),
        pl.col("dt").filter(pl.col("dt") >= thirty_days_ago_lit).count().alias("rides_last_30d"),
        pl.len().alias("total_rides_365d"),
        pl.col("vehicle_type").filter(pl.col("vehicle_type") == "Scooter").count().alias("scooter_rides_365d"),
        pl.col("vehicle_type").filter(pl.col("vehicle_type") == "Bicycle").count().alias("bicycle_rides_365d"),
        (pl.col("pay_amount").fill_null(0) + pl.col("out_of_area_charge").fill_null(0)).sum().alias("monetary_365d")
    )
    
    # 3. rich_user 로드
    print("전체 유저 정보를 로드합니다...")
    user_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_user/rich_user_all.parquet"
    df_users = pl.scan_parquet(user_path).select(["user_id", "register_dt", "region_id", "age_group", "gender"]).collect()
    df_users = df_users.with_columns(pl.col("register_dt").cast(pl.Datetime))
    df_users = df_users.filter(pl.col("register_dt").cast(pl.Date) <= target_date_polars_lit.cast(pl.Date))
    
    print("지역 정보를 로드하고 유저 정보와 결합합니다...")
    region_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_region/rich_region_hierarchy.parquet"
    df_region = pl.scan_parquet(region_path).select(["region_id", "대지역", "중지역", "소지역"]).collect()
    df_users = df_users.join(df_region, on="region_id", how="inner")
    
    # 4. Join
    print("유저 정보와 운행 통계를 병합합니다...")
    df_joined = df_users.join(df_orders_grouped, on="user_id", how="left")
    
    # 5. 파생 변수 계산
    df_res = df_joined.with_columns(
        (target_date_polars_lit.cast(pl.Date) - pl.col("register_dt").cast(pl.Date)).dt.total_days().alias("days_since_reg"),
        pl.coalesce(["last_ride_dt", "register_dt"]).alias("last_ride_dt_eff"),
        pl.col("rides_last_30d").fill_null(0),
        pl.col("total_rides_365d").fill_null(0),
        pl.col("scooter_rides_365d").fill_null(0),
        pl.col("bicycle_rides_365d").fill_null(0),
        pl.col("monetary_365d").fill_null(0)
    ).with_columns(
        (target_date_polars_lit.cast(pl.Date) - pl.col("last_ride_dt_eff").cast(pl.Date)).dt.total_days().alias("days_since_eff")
    )
    
    # 6. 세그먼트 로직
    # 조건1: 가입 30일 이내 & 운행횟수 0~1회 -> acquisition
    # 조건2: 최근 30일 이내 운행 4회 이상 -> active
    # 조건3: 최근 30일 이내 운행 1~3회 -> light_active
    # 조건4: (운행이 없었을 시 가입일로 대체한) 마지막 기준일이 90일 이내 -> inactive
    # 조건5: (운행이 없었을 시 가입일로 대체한) 마지막 기준일이 120일 이내 -> dormant
    # 조건6: 마지막 기준일이 365일 이내 -> churn
    # 그 외 (365일 초과) -> churn_over_365
    print("고객 세그먼트를 분류합니다...")
    segment_expr = (
        pl.when((pl.col("days_since_reg") <= 30) & (pl.col("total_rides_365d") <= 1)).then(pl.lit("acquisition"))
        .when(pl.col("rides_last_30d") >= 4).then(pl.lit("active"))
        .when(pl.col("rides_last_30d") > 0).then(pl.lit("light_active"))
        .when(pl.col("days_since_eff") <= 90).then(pl.lit("inactive"))
        .when(pl.col("days_since_eff") <= 120).then(pl.lit("dormant"))
        .when(pl.col("days_since_eff") <= 365).then(pl.lit("churn"))
        .otherwise(pl.lit("churn_over_365"))
    )
    
    print("주 이용수단을 판별합니다...")
    favorite_type_expr = (
        pl.when(pl.col("total_rides_365d") == 0).then(pl.lit("구분불가"))
        .when((pl.col("scooter_rides_365d") / pl.col("total_rides_365d")) >= 0.6).then(pl.lit("킥보드"))
        .when((pl.col("bicycle_rides_365d") / pl.col("total_rides_365d")) >= 0.6).then(pl.lit("자전거"))
        .otherwise(pl.lit("혼합"))
    )
    
    print("RFM 스코어 및 CLTV를 계산합니다...")
    total_users = df_res.height
    df_res = df_res.with_columns(
        pl.col("days_since_eff").rank(method="average", descending=True).alias("r_rank"),
        pl.col("total_rides_365d").rank(method="average").alias("f_rank"),
        pl.col("monetary_365d").rank(method="average").alias("m_rank")
    ).with_columns(
        ((pl.col("r_rank") / total_users) * 5).ceil().clip(1, 5).cast(pl.Int32).alias("recency_score"),
        ((pl.col("f_rank") / total_users) * 5).ceil().clip(1, 5).cast(pl.Int32).alias("frequency_score"),
        ((pl.col("m_rank") / total_users) * 5).ceil().clip(1, 5).cast(pl.Int32).alias("monetary_score")
    ).with_columns(
        pl.concat_str([pl.col("recency_score"), pl.col("frequency_score"), pl.col("monetary_score")]).alias("rfm_score")
    )

    # Expected Lifespan mapping
    # R=5 -> 365, R=4 -> 180, R=3 -> 90, R=1,2 -> 0
    lifespan_expr = (
        pl.when(pl.col("recency_score") == 5).then(365)
        .when(pl.col("recency_score") == 4).then(180)
        .when(pl.col("recency_score") == 3).then(90)
        .otherwise(0)
    )

    df_res = df_res.with_columns(
        (pl.col("monetary_365d") / pl.max_horizontal(pl.col("days_since_reg"), 1)).alias("daily_value"),
        lifespan_expr.alias("expected_lifespan_days")
    ).with_columns(
        (pl.col("monetary_365d") + (pl.col("daily_value") * pl.col("expected_lifespan_days"))).alias("cltv")
    )
    
    df_final = df_res.with_columns(
        segment_expr.alias("segment"),
        favorite_type_expr.alias("favorite_type")
    ).select([
        "user_id", "age_group", "gender", "대지역", "중지역", "소지역", "segment", "favorite_type",
        "register_dt", "last_ride_dt", 
        "days_since_reg", "days_since_eff", 
        "rides_last_30d", "total_rides_365d", "scooter_rides_365d", "bicycle_rides_365d",
        "monetary_365d", "rfm_score", "cltv"
    ])
    
    # 7. 저장
    base_output_dir = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_user_segment"
    output_dir = os.path.join(base_output_dir, f"dt={target_date_str}")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f"rich_user_segment_{target_date_str}.parquet")
    df_final.write_parquet(output_path)
    print(f"결과가 저장되었습니다: {output_path}")
    
    # 통계 출력
    print("\n[세그먼트 분포 요약]")
    stats = df_final.group_by("segment").len(name="count").sort("count", descending=True)
    total_users = df_final.height
    stats = stats.with_columns(
        ((pl.col("count") / total_users) * 100).round(1).alias("ratio(%)")
    )
    print(stats)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="유저 세그먼트 추출 스크립트")
    # 기본값을 None으로 설정하여 미입력 여부 확인
    parser.add_argument("--target-date", type=str, default=None, help="계산 시점 기준일 (YYYY-MM-DD).")
    
    args = parser.parse_args()
    
    if args.target_date:
        calculate_user_segments(args.target_date)
    else:
        print("target-date가 지정되지 않았습니다. 누락된 날짜를 탐색하여 자동 보완(Backfill)을 진행합니다.")
        base_output_dir = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_user_segment"
        
        # 어제 날짜까지 확인 (마이크로초 차이 방지를 위해 .date() 사용)
        today_date = datetime.now().date()
        end_date = today_date - timedelta(days=1)
        # 백필 기준 시작일 지정 (7일 이전부터 어제자까지 스캔)
        start_date = today_date - timedelta(days=8)
        
        curr_date = start_date
        missing_dates = []
        while curr_date <= end_date:
            dt_str = curr_date.strftime("%Y-%m-%d")
            file_path = os.path.join(base_output_dir, f"dt={dt_str}", f"rich_user_segment_{dt_str}.parquet")
            
            if not os.path.exists(file_path):
                missing_dates.append(dt_str)
                
            curr_date += timedelta(days=1)
            
        if not missing_dates:
            print(f"{start_date.strftime('%Y-%m-%d')} 부터 {end_date.strftime('%Y-%m-%d')} 까지 모든 파케이 파일이 정상적으로 존재합니다.")
        else:
            print(f"총 {len(missing_dates)}일치의 누락 데이터를 감지하여 자동 추출을 시작합니다.")
            for dt_str in missing_dates:
                calculate_user_segments(dt_str)
