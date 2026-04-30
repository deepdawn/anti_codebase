# deployed_zone_analysis 구현 계획서

`src/primary_data/deploy_usage.csv` 데이터를 활용하여 존(Zone)별, 기종(Model)별 수요를 정의하고, 수요가 낮은 지역에서 높은 지역으로의 재배치 제안을 생성하는 프로젝트입니다.

## User Review Required

> [!IMPORTANT]
> - **결과 저장 폴더**: `/results` 하위에 생성할 서브폴더 이름을 확정해 주세요.
> - **결측치 처리**: '출루까지 시간'이 `[NULL]`인 데이터는 아직 사용되지 않은 상태로 간주됩니다. 이를 분석에서 제외할지, 혹은 특정 임계값(예: 72시간 이상)으로 채워 분석에 포함할지 결정이 필요합니다.
> - **재배치 범위**: 재배치 제안 시 동일 '중지역' 내에서만 이동할지, 혹은 거리 기반으로 지역에 상관없이 제안할지에 대한 기준이 필요합니다.

## Proposed Changes

### 데이터 전처리 및 탐색 (EDA)
- `deploy_usage.csv` 로드 및 데이터 타입 정제 (날짜, 숫자형 등).
- '배치 구분' 별(ALIGHT/DEPLOY) 분포 및 특징 파악.
- '출루까지 시간'의 전체적인 분포 시각화.

#### [NEW] [01_data_preprocessing.py](file:///Users/galaxy/codebase/scripts/python/deployed_zone_analysis/01_data_preprocessing.py)
데이터를 정제하고, 결측치를 처리한 후 `src/secondary_data`에 저장하는 스크립트입니다.

---

### 수요 지표 분석 및 등급 부여
- 존(Zone) 및 기종(Model)별로 그룹화하여 다음 지표 계산:
    - **수요가 아주 큼**: 출루 시간 <= 1시간 비율 및 건수
    - **수요가 큼**: 출루 시간 <= 24시간 비율 및 건수
    - **수요가 적음**: 출루 시간 > 24시간 비율 혹은 미출루 상태

#### [NEW] [02_demand_analysis.py](file:///Users/galaxy/codebase/scripts/python/deployed_zone_analysis/02_demand_analysis.py)
각 존별 수요 등급을 매기고 핫스팟(High Demand)과 콜드스팟(Low Demand)을 도출합니다.

---

### 재배치 경로 최적화 제안
- 콜드스팟(과잉 공급 지역)에서 핫스팟(부족 지역)으로의 이동 경로 생성.
- 거리(위경도 기반 Haversine 공식)와 수요 등급 차이를 고려하여 우선순위 부여.

#### [NEW] [03_rebalance_recommendation.py](file:///Users/galaxy/codebase/scripts/python/deployed_zone_analysis/03_rebalance_recommendation.py)
재배치 대상 존과 수량을 제안하는 결과 파일을 생성합니다.

---

### 시각화 및 최종 보고
- 존별 수요 분포를 지도상에 시각화 (Heatmap 등).
- 최종 분석 결과 요약 및 MS Teams 공유.

#### [NEW] [04_final_report_generator.py](file:///Users/galaxy/codebase/scripts/python/deployed_zone_analysis/04_final_report_generator.py)
최종 결과물인 이미지와 리포트를 생성합니다.

## Open Questions

- **기종별 가중치**: 스쿠터와 자전거 간의 재배치 우선순위 차이가 있을까요?
- **거리 임계치**: 재배치를 제안할 최대 반경(km)을 어느 정도로 설정하면 실무적으로 유용할까요?

## Verification Plan

### Automated Tests
- 각 단계별 데이터 유실 여부 확인 (Row count 검증).
- 위경도 좌표 유효 범위 확인.

### Manual Verification
- 생성된 재배치 경로가 지리적으로 타당한지 지도를 통해 검수.
- 수요 지표 등급 할당 공식의 논리적 타당성 검토.
