import pandas as pd
import matplotlib.pyplot as plt
import os

def main():
    trip_file_path = "/Users/galaxy.jang/anti_codebase/results/pyeongtaek_latenight_analysis/20260101_20260519_pyeongtaek_late_night.xlsx"
    df = pd.read_excel(trip_file_path)
    
    # 그룹바이 - 월별, 시간대별 매출
    monthly_df = df.groupby(['ride_month', 'hour_type'])['net_revenue'].sum().reset_index()
    
    pivot_df = monthly_df.pivot(index='ride_month', columns='hour_type', values='net_revenue').fillna(0)
    
    # 비중 계산
    pivot_df['total_revenue'] = pivot_df['심야'] + pivot_df['주간']
    pivot_df['Late Night Revenue Ratio (%)'] = (pivot_df['심야'] / pivot_df['total_revenue']) * 100
    pivot_df['Day Revenue Ratio (%)'] = (pivot_df['주간'] / pivot_df['total_revenue']) * 100
    
    # 차트 그리기
    plt.figure(figsize=(10, 6))
    
    months = pivot_df.index
    late_night = pivot_df['Late Night Revenue Ratio (%)']
    day = pivot_df['Day Revenue Ratio (%)']
    
    plt.plot(months, late_night, marker='o', label='Late Night Revenue Ratio (%)', color='blue')
    plt.plot(months, day, marker='s', label='Day Revenue Ratio (%)', color='orange')
    
    # 데이터 라벨 추가 (비율은 소수점 첫째 자리까지 표기)
    for i, month in enumerate(months):
        plt.text(month, late_night.iloc[i] + 2, f"{late_night.iloc[i]:.1f}%", ha='center', color='blue', fontsize=9)
        plt.text(month, day.iloc[i] - 3, f"{day.iloc[i]:.1f}%", ha='center', color='orange', fontsize=9)
    
    plt.title('Monthly Revenue Ratio (Late Night vs Day)')
    plt.xlabel('Month')
    plt.ylabel('Revenue Ratio (%)')
    plt.ylim(0, 105)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # 저장 경로
    out_dir = "/Users/galaxy.jang/anti_codebase/results/pyeongtaek_latenight_analysis"
    out_path = os.path.join(out_dir, "monthly_revenue_ratio.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"Chart saved to {out_path}")

if __name__ == "__main__":
    main()
