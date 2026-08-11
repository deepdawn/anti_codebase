# 지역별/일자별 수요 예측 및 적정 할당대수 산출 모델

제공해주신 운영 데이터(배치존, 출루수, 미사용 시간 등) 및 기상 데이터를 종합적으로 활용하여 머신러닝 기반의 수요 예측 모델을 개발하고, 목표 매출 달성을 위한 매일의 **'적정 할당대수'**를 산출하는 프로젝트입니다.

## ⚠️ User Review Required

이전 리뷰를 바탕으로 1개(머신러닝 기반)의 최적화 대안으로 계획을 구체화하고, 말씀해주신 스크립트 및 피처들을 데이터 파이프라인에 모두 반영했습니다. 내용이 요구사항과 부합하는지 확인을 부탁드립니다.

## ❓ Open Questions

> [!IMPORTANT]
> 1. 기상 예측 데이터를 받아오기 위한 외부 API(예: 기상청 단기예보 API 등) 연동은 추후 어떤 API를 사용할지 결정된 바가 있으신가요?
> 2. 모델 피처로 사용될 **월별 목표 매출 데이터**는 현재 DB에 적재되어 있나요, 아니면 별도의 파일(Google Sheet, CSV 등) 형태로 가져와야 하나요?

---

## Proposed Changes

모델 개발은 1) 데이터 추출 및 피처 엔지니어링, 2) 수요 예측 모델링, 3) 최적 할당대수 도출의 3단계로 구성됩니다.

### 1. 데이터 파이프라인 구성 (Data Extraction & Feature Engineering)
기존에 존재하는 사내 스크립트들을 활용하여 과거 운영/기상 데이터를 추출하고, 모델 학습을 위한 종합 피처 테이블(Feature Table)로 조인합니다.

#### [NEW] `/scripts/python/extract/extract_allocation_features.py`
다음 데이터들을 불러오고 병합하여 모델 학습용 피처를 구성합니다.
- **매출 및 운영 지표:** `extract_rich_daily_statistics.py` (할당대수, 운행대수, 기기당 운행수, 매출)
- **가동률 파생변수:** (운행대수 / 할당대수) 계산
- **과거 기상 피처:** `extract_smartops_weather_data.py` (강수량, 날씨 등)
- **배치존 및 출루수 피처:** `extract_rich_deploy_zone_usages.py` (배치존 당 배치 수, 배치된 기기 운행수)
- **기기 운행 소요시간:** `extract_rich_deploy_used_time.py` (배치 후 운행까지 걸린 시간)
- **미사용 기기 지표:** `extract_vehicle_statistics.py` (일평균 n시간 미사용 기기 데이터)
- **목표 매출:** 월별 목표 매출 데이터 병합 (추후 데이터 소스 확인 후 반영)

#### [NEW] `/scripts/python/extract/extract_weather_forecast.py` (향후 개발 예정)
- 향후 예측 시점에 사용할 미래 날씨 데이터를 확보하기 위해 외부 API를 연동하여 기상 예보를 수집하는 스크립트입니다.

### 2. 머신러닝 기반 수요 예측 모델링 (Demand Forecasting Model)
말씀하신 대로 머신러닝 기반의 최적화 접근을 채택합니다.

#### [NEW] `/scripts/python/models/revenue_forecast/train_demand_model.py`
- **타겟 변수 (Y):** 일자별 수요(총 운행 수 및 기기당 운행 수) 및 예상 매출
- **주요 피처 (X):** 강수량, 날씨, 월별 목표 매출, 가동률, 출루수, 미사용 기기 지표 등 (공휴일/이벤트 데이터는 추후 확장 시 추가)
- **알고리즘:** 시계열 및 비선형 패턴 예측에 강한 **XGBoost**를 주력 모델로 사용합니다.
- **출력:** 학습이 완료된 모델 파일 저장 및 교차 검증을 통한 오차율(MAPE/RMSE) 성능 지표 출력.

### 3. 목표 매출 기반 적정대수 산출 (Allocation Optimization)
학습된 모델이 그리는 예측 수요 곡선을 바탕으로, **'월별 목표 매출'**이라는 비즈니스 타겟을 달성하기 위해 지역마다 며칠에 몇 대를 배치해야 하는지 최적해를 도출합니다.

#### [NEW] `/scripts/python/models/revenue_forecast/predict_optimal_allocation.py`
- 특정 일자에 예측된 기상 조건과 가동률 하에서, 목표 매출을 낼 수 있는 최소 할당대수를 역산합니다.
- 도출된 적정대수와 '현재 실제 할당대수'의 차이를 계산하여 지역별로 증차/감차가 필요한 수량을 엑셀 리포트 형태로 `/results` 디렉토리에 저장합니다.

---

## Verification Plan

### Automated Tests
- 분할된 검증(Validation) 세트(예: 최근 1개월 데이터)를 활용해 모델의 수요 및 매출 예측 정확도(MAPE)를 테스트합니다.
- 피처 병합 로직(`extract_allocation_features.py`) 실행 시 키 값이 누락되거나 예상치 못한 결측치(Null)가 생기지 않는지 무결성을 점검합니다.

### Manual Verification
- 산출된 지역별 적정 할당대수 예측 결과 파일(.xlsx)을 현업 실무진이 검토하여, 실제 지역 환경과 비즈니스 감각에 부합하는 적정 대수인지 피드백을 수렴합니다.
