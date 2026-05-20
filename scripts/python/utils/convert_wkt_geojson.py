import pandas as pd
import json
import geopandas as gpd
from shapely.wkt import loads
import os

def convert_wkt_to_geojson(input_path, output_path):
    print(f"Loading data from: {input_path}")
    
    # 1. JSON 로드 (orient='records' 또는 lines 형태에 따라 대응 필요할 수 있음)
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 'region_polygon' 키 아래에 리스트가 있는 것으로 추정 (이전 에러 메시지 기반)
    if isinstance(data, dict) and 'region_polygon' in data:
        df_items = data['region_polygon']
    else:
        df_items = data
        
    df = pd.DataFrame(df_items)
    
    print(f"Total rows found: {len(df)}")
    
    # 2. WKT 변환 (region_geometry 컬럼 추출)
    print("Converting WKT to Geometry objects...")
    df['geometry'] = df['region_geometry'].apply(lambda x: loads(x) if pd.notnull(x) else None)
    
    # 3. GeoDataFrame 생성
    gdf = gpd.GeoDataFrame(df, geometry='geometry')
    
    # 좌표계 설정 (일반적으로 WGS84 - EPSG:4324 이나 데이터에 따라 확인 필요)
    # 특별한 명시가 없으므로 기본 EPSG:4326(WGS84) 가정
    gdf.set_crs(epsg=4326, inplace=True)
    
    # 4. GeoJSON 저장
    print(f"Saving to GeoJSON: {output_path}")
    gdf.to_file(output_path, driver='GeoJSON', encoding='utf-8')
    print("Conversion completed successfully.")

if __name__ == "__main__":
    input_file = "/Users/galaxy/Downloads/region_polygon_202604211539.json"
    output_dir = "/Users/galaxy/anti_codebase/base_data/secondary_data/geojson_analysis"
    output_file = os.path.join(output_dir, "region_polygon_converted.geojson")
    
    # 출력 디렉토리 확인
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    convert_wkt_to_geojson(input_file, output_file)
