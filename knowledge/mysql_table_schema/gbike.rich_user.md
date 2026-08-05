# gbike.rich_user 테이블 스키마 정의

이 테이블은 서비스 가입 유저의 기본 정보와 상태값을 관리합니다. 분석 시 유저 세그멘테이션(연령, 성별, 가입시기 등)의 기준이 되는 핵심 테이블입니다.

## 주요 컬럼 상세 정보

| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **user_id** | INT | PRIMARY KEY | 유저 고유 식별자 | |
| **user_sn** | VARCHAR | INDEX | 유저 시리얼 넘버 | 내부 관리용 번호 |
| **mobile** | CHAR | INDEX | 휴대폰 번호 | |
| **nickname** | VARCHAR | | 유저 닉네임 | |
| **platform** | VARCHAR | | 가입/주사용 플랫폼 | 'android', 'ios' 등 |
| **gender** | INT | | 성별 코드 | 홀수: 남성, 짝수: 여성 (MOD 연산 활용) |
| **birthday** | VARCHAR | | 생년월일 | 'YYYYMMDD' 형식 (나이 계산 시 활용) |
| **credit_point**| SMALLINT | | 신용 점수 | 서비스 이용 매너 점수 |
| **add_time** | INT | INDEX | 가입 시점 | Unix Timestamp (Asia/Seoul 변환 필요) |
| **region_id** | INT | | 가입/최근 지역 ID | `rich_region` 테이블과 조인 |
| **user_type** | INT | INDEX | 유저 타입 | 10: 일반 유저 등 |
| **riding_distance**| VARCHAR| | 누적 주행 거리 | 단위: 미터(m) |
| **agreements** | JSON | | 약관 동의 현황 | 마케팅 수신 동의 등 포함 |
| **country_code**| CHAR | INDEX | 국가 코드 | 한국은 'kr' |

## 분석 활용 가이드 (Lead Data Scientist's Insight)

1.  **성별 및 연령대 도출**: 
    - `gender` 컬럼은 직접적인 '남/여' 텍스트가 아닌 숫자로 저장되므로, `MOD(gender, 2) = 1`이면 남성으로 분류합니다.
    - `birthday`는 문자열이므로 현재 연도와의 차이를 계산하여 연령대를 그룹화(10대, 20대 등)하여 분석합니다.
2.  **가입 시점 시계열 분석**: 
    - `add_time`은 UTC 기준 Unix Timestamp이므로 `CONVERT_TZ(FROM_UNIXTIME(add_time), 'UTC', 'Asia/Seoul')`를 사용하여 한국 시간으로 변환 후 일별/월별 가입자 추이를 분석합니다.
3.  **지역별 유저 분포**: 
    - `register_region_id` 또는 `region_id`를 `rich_region`과 조인하여 대/중/소지역별 유저 밀집도를 파악할 수 있습니다.
