COMPOSE ?= docker compose
PROJECT_DIR ?= /opt/airflow/project
AIRFLOW_SERVICE ?= airflow-scheduler
POSTGRES_CONTAINER ?= jobskill-postgres
POSTGRES_USER ?= jobskill
POSTGRES_DB ?= jobskill
DAG_ID ?= jobskill_mlops_pipeline
API_URL ?= http://localhost:8000
PROMETHEUS_URL ?= http://localhost:9090
ALERTMANAGER_URL ?= http://localhost:9093
PROMETHEUS_IMAGE ?= prom/prometheus:v2.55.1
ALERTMANAGER_IMAGE ?= prom/alertmanager:v0.27.0
LIMIT ?= 30
WRONG_EVERY ?= 5

AIRFLOW_SERVICES := \
	airflow-apiserver \
	airflow-scheduler \
	airflow-dag-processor \
	airflow-triggerer

APP_SERVICES := \
	mlflow \
	api \
	dashboard \
	alertmanager \
	prometheus \
	grafana

ALL_RUNTIME_SERVICES := $(AIRFLOW_SERVICES) $(APP_SERVICES)

.PHONY: \
	help \
	build up down restart ps logs \
	airflow-init create-tables psql \
	dag-list dag-errors dag-tasks dag-trigger dag-runs \
	lint test test-container ci \
	smoke data-contract-check model-class-performance-check drift-check production-feedback-sample production-feedback-check \
	alert-workflow-check runbook-check metrics-contract-check alert-rule-metric-check ops-static-check ops-check repo-artifact-check compose-config-check \
	report incident-report incident-drill model-archive model-card model-card-check model-rollback-plan model-rollback model-lifecycle-check \
	notify notification-check notification-test-alert notification-resolve-alert \
	dashboard dashboard-logs \
	api api-logs api-sample \
	mlflow mlflow-logs \
	cleanup clean-runtime \
	metrics \
	prometheus prometheus-logs prometheus-check prometheus-rule-test prometheus-external-target-check \
	alertmanager alertmanager-logs alertmanager-check \
	grafana grafana-logs

help:
	@echo ""
	@echo "JobSkill MLOps Commands"
	@echo ""
	@echo "Build / Run"
	@echo "  make build                                  Build Airflow and API images"
	@echo "  make up                                     Start Airflow, MLflow, API, Dashboard, Alertmanager, Prometheus and Grafana"
	@echo "  make down                                   Stop services"
	@echo "  make restart                                Recreate main runtime services"
	@echo "  make ps                                     Show container status"
	@echo "  make logs                                   Show all service logs"
	@echo ""
	@echo "Database / Airflow"
	@echo "  make airflow-init                           Initialize Airflow metadata DB"
	@echo "  make create-tables                          Create or update project DB tables"
	@echo "  make psql                                   Open PostgreSQL shell"
	@echo ""
	@echo "DAG"
	@echo "  make dag-list                               List DAGs"
	@echo "  make dag-errors                             Show DAG import errors"
	@echo "  make dag-tasks                              List pipeline DAG tasks"
	@echo "  make dag-trigger                            Trigger pipeline DAG"
	@echo "  make dag-runs                               List pipeline DAG runs"
	@echo ""
	@echo "Quality / MLOps Validation"
	@echo "  make lint                                   Run ruff"
	@echo "  make test                                   Run local pytest"
	@echo "  make test-container                         Run pytest in Airflow container"
	@echo "  make ci                                     Run lint and pytest"
	@echo "  make smoke                                  Run service smoke checks"
	@echo "  make data-contract-check                    Validate raw/cleaned/skill data contract"
	@echo "  make model-class-performance-check          Validate class-level model performance"
	@echo "  make drift-check                            Run prediction distribution drift check"
	@echo "  make production-feedback-sample             Create sample feedback from recent predictions"
	@echo "  make production-feedback-check              Evaluate production feedback performance"
	@echo ""
	@echo "Ops Validation"
	@echo "  make alert-workflow-check                   Run alert workflow smoke check"
	@echo "  make runbook-check                          Validate alert runbook coverage"
	@echo "  make metrics-contract-check                 Validate required Prometheus metrics"
	@echo "  make alert-rule-metric-check                Validate alert rule metric dependencies"
	@echo "  make ops-static-check                       Run static ops validation checks"
	@echo "  make ops-check                              Run full local ops validation checks"
	@echo "  make repo-artifact-check                    Check generated/runtime artifacts are not committed"
	@echo "  make compose-config-check                   Validate rendered Docker Compose config"
	@echo ""
	@echo "Reports / Model Ops"
	@echo "  make report                                 Generate pipeline report"
	@echo "  make incident-report                        Generate incident response report"
	@echo "  make incident-drill                         Run synthetic incident response drill"
	@echo "  make model-archive                          Archive current promoted model"
	@echo "  make model-card                             Generate promoted model card report"
	@echo "  make model-card-check                       Validate latest Model Card consistency"
	@echo "  make model-rollback-plan                    Show promoted model rollback plan"
	@echo "  make model-rollback                         Roll back to archived promoted model"
	@echo "  make model-lifecycle-check                  Validate model registry, archive and rollback integrity"
	@echo ""
	@echo "Apps"
	@echo "  make dashboard                              Start Streamlit dashboard"
	@echo "  make dashboard-logs                         Show dashboard logs"
	@echo "  make api                                    Start FastAPI"
	@echo "  make api-logs                               Show FastAPI logs"
	@echo "  make api-sample                             Send sample prediction requests to FastAPI"
	@echo "  make mlflow                                 Start MLflow"
	@echo "  make mlflow-logs                            Show MLflow logs"
	@echo "  make metrics                                Show FastAPI Prometheus metrics"
	@echo ""
	@echo "Monitoring / Alerting"
	@echo "  make prometheus                             Start Prometheus"
	@echo "  make prometheus-logs                        Show Prometheus logs"
	@echo "  make prometheus-check                       Validate Prometheus config and alert rules"
	@echo "  make prometheus-rule-test                   Run Prometheus alert rule unit tests"
	@echo "  make prometheus-external-target-check       Check Prometheus external scrape targets"
	@echo "  make alertmanager                           Start Alertmanager"
	@echo "  make alertmanager-logs                      Show Alertmanager logs"
	@echo "  make alertmanager-check                     Validate Alertmanager config"
	@echo "  make grafana                                Start Grafana"
	@echo "  make grafana-logs                           Show Grafana logs"
	@echo ""
	@echo "Notification"
	@echo "  make notify                                 Send or print pipeline status notification"
	@echo "  make notification-check                     Check Alertmanager and Slack webhook configuration"
	@echo "  make notification-test-alert                Send a test alert through Alertmanager"
	@echo "  make notification-resolve-alert             Resolve the test alert through Alertmanager"
	@echo ""
	@echo "Maintenance"
	@echo "  make cleanup                                Run cleanup retention script"
	@echo "  make clean-runtime                          Remove local runtime output files"
	@echo ""
	@echo "Useful variables"
	@echo "  LIMIT=30 WRONG_EVERY=5 make production-feedback-sample"
	@echo "  MODEL_ROLLBACK_ARCHIVE_ID=1 make model-rollback-plan"
	@echo "  MODEL_ROLLBACK_ARCHIVE_ID=1 make model-rollback"
	@echo ""

build:
	$(COMPOSE) build airflow-image api

up:
	$(COMPOSE) up -d --no-build --force-recreate $(ALL_RUNTIME_SERVICES)

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) up -d --no-build --force-recreate $(ALL_RUNTIME_SERVICES)

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs --tail=100

airflow-init:
	$(COMPOSE) up --no-build airflow-init

create-tables:
	docker exec -i $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) < sql/create_tables.sql

psql:
	docker exec -it $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

dag-list:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) airflow dags list

dag-errors:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) airflow dags list-import-errors

dag-tasks:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) airflow tasks list $(DAG_ID)

dag-trigger:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) airflow dags trigger $(DAG_ID)

dag-runs:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) airflow dags list-runs $(DAG_ID)

lint:
	ruff check src dags scripts tests

test:
	pytest

test-container:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && pytest"

ci: lint test

smoke:
	bash scripts/smoke_check.sh

data-contract-check:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python src/quality/check_data_contract.py"

model-class-performance-check:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python src/quality/check_model_class_performance.py"

drift-check:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python src/quality/check_prediction_drift.py"

production-feedback-sample:
	$(COMPOSE) exec -T $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python scripts/create_sample_prediction_feedback.py --limit $${LIMIT:-$(LIMIT)} --wrong-every $${WRONG_EVERY:-$(WRONG_EVERY)}"

production-feedback-check:
	$(COMPOSE) exec -T $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python src/quality/check_production_feedback.py"

alert-workflow-check:
	bash scripts/check_alert_workflow.sh

runbook-check:
	python scripts/check_runbook_coverage.py

metrics-contract-check:
	python scripts/check_metrics_contract.py --url $(API_URL)/metrics

alert-rule-metric-check:
	python scripts/check_alert_rule_metric_dependencies.py --url $(API_URL)/metrics

ops-static-check:
	bash scripts/check_static_ops_validation.sh

ops-check:
	bash scripts/check_ops_validation.sh

repo-artifact-check:
	./scripts/check_repository_artifacts.sh

compose-config-check:
	python scripts/check_compose_rendered_config.py

report:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python src/reporting/generate_pipeline_report.py"

incident-report:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python src/reporting/generate_incident_response_report.py"

incident-drill:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && API_URL=http://api:8000 ALERTMANAGER_URL=http://alertmanager:9093 python scripts/run_incident_drill.py"

model-archive:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python scripts/archive_promoted_model.py"

model-card:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python src/reporting/generate_model_card.py"

model-card-check:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python scripts/check_model_card_consistency.py"

model-rollback-plan:
	$(COMPOSE) exec \
		-e MODEL_ROLLBACK_ARCHIVE_ID="$${MODEL_ROLLBACK_ARCHIVE_ID:-}" \
		-e MODEL_ROLLBACK_CREATED_BY="$${MODEL_ROLLBACK_CREATED_BY:-local-user}" \
		-e MODEL_ROLLBACK_REASON="$${MODEL_ROLLBACK_REASON:-Manual rollback to archived promoted model.}" \
		-e MODEL_ROLLBACK_DRY_RUN=true \
		$(AIRFLOW_SERVICE) \
		bash -lc "cd $(PROJECT_DIR) && python scripts/rollback_promoted_model.py"

model-rollback:
	$(COMPOSE) exec \
		-e MODEL_ROLLBACK_ARCHIVE_ID="$${MODEL_ROLLBACK_ARCHIVE_ID:-}" \
		-e MODEL_ROLLBACK_CREATED_BY="$${MODEL_ROLLBACK_CREATED_BY:-local-user}" \
		-e MODEL_ROLLBACK_REASON="$${MODEL_ROLLBACK_REASON:-Manual rollback to archived promoted model.}" \
		-e MODEL_ROLLBACK_DRY_RUN=false \
		$(AIRFLOW_SERVICE) \
		bash -lc "cd $(PROJECT_DIR) && python scripts/rollback_promoted_model.py"

model-lifecycle-check:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python scripts/check_model_lifecycle_integrity.py"

notify:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python src/notification/notify_pipeline_status.py"

notification-check:
	python scripts/check_notification_channel.py

notification-test-alert:
	SEND_TEST_ALERT=true python scripts/check_notification_channel.py

notification-resolve-alert:
	SEND_TEST_ALERT=true RESOLVE_TEST_ALERT=true python scripts/check_notification_channel.py

dashboard:
	$(COMPOSE) up -d dashboard

dashboard-logs:
	$(COMPOSE) logs --tail=100 dashboard

api:
	$(COMPOSE) up -d api

api-logs:
	$(COMPOSE) logs --tail=100 api

api-sample:
	python scripts/send_sample_api_requests.py

mlflow:
	$(COMPOSE) up -d mlflow

mlflow-logs:
	$(COMPOSE) logs --tail=100 mlflow

cleanup:
	$(COMPOSE) exec $(AIRFLOW_SERVICE) bash -lc "cd $(PROJECT_DIR) && python src/maintenance/cleanup_old_records.py"

clean-runtime:
	rm -rf airflow_logs/*
	rm -rf reports/*
	rm -rf data/raw/*
	rm -rf data/processed/*

metrics:
	curl -s $(API_URL)/metrics | head -80

prometheus:
	$(COMPOSE) up -d prometheus

prometheus-logs:
	$(COMPOSE) logs --tail=100 prometheus

prometheus-check:
	docker run --rm \
		--entrypoint promtool \
		-v "$$(pwd)/monitoring/prometheus:/etc/prometheus:ro" \
		$(PROMETHEUS_IMAGE) \
		check config /etc/prometheus/prometheus.yml

prometheus-rule-test:
	docker run --rm \
		--entrypoint promtool \
		-v "$$(pwd)/monitoring/prometheus:/etc/prometheus:ro" \
		-w /etc/prometheus \
		$(PROMETHEUS_IMAGE) \
		test rules /etc/prometheus/tests/jobskill_alert_rules.test.yml

prometheus-external-target-check:
	python scripts/check_prometheus_external_targets.py --prometheus-url $(PROMETHEUS_URL)

alertmanager:
	$(COMPOSE) up -d alertmanager

alertmanager-logs:
	$(COMPOSE) logs --tail=100 alertmanager

alertmanager-check:
	docker run --rm \
		--entrypoint amtool \
		-v "$$(pwd)/monitoring/alertmanager:/etc/alertmanager:ro" \
		$(ALERTMANAGER_IMAGE) \
		check-config /etc/alertmanager/alertmanager.yml

grafana:
	$(COMPOSE) up -d grafana

grafana-logs:
	$(COMPOSE) logs --tail=100 grafana
