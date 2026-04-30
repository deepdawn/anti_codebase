# gbike.rich_orders 테이블 스키마 정의

트립(Trip) 정보가 저장되는 테이블로, 탑승 시간, 위치, 거리, 요금 등 핵심 매출 및 운영 지표 산출의 기초가 됩니다.

## 주요 컬럼 상세 정보

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **order_id** | INT | PRIMARY KEY | 트립 고유 식별자 | |
| **order_sn** | BIGINT | INDEX | 주문 시리얼 넘버 | |
| **user_id** | INT | INDEX | 유저 ID | `rich_user`와 조인 |
| **bicycle_id** | INT | | 기기 ID | `rich_bicycle`과 조인 |
| **bicycle_sn** | VARCHAR | INDEX | 기기 번호(QR번호 등) | |
| **add_time** | INT | INDEX | 주문 생성 시점 | Unix Timestamp |
| **start_time** | INT | | 실제 탑승 시작 시점 | Unix Timestamp |
| **end_time** | INT | | 탑승 종료 시점 | Unix Timestamp |
| **region_id** | INT | INDEX | 발생 지역 ID | `rich_region`과 조인 |
| **distance** | DECIMAL | | 주행 거리 | 단위: 미터(m) |
| **order_amount**| DECIMAL | | 주문 합계 금액 | |
| **pay_amount** | DECIMAL | | 실제 결제 금액 | 프로모션 제외 실매출 |
| **out_of_area_charge**| INT | | 지역 외 반납 추가금 | |
| **order_state** | TINYINT | INDEX | 주문 상태 | 2: 완료, 1: 진행 중, -1: 취소 등 |
| **start_point** | POINT | INDEX (SPATIAL) | 탑승 시작 위치 | 공간 데이터 (GeoJSON 활용 가능) |
| **end_point** | POINT | INDEX (SPATIAL) | 탑승 종료 위치 | 공간 데이터 |
| **currency_code**| CHAR | | 결제 통화 코드 | 'krw', 'usd' 등 |
| **from_api** | VARCHAR | INDEX | 유입 채널 | 'gcooter' 등 |

## 분석 활용 가이드 (Lead Data Scientist's Insight)

1.  **매출(Net Revenue) 산출**: 
    - 실매출은 `(pay_amount + out_of_area_charge) / 1.1` (VAT 제외) 공식을 주로 사용합니다. `from_api`가 'gcooter'가 아닌 경우 `order_amount`를 기준으로 하기도 하므로 채널별 확인이 필요합니다.
2.  **주행 시간 계산**: 
    - `TIMESTAMPDIFF(SECOND, start_time, end_time)`를 사용하여 분 단위 주행 시간을 산출합니다.
3.  **지리적 수요 분석**: 
    - `start_point`와 `end_point` 컬럼을 `ST_X()`, `ST_Y()` 함수로 변환하여 핫스팟(Hotspot) 분석 및 기기 재배치 전략 수립에 활용합니다.
4.  **유효 주문 필터링**: 
    - 분석 시 반드시 `order_state = 2` (완료된 주문) 조건을 확인하여 취소되거나 비정상적인 주문을 제외해야 합니다.
