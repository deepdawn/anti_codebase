# analysis_kickboard_down: W19 vs W20 캠프 대당 매출 감소 원인 분석 플랜

W19(5월 1주차) 대비 W20(5월 2주차)에 킥보드 대당 매출이 유독 크게 감소한 5개 캠프(대구1, 대구2, 부산2, 부산3, 원주)에 대한 원인을 다각도로 분석하기 위한 플랜입니다.

## User Review Required

> [!IMPORTANT]
> **Subfolder Name 필요**: Rule 5에 따라 분석 스크립트와 쿼리 결과를 저장할 하위 폴더(subfolder) 이름이 필요합니다. 어떤 이름으로 생성할지 알려주세요 (예: `analysis_kickboard_down`).

## 1. 분석 개요 및 목적
- **대상 기간**: 
  - W19: 2026-05-04 ~ 2026-05-10
  - W20: 2026-05-11 ~ 2026-05-17
- **대상 캠프**: 대구1, 대구2, 부산2, 부산3, 원주
- **분석 목적**: 
  단순 수요(이용건수) 감소인지, 특정 데모그라픽(10대/20대, 남/여)에서의 이탈인지, 특정 핫스팟(학교, 역 등)에서의 이용량 급감인지 파악하여 명확한 원인 진단.

## 2. 데이터 확보 (SQL 작성 방안)
Python에서 심층적인 위치(군집화) 및 데모그라피 분석을 수행하기 위해 **트립 단위(Trip-level) 원시 데이터**를 추출하는 쿼리를 작성합니다.

```sql
WITH region AS (
    SELECT  r.region_id,
            r.region_name AS '소지역',
            rr.region_name AS '중지역'
    FROM    gbike.rich_region r
    JOIN    gbike.rich_region rr ON r.parent_id = rr.region_id
    WHERE   (rr.region_name LIKE '%대구1%' 
             OR rr.region_name LIKE '%대구2%' 
             OR rr.region_name LIKE '%부산2%' 
             OR rr.region_name LIKE '%부산3%' 
             OR rr.region_name LIKE '%원주%')
            AND rr.depth = 2
), 
user_demo AS (
    SELECT user_id, 
           CASE 
               WHEN gender IS NULL THEN 'Unknown'
               WHEN MOD(gender, 2) = 1 THEN 'Male'
               ELSE 'Female'
           END AS gender,
           CASE
               WHEN birthday IS NULL THEN NULL
               ELSE FLOOR((EXTRACT(YEAR FROM CURRENT_DATE) * 10000 + EXTRACT(MONTH FROM CURRENT_DATE) * 100 + EXTRACT(DAY FROM CURRENT_DATE) - CAST(birthday AS UNSIGNED)) / 10000)
           END AS age
    FROM gbike.rich_user
)
SELECT 
    CASE 
        WHEN ro.start_time BETWEEN UNIX_TIMESTAMP(CONVERT_TZ('2026-05-04 00:00:00', 'Asia/Seoul', 'UTC')) AND UNIX_TIMESTAMP(CONVERT_TZ('2026-05-10 23:59:59', 'Asia/Seoul', 'UTC')) THEN 'W19'
        WHEN ro.start_time BETWEEN UNIX_TIMESTAMP(CONVERT_TZ('2026-05-11 00:00:00', 'Asia/Seoul', 'UTC')) AND UNIX_TIMESTAMP(CONVERT_TZ('2026-05-17 23:59:59', 'Asia/Seoul', 'UTC')) THEN 'W20'
    END AS week_num,
    r.중지역 AS camp_name,
    r.소지역 AS small_region_name,
    ro.order_id,
    ro.bicycle_sn,
    ud.gender,
    CASE
        WHEN ud.age IS NULL THEN 'Unknown'
        WHEN ud.age < 20 THEN 'Under 20'
        WHEN ud.age < 30 THEN '20s'
        WHEN ud.age < 40 THEN '30s'
        WHEN ud.age < 50 THEN '40s'
        WHEN ud.age < 60 THEN '50s'
        ELSE '60s+' 
    END AS age_group,
    (ro.pay_amount + ro.out_of_area_charge) / 1.1 AS net_revenue,
    TIMESTAMPDIFF(MINUTE, FROM_UNIXTIME(ro.start_time), FROM_UNIXTIME(ro.end_time)) AS duration_min,
    ST_X(ro.start_point) AS start_lng,
    ST_Y(ro.start_point) AS start_lat
FROM gbike.rich_orders ro
JOIN region r ON ro.region_id = r.region_id
LEFT JOIN user_demo ud ON ro.user_id = ud.user_id
WHERE ro.order_state = 2
  AND ro.start_time BETWEEN UNIX_TIMESTAMP(CONVERT_TZ('2026-05-04 00:00:00', 'Asia/Seoul', 'UTC')) 
                        AND UNIX_TIMESTAMP(CONVERT_TZ('2026-05-17 23:59:59', 'Asia/Seoul', 'UTC'))
  AND ro.bicycle_type IN (9,10,11,12,13,16,19,23) -- 스쿠터(킥보드)만 필터링
;
```

## 3. 진행 단계 (Milestones)
1. **데이터 추출**: (현재 단계) 사용자 승인 및 폴더명 확인 후 SQL을 저장하고 추출 스크립트 실행
2. **전반적 지표 비교 (W19 vs W20)**: 캠프별 회전율, 매출, 가동 대수 증감 확인
3. **데모그라피 및 공간 분석**: 
    - 성별/연령대별 이용량 이탈폭 확인
    - GeoJSON & 공간분석 패키지를 통한 주요 이탈 구역(Start point) 클러스터링 및 시각화 파악
4. **결과 시각화 및 리포팅**: 인사이트 정리 후 MS Teams 등으로 전송

## Open Questions
- **Subfolder Name**: SQL 및 결과 파일을 저장할 서브 폴더 이름을 지정해주세요. (예: `analysis_kickboard_down`)
- **Scooter Type**: `gbike_all.sql`에 기록된 킥보드 타입(9,10,11,12,13,16,19,23) 외에 추가로 포괄해야 할 타입이 있습니까?
