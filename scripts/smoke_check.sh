#!/usr/bin/env bash

set -euo pipefail

COMPOSE="${COMPOSE:-docker compose}"
PROJECT_DIR="${PROJECT_DIR:-/opt/airflow/project}"
AIRFLOW_SERVICE="${AIRFLOW_SERVICE:-airflow-scheduler}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-jobskill-postgres}"
POSTGRES_USER="${POSTGRES_USER:-jobskill}"
POSTGRES_DB="${POSTGRES_DB:-jobskill}"
PIPELINE_DAG_ID="${PIPELINE_DAG_ID:-jobskill_mlops_pipeline}"
FEEDBACK_OPS_DAG_ID="${FEEDBACK_OPS_DAG_ID:-jobskill_feedback_ops}"
API_URL="${API_URL:-http://localhost:8000}"
MLFLOW_URL="${MLFLOW_URL:-http://localhost:5000}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:9093}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:8501}"

PSQL="docker exec ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}"
AIRFLOW_PROJECT="${COMPOSE} exec -T ${AIRFLOW_SERVICE} bash -lc"

print_header() {
  echo ""
  echo "========================================"
  echo " JobSkill MLOps Smoke Check"
  echo "========================================"
  echo ""
}

print_group() {
  echo ""
  echo "########################################"
  echo "# $1"
  echo "########################################"
}

print_related_logs() {
  local name="$1"

  echo ""
  echo "[DEBUG] Related container logs"
  echo "----------------------------------------"

  if [[ "$name" == *"FastAPI"* || "$name" == *"API"* || "$name" == *"Readiness"* || "$name" == *"Prediction"* ]]; then
    ${COMPOSE} logs --tail=100 api || true
  fi

  if [[ "$name" == *"Streamlit"* || "$name" == *"Dashboard"* ]]; then
    ${COMPOSE} logs --tail=100 dashboard || true
  fi

  if [[ "$name" == *"Prometheus"* ]]; then
    ${COMPOSE} logs --tail=100 prometheus || true
  fi

  if [[ "$name" == *"Alertmanager"* || "$name" == *"Alert"* || "$name" == *"Synthetic"* ]]; then
    ${COMPOSE} logs --tail=100 alertmanager || true
    ${COMPOSE} logs --tail=100 api || true
  fi

  if [[ "$name" == *"Grafana"* ]]; then
    ${COMPOSE} logs --tail=100 grafana || true
  fi

  if [[ "$name" == *"MLflow"* ]]; then
    ${COMPOSE} logs --tail=100 mlflow || true
  fi

  if [[ "$name" == *"Airflow"* || "$name" == *"DAG"* ]]; then
    ${COMPOSE} logs --tail=100 airflow-scheduler || true
    ${COMPOSE} logs --tail=100 airflow-apiserver || true
    ${COMPOSE} logs --tail=100 airflow-dag-processor || true
  fi

  if [[ "$name" == *"PostgreSQL"* || "$name" == *"Project tables"* || "$name" == *"Core table"* || "$name" == *"feedback"* || "$name" == *"Retraining"* ]]; then
    ${COMPOSE} logs --tail=100 postgres || true
  fi
}

check_command() {
  local name="$1"
  local command="$2"

  echo ""
  echo "[CHECK] $name"
  echo "----------------------------------------"

  if bash -lc "$command"; then
    echo "[PASS] $name"
  else
    echo "[FAIL] $name"
    print_related_logs "$name"
    exit 1
  fi
}

check_http() {
  local name="$1"
  local url="$2"

  echo ""
  echo "[CHECK] $name"
  echo "----------------------------------------"
  echo "URL: $url"

  if curl -fsS "$url" > /tmp/jobskill_smoke_response.txt; then
    echo "[PASS] $name"
    head -c 500 /tmp/jobskill_smoke_response.txt || true
    echo ""
  else
    echo "[FAIL] $name"
    print_related_logs "$name"
    exit 1
  fi
}

print_header

print_group "Compose / Container Baseline"

check_command \
  "Docker Compose config" \
  "${COMPOSE} config > /tmp/jobskill_compose_config.yml"

check_command \
  "Container status" \
  "${COMPOSE} ps"

print_group "PostgreSQL / Project Schema"

check_command \
  "PostgreSQL connection" \
  "${PSQL} -c 'SELECT 1;'"

check_command \
  "API container can resolve PostgreSQL service" \
  "${COMPOSE} exec -T api getent hosts postgres"

check_command \
  "Project tables" \
  "${PSQL} -tAc \"
    WITH required_tables(table_name) AS (
      VALUES
        ('raw_job_posts'),
        ('cleaned_job_posts'),
        ('job_post_skills'),
        ('model_predictions'),
        ('prediction_feedbacks'),
        ('api_prediction_logs'),
        ('pipeline_check_results'),
        ('model_registry'),
        ('alert_events'),
        ('alert_current_states')
    ),
    missing_tables AS (
      SELECT rt.table_name
      FROM required_tables rt
      LEFT JOIN information_schema.tables it
        ON it.table_schema = 'public'
       AND it.table_name = rt.table_name
      WHERE it.table_name IS NULL
    )
    SELECT CASE
      WHEN COUNT(*) = 0 THEN 'OK'
      ELSE 'MISSING: ' || string_agg(table_name, ', ')
    END
    FROM missing_tables;
  \" | grep -q '^OK$'"

check_command \
  "Core table counts" \
  "${PSQL} -c \"
    SELECT 'raw_job_posts' AS table_name, COUNT(*) FROM raw_job_posts
    UNION ALL
    SELECT 'cleaned_job_posts', COUNT(*) FROM cleaned_job_posts
    UNION ALL
    SELECT 'job_post_skills', COUNT(*) FROM job_post_skills
    UNION ALL
    SELECT 'model_predictions', COUNT(*) FROM model_predictions
    UNION ALL
    SELECT 'prediction_feedbacks', COUNT(*) FROM prediction_feedbacks
    UNION ALL
    SELECT 'api_prediction_logs', COUNT(*) FROM api_prediction_logs
    UNION ALL
    SELECT 'pipeline_check_results', COUNT(*) FROM pipeline_check_results
    UNION ALL
    SELECT 'model_registry', COUNT(*) FROM model_registry
    UNION ALL
    SELECT 'alert_events', COUNT(*) FROM alert_events
    UNION ALL
    SELECT 'alert_current_states', COUNT(*) FROM alert_current_states;
  \""

print_group "Airflow DAGs"

check_command \
  "Airflow DAG import errors" \
  "${COMPOSE} exec -T ${AIRFLOW_SERVICE} airflow dags list-import-errors"

check_command \
  "Airflow pipeline tasks" \
  "${COMPOSE} exec -T ${AIRFLOW_SERVICE} airflow tasks list ${PIPELINE_DAG_ID}"

check_command \
  "Airflow feedback ops tasks" \
  "${COMPOSE} exec -T ${AIRFLOW_SERVICE} airflow tasks list ${FEEDBACK_OPS_DAG_ID} > /tmp/jobskill_feedback_ops_tasks.txt && \
   grep -q show_feedback_ops_config /tmp/jobskill_feedback_ops_tasks.txt && \
   grep -q check_production_feedback /tmp/jobskill_feedback_ops_tasks.txt && \
   grep -q check_retraining_candidate /tmp/jobskill_feedback_ops_tasks.txt"

print_group "Application Endpoints"

check_http \
  "MLflow UI" \
  "${MLFLOW_URL}"

check_http \
  "FastAPI root" \
  "${API_URL}/"

check_http \
  "FastAPI health" \
  "${API_URL}/health"

check_http \
  "FastAPI readiness" \
  "${API_URL}/ready"

check_http \
  "FastAPI model info" \
  "${API_URL}/model"

check_http \
  "FastAPI metrics" \
  "${API_URL}/metrics"

check_command \
  "FastAPI metrics content" \
  "curl -fsS ${API_URL}/metrics > /tmp/jobskill_metrics.txt && \
   grep -q jobskill_model_predictions_total /tmp/jobskill_metrics.txt && \
   grep -q jobskill_production_feedback_total /tmp/jobskill_metrics.txt && \
   grep -q jobskill_production_feedback_accuracy /tmp/jobskill_metrics.txt && \
   grep -q jobskill_production_feedback_f1_weighted /tmp/jobskill_metrics.txt && \
   grep -q jobskill_retraining_candidate_flag /tmp/jobskill_metrics.txt && \
   grep -q jobskill_retraining_candidate_feedback_count /tmp/jobskill_metrics.txt && \
   grep -q jobskill_retraining_candidate_accuracy /tmp/jobskill_metrics.txt && \
   grep -q jobskill_retraining_candidate_f1_weighted /tmp/jobskill_metrics.txt && \
   grep -q jobskill_retraining_candidate_accuracy_delta /tmp/jobskill_metrics.txt && \
   grep -q jobskill_retraining_candidate_f1_delta /tmp/jobskill_metrics.txt && \
   grep -q jobskill_alert_current_states_total /tmp/jobskill_metrics.txt && \
   grep -q jobskill_alert_avg_mtta_minutes /tmp/jobskill_metrics.txt && \
   grep -q jobskill_alert_avg_mttr_minutes /tmp/jobskill_metrics.txt && \
   grep -q jobskill_alert_unacknowledged_current_total /tmp/jobskill_metrics.txt"

print_group "API Prediction Path"

check_command \
  "FastAPI sample prediction requests" \
  "python scripts/send_sample_api_requests.py"

check_command \
  "API prediction logs" \
  "${PSQL} -tAc \"
    SELECT CASE
      WHEN COUNT(*) > 0 THEN 'OK'
      ELSE 'FAIL'
    END
    FROM api_prediction_logs
    WHERE status = 'SUCCESS';
  \" | grep -q OK"

check_command \
  "API prediction rows" \
  "${PSQL} -tAc \"
    SELECT CASE
      WHEN COUNT(*) > 0 THEN 'OK'
      ELSE 'FAIL'
    END
    FROM model_predictions
    WHERE prediction_source = 'API';
  \" | grep -q OK"

print_group "Production Feedback / Retraining"

check_command \
  "Create sample production feedback" \
  "${AIRFLOW_PROJECT} \"cd ${PROJECT_DIR} && python scripts/create_sample_prediction_feedback.py --limit 30 --wrong-every 5\""

check_command \
  "Prediction feedback rows" \
  "${PSQL} -tAc \"
    SELECT CASE
      WHEN COUNT(*) > 0 THEN 'OK'
      ELSE 'FAIL'
    END
    FROM prediction_feedbacks;
  \" | grep -q OK"

check_command \
  "Production feedback evaluation" \
  "${AIRFLOW_PROJECT} \"cd ${PROJECT_DIR} && python src/quality/check_production_feedback.py\""

check_command \
  "Production feedback check results" \
  "${PSQL} -tAc \"
    SELECT CASE
      WHEN COUNT(*) > 0 THEN 'OK'
      ELSE 'FAIL'
    END
    FROM pipeline_check_results
    WHERE check_type = 'PRODUCTION_FEEDBACK';
  \" | grep -q OK"

check_command \
  "Retraining candidate evaluation" \
  "${AIRFLOW_PROJECT} \"cd ${PROJECT_DIR} && python src/quality/check_retraining_candidate.py\""

check_command \
  "Retraining candidate check results" \
  "${PSQL} -tAc \"
    SELECT CASE
      WHEN COUNT(*) > 0 THEN 'OK'
      ELSE 'FAIL'
    END
    FROM pipeline_check_results
    WHERE check_type = 'RETRAINING_CANDIDATE';
  \" | grep -q OK"

check_command \
  "Production feedback metrics" \
  "curl -fsS ${API_URL}/metrics > /tmp/jobskill_production_feedback_metrics.txt && \
   grep -q jobskill_production_feedback_total /tmp/jobskill_production_feedback_metrics.txt && \
   grep -q jobskill_production_feedback_accuracy /tmp/jobskill_production_feedback_metrics.txt && \
   grep -q jobskill_production_feedback_f1_weighted /tmp/jobskill_production_feedback_metrics.txt"

check_command \
  "Retraining candidate metrics" \
  "curl -fsS ${API_URL}/metrics > /tmp/jobskill_retraining_candidate_metrics.txt && \
   grep -q jobskill_retraining_candidate_flag /tmp/jobskill_retraining_candidate_metrics.txt && \
   grep -q jobskill_retraining_candidate_feedback_count /tmp/jobskill_retraining_candidate_metrics.txt && \
   grep -q jobskill_retraining_candidate_accuracy /tmp/jobskill_retraining_candidate_metrics.txt && \
   grep -q jobskill_retraining_candidate_f1_weighted /tmp/jobskill_retraining_candidate_metrics.txt && \
   grep -q jobskill_retraining_candidate_accuracy_delta /tmp/jobskill_retraining_candidate_metrics.txt && \
   grep -q jobskill_retraining_candidate_f1_delta /tmp/jobskill_retraining_candidate_metrics.txt"

print_group "Prometheus / Alertmanager"

check_http \
  "Prometheus UI" \
  "${PROMETHEUS_URL}/-/ready"

check_command \
  "Prometheus jobskill-api target" \
  "curl -fsS '${PROMETHEUS_URL}/api/v1/query?query=up%7Bjob%3D%22jobskill-api%22%7D' | grep -q '\"value\"'"

check_http \
  "Alertmanager health" \
  "${ALERTMANAGER_URL}/-/ready"

check_command \
  "Alertmanager webhook lifecycle" \
  "${AIRFLOW_PROJECT} \"cd ${PROJECT_DIR} && python scripts/check_alert_webhook_lifecycle.py\""

check_command \
  "Alert events table is queryable" \
  "${PSQL} -tAc 'SELECT COUNT(*) FROM alert_events;' | grep -Eq '^[[:space:]]*[0-9]+[[:space:]]*$'"

check_command \
  "Alert current states table is queryable" \
  "${PSQL} -tAc 'SELECT COUNT(*) FROM alert_current_states;' | grep -Eq '^[[:space:]]*[0-9]+[[:space:]]*$'"

check_command \
  "Alert current state metrics" \
  "curl -fsS ${API_URL}/metrics | grep -q jobskill_alert_current_states_total"

check_command \
  "Synthetic alert residue check" \
  "${AIRFLOW_PROJECT} \"cd ${PROJECT_DIR} && python scripts/manage_synthetic_alerts.py --mode check\""

print_group "Dashboards"

check_http \
  "Grafana health" \
  "${GRAFANA_URL}/api/health"

check_http \
  "Streamlit dashboard" \
  "${DASHBOARD_URL}"

echo ""
echo "========================================"
echo " Smoke check completed successfully"
echo "========================================"
echo ""
