# jobskill-mlops Quick Start

이 문서는 로컬 Docker Compose 환경에서 `jobskill-mlops`를 실행하고, 오늘 추가한 Feedback Ops / Retraining Candidate / Alert Rule 검증까지 확인하는 순서입니다.

## 1. 환경 파일 준비

```bash
cp .env.example .env
```

Feedback Ops DAG 관련 값이 `.env`에 있는지 확인합니다.

```env
FEEDBACK_OPS_DAG_SCHEDULE="0 9 * * *"

PRODUCTION_FEEDBACK_STRICT=false
RETRAINING_CANDIDATE_STRICT=false

MIN_PRODUCTION_FEEDBACK_ROWS=10
MIN_PRODUCTION_ACCURACY=0.70
MIN_PRODUCTION_F1_WEIGHTED=0.70
PRODUCTION_FEEDBACK_WINDOW_DAYS=30

PRODUCTION_FEEDBACK_TREND_DROP_THRESHOLD=0.05
PRODUCTION_FEEDBACK_MIN_HISTORY_POINTS=3
```

수동 실행만 원하면 아래처럼 변경합니다.

```env
FEEDBACK_OPS_DAG_SCHEDULE=manual
```

## 2. 서비스 빌드/기동

```bash
make build
make up
```

상태 확인:

```bash
docker compose ps
```

주요 URL:

```text
FastAPI             http://localhost:8000
FastAPI Docs        http://localhost:8000/docs
Streamlit Dashboard http://localhost:8501
MLflow              http://localhost:5000
Prometheus          http://localhost:9090
Alertmanager        http://localhost:9093
Grafana             http://localhost:3000
```

## 3. DB 테이블 생성

```bash
make create-tables
```

DB 접속 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "SELECT 1;"
```

## 4. Airflow DAG 확인

메인 DAG:

```bash
make dag-list
make dag-tasks
```

Feedback Ops DAG:

```bash
make feedback-ops-dag-tasks
```

직접 확인:

```bash
docker compose exec -T airflow-scheduler airflow dags list | grep jobskill_feedback_ops
docker compose exec -T airflow-scheduler airflow tasks list jobskill_feedback_ops
```

기대 task:

```text
show_feedback_ops_config
check_production_feedback
check_retraining_candidate
```

## 5. 메인 파이프라인 실행

```bash
make dag-trigger
```

실행 이력 확인:

```bash
docker compose exec -T airflow-scheduler airflow dags list-runs jobskill_mlops_pipeline
```

## 6. FastAPI 확인

```bash
curl -fsS http://localhost:8000/health | jq
curl -fsS http://localhost:8000/ready | jq
curl -fsS http://localhost:8000/model | jq
```

샘플 요청:

```bash
make api-sample
```

API 컨테이너가 DB를 resolve하는지 확인:

```bash
docker compose exec -T api getent hosts postgres
```

로컬 컨테이너 재기동 후 `/predict`에서 DB 연결 오류가 나면 API만 재기동합니다.

```bash
docker compose up -d --force-recreate api
```

## 7. Production Feedback 생성/평가

샘플 production feedback 생성:

```bash
make production-feedback-sample
```

오답 feedback을 더 많이 만들어 alert 조건을 테스트하려면:

```bash
LIMIT=30 WRONG_EVERY=2 make production-feedback-sample
```

Production Feedback 평가:

```bash
make production-feedback-check
```

평가 결과 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    check_type,
    check_name,
    status,
    metric_value,
    threshold_value,
    message,
    checked_at
FROM pipeline_check_results
WHERE check_type = 'PRODUCTION_FEEDBACK'
ORDER BY checked_at DESC
LIMIT 20;
"
```

## 8. Retraining Candidate 평가

```bash
make retraining-candidate-check
```

결과 확인:

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

Metric 확인:

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_retraining_candidate"
```

## 9. Feedback Ops DAG 실행

수동 trigger:

```bash
make feedback-ops-dag-trigger
```

또는 직접 실행:

```bash
docker compose exec -T airflow-scheduler airflow dags trigger jobskill_feedback_ops
```

실행 결과 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    check_type,
    check_name,
    status,
    metric_value,
    threshold_value,
    dag_id,
    task_id,
    run_id,
    checked_at
FROM pipeline_check_results
WHERE check_type IN ('PRODUCTION_FEEDBACK', 'RETRAINING_CANDIDATE')
ORDER BY checked_at DESC
LIMIT 30;
"
```

기대값:

```text
dag_id = jobskill_feedback_ops
task_id = check_production_feedback
task_id = check_retraining_candidate
```

## 10. Prometheus / Alert Rule 검증

```bash
make prometheus-check
make prometheus-rule-test
make alert-rule-metric-check
make runbook-check
```

전체 static ops validation:

```bash
make ops-static-check
```

전체 smoke check:

```bash
make smoke
```

## 11. Alert current state 확인

현재 firing alert 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    id,
    alert_name,
    service,
    severity,
    status,
    starts_at,
    last_received_at,
    fingerprint,
    ROUND(EXTRACT(EPOCH FROM (NOW() - starts_at)) / 60, 2) AS firing_minutes
FROM alert_current_states
WHERE status = 'firing'
ORDER BY starts_at ASC;
"
```

`SmokeTestAlert`가 오래된 firing 상태로 남아 있으면 로컬 테스트 데이터 정리:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
DELETE FROM alert_current_states
WHERE fingerprint = 'smoke-test-fingerprint'
   OR service = 'smoke-test'
   OR alert_name = 'SmokeTestAlert';

DELETE FROM alert_events
WHERE fingerprint = 'smoke-test-fingerprint'
   OR service = 'smoke-test'
   OR alert_name = 'SmokeTestAlert';

DELETE FROM alert_current_states
WHERE alert_name IN (
    'JobSkillUnacknowledgedCurrentAlert',
    'JobSkillHighAverageMTTA',
    'JobSkillHighAverageMTTR'
);
"
```

정리 후 확인:

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_alert_unacknowledged_current_total|jobskill_alert_avg_mtta_minutes|jobskill_alert_avg_mttr_minutes"
```

## 12. 최종 검증 세트

오늘 작업 기준 최종 검증은 아래 순서로 실행합니다.

```bash
python -m py_compile src/quality/check_retraining_candidate.py
python -m py_compile dags/jobskill_feedback_ops_dag.py
python -m py_compile src/monitoring/prometheus_metrics.py
python -m py_compile src/dashboard/app.py

make ops-static-check
make production-feedback-sample
make production-feedback-check
make retraining-candidate-check
make feedback-ops-dag-tasks
make prometheus-check
make prometheus-rule-test
make alert-rule-metric-check
make runbook-check
make smoke
```

## 13. 종료

```bash
make down
```

volume까지 제거해야 하는 초기화 상황이 아니면 `docker compose down -v`는 사용하지 않습니다.
