import os
import pandas as pd
from datetime import datetime

def load_rich_deploy_zone_usages(start_date_str, end_date_str, columns=None, base_path=f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_deploy_zone_usages"):
    """
    지정된 기간 동안 구글 드라이브에 저장된 rich_deploy_zone_usages Parquet 파일들을 읽어와서 하나의 DataFrame으로 반환합니다.
    
    Args:
        start_date_str (str): 시작 날짜 (YYYY-MM-DD)
        end_date_str (str): 종료 날짜 (YYYY-MM-DD)
        columns (list, optional): 불러올 컬럼 리스트.
        base_path (str): Parquet 파일이 저장된 기본 경로
        
    Returns:
        pd.DataFrame: 병합된 데이터프레임
    """
    date_list = pd.date_range(start=start_date_str, end=end_date_str, freq='D')
    df_list = []
    
    for dt in date_list:
        target_date_str = dt.strftime('%Y-%m-%d')
        daily_folder_name = f"dt={target_date_str}"
        file_path = os.path.join(base_path, daily_folder_name, f"rich_deploy_zone_usages_{target_date_str}.parquet")
        
        if os.path.exists(file_path):
            try:
                df = pd.read_parquet(file_path, columns=columns)
                df_list.append(df)
            except Exception as e:
                print(f"[{target_date_str}] 파일 읽기 중 오류 발생: {e}")
        else:
            print(f"[{target_date_str}] 파일이 존재하지 않습니다: {file_path}")
            
    if not df_list:
        print("해당 기간 내 읽어올 수 있는 데이터가 없습니다.")
        return pd.DataFrame()
        
    final_df = pd.concat(df_list, ignore_index=True)
    return final_df

if __name__ == '__main__':
    # 단위 테스트 및 이상치 확인
    print("=== rich_deploy_zone_usages 로드 및 이상치 검증 테스트 ===")
    start = '2026-07-21'
    end = '2026-07-21'
    
    df = load_rich_deploy_zone_usages(start, end)
    
    if not df.empty:
        print(f"\n데이터 로드 완료. 총 건수: {len(df):,}건")
        
        # 기본 정보 검증
        print("\n[기본 정보]")
        # info()는 출력이 길 수 있으므로 중요한 결측치와 타입만 확인
        print(df.dtypes)
        
        print("\n[결측치 확인]")
        print(df.isnull().sum())
        
        print("\n[요약 통계]")
        print(df[['배치수', '출루수']].describe())
        
        # 이상치 검증 (음수 유무)
        anomaly_deploy = df[df['배치수'] < 0]
        anomaly_release = df[df['출루수'] < 0]
        if not anomaly_deploy.empty or not anomaly_release.empty:
            print(f"\n[!] 주의: 음수 값이 존재합니다. 배치수: {len(anomaly_deploy)}건, 출루수: {len(anomaly_release)}건")
        else:
            print("\n[O] 음수 값 등 주요 이상치는 발견되지 않았습니다.")
            
        # 조인 후 정상적으로 위경도가 있는지
        print("\n[위도/경도 결측치]")
        print(f"위도 결측: {df['위도'].isnull().sum()}, 경도 결측: {df['경도'].isnull().sum()}")
    else:
        print("조회된 데이터가 없습니다.")
