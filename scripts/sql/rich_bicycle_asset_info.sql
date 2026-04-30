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
		else 'none'	END as two_category,
		case when regexp_like(rb.region_name, '임대|파트너') then 1 else 0 end as franchise_yn,
		CONVERT_TZ(FROM_UNIXTIME(rb.add_time),'UTC','Asia/Seoul') as registerd_at,
		CONVERT_TZ(FROM_UNIXTIME(rb.last_used_time),'UTC','Asia/Seoul') as last_used_at,
		rb.speed_mode ->'$.low_speed_limit' AS low_speed,
		rb.speed_mode ->'$.high_speed_limit' AS high_speed
from gbike.rich_bicycle rb 
