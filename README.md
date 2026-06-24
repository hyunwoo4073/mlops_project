# jobskill-mlops project

채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow와 MLflow를 이용해 데이터 생성, 원천 적재, 전처리, 모델 학습, 실험 기록, 일괄 예측, API 추론까지 연결하는 경량 MLOps 파이프라인 프로젝트입니다.

## 프로젝트 목표

이 프로젝트는 채용공고 데이터를 사용해 아래 흐름을 구성하는 것을 목표로 합니다.

```text
샘플 채용공고 데이터 생성
→ PostgreSQL raw 테이블 적재
→ 텍스트 정제 / 직무 라벨링 / 기술스택 추출
→ PostgreSQL cleaned / skills 테이블 저장
→ TF-IDF + Logistic Regression 모델 학습
→ MLflow 실험 기록
→ 모델 artifact 저장
→ batch inference 실행
→ model_predictions 테이블 저장
→ FastAPI 단건 예측
→ Airflow DAG로 전체 파이프라인 실행
```

## 현재 구성

```text
Docker Compose
├── PostgreSQL
│   ├── jobskill DB  : 프로젝트 데이터 저장
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
    └── /predict API
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
│   │   └── db.py
│   ├── ingestion/
│   │   └── load_raw_jobs.py
│   ├── preprocessing/
│   │   ├── clean_text.py
│   │   ├── extract_skills.py
│   │   ├── label_jobs.py
│   │   └── preprocess_db.py
│   ├── training/
│   │   └── train_baseline.py
│   └── inference/
│       ├── api.py
│       └── batch_inference.py
├── data/
│   ├── raw/
│   └── processed/
├── models/
├── mlartifacts/
├── airflow_logs/
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

### 4. 모델 학습

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

### 5. Batch Inference

`src/inference/batch_inference.py`

학습된 모델을 이용해 `cleaned_job_posts` 전체 데이터에 대해 일괄 예측을 수행하고, 결과를 `model_predictions` 테이블에 저장합니다.

```text
cleaned_job_posts
→ model predict
→ model_predictions 저장
```

### 6. FastAPI

`src/inference/api.py`

학습된 모델을 로드해 단건 예측 API를 제공합니다.

주요 기능:

```text
POST /predict
→ 직무 카테고리 예측
→ confidence 반환
→ 기술스택 추출
→ model_predictions 테이블 저장
```

### 7. Airflow DAG

`dags/jobskill_pipeline_dag.py`

전체 파이프라인을 아래 순서로 실행합니다.

```text
generate_sample_jobs
    ↓
load_raw_jobs
    ↓
preprocess_jobs
    ↓
train_model
    ↓
batch_inference
```

DAG 이름:

```text
jobskill_mlops_pipeline
```

## PostgreSQL 테이블

현재 사용하는 테이블은 4개입니다.

```text
raw_job_posts
cleaned_job_posts
job_post_skills
model_predictions
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
```

FK 관계:

```text
cleaned_job_posts
    ↑
    ├── job_post_skills.job_post_id
    └── model_predictions.job_post_id
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
```

로컬 Python에서 직접 실행할 경우에는 `DB_HOST=localhost`로 변경합니다.

```env
DB_HOST=localhost
```

Docker Compose 내부에서 실행할 경우에는 `DB_HOST=postgres`를 사용합니다.

```env
DB_HOST=postgres
```

## Airflow 3.x 설정 주의사항

Airflow 3.x에서는 scheduler가 task 실행 상태를 `airflow-apiserver`의 execution API에 전달합니다.

따라서 Docker Compose 환경에서는 아래 설정이 필요합니다.

```yaml
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-apiserver:8080/execution/
```

컨테이너 내부 통신 기준이므로, 호스트 포트를 `8081:8080`으로 변경하더라도 위 값은 `8080`을 유지해야 합니다.

```text
브라우저 접속       : http://localhost:8081
컨테이너 내부 통신 : http://airflow-apiserver:8080/execution/
```

또한 scheduler, apiserver, dag-processor, triggerer 간 JWT secret 값이 다르면 아래 오류가 발생할 수 있습니다.

```text
Invalid auth token: Signature verification failed
```

이를 방지하기 위해 Airflow 공통 환경변수에 secret 값을 고정합니다.

```yaml
AIRFLOW__API_AUTH__JWT_SECRET: jobskill_airflow_jwt_secret_key_for_local_dev_please_change_1234567890
AIRFLOW__API__SECRET_KEY: jobskill_airflow_api_secret_key_for_local_dev_please_change_1234567890
AIRFLOW__CORE__FERNET_KEY: nRWFYBfEZXiyHGWnDUTXJufvQrd2KRfa4DSHs7YZxCI=
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

    AIRFLOW__API_AUTH__JWT_SECRET: jobskill_airflow_jwt_secret_key_for_local_dev_please_change_1234567890
    AIRFLOW__API__SECRET_KEY: jobskill_airflow_api_secret_key_for_local_dev_please_change_1234567890
    AIRFLOW__CORE__FERNET_KEY: nRWFYBfEZXiyHGWnDUTXJufvQrd2KRfa4DSHs7YZxCI=

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
mkdir -p data/raw data/processed models mlartifacts airflow_logs
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

## 로컬 Python 스크립트 실행 순서

Airflow 없이 개별 스크립트로 실행할 수도 있습니다.

```bash
python scripts/generate_sample_jobs.py
python src/ingestion/load_raw_jobs.py
python src/preprocessing/preprocess_db.py
python src/training/train_baseline.py
python src/inference/batch_inference.py
```

컨테이너 내부에서 실행할 경우:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python scripts/generate_sample_jobs.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/ingestion/load_raw_jobs.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/preprocessing/preprocess_db.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/training/train_baseline.py"
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

예시 요청:

```json
{
  "title": "데이터 엔지니어 채용",
  "description": "Python SQL Airflow Kafka Spark 기반 데이터 파이프라인 개발자를 찾습니다.",
  "job_post_id": null
}
```

예시 응답:

```json
{
  "job_category": "Data Engineer",
  "confidence": 0.91,
  "skills": ["Airflow", "Kafka", "Python", "Spark", "SQL"],
  "prediction_id": 1
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

라벨과 예측 결과 비교:

```sql
SELECT
    mp.id,
    cjp.title,
    cjp.job_category AS rule_label,
    mp.predicted_category,
    ROUND(mp.confidence::numeric, 4) AS confidence,
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

## Git 제외 대상

아래 파일과 디렉터리는 Git에 올리지 않습니다.

```text
.env
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
AIRFLOW__API_AUTH__JWT_SECRET: jobskill_airflow_jwt_secret_key_for_local_dev_please_change_1234567890
AIRFLOW__API__SECRET_KEY: jobskill_airflow_api_secret_key_for_local_dev_please_change_1234567890
```

확인:

```bash
docker compose exec airflow-scheduler airflow config get-value api_auth jwt_secret
docker compose exec airflow-apiserver airflow config get-value api_auth jwt_secret
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

## 현재 완료된 범위

```text
샘플 채용공고 데이터 생성
PostgreSQL raw/cleaned/skills 테이블 저장
TF-IDF + Logistic Regression 모델 학습
MLflow PostgreSQL backend store 연동
MLflow artifact 저장
FastAPI /predict API 구성
model_predictions 테이블 저장 구조 추가
batch inference 추가
Airflow 3.x Docker Compose 구성
Airflow execution API / JWT 설정 이슈 정리
```

## 다음 개선 예정

```text
docker-compose.yml 최종 정리 및 정상 기동 확인
Airflow DAG 전체 성공 검증
README 실행 스크린샷 추가
label_jobs.py 규칙 확장으로 Unknown 라벨 감소
FastAPI 예측 결과 품질 확인
실제 채용공고 크롤러 추가
데이터 품질 체크 task 추가
모델 성능 기준 기반 등록 로직 추가
Airflow DAG task를 PythonOperator 기반으로 개선 검토
```
