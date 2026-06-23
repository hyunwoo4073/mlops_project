# jobskill-mlops project

채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow와 MLflow를 이용해 데이터 수집부터 전처리, 학습, 실험 기록까지 연결하는 경량 MLOps 파이프라인 프로젝트입니다.

## 프로젝트 목표

이 프로젝트는 채용공고 데이터를 사용해 아래 흐름을 구성하는 것을 목표로 합니다.

```text
샘플 채용공고 데이터 생성
→ PostgreSQL raw 테이블 적재
→ 전처리 및 기술스택 추출
→ PostgreSQL cleaned/skills 테이블 저장
→ TF-IDF + Logistic Regression 모델 학습
→ MLflow 실험 기록
→ 모델 artifact 저장
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
│   └── jobskill_mlops_pipeline DAG 실행
└── MLflow
    ├── backend store  : PostgreSQL mlflow DB
    └── artifact store : ./mlartifacts
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
│       └── api.py
├── data/
│   ├── raw/
│   └── processed/
├── models/
├── mlartifacts/
└── notebooks/
```

> `data/`, `models/`, `mlartifacts/`, `.env`, `simple_auth_manager_passwords.json` 등은 로컬 실행 중 생성되는 산출물이므로 Git에는 포함하지 않습니다.

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

### 5. Airflow DAG

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
```

DAG 이름:

```text
jobskill_mlops_pipeline
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

## 실행 방법

### 1. 필요한 디렉터리 생성

```bash
mkdir -p data/raw data/processed models mlartifacts airflow_logs
```

### 2. Airflow 이미지 빌드

```bash
docker compose build airflow-image
```

### 3. PostgreSQL 실행

```bash
docker compose up -d postgres
```

### 4. DB 생성 확인 또는 생성

PostgreSQL volume이 이미 존재하는 경우 init SQL이 다시 실행되지 않을 수 있습니다.
그 경우 아래 명령으로 직접 DB를 생성합니다.

```bash
docker exec -it jobskill-postgres psql -U jobskill -d jobskill -c "CREATE DATABASE airflow;"
docker exec -it jobskill-postgres psql -U jobskill -d jobskill -c "CREATE DATABASE mlflow;"
```

이미 존재한다는 에러가 나오면 무시해도 됩니다.

### 5. 프로젝트 테이블 생성

```bash
docker exec -i jobskill-postgres psql -U jobskill -d jobskill < sql/create_tables.sql
```

### 6. Airflow 메타DB 초기화

```bash
docker compose up --no-build airflow-init
```

### 7. 전체 서비스 실행

```bash
docker compose up -d --no-build airflow-apiserver airflow-scheduler airflow-dag-processor airflow-triggerer mlflow
```

### 8. 컨테이너 상태 확인

```bash
docker compose ps
```

## 접속 정보

### Airflow UI

```text
http://localhost:8080
```

### MLflow UI

```text
http://localhost:5000
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

### DAG 테스트 실행

```bash
docker compose exec airflow-scheduler airflow dags test jobskill_mlops_pipeline 2026-06-22
```

## 로컬 Python 스크립트 실행 순서

Airflow 없이 개별 스크립트로 실행할 수도 있습니다.

```bash
python scripts/generate_sample_jobs.py
python src/ingestion/load_raw_jobs.py
python src/preprocessing/preprocess_db.py
python src/training/train_baseline.py
```

단, 로컬에서 실행하는 경우 `.env`의 `DB_HOST`는 `localhost`로 바꿔야 합니다.

```env
DB_HOST=localhost
```

Docker 컨테이너 내부에서 실행하는 경우에는 `postgres`를 사용합니다.

```env
DB_HOST=postgres
```

## FastAPI 실행

모델 학습 후 추론 API를 실행할 수 있습니다.

```bash
uvicorn src.inference.api:app --host 0.0.0.0 --port 8000 --reload
```

API 문서:

```text
http://localhost:8000/docs
```

예시 요청:

```json
{
  "title": "데이터 엔지니어 채용",
  "description": "Python SQL Airflow Kafka Spark 기반 데이터 파이프라인 개발자를 찾습니다."
}
```

예시 응답:

```json
{
  "job_category": "Data Engineer",
  "confidence": 0.91,
  "skills": ["Airflow", "Kafka", "Python", "Spark", "SQL"]
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

## 권한 문제 해결

Airflow task가 `data/raw/sample_jobs.csv` 또는 `models/`에 쓰지 못하는 경우 아래 명령을 실행합니다.

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

## 현재 완료된 범위

```text
샘플 채용공고 데이터 생성
PostgreSQL raw/cleaned/skills 테이블 저장
TF-IDF + Logistic Regression 모델 학습
MLflow PostgreSQL backend store 연동
MLflow artifact 저장
Airflow 3.x Docker Compose 구성
Airflow DAG 기반 파이프라인 실행
```

## 다음 개선 예정

```text
실제 채용공고 크롤러 추가
FastAPI 예측 결과를 model_predictions 테이블에 저장
Airflow DAG task를 PythonOperator 기반으로 개선
데이터 품질 체크 추가
모델 성능 기준 기반 등록 로직 추가
README 실행 스크린샷 추가
```
