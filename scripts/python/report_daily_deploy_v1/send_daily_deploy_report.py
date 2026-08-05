import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import unicodedata

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
utils_path = os.path.join(project_root, 'utils')
sys.path.append(utils_path)

from read_rich_deploy_zone_usages import load_rich_deploy_zone_usages
from send_google_chat_msg import send_google_chat_message

# 한글 폰트 설정 (Mac)
plt.rc('font', family='AppleGothic')
plt.rcParams['axes.unicode_minus'] = False

def pad_str(s, width, align='left'):
    """콘솔/마크다운 고정폭 글꼴에서 한글 폭을 2로 계산하여 패딩을 적용합니다."""
    s = str(s)
    disp_len = sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in s)
    pad = width - disp_len
    if pad <= 0:
        return s
    if align == 'left':
        return s + ' ' * pad
    elif align == 'right':
        return ' ' * pad + s
    else:
        return s + ' ' * pad

def main():
    end_date_dt = datetime.now() - timedelta(days=1)
    start_date_dt = end_date_dt - timedelta(days=13)
    
    end_date_str = end_date_dt.strftime('%Y-%m-%d')
    start_date_str = start_date_dt.strftime('%Y-%m-%d')
    
    print(f"Loading data from {start_date_str} to {end_date_str}...")
    df = load_rich_deploy_zone_usages(start_date_str, end_date_str)
    
    if df.empty:
        print("조회된 데이터가 없습니다.")
        return
        
    # 서울RS팀의 "폐기킥보드_서울운영팀" 데이터는 집계에서 제외합니다.
    df = df[~((df['대지역'] == '서울RS팀') & (df['중지역'] == '폐기킥보드_서울운영팀'))]

    # 대지역 매핑 (명칭 일치: '팀' 추가)
    channel_mapping = {
        '서울RS팀': 'AAQAdNEjFKk', 
        '강남RS팀': 'AAQA-vKFdg8', 
        '중앙RS팀': 'AAQAhht23yY', 
        '경상RS팀': 'AAQAB0_sqIQ', 
        '남부RS팀': 'AAQAbxfwAtM'
    }
    
    # 1. Grouping
    grouped = df.groupby(['date', '대지역', '중지역'])[['배치수', '출루수']].sum().reset_index()
    
    # 2. Calculate Release Rate (출루율)
    grouped['출루율'] = (grouped['출루수'] / grouped['배치수'] * 100).fillna(0)
    import numpy as np
    grouped['출루율'] = grouped['출루율'].replace([np.inf, -np.inf], 0)
    
    # 날짜 포맷 (MM/DD)
    grouped['date_str'] = pd.to_datetime(grouped['date']).dt.strftime('%m/%d')
    
    creds_file = f"{os.path.expanduser('~')}/anti_codebase/.etc/workspace_desktop_chat_galaxy.json"
    save_dir = f"{os.path.expanduser('~')}/anti_codebase/scripts/python/report_daily_deploy_v1"
    
    # 3. 각 대지역별로 처리
    for lg_region, space_id in channel_mapping.items():
        region_df = grouped[grouped['대지역'] == lg_region]
        if region_df.empty:
            print(f"[{lg_region}] 데이터가 없습니다. 스킵합니다.")
            continue
            
        print(f"[{lg_region}] 리포트 생성 중...")
        
        # 피벗 테이블 생성
        pivot_df = region_df.pivot_table(index='중지역', columns='date_str', values='출루율', fill_value=0)
        
        # Markdown 테이블 포맷팅
        markdown_table = f"▶️ *{lg_region} 일자별 출루율 (최근 14일)*\n```\n"
        
        cols = list(pivot_df.columns)[::-1]
        first_col_width = 16
        col_width = 7
        
        header_str = pad_str("중지역", first_col_width) + " | " + " | ".join([pad_str(c, col_width, 'right') for c in cols]) + "\n"
        markdown_table += header_str
        markdown_table += "-" * first_col_width + "-|-" + "-|-".join(["-" * col_width for _ in cols]) + "\n"
        
        for index, row in pivot_df.iterrows():
            row_str = pad_str(index, first_col_width) + " | "
            val_strs = []
            for col in cols:
                val = row[col]
                # 소수점 1자리 퍼센트
                val_formatted = f"{val:.1f}%"
                val_strs.append(pad_str(val_formatted, col_width, 'right'))
            row_str += " | ".join(val_strs)
            markdown_table += row_str + "\n"
        
        markdown_table += "```\n"
        
        # 라인 차트 생성
        plt.figure(figsize=(14, 7))
        sns.lineplot(data=region_df, x='date_str', y='출루율', hue='중지역', marker='o')
        
        # 축 레이블 영어 적용
        plt.title(f'Daily Release Rate - {lg_region}', fontsize=16)
        plt.xlabel('Date (MM/DD)', fontsize=12)
        plt.ylabel('Release Rate (%)', fontsize=12)
        plt.xticks(rotation=45)
        plt.legend(title='Medium Region', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        chart_filename = f"chart_release_rate_{lg_region}.png"
        chart_path = os.path.join(save_dir, chart_filename)
        plt.savefig(chart_path, dpi=150)
        plt.close()
        
        # 구글 챗 발송
        print(f"[{lg_region}] 구글 챗 발송 중...")
        send_google_chat_message(creds_file, space_id, markdown_table, image_path=chart_path)
        
    print("모든 대지역 리포트 발송이 완료되었습니다.")

if __name__ == '__main__':
    main()
