# 구현 계획서: launchd 기반 일별 데이터 추출 및 리포트 자동 발송 스케줄러 구성 (v2)

**결론 및 요약 (Head-First)**:
본 프로젝트는 매일 오전 10시(1차) 및 10시 30분(2차, 예비)에 데이터 추출(`extract_rich_orders_daily.py`)과 리포트 발송(`send_weekly_report.py`) 스크립트를 순차 실행하는 **macOS launchd 기반 스케줄러**를 구축합니다. 10시 30분 실행 시 중복 실행을 막기 위해 **성공 마커 파일 기반 중복 방지 로직**을 적용하며, PC가 잠자기(Sleep) 모드였다가 깨어났을 때도 안정적으로 대응할 수 있도록 macOS 표준 LaunchAgent 방식을 채택합니다.

---

## 1. 기술 대안 비교 및 선정

macOS 환경에서 스케줄러를 등록하고 PC 유휴(Idle/Sleep) 상태에 대응하기 위한 3가지 대안을 검토했습니다.

| 항목 | 대안 1: launchd (LaunchAgent) + 래퍼 파이썬 스크립트 (채택) | 대안 2: cron (crontab) + 래퍼 파이썬 스크립트 | 대안 3: Python 상시 실행 데몬 (APScheduler) + launchd keepalive |
| :--- | :--- | :--- | :--- |
| **개념** | macOS 표준 LaunchAgent 서비스(`com.gbike.daily_batch.plist`)에 10:00, 10:30 시간 스케줄을 등록하고 실행 제어 | `crontab`에 10:00, 10:30 실행을 등록하고 래퍼 스크립트로 제어 | Python 스케줄러 모듈을 이용한 백그라운드 프로세스 상시 구동 |
| **유휴(Sleep) 대응** | **우수**: 10:00에 PC가 Sleep 상태였다가 깨어나면 launchd가 밀린 이벤트를 인지하고 깨어난 직후 즉시 실행 가능함 | **불가**: 10:00에 PC가 Sleep 상태이면 10:00 실행은 건너뜀. 10:30에 깨어있어야만 비로소 실행됨 | **불가**: PC가 Sleep 상태이면 Python 프로세스 자체가 일시정지되므로 깨어나기 전까지 이벤트 감지 불가 |
| **보안/권한** | LaunchAgent는 사용자 세션 내에서 구동되므로 Full Disk Access 등 권한 문제가 적음 | macOS TCC 정책으로 인해 cron 프로세스에 수동으로 Full Disk Access 권한을 주는 복잡한 절차 필요 | 백그라운드 상시 상주 프로세스로 인해 시스템 자원 관리 및 비정상 종료 시 복구 오버헤드 존재 |
| **중복 실행 방지** | 마커 파일 검사 로직으로 10:30 실행 시 중복 실행 완벽 차단 | 동일하게 마커 파일 검사 로직 적용 가능 | 메모리 상에서 실행 여부를 체크하므로 별도 로직 필요 |

**최종 결정**: macOS 환경에서 가장 안정적이고 유휴(Sleep) 대응에 최적화된 **대안 1 (launchd + 중복 실행 방지 래퍼 파이썬 스크립트)** 방식을 채택합니다.

---

## 2. 세부 구현 계획

### 2.1 래퍼 파이썬 스크립트 (`/Users/galaxy/anti_codebase/scripts/python/extract/run_daily_batch.py`)
이 스크립트는 launchd에 의해 하루에 두 번(10:00, 10:30) 호출되며 다음 로직을 처리합니다:
1. **오늘 날짜 확인**: `YYYY-MM-DD` 형식의 당일 날짜를 획득합니다.
2. **성공 마커 검사**: 성공 마커 파일(`/Users/galaxy/anti_codebase/scripts/python/extract/.daily_success_YYYYMMDD`)이 존재하는지 체크합니다.
   - 존재할 경우: "오늘 이미 성공적으로 배치 작업이 완료되었습니다."라는 로그를 남기고 즉시 종료(exit 0)합니다.
3. **순차 실행**:
   - 1단계: `/Users/galaxy/anti_codebase/scripts/python/extract/extract_rich_orders_daily.py` 실행
   - 2단계: `/Users/galaxy/anti_codebase/scripts/python/report_daily_ststs_v1/send_weekly_report.py` 실행
   - 각 스크립트는 `.venv` 가상환경의 파이썬 인터프리터로 실행합니다.
4. **성공 마커 생성 및 로그**: 두 단계가 모두 에러 없이 끝나면 성공 마커 파일을 생성하고 로그를 작성합니다.
5. **예외 처리 및 로깅**: 각 단계 실행 중 에러 발생 시 로그 파일(`/Users/galaxy/anti_codebase/scripts/python/extract/cron_run.log`)에 상세 에러와 traceback을 기록하고, 이전 날짜의 임시 마커 파일들을 정리(cleanup)합니다.

### 2.2 launchd 설정 파일 (`/Users/galaxy/Library/LaunchAgents/com.gbike.daily_batch.plist`)
매일 오전 10시 0분과 10시 30분에 실행하도록 구성합니다.
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gbike.daily_batch</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/galaxy/anti_codebase/.venv/bin/python</string>
        <string>/Users/galaxy/anti_codebase/scripts/python/extract/run_daily_batch.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>10</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>10</integer>
            <key>Minute</key>
            <integer>30</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/Users/galaxy/anti_codebase/scripts/python/extract/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/galaxy/anti_codebase/scripts/python/extract/launchd_stderr.log</string>
</dict>
</plist>
```

---

## 3. 마일스톤 및 검증 계획

| 마일스톤 | 작업 내용 | 대상 파일/경로 |
| :--- | :--- | :--- |
| **M1: 래퍼 스크립트 구현** | 중복 실행 방지 및 순차 실행 로직을 담은 파이썬 스크립트 작성 | `scripts/python/extract/run_daily_batch.py` |
| **M2: launchd plist 작성 및 배치** | launchd 설정 파일 작성 후 LaunchAgents 디렉토리로 이동 | `/Users/galaxy/Library/LaunchAgents/com.gbike.daily_batch.plist` |
| **M3: launchd 등록 및 활성화** | `launchctl bootstrap`을 활용하여 사용자 GUI 세션에 서비스 등록 | N/A |
| **M4: 동작 테스트 및 로그 검증** | `launchctl kickstart` 명령으로 수동 강제 실행 후 로그 생성 및 마커 파일 확인 | N/A |
| **M5: 중복 실행 방지(Dry-run) 검증** | 마커 파일이 존재하는 상태에서 2차 강제 실행 시 즉시 스킵되는지 확인 | N/A |
