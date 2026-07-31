import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# utils 모듈 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.read_rich_orders_pandas import load_rich_orders, apply_channel_fee_logic
import calendar
from utils.read_rich_user_segment_polars import load_segment_trend_polars, load_segment_trend_for_dates, load_segment_ltv_for_date
from models.revenue_forecast.ensemble_predictor import predict_month_end_revenue, predict_month_end_trips

def send_google_chat_message(creds_path, space_name, text_message, image_path=None):
    """Google Chat API를 사용하여 메시지와 이미지를 전송합니다."""
    SCOPES = ['https://www.googleapis.com/auth/chat.messages.create']
    creds = None
    token_path = os.path.join(os.path.dirname(creds_path), 'token_chat.json')
    
    try:
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
                
        chat = build('chat', 'v1', credentials=creds)
        
        body = {'text': text_message}
        
        if image_path:
            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload(image_path, mimetype='image/png')
            attachment_resp = chat.media().upload(
                parent=space_name,
                body={'filename': os.path.basename(image_path)},
                media_body=media
            ).execute()
            
            if 'attachmentDataRef' in attachment_resp:
                body['attachment'] = [{'attachmentDataRef': attachment_resp['attachmentDataRef']}]
            elif attachment_resp.get('resourceName'):
                body['attachment'] = [{'attachmentDataRef': {'resourceName': attachment_resp.get('resourceName')}}]
        
        result = chat.spaces().messages().create(
            parent=space_name,
            body=body
        ).execute()
        print(f"메시지 전송 성공: {result.get('name')}")
        
    except Exception as e:
        print(f"구글 챗 메시지 전송 중 오류 발생: {e}")

def main():
    end_date_dt = datetime.now() - timedelta(days=1)
    
    current_week_start = end_date_dt - timedelta(days=6)
    
    prev_week_end = current_week_start - timedelta(days=1)
    prev_week_start = prev_week_end - timedelta(days=6)
    
    month_start_dt = datetime(end_date_dt.year, end_date_dt.month, 1)
    
    load_start_dt = min(prev_week_start, month_start_dt)
    
    load_start_str = load_start_dt.strftime('%Y-%m-%d')
    end_date_str = end_date_dt.strftime('%Y-%m-%d')
    
    current_week_start_str = current_week_start.strftime('%Y-%m-%d')
    prev_week_start_str = prev_week_start.strftime('%Y-%m-%d')
    prev_week_end_str = prev_week_end.strftime('%Y-%m-%d')
    month_start_str = month_start_dt.strftime('%Y-%m-%d')
    
    columns = ['dt', 'from_api', 'order_amount', 'pay_amount', 'out_of_area_charge', 'user_id', 'bicycle_sn']
    
    print(f"[{load_start_str} ~ {end_date_str}] 데이터를 로드합니다...")
    df = load_rich_orders(load_start_str, end_date_str, columns=columns)
    
    if not df.empty:
        df['out_of_area_charge'] = df['out_of_area_charge'].fillna(0)
        df['pay_amount'] = df['pay_amount'].fillna(0)
        df['order_amount'] = df['order_amount'].fillna(0)
        
        df = apply_channel_fee_logic(df)
        df['net_revenue'] = (df['calculated_pay_amount'] + df['calculated_out_of_area_charge']) / 1.1
        df['date_str'] = pd.to_datetime(df['dt']).dt.strftime('%Y-%m-%d')
        
        mtd_df = df[df['date_str'] >= month_start_str]
        mtd_revenue = mtd_df['net_revenue'].sum()
        mtd_trips = len(mtd_df)
        mtd_users = mtd_df['user_id'].nunique()
        
        # 1. 매출 예측
        df_train_pred, df_future_pred = None, None
        predicted_total_revenue = 0
        try:
            print("월말 최종 마감 예상 매출 계산 시작...")
            _, _, predicted_total_revenue, conservative_total_predicted, elapsed_pred, df_train_pred, df_future_pred = predict_month_end_revenue(last_actual_date=end_date_dt)
            pred_str_rev = f"{int(predicted_total_revenue):,}원 (모델 소요시간: {elapsed_pred:.1f}초)"
        except Exception as e:
            print(f"예측 매출 계산 실패: {e}")
            pred_str_rev = "계산 실패"
            
        # 2. 운행수 예측
        df_train_pred_trp, df_future_pred_trp = None, None
        predicted_total_trips = 0
        try:
            print("월말 최종 마감 예상 운행수 계산 시작...")
            _, _, predicted_total_trips, _, elapsed_pred_trp, df_train_pred_trp, df_future_pred_trp = predict_month_end_trips(last_actual_date=end_date_dt)
            pred_str_trp = f"{int(predicted_total_trips):,}건 (모델 소요시간: {elapsed_pred_trp:.1f}초)"
        except Exception as e:
            print(f"예측 운행수 계산 실패: {e}")
            pred_str_trp = "계산 실패"
        
        prev_week_df = df[(df['date_str'] >= prev_week_start_str) & (df['date_str'] <= prev_week_end_str)]
        prev_week_revenue = prev_week_df['net_revenue'].sum()
        
        week_df = df[(df['date_str'] >= current_week_start_str) & (df['date_str'] <= end_date_str)].copy()
        week_revenue = week_df['net_revenue'].sum()
        week_trips = len(week_df)
        week_users = week_df['user_id'].nunique()
        
        if prev_week_revenue > 0:
            wow_pct = ((week_revenue / prev_week_revenue) - 1) * 100
            wow_str = f"WoW {wow_pct:+.1f}%"
        else:
            wow_str = "WoW N/A"
        
        df_14d = df[(df['date_str'] >= prev_week_start_str) & (df['date_str'] <= end_date_str)]
        daily_14d = df_14d.groupby('date_str').agg(
            daily_revenue=('net_revenue', 'sum'),
            daily_trips=('net_revenue', 'count'),
            daily_users=('user_id', 'nunique'),
            daily_bikes=('bicycle_sn', 'nunique')
        ).reset_index().sort_values('date_str')
        
        if df_train_pred is not None:
            daily_14d = daily_14d.merge(df_train_pred[['date_str', 'final_pred', 'conservative_pred']], on='date_str', how='left')
            daily_14d.rename(columns={'final_pred': 'final_pred_rev', 'conservative_pred': 'conservative_pred_rev'}, inplace=True)
        else:
            daily_14d['final_pred_rev'] = None
            daily_14d['conservative_pred_rev'] = None
            
        if df_train_pred_trp is not None:
            daily_14d = daily_14d.merge(df_train_pred_trp[['date_str', 'final_pred']], on='date_str', how='left')
            daily_14d.rename(columns={'final_pred': 'final_pred_trp'}, inplace=True)
        else:
            daily_14d['final_pred_trp'] = None
        
        target_revenue = 0
        try:
            target_excel_path = "/Users/galaxy.jang/Library/CloudStorage/OneDrive-지바이크/서비스운영본부 - 현장데이터 개발센터/2026년 목표 매출.xlsx"
            df_target = pd.read_excel(target_excel_path, sheet_name='forecast_model_use')
            current_month = end_date_dt.month
            month_str = f"{current_month}월 (F)"
            target_row = df_target[df_target['month'] == month_str]
            if not target_row.empty:
                target_revenue = target_row.iloc[0]['total']
        except Exception as e:
            print(f"경영 목표 매출 로드 실패: {e}")
            
        # 날씨 데이터
        weather_dict = {}
        lat, lon = 37.5665, 126.9780
        try:
            import requests
            weather_url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={prev_week_start_str}&end_date={end_date_str}&daily=precipitation_sum&timezone=Asia%2FSeoul"
            weather_resp = requests.get(weather_url, timeout=5).json()
            if 'daily' in weather_resp:
                for d, p in zip(weather_resp['daily']['time'], weather_resp['daily']['precipitation_sum']):
                    status = "비" if p and p >= 3 else "-"
                    weather_dict[d] = {'status': status, 'precip': p if p else 0}
        except Exception as e:
            pass
            
        try:
            forecast_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_sum&timezone=Asia%2FSeoul&forecast_days=16"
            forecast_resp = requests.get(forecast_url, timeout=5).json()
            if 'daily' in forecast_resp:
                for d, p in zip(forecast_resp['daily']['time'], forecast_resp['daily']['precipitation_sum']):
                    if d not in weather_dict:
                        status = "비" if p and p >= 3 else "-"
                        weather_dict[d] = {'status': status, 'precip': p if p else 0}
        except Exception as e:
            pass
            
        # ---------------- 매출 메시지 생성 ----------------
        msg_rev = f"📊 *gbike 매출 실적 리포트*\n\n"
        msg_rev += f"▶️ *이번 달 누적 (MTD: {month_start_str} ~ {end_date_str})*\n"
        msg_rev += f"- 총 실매출(only 트립매출): {int(mtd_revenue):,}원\n"
        msg_rev += f"- 이번 달 최종 마감 예측 매출: {pred_str_rev}\n"
        if target_revenue > 0:
            msg_rev += f"- 이번 달 경영 목표 매출: {int(target_revenue):,}원\n"
            if predicted_total_revenue > 0:
                achievement_rate = (predicted_total_revenue / target_revenue) * 100
                msg_rev += f"- (경영목표 대비 {achievement_rate:.1f}% 달성 예상입니다.)\n"
        
        msg_rev += f"\n▶️ *최근 7일 요약 ({current_week_start_str} ~ {end_date_str})*\n"
        msg_rev += f"- 총 실매출(only 트립매출): {int(week_revenue):,}원 ({wow_str})\n"
        
        msg_rev += f"\n▶️ *최근 14일 일별 상세*\n"
        msg_rev += "```\n"
        msg_rev += f"{'일자':<8} | {'날씨':<2} | {'트립수':>7} | {'운행기기':>7} | {'only 트립매출(원)':>14} | {'예상매출(원)':>14}\n"
        msg_rev += "-" * 78 + "\n"
        
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        for _, row in daily_14d.iterrows():
            dt_full = str(row['date_str'])
            dt_obj = datetime.strptime(dt_full, '%Y-%m-%d')
            dt_str = f"{dt_full[-5:]}({weekdays[dt_obj.weekday()]})"
            weather = weather_dict.get(dt_full, {}).get('status', "-")
            rev = f"{int(row['daily_revenue']):,}"
            prd = f"{int(row['final_pred_rev']):,}" if pd.notnull(row['final_pred_rev']) else "-"
            trp = f"{int(row['daily_trips']):,}"
            bik = f"{int(row['daily_bikes']):,}"
            msg_rev += f"{dt_str:<8} | {weather:<4} | {trp:>8} | {bik:>8} | {rev:>15} | {prd:>15}\n"
        msg_rev += "```\n\n"
        
        msg_rev += "▶️ *이번달 일별 상세 (예상)*\n"
        msg_rev += "```\n"
        msg_rev += f"{'일자':<8} | {'날씨':<2} | {'실매출(원)':>15} | {'예상매출(원)':>15} | {'보수적예상(원)':>15}\n"
        msg_rev += "-" * 68 + "\n"
        
        month_actual = df[df['date_str'] >= month_start_str].groupby('date_str').agg(daily_revenue=('net_revenue', 'sum'), daily_trips=('net_revenue', 'count')).reset_index()
        if df_train_pred is not None:
            month_actual = month_actual.merge(df_train_pred[['date_str', 'final_pred', 'conservative_pred']], on='date_str', how='left')
            month_actual.rename(columns={'final_pred': 'final_pred_rev', 'conservative_pred': 'conservative_pred_rev'}, inplace=True)
            
        if df_future_pred is not None and not df_future_pred.empty:
            month_future = df_future_pred[['date_str', 'final_pred', 'conservative_pred']].copy()
            month_future.rename(columns={'final_pred': 'final_pred_rev', 'conservative_pred': 'conservative_pred_rev'}, inplace=True)
            month_future['daily_revenue'] = None
        else:
            month_future = pd.DataFrame(columns=['date_str', 'daily_revenue', 'final_pred_rev', 'conservative_pred_rev'])
            
        month_combined_rev = pd.concat([month_actual, month_future], ignore_index=True).sort_values('date_str')
        
        for _, row in month_combined_rev.iterrows():
            dt_full = str(row['date_str'])
            dt_obj = datetime.strptime(dt_full, '%Y-%m-%d')
            dt_str = f"{dt_full[-5:]}({weekdays[dt_obj.weekday()]})"
            weather = weather_dict.get(dt_full, {}).get('status', "-")
            act_rev = f"{int(row['daily_revenue']):,}" if pd.notnull(row['daily_revenue']) else "-"
            prd_rev = f"{int(row['final_pred_rev']):,}" if pd.notnull(row['final_pred_rev']) else "-"
            cons_rev = f"{int(row['conservative_pred_rev']):,}" if pd.notnull(row.get('conservative_pred_rev')) else "-"
            msg_rev += f"{dt_str:<8} | {weather:<4} | {act_rev:>15} | {prd_rev:>15} | {cons_rev:>15}\n"
        msg_rev += "```\n"
        
        # ---------------- 운행수 메시지 생성 ----------------
        msg_trp = f"📊 *gbike 트립(운행수) 실적 리포트*\n\n"
        msg_trp += f"▶️ *이번 달 누적 (MTD: {month_start_str} ~ {end_date_str})*\n"
        msg_trp += f"- 총 트립 수: {mtd_trips:,}건\n"
        msg_trp += f"- 이용 유저 수: {mtd_users:,}명\n"
        msg_trp += f"- 이번 달 최종 마감 예측 운행수: {pred_str_trp}\n"
        
        msg_trp += f"\n▶️ *최근 7일 요약 ({current_week_start_str} ~ {end_date_str})*\n"
        msg_trp += f"- 총 트립 수: {week_trips:,}건\n"
        msg_trp += f"- 이용 유저 수: {week_users:,}명\n"
        
        msg_trp += f"\n▶️ *최근 14일 일별 상세*\n"
        msg_trp += "```\n"
        msg_trp += f"{'일자':<8} | {'날씨':<2} | {'운행기기':>7} | {'트립수(건)':>12} | {'예상트립(건)':>12}\n"
        msg_trp += "-" * 55 + "\n"
        
        for _, row in daily_14d.iterrows():
            dt_full = str(row['date_str'])
            dt_obj = datetime.strptime(dt_full, '%Y-%m-%d')
            dt_str = f"{dt_full[-5:]}({weekdays[dt_obj.weekday()]})"
            weather = weather_dict.get(dt_full, {}).get('status', "-")
            trp = f"{int(row['daily_trips']):,}"
            bik = f"{int(row['daily_bikes']):,}"
            prd_trp = f"{int(row['final_pred_trp']):,}" if pd.notnull(row['final_pred_trp']) else "-"
            msg_trp += f"{dt_str:<8} | {weather:<4} | {bik:>8} | {trp:>14} | {prd_trp:>14}\n"
        msg_trp += "```\n\n"
        
        msg_trp += "▶️ *이번달 일별 상세 (예상)*\n"
        msg_trp += "```\n"
        msg_trp += f"{'일자':<8} | {'날씨':<2} | {'트립수(건)':>12} | {'예상트립(건)':>12} | {'차이(건)':>10}\n"
        msg_trp += "-" * 58 + "\n"
        
        if df_train_pred_trp is not None:
            month_actual_trp = month_actual.merge(df_train_pred_trp[['date_str', 'final_pred']], on='date_str', how='left')
            month_actual_trp.rename(columns={'final_pred': 'final_pred_trp'}, inplace=True)
        else:
            month_actual_trp = month_actual.copy()
            month_actual_trp['final_pred_trp'] = None
            
        if df_future_pred_trp is not None and not df_future_pred_trp.empty:
            month_future_trp = df_future_pred_trp[['date_str', 'final_pred']].copy()
            month_future_trp.rename(columns={'final_pred': 'final_pred_trp'}, inplace=True)
            month_future_trp['daily_trips'] = None
        else:
            month_future_trp = pd.DataFrame(columns=['date_str', 'daily_trips', 'final_pred_trp'])
            
        month_combined_trp = pd.concat([month_actual_trp, month_future_trp], ignore_index=True).sort_values('date_str')
        
        for _, row in month_combined_trp.iterrows():
            dt_full = str(row['date_str'])
            dt_obj = datetime.strptime(dt_full, '%Y-%m-%d')
            dt_str = f"{dt_full[-5:]}({weekdays[dt_obj.weekday()]})"
            weather = weather_dict.get(dt_full, {}).get('status', "-")
            act_trp = f"{int(row['daily_trips']):,}" if pd.notnull(row['daily_trips']) else "-"
            prd_trp = f"{int(row['final_pred_trp']):,}" if pd.notnull(row['final_pred_trp']) else "-"
            
            diff_str = "-"
            if pd.notnull(row['daily_trips']) and pd.notnull(row['final_pred_trp']):
                diff_val = int(row['daily_trips']) - int(row['final_pred_trp'])
                # 차이값이 양수면 + 표시
                diff_str = f"{diff_val:+,}" if diff_val != 0 else "0"
                
            msg_trp += f"{dt_str:<8} | {weather:<4} | {act_trp:>14} | {prd_trp:>14} | {diff_str:>10}\n"
        msg_trp += "```\n"
        
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
        plt.rc('font', family='AppleGothic')
        plt.rcParams['axes.unicode_minus'] = False
        
        # --- 차트 1: 매출 차트 ---
        plt.figure(figsize=(12, 6))
        dates = []
        for d in daily_14d['date_str']:
            dt_obj = datetime.strptime(str(d), '%Y-%m-%d')
            dt_str = f"{str(d)[-5:]}({weekdays[dt_obj.weekday()]})"
            if weather_dict.get(str(d), {}).get('status') == "비":
                dates.append(f"{dt_str}\n(비)")
            else:
                dates.append(dt_str)
                
        revenues = daily_14d['daily_revenue']
        plt.plot(dates, revenues, marker='o', linestyle='-', color='#1f77b4', linewidth=2, markersize=8, label='실제 매출')
        if 'final_pred_rev' in daily_14d.columns and daily_14d['final_pred_rev'].notnull().any():
            plt.plot(dates, daily_14d['final_pred_rev'], marker='s', linestyle='--', color='#2ca02c', linewidth=2, markersize=8, label='예상 매출')
        plt.legend(loc='upper left')
        
        min_val_r = revenues.min()
        min_idx_r = list(revenues).index(min_val_r)
        min_date_full_r = str(daily_14d.iloc[min_idx_r]['date_str'])
        plt.plot(dates[min_idx_r], min_val_r, marker='o', color='red', markersize=10)
        plt.title('Daily Net Revenue (Last 14 Days)', fontsize=16)
        plt.xlabel('Date (MM-DD)', fontsize=12)
        plt.ylabel('Net Revenue (KRW)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)
        
        for i, rev in enumerate(revenues):
            plt.text(i, rev * 1.02, f"{int(rev):,}", ha='center', va='bottom', fontsize=10)
            if i == min_idx_r and weather_dict.get(min_date_full_r, {}).get('status') == "비":
                precip = weather_dict.get(min_date_full_r, {}).get('precip', 0)
                plt.axvline(x=i, color='red', linestyle=':', alpha=0.7)
                top_y = revenues.min() + (revenues.max() - revenues.min()) * 0.8
                plt.text(i + 0.15, top_y, f"▼ 최저 매출\n(강수량: {precip}mm)", color='red', ha='left', va='center', fontsize=10, fontweight='bold', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
            
        plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        plt.ylim(revenues.min() * 0.85, revenues.max() * 1.15)
        plt.tight_layout()
        chart_path_rev = os.path.join(os.path.dirname(__file__), 'revenue_chart_14d.png')
        plt.savefig(chart_path_rev)
        plt.close()
        
        # --- 차트 2: 운행수 차트 ---
        plt.figure(figsize=(12, 6))
        trips = daily_14d['daily_trips']
        plt.plot(dates, trips, marker='o', linestyle='-', color='#9467bd', linewidth=2, markersize=8, label='실제 트립')
        if 'final_pred_trp' in daily_14d.columns and daily_14d['final_pred_trp'].notnull().any():
            plt.plot(dates, daily_14d['final_pred_trp'], marker='s', linestyle='--', color='#ff7f0e', linewidth=2, markersize=8, label='예상 트립')
        plt.legend(loc='upper left')
        
        min_val_t = trips.min()
        min_idx_t = list(trips).index(min_val_t)
        min_date_full_t = str(daily_14d.iloc[min_idx_t]['date_str'])
        plt.plot(dates[min_idx_t], min_val_t, marker='o', color='red', markersize=10)
        plt.title('Daily Trips (Last 14 Days)', fontsize=16)
        plt.xlabel('Date (MM-DD)', fontsize=12)
        plt.ylabel('Trips (Count)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)
        
        for i, trp in enumerate(trips):
            plt.text(i, trp * 1.02, f"{int(trp):,}", ha='center', va='bottom', fontsize=10)
            if i == min_idx_t and weather_dict.get(min_date_full_t, {}).get('status') == "비":
                precip = weather_dict.get(min_date_full_t, {}).get('precip', 0)
                plt.axvline(x=i, color='red', linestyle=':', alpha=0.7)
                top_y = trips.min() + (trips.max() - trips.min()) * 0.8
                plt.text(i + 0.15, top_y, f"▼ 최저 트립\n(강수량: {precip}mm)", color='red', ha='left', va='center', fontsize=10, fontweight='bold', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
            
        plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        plt.ylim(trips.min() * 0.85, trips.max() * 1.15)
        plt.tight_layout()
        chart_path_trp = os.path.join(os.path.dirname(__file__), 'trips_chart_14d.png')
        plt.savefig(chart_path_trp)
        plt.close()
        
        # --- 차트 3: 유저 세그먼트 비중 월말 추이 차트 ---
        print("유저 세그먼트 데이터 로드 및 차트 생성 중 (월별)...")
        chart_path_seg = os.path.join(os.path.dirname(__file__), 'segment_chart_monthly.png')
        msg_seg = "📊 *gbike 유저 세그먼트 월말 추이 리포트*\n\n"
        
        # 26년 1월부터 현재까지 월말 일자 계산
        eom_dates = []
        curr_year, curr_month = 2026, 1
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        while True:
            if curr_year > now.year or (curr_year == now.year and curr_month > now.month):
                break
            last_day = calendar.monthrange(curr_year, curr_month)[1]
            eom_date = datetime(curr_year, curr_month, last_day)
            
            if eom_date > yesterday:
                eom_dates.append(yesterday.strftime('%Y-%m-%d'))
                break
            else:
                eom_dates.append(eom_date.strftime('%Y-%m-%d'))
            curr_month += 1
            if curr_month > 12:
                curr_month = 1
                curr_year += 1

        df_seg_pl = load_segment_trend_for_dates(eom_dates)
        if not df_seg_pl.is_empty():
            df_seg = df_seg_pl.to_pandas()
            pivot_df = df_seg.pivot(index='dt', columns='segment', values='segment_ratio').fillna(0)
            
            # churn_over_365 세그먼트는 제외
            if 'churn_over_365' in pivot_df.columns:
                pivot_df = pivot_df.drop(columns=['churn_over_365'])
            
            plt.figure(figsize=(12, 6))
            dates_display = []
            for dt_val in pivot_df.index:
                dt_full = str(dt_val)[:10]
                dates_display.append(dt_full)
                
            markers = ['o', 's', '^', 'D', 'v', '<', '>']
            for i, col in enumerate(pivot_df.columns):
                line, = plt.plot(dates_display, pivot_df[col], marker=markers[i % len(markers)], linewidth=2, markersize=6, label=col)
                # 데이터 라벨 추가
                for j, val in enumerate(pivot_df[col]):
                    plt.text(j, val + 0.5, f"{val:.1f}%", color=line.get_color(), ha='center', va='bottom', fontsize=9)
                
            plt.title('End-of-Month User Segment Trend (%)', fontsize=16)
            plt.xlabel('Date (YYYY-MM-DD)', fontsize=12)
            plt.ylabel('Proportion (%)', fontsize=12)
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            plt.gca().yaxis.set_major_formatter(ticker.PercentFormatter())
            # Y축 최대값을 조금 높여 라벨이 잘리지 않게 함
            plt.ylim(0, pivot_df.max().max() * 1.15)
            plt.tight_layout()
            plt.savefig(chart_path_seg)
            plt.close()
            
            msg_seg += f"- 2026년 1월부터 현재까지 월말 기준(당월은 전일자) 세그먼트 비중(%) 변화입니다.\n"
        else:
            msg_seg += "- 세그먼트 데이터를 로드하지 못했습니다.\n"
            
        # 전일자 LTV 집계
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        df_ltv_pl = load_segment_ltv_for_date(yesterday_str)
        if not df_ltv_pl.is_empty():
            msg_seg += f"\n▶️ *세그먼트별 평균 LTV (전일자: {yesterday_str} 기준)*\n"
            msg_seg += "```\n"
            df_ltv = df_ltv_pl.to_pandas()
            # churn_over_365 제외
            df_ltv = df_ltv[df_ltv['segment'] != 'churn_over_365']
            for _, row in df_ltv.iterrows():
                seg_name = row['segment']
                avg_ltv = row['avg_ltv']
                if pd.notnull(avg_ltv):
                    msg_seg += f"{seg_name:<15} : {int(avg_ltv):,}원\n"
            msg_seg += "```\n"
        
        # 발송 (운영 채널)
        creds_file = "/Users/galaxy.jang/anti_codebase/.etc/workspace_desktop_chat_galaxy.json"
        space_id = "spaces/AAQA8O4oUkw" # 전마팀 매출 봇 채널
        
        print("매출 메시지 발송 중...")
        send_google_chat_message(creds_file, space_id, msg_rev, image_path=chart_path_rev)
        
        print("운행수 메시지 발송 중...")
        send_google_chat_message(creds_file, space_id, msg_trp, image_path=chart_path_trp)
        
        print("세그먼트 메시지 발송 중...")
        send_google_chat_message(creds_file, space_id, msg_seg, image_path=chart_path_seg if not df_seg_pl.is_empty() else None)
        
    else:
        print("집계할 데이터가 없습니다.")

if __name__ == '__main__':
    main()
