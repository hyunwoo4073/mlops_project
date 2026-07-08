#!/usr/bin/env bash

set -euo pipefail

echo ""
echo "========================================"
echo " JobSkill MLOps Smoke Check"
echo "========================================"
echo ""

print_related_logs() {
  local name="$1"

  echo ""
  echo "[DEBUG] Related container logs"
  echo "----------------------------------------"

  if [[ "$name" == *"FastAPI"* || "$name" == *"API"* ]]; then
    docker compose logs --tail=100 api || true
  fi

  if [[ "$name" == *"Streamlit"* || "$name" == *"Dashboard"* ]]; then
    docker compose logs --tail=100 dashboard || true
  fi

  if [[ "$name" == *"Prometheus"* ]]; then
    docker compose logs --tail=100 prometheus || true
  fi

  if [[ "$name" == *"Grafana"* ]]; then
    docker compose logs --tail=100 grafana || true
  fi

  if [[ "$name" == *"MLflow"* ]]; then
    docker compose logs --tail=100 mlflow || true
  fi

  if [[ "$name" == *"Airflow"* ]]; then
    docker compose logs --tail=100 airflow-scheduler || true
    docker compose logs --tail=100 airflow-apiserver || true
  fi

  if [[ "$name" == *"PostgreSQL"* || "$name" == *"Project tables"* || "$name" == *"Core table"* ]]; then
    docker compose logs --tail=100 postgres || true
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

check_command \
  "Docker Compose config" \
  "docker compose config > /tmp/jobskill_compose_config.yml"

check_command \
  "Container status" \
  "docker compose ps"

check_command \
  "PostgreSQL connection" \
  "docker exec jobskill-postgres psql -U jobskill -d jobskill -c 'SELECT 1;'"

check_command \
  "Project tables" \
  "docker exec jobskill-postgres psql -U jobskill -d jobskill -c \"
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN (
        'raw_job_posts',
        'cleaned_job_posts',
        'job_post_skills',
        'model_predictions',
        'api_prediction_logs',
        'pipeline_check_results',
        'model_registry'
      )
    ORDER BY table_name;
  \""

check_command \
  "Core table counts" \
  "docker exec jobskill-postgres psql -U jobskill -d jobskill -c \"
    SELECT 'raw_job_posts' AS table_name, COUNT(*) FROM raw_job_posts
    UNION ALL
    SELECT 'cleaned_job_posts', COUNT(*) FROM cleaned_job_posts
    UNION ALL
    SELECT 'job_post_skills', COUNT(*) FROM job_post_skills
    UNION ALL
    SELECT 'model_predictions', COUNT(*) FROM model_predictions
    UNION ALL
    SELECT 'api_prediction_logs', COUNT(*) FROM api_prediction_logs
    UNION ALL
    SELECT 'pipeline_check_results', COUNT(*) FROM pipeline_check_results
    UNION ALL
    SELECT 'model_registry', COUNT(*) FROM model_registry;
  \""

check_command \
  "Airflow DAG import errors" \
  "docker compose exec -T airflow-scheduler airflow dags list-import-errors"

check_command \
  "Airflow pipeline tasks" \
  "docker compose exec -T airflow-scheduler airflow tasks list jobskill_mlops_pipeline"

check_http \
  "MLflow UI" \
  "http://localhost:5000"

check_http \
  "FastAPI health" \
  "http://localhost:8000/"

check_http \
  "FastAPI model info" \
  "http://localhost:8000/model"

check_http \
  "FastAPI metrics" \
  "http://localhost:8000/metrics"

check_command \
  "FastAPI metrics content" \
  "curl -fsS http://localhost:8000/metrics | grep -q jobskill_model_predictions_total"

check_command \
  "FastAPI sample prediction requests" \
  "python scripts/send_sample_api_requests.py"

check_command \
  "API prediction logs" \
  "docker exec jobskill-postgres psql -U jobskill -d jobskill -tAc \"
    SELECT CASE
      WHEN COUNT(*) > 0 THEN 'OK'
      ELSE 'FAIL'
    END
    FROM api_prediction_logs
    WHERE status = 'SUCCESS';
  \" | grep -q OK"

check_command \
  "API prediction rows" \
  "docker exec jobskill-postgres psql -U jobskill -d jobskill -tAc \"
    SELECT CASE
      WHEN COUNT(*) > 0 THEN 'OK'
      ELSE 'FAIL'
    END
    FROM model_predictions
    WHERE prediction_source = 'API';
  \" | grep -q OK"

check_http \
  "Prometheus UI" \
  "http://localhost:9090/-/ready"

check_command \
  "Prometheus jobskill-api target" \
  "curl -fsS 'http://localhost:9090/api/v1/query?query=up%7Bjob%3D%22jobskill-api%22%7D' | grep -q '\"value\"'"

check_http \
  "Grafana health" \
  "http://localhost:3000/api/health"

check_http \
  "Streamlit dashboard" \
  "http://localhost:8501"

echo ""
echo "========================================"
echo " Smoke check completed successfully"
echo "========================================"
echo ""