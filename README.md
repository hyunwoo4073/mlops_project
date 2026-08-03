# jobskill-mlops

[![Python CI](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml)
[![Smoke Check](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml)

채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow, MLflow, FastAPI, Streamlit, Prometheus, Alertmanager, Grafana를 연결해 로컬에서 end-to-end MLOps 운영 흐름을 검증하는 프로젝트입니다.

이 프로젝트는 단순 모델 학습이 아니라 데이터 품질 검증, 모델 성능 검증, 모델 승격/롤백, API serving, production feedback 평가, 재학습 후보 판단, Prometheus metric, alert rule, runbook, smoke check, ops report, evidence bundle까지 포함한 운영형 MLOps 파이프라인을 목표로 합니다.

## 문서 구성

```text
README.md
- 프로젝트를 처음 보는 사람을 위한 간단한 메인 소개 문서입니다.

docs/README_SUMMARY.md
- 포트폴리오 검토자에게 보여주기 위한 요약 문서입니다.

docs/README_FULL.md
- 전체 구현 상세, 운영 기능, 트러블슈팅, 검증 절차를 담은 상세 문서입니다.

docs/QUICKSTART.md
- 로컬에서 직접 실행하고 검증하기 위한 명령어 중심 가이드입니다.
```

권장 확인 순서:

```text
README.md
→ docs/README_SUMMARY.md
→ docs/QUICKSTART.md
→ docs/README_FULL.md
```

## Architecture

```text
Job Data
→ PostgreSQL
→ Airflow Pipeline
→ Data Contract / Quality Checks
→ Model Training
→ MLflow Tracking
→ Model Promotion / Archive / Rollback
→ Batch Prediction / FastAPI Prediction
→ Production Feedback
→ Retraining Candidate Check
→ Prometheus Metrics
→ Alertmanager / Slack / Runbook
→ Streamlit / Grafana Dashboard
→ Ops Check / Ops Report / Evidence Bundle
```

## 주요 기능

```text
Data / Pipeline
- sample, crawler, mixed 데이터 소스 모드
- raw / cleaned / skill 테이블 적재
- Airflow 기반 pipeline orchestration
- data contract validation
- pipeline_check_results 기반 품질 검증 이력 저장

ML Lifecycle
- TF-IDF + Logistic Regression 직무 분류 모델
- MLflow experiment / artifact / dataset tracking
- class-level model performance gate
- best model promotion
- promoted model archive
- rollback dry-run / rollback execution
- model lifecycle integrity check
- model card 생성

Serving / Feedback
- FastAPI /predict
- API prediction log 저장
- production feedback 입력/조회
- production accuracy / weighted F1 평가
- retraining candidate 판단
- feedback ops 전용 Airflow DAG

Monitoring / Alerting
- FastAPI /health, /ready, /metrics
- Prometheus scrape / alert rule
- Alertmanager webhook
- Slack notification
- alert current state / alert history 저장
- runbook HTML serving
- MTTA / MTTR / acknowledgement metric
- maintenance mode / silence / incident report

Ops Validation
- Makefile 기반 명령어 표준화
- smoke check
- static ops validation
- ops-check 통합 검증
- synthetic alert cleanup
- alert webhook lifecycle check
- ops validation report
- ops evidence bundle ZIP 생성
```

## 주요 명령어

```bash
make help

make build
make up
make create-tables

make dag-list
make dag-errors
make dag-tasks

make ops-static-check
make smoke
make ops-check

make production-feedback-sample
make production-feedback-check
make retraining-candidate-check

make feedback-ops-dag-tasks
make feedback-ops-dag-trigger

make alert-webhook-lifecycle-check
make synthetic-alert-check

make ops-report
make ops-evidence-bundle
```

## 접속 URL

```text
FastAPI      http://localhost:8000
Airflow      http://localhost:8080
MLflow       http://localhost:5000
Streamlit    http://localhost:8501
Prometheus   http://localhost:9090
Alertmanager http://localhost:9093
Grafana      http://localhost:3000
```

## 최근 업데이트

```text
2026-07-31
- Makefile을 카테고리별로 정리
- static ops validation / smoke check / ops-check 구조 정리
- synthetic alert cleanup 도구 추가
- alert webhook lifecycle check 추가
- ops validation report 생성 기능 추가
- ops evidence bundle 생성 기능 추가

2026-07-30
- retraining candidate check CLI/Makefile/smoke 연결
- feedback ops 전용 Airflow DAG 추가
- production feedback / retraining alert rule 정리
- maintenance mode suppression rule test 반영

2026-07-29
- Streamlit Production Feedback 탭 추가
- Retraining Candidate Dashboard 추가
- retraining candidate metric / alert / runbook 추가

2026-07-28
- Production Feedback Evaluation Loop 추가
- prediction_feedbacks 테이블과 feedback 평가 스크립트 추가
- production feedback metric / alert / runbook 추가
```

## 빠른 실행

```bash
make build
make up
make create-tables
make ops-static-check
make smoke
```

상세 실행 절차는 `docs/QUICKSTART.md`를 확인합니다.
