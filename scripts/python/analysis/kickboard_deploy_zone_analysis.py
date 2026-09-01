import sys
import os
import polars as pl
import pandas as pd
from datetime import datetime, timedelta
import requests
import json
import concurrent.futures

GEMINI_API_KEY = "AIzaSyCwQ8bN7CCiGB-kUdgO0K727Ec45LBBMn0"

def get_gemini_insights(zone_name, device_type, deploy_count, usage_count, wait_time, peak_hours):
    prompt = f"""
    당신은 모빌리티 서비스 '지바이크'의 데이터 분석가입니다.
    다음은 '{zone_name}' 배치존의 '{device_type}' 운영 데이터 요약입니다.
    
    - 배치존명: {zone_name}
    - 기기: {device_type}
    - 90일간 배치수: {deploy_count}대
    - 90일간 출루수: {usage_count}회
    - 평균 출루 대기시간: {wait_time:.1f}시간
    - 주요 출루 피크 시간대(Top 3): {', '.join([str(h)+'시' for h in peak_hours]) if peak_hours else '특정 피크 없음'}
    
    이 데이터를 바탕으로 이 구역을 '{device_type} 전용존'으로 운영하기 적합한 이유를 분석해주세요.
    아래 JSON 형식에 맞추어 응답하세요. 다른 설명 없이 오직 JSON만 반환하세요.
    {{
        "reason": "해당 구역의 특징과 전용존으로 추천하는 사유 1문장",
        "strategy": "피크 시간을 고려한 최적의 배치 시간대 전략 1문장"
    }}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"}
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        if 'candidates' not in data:
            print(f"API Error Response: {data}")
        text_content = data['candidates'][0]['content']['parts'][0]['text']
        result = json.loads(text_content)
        return result.get("reason", ""), result.get("strategy", "")
    except Exception as e:
        print(f"Error fetching insights for {zone_name}: {e}")
        return "", ""

def main():
    camp_name = sys.argv[1] if len(sys.argv) > 1 else "강릉캠프"
    print(f"Running analysis for: {camp_name}")
    
    base_dir = os.path.expanduser("~/Google Drive/공유 드라이브")
    zone_usages_path = f"{base_dir}/gbike.rich_deploy_zone_usages"
    used_time_path = f"{base_dir}/gbike.rich_deploy_used_time"
    by_time_path = f"{base_dir}/gbike.rich_deploy_by_time"
    
    df_temp = pl.scan_parquet(f"{zone_usages_path}/**/*.parquet", extra_columns='ignore').select("date").max().collect()
    max_date = df_temp["date"][0]
    if max_date is None: return
    min_date = max_date - timedelta(days=90)
    print(f"Data period: {min_date} ~ {max_date}")

    print("Loading zone usages...")
    lf_usages = pl.scan_parquet(f"{zone_usages_path}/**/*.parquet", extra_columns='ignore').filter(
        (pl.col("date") >= min_date) & (pl.col("중지역") == camp_name)
    )
    
    df_zone_veh = (
        lf_usages.group_by(["배치존명", "기종"])
        .agg([pl.sum("배치수").alias("배치수_sum"), pl.sum("출루수").alias("출루수_sum")])
        .collect()
    )
    
    df_kick = df_zone_veh.filter(pl.col("기종") == "scooter").rename({"배치수_sum": "kb_deploy", "출루수_sum": "kb_usage"}).drop("기종")
    df_bike = df_zone_veh.filter(pl.col("기종") == "bicycle").rename({"배치수_sum": "bk_deploy", "출루수_sum": "bk_usage"}).drop("기종")
    
    df_zones = df_kick.join(df_bike.select(["배치존명", "bk_deploy", "bk_usage"]), on="배치존명", how="full", coalesce=True).fill_null(0)
    df_zones = df_zones.with_columns([
        (pl.col("kb_usage") / pl.col("kb_deploy")).fill_nan(0).fill_null(0).alias("kb_usage_rate"),
        (pl.col("bk_usage") / pl.col("bk_deploy")).fill_nan(0).fill_null(0).alias("bk_usage_rate")
    ])

    print("Loading wait times...")
    # Get wait times for BOTH vehicles
    lf_time = pl.scan_parquet(f"{used_time_path}/**/*.parquet", extra_columns='ignore').filter(
        (pl.col("date") >= min_date) & (pl.col("중지역") == camp_name)
    )
    df_wait = (
        lf_time.group_by(["배치존명", "기종"])
        .agg(pl.mean("출루까지 시간").alias("avg_wait_time"))
        .collect()
    )
    df_wait_kb = df_wait.filter(pl.col("기종")=="scooter").rename({"avg_wait_time": "kb_avg_wait_time"}).select(["배치존명", "kb_avg_wait_time"])
    df_wait_bk = df_wait.filter(pl.col("기종")=="bicycle").rename({"avg_wait_time": "bk_avg_wait_time"}).select(["배치존명", "bk_avg_wait_time"])
    
    df_final = df_zones.join(df_wait_kb, on="배치존명", how="left").join(df_wait_bk, on="배치존명", how="left")

    print("Filtering top zones...")
    # Kickboard top 10
    df_kb_filtered = df_final.filter((pl.col("kb_deploy") >= 50) & (pl.col("kb_usage") > pl.col("bk_usage") * 1.5))
    df_kb_top = df_kb_filtered.sort(["kb_usage_rate", "kb_avg_wait_time"], descending=[True, False]).head(10).to_pandas()
    
    # Bike top 10
    df_bk_filtered = df_final.filter((pl.col("bk_deploy") >= 50) & (pl.col("bk_usage") > pl.col("kb_usage") * 1.5))
    df_bk_top = df_bk_filtered.sort(["bk_usage_rate", "bk_avg_wait_time"], descending=[True, False]).head(10).to_pandas()

    all_top_zones = df_kb_top["배치존명"].tolist() + df_bk_top["배치존명"].tolist()

    print("Loading hourly data...")
    lf_hourly = pl.scan_parquet(f"{by_time_path}/**/*.parquet", extra_columns='ignore').filter(
        (pl.col("date") >= min_date) & (pl.col("중지역") == camp_name) & (pl.col("배치존명").is_in(all_top_zones))
    )
    df_hourly = lf_hourly.group_by(["배치존명", "기종", "hour"]).agg(pl.sum("출루수").alias("hourly_usage")).collect()
    
    df_peak = df_hourly.sort(["배치존명", "기종", "hourly_usage"], descending=[False, False, True]).group_by(["배치존명", "기종"]).head(3).to_pandas()
    
    def process_zone(row, device_type):
        zname = row["배치존명"]
        deploy = row["kb_deploy"] if device_type == "킥보드" else row["bk_deploy"]
        usage = row["kb_usage"] if device_type == "킥보드" else row["bk_usage"]
        wait = row["kb_avg_wait_time"] if device_type == "킥보드" else row["bk_avg_wait_time"]
        
        dtype_eng = "scooter" if device_type == "킥보드" else "bicycle"
        peaks = df_peak[(df_peak["배치존명"] == zname) & (df_peak["기종"] == dtype_eng)]["hour"].tolist()
        
        reason, strategy = get_gemini_insights(zname, device_type, deploy, usage, wait if pd.notnull(wait) else 0, peaks)
        return reason, strategy

    print("Generating insights with Gemini API...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        kb_futures = {executor.submit(process_zone, row, "킥보드"): i for i, row in df_kb_top.iterrows()}
        bk_futures = {executor.submit(process_zone, row, "자전거"): i for i, row in df_bk_top.iterrows()}
        
        df_kb_top["추천 사유"] = ""
        df_kb_top["배치 전략"] = ""
        for future in concurrent.futures.as_completed(kb_futures):
            i = kb_futures[future]
            reason, strategy = future.result()
            df_kb_top.at[i, "추천 사유"] = reason
            df_kb_top.at[i, "배치 전략"] = strategy
            
        df_bk_top["추천 사유"] = ""
        df_bk_top["배치 전략"] = ""
        for future in concurrent.futures.as_completed(bk_futures):
            i = bk_futures[future]
            reason, strategy = future.result()
            df_bk_top.at[i, "추천 사유"] = reason
            df_bk_top.at[i, "배치 전략"] = strategy
            
    df_kb_top.insert(1, "추천 기종", "킥보드")
    df_bk_top.insert(1, "추천 기종", "자전거")

    # Save to Excel
    output_dir = os.path.expanduser(f"~/anti_codebase/results/{camp_name}_deploy_zone_analysis")
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, "deploy_zone_analysis_with_insights.xlsx")
    
    with pd.ExcelWriter(out_file) as writer:
        df_kb_top.to_excel(writer, sheet_name="Top_10_Kickboard_Zones", index=False)
        df_bk_top.to_excel(writer, sheet_name="Top_10_Bicycle_Zones", index=False)
        df_final.to_pandas().to_excel(writer, sheet_name="All_Zones_Metrics", index=False)
        df_peak.to_excel(writer, sheet_name="Hourly_Peaks", index=False)
        
    print(f"Analysis complete. Results saved to: {out_file}")

if __name__ == "__main__":
    main()
