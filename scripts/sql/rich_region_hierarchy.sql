select	r.region_id,
		r.region_name as '소지역',
		rr.region_name as '중지역',
		rrr.region_name as '대지역'
from	gbike.rich_region r
join	gbike.rich_region rr on r.parent_id = rr.region_id
join	gbike.rich_region rrr on rr.parent_id = rrr.region_id
where	1=1
