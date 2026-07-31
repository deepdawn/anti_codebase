import os
import sys
import logging
import traceback
import polars as pl
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# 로그 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.read_rich_orders_polars import load_rich_orders_polars

def add_event_lines(ax):
    events = {
        '2025-12': '16세 미만 탑승 제한',
        '2026-04': '환승 혜택 폐지',
        '2026-06': '멤버십 폐지'
    }
    
    labels = [t.get_text() for t in ax.get_xticklabels()]
    
    for month, desc in events.items():
        if month in labels:
            idx = labels.index(month)
            ax.axvline(x=idx, color='red', linestyle='--', alpha=0.7)
            ax.text(idx, ax.get_ylim()[1] * 0.95, desc, rotation=90, va='top', ha='right', color='red', alpha=0.8, fontsize=10)

def save_line_chart(df, x_col, y_col, hue_col, title, filename):
    plt.figure(figsize=(16, 8))
    sns.set_style("whitegrid")
    
    # 폰트 깨짐 대비를 위해 한글 폰트 설정
    plt.rcParams['font.family'] = 'AppleGothic'
    plt.rcParams['axes.unicode_minus'] = False
    
    ax = sns.lineplot(data=df, x=x_col, y=y_col, hue=hue_col, marker='o', linewidth=2, markersize=8)
    
    # 데이터 라벨 추가
    for line in ax.lines:
        y_data = line.get_ydata()
        x_data = line.get_xdata()
        for x, y in zip(x_data, y_data):
            if not pd.isna(y):
                ax.annotate(f'{y:.1f}%', (x, y), textcoords="offset points", xytext=(0,8), ha='center', fontsize=9)
    
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Month', fontsize=12)
    plt.ylabel('Rate Plan Ratio (%)', fontsize=12)
    plt.xticks(rotation=45)
    
    try:
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    except:
        pass
        
    add_event_lines(ax)
    
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()

def main():
    try:
        logger.info("전국 단위 요금제 비중 추이 분석 시작")
        
        output_dir = "/Users/galaxy.jang/anti_codebase/results/gbike_rate_plan"
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. 지역 정보 로드
        region_path = "/Users/galaxy.jang/Google Drive/공유 드라이브/gbike.rich_region/rich_region_hierarchy.parquet"
        if not os.path.exists(region_path):
            logger.error(f"지역 계층 정보 파일이 존재하지 않습니다: {region_path}")
            return
            
        logger.info(f"지역 계층 데이터 로드: {region_path}")
        df_region = pl.read_parquet(region_path)
        
        # 2. 대상 기간 데이터 로드 (2025-01-01 ~ 2026-07-31)
        selected_cols = ['dt', 'low_region_id', 'riding_fee_type']
        
        logger.info("2025년 1월 ~ 2026년 7월 주문 데이터 로드 중...")
        df_orders = load_rich_orders_polars('2025-01-01', '2026-07-31', columns=selected_cols)
        
        if df_orders.is_empty():
            logger.warning("해당 기간의 주문 데이터가 없습니다.")
            return
            
        logger.info(f"로드된 전체 주문 건수: {df_orders.height:,}건")
        
        # 3. 조인 및 '알수없음' 제외
        logger.info("'알수없음' 요금제 제외 및 지역 정보 병합 중...")
        df_orders = df_orders.filter(pl.col("riding_fee_type") != "알수없음")
        df_joined = df_orders.join(
            df_region.select(["region_id", "대지역", "중지역"]), 
            left_on="low_region_id", 
            right_on="region_id", 
            how="inner"
        )
        
        df_joined = df_joined.with_columns(pl.col('dt').dt.strftime('%Y-%m').alias('year_month'))
        
        logger.info("집계 시작...")
        
        # 4. 집계 함수 정의
        def aggregate_ratio(df_source, group_cols):
            df_agg = df_source.group_by(group_cols + ['riding_fee_type']).agg(
                pl.col('dt').count().alias('order_count')
            )
            df_final = df_agg.with_columns(
                pl.col('order_count').sum().over(group_cols).alias('total_order_count')
            ).with_columns(
                (pl.col('order_count') / pl.col('total_order_count') * 100).alias('ratio_pct')
            ).sort(group_cols + ['riding_fee_type'])
            return df_final.to_pandas()
            
        df_total = aggregate_ratio(df_joined, ['year_month'])
        # 대지역(Center) 집계
        df_center = aggregate_ratio(df_joined, ['year_month', '대지역'])
        target_centers = ['RS그룹', '강남RS팀', '경상RS팀', '남부RS팀', '서울RS팀', '중앙RS팀']
        df_center = df_center[df_center['대지역'].isin(target_centers)]
        df_camp = aggregate_ratio(df_joined, ['year_month', '중지역'])
        
        # 5. 차트 생성
        logger.info("차트 이미지 생성 중...")
        
        # 영문명 변경 로직 제거
        df_total_eng = df_total.copy()
        save_line_chart(
            df_total_eng, 'year_month', 'ratio_pct', 'riding_fee_type', 
            'Total Rate Plan Ratio Trend', 
            os.path.join(output_dir, 'chart_total_trend.png')
        )
        
        # 대지역 차트
        df_center_dist = df_center[df_center['riding_fee_type'] == '거리요금제'].copy()
        save_line_chart(
            df_center_dist, 'year_month', 'ratio_pct', '대지역', 
            'Center Level Distance Rate Plan Ratio Trend', 
            os.path.join(output_dir, 'chart_center_trend.png')
        )
        
        # 6. 이상 트렌드 캠프 추출
        logger.info("이상 트렌드 캠프 탐지 중...")
        months = sorted(df_total['year_month'].unique())
        first_month = months[0]
        last_month = months[-1]
        
        total_per_min = df_total[df_total['riding_fee_type'] == '분당요금제']
        if not total_per_min.empty:
            first_total = total_per_min[total_per_min['year_month'] == first_month]['ratio_pct'].values[0]
            last_total = total_per_min[total_per_min['year_month'] == last_month]['ratio_pct'].values[0]
            total_diff = last_total - first_total
            
            camp_per_min = df_camp[df_camp['riding_fee_type'] == '분당요금제']
            camp_pivot = camp_per_min.pivot(index='중지역', columns='year_month', values='ratio_pct')
            
            outliers = []
            for camp, row in camp_pivot.iterrows():
                if pd.isna(row.get(first_month)) or pd.isna(row.get(last_month)):
                    continue
                camp_diff = row[last_month] - row[first_month]
                # 전체 트렌드와 반대거나 변동폭 차이가 5%p 이상인 캠프 필터
                if (total_diff > 0 and camp_diff < 0) or (total_diff < 0 and camp_diff > 0) or abs(total_diff - camp_diff) > 5:
                    outliers.append({
                        'Camp': camp,
                        f'{first_month} Ratio': round(row[first_month], 2),
                        f'{last_month} Ratio': round(row[last_month], 2),
                        'Difference (%p)': round(camp_diff, 2),
                        'Total Difference (%p)': round(total_diff, 2)
                    })
                    
            df_outliers = pd.DataFrame(outliers)
        else:
            df_outliers = pd.DataFrame()
        
        # 7. 결과 저장
        excel_path = os.path.join(output_dir, 'gbike_rate_plan_summary.xlsx')
        with pd.ExcelWriter(excel_path) as writer:
            df_total.to_excel(writer, sheet_name='Total', index=False)
            df_center.to_excel(writer, sheet_name='Center', index=False)
            df_camp.to_excel(writer, sheet_name='Camp', index=False)
            if not df_outliers.empty:
                df_outliers.to_excel(writer, sheet_name='Outlier_Camps', index=False)
                
        logger.info(f"엑셀 저장 완료: {excel_path}")
        logger.info("모든 분석이 성공적으로 완료되었습니다.")
        
    except Exception as e:
        logger.error(f"분석 중 오류 발생: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    main()
