# JobSkill MLOps Quick Start

## 1. 서비스 기동

```bash
make build
make up
```

## 2. DB 테이블 생성

```bash
make create-tables
```

## 3. Airflow 확인

```bash
make dag-list
make dag-errors
make dag-tasks
make feedback-ops-dag-tasks
```

## 4. 기본 endpoint 확인

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
curl -fsS http://localhost:8000/model
curl -fsS http://localhost:8000/metrics | head
```

## 5. 기본 검증

```bash
make ops-static-check
make smoke
```

## 6. 운영 검증 전체 실행

```bash
make ops-check
```

## 7. Production Feedback / Retraining

```bash
make production-feedback-sample
make production-feedback-check
make retraining-candidate-check
```

metric 확인:

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_production_feedback|jobskill_retraining_candidate"
```

## 8. Feedback Ops DAG

```bash
make feedback-ops-dag-tasks
make feedback-ops-dag-info
make feedback-ops-dag-trigger
```

## 9. Alert Lifecycle / Synthetic Alert 정리

```bash
make alert-webhook-lifecycle-check
make synthetic-alert-plan
make synthetic-alert-cleanup
make synthetic-alert-check
```

## 10. 운영 리포트 / 증빙 번들

```bash
make ops-report
cat reports/latest_ops_validation_report.md

make ops-evidence-bundle
ls -lh reports/ops_evidence/
```

## 권장 최종 검증 흐름

```bash
make ops-check
make ops-report
make ops-evidence-bundle
```
