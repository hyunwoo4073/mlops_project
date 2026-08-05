# jobskill-mlops Summary

## 프로젝트 개요

`jobskill-mlops`는 채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow/MLflow/FastAPI/Streamlit/Prometheus/Alertmanager/Grafana를 연결해 end-to-end MLOps 운영 흐름을 구성한 프로젝트입니다.

## 핵심 아키텍처

```text
PostgreSQL
- raw_job_posts
- cleaned_job_posts
- job_post_skills
- model_predictions
- prediction_feedbacks
- pipeline_check_results
- model_registry
- alert_events
- alert_current_states

Airflow
- jobskill_mlops_pipeline
- jobskill_feedback_ops

MLflow
- training dataset tracking
- evaluation artifact
- model artifact
- training cost metric

FastAPI
- /predict
- /health
- /ready
- /metrics
- /alertmanager/webhook
- /runbooks

Streamlit
- model lifecycle
- model evaluation
- model card
- production feedback
- retraining candidate
- alert history
- incident report

Prometheus / Alertmanager / Grafana
- metrics contract
- alert rule
- rule test
- runbook
- Slack notification
```

## 최근 개선: Retraining Strategy and Cost Benchmark

2026-08-04 ~ 2026-08-05 작업으로 production feedback 기반 재학습 후보 판단 이후, 어떤 방식으로 재학습할지 판단하는 운영 계층을 추가했습니다.

```text
Production Feedback
→ Retraining Candidate
→ Retraining Strategy Check
→ Training Cost Benchmark
→ Training Cost Monitoring
→ Training Data Selection Policy
```

추가된 주요 파일:

```text
src/quality/check_retraining_strategy.py
src/reporting/generate_retraining_strategy_report.py
src/common/training_cost.py
src/reporting/generate_training_cost_report.py
src/training/training_data_selector.py
docs/runbooks/jobskill_training_duration_high.md
```

추가된 Makefile target:

```text
retraining-strategy-check
retraining-strategy-report
training-cost-report
```

추가된 report:

```text
reports/latest_retraining_strategy_report.md
reports/latest_training_cost_report.md
```

추가된 check_type:

```text
RETRAINING_STRATEGY
TRAINING_COST
```

추가된 주요 metric:

```text
jobskill_training_duration_seconds
jobskill_training_duration_threshold_seconds
jobskill_training_rows
jobskill_training_category_count
jobskill_training_throughput_rows_per_second
jobskill_training_model_size_bytes
jobskill_training_incremental_experiment_by_duration
```

추가된 alert:

```text
JobSkillTrainingDurationHigh
```

## 운영 검증 명령어

```bash
make ops-static-check
make ops-check
make smoke
make metrics-contract-check
make prometheus-check
make prometheus-rule-test
make runbook-check
make alert-rule-metric-check
```

## 재학습 전략 검증 명령어

```bash
make production-feedback-check
make retraining-candidate-check
make retraining-strategy-check
make retraining-strategy-report
make training-cost-report
```

## Evidence Bundle

운영 검증 결과는 evidence bundle로 묶습니다.

```bash
make ops-report
make retraining-strategy-report
make training-cost-report
make ops-evidence-bundle
make ops-evidence-check
```

포함되는 주요 파일:

```text
README.md
docs/README_SUMMARY.md
docs/QUICKSTART.md
docs/README_FULL.md
reports/latest_ops_validation_report.md
reports/latest_retraining_strategy_report.md
reports/latest_training_cost_report.md
docs/runbooks/*
monitoring/metrics_contract.yml
monitoring/prometheus/rules/jobskill_alert_rules.yml
monitoring/prometheus/tests/jobskill_alert_rules.test.yml
monitoring/alertmanager/alertmanager.yml
docker-compose.yml
Makefile
```
