import os
import sys
import numpy as np
import polars as pl
import pandas as pd
from datetime import datetime

# sys.path 설정하여 utils 모듈을 로드할 수 있게 함
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

from utils.read_rich_orders_polars import load_rich_orders_polars

def haversine(lat1, lon1, lat2, lon2):
    """
    위경도 좌표를 기반으로 두 지점 사이의 거리를 미터(m) 단위로 계산합니다.
    """
    R = 6371000  # 지구 반지름 (미터)
    
    # float 타입 변환
    lat1, lon1, lat2, lon2 = map(np.float64, [lat1, lon1, lat2, lon2])
    
    # 라디안 변환
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    
    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c

def main():
    # 1. 설정
    ACCIDENT_LAT = 37.74256086900756
    ACCIDENT_LNG = 128.89392926505593
    
    # 26년 5월 9일 단일 일자 운행 정보 가져오기
    target_date = "2026-05-09"
    
    base_drive_path = "/Users/galaxy.jang/Google Drive/공유 드라이브"
    bicycle_file = os.path.join(base_drive_path, "gbike.rich_bicycle", "rich_bicycle_asset_info.parquet")
    region_file = os.path.join(base_drive_path, "gbike.rich_region", "rich_region_hierarchy.parquet")
    
    output_dir = "/Users/galaxy.jang/anti_codebase/results/accident_0509"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"사고 조사 스크립트 실행 시작 (v2)...")
    
    # 2. 주문 데이터 로드
    print(f"[1/5] 주문 데이터 ({target_date}) 로드 중...")
    try:
        df_orders = load_rich_orders_polars(target_date, target_date)
        if df_orders.is_empty():
            print("주문 데이터가 비어 있습니다.")
            return

        order_id_col = "order_id" if "order_id" in df_orders.columns else "id"
        
        # 필요한 컬럼 추출 (end_dt 가 있다면 사용, 없다면 생략)
        needed_cols = [order_id_col, "user_id", "end_lat", "end_lng", "bicycle_sn", "st_dt", "end_dt", "low_region_id"]
        df_orders = df_orders.select([c for c in needed_cols if c in df_orders.columns])
        
        # bicycle_sn 기준으로 정렬 후 다음 운행의 시작 시간(next_start_at) 계산
        if "st_dt" in df_orders.columns and "end_dt" in df_orders.columns and "bicycle_sn" in df_orders.columns:
            df_orders = df_orders.sort(["bicycle_sn", "end_dt"])
            df_orders = df_orders.with_columns(
                pl.col("st_dt").shift(-1).over("bicycle_sn").alias("next_start_at")
            )
            # end_at이 14시 50분 전인 내역 필터
            target_dt = datetime.strptime("2026-05-09 14:50:00", "%Y-%m-%d %H:%M:%S")
            df_orders = df_orders.filter(pl.col("end_dt") <= target_dt)
        
    except Exception as e:
        print(f"주문 데이터 로드 중 오류 발생: {e}")
        return
        
    print(f" - 로드된 주문 데이터 건수: {len(df_orders):,}건")

    # 3. 대중소 지역 정보 로드 및 주문 데이터와 조인
    print(f"[2/5] 지역 정보 로드 및 필터링 중...")
    df_region = pl.read_parquet(region_file)
    
    # df_orders에 low_region_id가 있는 경우 region_id로 이름 변경하여 조인 준비
    if "low_region_id" in df_orders.columns:
        df_orders = df_orders.rename({"low_region_id": "region_id"})
    
    # 타입 일치를 위해 캐스팅
    df_orders = df_orders.with_columns(pl.col("region_id").cast(pl.Utf8))
    df_region = df_region.with_columns(pl.col("region_id").cast(pl.Utf8))
    
    df_orders = df_orders.join(df_region, on="region_id", how="left")
    
    # 대지역 및 소지역 필터 조건 적용
    # 1) 대지역이 "중앙RS팀" 인 경우
    # 2) 대지역이 "가맹영업팀" 이고 소지역에 "강원" 또는 "강릉" 이 포함된 경우
    # 대지역 컬럼명은 '대지역', 소지역 컬럼명은 '소지역'으로 가정 (gbike_all.sql 참조)
    
    df_orders = df_orders.filter(
        (pl.col("대지역") == "중앙RS팀") |
        ((pl.col("대지역") == "가맹영업팀") & (pl.col("소지역").str.contains("강원|강릉")))
    )
    print(f" - 지역 필터 적용 후 주문 데이터 건수: {len(df_orders):,}건")
    
    # 4. 기기 정보 로드 및 조인
    print(f"[3/5] 기기 정보 로드 및 필터링 중...")
    df_bike = pl.read_parquet(bicycle_file)
    
    # 킥보드 필터링
    df_bike = df_bike.filter(pl.col("one_category") == "Scooter")
    
    # bicycle_sn으로 inner join
    try:
        df_orders = df_orders.with_columns(pl.col("bicycle_sn").cast(pl.Utf8))
        df_bike = df_bike.with_columns(pl.col("bicycle_sn").cast(pl.Utf8))
    except Exception as e:
        print(f"bicycle_sn 타입 캐스팅 중 오류: {e}")
        
    df_joined = df_orders.join(df_bike, on="bicycle_sn", how="inner")
    print(f" - 기기 정보(킥보드) inner join 후 결과 건수: {len(df_joined):,}건")
    
    # 5. 공간 거리 연산
    print(f"[4/5] 공간 거리 연산 중...")
    pd_joined = df_joined.to_pandas()
    
    if "end_lat" in pd_joined.columns and "end_lng" in pd_joined.columns:
        valid_coords = pd_joined["end_lat"].notnull() & pd_joined["end_lng"].notnull()
        pd_joined["accident_diff_end_point(m)"] = np.nan
        # 데이터셋에서 end_lat과 end_lng이 뒤바뀌어 저장되어 있음 (end_lat이 128.x, end_lng이 37.x)
        pd_joined.loc[valid_coords, "accident_diff_end_point(m)"] = haversine(
            ACCIDENT_LAT, 
            ACCIDENT_LNG, 
            pd_joined.loc[valid_coords, "end_lng"], # 실제 위도는 end_lng 컬럼에 존재
            pd_joined.loc[valid_coords, "end_lat"]  # 실제 경도는 end_lat 컬럼에 존재
        )
    else:
        print("경고: 주문 데이터에 end_lat, end_lng 컬럼이 존재하지 않습니다.")
        
    # 거리 오름차순 (가장 가까운 순) 정렬
    sort_cols = ["accident_diff_end_point(m)"]
    if "end_dt" in pd_joined.columns:
        sort_cols.append("end_dt")
        pd_joined = pd_joined.sort_values(by=sort_cols, ascending=[True, False])
    else:
        pd_joined = pd_joined.sort_values(by=sort_cols, ascending=[True])
    
    # 6. 저장 및 결과 도출
    print(f"[5/5] 결과 저장 및 도출 중...")
    output_file = os.path.join(output_dir, "candidate_kickboards_v2.xlsx")
    pd_joined.to_excel(output_file, index=False)
    
    print(f"\n분석 완료! 결과가 다음 위치에 저장되었습니다:")
    print(f" -> {output_file}")
    
    print("\n[사고 유력 후보 Top 5]")
    top5 = pd_joined.head(5)
    
    display_cols = ["bicycle_sn", "accident_diff_end_point(m)", "대지역", "소지역"]
    if "end_dt" in top5.columns:
        display_cols.append("end_dt")
    if "next_start_at" in top5.columns:
        display_cols.append("next_start_at")
    if "user_id" in top5.columns:
        display_cols.append("user_id")
    if "end_lat" in top5.columns:
        display_cols.extend(["end_lat", "end_lng"])
        
    display_cols = [c for c in display_cols if c in top5.columns]
    
    print(top5[display_cols])

if __name__ == "__main__":
    main()
