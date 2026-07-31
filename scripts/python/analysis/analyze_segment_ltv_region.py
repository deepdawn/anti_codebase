import os
import polars as pl
import argparse

def analyze(target_date_str):
    file_path = f"/Users/galaxy.jang/Google Drive/공유 드라이브/gbike.rich_user_segment/dt={target_date_str}/rich_user_segment_{target_date_str}.parquet"
    
    if not os.path.exists(file_path):
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return

    print(f"--- [성수기: {target_date_str}] 데이터 로드 및 분석 시작 ---")
    df = pl.read_parquet(file_path)

    # 1. 세그먼트별 LTV 비교
    print("\n[1] 세그먼트별 평균 LTV (CLTV) 비교")
    cltv_stats = df.group_by("segment").agg(
        pl.len().alias("user_count"),
        pl.col("cltv").mean().round(0).alias("avg_cltv")
    ).sort("avg_cltv", descending=True)
    print(cltv_stats)

    # 2. 대지역별 세그먼트 분포
    print("\n[2] 대지역별 세그먼트 분포 비율 (%)")
    # 대지역별 총 유저수
    region_totals = df.group_by("대지역").len().rename({"len": "region_total"})
    
    # 대지역 x 세그먼트별 유저수
    region_seg_counts = df.group_by(["대지역", "segment"]).len()
    
    # 조인 및 비율 계산
    region_seg_stats = region_seg_counts.join(region_totals, on="대지역").with_columns(
        (pl.col("len") / pl.col("region_total") * 100).round(1).alias("ratio(%)")
    )
    
    # 피벗 테이블 생성 (대지역별 x 세그먼트)
    pivot_df = region_seg_stats.pivot(
        values="ratio(%)",
        index="대지역",
        columns="segment",
        aggregate_function="first"
    ).fill_null(0.0)
    
    print(pivot_df)


if __name__ == "__main__":
    # 백필이 완료되는 성수기 기준일 (2026-06-24)로 기본 설정
    analyze("2026-06-24")
