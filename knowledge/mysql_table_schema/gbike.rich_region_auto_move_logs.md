# gbike.rich_region_auto_move_logs 테이블 스키마 정의

기기의 관리 지역이 변경될 때 발생하는 로그를 기록하는 테이블입니다.

## 주요 컬럼 상세 정보

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **bicycle_sn** | VARCHAR | INDEX | 기기 번호 | |
| **before_region_region_id**| INT | INDEX | 변경 전 지역 ID | |
| **current_region_id**| INT | INDEX | 변경 후 지역 ID | |
| **project_action** | VARCHAR | | 이동 사유 | trip_complete, deploy, admin_force 등 |
| **order_id** | INT | INDEX | 연관 트립 ID | 트립 종료로 인한 이동 시 기록 |
| **admin_id** | INT | INDEX | 작업 관리자 ID | 관리자가 직접 이동시킨 경우 |
| **created_at** | DATETIME | | 로그 생성 일시 | 이동 발생 시점 |

## 분석 활용 가이드 (Lead Data Scientist's Insight)

1.  **지역 간 기기 이동 추적**:
    - 기기가 어느 지역에서 어느 지역으로 흘러 들어가는지(Migration Path)를 분석하여 수요 불균형을 파악합니다.
2.  **재배치(Deploy) 효과 분석**:
    - `project_action = 'deploy'`인 데이터를 추출하여 관리 조직(Camp)의 재배치 작업량과 효율을 측정합니다.
3.  **트립 기반 지역 이동**:
    - `project_action = 'trip_complete'` 로그를 분석하여 유저들의 편도 이용 패턴(One-way pattern)을 정량화합니다.
