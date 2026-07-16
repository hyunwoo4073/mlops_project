.PHONY: help build up down restart ps logs \
        airflow-init create-tables \
        dag-list dag-errors dag-tasks dag-trigger dag-runs \
        lint test test-container ci smoke alert-workflow-check ops-check \
        report incident-report incident-drill notify api-sample cleanup drift-check metrics \
        prometheus prometheus-logs prometheus-check prometheus-rule-test \
        alertmanager alertmanager-logs alertmanager-check \
        grafana grafana-logs \
        dashboard dashboard-logs \
        api api-logs mlflow-logs \
        psql clean-runtime

help:
	@echo ""
	@echo "JobSkill MLOps Commands"
	@echo ""
	@echo "Build / Run"
	@echo "  make build                  Build Airflow and API images"
	@echo "  make up                     Start main services"
	@echo "  make down                   Stop services"
	@echo "  make restart                Restart main services"
	@echo "  make ps                     Show container status"
	@echo "  make logs                   Show all logs"
	@echo ""
	@echo "Database / Airflow"
	@echo "  make airflow-init           Initialize Airflow metadata DB"
	@echo "  make create-tables          Create or update project tables"
	@echo "  make psql                   Open PostgreSQL shell"
	@echo ""
	@echo "DAG"
	@echo "  make dag-list               List DAGs"
	@echo "  make dag-errors             Show DAG import errors"
	@echo "  make dag-tasks              List pipeline tasks"
	@echo "  make dag-trigger            Trigger pipeline DAG"
	@echo "  make dag-runs               List pipeline DAG runs"
	@echo ""
	@echo "Quality / Validation"
	@echo "  make lint                   Run ruff"
	@echo "  make test                   Run local pytest"
	@echo "  make test-container         Run pytest in Airflow container"
	@echo "  make ci                     Run lint and pytest"
	@echo "  make smoke                  Run service smoke checks"
	@echo "  make alert-workflow-check   Run alert workflow smoke check"
	@echo "  make ops-check              Run full local ops validation checks"
	@echo "  make drift-check            Run prediction distribution drift check"
	@echo ""
	@echo "Reports / Apps"
	@echo "  make report                 Generate pipeline report"
	@echo "  make incident-report        Generate incident response report"
	@echo "  make incident-drill         Run synthetic incident response drill"
	@echo "  make dashboard              Start Streamlit dashboard"
	@echo "  make dashboard-logs         Show dashboard logs"
	@echo "  make api                    Start FastAPI"
	@echo "  make api-logs               Show FastAPI logs"
	@echo "  make api-sample             Send sample prediction requests to FastAPI"
	@echo "  make metrics                Show FastAPI Prometheus metrics"
	@echo ""
	@echo "Monitoring / Alerting"
	@echo "  make prometheus             Start Prometheus"
	@echo "  make prometheus-logs        Show Prometheus logs"
	@echo "  make prometheus-check       Validate Prometheus config and alert rules"
	@echo "  make prometheus-rule-test  Run Prometheus alert rule unit tests"
	@echo "  make alertmanager           Start Alertmanager"
	@echo "  make alertmanager-logs      Show Alertmanager logs"
	@echo "  make alertmanager-check     Validate Alertmanager config"
	@echo "  make grafana                Start Grafana"
	@echo "  make grafana-logs           Show Grafana logs"
	@echo ""
	@echo "Notification"
	@echo "  make notify                 Send or print pipeline status notification"
	@echo ""
	@echo "Maintenance"
	@echo "  make cleanup                Run cleanup retention script"
	@echo "  make clean-runtime          Remove local runtime output files"
	@echo ""

build:
	docker compose build airflow-image api

up:
	docker compose up -d --no-build --force-recreate \
		airflow-apiserver \
		airflow-scheduler \
		airflow-dag-processor \
		airflow-triggerer \
		mlflow \
		api \
		dashboard \
		alertmanager \
		prometheus \
		grafana

down:
	docker compose down

restart:
	docker compose up -d --no-build --force-recreate \
		airflow-apiserver \
		airflow-scheduler \
		airflow-dag-processor \
		airflow-triggerer \
		mlflow \
		api \
		dashboard \
		alertmanager \
		prometheus \
		grafana

ps:
	docker compose ps

logs:
	docker compose logs --tail=100

airflow-init:
	docker compose up --no-build airflow-init

create-tables:
	docker exec -i jobskill-postgres psql -U jobskill -d jobskill < sql/create_tables.sql

psql:
	docker exec -it jobskill-postgres psql -U jobskill -d jobskill

dag-list:
	docker compose exec airflow-scheduler airflow dags list

dag-errors:
	docker compose exec airflow-scheduler airflow dags list-import-errors

dag-tasks:
	docker compose exec airflow-scheduler airflow tasks list jobskill_mlops_pipeline

dag-trigger:
	docker compose exec airflow-scheduler airflow dags trigger jobskill_mlops_pipeline

dag-runs:
	docker compose exec airflow-scheduler airflow dags list-runs jobskill_mlops_pipeline

lint:
	ruff check src dags scripts tests

test:
	pytest

test-container:
	docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && pytest"

ci: lint test

smoke:
	bash scripts/smoke_check.sh

alert-workflow-check:
	bash scripts/check_alert_workflow.sh

ops-check:
	bash scripts/check_ops_validation.sh

report:
	docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/reporting/generate_pipeline_report.py"

incident-report:
	docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/reporting/generate_incident_response_report.py"

notify:
	docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/notification/notify_pipeline_status.py"

dashboard:
	docker compose up -d dashboard

dashboard-logs:
	docker compose logs --tail=100 dashboard

api:
	docker compose up -d api

api-logs:
	docker compose logs --tail=100 api

mlflow-logs:
	docker compose logs --tail=100 mlflow

api-sample:
	python scripts/send_sample_api_requests.py

cleanup:
	docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/maintenance/cleanup_old_records.py"

drift-check:
	docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_prediction_drift.py"

metrics:
	curl -s http://localhost:8000/metrics | head -80

prometheus:
	docker compose up -d prometheus

prometheus-logs:
	docker compose logs --tail=100 prometheus

prometheus-check:
	docker run --rm \
		--entrypoint promtool \
		-v "$$(pwd)/monitoring/prometheus:/etc/prometheus:ro" \
		prom/prometheus:v2.55.1 \
		check config /etc/prometheus/prometheus.yml

prometheus-rule-test:
	docker run --rm \
		--entrypoint promtool \
		-v "$$(pwd)/monitoring/prometheus:/etc/prometheus:ro" \
		-w /etc/prometheus \
		prom/prometheus:v2.55.1 \
		test rules /etc/prometheus/tests/jobskill_alert_rules.test.yml

alertmanager:
	docker compose up -d alertmanager

alertmanager-logs:
	docker compose logs --tail=100 alertmanager

alertmanager-check:
	docker run --rm \
		--entrypoint amtool \
		-v "$$(pwd)/monitoring/alertmanager:/etc/alertmanager:ro" \
		prom/alertmanager:v0.27.0 \
		check-config /etc/alertmanager/alertmanager.yml

grafana:
	docker compose up -d grafana

grafana-logs:
	docker compose logs --tail=100 grafana

clean-runtime:
	rm -rf airflow_logs/*
	rm -rf reports/*
	rm -rf data/raw/*
	rm -rf data/processed/*

incident-drill:
	docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && API_URL=http://api:8000 ALERTMANAGER_URL=http://alertmanager:9093 python scripts/run_incident_drill.py"