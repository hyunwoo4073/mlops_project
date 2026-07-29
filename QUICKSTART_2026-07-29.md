# JobSkill MLOps Quick Start

이 문서는 로컬에서 `jobskill-mlops`를 빠르게 실행하고, DAG/API/Monitoring/Production Feedback/Retraining Candidate 흐름까지 검증하기 위한 가이드입니다.

## 1. 환경 준비

```bash
cp .env.example .env
mkdir -p .secrets
cp .secrets.example/slack_webhook_url.example .secrets/slack_webhook_url
```

Slack 알림을 실제로 받을 경우 `.secrets/slack_webhook_url`에 실제 Slack Incoming Webhook URL을 입력합니다.

테스트만 할 경우 placeholder 상태로 두어도 됩니다.

## 2. 서비스 기동

PostgreSQL 먼저 기동합니다.

```bash
docker compose up -d postgres
```

DB와 테이블을 생성합니다.

```bash
make create-tables
```

주요 서비스를 기동합니다.

```bash
docker compose up -d   airflow-apiserver   airflow-scheduler   airflow-dag-processor   airflow-triggerer   mlflow   api   dashboard   prometheus   alertmanager   grafana
```

상태 확인:

```bash
docker compose ps
```

## 3. 접속 URL

```text
Airflow      : http://localhost:8080
MLflow       : http://localhost:5000
FastAPI      : http://localhost:8000
Streamlit    : http://localhost:8501
Prometheus   : http://localhost:9090
Alertmanager : http://localhost:9093
Grafana      : http://localhost:3000
```

## 4. 기본 파이프라인 실행

Airflow DAG 실행:

```bash
make dag-trigger
```

DAG task 확인:

```bash
docker compose exec -T airflow-scheduler airflow tasks list jobskill_mlops_pipeline
```

## 5. API 확인

Health:

```bash
curl -fsS http://localhost:8000/health | jq
```

Readiness:

```bash
curl -fsS http://localhost:8000/ready | jq
```

Model info:

```bash
curl -fsS http://localhost:8000/model | jq
```

샘플 API 요청:

```bash
make api-sample
```

API prediction row 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    id,
    prediction_source,
    predicted_category,
    confidence,
    predicted_at
FROM model_predictions
ORDER BY id DESC
LIMIT 10;
"
```

## 6. Production Feedback 실행

샘플 feedback 생성:

```bash
make production-feedback-sample
```

오답 feedback을 더 많이 만들고 싶으면:

```bash
LIMIT=30 WRONG_EVERY=2 make production-feedback-sample
```

Production feedback 평가:

```bash
make production-feedback-check
```

평가 결과 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    check_name,
    status,
    metric_value,
    threshold_value,
    message,
    checked_at
FROM pipeline_check_results
WHERE check_type = 'PRODUCTION_FEEDBACK'
ORDER BY checked_at DESC
LIMIT 10;
"
```

metric 확인:

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_production_feedback"
```

## 7. Dashboard에서 Production Feedback 확인

Streamlit 접속:

```text
http://localhost:8501
```

이동:

```text
Production Feedback
```

확인할 하위 탭:

```text
Feedback Input
Evaluation Runner
Evaluation History
Retraining Candidate
Recent Feedback
Wrong Predictions
Confusion Table
Feedback Source
Evaluation Checks
```

Dashboard에서 직접 할 수 있는 작업:

```text
1. 최근 prediction 선택
2. actual_category feedback 저장
3. production feedback 평가 실행
4. accuracy / weighted F1 추세 확인
5. retraining candidate 여부 판단
6. 판단 결과 저장
```

## 8. Retraining Candidate 확인

Dashboard에서 판단 결과 저장:

```text
Production Feedback
→ Retraining Candidate
→ Save retraining candidate decision
```

DB 저장 결과 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    check_type,
    check_name,
    status,
    metric_value,
    threshold_value,
    message,
    dag_id,
    task_id,
    run_id,
    checked_at
FROM pipeline_check_results
WHERE check_type = 'RETRAINING_CANDIDATE'
ORDER BY checked_at DESC
LIMIT 30;
"
```

metric 확인:

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_retraining_candidate"
```

예상 metric:

```text
jobskill_retraining_candidate_flag
jobskill_retraining_candidate_feedback_count
jobskill_retraining_candidate_accuracy
jobskill_retraining_candidate_f1_weighted
jobskill_retraining_candidate_accuracy_delta
jobskill_retraining_candidate_f1_delta
```

## 9. Prometheus / Alert 검증

Prometheus config 검증:

```bash
make prometheus-check
```

Prometheus alert rule unit test:

```bash
make prometheus-rule-test
```

Runbook coverage:

```bash
make runbook-check
```

Alert rule metric dependency:

```bash
make alert-rule-metric-check
```

Metrics contract:

```bash
make metrics-contract-check
```

Static ops validation:

```bash
make ops-static-check
```

## 10. 전체 Smoke Check

```bash
make smoke
```

Smoke check는 주요 서비스와 운영 경로를 검증합니다.

```text
Docker Compose config
PostgreSQL connection
Project tables
Airflow DAG import / task list
MLflow UI
FastAPI health / ready / model / metrics
API sample prediction
Production feedback sample / evaluation / metrics
Prometheus readiness
Alertmanager readiness
Alert webhook 저장
Grafana health
Streamlit dashboard
```

## 11. 자주 확인하는 명령어

컨테이너 상태:

```bash
docker compose ps
```

API 로그:

```bash
docker compose logs --tail=100 api
```

Dashboard 로그:

```bash
docker compose logs --tail=100 dashboard
```

Prometheus metric 확인:

```bash
curl -fsS http://localhost:8000/metrics | head
```

Alert 목록:

```bash
curl -fsS "http://localhost:9090/api/v1/alerts" | jq
```

Alertmanager alert 목록:

```bash
curl -fsS http://localhost:9093/api/v2/alerts | jq
```

## 12. 마무리 검증 세트

작업 후 아래 명령어를 순서대로 실행합니다.

```bash
python -m py_compile src/dashboard/app.py
python -m py_compile src/monitoring/prometheus_metrics.py
make metrics-contract-check
make prometheus-check
make prometheus-rule-test
make runbook-check
make alert-rule-metric-check
make ops-static-check
make smoke
```
