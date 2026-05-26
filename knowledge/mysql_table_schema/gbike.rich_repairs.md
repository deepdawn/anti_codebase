# gbike.rich_repairs 테이블 스키마 정의

기기의 고장 신고 및 정비 이력을 관리하는 테이블입니다.

## 주요 컬럼 상세 정보

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **id** | INT | PRIMARY KEY | 정비 고유 ID | |
| **bicycle_sn** | VARCHAR | | 기기 번호 | `rich_bicycle.bicycle_sn`과 조인 |
| **status** | VARCHAR | INDEX | 정비 상태 | repair_ing, repair_complete 등 |
| **report_admin_id**| INT | | 입고자(신고자) ID | |
| **review_admin_id**| INT | | 정비 담당자 ID | |
| **type** | VARCHAR | | 정비 타입 | 고장 원인 구분 |
| **memo** | TEXT | INDEX | 정비 상세 메모 | |
| **repair_point** | POINT | INDEX (SPATIAL) | 정비 발생 위치 | |
| **created_at** | TIMESTAMP | | 정비 접수 시점 | 입고 시점 |
| **complete_at** | TIMESTAMP | | 정비 완료 시점 | 출고 시점 |

## 분석 활용 가이드 (Lead Data Scientist's Insight)

1.  **정비 리드 타임(Lead Time)**:
    - `TIMESTAMPDIFF(HOUR, created_at, complete_at)`를 계산하여 기기가 정비 센터에 머무는 평균 시간을 분석합니다. 이는 운영 효율 지표(Availability)에 직접적인 영향을 미칩니다.
2.  **기기 내구성 분석**:
    - `bicycle_sn`별 정비 빈도를 분석하여 특정 모델이나 특정 로트(Lot)의 결함 여부를 파악할 수 있습니다.
3.  **정비 사유 통계**:
    - `type` 컬럼과 `memo`의 텍스트 마이닝을 통해 주로 어떤 부품(브레이크, 타이어, 배터리 등)에서 고장이 발생하는지 통계를 산출합니다.
