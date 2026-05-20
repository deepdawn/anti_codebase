SELECT `출루수`.`date` AS `date`,
  `배치수`.`경도` AS `경도`,
  `배치수`.`기종` AS `기종`,
  `배치수`.`대지역` AS `대지역`,
  `배치수`.`배치 구분` AS `배치 구분`,
  `배치수`.`배치수` AS `배치수`,
  `배치수`.`배치존명` AS `배치존명`,
  `배치수`.`소지역` AS `소지역`,
  `배치수`.`위도` AS `위도`,
  `배치수`.`중지역` AS `중지역`,
  IFNULL(`출루수`.`출루수`, 0) AS `출루수`
FROM (
  SELECT 
      DATE(DATE_ADD(D.created_at, INTERVAL 9 HOUR)) AS 'date',
      D.deploy_type AS '배치 구분',
      D.model_type AS '기종',
      G.region_name AS '대지역',
      E.region_name AS '중지역',
      R.region_name AS '소지역',
      S.name AS '배치존명',
      S.lat AS '위도',
      S.lng AS '경도',
      COUNT(DISTINCT D.id) AS '배치수'
  FROM
      gbike.rich_deploy_zone_usages D
          JOIN
      gbike.rich_release_spot S ON D.deploy_zone_id = S.id
          JOIN
      gbike.rich_region R ON S.region_id = R.region_id
          JOIN
      gbike.rich_region E ON R.parent_id = E.region_id
          JOIN
      gbike.rich_region G ON E.parent_id = G.region_id
  WHERE
      (
          (DATE(DATE_ADD(D.created_at, INTERVAL 9 HOUR)) >= '2026-05-01' AND DATE(DATE_ADD(D.created_at, INTERVAL 9 HOUR)) <= '2026-05-18')
          OR
          (DATE(DATE_ADD(D.created_at, INTERVAL 9 HOUR)) >= '2025-05-01' AND DATE(DATE_ADD(D.created_at, INTERVAL 9 HOUR)) <= '2025-05-18')
      )
          AND D.deleted_at IS NULL
          AND D.model_type = 'scooter'
          AND E.region_name IN ('대구1캠프', '대구2캠프', '부산2캠프', '부산3캠프', '원주캠프')
  GROUP BY 1 , 2 , 3 , 4 , 5 , 6 , 7 , 8 , 9
) `배치수`
  LEFT JOIN (
  SELECT 
      DATE(DATE_ADD(D.released_at, INTERVAL 9 HOUR)) AS 'date',
      D.deploy_type AS '배치 구분',
      D.model_type AS '기종',
      G.region_name AS '대지역',
      E.region_name AS '중지역',
      R.region_name AS '소지역',
      S.name AS '배치존명',
      S.lat AS '위도',
      S.lng AS '경도',
      COUNT(DISTINCT D.id) AS '출루수'
  FROM
      gbike.rich_deploy_zone_usages D
          JOIN
      gbike.rich_release_spot S ON D.deploy_zone_id = S.id
          JOIN
      gbike.rich_region R ON S.region_id = R.region_id
          JOIN
      gbike.rich_region E ON R.parent_id = E.region_id
          JOIN
      gbike.rich_region G ON E.parent_id = G.region_id
  WHERE
      (
          (DATE(DATE_ADD(D.released_at, INTERVAL 9 HOUR)) >= '2026-05-01' AND DATE(DATE_ADD(D.released_at, INTERVAL 9 HOUR)) <= '2026-05-18')
          OR
          (DATE(DATE_ADD(D.released_at, INTERVAL 9 HOUR)) >= '2025-05-01' AND DATE(DATE_ADD(D.released_at, INTERVAL 9 HOUR)) <= '2025-05-18')
      )
          AND D.deleted_at IS NULL
          AND D.model_type = 'scooter'
          AND E.region_name IN ('대구1캠프', '대구2캠프', '부산2캠프', '부산3캠프', '원주캠프')
  GROUP BY 1 , 2 , 3 , 4 , 5 , 6 , 7 , 8 , 9
) `출루수` ON ((`배치수`.`date` = `출루수`.`date`) AND (`배치수`.`기종` = `출루수`.`기종`) AND (`배치수`.`대지역` = `출루수`.`대지역`) AND (`배치수`.`배치 구분` = `출루수`.`배치 구분`) AND (`배치수`.`배치존명` = `출루수`.`배치존명`) AND (`배치수`.`소지역` = `출루수`.`소지역`) AND (`배치수`.`중지역` = `출루수`.`중지역`));
