# Table Schema: `gbike.rich_daily_statistics` (Redshift)

## Description
지바이크의 지역 및 모델별 데일리 통계 데이터를 저장하는 테이블입니다. 캠프(중구역), 소구역 단위로 할당 및 배치된 기기 대수, 총 트립 수, 그리고 다양한 결제/환불 관련 집계 금액을 포함하고 있습니다.

## Schema Details

| Column Name | Data Type | Max Length | Nullable | Description |
| :--- | :--- | :--- | :--- | :--- |
| `region_id` | `smallint` | - | YES | 구역(Region) 고유 ID |
| `date` | `date` | - | YES | 통계 기준 날짜 |
| `high_region_name` | `varchar` | 100 | YES | 대구역(Center) 이름 |
| `middle_region_name` | `varchar` | 100 | YES | 중구역(Camp) 이름 |
| `low_region_name` | `varchar` | 100 | YES | 소구역(Small Area) 이름 |
| `model` | `varchar` | 60 | YES | 기기 모델 (예: 스쿠터, 자전거) |
| `assigned_count` | `smallint` | - | YES | 할당 대수 (캠프에 속한 전체 기기) |
| `deployed_count` | `smallint` | - | YES | 배치 대수 (그날 실제로 운행이 한번이라도 있었던 기기수. 가동률 산출 기준) |
| `order_count` | `smallint` | - | YES | 트립 수 (Order Count) |
| `calculated_order_amount` | `integer` | - | YES | 계산된 전체 주문 금액 |
| `calculated_pay_amount` | `integer` | - | YES | 계산된 실 결제 금액 |
| `calculated_out_of_area_charge` | `integer` | - | YES | 지역 외 반납 추가 요금 (Return Fee) |
| `refund_amount` | `integer` | - | YES | 환불 금액 |
| `refund_out_of_area_charge` | `integer` | - | YES | 지역 외 반납 추가 요금 환불액 |
