import os
import polars as pl
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set Matplotlib font to handle Korean for titles/legends, but axes labels must be English
import matplotlib.font_manager as fm
# AppleGothic or similar for mac
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False

def analyze_center_segment():
    dates = [
        "2026-01-31",
        "2026-02-28",
        "2026-03-31",
        "2026-04-30",
        "2026-05-31",
        "2026-06-30"
    ]
    
    base_dir = "/Users/galaxy/Google Drive/공유 드라이브/gbike.rich_user_segment"
    output_dir = "/Users/galaxy/anti_codebase/results/analyze_center_segment_v1"
    os.makedirs(output_dir, exist_ok=True)
    
    all_data = []
    
    for dt in dates:
        file_path = os.path.join(base_dir, f"dt={dt}", f"rich_user_segment_{dt}.parquet")
        if not os.path.exists(file_path):
            print(f"파일 누락 (Skip): {file_path}")
            continue
            
        print(f"데이터 로드 중: {dt}")
        df = pl.read_parquet(file_path)
        
        # Group by 대지역, segment
        region_seg_counts = df.group_by(["대지역", "segment"]).len()
        region_totals = df.group_by("대지역").len().rename({"len": "total"})
        
        # Join and calculate ratio
        stats = region_seg_counts.join(region_totals, on="대지역").with_columns(
            (pl.col("len") / pl.col("total") * 100).alias("ratio")
        )
        
        # Add date column
        stats = stats.with_columns(pl.lit(dt).alias("date"))
        
        all_data.append(stats.to_pandas())
        
    if not all_data:
        print("로딩된 데이터가 없습니다.")
        return
        
    # Combine all dates
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Standardize segments order for visualization
    segment_order = [
        "active", "light_active", "acquisition", 
        "inactive", "dormant", "churn", "churn_over_365"
    ]
    colors = ['#4CAF50', '#8BC34A', '#2196F3', '#FFC107', '#FF9800', '#F44336', '#9E9E9E']
    color_map = dict(zip(segment_order, colors))
    
    unique_regions = combined_df['대지역'].dropna().unique()
    
    # Save to Excel with multiple sheets
    excel_path = os.path.join(output_dir, "center_segment_analysis.xlsx")
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        for region in unique_regions:
            # Filter by region
            region_df = combined_df[combined_df['대지역'] == region].copy()
            
            # Pivot table: rows=date, columns=segment, values=ratio
            pivot_df = region_df.pivot(index='date', columns='segment', values='ratio').fillna(0)
            
            # Reorder columns to match standard order (only existing columns)
            cols_to_use = [col for col in segment_order if col in pivot_df.columns]
            pivot_df = pivot_df[cols_to_use]
            
            # Save to sheet
            safe_sheet_name = str(region).replace('/', '_')[:31]
            pivot_df.to_excel(writer, sheet_name=safe_sheet_name)
            
            # Plot stacked bar chart
            fig, ax = plt.subplots(figsize=(10, 6))
            pivot_df.plot(kind='bar', stacked=True, color=[color_map.get(c, '#000000') for c in pivot_df.columns], ax=ax, edgecolor='white', linewidth=0.5)
            
            # Rule 11: Axis labels must be written in English when creating image files.
            ax.set_xlabel("Date (End of Month)", fontsize=12, fontweight='bold')
            ax.set_ylabel("Segment Ratio (%)", fontsize=12, fontweight='bold')
            
            # Title can be in Korean as it is not axis label
            ax.set_title(f"Segment Distribution Trend (H1 2026) - {region}", fontsize=14, fontweight='bold')
            
            # Format y axis
            ax.set_ylim(0, 100)
            
            # Legend outside
            plt.legend(title='Segment', bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.tight_layout()
            
            # Save image
            img_path = os.path.join(output_dir, f"segment_trend_{safe_sheet_name}.png")
            plt.savefig(img_path, dpi=150, bbox_inches='tight')
            plt.close(fig)

    print(f"\n✅ 분석 완료! 모든 결과물이 '{output_dir}' 에 저장되었습니다.")


if __name__ == "__main__":
    analyze_center_segment()
