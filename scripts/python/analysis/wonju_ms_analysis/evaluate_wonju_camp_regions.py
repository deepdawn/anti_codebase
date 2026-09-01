import os
import sys
import polars as pl
import pandas as pd
from datetime import datetime, timedelta

# Import load_rich_orders_polars
sys.path.append(os.path.join(os.path.dirname(__file__), '../../utils'))
from read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic

def main():
    start_date = '2025-01-01'
    end_date = '2026-08-30'
    
    # 1. Load Region Hierarchy
    region_path = os.path.expanduser('~/Google Drive/공유 드라이브/gbike.rich_region/rich_region_hierarchy.parquet')
    df_region = pl.read_parquet(region_path)
    df_wonju_regions = df_region.filter(pl.col("중지역") == "원주캠프")
    wonju_region_ids = df_wonju_regions['region_id'].to_list()
    
    # Rename region_id to low_region_id for the join
    df_wonju_regions = df_wonju_regions.rename({"region_id": "low_region_id"})
    
    # 2. Load and Filter Orders
    print("Loading rich_orders...")
    cols = ['dt', 'low_region_id', 'order_amount', 'pay_amount', 'out_of_area_charge', 'from_api']
    
    filter_expr = pl.col('low_region_id').is_in(wonju_region_ids)
    
    df_orders = load_rich_orders_polars(start_date, end_date, columns=cols, filter_expr=filter_expr)
    if df_orders.is_empty():
        print("No orders found for Wonju camp in this period.")
        return
        
    print("Applying channel fee logic...")
    df_orders = apply_channel_fee_logic(df_orders)
    
    # calculate total real revenue
    df_orders = df_orders.with_columns(
        (pl.col('calculated_pay_amount') + pl.col('calculated_out_of_area_charge')).alias('real_revenue')
    )
    
    # Join with region info
    df_merged = df_orders.join(df_wonju_regions, on='low_region_id', how='inner')
    
    # Extract month
    df_merged = df_merged.with_columns(
        pl.col('dt').dt.strftime('%Y-%m').alias('year_month')
    )
    
    # 3. Aggregate Revenue
    df_total_rev = df_merged.group_by('소지역').agg(
        pl.col('real_revenue').sum().alias('total_revenue')
    )
    
    total_camp_revenue = df_total_rev['total_revenue'].sum()
    df_total_rev = df_total_rev.with_columns(
        (pl.col('total_revenue') / total_camp_revenue * 100).alias('revenue_share_pct')
    ).sort('total_revenue', descending=True)
    
    df_monthly_rev = df_merged.group_by(['소지역', 'year_month']).agg(
        pl.col('real_revenue').sum().alias('monthly_revenue')
    ).sort(['소지역', 'year_month'])
    
    df_monthly_pivot = df_monthly_rev.pivot(
        values='monthly_revenue',
        index='소지역',
        on='year_month',
        aggregate_function='sum'
    ).fill_null(0)
    
    # 4. Load MS Data
    ms_files = {
        '여주시': '여주시 MS.xlsx',
        '이천시': '이천시 MS.xlsx',
        '제천시': '제천시 MS.xlsx',
        '충주시': '충주시 MS.xlsx'
    }
    
    ms_summary = []
    base_dir = os.path.expanduser('~/anti_codebase')
    for city, file_name in ms_files.items():
        path = os.path.join(base_dir, file_name)
        if os.path.exists(path):
            try:
                df_ms = pd.read_excel(path)
                company_col = df_ms.columns[0]
                last_week = df_ms.columns[-1]
                
                gcoo_row = df_ms[df_ms[company_col].astype(str).str.strip() == '지쿠']
                gcoo_ms = gcoo_row[last_week].values[0] if not gcoo_row.empty else 0
                
                others = df_ms[df_ms[company_col].astype(str).str.strip() != '지쿠'].copy()
                if not others.empty:
                    top_comp_row = others.sort_values(by=last_week, ascending=False).iloc[0]
                    top_comp_name = top_comp_row[company_col]
                    top_comp_ms = top_comp_row[last_week]
                else:
                    top_comp_name = "None"
                    top_comp_ms = 0
                
                ms_summary.append({
                    '소지역_키워드': city,
                    '최근주차_MS_주차명': last_week,
                    '지쿠_MS_pct': gcoo_ms,
                    '1위경쟁사': top_comp_name,
                    '1위경쟁사_MS_pct': top_comp_ms
                })
            except Exception as e:
                print(f"Error reading {file_name}: {e}")
                
    df_ms_summary = pl.DataFrame(ms_summary) if ms_summary else pl.DataFrame()
    
    # 5. Save Results
    res_dir = os.path.join(base_dir, 'results/wonju_ms_analysis')
    os.makedirs(res_dir, exist_ok=True)
    res_path = os.path.join(res_dir, '원주캠프_권역별_운영지속_판단리포트.xlsx')
    
    with pd.ExcelWriter(res_path) as writer:
        df_total_rev.to_pandas().to_excel(writer, sheet_name='전체_매출비중', index=False)
        df_monthly_pivot.to_pandas().to_excel(writer, sheet_name='월별_매출추이', index=False)
        if not df_ms_summary.is_empty():
            df_ms_summary.to_pandas().to_excel(writer, sheet_name='최근_MS_현황', index=False)
            
    print(f"Analysis complete. Report saved to {res_path}")

if __name__ == '__main__':
    main()
