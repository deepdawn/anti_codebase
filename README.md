# Gbike Data Science Codebase

지바이크(gbike)의 공유 퍼스널 모빌리티(전동 킥보드, 전기 자전거) 서비스 데이터를 분석하고 모델링하는 데이터 사이언스 프로젝트 저장소입니다.

## 🚀 프로젝트 개요
본 프로젝트는 지바이크의 리드 데이터 사이언티스트로서 데이터의 과학적 타당성, 재현성 및 투명성을 최우선으로 하여 수행됩니다. 주요 목표는 다음과 같습니다:
- **매출 및 이용 패턴 분석**: 수익 최적화 및 사용자 행동 패턴 파악
- **운영 최적화**: 배포 구역(Deployed Zone) 수요 분석 및 자산 배치 최적화
- **이상 탐지**: 이상 사용자(Abnormal User) 식별 및 대응
- **지리 공간 데이터 처리**: 이동 경로 시각화 및 지역별 수요 분석

## 📁 디렉토리 구조
`user_global` 규칙에 따라 다음과 같은 구조를 유지합니다:
- `/base_data/primary_data`: 수정 불가능한 원본 데이터 파일
- `/base_data/secondary_data`: 전처리되거나 파생된 데이터셋 (태스크 그룹별 접두사 사용)
- `/scripts/python`: 분석 및 데이터 추출용 파이썬 스크립트
- `/scripts/sql`: 데이터베이스 쿼리 스크립트
- `/results`: 모든 분석 결과 파일 (시각화, 리포트 등)
- `/knowledge`: 도메인 지식 및 레퍼런스 문서
- `/implementation_plan`: 마일스톤 및 구현 계획서 (Markdown)

## 🛠 주요 기술 스택 및 도구
- **언어**: Python, SQL
- **분석/모델링**: Random Forest, Gradient Boosting, Regression, A/B Testing 등
- **데이터베이스**: 내부 `mysql` DB (MySQL)
- **협업**: MS Teams 연합 (분석 결과 자동 공유)
- **AI 어시스턴트**: Antigravity (Planning & Fast Mode 활용)

## 📖 도메인 지식 (gbike Terms)
- **BSS (Battery Swapping Station)**: 배터리 교환 스테이션
- **Gbike Pass**: 구독형(30일) 및 비구독형(1일) 패스 상품
- **운영 단위**: Small Area (폴리곤) → Mid Area (Camp) → Large Area (Center)
- **주요 지표**:
    - **Trips per Asset**: 자산당 이용 횟수 (Total Trips / Allocated Units)
    - **Revenue per Asset**: 자산당 매출 (Revenue / Allocated Units)
    - **Utilization Rate**: 가동률 (Deployed Units / Allocated Units)

## 🚦 데이터 분석 원칙
1. **과학적 엄밀성**: 모든 분석은 통계적 가정을 검증하고 방법론적 타당성을 제시합니다.
2. **재현성**: 모든 전처리 및 분석 과정은 스크립트로 관리됩니다.
3. **Deductive Reporting**: 분석 결과는 결론부터 제시하는 '두괄식' 방식을 따릅니다.
4. **자동화**: 데이터 추출 및 리포팅 과정의 자동화를 지향합니다.

---
**GitHub Repository**: [https://github.com/deepdawn/codebase](https://github.com/deepdawn/codebase)
