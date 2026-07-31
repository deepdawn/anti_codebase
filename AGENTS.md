# Repository Guidelines

## 프로젝트 구조와 모듈 구성

- `scripts/python/extract/`: MySQL 운영 데이터를 일자별 Parquet로 추출하는 배치와 오케스트레이터입니다.
- `scripts/python/utils/`: Parquet 로더, DB 연결, Google Chat 전송, 공간 데이터 변환 등 공통 기능입니다. 반복 로직은 이곳의 유틸리티를 우선 재사용합니다.
- `scripts/python/report_daily_*/`: Google Chat용 일일·주간 성과 및 배치 리포트입니다.
- `scripts/python/analysis/<주제>/`: 지역·캠페인·사용자 분석 스크립트와 산출물입니다.
- `scripts/python/models/revenue_forecast/`: Prophet과 XGBoost 기반 매출·운행 예측입니다.
- `scripts/sql/`: 추출 및 분석용 SQL입니다. 원본 데이터는 저장소 밖 Google Drive의 Parquet 경로에 있습니다.

## 실행과 개발 명령

가상환경을 활성화한 뒤 프로젝트 루트에서 실행합니다.

```bash
source .venv/bin/activate
bash scripts/run_daily.sh          # 주문·사용자·세그먼트·주간 리포트
bash scripts/run_deploy.sh         # 배치존 추출 및 배치 리포트
bash scripts/run_maco_googlesheet.sh # 운영 Google Sheet 갱신
python scripts/python/extract/extract_rich_orders_daily.py 2026-07-01 2026-07-01
```

현재 의존성 선언 파일과 자동화된 테스트 스위트는 없습니다. 변경 전에는 관련 모듈을 작은 기간으로 실행하고, 로그 파일과 생성된 Parquet·리포트를 확인합니다.

## 코딩 규칙

Python은 4칸 들여쓰기, `snake_case` 함수·변수명, `PascalCase` 클래스명을 사용합니다. 파일명은 역할을 드러내는 `extract_*.py`, `analyze_*.py`, `send_*.py` 패턴을 따릅니다. DB·파일·API 호출은 `try/except`로 감싸고, 실패 원인과 대상 날짜를 로그로 남긴 뒤 적절한 종료 코드를 반환합니다. 경로·수수료·채널 규칙처럼 재사용되는 값과 로직은 상수 또는 `utils/` 함수로 분리합니다.

## 데이터·보안

운영 데이터, Google Drive·Chat·Sheets, MySQL은 실제 외부 시스템에 연결됩니다. 대량 기간 실행이나 `--overwrite` 사용 전 대상 날짜·경로를 확인합니다. 비밀번호, 토큰, 서비스 계정 JSON, 채팅 공간 ID를 코드·로그·커밋에 추가하지 마세요. 새 설정은 환경변수 또는 로컬 비추적 설정 파일로 주입합니다.

## 변경 제출 기준

이 디렉터리는 현재 Git 저장소가 아니므로 기존 커밋 규칙은 확인할 수 없습니다. Git으로 관리할 경우, 한 목적만 담은 명령형 커밋 메시지(예: `feat: add daily revenue validation`)를 사용합니다. PR에는 변경 목적, 영향받는 배치·데이터 경로, 검증 명령 및 결과, 외부 시스템 영향 여부를 명시합니다.
