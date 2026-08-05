# jobskill-mlops Quick Start

## 1. 서비스 기동

```bash
make up
```

상태 확인:

```bash
docker compose ps
```

## 2. 기본 smoke check

```bash
make smoke
```

## 3. 운영 정적 검증

```bash
make ops-static-check
```

## 4. 전체 운영 검증

```bash
make ops-check
```

## 5. Production Feedback / Retraining Candidate

샘플 feedback 생성:

```bash
make production-feedback-sample
```

Production feedback 평가:

```bash
make production-feedback-check
```

재학습 후보 판단:

```bash
make retraining-candidate-check
```

## 6. Retraining Strategy and Cost Benchmark

재학습 전략 판단:

```bash
make retraining-strategy-check
```

재학습 전략 리포트 생성:

```bash
make retraining-strategy-report
cat reports/latest_retraining_strategy_report.md
```

학습 비용 리포트 생성:

```bash
make training-cost-report
cat reports/latest_training_cost_report.md
```

DB 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    check_type,
    check_name,
    status,
    metric_value,
    threshold_value,
    checked_at
FROM pipeline_check_results
WHERE check_type IN ('RETRAINING_STRATEGY', 'TRAINING_COST')
ORDER BY checked_at DESC, check_type, check_name
LIMIT 50;
"
```

## 7. Training Data Selection Policy

기본 모드:

```bash
docker compose exec -T airflow-scheduler bash -lc "
cd /opt/airflow/project &&
TRAINING_DATA_MODE=full python src/training/train_baseline.py
"
```

recent window 실험:

```bash
docker compose exec -T airflow-scheduler bash -lc "
cd /opt/airflow/project &&
TRAINING_DATA_MODE=recent TRAINING_RECENT_DAYS=90 python src/training/train_baseline.py
"
```

recent + historical sample 실험:

```bash
docker compose exec -T airflow-scheduler bash -lc "
cd /opt/airflow/project &&
TRAINING_DATA_MODE=recent_plus_history_sample TRAINING_RECENT_DAYS=90 TRAINING_HISTORY_SAMPLE_ROWS_PER_CLASS=50 python src/training/train_baseline.py
"
```

## 8. Training Cost Metrics

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_training_"
```

## 9. Prometheus / Alert 검증

```bash
make metrics-contract-check
make prometheus-check
make prometheus-rule-test
make runbook-check
make alert-rule-metric-check
```

## 10. Evidence Bundle 생성

```bash
make ops-report
make retraining-strategy-report
make training-cost-report
make ops-evidence-bundle
make ops-evidence-check
```

ZIP 확인:

```bash
unzip -l reports/ops_evidence/jobskill_ops_evidence_*.zip | grep -E "latest_retraining_strategy_report|latest_training_cost_report"
```

## 11. CI 진단 산출물

실패 진단 수집:

```bash
make ci-diagnostics
```

생성 위치:

```text
reports/ci_diagnostics/
```
