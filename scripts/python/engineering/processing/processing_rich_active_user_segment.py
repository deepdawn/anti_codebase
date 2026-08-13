import os
import sys
import argparse
from datetime import datetime, timedelta
import polars as pl

# utils 패키지 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../../utils'))
from read_rich_orders_polars import load_rich_orders_polars

def extract_active_user_segment(target_date_str):
    print(f"[{target_date_str}] Active User Segment 추출을 시작합니다.")
    
    # 1. 대상 일자의 rich_orders 로드 (당일 운행이 있었던 유저 목록 추출)
    print(f"{target_date_str} 일자의 운행 기록(rich_orders)을 로드합니다...")
    df_orders = load_rich_orders_polars(target_date_str, target_date_str, columns=["user_id"])
    
    if df_orders is None or df_orders.is_empty():
        print(f"[{target_date_str}] 운행 기록이 존재하지 않습니다. 작업을 종료합니다.")
        return
        
    # 당일 운행한 고유 user_id 추출
    df_active_users = df_orders.select("user_id").unique()
    print(f"해당 일자에 운행한 활성 유저 수: {df_active_users.height}명")
    
    # 2. 대상 일자의 rich_user_segment 로드
    print(f"{target_date_str} 일자의 유저 세그먼트(rich_user_segment)를 로드합니다...")
    segment_dir = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_user_segment/dt={target_date_str}"
    segment_file = os.path.join(segment_dir, f"rich_user_segment_{target_date_str}.parquet")
    
    if not os.path.exists(segment_file):
        print(f"[{target_date_str}] 유저 세그먼트 파일이 존재하지 않습니다: {segment_file}")
        return
        
    df_segment = pl.read_parquet(segment_file)
    
    # 3. Inner Join을 통해 당일 운행한 유저의 세그먼트만 필터링
    print("Inner join 수행 중...")
    df_active_segment = df_segment.join(df_active_users, on="user_id", how="inner")
    
    print(f"조인 결과 활성 유저 세그먼트 수: {df_active_segment.height}명")
    
    # 4. 결과 저장
    base_output_dir = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_active_user_segment"
    output_dir = os.path.join(base_output_dir, f"dt={target_date_str}")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f"rich_active_user_segment_{target_date_str}.parquet")
    
    # 용량 최적화를 위해 ZSTD 압축 사용
    df_active_segment.write_parquet(output_path, compression='zstd')
    print(f"결과가 성공적으로 저장되었습니다: {output_path}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Active User Segment 추출 스크립트")
    parser.add_argument("--target-date", type=str, default=None, help="추출 대상 기준일 (YYYY-MM-DD). 미입력 시 어제 날짜 자동 계산")
    
    args = parser.parse_args()
    
    if args.target_date:
        extract_active_user_segment(args.target_date)
    else:
        print("target-date가 지정되지 않았습니다. 누락된 날짜를 탐색하여 자동 보완(Backfill)을 진행합니다.")
        base_output_dir = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_active_user_segment"
        
        # 어제 날짜까지 확인 (마이크로초 차이 방지를 위해 .date() 사용)
        today_date = datetime.now().date()
        end_date = today_date - timedelta(days=1)
        # 백필 기준 시작일 지정 (7일 이전부터 어제자까지 스캔)
        start_date = today_date - timedelta(days=8)
        
        curr_date = start_date
        missing_dates = []
        while curr_date <= end_date:
            dt_str = curr_date.strftime("%Y-%m-%d")
            file_path = os.path.join(base_output_dir, f"dt={dt_str}", f"rich_active_user_segment_{dt_str}.parquet")
            
            if not os.path.exists(file_path):
                missing_dates.append(dt_str)
                
            curr_date += timedelta(days=1)
            
        if not missing_dates:
            print(f"{start_date.strftime('%Y-%m-%d')} 부터 {end_date.strftime('%Y-%m-%d')} 까지 모든 파케이 파일이 정상적으로 존재합니다.")
        else:
            print(f"총 {len(missing_dates)}일치의 누락 데이터를 감지하여 자동 추출을 시작합니다.")
            for dt_str in missing_dates:
                extract_active_user_segment(dt_str)
