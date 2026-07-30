# jobskill-mlops 요약

## 프로젝트 목적

`jobskill-mlops`는 채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, 모델 학습 이후 운영 품질 검증까지 연결하는 end-to-end MLOps 프로젝트입니다.

핵심 목표는 아래 흐름을 로컬 Docker Compose 환경에서 재현하는 것입니다.

```text
데이터 수집/생성
→ PostgreSQL 적재
→ 전처리
→ 데이터 계약 검증
→ 모델 학습
→ MLflow 기록
→ 모델 성능 검증
→ 모델 승격
→ batch/API inference
→ production feedback 수집
→ 운영 성능 평가
→ 재학습 후보 판단
→ Prometheus metric/alert
→ runbook 기반 대응
```

## 핵심 구성

```text
Workflow        : Apache Airflow 3.x
Database        : PostgreSQL
ML Lifecycle    : MLflow
Model           : scikit-learn TF-IDF + Logistic Regression
Serving         : FastAPI
Dashboard       : Streamlit, Grafana
Monitoring      : Prometheus
Alerting        : Alertmanager, Slack webhook
Validation      : Makefile, smoke check, rule test, metrics contract, runbook check
```

## 오늘 추가된 운영 개선

### 1. Retraining Candidate 자동화

Production Feedback 기반 재학습 후보 판단을 CLI/Smoke Check/Airflow/Metric 흐름에 연결했습니다.

```text
src/quality/check_retraining_candidate.py
→ Makefile retraining-candidate-check
→ smoke check
→ pipeline_check_results
→ FastAPI /metrics
→ Prometheus alert
```

주요 metric:

```text
jobskill_retraining_candidate_flag
jobskill_retraining_candidate_feedback_count
jobskill_retraining_candidate_accuracy
jobskill_retraining_candidate_f1_weighted
jobskill_retraining_candidate_accuracy_delta
jobskill_retraining_candidate_f1_delta
```

### 2. Feedback Ops Airflow DAG

메인 학습 DAG와 별도로 운영 품질 점검 DAG를 추가했습니다.

```text
dags/jobskill_feedback_ops_dag.py
```

DAG 흐름:

```text
show_feedback_ops_config
    ↓
check_production_feedback
    ↓
check_retraining_candidate
```

운영 의미:

```text
jobskill_mlops_pipeline
- 모델 생성/검증/승격 중심

jobskill_feedback_ops
- 운영 feedback 평가/재학습 후보 판단 중심
```

### 3. Schedule / threshold 환경변수화

Feedback Ops DAG는 기본 daily schedule이지만, 환경변수로 수동 모드 전환이 가능합니다.

```env
FEEDBACK_OPS_DAG_SCHEDULE="0 9 * * *"
```

수동 모드:

```env
FEEDBACK_OPS_DAG_SCHEDULE=manual
```

주요 threshold:

```text
MIN_PRODUCTION_FEEDBACK_ROWS=10
MIN_PRODUCTION_ACCURACY=0.70
MIN_PRODUCTION_F1_WEIGHTED=0.70
PRODUCTION_FEEDBACK_TREND_DROP_THRESHOLD=0.05
PRODUCTION_FEEDBACK_MIN_HISTORY_POINTS=3
```

### 4. Prometheus alert rule/test 정리

Production Feedback / Retraining Candidate alert에 maintenance mode 조건을 맞췄습니다.

```text
jobskill_alert_maintenance_mode == 0
```

Streamlit에서 확인해야 하는 model-quality 계열 alert의 `dashboard_url`은 아래로 정리했습니다.

```text
http://localhost:8501
```

추가/정리한 test:

```text
production_feedback_low_accuracy_should_fire
production_feedback_low_accuracy_should_be_suppressed_during_maintenance
production_feedback_low_f1_should_fire
production_feedback_low_f1_should_be_suppressed_during_maintenance
retraining_candidate_detected_should_fire
retraining_candidate_should_be_suppressed_during_maintenance
```

### 5. Alert response metric 트러블슈팅

로컬 smoke test에서 생성된 `SmokeTestAlert`가 오래된 firing 상태로 남으면 아래 alert를 유발할 수 있음을 확인했습니다.

```text
JobSkillUnacknowledgedCurrentAlert
JobSkillHighAverageMTTA
JobSkillHighAverageMTTR
```

확인 쿼리:

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

로컬 테스트 데이터 정리:

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

## 검증 명령어

```bash
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

## 포트폴리오 관점 핵심 메시지

이 프로젝트는 단순 ML 학습 코드가 아니라, 운영 중 모델 품질을 feedback 기반으로 다시 평가하고, 재학습 후보 판단까지 자동화하는 MLOps 운영 흐름을 구현합니다.

```text
배포 이후 예측
→ 실제 feedback 수집
→ 운영 성능 재평가
→ 재학습 후보 판단
→ metric/alert/runbook 연결
```

이 흐름이 오늘 작업으로 CLI, Dashboard, Airflow, Prometheus, Smoke Check까지 연결되었습니다.
