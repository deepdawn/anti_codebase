-- 신규 가입자의 가입일 기준 만 나이 및 신규 가입자 수 집계
-- MySQL 기준
-- 기간은 KST 가입일 기준으로 설정한다.
-- KST는 현재 DST가 없으므로 MySQL 타임존 테이블 의존을 피하기 위해 +09:00 고정 오프셋을 사용한다.
SET time_zone = '+00:00';
SET @start_date = '2026-06-01';
SET @end_date = '2026-06-30';
SET @start_add_time = UNIX_TIMESTAMP(CONCAT(@start_date, ' 00:00:00')) - 32400;
SET @end_add_time = UNIX_TIMESTAMP(DATE_ADD(CONCAT(@end_date, ' 00:00:00'), INTERVAL 1 DAY)) - 32400;

WITH new_users_raw AS (
    SELECT
        r.user_id,
        DATE(CONVERT_TZ(FROM_UNIXTIME(r.add_time), '+00:00', '+09:00')) AS register_dt,
        r.birthday
    FROM gbike.rich_user AS r
    WHERE r.add_time >= @start_add_time
      AND r.add_time < @end_add_time
      AND r.country_code = 'kr'
),
new_users_with_birth AS (
    SELECT
        user_id,
        register_dt,
        CASE
            WHEN birthday REGEXP '^[0-9]{8}$'
             AND STR_TO_DATE(birthday, '%Y%m%d') IS NOT NULL
             AND DATE_FORMAT(STR_TO_DATE(birthday, '%Y%m%d'), '%Y%m%d') = birthday
            THEN STR_TO_DATE(birthday, '%Y%m%d')
            ELSE NULL
        END AS birth_dt
    FROM new_users_raw
),
new_user_ages AS (
    SELECT
        user_id,
        register_dt,
        CASE
            WHEN birth_dt IS NULL THEN NULL
            WHEN birth_dt > register_dt THEN NULL
            ELSE TIMESTAMPDIFF(YEAR, birth_dt, register_dt)
        END AS age
    FROM new_users_with_birth
)
SELECT
    CASE
        WHEN age IS NULL THEN '알수없음'
        WHEN age < 10 THEN '10세 미만'
        WHEN age < 20 THEN '10대'
        WHEN age < 30 THEN '20대'
        WHEN age < 40 THEN '30대'
        WHEN age < 50 THEN '40대'
        WHEN age < 60 THEN '50대'
        ELSE '60대 이상'
    END AS age_group,
#     age,
    COUNT(DISTINCT user_id) AS new_user_count
FROM new_user_ages
GROUP BY
    age_group
#     age
ORDER BY
    CASE
        WHEN age IS NULL THEN 999
        ELSE age
    END;
