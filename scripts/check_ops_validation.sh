#!/usr/bin/env bash

set -euo pipefail

COMPOSE="${COMPOSE:-docker compose}"
API_URL="${API_URL:-http://localhost:8000}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:9093}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:8501}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-jobskill-postgres}"
POSTGRES_USER="${POSTGRES_USER:-jobskill}"
POSTGRES_DB="${POSTGRES_DB:-jobskill}"

print_banner() {
  echo ""
  echo "========================================"
  echo " JobSkill MLOps Ops Validation"
  echo "========================================"
  echo ""
}

print_section() {
  echo ""
  echo "========================================"
  echo "[CHECK] $1"
  echo "========================================"
}

pass() {
  echo "[PASS] $1"
}

fail() {
  echo "[FAIL] $1"
  exit 1
}

print_related_logs() {
  local name="$1"

  echo ""
  echo "[DEBUG] Related logs"
  echo "----------------------------------------"

  if [[ "$name" == *"API"* || "$name" == *"FastAPI"* || "$name" == *"Readiness"* ]]; then
    ${COMPOSE} logs --tail=100 api || true
  fi

  if [[ "$name" == *"Airflow"* || "$name" == *"DAG"* ]]; then
    ${COMPOSE} logs --tail=100 airflow-scheduler || true
    ${COMPOSE} logs --tail=100 airflow-dag-processor || true
    ${COMPOSE} logs --tail=100 airflow-apiserver || true
  fi

  if [[ "$name" == *"PostgreSQL"* || "$name" == *"Database"* ]]; then
    ${COMPOSE} logs --tail=100 postgres || true
  fi

  if [[ "$name" == *"Prometheus"* ]]; then
    ${COMPOSE} logs --tail=100 prometheus || true
  fi

  if [[ "$name" == *"Alertmanager"* || "$name" == *"Alert"* ]]; then
    ${COMPOSE} logs --tail=100 alertmanager || true
    ${COMPOSE} logs --tail=100 api || true
  fi

  if [[ "$name" == *"Dashboard"* || "$name" == *"Streamlit"* ]]; then
    ${COMPOSE} logs --tail=100 dashboard || true
  fi

  if [[ "$name" == *"Grafana"* ]]; then
    ${COMPOSE} logs --tail=100 grafana || true
  fi

  if [[ "$name" == *"MLflow"* ]]; then
    ${COMPOSE} logs --tail=100 mlflow || true
  fi
}

check_command() {
  local name="$1"
  local command="$2"

  print_section "$name"

  if bash -lc "$command"; then
    pass "$name"
  else
    echo ""
    echo "[FAIL] $name"
    print_related_logs "$name"
    exit 1
  fi
}

check_http() {
  local name="$1"
  local url="$2"

  print_section "$name"
  echo "URL: $url"

  if curl -fsS "$url" > /tmp/jobskill_ops_validation_response.txt; then
    pass "$name"
  else
    echo ""
    echo "[FAIL] $name"
    print_related_logs "$name"
    exit 1
  fi
}

print_banner

# -----------------------------------------------------------------------------
# 1. Static validation
# -----------------------------------------------------------------------------
check_command \
  "Static ops validation" \
  "make ops-static-check"

# -----------------------------------------------------------------------------
# 2. Docker Compose / runtime baseline
# -----------------------------------------------------------------------------
check_command \
  "Docker Compose rendered config" \
  "make compose-config-check"

check_command \
  "Container status" \
  "${COMPOSE} ps"

check_command \
  "Required containers are running" \
  "${COMPOSE} ps --status running | grep -q jobskill-postgres && \
   ${COMPOSE} ps --status running | grep -q jobskill-api && \
   ${COMPOSE} ps --status running | grep -q jobskill-airflow-scheduler && \
   ${COMPOSE} ps --status running | grep -q jobskill-prometheus && \
   ${COMPOSE} ps --status running | grep -q jobskill-alertmanager"

# -----------------------------------------------------------------------------
# 3. Database / service discovery
# -----------------------------------------------------------------------------
check_command \
  "PostgreSQL connection" \
  "docker exec ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c 'SELECT 1;'"

check_command \
  "API can resolve PostgreSQL service" \
  "${COMPOSE} exec -T api getent hosts postgres"

# -----------------------------------------------------------------------------
# 4. Airflow DAG health
# -----------------------------------------------------------------------------
check_command \
  "Airflow DAG import errors" \
  "${COMPOSE} exec -T airflow-scheduler airflow dags list-import-errors"

check_command \
  "Airflow pipeline DAG tasks" \
  "${COMPOSE} exec -T airflow-scheduler airflow tasks list jobskill_mlops_pipeline"

check_command \
  "Airflow feedback ops DAG tasks" \
  "${COMPOSE} exec -T airflow-scheduler airflow tasks list jobskill_feedback_ops | \
   grep -E 'show_feedback_ops_config|check_production_feedback|check_retraining_candidate'"

# -----------------------------------------------------------------------------
# 5. Retraining strategy checks
# -----------------------------------------------------------------------------
check_command \
  "Retraining strategy check" \
  "make retraining-strategy-check"

# -----------------------------------------------------------------------------
# 6. Application endpoints
# -----------------------------------------------------------------------------
check_http "FastAPI health" "${API_URL}/health"
check_http "FastAPI readiness" "${API_URL}/ready"
check_http "FastAPI model endpoint" "${API_URL}/model"
check_http "FastAPI metrics endpoint" "${API_URL}/metrics"
check_http "MLflow UI" "http://localhost:5000"
check_http "Streamlit Dashboard" "${DASHBOARD_URL}"

# -----------------------------------------------------------------------------
# 7. Monitoring / alerting config
# -----------------------------------------------------------------------------
check_command \
  "Prometheus config and alert rules" \
  "make prometheus-check"

check_command \
  "Prometheus rule tests" \
  "make prometheus-rule-test"

check_command \
  "Prometheus external target check" \
  "make prometheus-external-target-check"

check_command \
  "Alertmanager config" \
  "make alertmanager-check"

check_http "Prometheus readiness" "${PROMETHEUS_URL}/-/ready"
check_http "Alertmanager readiness" "${ALERTMANAGER_URL}/-/ready"
check_http "Grafana health" "${GRAFANA_URL}/api/health"

# -----------------------------------------------------------------------------
# 8. Documentation / metric dependency checks
# -----------------------------------------------------------------------------
check_command \
  "Runbook coverage" \
  "make runbook-check"

check_command \
  "Metrics contract check" \
  "make metrics-contract-check"

check_command \
  "Alert rule metric dependency check" \
  "make alert-rule-metric-check"

# -----------------------------------------------------------------------------
# 9. Alert lifecycle hygiene
# -----------------------------------------------------------------------------
check_command \
  "Alert webhook lifecycle check" \
  "make alert-webhook-lifecycle-check"

check_command \
  "Synthetic alert residue check" \
  "make synthetic-alert-check"

# -----------------------------------------------------------------------------
# 10. Full smoke check
# -----------------------------------------------------------------------------
check_command \
  "Smoke check" \
  "make smoke"

# -----------------------------------------------------------------------------
# 11. Repository hygiene
# -----------------------------------------------------------------------------
if [[ -x scripts/check_repository_artifacts.sh ]]; then
  check_command \
    "Repository artifact check" \
    "make repo-artifact-check"
fi

echo ""
echo "========================================"
echo "[PASS] JobSkill MLOps ops validation completed"
echo "========================================"
echo ""
