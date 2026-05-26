# gbike_smartops.vehicle_statistics_data 테이블 스키마 정의

기기의 시간별/지역별 운영 통계 및 미사용 기기 현황을 기록하는 테이블입니다.

## 주요 컬럼 상세 정보

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **date** | DATE | PK | 집계 날짜 | |
| **hour** | VARCHAR | PK | 집계 시간 | 00~23 |
| **region_id** | INT | PK | 지역 ID | |
| **type** | INT | PK | 기기 유형 | |
| **total_vehicle_count**| INT | | 총 기기 대수 | Allocated Units |
| **able_to_use** | INT | | 사용 가능 대수 | Deployed Units |
| **deactivate_24h_count**| INT | | 24시간 미사용 기기 수 | |
| **deactivate_48h_count**| INT | | 48시간 미사용 기기 수 | |
| **deactivate_24h_list** | MEDIUMTEXT| | 24시간 미사용 기기 목록 | 시리얼 번호 리스트 |

## 분석 활용 가이드 (Lead Data Scientist's Insight)

1.  **미사용 기기(Idle Assets) 분석**:
    - `deactivate_24h_count` 및 `48h_count` 데이터를 통해 수요가 없는 곳에 방치된 기기 비율을 측정하고, 수거 및 재배치 우선순위를 결정합니다.
2.  **시간대별 가용성 추이**:
    - `date`와 `hour`별로 `able_to_use` / `total_vehicle_count` 비율(Utilization Rate)을 계산하여 서비스 안정성을 모니터링합니다.
3.  **Allocated vs Deployed 비교**:
    - `total_vehicle_count`(할당 대수) 대비 `able_to_use`(실제 운영 대수) 차이를 통해 정비 또는 배터리 문제로 가동되지 못하는 기기의 규모를 파악합니다.
