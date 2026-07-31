"""
주말 야간(Weekend Night) 도착지 클러스터 기반 수거 동선 최적화
- TSP(Traveling Salesman Problem) 정확해(Exact Solution)
- Haversine 실거리 기반
- 메인 허브(Depot)에서 출발 → 5개 클러스터 순회 → 복귀
"""
import os
import math
import itertools
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.cluster import DBSCAN

# ── 상수 ──
EPS_RADIANS = 300 / 6_371_000
MIN_SAMPLES = 10
DEPOT = {'name': 'Depot (Main Hub)', 'lat': 37.53600, 'lon': 126.96550}
AVG_SPEED_KMH = 20  # 도심 내 수거 차량 평균 속도 (km/h)
COLLECTION_TIME_MIN = 10  # 클러스터당 평균 수거 소요 시간 (분)


def haversine_km(lat1, lon1, lat2, lon2):
    """두 지점 사이의 Haversine 거리 (km)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def classify_time_period(hour):
    if 6 <= hour < 10:
        return 'Morning (06-10)'
    elif 10 <= hour < 17:
        return 'Daytime (10-17)'
    elif 17 <= hour < 22:
        return 'Evening (17-22)'
    else:
        return 'Night (22-06)'


def extract_weekend_night_clusters(df):
    """주말 야간 도착지(end) 데이터에서 DBSCAN 클러스터링 수행."""
    df['add_time_kst'] = pd.to_datetime(df['add_time_kst'])
    df['hour'] = df['add_time_kst'].dt.hour
    df['day_of_week'] = df['add_time_kst'].dt.day_name()
    df['time_period'] = df['hour'].apply(classify_time_period)
    df['day_type'] = df['day_of_week'].apply(lambda d: 'Weekend' if d in ('Saturday', 'Sunday') else 'Weekday')

    subset = df[(df['day_type'] == 'Weekend') & (df['time_period'] == 'Night (22-06)')].copy()
    subset = subset.dropna(subset=['end_lon', 'end_lat'])
    subset = subset[(subset['end_lon'] != 0.0) & (subset['end_lat'] != 0.0)]

    coords_rad = np.radians(subset[['end_lat', 'end_lon']].values)
    db = DBSCAN(eps=EPS_RADIANS, min_samples=MIN_SAMPLES, metric='haversine')
    subset['cluster_id'] = db.fit_predict(coords_rad)

    clustered = subset[subset['cluster_id'] != -1]
    centroids = []
    for cid in sorted(clustered['cluster_id'].unique()):
        grp = clustered[clustered['cluster_id'] == cid]
        mean_lat = grp['end_lat'].mean()
        mean_lon = grp['end_lon'].mean()
        # 위도는 37.xx, 경도는 126.xx 범위여야 정상
        if mean_lat > 100:
            mean_lat, mean_lon = mean_lon, mean_lat
        centroids.append({
            'cluster_id': cid,
            'lat': mean_lat,
            'lon': mean_lon,
            'count': len(grp),
        })
    return centroids, subset


def solve_tsp_exact(depot, centroids):
    """
    Brute-force TSP: depot → all centroids → depot.
    N이 작으므로(≤10) 정확해로 전역 최적을 보장합니다.
    """
    n = len(centroids)
    nodes = [depot] + centroids  # index 0 = depot
    
    # 거리 행렬
    dist = [[0.0] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(n + 1):
            if i != j:
                dist[i][j] = haversine_km(nodes[i]['lat'], nodes[i]['lon'],
                                          nodes[j]['lat'], nodes[j]['lon'])

    best_dist = float('inf')
    best_perm = None

    for perm in itertools.permutations(range(1, n + 1)):
        d = dist[0][perm[0]]
        for k in range(len(perm) - 1):
            d += dist[perm[k]][perm[k + 1]]
        d += dist[perm[-1]][0]
        if d < best_dist:
            best_dist = d
            best_perm = perm

    route_indices = [0] + list(best_perm) + [0]
    route_nodes = [nodes[i] for i in route_indices]
    
    # 구간별 거리
    legs = []
    for i in range(len(route_indices) - 1):
        fi, ti = route_indices[i], route_indices[i + 1]
        legs.append({
            'from': nodes[fi].get('name', f"Cluster {nodes[fi].get('cluster_id', '?')}"),
            'to': nodes[ti].get('name', f"Cluster {nodes[ti].get('cluster_id', '?')}"),
            'distance_km': dist[fi][ti],
        })

    return route_nodes, best_dist, legs


def plot_route(route_nodes, centroids, raw_subset, results_dir):
    """최적 수거 동선 시각화."""
    fig, ax = plt.subplots(figsize=(10, 9))

    # 노이즈 포인트
    noise = raw_subset[raw_subset['cluster_id'] == -1]
    if len(noise) > 0:
        ax.scatter(noise['end_lon'], noise['end_lat'], c='#e0e0e0', s=6, alpha=0.25, label='Noise')

    # 클러스터 포인트
    clustered = raw_subset[raw_subset['cluster_id'] != -1]
    if len(clustered) > 0:
        ax.scatter(clustered['end_lon'], clustered['end_lat'],
                   c=clustered['cluster_id'], cmap='tab10', s=10, alpha=0.5, zorder=2)

    # 경로선
    lons = [n['lon'] for n in route_nodes]
    lats = [n['lat'] for n in route_nodes]
    ax.plot(lons, lats, 'r-', linewidth=2, alpha=0.8, zorder=3)

    # 방문 순서 번호
    for idx, node in enumerate(route_nodes):
        if idx == 0:
            ax.scatter(node['lon'], node['lat'], c='gold', s=300, marker='*',
                       edgecolor='black', zorder=5, label='Depot')
        elif idx < len(route_nodes) - 1:  # 마지막은 depot 복귀이므로 스킵
            ax.scatter(node['lon'], node['lat'], c='red', s=200, marker='X',
                       edgecolor='black', zorder=5)
            ax.annotate(f"{idx}", (node['lon'], node['lat']),
                        textcoords="offset points", xytext=(8, 8),
                        fontsize=14, fontweight='bold', color='red',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

    # 범위
    all_lons = [c['lon'] for c in centroids] + [DEPOT['lon']]
    all_lats = [c['lat'] for c in centroids] + [DEPOT['lat']]
    margin = 0.005
    ax.set_xlim(min(all_lons) - margin, max(all_lons) + margin)
    ax.set_ylim(min(all_lats) - margin, max(all_lats) + margin)

    ax.set_title('Optimal Collection Route — Weekend Night (DBSCAN + TSP)')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')

    gold_star = mpatches.Patch(color='gold', label='Depot (Start/End)')
    red_x = mpatches.Patch(color='red', label='Cluster Centroid (Stop)')
    gray_dot = mpatches.Patch(color='#e0e0e0', label='Noise Points')
    route_line = mpatches.Patch(color='red', label='Optimal Route')
    ax.legend(handles=[gold_star, red_x, gray_dot, route_line],
              loc='upper left', fontsize=9)

    plt.tight_layout()
    path = os.path.join(results_dir, 'optimal_collection_route.png')
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(base_dir, '../../../base_data/secondary_data/rumi_analysis_v2/rumi_deep_data.csv')
    results_dir = os.path.join(base_dir, '../../../results/rumi_clustering_v1/')
    os.makedirs(results_dir, exist_ok=True)

    print("Loading data...")
    df = pd.read_csv(input_csv)
    print(f"Loaded {len(df)} rows.")

    # Step 1: 주말 야간 도착지 클러스터 추출
    print("\n[Step 1] Extracting Weekend Night arrival clusters (DBSCAN)...")
    centroids, raw_subset = extract_weekend_night_clusters(df)
    print(f"  Found {len(centroids)} clusters:")
    for c in centroids:
        print(f"    Cluster {c['cluster_id']}: ({c['lat']:.5f}, {c['lon']:.5f}) — {c['count']} devices")

    # Step 2: TSP 최적 경로 탐색
    print(f"\n[Step 2] Solving TSP (Depot + {len(centroids)} clusters)...")
    route_nodes, total_dist, legs = solve_tsp_exact(DEPOT, centroids)

    travel_time_min = (total_dist / AVG_SPEED_KMH) * 60
    collection_time_min = len(centroids) * COLLECTION_TIME_MIN
    total_time_min = travel_time_min + collection_time_min

    print(f"  Total distance: {total_dist:.2f} km")
    print(f"  Estimated travel time: {travel_time_min:.1f} min")
    print(f"  Estimated collection time: {collection_time_min} min")
    print(f"  Total estimated time: {total_time_min:.1f} min")

    # Step 3: 보고서 작성
    report_path = os.path.join(results_dir, 'collection_route_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("  주말 야간 수거 동선 최적화 보고서\n")
        f.write("  Weekend Night Collection Route Optimization Report\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"Depot (출발/복귀): ({DEPOT['lat']:.5f}, {DEPOT['lon']:.5f})\n")
        f.write(f"Average speed: {AVG_SPEED_KMH} km/h\n")
        f.write(f"Collection time per stop: {COLLECTION_TIME_MIN} min\n\n")

        f.write("── Cluster Summary ──\n")
        for c in centroids:
            f.write(f"  Cluster {c['cluster_id']}: center=({c['lat']:.5f}, {c['lon']:.5f}), devices={c['count']}\n")

        f.write(f"\n── Optimal Route ──\n")
        for i, leg in enumerate(legs):
            f.write(f"  {i + 1}. {leg['from']:30s} → {leg['to']:30s}  ({leg['distance_km']:.3f} km)\n")

        f.write(f"\n── Summary ──\n")
        f.write(f"  Total distance:        {total_dist:.3f} km\n")
        f.write(f"  Travel time:           {travel_time_min:.1f} min\n")
        f.write(f"  Collection time:       {collection_time_min} min ({len(centroids)} stops × {COLLECTION_TIME_MIN} min)\n")
        f.write(f"  Total estimated time:  {total_time_min:.1f} min\n")

    print(f"\nReport saved to: {report_path}")

    # Step 4: 시각화
    print("\n[Step 4] Generating route visualization...")
    img_path = plot_route(route_nodes, centroids, raw_subset, results_dir)
    print(f"Route map saved to: {img_path}")

    print("\nRoute optimization complete.")


if __name__ == '__main__':
    main()
