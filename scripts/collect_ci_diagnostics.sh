#!/usr/bin/env bash

set -euo pipefail

COMPOSE="${COMPOSE:-docker compose}"
OUTPUT_DIR="${CI_DIAGNOSTICS_DIR:-reports/ci_diagnostics}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-jobskill-postgres}"
POSTGRES_USER="${POSTGRES_USER:-jobskill}"
POSTGRES_DB="${POSTGRES_DB:-jobskill}"

SERVICES=(
  postgres
  airflow-apiserver
  airflow-scheduler
  airflow-dag-processor
  airflow-triggerer
  mlflow
  api
  dashboard
  alertmanager
  prometheus
  grafana
)

mkdir -p "${OUTPUT_DIR}/logs"
mkdir -p "${OUTPUT_DIR}/db"
mkdir -p "${OUTPUT_DIR}/http"

redact_file() {
  local path="$1"

  if [[ ! -f "${path}" ]]; then
    return 0
  fi

  sed -i \
    -e 's/\(DB_PASSWORD=\).*/\1***REDACTED***/g' \
    -e 's/\(AIRFLOW_DB_PASSWORD=\).*/\1***REDACTED***/g' \
    -e 's/\(AIRFLOW_JWT_SECRET=\).*/\1***REDACTED***/g' \
    -e 's/\(AIRFLOW_API_SECRET_KEY=\).*/\1***REDACTED***/g' \
    -e 's/\(AIRFLOW_FERNET_KEY=\).*/\1***REDACTED***/g' \
    -e 's/\(SLACK_WEBHOOK_URL=\).*/\1***REDACTED***/g' \
    -e 's#https://hooks.slack.com/services/[A-Za-z0-9/_-]*#https://hooks.slack.com/services/***REDACTED***#g' \
    "${path}" || true
}

write_section() {
  local title="$1"
  local path="$2"

  {
    echo ""
    echo "========================================"
    echo "${title}"
    echo "========================================"
    echo ""
  } >> "${path}"
}

capture_command() {
  local title="$1"
  local output_file="$2"
  shift 2

  write_section "${title}" "${output_file}"

  {
    echo "$ $*"
    echo ""
    "$@"
  } >> "${output_file}" 2>&1 || true

  redact_file "${output_file}"
}

capture_shell() {
  local title="$1"
  local output_file="$2"
  local command="$3"

  write_section "${title}" "${output_file}"

  {
    echo "$ ${command}"
    echo ""
    bash -lc "${command}"
  } >> "${output_file}" 2>&1 || true

  redact_file "${output_file}"
}

capture_http() {
  local title="$1"
  local output_file="$2"
  local url="$3"

  capture_shell "${title}" "${output_file}" "curl -fsS '${url}'"
}

capture_psql() {
  local title="$1"
  local output_file="$2"
  local sql="$3"

  capture_shell \
    "${title}" \
    "${output_file}" \
    "docker exec ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c \"${sql}\""
}

echo "Collecting CI diagnostics into ${OUTPUT_DIR}"

capture_command \
  "Docker version" \
  "${OUTPUT_DIR}/runtime.txt" \
  docker version

capture_command \
  "Docker Compose version" \
  "${OUTPUT_DIR}/runtime.txt" \
  docker compose version

capture_shell \
  "Docker Compose ps" \
  "${OUTPUT_DIR}/runtime.txt" \
  "${COMPOSE} ps"

capture_shell \
  "Docker images" \
  "${OUTPUT_DIR}/runtime.txt" \
  "docker images | head -100"

capture_shell \
  "Disk usage" \
  "${OUTPUT_DIR}/runtime.txt" \
  "df -h"

capture_shell \
  "Memory usage" \
  "${OUTPUT_DIR}/runtime.txt" \
  "free -h || true"

for service in "${SERVICES[@]}"; do
  capture_shell \
    "Logs for ${service}" \
    "${OUTPUT_DIR}/logs/${service}.log" \
    "${COMPOSE} logs --tail=300 ${service}"
done

if docker exec "${POSTGRES_CONTAINER}" pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
  capture_psql \
    "Project table row counts" \
    "${OUTPUT_DIR}/db/table_counts.txt" \
    "
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
    "

  capture_psql \
    "Latest pipeline check results" \
    "${OUTPUT_DIR}/db/pipeline_check_results.txt" \
    "
    SELECT
      check_type,
      check_name,
      status,
      metric_value,
      threshold_value,
      message,
      checked_at
    FROM pipeline_check_results
    ORDER BY checked_at DESC
    LIMIT 30;
    "

  capture_psql \
    "Current firing alerts" \
    "${OUTPUT_DIR}/db/current_alerts.txt" \
    "
    SELECT
      alert_name,
      service,
      severity,
      status,
      starts_at,
      last_received_at,
      fingerprint
    FROM alert_current_states
    WHERE status = 'firing'
    ORDER BY starts_at ASC
    LIMIT 30;
    "

  capture_psql \
    "Recent alert events" \
    "${OUTPUT_DIR}/db/alert_events.txt" \
    "
    SELECT
      alert_name,
      service,
      severity,
      status,
      starts_at,
      ends_at,
      received_at,
      fingerprint
    FROM alert_events
    ORDER BY received_at DESC
    LIMIT 30;
    "

  capture_psql \
    "Recent model registry records" \
    "${OUTPUT_DIR}/db/model_registry.txt" \
    "
    SELECT *
    FROM model_registry
    ORDER BY id DESC
    LIMIT 10;
    "
else
  echo "PostgreSQL is not ready or container does not exist." > "${OUTPUT_DIR}/db/postgres_unavailable.txt"
fi

capture_http "FastAPI health" "${OUTPUT_DIR}/http/api_health.json" "http://localhost:8000/health"
capture_http "FastAPI readiness" "${OUTPUT_DIR}/http/api_ready.json" "http://localhost:8000/ready"
capture_http "FastAPI model" "${OUTPUT_DIR}/http/api_model.json" "http://localhost:8000/model"
capture_http "FastAPI metrics" "${OUTPUT_DIR}/http/api_metrics.txt" "http://localhost:8000/metrics"
capture_http "Prometheus readiness" "${OUTPUT_DIR}/http/prometheus_ready.txt" "http://localhost:9090/-/ready"
capture_http "Prometheus alerts" "${OUTPUT_DIR}/http/prometheus_alerts.json" "http://localhost:9090/api/v1/alerts"
capture_http "Prometheus targets" "${OUTPUT_DIR}/http/prometheus_targets.json" "http://localhost:9090/api/v1/targets"
capture_http "Alertmanager readiness" "${OUTPUT_DIR}/http/alertmanager_ready.txt" "http://localhost:9093/-/ready"
capture_http "Alertmanager alerts" "${OUTPUT_DIR}/http/alertmanager_alerts.json" "http://localhost:9093/api/v2/alerts"
capture_http "Grafana health" "${OUTPUT_DIR}/http/grafana_health.json" "http://localhost:3000/api/health"
capture_http "Streamlit dashboard" "${OUTPUT_DIR}/http/dashboard.html" "http://localhost:8501"

cat > "${OUTPUT_DIR}/README.md" <<'EOF'
# JobSkill CI Diagnostics

This directory contains diagnostic artifacts collected from a GitHub Actions smoke-check run.

## Contents

```text
runtime.txt
- Docker / Docker Compose / container / disk / memory status

logs/
- Tail logs for PostgreSQL, Airflow, MLflow, FastAPI, Dashboard, Alertmanager, Prometheus and Grafana

db/
- Project table counts
- Latest pipeline check results
- Current firing alerts
- Recent alert events
- Recent model registry records

http/
- FastAPI health/readiness/model/metrics
- Prometheus readiness/alerts/targets
- Alertmanager readiness/alerts
- Grafana health
- Streamlit dashboard response
```

## Intended Use

Use this bundle when CI fails before the normal ops evidence bundle is generated.
It is focused on troubleshooting rather than portfolio evidence.
EOF

echo "CI diagnostics collection completed."
echo "path=${OUTPUT_DIR}"

