# 강릉캠프 16세 미만 탑승 현황 및 기기별 매출 분석 데이터 추출 계획

본 계획서는 강릉캠프의 킥보드 매출 저조 원인을 분석하기 위해, 16세 미만 유저의 자전거 이용 급증 여부와 기기별 매출 현황을 비교 분석하기 위한 데이터 추출 과정을 정의합니다.

## User Review Required

> [!IMPORTANT]
> **데이터 추출 기간**: 2026.01.01 ~ 2026.05.13 및 2025.01.01 ~ 2025.05.13 (전년 동기간 비교용)
> **연령대 구분**: 요청하신 대로 16세 미만을 별도 그룹으로 분리하여 추출합니다.
> **주차별 집계**: 분석의 용이성을 위해 DB에서 일별 데이터를 추출한 후, 파이썬에서 주차(Year-Week) 정보를 추가하여 처리하겠습니다.

## Proposed Changes

### [Component] Data Extraction Script

#### [NEW] [extract_gangneung_data.py](file:///Users/galaxy/codebase/scripts/python/gangneung_trip_analysis_v1/extract_gangneung_data.py)
- `rich_orders`, `rich_user`, `rich_bicycle`, `rich_region` 테이블을 조인하여 데이터 추출.
- **연령 계산**: `FLOOR((YEAR(CURRENT_DATE) * 10000 + MONTH(CURRENT_DATE) * 100 + DAY(CURRENT_DATE) - birthday) / 10000)` 로직 적용.
- **분할 쿼리**: 1개월 단위로 `add_time` 기준 루프를 돌며 쿼리 실행.
- **결과 저장**: `utf-8-sig` 인코딩을 적용한 Excel(.xlsx) 파일로 `/results/data_extract/gangneung_trip_analysis_v1/` 경로에 저장.

### [Component] SQL Query Logic (Python 내부 포함)
- **Age Groups**:
    - Under 16
    - 16 ~ 20 (Exclusive)
    - 20s, 30s, 40s, 50s
    - Others
- **Dimensions**: 일자(dt), 소지역, 카테고리(Bicycle/Scooter), 성별, 연령대.
- **Metrics**: 트립수, 운행기기수(중복제거), 매출(order_amount), 유저수.

## Verification Plan

### Automated Verification
- 추출된 데이터의 총 행 수(Row count)가 0이 아닌지 확인.
- `Bicycle`과 `Scooter` 카테고리가 정상적으로 분류되었는지 샘플 검증.
- 16세 미만 데이터가 존재하는지 확인.

### Manual Verification
- 추출된 Excel 파일에서 2026년과 2025년 데이터가 모두 포함되어 있는지 확인.
- 요청된 컬럼(주차별, 소지역별, 연령별)이 모두 존재하는지 확인.
