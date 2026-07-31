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
            END AS age,
            date(CONVERT_TZ(FROM_UNIXTIME(r.add_time),'UTC','Asia/Seoul')) as dt
        from gbike.rich_user r
) r
