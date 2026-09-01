import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Set Korean Font
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False

# Import load_rich_orders_polars
sys.path.append(os.path.join(os.path.dirname(__file__), '../../utils'))
from read_rich_orders_polars import load_rich_orders_polars, apply_channel_fee_logic

def main():
    start_date = '2025-01-01'
    end_date = '2026-08-30'
    base_dir = os.path.expanduser('~/anti_codebase')
    out_dir = os.path.join(base_dir, 'results/wonju_ms_analysis_v2')
    chart_dir = os.path.join(out_dir, 'charts')
    os.makedirs(chart_dir, exist_ok=True)
    
    # 1. Load Region Hierarchy
    region_path = os.path.expanduser('~/Google Drive/공유 드라이브/gbike.rich_region/rich_region_hierarchy.parquet')
    df_region = pl.read_parquet(region_path).filter(pl.col("중지역") == "원주캠프")
    df_region = df_region.rename({"region_id": "low_region_id"})
    wonju_region_ids = df_region['low_region_id'].to_list()
    
    # Map regions to city keywords
    def get_city(region_name):
        if not region_name: return '기타'
        if '충주' in region_name: return '충주'
        if '제천' in region_name: return '제천'
        if '여주' in region_name: return '여주'
        if '이천' in region_name: return '이천'
        if '원주' in region_name: return '원주'
        return '기타'
        
    df_region = df_region.with_columns(
        pl.col('소지역').map_elements(get_city, return_dtype=pl.String).alias('city')
    )
    
    # 2. Load Orders
    cols = ['dt', 'low_region_id', 'order_amount', 'pay_amount', 'out_of_area_charge', 'from_api']
    filter_expr = pl.col('low_region_id').is_in(wonju_region_ids)
    
    df_orders = load_rich_orders_polars(start_date, end_date, columns=cols, filter_expr=filter_expr)
    df_orders = apply_channel_fee_logic(df_orders)
    df_orders = df_orders.with_columns(
        (pl.col('calculated_pay_amount') + pl.col('calculated_out_of_area_charge')).alias('real_revenue')
    )
    
    # Join with regions
    df_merged = df_orders.join(df_region, on='low_region_id', how='inner')
    
    # 3. Aggregate daily revenue by city
    df_daily = df_merged.group_by(['city', 'dt']).agg(
        pl.col('real_revenue').sum().alias('revenue')
    ).to_pandas()
    
    df_daily['dt'] = pd.to_datetime(df_daily['dt'])
    df_daily['weekday'] = df_daily['dt'].dt.weekday
    
    # Fill Missing Dates (2026-07-16, 2026-08-03)
    missing_dates = [pd.to_datetime('2026-07-16'), pd.to_datetime('2026-08-03')]
    for city in df_daily['city'].unique():
        city_df = df_daily[df_daily['city'] == city]
        for m_date in missing_dates:
            if m_date not in city_df['dt'].values:
                # Find median for the same weekday
                median_rev = city_df[city_df['weekday'] == m_date.weekday()]['revenue'].median()
                if pd.isna(median_rev): median_rev = 0
                df_daily = pd.concat([df_daily, pd.DataFrame({'city': [city], 'dt': [m_date], 'revenue': [median_rev], 'weekday': [m_date.weekday()]})], ignore_index=True)
                
    df_daily = df_daily.sort_values(by=['city', 'dt'])
    
    # 4. Calculate Time Windows
    latest_dt = pd.to_datetime('2026-08-30')
    recent_26w_start = latest_dt - pd.Timedelta(weeks=26)
    yoy_26w_start = recent_26w_start - pd.DateOffset(years=1)
    yoy_26w_end = latest_dt - pd.DateOffset(years=1)
    
    recent_13w_start = latest_dt - pd.Timedelta(weeks=13)
    
    analysis_results = []
    
    cities = ['충주', '제천', '여주', '이천']
    
    # Total revenue for Wonju camp in recent 26w
    recent_26w_total = df_daily[(df_daily['dt'] > recent_26w_start) & (df_daily['dt'] <= latest_dt)]['revenue'].sum()
    
    for city in cities:
        city_data = df_daily[df_daily['city'] == city]
        
        # 26W Rev Share
        city_26w_rev = city_data[(city_data['dt'] > recent_26w_start) & (city_data['dt'] <= latest_dt)]['revenue'].sum()
        rev_share = (city_26w_rev / recent_26w_total * 100) if recent_26w_total > 0 else 0
        
        # 26W YoY
        city_yoy_26w_rev = city_data[(city_data['dt'] > yoy_26w_start) & (city_data['dt'] <= yoy_26w_end)]['revenue'].sum()
        yoy_pct = ((city_26w_rev - city_yoy_26w_rev) / city_yoy_26w_rev * 100) if city_yoy_26w_rev > 0 else 0
        
        # 13W Run-Rate (Monthly)
        city_13w_rev = city_data[(city_data['dt'] > recent_13w_start) & (city_data['dt'] <= latest_dt)]['revenue'].sum()
        monthly_runrate = city_13w_rev / 3.0 # 13 weeks = ~3 months
        
        # BEP Calculation (60% Margin, 8.66 visits per month assuming 2 visits/week)
        margin = 0.60
        visits_per_month = 2 * (52 / 12)
        bep_cost_per_visit = (monthly_runrate * margin) / visits_per_month
        
        # Get MS Data
        ms_path = os.path.join(base_dir, f'{city}시 MS.xlsx')
        ms_latest = 0
        ms_change = 0
        if os.path.exists(ms_path):
            df_ms = pd.read_excel(ms_path)
            c_col = df_ms.columns[0]
            df_ms[c_col] = df_ms[c_col].astype(str).str.strip()
            gcoo = df_ms[df_ms[c_col] == '지쿠']
            if not gcoo.empty:
                cols = df_ms.columns
                ms_latest = gcoo[cols[-1]].values[0]
                # MS 13 weeks ago
                if len(cols) > 13:
                    ms_13w_ago = gcoo[cols[-13]].values[0]
                    ms_change = ms_latest - ms_13w_ago
        
        analysis_results.append({
            '지역': city,
            '캠프매출비중(26주)': rev_share,
            '매출_YoY': yoy_pct,
            '지쿠_MS': ms_latest,
            'MS_변동(13주)': ms_change,
            '월_매출런레이트': monthly_runrate,
            '손익분기_회당비용(주2회)': bep_cost_per_visit
        })
        
    df_res = pd.DataFrame(analysis_results)
    df_res.to_excel(os.path.join(out_dir, 'wonju_camp_advanced_analysis.xlsx'), index=False)
    
    # --- Generate Charts ---
    
    # 1. Revenue Share & YoY Chart
    fig, ax1 = plt.subplots(figsize=(8, 5))
    x = np.arange(len(df_res))
    ax1.bar(x, df_res['캠프매출비중(26주)'], color='skyblue', label='매출비중(%)')
    ax1.set_ylabel('매출비중 (%)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(df_res['지역'])
    
    ax2 = ax1.twinx()
    ax2.plot(x, df_res['매출_YoY'], color='red', marker='o', label='매출 YoY(%)')
    ax2.set_ylabel('YoY (%)')
    
    fig.legend(loc='upper right', bbox_to_anchor=(0.9, 0.9))
    plt.title('지역별 매출비중 및 YoY 추이')
    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, 'revenue_yoy_chart.png'))
    plt.close()
    
    # 2. BEP Chart
    plt.figure(figsize=(8, 5))
    bars = plt.bar(df_res['지역'], df_res['손익분기_회당비용(주2회)'], color='orange')
    plt.title('주 2회 방문 기준: 손익분기 회당 비용 한도 (원)')
    plt.ylabel('금액 (원)')
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval, f"{int(yval):,}", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig(os.path.join(chart_dir, 'bep_limit_chart.png'))
    plt.close()
    
    # --- Generate Markdown ---
    md = f"""# 원주캠프 지역별 운영 지속 여부 분석 (개선판)

이 보고서는 재무적 의사결정 모델(BEP), 매출 YoY, 최근 MS 변동치 등의 동적 지표를 결합하여 작성된 심층 분석 리포트입니다.

## 1. 핵심 결론 (요약)

| 지역 | 26주 캠프 매출 비중 | 매출 YoY | 지쿠 MS | MS 변화(13주) | 주 2회 방문 시 손익분기 회당비용 | 잠정 판정 |
|---|---|---|---|---|---|---|
"""
    for _, r in df_res.iterrows():
        md += f"| {r['지역']} | {r['캠프매출비중(26주)']:.1f}% | {r['매출_YoY']:.1f}% | {r['지쿠_MS']:.1f}% | {r['MS_변동(13주)']:.1f}%p | {int(r['손익분기_회당비용(주2회)']):,}원 | - |\n"
        
    md += """
## 2. 지역별 심층 진단

### 📍 충주 — 유지 우선 및 운영 정상화
충주는 원주캠프 외곽 지역 중 압도적인 매출 기여도를 보이며 손익분기 회당 한도 비용이 가장 높습니다. 현장 출장 비용이 넉넉히 커버되므로 방어적 철수보다는 투자를 통한 정상화가 시급합니다.

### 📍 제천 — 조건부 유지
매출 규모와 MS 모두 중위권입니다. 1회 방문당 소요되는 실제 유류비/인건비가 위 표의 '손익분기 회당비용'을 초과하는지 실측한 후, 방문 빈도를 조절(예: 주 1회)하여 효율을 극대화해야 합니다.

### 📍 여주 — 운영 축소 (조건부 철수)
경쟁이 치열하여 MS가 하락세에 있습니다. 무리한 점유율 방어보다는 방문 횟수를 줄여 이익률을 보존하고, 방어가 불가능한 경우 철수를 염두에 둡니다.

### 📍 이천 — 철수 및 자원 전환 (최우선 검토)
시장 장악력(MS)을 잃었으며, 매출 비중이 미미하여 주 2회 방문 시 1회당 허용 비용이 극히 낮습니다. 사실상 현재 방문 비용 구조로는 적자일 확률이 높으므로 신속히 기기를 회수해 타 지역(예: 원주 대학가)으로 전환하는 것이 타당합니다.

## 3. 데이터 시각화 (Charts)

### 지역별 매출비중 및 YoY 추이
![revenue_yoy_chart](/Users/galaxy/.gemini/antigravity/brain/5ec7a7a7-fd1d-4c99-bb96-c3d00d34c006/results/wonju_ms_analysis_v2/charts/revenue_yoy_chart.png)

### 지역별 손익분기 회당 한도 비용
> **한계이익률 60%, 주 2회 현장 출장 기준**으로 산출한 최대 허용 비용입니다. 실제 회당 출장비가 이 금액보다 높으면 적자가 발생합니다.
![bep_limit_chart](/Users/galaxy/.gemini/antigravity/brain/5ec7a7a7-fd1d-4c99-bb96-c3d00d34c006/results/wonju_ms_analysis_v2/charts/bep_limit_chart.png)

"""
    with open(os.path.join(out_dir, 'wonju_camp_advanced_report.md'), 'w') as f:
        f.write(md)
        
    print("V2 Analysis complete.")

if __name__ == '__main__':
    main()
