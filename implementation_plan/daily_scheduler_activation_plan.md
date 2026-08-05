# 구현 계획서: 일별 데이터 추출 및 리포트 발송 스케줄러 활성화 계획

본 문서는 매일 오전 10시 및 10시 30분에 `run_daily_batch.py` 스크립트를 수행하는 macOS launchd 스케줄러(`com.gbike.daily_batch.plist`)를 로드, 활성화 및 정상 동작 여부를 검증하기 위한 구현 계획을 정의합니다.

---

## 1. 기술 대안 비교 및 선정

macOS 환경에서 스케줄러 서비스를 활성화하는 방법에 대해 아래와 같이 세 가지 대안을 비교 분석하였습니다.

### 대안 1: `launchctl bootstrap` 명령어 사용 (채택)
* **방식**: `launchctl bootstrap gui/501 /Users/galaxy/Library/LaunchAgents/com.gbike.daily_batch.plist`
* **장점**: 
  - macOS Catalina(10.15) 이상에서 권장하는 공식 최신 표준 방식입니다.
  - GUI 세션 도메인을 명확하게 지정하여 세션이 활성화될 때 정상 동작하도록 보장합니다.
* **단점**: 구형 macOS 버전에서는 지원되지 않지만, 현재 개발 PC 환경(macOS 최신 사양)에서는 가장 적합합니다.

### 대안 2: `launchctl load` 명령어 사용 (레거시)
* **방식**: `launchctl load -w /Users/galaxy/Library/LaunchAgents/com.gbike.daily_batch.plist`
* **장점**: 레거시 명령어로 직관적이며 오랜 기간 널리 사용되어 관련 레퍼런스가 많습니다.
* **단점**: macOS 공식 문서상 Deprecated 상태이며 최신 macOS 보안 정책 및 세션 관리 환경에서 예기치 않은 오류가 발생할 수 있습니다.

### 대안 3: cron (crontab)으로 전환
* **방식**: `crontab -e`에 `0,30 10 * * *` 스케줄 등록
* **장점**: OS 스케줄러 백업 관리가 단순합니다.
* **단점**: macOS의 Full Disk Access 보안 정책(TCC)으로 인해 cron 프로세스의 권한 획득이 번거롭고, PC가 Sleep 모드 상태에서 깨어났을 때 누락된 이벤트를 복구하여 즉시 실행해 주는 기능이 부족합니다.

**결정**: 가장 안전하고 권장되는 **대안 1 (`launchctl bootstrap`)** 방식을 채택하여 활성화합니다.

---

## 2. 세부 활성화 및 검증 절차 (Milestones)

### M1: 기존 launchd 로드 상태 확인 및 정리
1. 기존에 잘못 로드되어 있을 수 있는 서비스가 있다면 언로드(unload / bootout)를 먼저 수행합니다.
   - 명령어: `launchctl bootout gui/501/com.gbike.daily_batch` 또는 `launchctl unload /Users/galaxy/Library/LaunchAgents/com.gbike.daily_batch.plist` (에러 무시)

### M2: launchd 서비스 활성화 (bootstrap)
1. 신규 plist 구성을 GUI 세션에 등록하고 활성화합니다.
   - 명령어: `launchctl bootstrap gui/501 /Users/galaxy/Library/LaunchAgents/com.gbike.daily_batch.plist`
2. 정상 등록 여부 확인: `launchctl print gui/501/com.gbike.daily_batch` 또는 `launchctl list | grep gbike`

### M3: 수동 강제 실행 테스트 및 로그 검증
1. launchd 서비스를 강제 실행(kickstart)하여 래퍼 스크립트(`run_daily_batch.py`)가 정상 구동되는지 검증합니다.
   - 명령어: `launchctl kickstart -k gui/501/com.gbike.daily_batch`
2. 생성되는 로그 파일들을 실시간 모니터링하여 예외 처리가 작동하는지 확인합니다.
   - `daily_batch.log`: 스크립트 실행 로그
   - `launchd_stdout.log` & `launchd_stderr.log`: launchd 표준 입출력 로그
   - `.run_status.json`: 오늘 날짜 성공 상태 기록 파일

### M4: 예외 처리 동작성 확인 (Dry-run 테스트)
1. 오늘 성공 로그가 기록된 상태에서 한 번 더 실행하여 10시 30분 실행 시 동작이 정상적으로 건너뛰어지는지 확인합니다.
