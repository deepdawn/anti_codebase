import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add path for utility scripts
sys.path.append('/Users/galaxy/codebase/scripts/python/utils')
from test_db_conn import get_engine

def get_query(start_date, end_date):
    """
    Generate SQL query for a specific date range.
    """
    query = f"""
    with region as (
        select	r.region_id,
                r.region_name as 'sub_region',
                rr.region_name as 'mid_region',
                rrr.region_name as 'large_region'
        from	gbike.rich_region r
        join	gbike.rich_region rr on r.parent_id = rr.region_id
        join	gbike.rich_region rrr on rr.parent_id = rrr.region_id
        where	rr.region_name = '강릉캠프'
    ), bike as (
        select	rb.bicycle_sn,
                rb.bicycle_id,
                rb.region_id,
                CASE
                    when rb.type in (15,17,18,22,24) then 'Bicycle'
                    when rb.type in (9,10,11,12,13,16,19,23) then 'Scooter'
                else 'none'	END as one_category
        from gbike.rich_bicycle rb
    ), user as (
        select r.*,
                case
                    when r.age is null then 'unknown'
                    when r.age < 16 then '16세 미만'
                    when r.age >= 16 and r.age < 20 then '16세~20세 미만'
                    when r.age >= 20 and r.age < 30 then '20대'
                    when r.age >= 30 and r.age < 40 then '30대'
                    when r.age >= 40 and r.age < 50 then '40대'
                    when r.age >= 50 and r.age < 60 then '50대'
                else '기타' end as age_group
        from (
                select user_id,
                    CASE
                        WHEN r.gender IS NULL THEN 'unknown'
                        WHEN MOD(r.gender, 2) = 1 THEN '남자'
                        ELSE '여자'
                    END AS gender,
                    CASE
                        WHEN r.birthday IS NULL THEN NULL
                        ELSE
                            FLOOR(
                                (20260514 - r.birthday) / 10000
                            )
                    END AS age
                from gbike.rich_user r
        ) r
    )
    select
            date(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul')) as dt,
            r.`large_region`,
            r.`mid_region`,
            r.`sub_region`,
            b.one_category,
            u.gender,
            u.age_group,
            count(o.order_id) as `trip_count`,
            count(distinct o.bicycle_sn) as `device_count`,
            count(distinct o.user_id) as `user_count`,
            sum(o.order_amount) as `order_amount`,
            sum(o.pay_amount) as `pay_amount`
    FROM
      gbike.rich_orders o
      join region r on o.region_id = r.region_id
      join bike  b on o.bicycle_id = b.bicycle_id
      join user u on u.user_id = o.user_id
    WHERE 1=1
      and o.order_state = 2
      AND o.add_time BETWEEN UNIX_TIMESTAMP(CONVERT_TZ('{start_date} 00:00:00', 'Asia/Seoul', 'UTC'))
                         AND UNIX_TIMESTAMP(CONVERT_TZ('{end_date} 23:59:59', 'Asia/Seoul', 'UTC'))
    group by 1, 2, 3, 4, 5, 6, 7
    """
    return query

def main():
    engine = get_engine()
    
    # Define date chunks (1 month each)
    date_ranges = [
        # 2026
        ('2026-01-01', '2026-01-31'),
        ('2026-02-01', '2026-02-28'),
        ('2026-03-01', '2026-03-31'),
        ('2026-04-01', '2026-04-30'),
        ('2026-05-01', '2026-05-13'),
        # 2025
        ('2025-01-01', '2025-01-31'),
        ('2025-02-01', '2025-02-28'),
        ('2025-03-01', '2025-03-31'),
        ('2025-04-01', '2025-04-30'),
        ('2025-05-01', '2025-05-13'),
    ]
    
    all_data = []
    
    for start_date, end_date in date_ranges:
        print(f"Fetching data from {start_date} to {end_date}...")
        query = get_query(start_date, end_date)
        try:
            with engine.connect() as conn:
                df = pd.read_sql(query, conn)
                all_data.append(df)
                print(f"  Rows fetched: {len(df)}")
        except Exception as e:
            print(f"  Error fetching {start_date} to {end_date}: {e}")
            
    if not all_data:
        print("No data fetched. Exiting.")
        return
        
    final_df = pd.concat(all_data, ignore_index=True)
    
    # Post-processing: Add Year-Week
    final_df['dt'] = pd.to_datetime(final_df['dt'])
    final_df['year_week'] = final_df['dt'].dt.strftime('%Y-W%U') # %U: Week starting Sunday, %W: Monday. Let's use %V or manual.
    # User requested '주차별'. Let's use ISO week or simple week.
    final_df['year_week'] = final_df['dt'].apply(lambda x: x.strftime('%Y-W%W'))
    
    # Save to Excel
    save_path = '/Users/galaxy/codebase/results/data_extract/gangneung_trip_analysis_v1/gangneung_trip_data.xlsx'
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # Reorder columns
    cols = ['dt', 'year_week', 'large_region', 'mid_region', 'sub_region', 'one_category', 'gender', 'age_group', 
            'trip_count', 'device_count', 'user_count', 'order_amount', 'pay_amount']
    final_df = final_df[cols]
    
    final_df.to_excel(save_path, index=False)
    print(f"\nTotal rows: {len(final_df)}")
    print(f"Data successfully saved to: {save_path}")

if __name__ == "__main__":
    main()
