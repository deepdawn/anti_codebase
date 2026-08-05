import os
import sys
import polars as pl
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import matplotlib.ticker as ticker

# 폰트 설정 (Mac)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# 유틸리티 스크립트 경로 추가
sys.path.append(f'{os.path.expanduser("~")}/anti_codebase/scripts/python/utils')
from read_rich_orders_polars import load_rich_orders_polars

def main():
    base_drive_path = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브"
    orders_path = f"{base_drive_path}/gbike.rich_orders"
    region_path = f"{base_drive_path}/gbike.rich_region/rich_region_hierarchy.parquet"
    user_path = f"{base_drive_path}/gbike.rich_user/rich_user_all.parquet"
    
    results_dir = f"{os.path.expanduser('~')}/anti_codebase/results/goyang2_demo_analysis"
    os.makedirs(results_dir, exist_ok=True)
    
    print("1. 데이터 로드 및 전처리 시작...")
    
    # 1) Region 로드 및 필터링 (고양2캠프)
    region_df = pl.scan_parquet(region_path).filter(pl.col('중지역') == '고양2캠프').select(['region_id', '소지역', '중지역']).collect()
    print(f" - 고양2캠프 지역 정보 로드 완료 (건수: {region_df.height:,})")
    
    # 2) User 로드
    user_cols = ['user_id', 'gender', 'age_group']
    user_lf = pl.scan_parquet(user_path).select(user_cols)
    
    # 3) Orders 로드 (2025-01-01 ~ 2026-05-31)
    orders_cols = ['dt', 'order_id', 'user_id', 'low_region_id', 'vehicle_type', 'bicycle_type']
    print(" - Orders 데이터 로드 중 (2025-01-01 ~ 2026-05-31)...")
    orders_df = load_rich_orders_polars('2025-01-01', '2026-05-31', columns=orders_cols, base_path=orders_path)
    print(f" - Orders 데이터 로드 완료 (건수: {orders_df.height:,})")
    
    if orders_df.height == 0:
        print("조건에 맞는 데이터가 없어 스크립트를 종료합니다.")
        return
        
    print("2. 데이터 조인 및 속성 생성...")
    # Orders x Region (Inner Join - 고양2캠프에서 시작한 운행만)
    joined_df = orders_df.join(region_df, left_on='low_region_id', right_on='region_id', how='inner')
    
    # 결합 x User (Left Join)
    user_df = user_lf.collect()
    joined_df = joined_df.join(user_df, on='user_id', how='left')
    
    # 결측치 처리
    joined_df = joined_df.with_columns([
        pl.col('gender').fill_null('Unknown'),
        pl.col('age_group').fill_null('Unknown')
    ])
    
    # 데모그라피 통합 속성명 생성 및 시간 변수 포맷팅
    joined_df = joined_df.with_columns(
        (pl.col('age_group') + "_" + pl.col('gender')).alias('demo_group'),
        pl.col('dt').dt.strftime('%Y').alias('year'),
        pl.col('dt').dt.strftime('%Y-%m').alias('year_month'),
        pl.col('dt').dt.strftime('%Y-%m-%d').alias('date'),
        pl.col('dt').dt.month().alias('month')
    )
    print(f" - 조인 및 처리 완료 후 분석 데이터 건수: {joined_df.height:,}")
    
    print("3. 주요 지표 및 세부 데이터 집계...")
    
    # 3-1) 전체 요약(Summary) 및 YoY 산출
    monthly_total = joined_df.group_by(['year', 'month', 'year_month']).agg(pl.len().alias('order_count')).sort(['year', 'month'])
    
    yoy_df = monthly_total.pivot(index='month', columns='year', values='order_count').sort('month')
    # YoY 계산
    if '2025' in yoy_df.columns and '2026' in yoy_df.columns:
        yoy_df = yoy_df.with_columns(
            ((pl.col('2026').cast(pl.Float64) - pl.col('2025').cast(pl.Float64)) / pl.col('2025').cast(pl.Float64)).alias('yoy_growth_ratio')
        )
        
    # 3-2) 데모그라피 별 월별 비중 산출
    monthly_demo = joined_df.group_by(['year_month', 'demo_group']).agg(pl.len().alias('demo_order_count')).sort(['year_month', 'demo_group'])
    monthly_total_simple = monthly_total.select(['year_month', 'order_count']).rename({'order_count': 'total_order_count'})
    
    monthly_demo = monthly_demo.join(monthly_total_simple, on='year_month', how='left')
    monthly_demo = monthly_demo.with_columns(
        (pl.col('demo_order_count') / pl.col('total_order_count')).alias('share_ratio')
    )
    
    # 3-3) 데모그라피별 선호 소지역, 선호 기종 (전체)
    demo_pref_region = joined_df.group_by(['demo_group', '소지역']).agg(pl.len().alias('order_count')) \
        .sort(['demo_group', 'order_count'], descending=[False, True])
        
    demo_pref_vehicle = joined_df.group_by(['demo_group', 'vehicle_type', 'bicycle_type']).agg(pl.len().alias('order_count')) \
        .sort(['demo_group', 'order_count'], descending=[False, True])
        
    # 3-4) 피벗용 Raw 집계 (일별, 기종별, 소지역별, 연령대별)
    raw_daily_agg = joined_df.group_by(['date', 'vehicle_type', '소지역', 'age_group']).agg(pl.len().alias('order_count')).sort(['date', '소지역'])
        
    print("4. 분석 결과 엑셀 저장...")
    excel_path = os.path.join(results_dir, "goyang2_demo_analysis_results.xlsx")
    with pd.ExcelWriter(excel_path) as writer:
        # 요약본
        monthly_total.to_pandas().to_excel(writer, sheet_name='Summary_Overall', index=False)
        yoy_df.to_pandas().to_excel(writer, sheet_name='Summary_YoY', index=False)
        monthly_demo.to_pandas().to_excel(writer, sheet_name='Summary_Demo_Share', index=False)
        demo_pref_region.to_pandas().to_excel(writer, sheet_name='Summary_Pref_Region', index=False)
        demo_pref_vehicle.to_pandas().to_excel(writer, sheet_name='Summary_Pref_Vehicle', index=False)
        
        # 피벗용 일별 raw
        raw_daily_agg.to_pandas().to_excel(writer, sheet_name='Raw_Daily_Agg', index=False)
        
        # 데모그라피 속성별 개별 시트 분리 (사용자 선호사항)
        demo_groups = joined_df['demo_group'].unique().to_list()
        for dg in demo_groups:
            # 엑셀 시트명 제약(최대 31자) 준수 및 유효하지 않은 문자 대체
            safe_sheet_name = str(dg).replace('/', '_')[:31] 
            
            dg_df = joined_df.filter(pl.col('demo_group') == dg)
            # 해당 데모의 소지역 및 기종별 전체 집계
            dg_summary = dg_df.group_by(['year_month', '소지역', 'vehicle_type']).agg(pl.len().alias('order_count')).sort(['year_month', 'order_count'], descending=[False, True])
            dg_summary.to_pandas().to_excel(writer, sheet_name=safe_sheet_name, index=False)
            
    print(f" - 엑셀 저장 완료: {excel_path}")
    
    print("5. 시각화 (라인 차트) 산출...")
    # 모든 데모그룹 도출
    top_demos = joined_df.group_by('demo_group').agg(pl.len().alias('cnt')).sort('cnt', descending=True)['demo_group'].to_list()
    
    plt.figure(figsize=(15, 8))
    pdf = monthly_demo.to_pandas()
    colors = sns.color_palette("husl", len(top_demos))
    
    for i, demo in enumerate(top_demos):
        demo_data = pdf[pdf['demo_group'] == demo].sort_values('year_month')
        if demo_data.empty: continue
        
        # 퍼센트 전환
        share_pct_values = demo_data['share_ratio'] * 100
        x_vals = demo_data['year_month']
        
        # 선 그리기
        plt.plot(x_vals, share_pct_values, marker='o', label=demo, color=colors[i], linewidth=2.5)
        
        # 데이터 라벨 표기 (1자리 소수점 + %)
        for x, y in zip(x_vals, share_pct_values):
            plt.annotate(f'{y:.1f}%', (x, y), textcoords="offset points", xytext=(0, 6), ha='center', fontsize=9, color=colors[i])

    plt.title('Monthly Trip Share by Demographic Groups (Goyang 2 Camp)', fontsize=16)
    plt.xlabel('Year-Month (year_month)', fontsize=12)
    plt.ylabel('Share of Total Orders (%)', fontsize=12)
    plt.xticks(rotation=45)
    
    # Y축 퍼센트 표기 포맷 변경
    ax = plt.gca()
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=100, decimals=1))
    
    plt.legend(title='Demographic Group', bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    chart_path = os.path.join(results_dir, "monthly_demo_share_chart.png")
    plt.savefig(chart_path, dpi=150)
    plt.close()
    
    print(f" - 시각화 이미지 저장 완료: {chart_path}")
    print("\n[작업 완료] 모든 프로세스가 정상적으로 마무리되었습니다.")

if __name__ == "__main__":
    main()
