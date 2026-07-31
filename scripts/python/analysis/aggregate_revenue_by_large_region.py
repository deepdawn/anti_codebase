import polars as pl
from datetime import datetime, timedelta
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append('/Users/galaxy.jang/anti_codebase')
from scripts.python.utils.read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic

def main():
    if len(sys.argv) < 2:
        print("Usage: python aggregate_revenue_by_large_region.py <subfolder_name>")
        sys.exit(1)
        
    subfolder_name = sys.argv[1]
    
    # 1. 어제 날짜 계산
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"[{yesterday}] 데이터를 집계합니다.")

    # 2. rich_orders 어제자 데이터 로드
    df_orders = load_rich_orders_polars(yesterday, yesterday)
    if df_orders.is_empty():
        print("어제자 주문 데이터가 없습니다.")
        return

    # 채널별 수수료 정책 반영 (calculated_pay_amount, calculated_out_of_area_charge 생성)
    df_orders = apply_channel_fee_logic(df_orders)

    # revenue 컬럼 생성: calculated_pay_amount + calculated_out_of_area_charge
    df_orders = df_orders.with_columns(
        (pl.col("calculated_pay_amount").fill_null(0) + pl.col("calculated_out_of_area_charge").fill_null(0)).alias("revenue")
    )

    # 3. rich_region_hierarchy 로드
    region_path = "/Users/galaxy.jang/Google Drive/공유 드라이브/gbike.rich_region/rich_region_hierarchy.parquet"
    df_region = pl.read_parquet(region_path)

    # 4. 조인 (low_region_id = region_id)
    df_joined = df_orders.join(df_region, left_on="low_region_id", right_on="region_id", how="left")

    # 5. "대지역" 별 매출 집계
    df_agg = (
        df_joined
        .group_by("대지역")
        .agg(
            pl.col("revenue").sum().alias("총매출"),
            pl.col("order_id").count().alias("이용건수")
        )
        .sort("총매출", descending=True)
    )
    
    # 숫자 포맷 적용을 위해 임시 출력
    # (실제 엑셀 저장용은 숫자 타입 유지)
    pl.Config.set_tbl_rows(20)
    print("=== 대지역별 매출 집계 결과 ===")
    print(df_agg)

    # 6. 결과를 저장할 폴더 및 파일 경로 설정
    result_dir = os.path.join("/Users/galaxy.jang/anti_codebase/results", subfolder_name)
    os.makedirs(result_dir, exist_ok=True)
    
    result_file = os.path.join(result_dir, f"revenue_by_large_region_{yesterday}.xlsx")
    
    # 7. 엑셀 파일로 저장
    try:
        df_agg.write_excel(result_file)
        print(f"결과가 성공적으로 저장되었습니다: {result_file}")
    except Exception as e:
        print(f"엑셀 저장 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
