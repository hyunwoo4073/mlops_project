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

## 3. 기본 검증

```bash
make ops-static-check
make smoke
```

## 4. 운영 검증 전체 실행

```bash
make ops-check
```

## 5. Production Feedback / Retraining

```bash
make production-feedback-sample
make production-feedback-check
make retraining-candidate-check
```

metric 확인:

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_production_feedback|jobskill_retraining_candidate"
```

## 6. Alert Lifecycle / Synthetic Alert 정리

```bash
make alert-webhook-lifecycle-check
make synthetic-alert-plan
make synthetic-alert-cleanup
make synthetic-alert-check
```

## 7. 운영 리포트 / 증빙 번들

```bash
make ops-report
make ops-evidence-bundle
make ops-evidence-check
```

## 8. CI evidence 흐름 로컬 확인

```bash
make ops-evidence-ci
```

## 9. CI diagnostics 로컬 확인

```bash
make ci-diagnostics
ls -R reports/ci_diagnostics | head -80
```

## 권장 최종 검증 흐름

```bash
make ops-check
make ops-report
make ops-evidence-bundle
make ops-evidence-check
```
