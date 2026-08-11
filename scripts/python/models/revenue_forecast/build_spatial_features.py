import os
import glob
import argparse
import polars as pl
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
from datetime import datetime
import gc

def build_spatial_and_user_features(start_date, end_date, output_path):
    base_path = os.path.expanduser("~/Google Drive/공유 드라이브")
    
    print("1. Loading Deploy Spots and building cKDTree...")
    spot_files = glob.glob(os.path.join(base_path, "gbike.rich_deploy_spot_info", "**/*.parquet"), recursive=True)
    df_spots = pl.scan_parquet(spot_files[-1]).select(['배치존명', 'lat', 'lng']).drop_nulls().collect()
    
    zones = df_spots['배치존명'].to_list()
    zone_coords = np.column_stack([df_spots['lat'].to_numpy(), df_spots['lng'].to_numpy()])
    tree = cKDTree(zone_coords)
    
    print("2. Loading User Segments...")
    user_files = glob.glob(os.path.join(base_path, "gbike.rich_user_segment", "**/*.parquet"), recursive=True)
    df_users = pl.scan_parquet(user_files[-1]).select(['user_id', 'segment', 'age_group']).collect()
    
    print(f"3. Processing rich_orders from {start_date} to {end_date}...")
    order_path = os.path.join(base_path, "gbike.rich_orders")
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Generate list of partitioned directories if they exist
    # Assume partitioned by dt=YYYY-MM-DD
    all_order_files = []
    for dt in pd.date_range(start_dt, end_dt):
        dt_str = dt.strftime("%Y-%m-%d")
        possible_paths = [
            os.path.join(order_path, f"dt={dt_str}", "*.parquet"),
            os.path.join(order_path, f"date={dt_str}", "*.parquet"),
            os.path.join(order_path, dt_str, "*.parquet")
        ]
        for p in possible_paths:
            matched = glob.glob(p)
            if matched:
                all_order_files.extend(matched)
                break
                
    if not all_order_files:
        print("Partitioned structure not found. Falling back to all files (this might take a lot of memory).")
        all_order_files = glob.glob(os.path.join(order_path, "**/*.parquet"), recursive=True)
        # Assuming we filter by dt later. We will just load all and filter.
        
    print(f"Found {len(all_order_files)} order files.")
    
    # To save memory, process in chunks
    chunk_results = []
    
    for f in all_order_files:
        # We read file by file
        try:
            df_order = pl.read_parquet(f, columns=['dt', 'user_id', 'start_lat', 'start_lng', 'end_lat', 'end_lng'])
        except Exception:
            # Maybe some files lack columns
            continue
            
        # Ensure it's in the date range
        # dt could be datetime, extract date
        if df_order['dt'].dtype != pl.Date:
            df_order = df_order.with_columns(pl.col('dt').dt.date().alias('date_only'))
        else:
            df_order = df_order.with_columns(pl.col('dt').alias('date_only'))
            
        df_order = df_order.filter(
            (pl.col('date_only') >= start_dt.date()) & 
            (pl.col('date_only') <= end_dt.date())
        )
        
        if len(df_order) == 0:
            continue
            
        # Outflow mapping
        valid_start = df_order.drop_nulls(subset=['start_lat', 'start_lng'])
        start_coords = np.column_stack([valid_start['start_lat'].to_numpy(), valid_start['start_lng'].to_numpy()])
        dists_out, idx_out = tree.query(start_coords, distance_upper_bound=0.00045)
        
        # Only keep mapped
        mapped_mask_out = dists_out != np.inf
        valid_start = valid_start.filter(mapped_mask_out)
        mapped_idx_out = idx_out[mapped_mask_out]
        mapped_zones_out = [zones[i] for i in mapped_idx_out]
        
        valid_start = valid_start.with_columns(pl.Series(name="배치존명", values=mapped_zones_out))
        
        # Inflow mapping
        valid_end = df_order.drop_nulls(subset=['end_lat', 'end_lng'])
        end_coords = np.column_stack([valid_end['end_lat'].to_numpy(), valid_end['end_lng'].to_numpy()])
        dists_in, idx_in = tree.query(end_coords, distance_upper_bound=0.00045)
        
        mapped_mask_in = dists_in != np.inf
        valid_end = valid_end.filter(mapped_mask_in)
        mapped_idx_in = idx_in[mapped_mask_in]
        mapped_zones_in = [zones[i] for i in mapped_idx_in]
        
        valid_end = valid_end.with_columns(pl.Series(name="배치존명", values=mapped_zones_in))
        
        # Aggregate Outflow
        outflow_agg = valid_start.group_by(['date_only', '배치존명']).agg(pl.len().alias('Outflow_건수'))
        
        # Aggregate User Segments on Outflow
        valid_start_users = valid_start.join(df_users, on='user_id', how='inner')
        user_agg = valid_start_users.group_by(['date_only', '배치존명']).agg(
            pl.col('segment').eq('active').mean().alias('active_유저_비율'),
            pl.col('age_group').is_in(['20대', '30대']).mean().alias('2030_유저_비율')
        )
        
        # Aggregate Inflow
        inflow_agg = valid_end.group_by(['date_only', '배치존명']).agg(pl.len().alias('Inflow_건수'))
        
        # Join them for this chunk
        chunk_df = outflow_agg.join(inflow_agg, on=['date_only', '배치존명'], how='outer_coalesce')
        chunk_df = chunk_df.join(user_agg, on=['date_only', '배치존명'], how='left')
        
        chunk_results.append(chunk_df)
        
    print("4. Combining all chunks...")
    if chunk_results:
        final_df = pl.concat(chunk_results)
        # Because we might have multiple chunks for the same day (if there are multiple files per day), we groupby again
        final_df = final_df.group_by(['date_only', '배치존명']).agg(
            pl.col('Outflow_건수').sum().fill_null(0),
            pl.col('Inflow_건수').sum().fill_null(0),
            pl.col('active_유저_비율').mean().fill_null(0.0),
            pl.col('2030_유저_비율').mean().fill_null(0.0)
        )
        final_df = final_df.with_columns((pl.col('Inflow_건수') - pl.col('Outflow_건수')).alias('순유출입_건수'))
        final_df = final_df.rename({'date_only': 'date'})
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final_df.write_parquet(output_path, compression='snappy')
        print(f"Spatial features successfully saved to {output_path}")
    else:
        print("No valid data processed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', type=str, default='2026-05-01')
    parser.add_argument('--end-date', type=str, default='2026-08-06')
    parser.add_argument('--output', type=str, default='/Users/galaxy/anti_codebase/base_data/primary_data/revenue_forecast/spatial_features.parquet')
    args = parser.parse_args()
    
    build_spatial_and_user_features(args.start_date, args.end_date, args.output)
