# jobskill-mlops Quick Start

이 문서는 로컬에서 JobSkill MLOps 프로젝트를 빠르게 실행하고, 모델 생성, API 호출, Production Feedback 평가, Prometheus/Alertmanager/Grafana 검증까지 따라 하기 위한 가이드입니다.

## 1. 사전 준비

필요 도구:

```text
Docker
Docker Compose
Python 3.12+
make
```

프로젝트 루트에서 실행합니다.

```bash
cd ~/jobskill-mlops
```

## 2. 환경 파일 준비

```bash
cp .env.example .env
```

Slack 알림을 테스트하지 않더라도 Alertmanager 설정에서 secret 파일 mount가 필요하므로 placeholder를 준비합니다.

```bash
mkdir -p .secrets
cp .secrets.example/slack_webhook_url.example .secrets/slack_webhook_url
```

## 3. 런타임 디렉터리 준비

```bash
mkdir -p data/raw data/processed models/best mlartifacts airflow_logs reports docs/images
touch simple_auth_manager_passwords.json
chmod -R 777 data models mlartifacts airflow_logs reports
```

## 4. 이미지 빌드

```bash
make build
```

또는 직접:

```bash
docker compose build airflow-image api
```

## 5. PostgreSQL 기동

```bash
docker compose up -d postgres
```

확인:

```bash
docker exec jobskill-postgres pg_isready -U jobskill -d jobskill
```

## 6. 프로젝트 테이블 생성

```bash
make create-tables
```

확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "\dt"
```

## 7. Airflow metadata DB 초기화

```bash
make airflow-init
```

## 8. 전체 서비스 기동

```bash
make up
```

상태 확인:

```bash
make ps
```

## 9. 주요 UI 접속

```text
Airflow     : http://localhost:8080
MLflow      : http://localhost:5000
FastAPI     : http://localhost:8000
Dashboard   : http://localhost:8501
Prometheus  : http://localhost:9090
Alertmanager: http://localhost:9093
Grafana     : http://localhost:3000
```

## 10. Airflow DAG 실행

DAG 목록 확인:

```bash
make dag-list
```

DAG task 확인:

```bash
make dag-tasks
```

DAG 실행:

```bash
make dag-trigger
```

DAG run 확인:

```bash
make dag-runs
```

## 11. 수동 최소 파이프라인 실행

Airflow DAG 대신 최소 흐름만 직접 실행할 경우:

```bash
docker compose exec -T airflow-scheduler bash -lc "
cd /opt/airflow/project &&

python src/ingestion/prepare_raw_sources.py &&
python scripts/generate_sample_jobs.py &&
python src/ingestion/load_raw_jobs.py &&
python src/preprocessing/preprocess_db.py &&

python src/quality/check_data_contract.py &&
python src/quality/check_training_data.py &&

python src/training/train_baseline.py &&
python src/quality/check_model_performance.py &&
python src/quality/check_model_class_performance.py &&
python src/training/promote_model.py &&

python src/reporting/generate_model_card.py &&
python src/inference/batch_inference.py &&
python src/quality/check_prediction_quality.py &&
python src/quality/check_prediction_drift.py &&
python src/reporting/generate_pipeline_report.py
"
```

## 12. API 확인

Health:

```bash
curl -fsS http://localhost:8000/health
```

Readiness:

```bash
curl -fsS http://localhost:8000/ready
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
    confidence
FROM model_predictions
ORDER BY id DESC
LIMIT 10;
"
```

## 13. Production Feedback 평가

샘플 feedback 생성:

```bash
make production-feedback-sample
```

오답 비율을 높여 alert 시나리오를 만들고 싶으면:

```bash
LIMIT=30 WRONG_EVERY=2 make production-feedback-sample
```

feedback row 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    pf.id,
    pf.prediction_id,
    mp.predicted_category,
    pf.actual_category,
    CASE
        WHEN mp.predicted_category = pf.actual_category THEN 'CORRECT'
        ELSE 'WRONG'
    END AS result,
    pf.feedback_source,
    pf.updated_at
FROM prediction_feedbacks pf
JOIN model_predictions mp
    ON pf.prediction_id = mp.id
ORDER BY pf.updated_at DESC
LIMIT 20;
"
```

Production feedback 성능 평가:

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

## 14. Metrics 확인

FastAPI metrics:

```bash
make metrics
```

Production feedback metrics:

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_production_feedback"
```

예상 metric:

```text
jobskill_production_feedback_total
jobskill_production_feedback_accuracy
jobskill_production_feedback_f1_weighted
jobskill_production_feedback_category_total
```

## 15. Prometheus / Alertmanager / Grafana 검증

Prometheus config:

```bash
make prometheus-check
```

Prometheus rule unit test:

```bash
make prometheus-rule-test
```

Alertmanager config:

```bash
make alertmanager-check
```

Grafana health:

```bash
curl -fsS http://localhost:3000/api/health
```

Production feedback alert rule 확인:

```bash
curl -fsS http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.name | startswith("JobSkillProductionFeedback"))'
```

Alert 확인:

```bash
curl -fsS "http://localhost:9090/api/v1/alerts" | jq '.data.alerts[] | select(.labels.alertname | startswith("JobSkillProductionFeedback"))'
```

## 16. 운영 검증 명령어

정적 운영 검증:

```bash
make ops-static-check
```

Full smoke check:

```bash
make smoke
```

통합 운영 검증:

```bash
make ops-check
```

개별 검증:

```bash
make runbook-check
make metrics-contract-check
make alert-rule-metric-check
make prometheus-external-target-check
make compose-config-check
make repo-artifact-check
```

## 17. Runbook 확인

Runbook 목록:

```bash
curl -fsS http://localhost:8000/runbooks
```

Production feedback runbook:

```text
http://localhost:8000/runbooks/jobskill_production_feedback_low_accuracy.md
```

Raw markdown:

```text
http://localhost:8000/runbooks/jobskill_production_feedback_low_accuracy.md/raw
```

## 18. 자주 쓰는 Makefile 명령어

```bash
make help

make build
make up
make down
make restart
make ps
make logs

make create-tables
make airflow-init
make dag-trigger
make dag-runs

make api-sample
make production-feedback-sample
make production-feedback-check

make metrics
make smoke
make ops-static-check
make ops-check
```

## 19. 종료

서비스 중지:

```bash
make down
```

로컬 런타임 산출물 정리:

```bash
make clean-runtime
```

Docker volume까지 초기화해야 하는 경우:

```bash
docker compose down -v
```

주의: `down -v`는 PostgreSQL 데이터도 삭제합니다. 이후 다시 `make create-tables`, `make airflow-init`, 파이프라인 실행이 필요합니다.
