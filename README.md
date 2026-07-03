# jobskill-mlops project

[![Python CI](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml)
[![Smoke Check](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml)

채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow와 MLflow를 이용해 데이터 수집, 원천 적재, 전처리, 데이터 품질 검증, 모델 학습, 성능 검증, 모델 승격, 일괄 예측, API 추론, 리포트 생성까지 연결하는 경량 MLOps 파이프라인 프로젝트입니다.

이 프로젝트는 단순 모델 학습이 아니라, 학습 전 데이터 품질 검증, 모델 성능 gate, best model promotion, 예측 결과 lineage 저장, FastAPI serving model 자동 reload, source별 데이터 품질 리포트, 데이터 소스 모드 분리, 외부 수집 실패 fallback, API 요청/응답 로그, prediction quality gate, Streamlit 기반 운영 대시보드, Makefile 기반 실행 명령어 표준화, smoke check 자동 검증, GitHub Actions 기반 테스트/코드 품질/서비스 기동 검증까지 포함한 end-to-end MLOps 흐름을 구성하는 것을 목표로 합니다.

## 주요 업데이트 내역

```text
2026-07-03
- Makefile 기반 실행 명령어 표준화 추가
- scripts/smoke_check.sh 기반 로컬 smoke check 추가
- GitHub Actions 기반 Docker Compose smoke check workflow 추가
- Smoke workflow에서 API 기동 전 sample 기반 최소 파이프라인 실행 및 promoted model 생성 검증 추가
- README 상단 GitHub Actions badge 추가
- CHANGELOG.md 기반 MVP release 기록 추가
- GitHub Actions 기반 pytest 자동 실행 workflow 추가
- Ruff 기반 코드 품질 검사 CI 추가
- requirements-dev.txt / pyproject.toml 추가
- reports/latest_pipeline_report.md와 docs/sample_pipeline_report.md 역할 분리
- 포트폴리오용 sample pipeline report 문서화
- Streamlit 기반 MLOps Dashboard 추가
- Docker Compose dashboard 서비스 추가
- Dashboard 화면 캡처 docs/images/dashboard.png 추가
- README에 Dashboard 실행 방법 / 접속 정보 / 스크린샷 반영
Makefile 추가 및 주요 명령어 표준화
scripts/smoke_check.sh 추가
로컬 Docker Compose smoke check 검증
GitHub Actions smoke.yml 추가
CI smoke workflow에서 sample 기반 최소 파이프라인 실행 후 API / Dashboard smoke check 수행
README badge 추가
CHANGELOG.md 기반 MVP release 정리
.gitattributes 기반 line ending 관리 추가
- 다음 개선 예정에서 완료 항목 정리

2026-07-02
- DATA_SOURCE_MODE 기반 데이터 소스 실행 모드 추가
- sample_only / crawler_only / mixed 모드 분리
- DAG 시작 단계에 prepare_raw_sources task 추가
- Remote OK crawler retry / fallback 처리 추가
- crawler_only 학습 시 rare class 자동 제외 처리 추가
- FastAPI 요청/응답/실패/latency 로그 테이블 분리
- model_predictions에 prediction_source 추가
- API prediction과 BATCH prediction 저장 경로 분리
- batch inference는 BATCH 예측만 삭제 후 재생성하도록 수정
- batch inference 이후 prediction quality gate 추가
- prediction quality 결과를 pipeline_check_results에 저장
- API quality / prediction quality 리포트 항목 추가
- FK 제약조건 및 SQL 문법 오류 트러블슈팅 정리
```


## 프로젝트 목표

이 프로젝트는 채용공고 데이터를 사용해 아래 흐름을 구성합니다.

```text
데이터 소스 모드 결정(sample_only / crawler_only / mixed)
→ 샘플 채용공고 데이터 생성 또는 skip
→ 외부 채용공고 수집 또는 skip
→ 외부 수집 실패 시 retry / fallback 처리
→ PostgreSQL raw 테이블 적재
→ 텍스트 정제 / 직무 라벨링 / 기술스택 추출
→ PostgreSQL cleaned / skills 테이블 저장
→ 학습 데이터 품질 체크
→ 검증 결과 저장
→ rare class 필터링 후 모델 학습
→ TF-IDF + Logistic Regression 모델 학습
→ MLflow 실험 기록
→ 모델 artifact 저장
→ 모델 성능 기준 체크
→ 성능 검증 결과 저장
→ best model promotion
→ model_registry 저장
→ promoted model 기반 batch inference
→ BATCH prediction 저장
→ batch prediction quality gate
→ FastAPI 단건 예측
→ API prediction 저장
→ FastAPI 요청/응답 로그 저장
→ prediction lineage 저장
→ source별 / prediction quality / API quality 리포트 생성
→ Streamlit Dashboard로 모델/데이터/API 품질 지표 시각화
→ FastAPI serving model 자동 reload
→ Airflow DAG로 전체 파이프라인 실행
```

## Architecture

```mermaid
flowchart LR
    MODE[DATA_SOURCE_MODE] --> PREP[prepare_raw_sources]

    PREP --> A[Sample Job CSV]
    PREP --> CR[Remote OK Crawler]

    A --> B[raw_job_posts]
    EXT[Remote OK Job Feed] --> CR
    CR --> RF[Retry / Fallback]
    RF --> B

    B --> C[Preprocessing]
    C --> D[cleaned_job_posts]
    C --> E[job_post_skills]

    D --> Q1[Data Quality Check]
    Q1 --> QR[pipeline_check_results]

    Q1 --> F[Train Model]
    F --> G[MLflow Tracking]
    F --> H[models/job_classifier.pkl]

    G --> Q2[Model Performance Check]
    Q2 --> QR

    Q2 --> P[Promote Model]
    P --> MR[model_registry]
    P --> BM[models/best/job_classifier.pkl]

    MR --> I[Batch Inference]
    BM --> I
    I --> J[model_predictions]
    I --> Q3[Prediction Quality Check]
    Q3 --> QR

    MR --> K[FastAPI /predict]
    BM --> K
    K --> J
    K --> AL[api_prediction_logs]

    QR --> R[Pipeline Report]
    MR --> R
    J --> R
    AL --> R
    D --> R

    B --> DASH[Streamlit Dashboard]
    D --> DASH
    J --> DASH
    AL --> DASH
    QR --> DASH
    MR --> DASH

    subgraph Orchestration
        L[Airflow DAG / PythonOperator]
    end

    subgraph CI
        CI1[GitHub Actions]
        CI2[pytest]
        CI3[Ruff]
        CI4[Docker Compose Smoke Check]
        CI1 --> CI2
        CI1 --> CI3
        CI1 --> CI4
    end

    L --> PREP
    L --> A
    L --> CR
    L --> C
    L --> Q1
    L --> F
    L --> Q2
    L --> P
    L --> I
    L --> Q3
    L --> R
```

## 현재 구성

```text
Docker Compose
├── PostgreSQL
│   ├── jobskill DB  : 프로젝트 데이터 / 예측 / 검증 / 모델 registry 저장
│   ├── airflow DB   : Airflow 메타데이터 저장
│   └── mlflow DB    : MLflow 실험/런 메타데이터 저장
├── Airflow 3.x
│   ├── airflow-apiserver
│   ├── airflow-scheduler
│   ├── airflow-dag-processor
│   └── airflow-triggerer
├── MLflow
│   ├── backend store  : PostgreSQL mlflow DB
│   └── artifact store : ./mlartifacts
├── FastAPI
│   ├── /predict
│   ├── /model
│   └── /reload-model
├── Streamlit Dashboard
│   ├── latest promoted model 조회
│   ├── source별 데이터 품질 조회
│   ├── batch prediction quality 조회
│   ├── pipeline check 결과 조회
│   ├── FastAPI prediction logs 조회
│   └── recent predictions 조회
└── Local / CI Validation
    ├── Makefile 명령어 표준화
    ├── scripts/smoke_check.sh
    ├── GitHub Actions Python CI
    └── GitHub Actions Smoke Check
```

## 기술 스택

```text
Language        : Python
Workflow        : Apache Airflow 3.x
Database        : PostgreSQL
ML Lifecycle    : MLflow
Preprocessing   : pandas
Model           : scikit-learn
API             : FastAPI
Dashboard       : Streamlit, Plotly
Crawler         : requests, BeautifulSoup
Test            : pytest
Code Quality    : Ruff
CI              : GitHub Actions
Command Runner  : Makefile, Shell Script
Container       : Docker Compose
```

## 디렉터리 구조

```text
.
├── README.md
├── CHANGELOG.md
├── Makefile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── pytest.ini
├── .env.example
├── .gitattributes
├── .gitignore
├── .github/
│   └── workflows/
│       ├── pytest.yml
│       └── smoke.yml
├── dags/
│   └── jobskill_pipeline_dag.py
├── docker/
│   ├── airflow/
│   │   └── Dockerfile
│   ├── api/
│   │   └── Dockerfile
│   └── postgres/
│       └── init/
│           ├── 01-create-airflow-db.sql
│           └── 02-create-mlflow-db.sql
├── sql/
│   ├── create_tables.sql
│   └── report_queries.sql
├── scripts/
│   ├── generate_sample_jobs.py
│   └── smoke_check.sh
├── src/
│   ├── common/
│   │   ├── db.py
│   │   ├── data_source_mode.py
│   │   ├── model_registry.py
│   │   └── prediction_quality.py
│   ├── crawling/
│   │   └── crawl_remoteok_jobs.py
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── app.py
│   ├── ingestion/
│   │   ├── prepare_raw_sources.py
│   │   └── load_raw_jobs.py
│   ├── preprocessing/
│   │   ├── clean_text.py
│   │   ├── extract_skills.py
│   │   ├── label_jobs.py
│   │   └── preprocess_db.py
│   ├── quality/
│   │   ├── check_logger.py
│   │   ├── check_training_data.py
│   │   ├── check_model_performance.py
│   │   └── check_prediction_quality.py
│   ├── reporting/
│   │   └── generate_pipeline_report.py
│   ├── training/
│   │   ├── train_baseline.py
│   │   └── promote_model.py
│   └── inference/
│       ├── api.py
│       └── batch_inference.py
├── tests/
│   └── unit/
├── data/
│   ├── raw/
│   └── processed/
├── models/
│   └── best/
├── reports/
│   └── latest_pipeline_report.md
├── mlartifacts/
├── airflow_logs/
├── docs/
│   ├── sample_pipeline_report.md
│   └── images/
│       ├── Airflow DAG success.png
│       ├── dashboard.png
│       ├── fastapi.png
│       ├── mlflow.png
│       └── postgresql.png
└── notebooks/
```

> `data/`, `models/`, `mlartifacts/`, `airflow_logs/`, `.env`, `simple_auth_manager_passwords.json` 등은 로컬 실행 중 생성되는 산출물이므로 Git에는 포함하지 않습니다.  
> 포트폴리오 확인용 스크린샷은 `docs/images/`에 저장하고 README에서 상대경로로 참조합니다.

## 주요 컴포넌트

### 1. 데이터 생성

`scripts/generate_sample_jobs.py`

직무별 템플릿을 기반으로 샘플 채용공고 데이터를 생성합니다.

생성 대상 직무:

```text
Data Engineer
Backend Engineer
ML Engineer
DevOps Engineer
Data Analyst
```

생성 파일:

```text
data/raw/sample_jobs.csv
```

### 1-1. 데이터 소스 모드

`src/common/data_source_mode.py`  
`src/ingestion/prepare_raw_sources.py`

파이프라인 실행 시 사용할 데이터 소스를 환경변수로 제어합니다.

```env
DATA_SOURCE_MODE=mixed
```

지원 모드:

```text
sample_only  : 샘플 CSV 데이터만 사용
crawler_only : Remote OK 수집 데이터만 사용
mixed        : 샘플 데이터와 Remote OK 수집 데이터를 함께 사용
```

DAG 시작 단계에서 `prepare_raw_sources` task가 실행되어 선택한 모드에 맞게 raw/source 데이터를 정리합니다.

```text
sample_only
→ sample 외 source raw 제거
→ sample 생성/적재 task 실행
→ crawler task skip

crawler_only
→ sample raw 제거
→ sample 생성/적재 task skip
→ crawler task 실행

mixed
→ sample과 crawler 데이터를 함께 유지
→ sample 생성/적재 task 실행
→ crawler task 실행
```

### 2. 외부 채용공고 수집

`src/crawling/crawl_remoteok_jobs.py`

Remote OK의 public job feed를 사용해 실제 원격 채용공고 데이터를 수집하고 `raw_job_posts`에 upsert합니다.

저장 정보:

```text
source
source_job_id
external_id
source_url
title
company
location
description
tags
crawled_at
```

수집 단계에서는 비개발/비데이터 직무가 학습 데이터에 과도하게 유입되지 않도록 필터링을 수행합니다.

```text
수집 대상:
Data Engineer
Backend Engineer
ML Engineer
DevOps Engineer
Data Analyst

필터링 기준:
title, description, tags 기반 직무 라벨 추론
Unknown으로 분류되는 공고는 raw 적재 전 제외
```


### 2-1. 외부 수집 retry / fallback

Remote OK API 호출 실패에 대비해 crawler에 retry와 fallback 처리를 추가했습니다.

환경변수:

```env
REMOTEOK_MAX_RETRIES=3
REMOTEOK_RETRY_SLEEP_SECONDS=3
REMOTEOK_REQUEST_TIMEOUT_SECONDS=30
REMOTEOK_FALLBACK_TO_EXISTING_RAW=true
REMOTEOK_MIN_FETCHED_JOBS=1
```

동작 방식:

```text
1. Remote OK API 호출
2. 실패 시 지정 횟수만큼 retry
3. retry 이후에도 실패하면 기존 raw_job_posts의 remoteok 데이터 확인
4. 기존 데이터가 있으면 fallback으로 기존 데이터를 사용해 파이프라인 계속 진행
5. 기존 데이터도 없으면 crawler task 실패
```

이를 통해 외부 API 일시 장애가 전체 DAG 실패로 바로 이어지지 않도록 개선했습니다.

### 3. Raw 데이터 적재

`src/ingestion/load_raw_jobs.py`

생성된 CSV 데이터를 PostgreSQL의 `raw_job_posts` 테이블에 적재합니다.

샘플 데이터와 외부 수집 데이터는 `source`로 구분합니다.

```text
source = sample
source = remoteok
```

### 4. 전처리

`src/preprocessing/preprocess_db.py`

`raw_job_posts` 데이터를 읽어 아래 처리를 수행합니다.

```text
텍스트 정제
직무 라벨링
기술스택 추출
전처리 결과 저장
```

Remote OK 데이터는 중요한 힌트가 `tags`에 포함되는 경우가 많기 때문에, 전처리와 라벨링에는 `title`, `description`, `tags`를 함께 사용합니다.

```text
text_for_model = cleaned_title + cleaned_description + cleaned_tags
job_category  = label_job(title, description + tags)
```

저장 테이블:

```text
cleaned_job_posts
job_post_skills
```

전처리 재실행 시 기존 전처리/예측 결과를 초기화합니다.

```sql
TRUNCATE TABLE
    model_predictions,
    job_post_skills,
    cleaned_job_posts
RESTART IDENTITY
CASCADE;
```

`model_predictions`와 `job_post_skills`가 `cleaned_job_posts`를 참조하므로, 단순히 `cleaned_job_posts`만 먼저 삭제하면 FK 제약조건 오류가 발생할 수 있습니다.

### 5. 직무 라벨링 규칙

`src/preprocessing/label_jobs.py`

기존 단순 키워드 기반 라벨링을 직무별 weighted keyword scoring 방식으로 개선했습니다.

개선 내용:

```text
제목 키워드 가중치 반영
description / tags 기반 라벨링 보강
직무별 주요 기술 키워드 확장
영문/한글 직무 표현 동시 지원
Unknown 라벨 비율 감소
```

라벨 대상:

```text
Data Engineer
Backend Engineer
ML Engineer
DevOps Engineer
Data Analyst
Unknown
```

### 6. 데이터 품질 체크

`src/quality/check_training_data.py`

전처리 결과가 모델 학습에 적합한지 확인합니다.

검증 항목:

```text
raw_job_posts 데이터 존재 여부
cleaned_job_posts 최소 학습 데이터 수
job_post_skills 추출 결과 존재 여부
text_for_model 누락 여부
job_category 누락 여부
직무 카테고리 다양성
Unknown 라벨 비율
```

데이터 품질 기준을 통과하지 못하면 DAG를 실패시켜, 부적절한 데이터로 모델 학습이 진행되지 않도록 합니다.

### 7. 검증 결과 저장

`src/quality/check_logger.py`

데이터 품질 체크와 모델 성능 체크 결과를 PostgreSQL의 `pipeline_check_results` 테이블에 저장합니다.

저장 대상:

```text
DATA_QUALITY
MODEL_PERFORMANCE
PREDICTION_QUALITY
```

저장 컬럼:

```text
check_type
check_name
status
metric_value
threshold_value
message
dag_id
task_id
run_id
checked_at
```

이를 통해 Airflow DAG 실행 시점마다 어떤 검증 항목이 통과 또는 실패했는지 추적할 수 있습니다.

### 8. 모델 학습

`src/training/train_baseline.py`

PostgreSQL의 `cleaned_job_posts` 테이블에서 학습 데이터를 읽어 모델을 학습합니다.

모델 구성:

```text
TF-IDF Vectorizer
+ Logistic Regression
```

학습 결과:

```text
models/job_classifier.pkl
MLflow experiment/run 기록
MLflow model artifact 저장
```


`crawler_only` 모드에서는 실제 외부 데이터 분포가 치우칠 수 있으므로, stratified split이 불가능한 rare class를 학습 전에 제외합니다.

```text
MIN_SAMPLES_PER_CLASS보다 적은 라벨
→ 학습 데이터에서 제외
→ 남은 라벨 기준으로 stratified train/test split 수행
```

관련 환경변수:

```env
MIN_SAMPLES_PER_CLASS=2
TEST_SIZE=0.3
```

### 9. MLflow Tracking

MLflow는 PostgreSQL의 `mlflow` DB를 backend store로 사용합니다.

```text
MLFLOW_TRACKING_URI=postgresql+psycopg2://jobskill:jobskill@postgres:5432/mlflow
```

Artifact는 로컬 `mlartifacts/` 디렉터리에 저장됩니다.

```text
MLFLOW_ARTIFACT_ROOT=/opt/airflow/project/mlartifacts
```

MLflow UI:

```text
http://localhost:5000
```

<img src="docs/images/mlflow.png" width="900">

### 10. 모델 성능 체크

`src/quality/check_model_performance.py`

MLflow에 기록된 최신 학습 run의 metric을 조회해 모델 성능 기준을 검증합니다.

검증 항목:

```text
accuracy >= MIN_MODEL_ACCURACY
f1_weighted >= MIN_MODEL_F1_WEIGHTED
```

모델 성능이 기준보다 낮으면 DAG를 실패시켜, 낮은 품질의 모델이 promotion 또는 batch inference 단계로 넘어가지 않도록 합니다.

### 11. 모델 승격

`src/training/promote_model.py`

MLflow에 기록된 최신 학습 run의 성능을 기준으로 기존 best model과 비교합니다.

승격 조건:

```text
기존 promoted model이 없는 경우
또는 최신 모델의 f1_weighted가 기존 best model보다 높은 경우
또는 f1_weighted가 같고 accuracy가 더 높은 경우
```

승격된 모델은 아래 경로에 저장됩니다.

```text
models/best/job_classifier.pkl
```

승격 결과는 PostgreSQL의 `model_registry` 테이블에 저장됩니다.

```text
PROMOTED
REJECTED
```

이를 통해 기준 미달 모델이나 기존 best보다 낮은 성능의 모델이 추론 단계에 사용되지 않도록 제어합니다.

### 12. Prediction Lineage

`src/common/model_registry.py`

batch inference와 FastAPI 예측은 `model_registry`에서 현재 PROMOTED 상태의 모델 metadata를 조회합니다.

예측 결과에는 아래 모델 정보를 함께 저장합니다.

```text
model_name
model_version
model_run_id
model_registry_id
model_path
```

이를 통해 `model_predictions`의 각 예측 결과가 어떤 MLflow run과 어떤 promoted model에서 생성되었는지 추적할 수 있습니다.

```text
model_registry
    ↓
model_predictions
```

### 13. 예측 품질 정보

`src/common/prediction_quality.py`

FastAPI와 batch inference 예측 결과에 단순 예측값뿐 아니라 예측 품질 정보를 함께 저장합니다.

저장 정보:

```text
confidence
confidence_level
is_low_confidence
top_predictions
```

예측 품질 기준:

```text
HIGH   : confidence >= 0.8
MEDIUM : confidence >= 0.6
LOW    : confidence < 0.6
```

이를 통해 예측 결과가 낮은 신뢰도인지, 상위 후보군이 어떻게 분포하는지 확인할 수 있습니다.

### 13-1. Prediction Quality Gate

`src/quality/check_prediction_quality.py`

batch inference 이후 예측 결과 품질을 검증합니다.

검증 항목:

```text
prediction_count
avg_prediction_confidence
low_confidence_ratio
null_confidence_count
```

환경변수:

```env
MIN_AVG_PREDICTION_CONFIDENCE=0.6
MAX_LOW_CONFIDENCE_RATIO=0.4
MIN_PREDICTION_ROWS=1
```

검증 결과는 `pipeline_check_results`에 `PREDICTION_QUALITY` 타입으로 저장됩니다.

DAG 흐름:

```text
batch_inference
    ↓
check_prediction_quality
    ↓
generate_pipeline_report
```

예측 품질 기준을 통과하지 못하면 DAG를 실패시켜, 낮은 품질의 예측 결과가 정상 산출물처럼 리포트되지 않도록 합니다.


### 14. Batch Inference

`src/inference/batch_inference.py`

현재 promoted model을 이용해 `cleaned_job_posts` 전체 데이터에 대해 일괄 예측을 수행하고, 결과를 `model_predictions` 테이블에 저장합니다.

```text
cleaned_job_posts
→ promoted model predict
→ prediction quality 계산
→ model_predictions 저장
```

batch inference 결과에는 예측값, confidence, top-k 후보, model lineage가 함께 저장됩니다.

`model_predictions.prediction_source`에는 `BATCH`가 저장됩니다.

```text
prediction_source = BATCH
```

API 예측 로그가 `model_predictions`를 FK로 참조할 수 있기 때문에, batch inference 재실행 시 `model_predictions` 전체를 TRUNCATE하지 않습니다. 대신 batch 결과만 삭제 후 재생성합니다.

```sql
DELETE FROM model_predictions
WHERE COALESCE(prediction_source, 'BATCH') = 'BATCH';
```

### 15. FastAPI

`src/inference/api.py`

현재 promoted model을 로드해 단건 예측 API를 제공합니다.

주요 기능:

```text
GET  /
GET  /model
POST /reload-model
POST /predict
```

`/predict`는 아래 작업을 수행합니다.

```text
직무 카테고리 예측
confidence 반환
confidence_level 반환
low confidence 여부 반환
top-k prediction 반환
기술스택 추출
model_predictions 테이블 저장
api_prediction_logs 테이블 저장
model lineage 저장
latency_ms 저장
성공/실패 status 저장
```

API 예측은 `model_predictions.prediction_source = API`로 저장되며, API 요청/응답 로그는 `api_prediction_logs`에 별도로 저장됩니다.

```text
model_predictions
→ 모델 예측 결과 저장

api_prediction_logs
→ FastAPI 요청/응답/실패/latency 로그 저장
```

FastAPI는 시작 시점에 모델을 로드하며, 요청 시점에 현재 promoted model metadata를 확인합니다. 모델 파일 또는 registry 정보가 변경되면 새 모델을 자동으로 reload합니다.

<img src="docs/images/fastapi.png" width="900">

### 16. Pipeline Report

`src/reporting/generate_pipeline_report.py`

모델 registry, prediction lineage, pipeline check 결과를 조회해 Markdown 리포트를 생성합니다.

생성 파일:

```text
reports/latest_pipeline_report.md
```

리포트 포함 내용:

```text
Latest Promoted Model
Model Registry History
Prediction Lineage Summary
Latest Predictions
Prediction Category Distribution
Check Result Summary
Latest Check Details
Failed Checks
Model Promotion Summary
Raw Job Count by Source
Cleaned Job Quality by Source
Job Category Distribution by Source
Skill Extraction Summary by Source
Top Skills by Source
Prediction Summary by Source
Prediction Quality Check Results
Prediction Quality Summary
Prediction Quality by Category
API Request Quality Summary
API Low Confidence Summary
Recent API Prediction Logs
```

이를 통해 현재 서빙 모델, 모델 승격 이력, 예측 lineage, 데이터/모델 검증 결과, source별 데이터 품질을 한 번에 확인할 수 있습니다.


### 16-1. Streamlit Dashboard

`src/dashboard/app.py`

PostgreSQL에 저장된 MLOps 파이프라인 실행 결과를 조회하는 대시보드입니다.

확인 가능한 항목:

```text
Latest promoted model
Source data quality
Batch prediction quality
Pipeline check results
FastAPI prediction logs
Recent predictions
```

Docker Compose 서비스:

```text
dashboard
```

실행:

```bash
docker compose up -d dashboard
```

접속:

```text
http://localhost:8501
```

<img src="docs/images/dashboard.png" width="900">

### 17. Airflow DAG

`dags/jobskill_pipeline_dag.py`

전체 파이프라인을 아래 순서로 실행합니다.

```text
prepare_raw_sources
    ↓
generate_sample_jobs
    ↓
load_raw_jobs
    ↓
crawl_remoteok_jobs
    ↓
preprocess_jobs
    ↓
check_training_data
    ↓
train_model
    ↓
check_model_performance
    ↓
promote_model
    ↓
batch_inference
    ↓
check_prediction_quality
    ↓
generate_pipeline_report
```

DAG 이름:

```text
jobskill_mlops_pipeline
```

초기 DAG는 BashOperator로 각 Python 스크립트를 실행하는 방식이었지만, 현재는 PythonOperator 기반으로 개선했습니다.

```text
기존:
BashOperator
→ python src/xxx.py

개선:
PythonOperator
→ 각 모듈의 main() 함수 직접 호출
```

<img src="docs/images/Airflow%20DAG%20success.png" width="900">

### 18. 테스트 코드

`tests/unit/`

주요 전처리/예측 품질 로직에 대해 pytest 기반 단위 테스트를 추가했습니다.

테스트 대상:

```text
직무 라벨링 규칙
confidence level 계산
low confidence 판단
top-k prediction 생성
```

실행:

```bash
pytest
```

컨테이너 내부 실행:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && pytest"
```


### 18-1. GitHub Actions / Ruff

`.github/workflows/pytest.yml`  
`pyproject.toml`  
`requirements-dev.txt`

push 또는 pull request 발생 시 GitHub Actions에서 단위 테스트와 코드 품질 검사를 자동 실행합니다.

실행 조건:

```text
push to main
push to feature/**
pull request to main
```

실행 항목:

```text
ruff check src dags scripts tests
pytest
```

현재 Ruff는 초기 도입 단계이므로 전체 스타일 규칙이 아니라, 런타임 오류로 이어질 가능성이 높은 기본 규칙만 검사합니다.

활성화한 Ruff 규칙:

```text
E9  : syntax error
F63 : invalid comparison / usage
F7  : control-flow related issue
F82 : undefined name
```

## PostgreSQL 테이블

현재 사용하는 주요 테이블은 아래와 같습니다.

```text
raw_job_posts
cleaned_job_posts
job_post_skills
model_predictions
api_prediction_logs
pipeline_check_results
model_registry
```

역할:

```text
raw_job_posts
- 원천 채용공고 저장
- sample / remoteok 등 source 구분
- external_id / source_job_id 기반 외부 데이터 추적

cleaned_job_posts
- 정제된 채용공고 저장
- 직무 라벨 저장
- 모델 입력용 text_for_model 저장

job_post_skills
- 채용공고별 추출된 기술스택 저장

model_predictions
- FastAPI 또는 batch inference 예측 결과 저장
- prediction_source로 API / BATCH 구분
- 예측에 사용된 모델 lineage 저장
- confidence / top-k prediction 저장

api_prediction_logs
- FastAPI 요청/응답/실패/latency 로그 저장
- model_predictions.prediction_id와 연결
- API 운영 관점의 request/response 추적

pipeline_check_results
- 데이터 품질 체크 결과 저장
- 모델 성능 체크 결과 저장

model_registry
- MLflow run 기반 모델 승격 결과 저장
- promoted / rejected 모델 이력 관리
```

FK 관계:

```text
raw_job_posts
    ↑
    └── cleaned_job_posts.raw_id

cleaned_job_posts
    ↑
    ├── job_post_skills.job_post_id
    └── model_predictions.job_post_id

model_registry
    ↑
    └── model_predictions.model_registry_id

model_predictions
    ↑
    └── api_prediction_logs.prediction_id
```

<img src="docs/images/postgresql.png" width="900">

## 환경 변수

`.env.example`을 복사해서 `.env`를 생성합니다.

```bash
cp .env.example .env
```

예시:

```env
DB_HOST=postgres
DB_PORT=5432
DB_NAME=jobskill
DB_USER=jobskill
DB_PASSWORD=jobskill

AIRFLOW_DB_NAME=airflow
MLFLOW_DB_NAME=mlflow

MLFLOW_TRACKING_URI=postgresql+psycopg2://jobskill:jobskill@postgres:5432/mlflow
MLFLOW_ARTIFACT_ROOT=/opt/airflow/project/mlartifacts
MLFLOW_EXPERIMENT_NAME=jobskill-classifier

MODEL_NAME=job_classifier
MODEL_PATH=models/job_classifier.pkl
BEST_MODEL_PATH=models/best/job_classifier.pkl

AIRFLOW_JWT_SECRET=change_me
AIRFLOW_API_SECRET_KEY=change_me
AIRFLOW_FERNET_KEY=change_me

MIN_TRAINING_ROWS=50
MIN_CATEGORY_COUNT=2
MAX_UNKNOWN_RATIO=0.5
MIN_SAMPLES_PER_CLASS=2
TEST_SIZE=0.3

MIN_MODEL_ACCURACY=0.7
MIN_MODEL_F1_WEIGHTED=0.7

LOW_CONFIDENCE_THRESHOLD=0.6
PREDICTION_TOP_K=3
MIN_AVG_PREDICTION_CONFIDENCE=0.6
MAX_LOW_CONFIDENCE_RATIO=0.4
MIN_PREDICTION_ROWS=1

REMOTEOK_API_URL=https://remoteok.com/api
REMOTEOK_CRAWL_LIMIT=50
REMOTEOK_SCAN_LIMIT=1000
REMOTEOK_FILTER_ENABLED=true
REMOTEOK_MIN_RELEVANCE_SCORE=2
REMOTEOK_MAX_RETRIES=3
REMOTEOK_RETRY_SLEEP_SECONDS=3
REMOTEOK_REQUEST_TIMEOUT_SECONDS=30
REMOTEOK_FALLBACK_TO_EXISTING_RAW=true
REMOTEOK_MIN_FETCHED_JOBS=1

DATA_SOURCE_MODE=mixed
```

로컬 Python에서 직접 실행할 경우에는 `DB_HOST=localhost`로 변경합니다.

```env
DB_HOST=localhost
```

Docker Compose 내부에서 실행할 경우에는 `DB_HOST=postgres`를 사용합니다.

```env
DB_HOST=postgres
```

## 보안 및 Secret 관리

이 프로젝트는 포트폴리오 공개 저장소를 전제로 하므로, 실제 secret 값은 Git에 포함하지 않습니다.

Airflow 3.x 실행에 필요한 JWT secret, API secret, Fernet key는 `.env` 파일에서만 관리하고, `docker-compose.yml`에서는 환경변수 참조 방식으로 사용합니다.

```yaml
AIRFLOW__API_AUTH__JWT_SECRET: ${AIRFLOW_JWT_SECRET}
AIRFLOW__API__SECRET_KEY: ${AIRFLOW_API_SECRET_KEY}
AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
```

`.env.example`에는 실제 값이 아니라 placeholder만 작성합니다.

```env
AIRFLOW_JWT_SECRET=change_me
AIRFLOW_API_SECRET_KEY=change_me
AIRFLOW_FERNET_KEY=change_me
```

Secret 값은 아래와 같이 생성할 수 있습니다.

```bash
python - <<'PY'
from cryptography.fernet import Fernet
import secrets

print("AIRFLOW_JWT_SECRET=" + secrets.token_urlsafe(64))
print("AIRFLOW_API_SECRET_KEY=" + secrets.token_urlsafe(64))
print("AIRFLOW_FERNET_KEY=" + Fernet.generate_key().decode())
PY
```

`.env`, Airflow 로그인 파일, 실행 로그, 모델 artifact 등은 Git에 포함하지 않습니다.

```gitignore
.env
.env.*
!.env.example
simple_auth_manager_passwords.json
airflow_logs/
models/
mlartifacts/
```

개발 중 README와 Compose 설정에 로컬 개발용 secret 값이 포함된 이력이 있었기 때문에, 공개 저장소 정리 과정에서 `git-filter-repo`를 사용해 Git history에서도 해당 값을 제거했습니다.

```bash
git filter-repo --replace-text replacements.txt --force
```

History rewrite 이후에는 원격 저장소에 force push가 필요합니다.

```bash
git push origin --force --all
git push origin --force --tags
```

이미 Git에 노출된 secret은 폐기하고 새 secret을 생성해 `.env`에 반영했습니다.

## Airflow 3.x 설정 주의사항

Airflow 3.x에서는 scheduler가 task 실행 상태를 `airflow-apiserver`의 execution API에 전달합니다.

따라서 Docker Compose 환경에서는 아래 설정이 필요합니다.

```yaml
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-apiserver:8080/execution/
```

이 값은 컨테이너 내부 통신 기준입니다.  
따라서 호스트 포트를 `8081:8080`으로 변경하더라도 execution API URL은 `8080`을 유지해야 합니다.

```text
브라우저 접속       : http://localhost:8081
컨테이너 내부 통신 : http://airflow-apiserver:8080/execution/
```

또한 scheduler, apiserver, dag-processor, triggerer 간 JWT secret 값이 다르면 아래 오류가 발생할 수 있습니다.

```text
Invalid auth token: Signature verification failed
```

이를 방지하기 위해 Airflow 공통 환경변수에 secret 값을 고정합니다.  
단, 실제 secret 값은 Git에 올리지 않고 `.env`에서만 관리합니다.

```yaml
AIRFLOW__API_AUTH__JWT_SECRET: ${AIRFLOW_JWT_SECRET}
AIRFLOW__API__SECRET_KEY: ${AIRFLOW_API_SECRET_KEY}
AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
```

Airflow 설정 반영 여부는 아래 명령으로 확인합니다.

```bash
docker compose exec airflow-scheduler airflow config get-value api_auth jwt_secret
docker compose exec airflow-apiserver airflow config get-value api_auth jwt_secret

docker compose exec airflow-scheduler airflow config get-value api secret_key
docker compose exec airflow-apiserver airflow config get-value api secret_key

docker compose exec airflow-scheduler airflow config get-value core execution_api_server_url
```

정상 조건:

```text
scheduler jwt_secret == apiserver jwt_secret
scheduler api_secret == apiserver api_secret
execution_api_server_url == http://airflow-apiserver:8080/execution/
```

## 실행 방법

### 1. 필요한 디렉터리 생성

```bash
mkdir -p data/raw data/processed models/best mlartifacts airflow_logs reports docs/images
```

권한 설정:

```bash
sudo chown -R 50000:0 data models mlartifacts airflow_logs reports
sudo chmod -R g+rwX data models mlartifacts airflow_logs reports
```

### 2. Airflow 이미지 빌드

```bash
docker compose build airflow-image
```

### 3. API 이미지 빌드

```bash
docker compose build api
```

### 4. PostgreSQL 실행

```bash
docker compose up -d postgres
```

### 5. DB 생성 확인 또는 생성

PostgreSQL volume이 이미 존재하는 경우 init SQL이 다시 실행되지 않을 수 있습니다.  
그 경우 아래 명령으로 직접 DB를 생성합니다.

```bash
docker exec -it jobskill-postgres psql -U jobskill -d jobskill -c "CREATE DATABASE airflow;"
docker exec -it jobskill-postgres psql -U jobskill -d jobskill -c "CREATE DATABASE mlflow;"
```

이미 존재한다는 에러가 나오면 무시해도 됩니다.

### 6. 프로젝트 테이블 생성

```bash
docker exec -i jobskill-postgres psql -U jobskill -d jobskill < sql/create_tables.sql
```

### 7. Airflow 메타DB 초기화

```bash
docker compose up --no-build airflow-init
```

### 8. 전체 서비스 실행

```bash
docker compose up -d --no-build --force-recreate \
  airflow-apiserver \
  airflow-scheduler \
  airflow-dag-processor \
  airflow-triggerer \
  mlflow \
  api \
  dashboard
```

### 9. 컨테이너 상태 확인

```bash
docker compose ps
```

## Makefile 명령어

자주 사용하는 Docker Compose, Airflow, 테스트, 리포트, smoke check 명령어는 `Makefile`로 표준화했습니다.

명령어 목록 확인:

```bash
make help
```

주요 명령어:

```bash
make build
make up
make ps
make dag-errors
make dag-tasks
make dag-trigger
make report
make dashboard
make smoke
make ci
```

대표 실행 흐름:

```bash
make build
make up
make dag-trigger
make smoke
make dashboard
```

`make ci`는 로컬에서 Ruff와 pytest를 함께 실행합니다.

```bash
make ci
```

`make smoke`는 로컬 Docker Compose 서비스의 기본 기동성과 주요 엔드포인트를 확인합니다.

```bash
make smoke
```

## 접속 정보

### Airflow UI

호스트 포트를 `8081:8080`으로 사용한 경우:

```text
http://localhost:8081
```

호스트 포트를 `8080:8080`으로 사용한 경우:

```text
http://localhost:8080
```

### MLflow UI

```text
http://localhost:5000
```

### FastAPI

```text
http://localhost:8000/docs
```

### Streamlit Dashboard

```text
http://localhost:8501
```


## Streamlit Dashboard 실행

### Docker Compose 실행

```bash
docker compose up -d dashboard
```

접속:

```text
http://localhost:8501
```

로그 확인:

```bash
docker compose logs --tail=100 dashboard
```

### 로컬 실행

로컬에서 직접 실행하려면 Streamlit과 Plotly가 필요합니다.

```bash
pip install streamlit plotly
```

로컬 실행 시 PostgreSQL 컨테이너에 호스트 기준으로 접속해야 하므로 `DB_HOST=localhost`를 사용합니다.

```bash
DB_HOST=localhost streamlit run src/dashboard/app.py
```

## Airflow DAG 실행

### DAG 목록 확인

```bash
docker compose exec airflow-scheduler airflow dags list
```

### DAG import error 확인

```bash
docker compose exec airflow-scheduler airflow dags list-import-errors
```

### DAG task 목록 확인

```bash
docker compose exec airflow-scheduler airflow tasks list jobskill_mlops_pipeline
```

### DAG unpause

```bash
docker compose exec airflow-scheduler airflow dags unpause jobskill_mlops_pipeline
```

### DAG trigger

```bash
docker compose exec airflow-scheduler airflow dags trigger jobskill_mlops_pipeline
```

### DAG run 확인

```bash
docker compose exec airflow-scheduler airflow dags list-runs jobskill_mlops_pipeline
```

### DAG run별 task 상태 확인

```bash
docker compose exec airflow-scheduler airflow tasks states-for-dag-run jobskill_mlops_pipeline "<run_id>"
```

## 실행 결과 확인

Airflow DAG를 통해 전체 파이프라인이 아래 순서로 실행됩니다.

```text
prepare_raw_sources
    ↓
generate_sample_jobs
    ↓
load_raw_jobs
    ↓
crawl_remoteok_jobs
    ↓
preprocess_jobs
    ↓
check_training_data
    ↓
train_model
    ↓
check_model_performance
    ↓
promote_model
    ↓
batch_inference
    ↓
check_prediction_quality
    ↓
generate_pipeline_report
```

정상 상태 예시:

```text
prepare_raw_sources         success
generate_sample_jobs         success
load_raw_jobs                success
crawl_remoteok_jobs          success
preprocess_jobs              success
check_training_data          success
train_model                  success
check_model_performance      success
promote_model                success
batch_inference              success
check_prediction_quality      success
generate_pipeline_report     success
```

파이프라인 실행 후 PostgreSQL에는 데이터, 검증 결과, 모델 승격 결과, 예측 결과가 저장됩니다.

```sql
SELECT COUNT(*) FROM raw_job_posts;
SELECT COUNT(*) FROM cleaned_job_posts;
SELECT COUNT(*) FROM job_post_skills;
SELECT COUNT(*) FROM pipeline_check_results;
SELECT COUNT(*) FROM model_registry;
SELECT COUNT(*) FROM model_predictions;
SELECT COUNT(*) FROM api_prediction_logs;
```

## Smoke Check

서비스 실행 후 주요 컴포넌트가 정상 동작하는지 확인하기 위해 smoke check 스크립트를 제공합니다.

실행:

```bash
make smoke
```

또는 직접 실행:

```bash
./scripts/smoke_check.sh
```

검증 항목:

```text
Docker Compose config
Container status
PostgreSQL connection
Project table existence
Core table counts
Airflow DAG import errors
Airflow pipeline task list
MLflow UI
FastAPI health
FastAPI model info
Streamlit dashboard
```

GitHub Actions smoke workflow에서도 동일한 스크립트를 사용합니다.  
단, GitHub Actions runner는 빈 환경이므로 API를 기동하기 전에 sample data 기반 최소 파이프라인을 먼저 실행해 promoted model을 생성한 뒤 smoke check를 수행합니다.

```text
PostgreSQL 실행
→ 프로젝트 테이블 생성
→ Airflow / MLflow 실행
→ sample_only 기반 최소 파이프라인 실행
→ promoted model 생성 확인
→ API / Dashboard 실행
→ smoke_check.sh 실행
```

## 로컬 Python 스크립트 실행 순서

Airflow 없이 개별 스크립트로 실행할 수도 있습니다.

```bash
python src/ingestion/prepare_raw_sources.py
python scripts/generate_sample_jobs.py
python src/ingestion/load_raw_jobs.py
python src/crawling/crawl_remoteok_jobs.py
python src/preprocessing/preprocess_db.py
python src/quality/check_training_data.py
python src/training/train_baseline.py
python src/quality/check_model_performance.py
python src/training/promote_model.py
python src/inference/batch_inference.py
python src/quality/check_prediction_quality.py
python src/reporting/generate_pipeline_report.py
```

컨테이너 내부에서 실행할 경우:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/ingestion/prepare_raw_sources.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python scripts/generate_sample_jobs.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/ingestion/load_raw_jobs.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/crawling/crawl_remoteok_jobs.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/preprocessing/preprocess_db.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_training_data.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/training/train_baseline.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_model_performance.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/training/promote_model.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/inference/batch_inference.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_prediction_quality.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/reporting/generate_pipeline_report.py"
```

## FastAPI 실행

### 로컬 실행

```bash
uvicorn src.inference.api:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Compose 실행

```bash
docker compose up -d api
```

API 문서:

```text
http://localhost:8000/docs
```

### API 엔드포인트

```text
GET  /
GET  /model
POST /reload-model
POST /predict
```

모델 정보 확인:

```bash
curl http://localhost:8000/model
```

모델 강제 reload:

```bash
curl -X POST http://localhost:8000/reload-model
```

예시 요청:

```json
{
  "title": "데이터 엔지니어 채용",
  "description": "Python SQL Airflow Kafka Spark 기반 데이터 파이프라인 개발자를 찾습니다.",
  "job_post_id": null
}
```

curl 테스트:

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "데이터 엔지니어 채용",
    "description": "Python SQL Airflow Kafka Spark 기반 데이터 파이프라인 개발자를 찾습니다.",
    "job_post_id": null
  }'
```

예시 응답:

```json
{
  "job_category": "Data Engineer",
  "confidence": 0.91,
  "confidence_level": "HIGH",
  "is_low_confidence": false,
  "top_predictions": [
    {
      "category": "Data Engineer",
      "probability": 0.91
    },
    {
      "category": "Backend Engineer",
      "probability": 0.05
    },
    {
      "category": "ML Engineer",
      "probability": 0.02
    }
  ],
  "skills": ["Airflow", "Kafka", "Python", "Spark", "SQL"],
  "prediction_id": 1,
  "prediction_source": "API",
  "api_log_id": 1,
  "model_name": "job_classifier",
  "model_run_id": "472340fc8ca14b50a382dd46f61108bf",
  "model_registry_id": 1,
  "model_path": "models/best/job_classifier.pkl"
}
```

## PostgreSQL 확인 명령어

PostgreSQL 접속:

```bash
docker exec -it jobskill-postgres psql -U jobskill -d jobskill
```

테이블 확인:

```sql
\dt
```

데이터 건수 확인:

```sql
SELECT COUNT(*) FROM raw_job_posts;
SELECT COUNT(*) FROM cleaned_job_posts;
SELECT COUNT(*) FROM job_post_skills;
SELECT COUNT(*) FROM pipeline_check_results;
SELECT COUNT(*) FROM model_registry;
SELECT COUNT(*) FROM model_predictions;
SELECT COUNT(*) FROM api_prediction_logs;
```

source별 raw 데이터 확인:

```sql
SELECT
    source,
    COUNT(*) AS cnt
FROM raw_job_posts
GROUP BY source
ORDER BY source;
```

source별 라벨 품질 확인:

```sql
SELECT
    COALESCE(r.source, 'unknown') AS source,
    COUNT(*) AS cleaned_count,
    COUNT(*) FILTER (WHERE c.job_category = 'Unknown') AS unknown_count,
    ROUND(
        COUNT(*) FILTER (WHERE c.job_category = 'Unknown')::numeric
        / NULLIF(COUNT(*), 0),
        4
    ) AS unknown_ratio
FROM cleaned_job_posts c
JOIN raw_job_posts r
    ON c.raw_id = r.id
GROUP BY COALESCE(r.source, 'unknown')
ORDER BY cleaned_count DESC;
```

직무별 건수 확인:

```sql
SELECT job_category, COUNT(*)
FROM cleaned_job_posts
GROUP BY job_category
ORDER BY job_category;
```

기술스택 상위 목록 확인:

```sql
SELECT skill_name, COUNT(*)
FROM job_post_skills
GROUP BY skill_name
ORDER BY COUNT(*) DESC
LIMIT 20;
```

검증 결과 확인:

```sql
SELECT
    check_type,
    check_name,
    status,
    metric_value,
    threshold_value,
    message,
    checked_at
FROM pipeline_check_results
ORDER BY id DESC
LIMIT 20;
```

모델 registry 확인:

```sql
SELECT
    id,
    model_name,
    run_id,
    accuracy,
    f1_weighted,
    status,
    promoted_model_path,
    created_at
FROM model_registry
ORDER BY id DESC
LIMIT 10;
```

예측 결과 확인:

```sql
SELECT
    predicted_category,
    COUNT(*) AS cnt,
    ROUND(AVG(confidence)::numeric, 4) AS avg_confidence
FROM model_predictions
GROUP BY predicted_category
ORDER BY predicted_category;
```

예측 결과와 model lineage 확인:

```sql
SELECT
    mp.id,
    mp.job_post_id,
    mp.predicted_category,
    ROUND(mp.confidence::numeric, 4) AS confidence,
    mp.confidence_level,
    mp.is_low_confidence,
    mp.model_name,
    mp.model_version,
    mp.model_run_id,
    mp.model_registry_id,
    mr.status AS registry_status,
    mr.f1_weighted,
    mp.model_path,
    mp.predicted_at
FROM model_predictions mp
LEFT JOIN model_registry mr
    ON mp.model_registry_id = mr.id
ORDER BY mp.id DESC
LIMIT 20;
```

라벨과 예측 결과 비교:

```sql
SELECT
    mp.id,
    cjp.title,
    cjp.job_category AS rule_label,
    mp.predicted_category,
    ROUND(mp.confidence::numeric, 4) AS confidence,
    mp.model_name,
    mp.model_run_id,
    mp.predicted_at
FROM model_predictions mp
JOIN cleaned_job_posts cjp
    ON mp.job_post_id = cjp.id
ORDER BY mp.id
LIMIT 20;
```


API / BATCH 예측 구분 확인:

```sql
SELECT
    prediction_source,
    COUNT(*) AS cnt
FROM model_predictions
GROUP BY prediction_source
ORDER BY prediction_source;
```

API 요청 로그 확인:

```sql
SELECT
    id,
    prediction_id,
    request_title,
    response_category,
    response_confidence_level,
    status,
    ROUND(latency_ms::numeric, 2) AS latency_ms,
    created_at
FROM api_prediction_logs
ORDER BY id DESC
LIMIT 10;
```

Prediction quality check 결과 확인:

```sql
SELECT
    check_type,
    check_name,
    status,
    ROUND(metric_value::numeric, 4) AS metric_value,
    ROUND(threshold_value::numeric, 4) AS threshold_value,
    message,
    checked_at
FROM pipeline_check_results
WHERE check_type = 'PREDICTION_QUALITY'
ORDER BY id DESC
LIMIT 20;
```

## Pipeline Report 생성

리포트 생성:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/reporting/generate_pipeline_report.py"
```

생성 결과:

```text
reports/latest_pipeline_report.md
```

리포트에서 확인 가능한 내용:

```text
현재 promoted model
모델 승격/거절 이력
예측 결과 lineage
데이터 품질 체크 결과
모델 성능 체크 결과
source별 Unknown 비율
source별 라벨 분포
source별 skill 추출 결과
source별 prediction confidence
prediction quality gate 결과
API 요청 성공/실패율
API low confidence 비율
최근 API prediction logs
```


### Sample Pipeline Report

포트폴리오용 샘플 리포트는 아래 문서에서 확인할 수 있습니다.

```text
docs/sample_pipeline_report.md
```

`reports/latest_pipeline_report.md`는 DAG 실행 시점마다 갱신되는 runtime output입니다.  
GitHub에서 고정된 예시 산출물을 보여주기 위해 `docs/sample_pipeline_report.md`를 별도로 관리합니다.

## 테스트 실행

로컬 실행:

```bash
pytest
```

컨테이너 내부 실행:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && pytest"
```

테스트 대상:

```text
직무 라벨링 규칙
예측 confidence level
low confidence 판단
top-k prediction 생성
```

### GitHub Actions

GitHub Actions는 두 가지 workflow로 구성합니다.

```text
.github/workflows/pytest.yml
.github/workflows/smoke.yml
```

#### Python CI

push 또는 pull request 발생 시 pytest와 Ruff를 자동 실행합니다.

실행 조건:

```text
push to main
push to feature/**
pull request to main
```

실행 항목:

```bash
ruff check src dags scripts tests
pytest
```

로컬에서도 동일하게 확인할 수 있습니다.

```bash
pip install -r requirements-dev.txt
ruff check src dags scripts tests
pytest
```

#### Smoke Check

Docker Compose 기반 전체 서비스 기동성을 확인하는 smoke check workflow입니다.

실행 조건:

```text
workflow_dispatch
push to main
push to feature/**
```

검증 흐름:

```text
Docker Compose image build
PostgreSQL start
Airflow / MLflow metadata DB prepare
Project table create
Airflow metadata DB init
Airflow / MLflow start
sample_only minimal pipeline run
promoted model existence check
FastAPI / Dashboard start
scripts/smoke_check.sh run
```

GitHub Actions의 빈 runner에서는 promoted model이 존재하지 않으므로, API를 시작하기 전에 최소 파이프라인을 먼저 실행해 `models/best/job_classifier.pkl`과 `model_registry`의 promoted model을 생성합니다.

## Release / Changelog

프로젝트의 주요 완성 단위는 `CHANGELOG.md`에 기록합니다.

현재 기준 MVP 릴리스:

```text
v0.1.0 - MVP Release
```

릴리스 기준:

```text
Airflow end-to-end DAG 구성
PostgreSQL 기반 데이터/예측/검증/모델 메타데이터 저장
MLflow tracking / artifact 연동
모델 성능 gate와 promotion
Batch inference / API inference 저장 분리
Prediction quality gate
Pipeline report
Streamlit Dashboard
Makefile
Local smoke check
GitHub Actions Python CI
GitHub Actions Docker Compose smoke check
```

태그 생성 예시:

```bash
git tag -a v0.1.0 -m "v0.1.0 MVP release"
git push origin v0.1.0
```

## Git 제외 대상

아래 파일과 디렉터리는 Git에 올리지 않습니다.

```text
.env
.env.*
!.env.example
.venv/
__pycache__/
data/raw/*.csv
data/processed/*.csv
models/
mlartifacts/
mlflow.db
mlruns/
airflow_logs/
reports/*
!reports/.gitkeep
simple_auth_manager_passwords.json
```

포트폴리오용 스크린샷은 Git에 포함합니다.

```text
docs/images/
```

`reports/latest_pipeline_report.md`는 실행 결과 예시로 보여주고 싶으면 커밋해도 되고, 매 실행마다 바뀌는 산출물로 관리하려면 `.gitignore`에 추가합니다.

## Line Ending 관리

WSL / Windows 환경에서 shell script, Makefile, workflow 파일의 줄바꿈이 CRLF로 바뀌면 실행 문제가 생길 수 있습니다.

이를 방지하기 위해 `.gitattributes`에서 주요 파일의 line ending을 LF로 고정합니다.

```gitattributes
*.sh text eol=lf
Makefile text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.py text eol=lf
*.md text eol=lf
```

변경 후 기존 파일을 재정규화할 수 있습니다.

```bash
git add --renormalize .
```

## 트러블슈팅

### 1. MLflow command error

에러:

```text
airflow command error: argument GROUP_OR_COMMAND: invalid choice: 'mlflow'
```

원인:

```text
apache/airflow 이미지의 기본 entrypoint가 airflow이기 때문에
mlflow ui 명령이 airflow mlflow ui처럼 해석됨
```

해결:

```yaml
mlflow:
  image: jobskill-airflow:3.2.2
  entrypoint: /bin/bash
  command:
    - -c
    - |
      mlflow ui \
        --backend-store-uri postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@postgres:5432/${MLFLOW_DB_NAME} \
        --default-artifact-root /opt/airflow/project/mlartifacts \
        --host 0.0.0.0 \
        --port 5000
```

### 2. Airflow task 권한 오류

증상:

```text
PermissionError: [Errno 13] Permission denied: 'data/raw/sample_jobs.csv'
```

해결:

```bash
sudo chown -R 50000:0 data models mlartifacts airflow_logs reports
sudo chmod -R g+rwX data models mlartifacts airflow_logs reports
```

### 3. cleaned_job_posts 삭제 시 FK 오류

증상:

```text
DELETE FROM cleaned_job_posts
ForeignKeyViolation
```

원인:

```text
model_predictions 또는 job_post_skills가 cleaned_job_posts를 참조 중
```

해결:

```sql
TRUNCATE TABLE
    model_predictions,
    job_post_skills,
    cleaned_job_posts
RESTART IDENTITY
CASCADE;
```

Remote OK raw 데이터를 삭제하려면 파생 테이블을 먼저 비워야 합니다.

```sql
TRUNCATE TABLE
    model_predictions,
    job_post_skills,
    cleaned_job_posts
RESTART IDENTITY
CASCADE;

DELETE FROM raw_job_posts
WHERE source = 'remoteok';
```

### 4. Airflow execution API connection refused

증상:

```text
httpx.ConnectError: [Errno 111] Connection refused
```

해결:

```yaml
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-apiserver:8080/execution/
```

확인:

```bash
docker compose exec airflow-scheduler airflow config get-value core execution_api_server_url
```

정상:

```text
http://airflow-apiserver:8080/execution/
```

### 5. Invalid auth token

증상:

```text
Invalid auth token: Signature verification failed
```

원인:

```text
scheduler / apiserver / dag-processor / triggerer 간 JWT secret 불일치
```

해결:

```yaml
AIRFLOW__API_AUTH__JWT_SECRET: ${AIRFLOW_JWT_SECRET}
AIRFLOW__API__SECRET_KEY: ${AIRFLOW_API_SECRET_KEY}
```

확인:

```bash
docker compose exec airflow-scheduler airflow config get-value api_auth jwt_secret
docker compose exec airflow-apiserver airflow config get-value api_auth jwt_secret

docker compose exec airflow-scheduler airflow config get-value api secret_key
docker compose exec airflow-apiserver airflow config get-value api secret_key
```

정상 조건:

```text
scheduler jwt_secret == apiserver jwt_secret
scheduler api_secret == apiserver api_secret
```

### 6. 8080 port already allocated

증상:

```text
Bind for 0.0.0.0:8080 failed: port is already allocated
```

해결 1. 기존 컨테이너 제거:

```bash
docker ps | grep 8080
docker rm -f <container_name>
```

해결 2. 호스트 포트 변경:

```yaml
ports:
  - "8081:8080"
```

이 경우 Airflow UI는 아래로 접속합니다.

```text
http://localhost:8081
```

단, execution API URL은 그대로 둡니다.

```yaml
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-apiserver:8080/execution/
```

### 7. docker-compose.yml environment must be a mapping

증상:

```text
services.airflow-apiserver.environment must be a mapping
services.airflow-scheduler.environment must be a mapping
```

정상:

```yaml
environment:
  KEY: value
  KEY2: value2
```

잘못된 예:

```yaml
environment:
  - KEY=value
```

확인:

```bash
docker compose config
```

### 8. Batch inference 입력 데이터 없음

증상:

```text
ValueError: No cleaned job posts found. Run preprocess_db.py first.
```

해결:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/preprocessing/preprocess_db.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_training_data.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/inference/batch_inference.py"
```

또는 전체 DAG를 다시 실행합니다.

```bash
docker compose exec airflow-scheduler airflow dags trigger jobskill_mlops_pipeline
```

### 9. 모델 승격 결과 확인

모델 promotion 결과는 `model_registry` 테이블에서 확인합니다.

```bash
docker exec -it jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    model_name,
    run_id,
    accuracy,
    f1_weighted,
    status,
    message,
    created_at
FROM model_registry
ORDER BY id DESC
LIMIT 10;
"
```

같은 성능의 모델을 반복 실행하면 `REJECTED`가 나올 수 있습니다. 이는 기존 best model보다 성능이 개선되지 않았다는 의미이므로 정상 동작입니다.

### 10. API 모델 reload 확인

현재 API가 사용하는 모델 정보는 `/model`에서 확인합니다.

```bash
curl http://localhost:8000/model
```

강제로 reload하려면 아래 API를 호출합니다.

```bash
curl -X POST http://localhost:8000/reload-model
```

예측 시점에 promoted model 정보가 바뀌면 API는 새 모델을 reload합니다. reload 로그는 API 컨테이너 로그에서 확인할 수 있습니다.

```bash
docker compose logs --tail=100 api
```

### 11. 크롤링 데이터 Unknown 비율이 높은 경우

Remote OK는 개발/데이터 직무 외의 공고도 포함될 수 있습니다.

확인:

```sql
SELECT
    job_category,
    COUNT(*) AS cnt
FROM cleaned_job_posts
GROUP BY job_category
ORDER BY cnt DESC;
```

source별 Unknown 비율 확인:

```sql
SELECT
    COALESCE(r.source, 'unknown') AS source,
    COUNT(*) AS cleaned_count,
    COUNT(*) FILTER (WHERE c.job_category = 'Unknown') AS unknown_count,
    ROUND(
        COUNT(*) FILTER (WHERE c.job_category = 'Unknown')::numeric
        / NULLIF(COUNT(*), 0),
        4
    ) AS unknown_ratio
FROM cleaned_job_posts c
JOIN raw_job_posts r
    ON c.raw_id = r.id
GROUP BY COALESCE(r.source, 'unknown')
ORDER BY cleaned_count DESC;
```

해결 방향:

```text
crawler에서 label_jobs.py 기준으로 Unknown 공고 제외
preprocess_db.py에서 tags를 description과 함께 라벨링에 사용
label_jobs.py의 직무별 keyword 확장
```


### 12. crawler_only 학습 시 stratified split 실패

증상:

```text
ValueError: The least populated classes in y have only 1 member
```

원인:

```text
crawler_only 모드에서는 실제 수집 데이터 분포가 치우쳐 특정 직무 라벨이 1건만 존재할 수 있음
stratify=y를 사용하는 train_test_split은 클래스별 최소 2건 이상이 필요함
```

해결:

```text
train_baseline.py에서 MIN_SAMPLES_PER_CLASS보다 적은 rare class를 학습 데이터에서 제외
TEST_SIZE를 class 개수 이상으로 보정
```

환경변수:

```env
MIN_SAMPLES_PER_CLASS=2
TEST_SIZE=0.3
```

### 13. api_prediction_logs FK로 인한 batch inference TRUNCATE 실패

증상:

```text
cannot truncate a table referenced in a foreign key constraint
Table "api_prediction_logs" references "model_predictions"
```

원인:

```text
api_prediction_logs.prediction_id가 model_predictions.id를 참조하므로
model_predictions만 단독 TRUNCATE할 수 없음
```

해결:

```text
model_predictions에 prediction_source 컬럼 추가
API 예측은 prediction_source = API
batch 예측은 prediction_source = BATCH
batch inference는 BATCH row만 DELETE 후 재생성
```

```sql
DELETE FROM model_predictions
WHERE COALESCE(prediction_source, 'BATCH') = 'BATCH';
```

### 14. batch inference INSERT 컬럼 개수 불일치

증상:

```text
INSERT has more expressions than target columns
```

원인:

```text
VALUES에는 prediction_source를 넣었지만
INSERT INTO model_predictions 컬럼 목록에 prediction_source가 빠져 있었음
```

해결:

```sql
INSERT INTO model_predictions (
    job_post_id,
    prediction_source,
    model_name,
    model_version,
    model_run_id,
    model_registry_id,
    model_path,
    predicted_category,
    confidence,
    confidence_level,
    is_low_confidence,
    top_predictions
)
```

### 15. check_prediction_quality SQL JOIN 문법 오류

증상:

```text
syntax error at or near "JOIN"
```

원인:

```text
SQL 작성 시 WHERE가 JOIN보다 먼저 배치됨
```

잘못된 예:

```sql
FROM model_predictions mp
WHERE COALESCE(mp.prediction_source, 'BATCH') = 'BATCH'
JOIN cleaned_job_posts c
    ON mp.job_post_id = c.id
```

정상:

```sql
FROM model_predictions mp
JOIN cleaned_job_posts c
    ON mp.job_post_id = c.id
WHERE COALESCE(mp.prediction_source, 'BATCH') = 'BATCH'
```

### 16. Prediction quality gate 실패

증상:

```text
avg_prediction_confidence failed
low_confidence_ratio failed
```

원인:

```text
batch inference 결과의 평균 confidence가 기준보다 낮거나
low confidence 비율이 허용 기준보다 높음
```

확인:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_prediction_quality.py"
```

임시 기준 완화:

```env
MIN_AVG_PREDICTION_CONFIDENCE=0.3
MAX_LOW_CONFIDENCE_RATIO=0.8
```

단, 포트폴리오 관점에서는 기준을 낮추는 것보다 source별 / category별 confidence 리포트로 품질 이슈를 드러내는 것이 더 자연스럽습니다.



### 17. docker-compose.yml dashboard 들여쓰기 오류

증상:

```text
mapping key "image" already defined
mapping key "container_name" already defined
```

원인:

```text
dashboard 서비스가 services 하위가 아니라 api 서비스 내부에 잘못 들여쓰기됨
```

잘못된 예:

```yaml
  api:
    ...
    depends_on:
      postgres:
        condition: service_healthy

    dashboard:
    image: jobskill-airflow:3.2.2
```

정상:

```yaml
  api:
    ...
    depends_on:
      postgres:
        condition: service_healthy

  dashboard:
    image: jobskill-airflow:3.2.2
```

확인:

```bash
docker compose config
```

### 18. Streamlit command not found

증상:

```text
streamlit: command not found
```

원인:

```text
dashboard 서비스가 사용하는 jobskill-airflow 이미지에 streamlit / plotly가 설치되지 않음
```

해결:

```text
requirements.txt에 streamlit, plotly 추가
Airflow 이미지 재빌드
dashboard 서비스 재실행
```

```bash
docker compose build airflow-image
docker compose up -d dashboard
```

### 19. GitHub Actions에서 pytest import 실패

증상:

```text
ModuleNotFoundError
```

원인:

```text
workflow에서 테스트에 필요한 의존성을 충분히 설치하지 않음
```

해결:

```text
requirements-dev.txt에 pytest / ruff 추가
테스트가 pandas, sklearn 등 프로젝트 의존성을 직접 import하면 requirements.txt도 함께 설치
```

예시:

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
```


### 20. GitHub Actions에 Smoke Check workflow가 보이지 않는 경우

증상:

```text
Actions 화면에 pytest.yml만 보이고 smoke.yml이 보이지 않음
```

확인:

```bash
git fetch origin
git ls-tree -r origin/main --name-only | grep ".github/workflows"
git show origin/main:.github/workflows/smoke.yml
```

정상 조건:

```text
.github/workflows/pytest.yml
.github/workflows/smoke.yml
```

`workflow_dispatch`만 있는 workflow는 기본 브랜치에 workflow 파일이 반영되어야 Actions 화면에 보입니다.  
초기 등록 확인을 쉽게 하기 위해 아래처럼 `push` trigger를 임시로 추가할 수 있습니다.

```yaml
on:
  workflow_dispatch:
  push:
    branches:
      - main
      - "feature/**"
```

### 21. GitHub Actions smoke check에서 FastAPI health 실패

증상:

```text
[CHECK] FastAPI health
curl: (7) Failed to connect to localhost port 8000
[FAIL] FastAPI health
```

원인:

```text
GitHub Actions runner는 빈 환경이므로 API 기동 시점에 promoted model이 아직 존재하지 않음
FastAPI가 시작 시점에 모델을 로드하지 못해 컨테이너가 종료됨
```

해결:

```text
smoke workflow에서 API를 시작하기 전에 sample_only 기반 최소 파이프라인을 먼저 실행
models/best/job_classifier.pkl 생성 확인
model_registry의 PROMOTED row 생성 확인
이후 API와 Dashboard 실행
```

확인 명령:

```bash
test -f models/best/job_classifier.pkl

docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT id, model_name, status, promoted_model_path, created_at
FROM model_registry
ORDER BY id DESC
LIMIT 5;
"
```

### 22. feature 브랜치 push 시 upstream branch 없음

증상:

```text
fatal: The current branch feature/xxx has no upstream branch.
```

해결:

```bash
git push --set-upstream origin feature/xxx
```

이후부터는 같은 브랜치에서 `git push`만 실행하면 됩니다.

## What I Learned

이 프로젝트를 통해 아래 내용을 실습했습니다.

```text
Airflow 3.x 기반 DAG orchestration 구성
Airflow scheduler, apiserver, dag-processor, triggerer 분리 실행
Airflow execution API와 JWT secret 설정 문제 해결
LocalExecutor 기반 task 실행 구조 확인
BashOperator 기반 DAG를 PythonOperator 기반 DAG로 개선
PostgreSQL을 서비스 DB, Airflow metadata DB, MLflow backend store로 분리 구성
MLflow backend store와 artifact store 분리
scikit-learn 모델 학습 결과를 MLflow에 기록
데이터 품질 체크를 통한 학습 전 검증 로직 구성
MLflow metric 기반 모델 성능 gate 구성
데이터 품질/모델 성능 검증 결과를 PostgreSQL에 저장
기준 미달 데이터/모델이 후속 task로 넘어가지 않도록 DAG 제어
기존 best model과 신규 학습 모델의 성능 비교 및 promotion 로직 구성
promoted model 기반 batch inference 구성
FastAPI 기반 단건 추론 API 구성
FastAPI serving model 자동 reload 구성
예측 결과에 model lineage와 prediction quality 저장
Remote OK 외부 채용공고 수집 및 필터링 구성
source별 데이터 품질 리포트 구성
pytest 기반 단위 테스트 추가
Docker Compose 기반 MLOps 개발 환경 구성
Git history에 포함된 secret 제거 및 secret rotation 수행
DATA_SOURCE_MODE 기반 sample/crawler/mixed 실행 모드 구성
외부 API 수집 실패에 대한 retry / fallback 처리 구성
FastAPI 요청/응답/실패/latency 로그 테이블 분리
API prediction과 batch prediction 저장 경로 분리
FK 제약조건을 고려한 batch inference 재실행 방식 개선
prediction quality gate를 통한 batch inference 결과 검증
source/category별 prediction confidence 분석 리포트 구성
GitHub Actions 기반 pytest 자동 실행 구성
Ruff 기반 코드 품질 검사 CI 구성
Streamlit / Plotly 기반 MLOps Dashboard 구성
포트폴리오용 dashboard 스크린샷 및 sample pipeline report 문서화
Makefile 기반 프로젝트 실행 명령어 표준화
로컬 smoke check script를 통한 서비스 기동성 검증
GitHub Actions에서 Docker Compose 기반 smoke check workflow 구성
CI 빈 환경에서 promoted model 생성 전 API 기동 시 실패하는 문제 해결
CHANGELOG와 Git tag 기반 MVP 릴리스 관리
```

## 현재 완료된 범위

```text
샘플 채용공고 데이터 생성
Remote OK 외부 채용공고 수집 추가
크롤링 데이터 source / external_id / source_url 저장
크롤링 데이터 필터링 추가
PostgreSQL raw/cleaned/skills 테이블 저장
전처리 결과 기반 데이터 품질 체크 추가
데이터 품질 체크 결과 저장 테이블 추가
label_jobs.py weighted keyword scoring 개선
description / tags 기반 라벨링 개선
TF-IDF + Logistic Regression 모델 학습
MLflow PostgreSQL backend store 연동
MLflow artifact 저장
MLflow metric 기반 모델 성능 체크 추가
모델 성능 체크 결과 저장 테이블 추가
best model promotion 로직 추가
model_registry 테이블 추가
promoted model 기반 batch inference 추가
prediction lineage 저장 구조 추가
prediction quality 저장 구조 추가
FastAPI /predict API 구성
FastAPI /model API 추가
FastAPI /reload-model API 추가
FastAPI serving model 자동 reload 추가
Pipeline report 생성 추가
source별 데이터 품질 리포트 추가
pytest 단위 테스트 추가
Airflow 3.x Docker Compose 구성
Airflow DAG PythonOperator 전환
Airflow execution API / JWT 설정 이슈 해결
Airflow DAG 전체 실행 검증
Git history secret 제거
실행용 secret rotation
README 스크린샷 추가
포트폴리오용 README 보안 정리
DATA_SOURCE_MODE 기반 데이터 소스 모드 분리
prepare_raw_sources task 추가
sample_only / crawler_only / mixed 실행 모드 추가
Remote OK retry / fallback 처리 추가
crawler_only 학습 rare class 제외 처리 추가
api_prediction_logs 테이블 추가
FastAPI 요청/응답/실패/latency 로그 저장 추가
model_predictions prediction_source 추가
API / BATCH prediction 저장 구분 추가
batch inference BATCH row만 삭제 후 재생성하도록 개선
check_prediction_quality.py 추가
prediction quality gate DAG 추가
API quality / prediction quality 리포트 항목 추가
FK / SQL / INSERT 컬럼 불일치 트러블슈팅 정리
GitHub Actions 기반 pytest 자동 실행 workflow 추가
Ruff 기반 코드 품질 검사 추가
requirements-dev.txt / pyproject.toml 추가
포트폴리오용 sample pipeline report 추가
runtime report와 documentation sample 분리
Streamlit Dashboard 추가
Docker Compose dashboard 서비스 추가
Dashboard 스크린샷 docs/images/dashboard.png 추가
README에 Dashboard 실행 방법 / 접속 정보 / 스크린샷 반영
```

## 다음 개선 예정

```text
prediction quality 기반 Slack/Email 알림 추가
크롤링 source 추가 또는 수집 데이터 다양화
실제 운영 환경 기준 README 아키텍처 다이어그램 보강
모델 성능 개선을 위한 데이터 라벨링/피처 개선
GitHub Actions smoke workflow 실행 시간 최적화
GitHub Actions smoke workflow를 workflow_dispatch 전용으로 전환할지 검토
Streamlit Dashboard 필터 / 기간 조건 / 상세 drill-down 추가
API 요청 로그 기반 모니터링 지표 고도화
```
