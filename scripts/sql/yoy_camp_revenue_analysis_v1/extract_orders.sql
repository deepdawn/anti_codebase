with user as ( -- 유저 구분
select *,
        case
            when r.age is null then '알수없음'
            when r.age >= 10 and r.age < 20 then '10대'
            when r.age >= 20 and r.age < 30 then '20대'
            when r.age >= 30 and r.age < 40 then '30대'
            when r.age >= 40 and r.age < 50 then '40대'
            when r.age >= 50 and r.age < 60 then '50대'
        else '기타' end as age_group
from (
        select user_id,nickname,region_id,
            CASE 
                WHEN r.gender IS NULL THEN null
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
            END AS age
        from gbike.rich_user r
) r
)
SELECT
    o.order_id,
    CONVERT_TZ(FROM_UNIXTIME(o.start_time), 'UTC', 'Asia/Seoul') AS start_datetime_kst,
    CONVERT_TZ(FROM_UNIXTIME(o.end_time), 'UTC', 'Asia/Seoul') AS end_datetime_kst,
    CASE
        WHEN DAYOFWEEK(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul')) IN (1, 7) THEN 'Weekend'
        ELSE 'Weekday'
    END AS day_type,
    HOUR(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul')) AS hour_of_day,
    CASE
        WHEN HOUR(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul')) BETWEEN 0 AND 5 THEN '00-05'
        WHEN HOUR(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul')) BETWEEN 6 AND 10 THEN '06-10'
        WHEN HOUR(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul')) BETWEEN 11 AND 16 THEN '11-16'
        WHEN HOUR(CONVERT_TZ(FROM_UNIXTIME(o.add_time), 'UTC', 'Asia/Seoul')) BETWEEN 17 AND 21 THEN '17-21'
        ELSE '22-23'
    END AS hour_band,
    o.distance,
    o.order_amount,
    o.pay_amount,
    o.out_of_area_charge,
    (COALESCE(CASE WHEN o.from_api = 'gcooter' THEN o.pay_amount ELSE o.order_amount END, 0) + COALESCE(o.out_of_area_charge, 0)) / 1.1 AS net_revenue_krw,
    o.from_api,
    ST_X(o.start_point) AS start_lon,
    ST_Y(o.start_point) AS start_lat,
    ST_X(o.end_point) AS end_lon,
    ST_Y(o.end_point) AS end_lat,
    u.gender,
    u.age_group,
    r2.region_name AS camp_name,
    r3.region_name AS small_region_name,
    '킥보드' AS vehicle_type,
    CASE 
        WHEN o.add_time >= UNIX_TIMESTAMP('2026-04-30 15:00:00') THEN 'CY'
        ELSE 'PY'
    END AS period_type
FROM gbike.rich_orders o
JOIN gbike.rich_region r3 ON o.region_id = r3.region_id
JOIN gbike.rich_region r2 ON r3.parent_id = r2.region_id
LEFT JOIN user u ON o.user_id = u.user_id
WHERE o.order_state = 2
  AND r2.region_name IN ('대구1캠프', '대구2캠프', '부산2캠프', '부산3캠프', '원주캠프')
  AND o.bicycle_type IN (9, 10, 11, 12, 13, 16, 19, 23) -- 킥보드 전용
  AND (
      (o.add_time >= UNIX_TIMESTAMP('2026-04-30 15:00:00') AND o.add_time < UNIX_TIMESTAMP('2026-05-18 15:00:00'))
      OR 
      (o.add_time >= UNIX_TIMESTAMP('2025-04-30 15:00:00') AND o.add_time < UNIX_TIMESTAMP('2025-05-18 15:00:00'))
  );
