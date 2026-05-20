# YoY Camp Revenue Analysis (Daegu 1/2, Busan 2/3, Wonju)

대구1, 대구2, 부산2, 부산3, 원주 캠프의 2026년 5월 MTD (5/1~5/18) 매출 부진 원인을 파악하기 위해 전년도 동기간과 비교 분석을 수행합니다. 

## User Review Required

> [!IMPORTANT]
> - 데이터 추출을 위한 SQL 작성을 완료했습니다. 
> - 파일 경로는 `/Users/galaxy/anti_codebase/scripts/sql/yoy_camp_revenue_analysis_v1/` 내에 `extract_orders.sql` 과 `extract_deployed.sql` 두 가지로 나누어 저장하였습니다.
> - `extract_orders.sql`: 매출, 대당회전수, 데모그라피, 위치 정보 분석용 트립 데이터
> - `extract_deployed.sql`: 배치수 계산용 데이터 (가동 대수)
> - 할당대수는 요청하신 대로 `base_data/secondary_data/daily allocated number per camp.xlsx` 데이터를 활용할 계획입니다.
> 
> **위 SQL 및 분석 방향성에 대한 검토 및 승인을 부탁드립니다.** 승인해주시면 Python 스크립트를 작성하여 데이터를 추출하고 분석을 이어가겠습니다.

## Open Questions

> [!WARNING]
> 1. 제공해주실 `daily allocated number per camp.xlsx` 파일 내에서 작년(2025년) 동기간의 할당대수 데이터도 포함되어 있는지 확인이 필요합니다. 만약 포함되어 있지 않다면 별도의 방식으로 산출해야 합니다.
> 2. `출루수` 지표 계산 시, '특정 기간 동안 1회 이상 이용된 기기의 수(Distinct Bicycle ID)'로 산출하는 방향이 맞는지 확인해주시면 감사하겠습니다.

## Proposed Changes

### 1. Data Extraction (SQL)

- **[NEW]** [extract_orders.sql](file:///Users/galaxy/anti_codebase/scripts/sql/yoy_camp_revenue_analysis_v1/extract_orders.sql)
  - 내용: `gbike.rich_orders`, `rich_user`, `rich_region`, `rich_bicycle`을 조인하여 트립(Trip) 단위 상세 내역 추출 (시간은 UTC → KST 기준 필터링 적용)
- **[NEW]** [extract_deployed.sql](file:///Users/galaxy/anti_codebase/scripts/sql/yoy_camp_revenue_analysis_v1/extract_deployed.sql)
  - 내용: `gbike_smartops.vehicle_statistics_data`에서 각 캠프의 기간별 가용 대수(Deployed Units)의 일별 평균치 추출

### 2. Data Processing & Analysis (Python)

향후 작성될 Python 코드의 개요입니다.
- **[NEW]** `scripts/python/yoy_camp_revenue_analysis_v1/extract_data.py`: `utils/test_db_conn.py`를 활용해 SQL 쿼리를 실행하고 데이터를 추출하여 `/base_data/primary_data/yoy_camp_revenue_analysis_v1` 에 저장.
- **[NEW]** `scripts/python/yoy_camp_revenue_analysis_v1/analyze_data.py`: 
  - 기본 지표 YoY 산출 (대당 매출, 회전율, 건당 매출, 배치수 대비 출루수)
  - 데모그라피 분석 (연령대별, 성별 유저 분포 및 매출 기여도 변화)
  - 위치 핫스팟/콜드스팟 분석 및 WKT 시각화

## Verification Plan

- SQL 추출 결과의 정합성 검증 (총 매출, 주문 건수 등의 기본 집계치 확인)
- Python 연산을 통해 산출된 대당 매출/회전율과 내부 보고 기준이 맞는지 샘플 데이터 비교
