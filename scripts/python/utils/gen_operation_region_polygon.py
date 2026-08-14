import os
import json
import urllib.request
import polars as pl

def main():
    # 1. Download all_polygons.geojson
    url = "https://region.gbike.io/kr/all_polygons.geojson"
    print(f"Downloading from {url}...")
    req = urllib.request.urlopen(url)
    geojson_data = json.loads(req.read())
    
    # 2. Load rich_region
    print("Loading gbike.rich_region...")
    region_path = os.path.expanduser("~/Google Drive/공유 드라이브/gbike.rich_region/rich_region_hierarchy.parquet")
    df_region = pl.read_parquet(region_path).select(["region_id", "소지역", "중지역", "대지역"])
    
    # Convert region df to a dictionary for fast lookup
    region_dict = {}
    for row in df_region.iter_rows(named=True):
        if row["region_id"] is not None:
            region_dict[row["region_id"]] = {
                "소지역": row["소지역"],
                "중지역": row["중지역"],
                "대지역": row["대지역"]
            }
        
    # 3. Filter and join
    print("Processing GeoJSON features...")
    new_features = []
    for feature in geojson_data.get("features", []):
        props = feature.get("properties", {})
        
        # Keep only "운영 지역" (ph = 1)
        if props.get("ph") == 1:
            region_id = props.get("region_id")
            if region_id in region_dict:
                # Add region info
                r_info = region_dict[region_id]
                props["소지역"] = r_info["소지역"]
                props["중지역"] = r_info["중지역"]
                props["대지역"] = r_info["대지역"]
            new_features.append(feature)
            
    # Update geojson
    geojson_data["features"] = new_features
    
    # 4. Save to Google Drive
    # Note: Fixed typo 'geojseon' to 'geojson' as intended
    save_dir = os.path.expanduser("~/Google Drive/공유 드라이브/gbike.operation_region_geojson")
    os.makedirs(save_dir, exist_ok=True)
    
    save_path = os.path.join(save_dir, "operation_region_polygons.geojson")
    print(f"Saving to {save_path}...")
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, ensure_ascii=False)
        
    print(f"Done! Saved {len(new_features)} features.")

if __name__ == "__main__":
    main()
