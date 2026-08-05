import polars as pl
import pandas as pd

def main():
    # 1. 26년도 상반기 Active 비율 확인
    print("--- 26년도 상반기 연령대별 Active 비율 ---")
    dates = ["2026-03-31", "2026-04-30", "2026-05-31", "2026-06-24"]
    for dt in dates:
        df = pl.read_parquet(f"/Users/galaxy/Google Drive/공유 드라이브/gbike.rich_user_segment/dt={dt}/rich_user_segment_{dt}.parquet")
        
        # 10대~30대 필터링
        df_target = df.filter(pl.col("age_group").is_in(["10~16세", "17~19세", "20대", "30대"]))
        
        # age_group 별 총 유저 수
        total_by_age = df_target.group_by("age_group").len(name="total_users")
        
        # age_group 별 active 유저 수
        active_by_age = df_target.filter(pl.col("segment") == "active").group_by("age_group").len(name="active_users")
        
        # 조인 및 비율 계산
        res = total_by_age.join(active_by_age, on="age_group", how="left").fill_null(0)
        res = res.with_columns(((pl.col("active_users") / pl.col("total_users")) * 100).alias("active_ratio"))
        print(f"Date: {dt}")
        print(res.sort("age_group"))
        print()

    # 2. 선호도별 세그먼트 비교 (가장 최근 26-06-24 기준)
    print("--- 26-06-24 기준 세그먼트별 favorite_type 비중 ---")
    df_latest = pl.read_parquet("/Users/galaxy/Google Drive/공유 드라이브/gbike.rich_user_segment/dt=2026-06-24/rich_user_segment_2026-06-24.parquet")
    
    # 세그먼트 별 총 유저
    seg_total = df_latest.group_by("segment").len(name="seg_total")
    
    # 세그먼트 & favorite_type 별 유저
    seg_fav = df_latest.group_by(["segment", "favorite_type"]).len(name="count")
    
    seg_fav_ratio = seg_fav.join(seg_total, on="segment").with_columns(
        ((pl.col("count") / pl.col("seg_total")) * 100).alias("ratio")
    )
    print(seg_fav_ratio.sort(["segment", "ratio"], descending=[False, True]))
    print()

    # 3. 16세 미만 전환 유저 (25-11-30 -> 26-06-24)
    print("--- 16세 미만 킥보드 -> 자전거 전환 유저 ---")
    df_before = pl.read_parquet("/Users/galaxy/Google Drive/공유 드라이브/gbike.rich_user_segment/dt=2025-11-30/rich_user_segment_2025-11-30.parquet")
    df_after = pl.read_parquet("/Users/galaxy/Google Drive/공유 드라이브/gbike.rich_user_segment/dt=2026-06-24/rich_user_segment_2026-06-24.parquet")
    
    # 10~16세 대상
    df_before_teens = df_before.filter(pl.col("age_group") == "10~16세").select(["user_id", "favorite_type"])
    df_after_teens = df_after.filter(pl.col("age_group") == "10~16세").select(["user_id", "favorite_type"])
    
    # 조인
    switched = df_before_teens.join(df_after_teens, on="user_id", suffix="_after")
    
    # 킥보드 -> 자전거
    switched_count = switched.filter((pl.col("favorite_type") == "킥보드") & (pl.col("favorite_type_after") == "자전거")).height
    total_teens_kick_before = df_before_teens.filter(pl.col("favorite_type") == "킥보드").height
    
    print(f"25년 11월 당시 10~16세 킥보드 선호 유저 수: {total_teens_kick_before}")
    print(f"그 중 26년 6월에 자전거 선호로 전환된 유저 수: {switched_count}")

if __name__ == "__main__":
    main()
