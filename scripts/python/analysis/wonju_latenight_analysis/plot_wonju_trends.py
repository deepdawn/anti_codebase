import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager

def main():
    # 한글 폰트 설정 (Mac)
    plt.rc('font', family='AppleGothic')
    plt.rcParams['axes.unicode_minus'] = False
    
    base_dir = "/Users/galaxy.jang/anti_codebase"
    excel_file = os.path.join(base_dir, "results/wonju_latenight_analysis/wonju_latenight_analysis_final_summary.xlsx")
    out_dir = os.path.join(base_dir, "results/wonju_latenight_analysis")
    
    # 1. 2026 주간 트렌드 차트
    weekly_df = pd.read_excel(excel_file, sheet_name="주간_트렌드")
    weekly_2026 = weekly_df[weekly_df['ride_week'].astype(str).str.startswith('2026')].copy()
    weekly_2026['주간_매출_비중(%)'] = 100 - weekly_2026['심야_매출_비중(%)']
    
    plt.figure(figsize=(12, 6))
    plt.plot(weekly_2026['ride_week'], weekly_2026['주간_매출_비중(%)'], marker='o', label='Day Revenue Ratio (%)', color='#ff9999', linewidth=2)
    plt.plot(weekly_2026['ride_week'], weekly_2026['심야_매출_비중(%)'], marker='o', label='Late Night Revenue Ratio (%)', color='#66b3ff', linewidth=2)
    
    plt.title('2026 Weekly Revenue Ratio Trend (Day vs Late Night)', fontsize=16)
    plt.xlabel('Week (YYYY-WW)', fontsize=12)
    plt.ylabel('Ratio (%)', fontsize=12)
    plt.xticks(rotation=45)
    
    # 데이터 라벨 추가
    for i, row in weekly_2026.reset_index(drop=True).iterrows():
        plt.text(i, row['심야_매출_비중(%)'] + 0.5, f"{row['심야_매출_비중(%)']:.1f}%", ha='center', color='#004c99', fontsize=9)
        plt.text(i, row['주간_매출_비중(%)'] + 0.5, f"{row['주간_매출_비중(%)']:.1f}%", ha='center', color='#990000', fontsize=9)
        
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    weekly_chart_path = os.path.join(out_dir, "wonju_2026_weekly_trend.png")
    plt.savefig(weekly_chart_path, dpi=300)
    plt.close()
    print(f"주간 차트 저장: {weekly_chart_path}")
    
    # 2. 2026 월간 차트 (월간 요약 시트 활용)
    monthly_df = pd.read_excel(excel_file, sheet_name="월간_요약")
    monthly_2026 = monthly_df[monthly_df['ride_month'].astype(str).str.startswith('2026')].copy()
    
    # 소지역 단위 데이터를 월 단위로 총합
    monthly_agg = monthly_2026.groupby('ride_month').agg({
        'net_revenue_심야': 'sum',
        '총_매출': 'sum'
    }).reset_index()
    
    monthly_agg['심야_매출_비중(%)'] = (monthly_agg['net_revenue_심야'] / monthly_agg['총_매출']) * 100
    monthly_agg['주간_매출_비중(%)'] = 100 - monthly_agg['심야_매출_비중(%)']
    
    plt.figure(figsize=(10, 6))
    plt.plot(monthly_agg['ride_month'], monthly_agg['주간_매출_비중(%)'], marker='s', label='Day Revenue Ratio (%)', color='#ff9999', linewidth=2, markersize=8)
    plt.plot(monthly_agg['ride_month'], monthly_agg['심야_매출_비중(%)'], marker='s', label='Late Night Revenue Ratio (%)', color='#66b3ff', linewidth=2, markersize=8)
    
    plt.title('2026 Monthly Revenue Ratio Trend (Day vs Late Night)', fontsize=16)
    plt.xlabel('Month (YYYY-MM)', fontsize=12)
    plt.ylabel('Ratio (%)', fontsize=12)
    
    # 데이터 라벨 추가
    for i, row in monthly_agg.iterrows():
        plt.text(i, row['심야_매출_비중(%)'] + 1, f"{row['심야_매출_비중(%)']:.1f}%", ha='center', color='#004c99')
        plt.text(i, row['주간_매출_비중(%)'] + 1, f"{row['주간_매출_비중(%)']:.1f}%", ha='center', color='#990000')

    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    monthly_chart_path = os.path.join(out_dir, "wonju_2026_monthly_trend.png")
    plt.savefig(monthly_chart_path, dpi=300)
    plt.close()
    print(f"월간 차트 저장: {monthly_chart_path}")
    
    # 인사이트(특이사항) 추출용 출력
    print("\n[인사이트 도출을 위한 통계 요약]")
    
    # 월간 탑승률 특이사항
    print("\n--- 2026 월간 심야 탑승률 Top 3 소지역 ---")
    top_util = monthly_2026.sort_values(by='심야_탑승률(%)', ascending=False).head(3)
    print(top_util[['ride_month', '소지역', '심야_탑승률(%)', '심야_매출_비중(%)']])
    
    # YoY 성장에 대한 특이사항
    yoy_df = pd.read_excel(excel_file, sheet_name="YoY_비교")
    
    # 2025 -> 2026 심야 매출이 많이 성장한 곳
    print("\n--- 심야 매출 YoY 성장률 Top 3 소지역 ---")
    valid_yoy = yoy_df[yoy_df['심야_매출_YoY_Growth(%)'] > 0]
    top_growth = valid_yoy.sort_values(by='심야_매출_YoY_Growth(%)', ascending=False).head(3)
    print(top_growth[['소지역', 'month_only', '2025_심야_매출', '2026_심야_매출', '심야_매출_YoY_Growth(%)']])

    print("\n--- 심야 매출 YoY 하락율 Top 3 소지역 (0% 미만) ---")
    drop_yoy = yoy_df[(yoy_df['심야_매출_YoY_Growth(%)'] < 0) & (yoy_df['2025_심야_매출'] > 1000)]
    top_drop = drop_yoy.sort_values(by='심야_매출_YoY_Growth(%)', ascending=True).head(3)
    print(top_drop[['소지역', 'month_only', '2025_심야_매출', '2026_심야_매출', '심야_매출_YoY_Growth(%)']])

    # 주간 트렌드에 대한 특이사항
    print("\n--- 2026 주간 트렌드 특이사항 ---")
    max_late_night_week = weekly_2026.loc[weekly_2026['심야_매출_비중(%)'].idxmax()]
    min_late_night_week = weekly_2026.loc[weekly_2026['심야_매출_비중(%)'].idxmin()]
    print(f"최고 심야 매출 비중 주차: {max_late_night_week['ride_week']} ({max_late_night_week['심야_매출_비중(%)']:.1f}%)")
    print(f"최저 심야 매출 비중 주차: {min_late_night_week['ride_week']} ({min_late_night_week['심야_매출_비중(%)']:.1f}%)")
    print(f"2026 전체 주간 심야 매출 비중 평균: {weekly_2026['심야_매출_비중(%)'].mean():.1f}%")

if __name__ == '__main__':
    main()
