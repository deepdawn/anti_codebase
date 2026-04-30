# gbike_smartops.bicycle_data 테이블 스키마 정의

기기의 배터리 상태 및 운영 지표를 요약하여 관리하는 스마트 운영 지원용 테이블입니다.

## 주요 컬럼 상세 정보

| 컬럼명 | 데이터 타입 | 설명 | 비고 |
| :--- | :--- | :--- | :--- |
| **id** | INT | 고유 식별자 | |
| **date** | DATETIME | 집계 날짜 | |
| **region_id** | INT | 지역 ID | `gbike.rich_region`과 연동 |
| **region_1** | VARCHAR | 대지역 명칭 | |
| **region_2** | VARCHAR | 중지역 명칭 | |
| **region_3** | VARCHAR | 소지역 명칭 | |
| **bicycle_type**| INT | 기기 유형 | |
| **battery_0_20** | INT | 배터리 0~20% 기기 수 | 교체 시급 대상 |
| **battery_20_40**| INT | 배터리 20~40% 기기 수 | |
| **average_battery**| DOUBLE | 지역 내 평균 배터리 잔량 | |
| **trip_count** | INT | 해당 지역의 트립 수 | |
| **total_count** | INT | 해당 지역의 총 기기 수 | |

## 분석 활용 가이드 (Lead Data Scientist's Insight)

1.  **배터리 관리 우선순위**:
    - `battery_0_20` 컬럼 비중이 높은 지역을 우선적으로 배터리 교체 작업(Battery Swapping) 대상으로 선정합니다.
2.  **운영 밀도 분석**:
    - `total_count` 대비 `trip_count` 비율을 통해 지역별 기기 가동률을 빠르게 파악할 수 있습니다.
3.  **지역별 상태 모니터링**:
    - 별도의 조인 없이도 `region_1` ~ `region_3` 명칭이 포함되어 있어, 대시보드 제작 및 퀵 리포트 생성에 매우 효율적입니다.
