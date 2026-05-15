# 강릉캠프 데이터 가공 계획 (gangneung_trip_data_v1)

추출된 트립 데이터와 Redshift 일별 통계 데이터를 결합하여 분석용 세컨더리 데이터를 생성하는 계획입니다.

## User Review Required

> [!IMPORTANT]
> - **가공 로직**: 소지역/기종별 총 트립 수 대비 각 인구통계학적 그룹(성별, 연령대 등)의 트립 비율을 계산하고, 이 비율에 따라 `assigned_count`와 `revenue`를 배분(Allocation)합니다.
> - **저장 경로**: `/base_data/secondary_data/gangneung_trip_data_v1/gangneung_trip_data_v1_processed.xlsx` 경로에 저장할 예정입니다.

## Proposed Changes

### 1. 환경 설정 및 폴더 구조 생성
- `/base_data/secondary_data/gangneung_trip_data_v1` 생성

### 2. 데이터 가공 스크립트 작성
- `scripts/python/gangneung_trip_data_v1/process_gangneung_data.py` [NEW]
    - 추출 데이터(`gangneung_trip_data_v1_total.xlsx`)와 통계 데이터(`redshift_rich_daily_statistics.xlsx`) 로드.
    - 데이터 클렌징: 날짜 형식 통일 및 컬럼명 매핑 (`dt` <-> `date`, `소지역` <-> `low_region_name`, `one_category` <-> `vehicle_type`).
    - **비율 계산**: (일자, 소지역, 기종) 그룹별 총 트립 수 대비 개별 로우의 트립 비율 계산.
    - **결합 및 배분**: 통계 데이터와 Join 후, 계산된 비율을 `assigned_count` 및 `revenue`에 곱하여 할당.
    - 최종 결과를 `.xlsx`로 저장.

### 3. 데이터 가공 실행
- 작성된 스크립트를 실행하여 세컨더리 데이터 생성.

## Verification Plan

### Automated Tests
- 가공 후 `assigned_count`와 `revenue`의 합계가 원본 통계 데이터와 일치하는지 확인 (검증 스크립트 실행).
- 결측치 및 Join 누락 발생 여부 체크.

### Manual Verification
- 가공된 데이터 샘플을 확인하여 비율 배분이 정상적으로 이루어졌는지 검토.
