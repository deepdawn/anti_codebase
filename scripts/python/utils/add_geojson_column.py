import pandas as pd
import shapely.wkt
import json
from shapely.geometry import mapping, LineString
import os

def add_geojson_column(input_path, output_path):
    # 데이터 로드 (utf-8-sig로 한글 및 인코딩 대응)
    df = pd.read_csv(input_path, encoding='utf-8-sig')
    
    def create_geojson(row):
        try:
            # WKT로부터 포인트 객체 생성
            start_p = shapely.wkt.loads(row['start_geo'])
            end_p = shapely.wkt.loads(row['end_geo'])
            
            # 출발지와 도착지를 잇는 LineString 생성
            line = LineString([start_p, end_p])
            
            # GeoJSON 형식(dict)으로 변환 후 문자열화
            return json.dumps(mapping(line))
        except Exception as e:
            return None

    # geojson 컬럼 추가
    df['geojson'] = df.apply(create_geojson, axis=1)
    
    # 결과 저장
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Success: GeoJSON column added and saved to {output_path}")

if __name__ == "__main__":
    input_file = f"{os.path.expanduser('~')}/anti_codebase/base_data/primary_data/result_46.csv"
    
    # 결과를 저장할 디렉토리 설정 (Rule 5에 따라 사용자 확인 후 최종 결정 필요)
    # 임시로 프로젝트 구조 내에 저장 경로 설정
    subfolder_name = "daejeon_bike_geojson"
    output_dir = f"{os.path.expanduser('~')}/anti_codebase/results/{subfolder_name}"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_file = os.path.join(output_dir, "result_46_with_geojson.csv")
    
    add_geojson_column(input_file, output_file)
