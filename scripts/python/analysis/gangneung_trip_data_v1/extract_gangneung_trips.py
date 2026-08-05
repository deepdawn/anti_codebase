import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import calendar

# Add utils path to sys.path
utils_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils'))
sys.path.append(utils_path)

from test_db_conn import get_engine

def get_monthly_ranges(start_date_str, end_date_str):
    """
    YYYY-MM-DD 형식의 시작/종료 날짜 사이를 월 단위 (start_dt, end_dt) 튜플 리스트로 반환합니다.
    """
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    ranges = []
    current_start = start_date
    
    while current_start <= end_date:
        last_day = calendar.monthrange(current_start.year, current_start.month)[1]
        current_end = datetime(current_start.year, current_start.month, last_day, 23, 59, 59)
        
        target_end_of_day = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        if current_end > target_end_of_day:
            current_end = target_end_of_day
            
        ranges.append((current_start.strftime('%Y-%m-%d 00:00:00'), current_end.strftime('%Y-%m-%d 23:59:59')))
        
        # move to next month
        if current_start.month == 12:
            current_start = datetime(current_start.year + 1, 1, 1)
        else:
            current_start = datetime(current_start.year, current_start.month + 1, 1)
            
    return ranges

def main():
    base_output_path = f'{os.path.expanduser("~")}/anti_codebase/base_data/primary_data/gangneung_trip_data_v1'
    os.makedirs(base_output_path, exist_ok=True)
    
    # 1. 추출 기간 설정
    period_2026 = ('2026-01-01', '2026-05-13')
    period_2025 = ('2025-01-01', '2025-05-13')
    
    # 최종 결과 파일명
    result_file = os.path.join(base_output_path, 'gangneung_trip_data_v1_total.xlsx')
    
    engine = get_engine()
    all_dfs = []
    
    periods = [period_2026, period_2025]
    
    for start_p, end_p in periods:
        ranges = get_monthly_ranges(start_p, end_p)
        for start_ts, end_ts in ranges:
            print(f"Extracting: {start_ts} ~ {end_ts}...")
            
            query = f"""
            with region as ( -- 지역 구분
                select	r.region_id,
                        r.region_name as '소지역',
                        rr.region_name as '중지역',
                        rrr.region_name as '대지역'
                from	gbike.rich_region r
                join	gbike.rich_region rr on r.parent_id = rr.region_id
                join	gbike.rich_region rrr on rr.parent_id = rrr.region_id
                where	1=1
            ), bike as ( -- 바이크 구분
                select	rb.bicycle_sn,
                        rb.bicycle_id,
                        rb.region_id, -- 소지역
                        rb.current_speed_mode,
                        rb.pre_order_id,
                        rb.status,
                        CASE
                            when rb.type in (15,17,18,22,24) then 'Bicycle'
                            when rb.type in (9,10,11,12,13,16,19,23) then 'Scooter'
                        else 'none'	END as one_category,
                        CASE
                            when rb.type = 1 then 'none'
                            when rb.type = 2 then 'none'
                            when rb.type = 3 then '에어드레서'
                            when rb.type = 9 then 'SC_ES4'
                            when rb.type = 10 then 'SC_MAX'
                            when rb.type = 11 then 'SC_MAX Pro'
                            when rb.type = 12 then 'SC_GCOO-K1'
                            when rb.type = 13 then 'SC_Max Plus'
                            when rb.type = 14 then '슈드레서'
                            when rb.type = 15 then 'BI_OMNI bicycle'
                            when rb.type = 16 then 'SC_GCOO-K2'
                            when rb.type = 17 then 'BI_GCOO-B3'
                            when rb.type = 18 then 'BI_GCOO-B2'
                            when rb.type = 19 then 'SC_Max Plus X'
                            when rb.type = 22 then 'BI_GCOO-B4'
                            when rb.type = 23 then 'SC_GCOO-K3'
                            when rb.type = 24 then 'BI_A200P'
                        else 'none'	END as two_category
                from gbike.rich_bicycle rb
            ), user as ( -- 유저 구분
                select r.*,
                        case
                            when r.age is null then 'unknown'
                            when r.age < 16  then '16세 미만'
                            when r.age >= 16 and r.age < 20 then '16~19세'
                            when r.age >= 20 and r.age < 30 then '20대'
                            when r.age >= 30 and r.age < 40 then '30대'
                            when r.age >= 40 and r.age < 50 then '40대'
                            when r.age >= 50 and r.age < 60 then '50대'
                        else '기타-60대이상' end as age_group,
                        case when rr.중지역 = '강릉캠프' then '강릉 가입자' else '타지역 가입자' end as regist_gubun,
                        case when r.country_code = 'kr' then '내국인' else '외국인' end as country_gubun
                from (
                        select user_id,nickname,region_id,
                            CASE
                                WHEN r.gender IS NULL THEN 'unknown'
                                WHEN MOD(r.gender, 2) = 1 THEN '남자'
                                ELSE '여자'
                            END AS gender,
                            CASE
                                WHEN r.birthday IS NULL THEN NULL
                                ELSE
                                    FLOOR(
                                        (EXTRACT(YEAR FROM CURRENT_DATE) * 10000 + EXTRACT(MONTH FROM CURRENT_DATE) * 100 + EXTRACT(DAY FROM CURRENT_DATE)
                                        - r.birthday) / 10000
                                    )
                            END AS age,
                            r.country_code
                        from gbike.rich_user r
                ) r
                join region rr on r.region_id = rr.region_id
            )
            select
                    date(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul')) as dt,
                    DATE_FORMAT(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul'),'%%Y-%%m') as month,
                    DATE_FORMAT(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul'),'%%Y') as year,
                    r.`대지역`,
                    r.`중지역`,
                    r.`소지역`,
                    b.one_category,
                    u.gender,u.age_group,
                    u.regist_gubun,u.country_gubun,
                    count(o.order_id) as `트립수`,
                    count(distinct o.bicycle_sn) as `운행기기수_중복제거`,
                    count(distinct o.user_id) as `유저수_중복제거`,
                    sum(TIMESTAMPDIFF(SECOND,
                    CONVERT_TZ(FROM_UNIXTIME(o.start_time), 'UTC', 'Asia/Seoul'),
                    CONVERT_TZ(FROM_UNIXTIME(o.end_time), 'UTC', 'Asia/Seoul')
                    ) / 60) AS `합계운행시간(분)`,
                    sum(o.distance) as `합계운행거리(meter)`,
                    sum(o.order_amount) as `합계주문금액`,
                    sum(o.pay_amount) as `합계결제금액`
            FROM
            gbike.rich_orders o use index (IDX_SALES)
            join region r on o.region_id = r.region_id
            join bike  b on o.bicycle_id = b.bicycle_id
            join user u on u.user_id = o.user_id
            WHERE 1=1
            and o.order_state = 2
            AND o.add_time BETWEEN UNIX_TIMESTAMP(CONVERT_TZ('{start_ts}', 'Asia/Seoul', 'UTC'))
            AND UNIX_TIMESTAMP(CONVERT_TZ('{end_ts}', 'Asia/Seoul', 'UTC'))
            and r.중지역 = '강릉캠프'
            group by
                    date(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul')),
                    DATE_FORMAT(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul'),'%%Y-%%m'),
                    DATE_FORMAT(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul'),'%%Y'),
                    r.`대지역`,
                    r.`중지역`,
                    r.`소지역`,
                    b.one_category,
                    u.gender,u.age_group,
                    u.regist_gubun,u.country_gubun
            """
            
            try:
                with engine.connect() as connection:
                    df_chunk = pd.read_sql(query, connection)
                    if not df_chunk.empty:
                        all_dfs.append(df_chunk)
                    print(f"Chunk complete: {len(df_chunk)} rows")
            except Exception as e:
                print(f"Error during chunk extraction ({start_ts}): {e}")
                continue

    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df.to_excel(result_file, index=False, engine='openpyxl')
        print(f"Final file saved: {result_file} (Total: {len(final_df)} rows)")
    else:
        print("No data extracted.")

if __name__ == '__main__':
    main()
