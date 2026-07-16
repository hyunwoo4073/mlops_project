# JobSkill API Not Ready

## 의미

FastAPI 프로세스는 실행 중이지만 실제 예측 요청을 받을 준비가 되지 않은 상태입니다.

`jobskill_api_ready` 지표가 0이면 아래 항목 중 하나가 실패한 상태입니다.

```text
PostgreSQL 연결 실패
PROMOTED model_registry 없음
promoted model file 없음
```

## 영향

API 컨테이너는 떠 있어도 `/predict` 요청이 실패하거나, 정상 모델로 예측하지 못할 수 있습니다.

이 alert는 `/metrics` scrape 실패와는 다릅니다.

```text
JobSkillApiMetricsDown
→ Prometheus가 FastAPI /metrics 자체를 scrape하지 못하는 상태

JobSkillApiNotReady
→ FastAPI는 떠 있지만 DB/model/model file readiness가 실패한 상태
```

## 확인 명령어

```bash
curl -fsS http://localhost:8000/health
curl -i http://localhost:8000/ready
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_api_ready|jobskill_api_database_ready|jobskill_api_promoted_model"
```

정상 기준:

```text
jobskill_api_ready 1
jobskill_api_database_ready 1
jobskill_api_promoted_model_ready 1
jobskill_api_promoted_model_file_exists 1
```

## DB 확인

```bash
docker compose exec postgres psql -U jobskill -d jobskill -c "
SELECT
    id,
    model_name,
    status,
    promoted_model_path,
    accuracy,
    f1_weighted,
    created_at
FROM model_registry
ORDER BY id DESC
LIMIT 10;
"
```

PROMOTED 모델만 확인하려면 아래 명령어를 사용합니다.

```bash
docker compose exec postgres psql -U jobskill -d jobskill -c "
SELECT
    id,
    model_name,
    status,
    promoted_model_path,
    accuracy,
    f1_weighted,
    created_at
FROM model_registry
WHERE status = 'PROMOTED'
ORDER BY id DESC
LIMIT 5;
"
```

## 모델 파일 확인

로컬 프로젝트 기준:

```bash
ls -l models/best/job_classifier.pkl
```

API 컨테이너 내부 기준:

```bash
docker compose exec api bash -lc "pwd && ls -l models/best/job_classifier.pkl"
```

만약 API 컨테이너의 작업 디렉터리가 `/app`이면 아래도 확인합니다.

```bash
docker compose exec api bash -lc "cd /app && ls -l models/best/job_classifier.pkl"
```

프로젝트가 `/opt/airflow/project`로 mount되어 있다면 아래도 확인합니다.

```bash
docker compose exec api bash -lc "cd /opt/airflow/project && ls -l models/best/job_classifier.pkl"
```

## 주요 원인

```text
PostgreSQL 컨테이너가 내려가 있음
model_registry에 PROMOTED 모델이 없음
promote_model task가 실패함
models/best/job_classifier.pkl 파일이 없음
API 컨테이너에 models 디렉터리가 mount되지 않음
promoted_model_path가 API 컨테이너 내부 경로와 맞지 않음
```

## 조치

### 1. PostgreSQL 상태 확인

```bash
docker compose ps postgres
docker compose logs --tail=100 postgres
```

PostgreSQL 접속 확인:

```bash
docker compose exec postgres pg_isready -U jobskill -d jobskill
```

### 2. PROMOTED 모델 존재 여부 확인

```bash
docker compose exec postgres psql -U jobskill -d jobskill -c "
SELECT
    id,
    model_name,
    status,
    promoted_model_path,
    created_at
FROM model_registry
WHERE status = 'PROMOTED'
ORDER BY id DESC
LIMIT 5;
"
```

PROMOTED 모델이 없으면 Airflow DAG를 실행합니다.

```bash
make dag-trigger
```

또는 필요한 최소 학습/승격 스크립트를 실행합니다.

```bash
docker compose exec airflow-scheduler bash -lc "
cd /opt/airflow/project &&
python src/training/train_baseline.py &&
python src/quality/check_model_performance.py &&
python src/training/promote_model.py
"
```

### 3. 모델 파일 확인

```bash
ls -l models/best/job_classifier.pkl
```

파일이 없으면 `promote_model` 단계가 정상적으로 완료됐는지 확인합니다.

```bash
docker compose logs --tail=100 airflow-scheduler
```

### 4. API 컨테이너 mount 확인

```bash
docker compose exec api bash -lc "
pwd
ls -l
ls -l models
ls -l models/best
"
```

`models/best/job_classifier.pkl`이 API 컨테이너 안에서 보이지 않으면 `docker-compose.yml`의 API volume mount를 확인합니다.

### 5. API 재기동

```bash
docker compose up -d --force-recreate api
```

### 6. readiness 재확인

```bash
curl -fsS http://localhost:8000/ready | jq
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_api_ready|jobskill_api_database_ready|jobskill_api_promoted_model"
```

## 정상 복구 기준

아래 값이 모두 1이면 정상입니다.

```text
jobskill_api_ready 1
jobskill_api_database_ready 1
jobskill_api_promoted_model_ready 1
jobskill_api_promoted_model_file_exists 1
```

Prometheus alert 상태도 확인합니다.

```text
http://localhost:9090/alerts
```

## 관련 화면

```text
FastAPI health
http://localhost:8000/health

FastAPI readiness
http://localhost:8000/ready

FastAPI metrics
http://localhost:8000/metrics

Prometheus alerts
http://localhost:9090/alerts

Streamlit dashboard
http://localhost:8501
```
