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

check_file_exists() {
  local path="$1"

  if [[ ! -f "$path" ]]; then
    fail "Required file not found: $path"
  fi
}

check_python_compile() {
  local name="$1"
  local path="$2"

  check_file_exists "$path"

  check_command \
    "$name" \
    python -m py_compile "$path"
}

check_shell_syntax() {
  local name="$1"
  local path="$2"

  check_file_exists "$path"

  check_command \
    "$name" \
    bash -n "$path"
}

check_optional_python_compile() {
  local name="$1"
  local path="$2"

  if [[ -f "$path" ]]; then
    check_command \
      "$name" \
      python -m py_compile "$path"
  fi
}

check_optional_shell_syntax() {
  local name="$1"
  local path="$2"

  if [[ -f "$path" ]]; then
    check_command \
      "$name" \
      bash -n "$path"
  fi
}

echo ""
echo "JobSkill MLOps Static Ops Validation"

print_section "Required file presence"
check_file_exists src/inference/api.py
check_file_exists src/dashboard/app.py
check_file_exists src/monitoring/prometheus_metrics.py
check_file_exists monitoring/prometheus/prometheus.yml
check_file_exists monitoring/prometheus/rules/jobskill_alert_rules.yml
check_file_exists monitoring/prometheus/tests/jobskill_alert_rules.test.yml
check_file_exists monitoring/alertmanager/alertmanager.yml
check_file_exists monitoring/metrics_contract.yml
check_file_exists docker-compose.yml
check_file_exists Makefile
pass "Required file presence"

# -----------------------------------------------------------------------------
# Core application modules
# -----------------------------------------------------------------------------
check_python_compile \
  "Compile FastAPI app" \
  src/inference/api.py

check_python_compile \
  "Compile Streamlit dashboard" \
  src/dashboard/app.py

check_python_compile \
  "Compile monitoring metrics" \
  src/monitoring/prometheus_metrics.py

# -----------------------------------------------------------------------------
# Quality / model operations modules
# -----------------------------------------------------------------------------
check_python_compile \
  "Compile production feedback check" \
  src/quality/check_production_feedback.py

check_python_compile \
  "Compile retraining candidate check" \
  src/quality/check_retraining_candidate.py

check_python_compile \
  "Compile retraining strategy check" \
  src/quality/check_retraining_strategy.py

check_python_compile \
  "Compile training cost report" \
  src/reporting/generate_training_cost_report.py

check_python_compile \
  "Compile training data selector" \
  src/training/training_data_selector.py

check_python_compile \
  "Compile ops evidence bundle creator" \
  scripts/create_ops_evidence_bundle.py

check_optional_python_compile \
  "Compile data contract check" \
  src/quality/check_data_contract.py

check_optional_python_compile \
  "Compile model lifecycle integrity check" \
  scripts/check_model_lifecycle_integrity.py

check_optional_python_compile \
  "Compile model card consistency check" \
  scripts/check_model_card_consistency.py

# -----------------------------------------------------------------------------
# Alert / incident operations scripts
# -----------------------------------------------------------------------------
check_python_compile \
  "Compile synthetic alert hygiene manager" \
  scripts/manage_synthetic_alerts.py

check_python_compile \
  "Compile alert webhook lifecycle check" \
  scripts/check_alert_webhook_lifecycle.py

check_python_compile \
  "Compile ops validation report" \
  src/reporting/generate_ops_validation_report.py

check_python_compile \
  "Compile retraining strategy report" \
  src/reporting/generate_retraining_strategy_report.py

check_python_compile \
  "Compile ops evidence bundle creator" \
  scripts/create_ops_evidence_bundle.py

check_python_compile \
  "Compile ops evidence bundle checker" \
  scripts/check_ops_evidence_bundle.py

check_optional_python_compile \
  "Compile incident response report" \
  src/reporting/generate_incident_response_report.py

check_optional_python_compile \
  "Compile incident drill" \
  scripts/run_incident_drill.py

# -----------------------------------------------------------------------------
# Validation helper scripts
# -----------------------------------------------------------------------------
check_python_compile \
  "Compile metrics contract check" \
  scripts/check_metrics_contract.py

check_python_compile \
  "Compile alert rule metric dependency check" \
  scripts/check_alert_rule_metric_dependencies.py

check_python_compile \
  "Compile runbook coverage check" \
  scripts/check_runbook_coverage.py

check_optional_python_compile \
  "Compile compose rendered config check" \
  scripts/check_compose_rendered_config.py

check_optional_python_compile \
  "Compile repository artifact check" \
  scripts/check_repository_artifacts.py

# -----------------------------------------------------------------------------
# Airflow DAGs
# -----------------------------------------------------------------------------
check_python_compile \
  "Compile pipeline DAG" \
  dags/jobskill_pipeline_dag.py

check_python_compile \
  "Compile feedback ops DAG" \
  dags/jobskill_feedback_ops_dag.py

# -----------------------------------------------------------------------------
# Shell script syntax
# -----------------------------------------------------------------------------
check_shell_syntax \
  "Validate smoke check shell syntax" \
  scripts/smoke_check.sh

check_shell_syntax \
  "Validate alert workflow shell syntax" \
  scripts/check_alert_workflow.sh

check_shell_syntax \
  "Validate CI diagnostics shell syntax" \
  scripts/collect_ci_diagnostics.sh

check_shell_syntax \
  "Validate static ops validation shell syntax" \
  scripts/check_static_ops_validation.sh

check_optional_shell_syntax \
  "Validate repository artifact shell syntax" \
  scripts/check_repository_artifacts.sh

# -----------------------------------------------------------------------------
# Compose / monitoring config validation
# -----------------------------------------------------------------------------
check_command \
  "Compose rendered config check" \
  make compose-config-check

check_command \
  "Prometheus config and alert rules" \
  make prometheus-check

check_command \
  "Prometheus alert rule unit tests" \
  make prometheus-rule-test

check_command \
  "Alertmanager config" \
  make alertmanager-check

# -----------------------------------------------------------------------------
# Documentation / metric dependency validation
# -----------------------------------------------------------------------------
check_command \
  "Runbook coverage" \
  make runbook-check

check_command \
  "Metrics contract static validation" \
  python scripts/check_metrics_contract.py --skip-url

check_command \
  "Alert rule metric dependencies" \
  python scripts/check_alert_rule_metric_dependencies.py --skip-url

echo ""
echo "========================================"
echo "[PASS] JobSkill MLOps static ops validation completed"
echo "========================================"