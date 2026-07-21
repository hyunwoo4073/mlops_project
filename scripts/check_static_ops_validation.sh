#!/usr/bin/env bash

set -euo pipefail

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

echo ""
echo "JobSkill MLOps Static Ops Validation"

check_command \
  "Compile FastAPI app" \
  python -m py_compile src/inference/api.py

check_command \
  "Compile monitoring metrics" \
  python -m py_compile src/monitoring/prometheus_metrics.py

if test -f src/reporting/generate_incident_response_report.py; then
  check_command \
    "Compile incident response report" \
    python -m py_compile src/reporting/generate_incident_response_report.py
fi

if test -f scripts/check_metrics_contract.py; then
  check_command \
    "Compile metrics contract check" \
    python -m py_compile scripts/check_metrics_contract.py
fi

if test -f scripts/check_alert_rule_metric_dependencies.py; then
  check_command \
    "Compile alert rule metric dependency check" \
    python -m py_compile scripts/check_alert_rule_metric_dependencies.py
fi

if test -f scripts/check_runbook_coverage.py; then
  check_command \
    "Compile runbook coverage check" \
    python -m py_compile scripts/check_runbook_coverage.py
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

check_command \
  "Runbook coverage" \
  make runbook-check

check_command \
  "Alert rule metric dependencies" \
  python scripts/check_alert_rule_metric_dependencies.py --skip-metrics-endpoint

echo ""
echo "========================================"
echo "[PASS] JobSkill MLOps static ops validation completed"
echo "========================================"
