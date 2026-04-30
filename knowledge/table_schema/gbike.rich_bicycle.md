# gbike.rich_bicycle 테이블 스키마 정의

기기(전동 킥보드, 전기 자전거)의 물리적 정보와 현재 상태를 관리하는 테이블입니다.

## 주요 컬럼 상세 정보

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **bicycle_id** | INT | PRIMARY KEY | 기기 고유 식별자 | |
| **bicycle_sn** | VARCHAR | INDEX | 기기 번호 (QR번호) | |
| **region_id** | INT | INDEX | 현재 위치 소지역 ID | `rich_region`과 조인 |
| **type** | TINYINT | INDEX | 기기 유형 코드 | 9,10,11: 킥보드, 17,18,22: 자전거 등 |
| **status** | VARCHAR | | 현재 기기 상태 | registration, idle, riding, repair 등 |
| **lock_sn** | VARCHAR | INDEX | 스마트락 시리얼 번호 | |
| **is_using** | TINYINT | | 사용 중 여부 | 1: 사용 중, 0: 대기 중 |
| **last_used_time**| INT | | 마지막 사용 시점 | Unix Timestamp |
| **speed_mode** | JSON | | 속도 제한 설정 정보 | low_speed_limit, high_speed_limit 등 |
| **add_time** | INT | INDEX | 기기 등록 시점 | Unix Timestamp |
| **is_activated** | TINYINT | INDEX | 활성화 여부 | 운영 가능 상태 여부 |

## 분석 활용 가이드 (Lead Data Scientist's Insight)

1.  **기종 분류(Model Mapping)**:
    - `type` 코드를 바탕으로 'Scooter'와 'Bicycle'을 구분합니다. 
    - 예: `type IN (15, 17, 18, 22, 24)` -> Bicycle, `type IN (9, 10, 11, 12, 13, 16, 19, 23)` -> Scooter.
2.  **운영 효율 지표**:
    - `status = 'idle'`인 기기 대수를 파악하여 지역별 가용 대수(Deployed Units)를 산출합니다.
    - `last_used_time`과 현재 시점의 차이를 계산하여 '미사용 기간'을 분석, 장기 미사용 기기(Idle assets)를 식별합니다.
3.  **정비 필요성 판단**:
    - `status = 'repair'` 상태인 기기 목록을 `rich_repairs`와 조인하여 정비 소요 시간 및 원인을 분석합니다.
