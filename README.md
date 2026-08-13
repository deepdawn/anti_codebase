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

- `/scripts/orchestrator`: 쉘 기반 마스터 파이프라인 및 스케줄링 오케스트레이터
- `/scripts/python/engineering`: 데이터 파이프라인 엔지니어링 스크립트 모음
  - `/extract`: 원천 데이터 추출
  - `/processing`: 추출된 데이터의 2차 가공 및 세그먼트 생성
  - `/tableau`: 태블로 대시보드 자동화 연동
  - `/orchestrator`: 파이썬 기반 데일리 배치 오케스트레이터
- `/scripts/python/analysis`: 데이터 탐색 및 심층 분석용 스크립트
- `/scripts/python/models`: 머신러닝 모델 학습 및 예측 스크립트
- `/scripts/python/utils`: 재사용 가능한 공통 유틸리티 함수 및 설정 파일
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

## 📈 주요 분석 프로젝트 목록

- **부산 3캠프 실적 비교 분석 (`busan3camp_25_26_statistics`, `busan3camp_yoy_extract`)**: 2025년과 2026년 부산 3캠프 관할 소권역별 자산당 매출 및 회전수(Trips per Asset) 변화 분석
- **전사 연도별 캠프 매출 분석 (`yoy_camp_revenue_analysis_v1`)**: 캠프 단위의 연도별 매출 트렌드 파악 및 비교
- **평택 심야 시간대 분석 (`pyeongtaek_latenight_analysis`)**: 평택 지역의 심야 시간대 퍼스널 모빌리티 이용 패턴 분석
- **강릉 트립 데이터 분석 (`gangneung_trip_data_v1`)**: 강릉 지역 사용자 이동 경로 및 트립 데이터 분석
- **배포 구역 수요 분석 (`deployed_zone_analysis_v1`)**: 자산 배포 구역(Deployed Zone) 기준 수요 및 가동률 최적화 모델링
- **킥보드 실적 데이터 추출 (`analysis_kickboard_down`)**: 전동 킥보드 하락세 분석 및 실적 데이터 추출
- **지역별 기초 분석 (`jeju_extract`, `pohang_extract` 등)**: 제주, 포항 등 주요 거점 지역의 트립 데이터 추출 및 현황 파악

---

**GitHub Repository**: [https://github.com/deepdawn/anti_codebase](https://github.com/deepdawn/anti_codebase)
