# jobskill-mlops project

채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow와 MLflow를 이용해 데이터 생성, 원천 적재, 전처리, 데이터 품질 검증, 모델 학습, 성능 검증, 모델 승격, 일괄 예측, API 추론까지 연결하는 경량 MLOps 파이프라인 프로젝트입니다.

이 프로젝트는 단순 모델 학습이 아니라, 학습 전 데이터 품질 검증, 모델 성능 gate, best model promotion, 예측 결과 lineage 저장, FastAPI serving model 자동 리로드까지 포함한 end-to-end MLOps 흐름을 구성하는 것을 목표로 합니다.

## 프로젝트 목표

이 프로젝트는 채용공고 데이터를 사용해 아래 흐름을 구성합니다.

```text
샘플 채용공고 데이터 생성
→ PostgreSQL raw 테이블 적재
→ 텍스트 정제 / 직무 라벨링 / 기술스택 추출
→ PostgreSQL cleaned / skills 테이블 저장
→ 학습 데이터 품질 체크
→ 검증 결과 저장
→ TF-IDF + Logistic Regression 모델 학습
→ MLflow 실험 기록
→ 모델 artifact 저장
→ 모델 성능 기준 체크
→ 성능 검증 결과 저장
→ best model promotion
→ model_registry 저장
→ promoted model 기반 batch inference
→ model_predictions 테이블 저장
→ prediction lineage 저장
→ FastAPI 단건 예측
→ FastAPI serving model 자동 reload
→ Airflow DAG로 전체 파이프라인 실행
```

## Architecture

```mermaid
flowchart LR
    A[Sample Job CSV] --> B[raw_job_posts]
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

    MR --> K[FastAPI /predict]
    BM --> K
    K --> J

    subgraph Orchestration
        L[Airflow DAG]
    end

    L --> A
    L --> B
    L --> C
    L --> Q1
    L --> F
    L --> Q2
    L --> P
    L --> I
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
└── FastAPI
    ├── /predict
    ├── /model
    └── /reload-model
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
Container       : Docker Compose
```

## 디렉터리 구조

```text
.
├── README.md
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
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
│   └── create_tables.sql
├── scripts/
│   └── generate_sample_jobs.py
├── src/
│   ├── common/
│   │   ├── db.py
│   │   └── model_registry.py
│   ├── ingestion/
│   │   └── load_raw_jobs.py
│   ├── preprocessing/
│   │   ├── clean_text.py
│   │   ├── extract_skills.py
│   │   ├── label_jobs.py
│   │   └── preprocess_db.py
│   ├── quality/
│   │   ├── check_logger.py
│   │   ├── check_training_data.py
│   │   └── check_model_performance.py
│   ├── training/
│   │   ├── train_baseline.py
│   │   └── promote_model.py
│   └── inference/
│       ├── api.py
│       └── batch_inference.py
├── data/
│   ├── raw/
│   └── processed/
├── models/
│   └── best/
├── mlartifacts/
├── airflow_logs/
├── docs/
│   └── images/
└── notebooks/
```

> `data/`, `models/`, `mlartifacts/`, `airflow_logs/`, `.env`, `simple_auth_manager_passwords.json` 등은 로컬 실행 중 생성되는 산출물이므로 Git에는 포함하지 않습니다.

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

### 2. Raw 데이터 적재

`src/ingestion/load_raw_jobs.py`

생성된 CSV 데이터를 PostgreSQL의 `raw_job_posts` 테이블에 적재합니다.

### 3. 전처리

`src/preprocessing/preprocess_db.py`

`raw_job_posts` 데이터를 읽어 아래 처리를 수행합니다.

```text
텍스트 정제
직무 라벨링
기술스택 추출
전처리 결과 저장
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

### 4. 데이터 품질 체크

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

Airflow DAG에서는 `preprocess_jobs` 이후, `train_model` 이전에 실행됩니다.

```text
preprocess_jobs
    ↓
check_training_data
    ↓
train_model
```

데이터 품질 기준을 통과하지 못하면 DAG를 실패시켜, 부적절한 데이터로 모델 학습이 진행되지 않도록 합니다.

### 5. 검증 결과 저장

`src/quality/check_logger.py`

데이터 품질 체크와 모델 성능 체크 결과를 PostgreSQL의 `pipeline_check_results` 테이블에 저장합니다.

저장 대상:

```text
DATA_QUALITY
MODEL_PERFORMANCE
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

### 6. 모델 학습

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

### 7. 모델 성능 체크

`src/quality/check_model_performance.py`

MLflow에 기록된 최신 학습 run의 metric을 조회해 모델 성능 기준을 검증합니다.

검증 항목:

```text
accuracy >= MIN_MODEL_ACCURACY
f1_weighted >= MIN_MODEL_F1_WEIGHTED
```

Airflow DAG에서는 `train_model` 이후, `promote_model` 이전에 실행됩니다.

```text
train_model
    ↓
check_model_performance
    ↓
promote_model
```

모델 성능이 기준보다 낮으면 DAG를 실패시켜, 낮은 품질의 모델이 promotion 또는 batch inference 단계로 넘어가지 않도록 합니다.

### 8. 모델 승격

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

Airflow DAG에서는 `check_model_performance` 이후, `batch_inference` 이전에 실행됩니다.

```text
check_model_performance
    ↓
promote_model
    ↓
batch_inference
```

이를 통해 기준 미달 모델이나 기존 best보다 낮은 성능의 모델이 추론 단계에 사용되지 않도록 제어합니다.

### 9. Prediction Lineage

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

### 10. Batch Inference

`src/inference/batch_inference.py`

현재 promoted model을 이용해 `cleaned_job_posts` 전체 데이터에 대해 일괄 예측을 수행하고, 결과를 `model_predictions` 테이블에 저장합니다.

```text
cleaned_job_posts
→ promoted model predict
→ model_predictions 저장
```

batch inference 결과에는 예측값뿐 아니라 model lineage도 함께 저장됩니다.

### 11. FastAPI

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
기술스택 추출
model_predictions 테이블 저장
model lineage 저장
```

FastAPI는 시작 시점에 모델을 로드하며, 요청 시점에 현재 promoted model metadata를 확인합니다. 모델 파일 또는 registry 정보가 변경되면 새 모델을 자동으로 reload합니다.

### 12. Airflow DAG

`dags/jobskill_pipeline_dag.py`

전체 파이프라인을 아래 순서로 실행합니다.

```text
generate_sample_jobs
    ↓
load_raw_jobs
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
```

DAG 이름:

```text
jobskill_mlops_pipeline
```

## PostgreSQL 테이블

현재 사용하는 주요 테이블은 아래와 같습니다.

```text
raw_job_posts
cleaned_job_posts
job_post_skills
model_predictions
pipeline_check_results
model_registry
```

역할:

```text
raw_job_posts
- 원천 채용공고 저장

cleaned_job_posts
- 정제된 채용공고 저장
- 직무 라벨 저장
- 모델 입력용 text_for_model 저장

job_post_skills
- 채용공고별 추출된 기술스택 저장

model_predictions
- FastAPI 또는 batch inference 예측 결과 저장
- 예측에 사용된 모델 lineage 저장

pipeline_check_results
- 데이터 품질 체크 결과 저장
- 모델 성능 체크 결과 저장

model_registry
- MLflow run 기반 모델 승격 결과 저장
- promoted / rejected 모델 이력 관리
```

FK 관계:

```text
cleaned_job_posts
    ↑
    ├── job_post_skills.job_post_id
    └── model_predictions.job_post_id

model_registry
    ↑
    └── model_predictions.model_registry_id
```

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

MIN_MODEL_ACCURACY=0.7
MIN_MODEL_F1_WEIGHTED=0.7
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

## Airflow 로그인 설정

Airflow 3.x Simple Auth Manager를 사용합니다.

개발 편의를 위해 로컬에 아래 파일을 생성합니다.

```bash
vi simple_auth_manager_passwords.json
```

내용:

```json
{
  "airflow": "airflow"
}
```

해당 파일은 Git에 포함하지 않습니다.

```text
ID: airflow
PW: airflow
```

만약 자동 생성된 계정을 사용하는 경우, 로그에 아래와 같은 형태로 비밀번호가 출력될 수 있습니다.

```text
Simple auth manager | Password for user 'admin': <generated-password>
```

이 경우 접속 정보는 아래와 같습니다.

```text
ID: admin
PW: <generated-password>
```

## Docker Compose Airflow 공통 설정 예시

`x-airflow-common`의 `environment`는 반드시 map 형태로 작성합니다.

정상:

```yaml
environment:
  KEY: value
  KEY2: value2
```

잘못된 형태:

```yaml
environment:
  - KEY=value
```

Airflow 공통 설정 예시:

```yaml
x-airflow-common: &airflow-common
  image: jobskill-airflow:3.2.2
  env_file:
    - .env
  environment: &airflow-common-env
    AIRFLOW__CORE__EXECUTOR: LocalExecutor
    AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-apiserver:8080/execution/

    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@postgres:5432/${AIRFLOW_DB_NAME}

    AIRFLOW__API_AUTH__JWT_SECRET: ${AIRFLOW_JWT_SECRET}
    AIRFLOW__API__SECRET_KEY: ${AIRFLOW_API_SECRET_KEY}
    AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}

    AIRFLOW__CORE__LOAD_EXAMPLES: "false"
    AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: "true"

    AIRFLOW__CORE__PARALLELISM: "4"
    AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG: "1"
    AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG: "1"

    AIRFLOW__CORE__AUTH_MANAGER: airflow.api_fastapi.auth.managers.simple.simple_auth_manager.SimpleAuthManager
    AIRFLOW__SIMPLE_AUTH_MANAGER__USERS: airflow:admin
    AIRFLOW__SIMPLE_AUTH_MANAGER__PASSWORDS_FILE: /opt/airflow/simple_auth_manager_passwords.json

    PYTHONPATH: /opt/airflow/project
```

Airflow 서비스 예시:

```yaml
airflow-apiserver:
  <<: *airflow-common
  container_name: jobskill-airflow-apiserver
  command: api-server --host 0.0.0.0 --port 8080
  ports:
    - "8081:8080"

airflow-scheduler:
  <<: *airflow-common
  container_name: jobskill-airflow-scheduler
  command: scheduler

airflow-dag-processor:
  <<: *airflow-common
  container_name: jobskill-airflow-dag-processor
  command: dag-processor

airflow-triggerer:
  <<: *airflow-common
  container_name: jobskill-airflow-triggerer
  command: triggerer
```

## 실행 방법

### 1. 필요한 디렉터리 생성

```bash
mkdir -p data/raw data/processed models/best mlartifacts airflow_logs
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
  api
```

### 9. 컨테이너 상태 확인

```bash
docker compose ps
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

### DAG 테스트 실행

```bash
docker compose exec airflow-scheduler airflow dags test jobskill_mlops_pipeline 2026-06-24
```

## 실행 결과 확인

Airflow DAG를 통해 전체 파이프라인이 아래 순서로 실행됩니다.

```text
generate_sample_jobs
    ↓
load_raw_jobs
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
```

정상 상태 예시:

```text
generate_sample_jobs        success
load_raw_jobs               success
preprocess_jobs             success
check_training_data         success
train_model                 success
check_model_performance     success
promote_model               success
batch_inference             success
```

파이프라인 실행 후 PostgreSQL에는 데이터, 검증 결과, 모델 승격 결과, 예측 결과가 저장됩니다.

```sql
SELECT COUNT(*) FROM raw_job_posts;
SELECT COUNT(*) FROM cleaned_job_posts;
SELECT COUNT(*) FROM job_post_skills;
SELECT COUNT(*) FROM pipeline_check_results;
SELECT COUNT(*) FROM model_registry;
SELECT COUNT(*) FROM model_predictions;
```

직무별 데이터 분포 확인:

```sql
SELECT job_category, COUNT(*)
FROM cleaned_job_posts
GROUP BY job_category
ORDER BY job_category;
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

예측 결과와 model lineage 확인:

```sql
SELECT
    id,
    job_post_id,
    predicted_category,
    ROUND(confidence::numeric, 4) AS confidence,
    model_name,
    model_version,
    model_run_id,
    model_registry_id,
    model_path,
    predicted_at
FROM model_predictions
ORDER BY id DESC
LIMIT 10;
```

MLflow에서는 모델 학습 run, metric, artifact 저장 여부를 확인합니다.

```text
http://localhost:5000
```

FastAPI는 Swagger UI에서 확인합니다.

```text
http://localhost:8000/docs
```

## 로컬 Python 스크립트 실행 순서

Airflow 없이 개별 스크립트로 실행할 수도 있습니다.

```bash
python scripts/generate_sample_jobs.py
python src/ingestion/load_raw_jobs.py
python src/preprocessing/preprocess_db.py
python src/quality/check_training_data.py
python src/training/train_baseline.py
python src/quality/check_model_performance.py
python src/training/promote_model.py
python src/inference/batch_inference.py
```

컨테이너 내부에서 실행할 경우:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python scripts/generate_sample_jobs.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/ingestion/load_raw_jobs.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/preprocessing/preprocess_db.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_training_data.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/training/train_baseline.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_model_performance.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/training/promote_model.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/inference/batch_inference.py"
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
  "skills": ["Airflow", "Kafka", "Python", "Spark", "SQL"],
  "prediction_id": 1,
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

## 권한 문제 해결

Airflow task가 `data/raw/sample_jobs.csv`, `models/`, `mlartifacts/`, `airflow_logs/`에 쓰지 못하는 경우 아래 명령을 실행합니다.

```bash
sudo chown -R 50000:0 data models mlartifacts airflow_logs
sudo chmod -R g+rwX data models mlartifacts airflow_logs
```

개발용으로 간단히 열어도 됩니다.

```bash
chmod -R 777 data models mlartifacts airflow_logs
```

## MLflow

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

## Screenshots

포트폴리오 확인용으로 아래 스크린샷을 추가할 수 있습니다.

```text
docs/images/
├── airflow-dag-success.png
├── airflow-task-graph.png
├── mlflow-run-metrics.png
├── mlflow-artifacts.png
├── fastapi-docs.png
├── api-model-info.png
├── postgres-check-results.png
├── postgres-model-registry.png
└── postgres-prediction-lineage.png
```

README 예시:

```md
### Airflow DAG

![Airflow DAG Success](docs/images/airflow-dag-success.png)

### MLflow Experiment

![MLflow Run Metrics](docs/images/mlflow-run-metrics.png)

### FastAPI Docs

![FastAPI Docs](docs/images/fastapi-docs.png)

### Model Registry

![Model Registry](docs/images/postgres-model-registry.png)

### Prediction Lineage

![Prediction Lineage](docs/images/postgres-prediction-lineage.png)
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
simple_auth_manager_passwords.json
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
sudo chown -R 50000:0 data models mlartifacts airflow_logs
sudo chmod -R g+rwX data models mlartifacts airflow_logs
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

### 4. Airflow execution API connection refused

증상:

```text
httpx.ConnectError: [Errno 111] Connection refused
```

원인:

```text
scheduler 컨테이너가 execution API를 localhost:8080으로 찾거나,
airflow-apiserver가 실행 중이지 않음
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

원인:

```text
environment를 list 형태 또는 잘못된 YAML 형태로 작성함
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

### 8. Docker Desktop API 500 오류

증상:

```text
request returned 500 Internal Server Error for API route
check if the server supports the requested API version
```

원인:

```text
Docker Desktop 또는 Docker Engine 상태가 꼬인 경우
```

해결:

```powershell
wsl --shutdown
```

그 후 Docker Desktop을 재시작합니다.

WSL에서 다시 확인:

```bash
docker version
docker compose ps
```

### 9. No logs available for this task

증상:

```text
No logs available for this task.
```

원인:

```text
task가 아직 running 상태로 넘어가지 못하고 queued 상태에 머물러 있으면 로그 파일이 생성되지 않을 수 있음
```

확인:

```bash
docker compose exec airflow-scheduler airflow dags list-runs jobskill_mlops_pipeline
docker compose exec airflow-scheduler airflow tasks states-for-dag-run jobskill_mlops_pipeline "<run_id>"
```

scheduler 로그 확인:

```bash
docker compose logs --tail=500 airflow-scheduler | grep -E "jobskill_mlops_pipeline|queued|scheduled|running|failed|ERROR|Traceback|LocalExecutor|TaskInstance|paused|pool" -A 30 -B 30
```

scheduler가 정상 기동되면 아래와 같은 로그를 확인할 수 있습니다.

```text
Worker starting up
LocalExecutor
Adopting or resetting orphaned tasks for active dag runs
Uvicorn running on http://:8793
```

DAG가 paused 상태인 경우 unpause 후 다시 trigger합니다.

```bash
docker compose exec airflow-scheduler airflow dags unpause jobskill_mlops_pipeline
docker compose exec airflow-scheduler airflow dags trigger jobskill_mlops_pipeline
```

### 10. Git history에 포함된 secret 제거

증상:

```text
README 또는 docker-compose.yml에 로컬 개발용 secret 값이 커밋됨
```

해결:

```bash
cat > replacements.txt <<'EOF'
기존_SECRET_값==>REMOVED_SECRET
EOF

git filter-repo --replace-text replacements.txt --force
```

검증:

```bash
git log -S"기존_SECRET_값" --all --oneline
git grep -n "기존_SECRET_값"
```

History rewrite 이후 원격 저장소에 강제 push합니다.

```bash
git push origin --force --all
git push origin --force --tags
```

노출된 secret은 폐기하고 새 값으로 교체합니다.

### 11. 데이터 품질 체크 실패

증상:

```text
check_training_data task failed
```

원인 예시:

```text
cleaned_job_posts 데이터 수 부족
text_for_model 누락
job_category 누락
Unknown 라벨 비율 초과
기술스택 추출 결과 없음
```

확인:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_training_data.py"
```

관련 환경변수:

```env
MIN_TRAINING_ROWS=50
MIN_CATEGORY_COUNT=2
MAX_UNKNOWN_RATIO=0.5
```

데이터 품질 기준을 통과하지 못하면 모델 학습을 중단합니다.

### 12. 모델 성능 체크 실패

증상:

```text
check_model_performance task failed
```

원인 예시:

```text
MLflow experiment 없음
MLflow run 없음
accuracy metric 없음
f1_weighted metric 없음
성능 기준 미달
```

확인:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_model_performance.py"
```

관련 환경변수:

```env
MLFLOW_EXPERIMENT_NAME=jobskill-classifier
MIN_MODEL_ACCURACY=0.7
MIN_MODEL_F1_WEIGHTED=0.7
```

실패 테스트:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && MIN_MODEL_ACCURACY=1.1 python src/quality/check_model_performance.py"
```

모델 성능 기준을 통과하지 못하면 promotion과 batch inference를 중단합니다.

### 13. Batch inference 입력 데이터 없음

증상:

```text
ValueError: No cleaned job posts found. Run preprocess_db.py first.
```

원인:

```text
cleaned_job_posts에 text_for_model이 있는 데이터가 없음
batch_inference를 전처리 없이 단독 실행함
```

확인:

```bash
docker exec -it jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    COUNT(*) AS cleaned_count,
    COUNT(text_for_model) AS text_not_null_count
FROM cleaned_job_posts;
"
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

### 14. 모델 승격 결과 확인

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

### 15. API 모델 reload 확인

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

## What I Learned

이 프로젝트를 통해 아래 내용을 실습했습니다.

```text
Airflow 3.x 기반 DAG orchestration 구성
Airflow scheduler, apiserver, dag-processor, triggerer 분리 실행
Airflow execution API와 JWT secret 설정 문제 해결
LocalExecutor 기반 task 실행 구조 확인
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
예측 결과에 model lineage를 저장해 추적 가능성 확보
Docker Compose 기반 MLOps 개발 환경 구성
Git history에 포함된 secret 제거 및 secret rotation 수행
```

## 현재 완료된 범위

```text
샘플 채용공고 데이터 생성
PostgreSQL raw/cleaned/skills 테이블 저장
전처리 결과 기반 데이터 품질 체크 추가
데이터 품질 체크 결과 저장 테이블 추가
TF-IDF + Logistic Regression 모델 학습
MLflow PostgreSQL backend store 연동
MLflow artifact 저장
MLflow metric 기반 모델 성능 체크 추가
모델 성능 체크 결과 저장 테이블 추가
best model promotion 로직 추가
model_registry 테이블 추가
promoted model 기반 batch inference 추가
prediction lineage 저장 구조 추가
FastAPI /predict API 구성
FastAPI /model API 추가
FastAPI /reload-model API 추가
FastAPI serving model 자동 reload 추가
model_predictions 테이블 저장 구조 확장
Airflow 3.x Docker Compose 구성
Airflow execution API / JWT 설정 이슈 해결
Airflow DAG 전체 실행 검증
Git history secret 제거
실행용 secret rotation
포트폴리오용 README 보안 정리
```

## 다음 개선 예정

```text
README 실행 스크린샷 추가
label_jobs.py 규칙 확장으로 Unknown 라벨 감소
FastAPI 예측 결과 품질 확인 강화
실제 채용공고 크롤러 추가
모델 registry / prediction lineage 기반 리포트 쿼리 추가
Airflow DAG task를 BashOperator에서 PythonOperator 기반으로 개선 검토
테스트 코드 추가
```
