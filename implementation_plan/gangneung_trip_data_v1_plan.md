# 강릉캠프 트립 데이터 추출 및 분석 계획 (gangneung_trip_data_v1)

이 계획은 2026년 1월 1일부터 5월 13일까지의 강릉캠프 트립 데이터와 전년 동기간 데이터를 추출하고 분석하기 위한 단계별 가이드를 제공합니다.

## User Review Required

> [!IMPORTANT]
> - 데이터 추출 경로: `/base_data/primary_data/gangneung_trip_data_v1` 폴더를 생성하여 저장할 예정입니다. 이 폴더명이 적절한지 확인 부탁드립니다.
> - 추출 기간: 2026년(1/1~5/13) 및 2025년(1/1~5/13) 데이터를 월 단위로 청킹하여 추출합니다.

## Proposed Changes

### 1. 환경 설정 및 폴더 구조 생성
- `/base_data/primary_data/gangneung_trip_data_v1` 생성 (사용자 확인 후)
- `/scripts/python/extract/gangneung` 생성 (추출 스크립트 저장)

### 2. 데이터 추출 스크립트 작성
- `scripts/python/extract/gangneung/extract_gangneung_trips.py` [NEW]
    - 제공된 SQL 쿼리를 기반으로 기간 파라미터를 입력받아 처리.
    - 월별(또는 특정 기간)로 루프를 돌며 `test_db_conn.py`를 활용해 데이터 추출.
    - 추출된 데이터는 CSV 형식(`utf-8-sig`)으로 저장.

### 3. 데이터 추출 실행
- 2025년 5개 청크, 2026년 5개 청크 추출.

## Verification Plan

### Automated Tests
- 추출된 각 CSV 파일의 로우 수 및 컬럼 구성 확인.
- `강릉캠프` 데이터만 포함되어 있는지 샘플 검증.

### Manual Verification
- 추출 완료 후 요약 리포트 제공.
