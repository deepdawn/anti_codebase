SELECT
    DATE(FROM_UNIXTIME(O.add_time + 32400)) AS kst_date,
    G.region_name AS depth1_region,
    E.region_name AS depth2_region,
    R.region_name AS depth3_region,
    O.from_api,
    -- 기종 정보 매핑 (bicycle_type 컬럼 사용)
    CASE O.bicycle_type
        WHEN 1 THEN 'GCOO-B1'
        WHEN 2 THEN 'UNKNOWN'
        WHEN 3 THEN '에어드레서'
        WHEN 9 THEN 'ES4'
        WHEN 10 THEN 'Max'
        WHEN 11 THEN 'Max Pro'
        WHEN 12 THEN 'GCOO-K1'
        WHEN 13 THEN 'Max Plus'
        WHEN 14 THEN '슈드레서'
        WHEN 15 THEN 'OMNI BICYCLE'
        WHEN 16 THEN 'GCOO-K2'
        WHEN 17 THEN 'GCOO-B3'
        WHEN 18 THEN 'GCOO-B2'
        WHEN 19 THEN 'Max Plus X'
        WHEN 22 THEN 'GCOO-B4'
        WHEN 23 THEN 'GCOO-K3'
        WHEN 24 THEN 'A200P'
        ELSE CONCAT('기타(', IFNULL(O.bicycle_type, 'NULL'), ')')
    END AS model_name,
    SUM(
        (
            CASE
                WHEN O.from_api = 'gcooter' THEN O.pay_amount
                ELSE O.order_amount
            END
            + O.out_of_area_charge
        ) / 1.1
    ) AS net_revenue
FROM
    gbike.rich_orders O
    JOIN gbike.rich_region R
        ON O.region_id = R.region_id
    JOIN gbike.rich_region E
        ON R.parent_id = E.region_id
    JOIN gbike.rich_region G
        ON E.parent_id = G.region_id
WHERE
    O.order_state = 2
  AND O.currency_code = 'krw'
  AND G.country_code = 'kr'
  AND O.add_time >= UNIX_TIMESTAMP('2026-03-01 00:00:00') - 32400
  AND O.add_time <  UNIX_TIMESTAMP('2026-04-24 00:00:00') - 32400
GROUP BY
    kst_date,
    depth1_region,
    depth2_region,
    depth3_region,
    O.from_api,
    model_name;
