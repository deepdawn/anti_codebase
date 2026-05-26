SELECT
    DATE_FORMAT(FROM_UNIXTIME(o.add_time), '%Y-%m') AS month_str,
    DATE_FORMAT(FROM_UNIXTIME(o.add_time), '%x-W%v') AS week_str,
    DATE_FORMAT(FROM_UNIXTIME(o.add_time), '%Y-%m-%d') AS date_str,
    r3.region_name AS small_area,
    COUNT(o.order_id) AS trip_count,
    SUM((o.pay_amount + o.out_of_area_charge) / 1.1) AS net_revenue_krw
FROM gbike.rich_orders o
JOIN gbike.rich_bicycle b 
  ON o.bicycle_id = b.bicycle_id
JOIN gbike.rich_region r3 
  ON o.region_id = r3.region_id
JOIN gbike.rich_region r2 
  ON r3.parent_id = r2.region_id
WHERE r2.region_name = '부산3캠프'
  AND r3.depth = 3
  AND r2.depth = 2
  AND b.type IN (9, 10, 11, 12, 13, 16, 19, 23)
  AND o.order_state = 2
  AND o.add_time >= UNIX_TIMESTAMP('{start} 00:00:00')
  AND o.add_time < UNIX_TIMESTAMP('{end} 00:00:00')
GROUP BY
    month_str,
    week_str,
    date_str,
    small_area;
