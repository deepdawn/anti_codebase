# gbike.rich_region 테이블 스키마 정의

운영 지역의 계층 구조와 지역별 설정(요금, 운영 시간 등)을 관리하는 마스터 테이블입니다.

## 주요 컬럼 상세 정보

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **region_id** | INT | PRIMARY KEY | 지역 고유 식별자 | |
| **region_name** | VARCHAR | | 지역 명칭 | 소지역 단위 명칭 |
| **parent_id** | INT | INDEX | 상위 지역 ID | Self-Join을 통한 계층 구조 형성 |
| **depth** | INT | INDEX | 계층 깊이 | 1: 대지역, 2: 중지역, 3: 소지역 |
| **operation_type**| VARCHAR | INDEX | 운영 형태 | direct(직영), franchise(가맹) 등 |
| **is_used** | CHAR | INDEX | 사용 여부 | 'y': 운영 중, 'n': 미운영 |
| **region_bounds** | MEDIUMTEXT | | 지역 경계 (WKT/JSON) | 폴리곤 데이터 |
| **timezone** | VARCHAR | | 지역 시간대 | 한국: 'Asia/Seoul' |
| **country_code** | CHAR | INDEX | 국가 코드 | 'kr' 등 |
| **start_fee** | INT | | 기본 요금 | |
| **region_charge_fee**| INT | | 분당 요금 | |

## 분석 활용 가이드 (Lead Data Scientist's Insight)

1.  **지역 계층(Hierarchy) 구성**:
    - 이 테이블은 Self-Join을 통해 `소지역(3) -> 중지역(2, Camp) -> 대지역(1, Center)` 구조를 형성합니다. 
    - 분석 시 3단 조인을 통해 `대지역/중지역/소지역` 명칭을 한 번에 가져오는 쿼리 패턴이 자주 사용됩니다.
2.  **운영 지표 그룹화**:
    - `operation_type`을 기준으로 직영점과 가맹점의 성과(매출, 회전율)를 비교 분석할 때 필수적입니다.
3.  **지오펜싱(Geofencing)**:
    - `region_bounds` 데이터를 활용하여 특정 좌표가 어느 지역에 속하는지 판별하거나, 반납 제한 구역(Forbidden zone) 분석에 활용합니다.
