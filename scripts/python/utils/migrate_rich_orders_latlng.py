import os
import glob
import polars as pl
import time

def main():
    base_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_orders"
    parquet_files = glob.glob(f"{base_path}/*/*.parquet")
    
    print(f"총 {len(parquet_files)}개의 Parquet 파일에 대해 위경도 컬럼 스왑 마이그레이션을 시작합니다.")
    start_time = time.time()
    
    success_count = 0
    error_count = 0
    
    for idx, file_path in enumerate(parquet_files):
        try:
            df = pl.read_parquet(file_path)
            cols = df.columns
            
            if all(c in cols for c in ['start_lat', 'start_lng', 'end_lat', 'end_lng']):
                # 서로 이름을 바꾸기 위해 임시 이름(temp)으로 먼저 변경한 후 확정
                df = df.rename({
                    "start_lat": "__start_lng",
                    "start_lng": "__start_lat",
                    "end_lat": "__end_lng",
                    "end_lng": "__end_lat"
                })
                
                df = df.rename({
                    "__start_lng": "start_lng",
                    "__start_lat": "start_lat",
                    "__end_lng": "end_lng",
                    "__end_lat": "end_lat"
                })
                
                # 원본 파일 덮어쓰기
                df.write_parquet(file_path)
                success_count += 1
                
                if (idx + 1) % 100 == 0:
                    print(f"진행 상황: {idx + 1} / {len(parquet_files)} 파일 처리 완료...")
                    
        except Exception as e:
            print(f"[{file_path}] 처리 중 오류 발생: {e}")
            error_count += 1

    elapsed = time.time() - start_time
    print(f"\n마이그레이션 완료!")
    print(f"성공: {success_count}건, 실패: {error_count}건 (소요 시간: {elapsed:.2f}초)")

if __name__ == '__main__':
    main()
