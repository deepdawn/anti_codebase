# 구현 계획서: crontab 기반 일별 데이터 추출 및 리포트 자동 발송 스케줄러 구성

본 문서에서는 매일 오전 10시에 `extract_rich_orders_daily.py`를 먼저 실행하고, 성공 시 `send_weekly_report.py`를 순차적으로 실행하도록 crontab에 스케줄러를 등록하는 계획을 기술합니다.

---

## 1. 대안 비교 및 기술 선정

### 대안 1: 전용 래퍼 쉘 스크립트 (`run_daily.sh`) 사용 (채택)
* **설명**: 크론탭에는 단일 쉘 스크립트(`/Users/galaxy/anti_codebase/scripts/run_daily.sh`)를 등록합니다. 쉘 스크립트 내부에서 가상환경 파이썬 및 환경변수(PATH)를 설정한 뒤 두 파이썬 스크립트를 `&&` 연산자로 순차 실행합니다.
* **장점**:
  - macOS `cron` 실행 환경의 고유한 한계(제한적인 환경 변수)를 쉘 스크립트 내부에서 명시적 선언(PATH 설정 등)으로 극복할 수 있어 신뢰성이 높습니다.
  - 크론탭 설정이 단일 라인으로 매우 간단해집니다.
* **단점**: 쉘 스크립트 파일 관리가 추가로 필요합니다.

### 대안 2: crontab에 직접 파이썬 명령어 체이닝 등록
* **설명**: `crontab` 설정에 직접 `python path/to/script1.py && python path/to/script2.py` 형태로 등록합니다.
* **장점**: 별도의 파일 생성 없이 크론탭 설정만으로 완료됩니다.
* **단점**:
  - 크론 실행 시 환경변수(PATH, LANG 등)가 누락되어 모듈을 임포트하지 못하거나 한글 인코딩 에러가 발생할 가능성이 큽니다.
  - 명령어 라인이 길어져 유지보수가 어렵습니다.

**결정**: **대안 1 (전용 래퍼 쉘 스크립트 `run_daily.sh` 사용)** 방식을 채택합니다.

---

## 2. 세부 구현 계획

### 2.1 래퍼 쉘 스크립트 (`/Users/galaxy/anti_codebase/scripts/run_daily.sh`)
이 스크립트는 다음 작업을 수행합니다:
1. 환경변수 `PATH` 및 파이썬 가상환경 경로를 명시적으로 지정합니다.
2. `extract_rich_orders_daily.py`를 실행합니다.
3. 2번이 성공할 경우, `send_weekly_report.py`를 실행합니다.
4. 전체 실행 결과와 표준 출력/에러를 로그 파일(`/Users/galaxy/anti_codebase/scripts/python/extract/cron_run.log`)에 기록합니다.

### 2.2 crontab 등록 내용
* **실행 시각**: 매일 오전 10시 (`0 10 * * *`)
* **등록 명령어**:
  ```bash
  0 10 * * * /bin/bash /Users/galaxy/anti_codebase/scripts/run_daily.sh
  ```

---

## 3. 구현 일정 및 마일스톤

| 마일스톤 | 작업 내용 | 파일 경로 |
| :--- | :--- | :--- |
| **M1: 래퍼 쉘 스크립트 작성** | 환경 변수 설정 및 파이썬 스크립트 순차 실행 쉘 스크립트 생성 | `scripts/run_daily.sh` |
| **M2: 수동 검증** | `run_daily.sh` 단독 실행을 통한 모듈 참조 및 순차 실행 오류 여부 검증 | N/A |
| **M3: crontab 등록** | `crontab -l` 로 기존 설정 백업 후 `crontab`에 스케줄 추가 | N/A |
| **M4: 최종 확인** | crontab 리스트 확인 | N/A |
