import os
import pandas as pd
from datetime import datetime

def load_rich_orders(start_date_str, end_date_str, columns=None, base_path=f"{os.path.expanduser('~')}/Google Drive/공유 드라이브/gbike.rich_orders"):
    """
    지정된 기간 동안 구글 드라이브에 저장된 rich_orders Parquet 파일들을 읽어와서 하나의 DataFrame으로 반환합니다.
    
    Args:
        start_date_str (str): 시작 날짜 (YYYY-MM-DD)
        end_date_str (str): 종료 날짜 (YYYY-MM-DD)
        columns (list, optional): 불러올 컬럼 리스트. 메모리 최적화를 위해 필요한 컬럼만 지정 권장.
        base_path (str): Parquet 파일이 저장된 기본 경로
        
    Returns:
        pd.DataFrame: 병합된 데이터프레임
    """
    date_list = pd.date_range(start=start_date_str, end=end_date_str, freq='D')
    df_list = []
    
    for dt in date_list:
        target_date_str = dt.strftime('%Y-%m-%d')
        daily_folder_name = f"dt={target_date_str}"
        file_path = os.path.join(base_path, daily_folder_name, f"rich_orders_{target_date_str}.parquet")
        
        if os.path.exists(file_path):
            try:
                # 메모리 절약을 위해 columns 파라미터 활용 가능
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

import numpy as np

def apply_channel_fee_logic(df: pd.DataFrame) -> pd.DataFrame:
    """
    채널별 수수료 정책을 반영하여 실제 수령액 기준의 매출(calculated_pay_amount, calculated_out_of_area_charge) 컬럼을 생성합니다.
    tmap: 9.9%, kakaot: 10%, tmoney: 8.5%, 기타: 수수료 없음
    """
    required_cols = ["from_api", "order_amount", "pay_amount", "out_of_area_charge"]
    if not all(col in df.columns for col in required_cols):
        return df
        
    conditions = [
        df["from_api"] == "tmap",
        df["from_api"] == "kakaot",
        df["from_api"] == "tmoney"
    ]
    
    pay_choices = [
        np.floor(df["order_amount"] * 0.901),
        np.floor(df["order_amount"] * 0.9),
        np.floor(df["order_amount"] * 0.915)
    ]
    
    out_choices = [
        np.floor(df["out_of_area_charge"] * 0.901),
        np.floor(df["out_of_area_charge"] * 0.9),
        np.floor(df["out_of_area_charge"] * 0.915)
    ]
    
    df["calculated_pay_amount"] = np.select(conditions, pay_choices, default=df["pay_amount"])
    df["calculated_out_of_area_charge"] = np.select(conditions, out_choices, default=df["out_of_area_charge"])
    
    return df


if __name__ == '__main__':
    # 예시: 2022년 1월 1일 ~ 2022년 1월 31일의 데이터 로드 후 간단한 집계 테스트
    print("=== rich_orders 로드 및 집계 테스트 ===")
    # 2022년 전체 로드
    start = '2022-01-01'
    end = '2022-12-31'
    
    # 예시: 매출 집계를 위해 컬럼 선택
    selected_cols = ['dt', 'pay_amount', 'duration_minutes']
    
    df = load_rich_orders(start, end, columns=selected_cols)
    
    if not df.empty:
        print(f"\n데이터 로드 완료. 총 건수: {len(df):,}건")
        
        # 년-월 단위 파생 변수 생성
        df['dt'] = pd.to_datetime(df['dt'])
        df['year_month'] = df['dt'].dt.strftime('%Y-%m')
        
        agg_df = df.groupby('year_month').agg(
            total_pay_amount=('pay_amount', 'sum'),
            order_count=('pay_amount', 'count')
        ).reset_index()
        
        # 보기 좋게 포맷팅 (Rule 20)
        agg_df['total_pay_amount_formatted'] = agg_df['total_pay_amount'].apply(lambda x: f"{x:,.0f}")
        agg_df['order_count_formatted'] = agg_df['order_count'].apply(lambda x: f"{x:,.0f}")
        
        print("\n=== 2022년 월별 집계 결과 ===")
        print(agg_df[['year_month', 'order_count_formatted', 'total_pay_amount_formatted']])
    else:
        print("집계할 데이터가 없습니다.")
