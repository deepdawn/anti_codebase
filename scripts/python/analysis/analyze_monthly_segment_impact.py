import os
import polars as pl
import matplotlib.pyplot as plt
import pandas as pd

def main():
    dates = [
        "2025-01-31", "2025-02-28", "2025-03-31", "2025-04-30", "2025-05-31", "2025-06-30",
        "2025-07-31", "2025-08-31", "2025-09-30", "2025-10-31", "2025-11-30", "2025-12-31",
        "2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30", "2026-05-31", "2026-06-24"
    ]
    
    base_dir = f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_user_segment"
    
    plt.rcParams['font.family'] = 'AppleGothic'
    plt.rcParams['axes.unicode_minus'] = False
    
    all_data = []
    
    for dt in dates:
        path = os.path.join(base_dir, f"dt={dt}", f"rich_user_segment_{dt}.parquet")
        if not os.path.exists(path):
            print(f"File not found: {path}")
            continue
            
        df = pl.read_parquet(path)
        
        total_users = df.height
        seg_stats = df.group_by("segment").len(name="count")
        seg_stats = seg_stats.with_columns(
            pl.lit(dt).alias("date"),
            pl.lit(total_users).alias("total_users"),
            ((pl.col("count") / total_users) * 100).alias("ratio")
        )
        
        age_stats = df.group_by(["age_group", "segment"]).len(name="count")
        age_stats = age_stats.with_columns(
            pl.lit(dt).alias("date"),
            pl.lit(total_users).alias("total_users")
        )
        
        all_data.append({"date": dt, "seg": seg_stats, "age": age_stats})
        
    if not all_data:
        print("No data loaded")
        return
        
    df_seg_all = pl.concat([d["seg"] for d in all_data])
    df_age_all = pl.concat([d["age"] for d in all_data])
    
    pd_seg = df_seg_all.to_pandas()
    pd_seg['date'] = pd.to_datetime(pd_seg['date'])
    
    pivot_seg = pd_seg.pivot(index='date', columns='segment', values='ratio').fillna(0)
    
    order = ['active', 'light_active', 'acquisition', 'inactive', 'dormant', 'churn', 'churn_over_365']
    available_cols = [c for c in order if c in pivot_seg.columns]
    pivot_seg = pivot_seg[available_cols]
    
    out_dir = f"{os.path.expanduser('~')}/anti_codebase/results/segment_analysis"
    os.makedirs(out_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(14, 8))
    pivot_seg.plot(kind='line', marker='o', ax=ax, linewidth=2)
    
    ax.axvline(pd.to_datetime("2026-04-30"), color='red', linestyle='--', linewidth=2, label="26.04: 환승혜택 삭제")
    ax.axvline(pd.to_datetime("2025-12-31"), color='purple', linestyle='--', linewidth=2, label="25.12: 16세 미만 제한")
    
    ax.set_title("월별 세그먼트 비중(%) 변화 추이", fontsize=16)
    ax.set_xlabel("Date")
    ax.set_ylabel("Ratio (%)")
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "segment_trend.png"))
    plt.close()
    
    pd_age = df_age_all.to_pandas()
    pd_age['date'] = pd.to_datetime(pd_age['date'])
    
    age_total = pd_age.groupby(['date', 'age_group'])['count'].sum().reset_index()
    pd_age = pd_age.merge(age_total, on=['date', 'age_group'], suffixes=('', '_total'))
    pd_age['ratio_within_age'] = (pd_age['count'] / pd_age['count_total']) * 100
    
    teens = pd_age[(pd_age['age_group'] == '10~16세') & (pd_age['segment'].isin(['churn', 'dormant']))]
    if not teens.empty:
        teens_pivot = teens.pivot(index='date', columns='segment', values='ratio_within_age').fillna(0)
        fig, ax = plt.subplots(figsize=(12, 6))
        teens_pivot.plot(kind='line', marker='o', ax=ax, linewidth=2)
        ax.axvline(pd.to_datetime("2026-04-30"), color='red', linestyle='--', linewidth=2, label="26.04: 환승 혜택 폐지")
        ax.set_title("10~16세 유저 내 이탈(Churn) & 휴면(Dormant) 비중 추이", fontsize=14)
        ax.set_xlabel("Date")
        ax.set_ylabel("Ratio (%)")
        ax.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "teens_churn_trend.png"))
        plt.close()
    
    young_adults = pd_age[(pd_age['age_group'].isin(['10~16세', '17~19세', '20대', '30대'])) & (pd_age['segment'] == 'active')]
    if not young_adults.empty:
        ya_pivot = young_adults.pivot(index='date', columns='age_group', values='ratio_within_age').fillna(0)
        fig, ax = plt.subplots(figsize=(12, 6))
        ya_pivot.plot(kind='line', marker='o', ax=ax, linewidth=2)
        ax.axvline(pd.to_datetime("2025-12-31"), color='red', linestyle='--', linewidth=2, label="25.12: 16세 미만 제한 정책 도입")
        ax.set_title("10대, 20대, 30대 유저 내 Active 비중 추이", fontsize=14)
        ax.set_xlabel("Date")
        ax.set_ylabel("Active Ratio (%)")
        ax.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "core_users_active_trend.png"))
        plt.close()
        
    df_seg_all.write_excel(os.path.join(out_dir, "segment_stats_monthly.xlsx"))
    print(f"분석 완료: 결과 파일들이 {out_dir} 에 저장되었습니다.")

if __name__ == "__main__":
    main()
