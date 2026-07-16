#!/usr/bin/env bash

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

print_section() {
  echo ""
  echo "========================================"
  echo "[CHECK] $1"
  echo "========================================"
}

fail() {
  echo "[FAIL] $1"
  exit 1
}

pass() {
  echo "[PASS] $1"
}

check_command() {
  local name="$1"
  shift

  print_section "$name"
  "$@"
  pass "$name"
}

check_url() {
  local name="$1"
  local url="$2"

  print_section "$name"
  echo "URL: $url"

  curl -fsS "$url" >/dev/null || fail "$name"
  pass "$name"
}

check_metric() {
  local metric_name="$1"

  print_section "Metric: ${metric_name}"

  curl -fsS "${API_URL}/metrics" | grep -q "$metric_name" \
    || fail "Metric not found: ${metric_name}"

  pass "Metric found: ${metric_name}"
}

check_file() {
  local file_path="$1"

  print_section "File: ${file_path}"

  test -f "$file_path" || fail "File not found: ${file_path}"

  pass "File exists: ${file_path}"
}

echo ""
echo "JobSkill MLOps Ops Validation"
echo "API_URL=${API_URL}"

check_command \
  "Compile monitoring metrics" \
  python -m py_compile src/monitoring/prometheus_metrics.py

check_command \
  "Compile FastAPI app" \
  python -m py_compile src/inference/api.py

if test -f src/reporting/generate_incident_response_report.py; then
  check_command \
    "Compile incident response report" \
    python -m py_compile src/reporting/generate_incident_response_report.py
fi

check_command \
  "Prometheus config and alert rules" \
  make prometheus-check

check_command \
  "Prometheus alert rule unit tests" \
  make prometheus-rule-test

check_command \
  "Alertmanager config" \
  make alertmanager-check

check_url \
  "FastAPI health" \
  "${API_URL}/health"

check_url \
  "FastAPI readiness" \
  "${API_URL}/ready"

check_url \
  "FastAPI metrics" \
  "${API_URL}/metrics"

check_metric "jobskill_api_ready"
check_metric "jobskill_api_database_ready"
check_metric "jobskill_api_promoted_model_ready"
check_metric "jobskill_api_promoted_model_file_exists"
check_metric "jobskill_alert_maintenance_mode"
check_metric "jobskill_alert_events_total"
check_metric "jobskill_alert_current_states_total"

check_file "docs/runbooks/jobskill_api_not_ready.md"
check_file "docs/runbooks/jobskill_api_metrics_down.md"
check_file "docs/runbooks/jobskill_high_low_confidence_ratio.md"
check_file "docs/runbooks/jobskill_pipeline_check_failure.md"

check_command \
  "Service smoke check" \
  bash scripts/smoke_check.sh

check_command \
  "Alert workflow smoke check" \
  bash scripts/check_alert_workflow.sh

echo ""
echo "========================================"
echo "[PASS] JobSkill MLOps ops validation completed"
echo "========================================"
