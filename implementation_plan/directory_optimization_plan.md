# 프로젝트 디렉토리 구조 최적화 계획

현재 프로젝트의 디렉토리 구조를 분석한 결과, 사용자 정의 규칙(Rule 4)을 대체로 잘 준수하고 있으나, 관리 효율성과 규칙 준수 강화를 위해 일부 보완이 필요합니다.

## User Review Required

> [!IMPORTANT]
> 루트 디렉토리에 있는 파일들을 관련 폴더로 이동시키고, 용도가 중첩되는 `/src/data_extract` 폴더를 정리할 계획입니다. 이에 대한 승인이 필요합니다.

## Proposed Changes

### 1. 루트 디렉토리 정리
루트 디렉토리는 프로젝트의 입구이므로 최소한의 설정 파일만 남기고 분석 관련 파일은 폴더로 이동합니다.

- [MODIFY] `jupyter_nb_galaxy.ipynb` -> `/scripts/python/notebooks/` (신규 폴더 생성)
- [MODIFY] `맥 각종 커맨드 정리.md` -> `/knowledge/commands/` (신규 폴더 생성)

### 2. 데이터 및 스크립트 위치 조정
규칙에 명시된 폴더 역할에 맞춰 파일을 재배치합니다.

- [MODIFY] `/src/data_extract/*.xlsx` -> `/results/data_extract/` (엑셀 결과물이므로 results로 이동)
- [DELETE] `/src/data_extract` (파일 이동 후 삭제)
- [MODIFY] `/.etc/gbike_all.sql` -> `/scripts/sql/reference/` (중요 쿼리이므로 sql 관리 폴더로 이동)

### 3. 스크립트 구조화
`scripts/python` 아래의 개별 파일들을 관련 분석 프로젝트 폴더로 이동하거나 카테고리화합니다.

- `/scripts/python/utils/` 생성: `teams_email_mcp.py`, `send_teams_test.py`, `test_db_conn.py` 이동
- `/scripts/python/extract/` 생성: `extract_to_excel.py`, `send_extract_summary.py` 이동

## Verification Plan

### Automated Tests
- 파일 이동 후 각 스크립트 내의 상대 경로(Relative Path)가 깨지지 않았는지 확인합니다.
- 특히 `extract_to_excel.py`와 같은 자동화 스크립트의 경로 설정을 체크합니다.

### Manual Verification
- `ls -R` 명령을 통해 재정리된 구조가 규칙과 일치하는지 최종 확인합니다.
