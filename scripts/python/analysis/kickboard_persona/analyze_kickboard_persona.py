import sys
import os
import polars as pl
from datetime import datetime

# sys.path 설정
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from scripts.python.utils.read_rich_user_polars import load_rich_user_polars, apply_actual_age_logic

def analyze_kickboard_persona():
    print("Loading rich_user data...")
    # 최신 사용자 데이터 위주로 로드
    df_user = load_rich_user_polars(['2024', '2025', '2026'])
    if df_user.is_empty():
        print("No user data found.")
        return
        
    df_user = apply_actual_age_logic(df_user)
    
    print("Loading rich_user_segment data...")
    segment_base_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_user_segment"
    segment_dirs = [d for d in os.listdir(segment_base_path) if d.startswith('dt=')]
    latest_segment_dir = sorted(segment_dirs)[-1]
    
    lf_segment = pl.scan_parquet(os.path.join(segment_base_path, latest_segment_dir, "*.parquet"))
    lf_segment = lf_segment.select(["user_id", "favorite_type"])
    df_segment = lf_segment.collect()
    
    print("Joining data...")
    df_joined = df_user.join(df_segment, on="user_id", how="inner")
    
    # 킥보드 선호 유저 필터링
    df_kickboard = df_joined.filter(pl.col("favorite_type") == "킥보드")
    
    print("Aggregating demographic data...")
    df_kickboard = df_kickboard.with_columns([
        pl.col("gender").fill_null("알수없음"),
        pl.col("now_age_group").fill_null("알수없음")
    ])
    
    df_agg = (
        df_kickboard.group_by(["now_age_group", "gender"])
        .agg(pl.len().alias("user_count"))
        .sort(["now_age_group", "gender"])
    )
    
    total_kickboard_users = df_kickboard.height
    df_agg = df_agg.with_columns(
        (pl.col("user_count") / total_kickboard_users * 100).round(1).alias("ratio_pct")
    )
    
    # 결과 저장
    result_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../results/kickboard_persona/kickboard_persona_results.xlsx"))
    
    # xlsxwriter 엔진 사용을 위해 pandas로 변환하여 저장
    df_agg.to_pandas().to_excel(result_path, index=False)
    
    print(f"Analysis completed. Results saved to: {result_path}")
    
if __name__ == "__main__":
    analyze_kickboard_persona()
