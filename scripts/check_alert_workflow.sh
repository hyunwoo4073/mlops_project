#!/usr/bin/env bash

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:9093}"

DB_SERVICE="${DB_SERVICE:-postgres}"
DB_NAME="${DB_NAME:-jobskill}"
DB_USER="${DB_USER:-jobskill}"

SMOKE_ALERT_NAME="${SMOKE_ALERT_NAME:-JobSkillSmokeAlertWorkflowTest}"
SMOKE_ALERT_FINGERPRINT="${SMOKE_ALERT_FINGERPRINT:-jobskill-smoke-alert-workflow-test}"
SMOKE_CLEANUP_ALERT_ROWS="${SMOKE_CLEANUP_ALERT_ROWS:-true}"

echo "[alert-workflow-check] start"

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "[alert-workflow-check][ERROR] required command not found: $command_name"
    exit 1
  fi
}

http_check() {
  local name="$1"
  local url="$2"

  echo "[alert-workflow-check] checking ${name}: ${url}"

  if ! curl -fsS "$url" >/tmp/alert_workflow_check_response.txt; then
    echo "[alert-workflow-check][ERROR] failed: ${name}"
    echo "[alert-workflow-check][ERROR] url: ${url}"
    exit 1
  fi
}

metrics_has() {
  local metric_name="$1"

  echo "[alert-workflow-check] checking metric: ${metric_name}"

  if ! curl -fsS "${API_URL}/metrics" | grep -q "${metric_name}"; then
    echo "[alert-workflow-check][ERROR] metric not found: ${metric_name}"
    exit 1
  fi
}

psql_scalar() {
  local query="$1"

  docker compose exec -T "${DB_SERVICE}" \
    psql -U "${DB_USER}" -d "${DB_NAME}" -Atc "${query}"
}

assert_table_exists() {
  local table_name="$1"

  echo "[alert-workflow-check] checking table: ${table_name}"

  local exists
  exists="$(psql_scalar "SELECT to_regclass('public.${table_name}') IS NOT NULL;")"

  if [[ "${exists}" != "t" ]]; then
    echo "[alert-workflow-check][ERROR] table not found: ${table_name}"
    exit 1
  fi
}

assert_db_count_gt_zero() {
  local name="$1"
  local query="$2"

  echo "[alert-workflow-check] checking DB count: ${name}"

  local count
  count="$(psql_scalar "${query}")"

  if [[ -z "${count}" || "${count}" -le 0 ]]; then
    echo "[alert-workflow-check][ERROR] expected count > 0 for ${name}, got: ${count}"
    exit 1
  fi
}

cleanup_smoke_alert_rows() {
  if [[ "${SMOKE_CLEANUP_ALERT_ROWS}" != "true" ]]; then
    echo "[alert-workflow-check] skip smoke alert cleanup"
    return
  fi

  echo "[alert-workflow-check] cleanup smoke alert rows"

  psql_scalar "
DELETE FROM alert_current_states
WHERE alert_name = '${SMOKE_ALERT_NAME}'
   OR fingerprint = '${SMOKE_ALERT_FINGERPRINT}';

DELETE FROM alert_events
WHERE alert_name = '${SMOKE_ALERT_NAME}'
   OR fingerprint = '${SMOKE_ALERT_FINGERPRINT}';
" >/dev/null
}

require_command curl
require_command docker

http_check "FastAPI root" "${API_URL}/"
http_check "FastAPI metrics" "${API_URL}/metrics"
http_check "FastAPI runbooks" "${API_URL}/runbooks"
http_check "Alertmanager status" "${ALERTMANAGER_URL}/api/v2/status"
http_check "Prometheus targets" "${PROMETHEUS_URL}/api/v1/targets"

echo "[alert-workflow-check] checking runbook endpoints"

http_check \
  "unacknowledged alert runbook" \
  "${API_URL}/runbooks/jobskill_unacknowledged_current_alert.md"

http_check \
  "alert response SLO breach runbook" \
  "${API_URL}/runbooks/jobskill_alert_response_slo_breach.md"

metrics_has "jobskill_alert_events_total"
metrics_has "jobskill_alert_current_states_total"
metrics_has "jobskill_alert_acknowledgements_total"
metrics_has "jobskill_alert_avg_mtta_minutes"
metrics_has "jobskill_alert_avg_mttr_minutes"
metrics_has "jobskill_alert_unacknowledged_current_total"
metrics_has "jobskill_alert_maintenance_mode"
metrics_has "jobskill_api_ready"
metrics_has "jobskill_api_database_ready"
metrics_has "jobskill_api_promoted_model_ready"
metrics_has "jobskill_api_promoted_model_file_exists"

echo "[alert-workflow-check] checking Prometheus query API"

curl -fsS \
  --get "${PROMETHEUS_URL}/api/v1/query" \
  --data-urlencode "query=jobskill_alert_maintenance_mode" \
  | grep -q '"status":"success"'

assert_table_exists "alert_events"
assert_table_exists "alert_current_states"
assert_table_exists "alert_acknowledgements"
assert_table_exists "alert_settings"
assert_table_exists "alert_silence_actions"

assert_db_count_gt_zero \
  "alert_settings maintenance_mode" \
  "SELECT COUNT(*) FROM alert_settings WHERE setting_key = 'maintenance_mode';"

cleanup_smoke_alert_rows

echo "[alert-workflow-check] posting synthetic Alertmanager webhook payload"

curl -fsS -X POST "${API_URL}/alertmanager/webhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"version\": \"4\",
    \"groupKey\": \"{}:{alertname=\\\"${SMOKE_ALERT_NAME}\\\"}\",
    \"truncatedAlerts\": 0,
    \"status\": \"firing\",
    \"receiver\": \"smoke-check\",
    \"groupLabels\": {
      \"alertname\": \"${SMOKE_ALERT_NAME}\"
    },
    \"commonLabels\": {
      \"alertname\": \"${SMOKE_ALERT_NAME}\",
      \"severity\": \"warning\",
      \"service\": \"smoke-check\",
      \"instance\": \"manual\"
    },
    \"commonAnnotations\": {
      \"summary\": \"Smoke check alert workflow test\",
      \"description\": \"Synthetic alert payload for alert workflow smoke check.\",
      \"runbook_url\": \"${API_URL}/runbooks/jobskill_alertmanager_slack_notification.md\",
      \"dashboard_url\": \"http://localhost:8501\",
      \"prometheus_url\": \"${PROMETHEUS_URL}/alerts\"
    },
    \"externalURL\": \"${ALERTMANAGER_URL}\",
    \"alerts\": [
      {
        \"status\": \"firing\",
        \"labels\": {
          \"alertname\": \"${SMOKE_ALERT_NAME}\",
          \"severity\": \"warning\",
          \"service\": \"smoke-check\",
          \"instance\": \"manual\"
        },
        \"annotations\": {
          \"summary\": \"Smoke check alert workflow test\",
          \"description\": \"Synthetic alert payload for alert workflow smoke check.\",
          \"runbook_url\": \"${API_URL}/runbooks/jobskill_alertmanager_slack_notification.md\",
          \"dashboard_url\": \"http://localhost:8501\",
          \"prometheus_url\": \"${PROMETHEUS_URL}/alerts\"
        },
        \"startsAt\": \"2026-07-15T00:00:00Z\",
        \"endsAt\": \"0001-01-01T00:00:00Z\",
        \"generatorURL\": \"${PROMETHEUS_URL}/graph\",
        \"fingerprint\": \"${SMOKE_ALERT_FINGERPRINT}\"
      }
    ]
  }" >/dev/null

assert_db_count_gt_zero \
  "smoke alert event inserted" \
  "SELECT COUNT(*) FROM alert_events WHERE alert_name = '${SMOKE_ALERT_NAME}' AND fingerprint = '${SMOKE_ALERT_FINGERPRINT}';"

assert_db_count_gt_zero \
  "smoke alert current state upserted" \
  "SELECT COUNT(*) FROM alert_current_states WHERE alert_name = '${SMOKE_ALERT_NAME}' AND fingerprint = '${SMOKE_ALERT_FINGERPRINT}';"

cleanup_smoke_alert_rows

echo "[alert-workflow-check] success"
