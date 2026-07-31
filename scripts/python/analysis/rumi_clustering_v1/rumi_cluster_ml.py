import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import DBSCAN

# Haversine DBSCAN eps: 300m in radians (300 / 6_371_000)
EPS_RADIANS = 300 / 6_371_000
MIN_SAMPLES = 10

TIME_BINS = {
    'Morning (06-10)': (6, 10),
    'Daytime (10-17)': (10, 17),
    'Evening (17-22)': (17, 22),
    'Night (22-06)':   (22, 6),
}

def classify_time_period(hour):
    if 6 <= hour < 10:
        return 'Morning (06-10)'
    elif 10 <= hour < 17:
        return 'Daytime (10-17)'
    elif 17 <= hour < 22:
        return 'Evening (17-22)'
    else:
        return 'Night (22-06)'

def classify_day_type(day_name):
    if day_name in ('Saturday', 'Sunday'):
        return 'Weekend'
    return 'Weekday'

def run_dbscan(subset, lon_col, lat_col):
    """Run DBSCAN with Haversine distance on lat/lon coordinates."""
    coords_rad = np.radians(subset[[lat_col, lon_col]].values)  # haversine expects [lat, lon]
    db = DBSCAN(eps=EPS_RADIANS, min_samples=MIN_SAMPLES, metric='haversine')
    labels = db.fit_predict(coords_rad)
    return labels

def cluster_segment(df, prefix, day_type, time_period, results_dir):
    """Cluster a specific segment (day_type x time_period) for start or end points."""
    lon_col = f'{prefix}_lon'
    lat_col = f'{prefix}_lat'
    
    subset = df[(df['day_type'] == day_type) & (df['time_period'] == time_period)].copy()
    subset = subset.dropna(subset=[lon_col, lat_col])
    subset = subset[(subset[lon_col] != 0.0) & (subset[lat_col] != 0.0)]
    
    if len(subset) < MIN_SAMPLES:
        print(f"  [{prefix.upper()}] {day_type}/{time_period}: Skip (only {len(subset)} rows)")
        return None
    
    labels = run_dbscan(subset, lon_col, lat_col)
    cluster_col = f'{prefix}_cluster_id'
    subset[cluster_col] = labels
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = (labels == -1).sum()
    print(f"  [{prefix.upper()}] {day_type}/{time_period}: {len(subset)} pts → {n_clusters} clusters, {n_noise} noise")
    
    return subset, n_clusters

def plot_segment(subset, prefix, day_type, time_period, results_dir):
    """Plot a single segment's clustering result."""
    lon_col = f'{prefix}_lon'
    lat_col = f'{prefix}_lat'
    cluster_col = f'{prefix}_cluster_id'
    
    fig, ax = plt.subplots(figsize=(9, 7))
    
    noise = subset[subset[cluster_col] == -1]
    clustered = subset[subset[cluster_col] != -1]
    
    if len(noise) > 0:
        ax.scatter(noise[lon_col], noise[lat_col], c='lightgray', s=8, alpha=0.3, label='Noise')
    
    if len(clustered) > 0:
        scatter = ax.scatter(
            clustered[lon_col], clustered[lat_col],
            c=clustered[cluster_col], cmap='tab10', s=12, alpha=0.6
        )
        
        # Plot centroids per cluster
        for cid in sorted(clustered[cluster_col].unique()):
            grp = clustered[clustered[cluster_col] == cid]
            cx, cy = grp[lon_col].mean(), grp[lat_col].mean()
            ax.scatter(cx, cy, c='red', s=180, marker='X', edgecolor='black', zorder=5)
    
    direction = 'Departure' if prefix == 'start' else 'Arrival'
    ax.set_title(f'{direction} Clusters — {day_type} / {time_period}\n(DBSCAN, eps=300m, Haversine)')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    
    lon_min, lon_max = subset[lon_col].quantile([0.005, 0.995])
    lat_min, lat_max = subset[lat_col].quantile([0.005, 0.995])
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    
    plt.tight_layout()
    safe_time = time_period.replace(' ', '_').replace('(', '').replace(')', '').replace('-', '')
    fname = f'{prefix}_{day_type.lower()}_{safe_time}.png'
    path = os.path.join(results_dir, fname)
    plt.savefig(path, dpi=150)
    plt.close()
    return path

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(base_dir, '../../../base_data/secondary_data/rumi_analysis_v2/rumi_deep_data.csv')
    
    print(f"Loading data from {input_csv}...")
    df = pd.read_csv(input_csv)
    print(f"Loaded {len(df)} rows.")
    
    # Feature engineering: time dimensions
    df['add_time_kst'] = pd.to_datetime(df['add_time_kst'])
    df['hour'] = df['add_time_kst'].dt.hour
    df['day_of_week'] = df['add_time_kst'].dt.day_name()
    df['time_period'] = df['hour'].apply(classify_time_period)
    df['day_type'] = df['day_of_week'].apply(classify_day_type)
    
    results_dir = os.path.join(base_dir, '../../../results/rumi_clustering_v1/')
    os.makedirs(results_dir, exist_ok=True)
    
    # Run DBSCAN for each segment
    all_results = []
    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("DBSCAN Clustering Report (Haversine, eps=300m, min_samples=10)")
    report_lines.append("=" * 70)
    
    day_types = ['Weekday', 'Weekend']
    time_periods = list(TIME_BINS.keys())
    
    for prefix in ['start', 'end']:
        direction = 'Departure' if prefix == 'start' else 'Arrival'
        report_lines.append(f"\n{'─' * 70}")
        report_lines.append(f"  {direction} Point Clustering")
        report_lines.append(f"{'─' * 70}")
        
        for day_type in day_types:
            for time_period in time_periods:
                result = cluster_segment(df, prefix, day_type, time_period, results_dir)
                if result is None:
                    report_lines.append(f"  {day_type:8s} | {time_period:18s} | SKIPPED (insufficient data)")
                    continue
                    
                subset, n_clusters = result
                cluster_col = f'{prefix}_cluster_id'
                n_noise = (subset[cluster_col] == -1).sum()
                n_valid = len(subset) - n_noise
                
                report_lines.append(f"  {day_type:8s} | {time_period:18s} | {n_clusters} clusters | {n_valid} clustered | {n_noise} noise | {len(subset)} total")
                
                # Centroid details
                clustered = subset[subset[cluster_col] != -1]
                if len(clustered) > 0:
                    for cid in sorted(clustered[cluster_col].unique()):
                        grp = clustered[clustered[cluster_col] == cid]
                        report_lines.append(
                            f"           Cluster {cid}: center=({grp[f'{prefix}_lon'].mean():.5f}, {grp[f'{prefix}_lat'].mean():.5f}), count={len(grp)}"
                        )
                
                # Plot
                img_path = plot_segment(subset, prefix, day_type, time_period, results_dir)
                all_results.append({
                    'prefix': prefix, 'day_type': day_type,
                    'time_period': time_period, 'n_clusters': n_clusters,
                    'img': img_path
                })
    
    # Write report
    report_path = os.path.join(results_dir, 'dbscan_cluster_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    print(f"\nReport saved to: {report_path}")
    
    # Summary comparison chart: cluster count by segment
    if all_results:
        summary_df = pd.DataFrame(all_results)
        
        for prefix in ['start', 'end']:
            sub = summary_df[summary_df['prefix'] == prefix]
            if sub.empty:
                continue
            pivot = sub.pivot(index='day_type', columns='time_period', values='n_clusters').fillna(0).astype(int)
            pivot = pivot.reindex(index=['Weekday', 'Weekend'], columns=list(TIME_BINS.keys()))
            
            plt.figure(figsize=(8, 4))
            sns.heatmap(pivot, annot=True, fmt='d', cmap='YlOrRd')
            direction = 'Departure' if prefix == 'start' else 'Arrival'
            plt.title(f'{direction} — Number of Clusters by Day Type & Time Period')
            plt.ylabel('Day Type')
            plt.xlabel('Time Period')
            plt.tight_layout()
            plt.savefig(os.path.join(results_dir, f'{prefix}_cluster_summary_heatmap.png'), dpi=150)
            plt.close()
    
    print("DBSCAN clustering complete.")

if __name__ == '__main__':
    main()
