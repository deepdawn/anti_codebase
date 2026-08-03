import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta

# utils 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.read_rich_deploy_used_time import load_rich_deploy_used_time

def main():
    parser = argparse.ArgumentParser(description='Tableau used_time CSV 증분 업데이트 스크립트')
    parser.add_argument('--start_date', type=str, help='시작 일자 (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, help='종료 일자 (YYYY-MM-DD)')
    args = parser.parse_args()
    
    # 기본값: D-5 ~ D-1
    if not args.start_date or not args.end_date:
        today = datetime.now()
        end_date_dt = today - timedelta(days=1)
        start_date_dt = today - timedelta(days=5)
        
        start_date = args.start_date if args.start_date else start_date_dt.strftime('%Y-%m-%d')
        end_date = args.end_date if args.end_date else end_date_dt.strftime('%Y-%m-%d')
    else:
        start_date = args.start_date
        end_date = args.end_date
        
    print(f"작업 기간: {start_date} ~ {end_date}")
    
    target_dir = "/Users/galaxy.jang/Google Drive/공유 드라이브/gbike.rich_deploy_used_time/tableau"
    csv_path = os.path.join(target_dir, "used_time(출루까지시간).csv")
    
    # 1. 신규 데이터 로드
    print(f"신규 데이터 로드 중...")
    new_df = load_rich_deploy_used_time(start_date, end_date)
    
    if new_df.empty:
        print("해당 기간의 신규 데이터가 없어 기존 파일을 유지하고 종료합니다.")
        sys.exit(0)
        
    # 날짜 형식을 문자열로 통일
    if 'date' in new_df.columns:
        new_df['date'] = pd.to_datetime(new_df['date']).dt.strftime('%Y-%m-%d')
    
    # 2. 기존 데이터 로드 및 Upsert
    existing_df = pd.DataFrame()
    if os.path.exists(csv_path):
        print(f"기존 CSV 파일 로드 중: {csv_path}")
        try:
            existing_df = pd.read_csv(csv_path)
            if not existing_df.empty and 'date' in existing_df.columns:
                existing_df['date'] = pd.to_datetime(existing_df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
                existing_df = existing_df.dropna(subset=['date'])                
                initial_len = len(existing_df)
                
                # Upsert: 기존 데이터에서 겹치는 기간 삭제
                existing_df = existing_df[(existing_df['date'] < start_date) | (existing_df['date'] > end_date)]
                deleted_len = initial_len - len(existing_df)
                print(f"겹치는 기간({start_date}~{end_date})의 기존 데이터 {deleted_len}건을 제외(대체)합니다.")
        except Exception as e:
            print(f"기존 CSV 읽기 실패 (새로 생성합니다): {e}")
            existing_df = pd.DataFrame()
    else:
        print(f"기존 CSV 파일이 없어 새로 생성합니다: {csv_path}")
        
    # 3. 데이터 병합
    final_df = pd.concat([existing_df, new_df], ignore_index=True)
    
    # 날짜순 정렬
    if 'date' in final_df.columns:
        final_df.sort_values(by='date', inplace=True)
    
    # 4. 저장
    print(f"CSV 저장 중 (총 {len(final_df)}건)...")
    os.makedirs(target_dir, exist_ok=True)
    final_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print("작업이 완료되었습니다.")

if __name__ == "__main__":
    main()
