# jobskill-mlops project

[![Python CI](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml)
[![Smoke Check](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml)

채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow, MLflow, FastAPI, Streamlit, Prometheus, Alertmanager를 연결해 end-to-end MLOps 운영 흐름을 구성하는 프로젝트입니다.

이 프로젝트의 목적은 단순히 모델을 학습하는 것이 아니라, 데이터 품질 검증, 모델 성능 검증, 모델 승격, batch/API inference, production feedback 평가, 재학습 후보 판단, 운영 metric 노출, alert rule, runbook, smoke check까지 연결해 실제 운영 관점의 MLOps 파이프라인을 실습하는 것입니다.

## 문서 구성

```text
README.md
- 프로젝트 개요, 핵심 아키텍처, 주요 실행 명령어를 빠르게 확인하는 메인 문서

docs/README_FULL.md
- 전체 구현 상세, 운영 기능, 트러블슈팅, 검증 절차를 담은 상세 문서

docs/README_SUMMARY.md
- 포트폴리오 검토자가 빠르게 볼 수 있는 요약 문서

docs/QUICKSTART.md
- 로컬에서 서비스를 기동하고 검증하는 실행 가이드
```

## 주요 기능

```text
Data Pipeline
- sample / crawler / mixed 데이터 소스 모드
- PostgreSQL raw / cleaned / skill 테이블 적재
- Data Contract Check
- Training Data Quality Check

Model Lifecycle
- TF-IDF + Logistic Regression 모델 학습
- MLflow experiment / metric / artifact 기록
- Class-level model performance gate
- Best model promotion
- Promoted model archive
- Rollback CLI
- Model card 생성
- Model lifecycle integrity check

Serving
- FastAPI /predict
- FastAPI /health, /ready
- FastAPI /model, /reload-model
- Batch inference
- API prediction log
- model_predictions 기반 inference lineage 저장

Production Feedback
- prediction_feedbacks 테이블
- 예측 결과별 actual label feedback 저장
- production accuracy / weighted F1 평가
- Production Feedback Dashboard
- Evaluation History
- Retraining Candidate 판단
- Feedback Ops Airflow DAG

Monitoring / Alerting
- FastAPI /metrics
- Prometheus scrape
- Prometheus alert rule
- Prometheus rule unit test
- Alertmanager webhook
- Slack notification
- Alert current state / event 저장
- Runbook URL 연결
- Streamlit maintenance mode
- Alertmanager silence
- MTTA / MTTR 기반 alert response metric
```

## 2026-07-30 업데이트

```text
- 재학습 후보 판단 스크립트를 Makefile, static validation, smoke check에 연결
- `retraining-candidate-check` target 추가
- Production Feedback 평가와 Retraining Candidate 판단을 전용 Airflow DAG로 분리
- `dags/jobskill_feedback_ops_dag.py` 추가
- `jobskill_feedback_ops` DAG에 daily/manual schedule 제어 추가
- `FEEDBACK_OPS_DAG_SCHEDULE` 환경변수 추가
- Feedback Ops DAG에 max_active_runs, dagrun_timeout, retry 설정 적용
- Production Feedback / Retraining Candidate alert rule에 maintenance mode 조건 정리
- model-quality 계열 alert의 dashboard_url을 Streamlit Dashboard인 `http://localhost:8501` 기준으로 정리
- Prometheus rule test에 Production Feedback firing/suppression 케이스 추가
- `SmokeTestAlert` 테스트 current state가 MTTA/MTTR alert를 유발할 수 있음을 확인하고 정리 절차 문서화
```

## 아키텍처 요약

```text
Airflow
→ raw data 준비
→ preprocessing
→ data contract / training data check
→ model train
→ MLflow tracking
→ model performance gate
→ promote model
→ batch inference
→ quality / drift check
→ report / notification

FastAPI
→ /predict
→ model_predictions 저장
→ api_prediction_logs 저장
→ /metrics 노출
→ /alertmanager/webhook alert 저장
→ /runbooks HTML 제공

Streamlit Dashboard
→ 모델/데이터/API 품질 조회
→ Production Feedback 입력/평가
→ Retraining Candidate 판단
→ Alert History / Current Alerts
→ Maintenance Mode / Silence
→ Incident Response Report

Prometheus / Alertmanager
→ FastAPI metric scrape
→ alert rule 평가
→ Alertmanager webhook/Slack 전송
→ runbook 기반 대응
```

## 핵심 실행 명령어

서비스 기동:

```bash
make up
```

테이블 생성:

```bash
make create-tables
```

Airflow DAG 확인:

```bash
make dag-list
make dag-tasks
```

메인 파이프라인 실행:

```bash
make dag-trigger
```

샘플 API 요청:

```bash
make api-sample
```

Production Feedback 샘플 생성 및 평가:

```bash
make production-feedback-sample
make production-feedback-check
```

Retraining Candidate 평가:

```bash
make retraining-candidate-check
```

Feedback Ops DAG 확인 및 실행:

```bash
make feedback-ops-dag-tasks
make feedback-ops-dag-trigger
```

운영 검증:

```bash
make metrics-contract-check
make prometheus-check
make prometheus-rule-test
make alert-rule-metric-check
make runbook-check
make ops-static-check
make smoke
```

## 주요 접속 URL

```text
FastAPI             http://localhost:8000
FastAPI Docs        http://localhost:8000/docs
Streamlit Dashboard http://localhost:8501
MLflow              http://localhost:5000
Prometheus          http://localhost:9090
Alertmanager        http://localhost:9093
Grafana             http://localhost:3000
```

## 오늘 작업 검증 순서

```bash
python -m py_compile src/quality/check_retraining_candidate.py
python -m py_compile dags/jobskill_feedback_ops_dag.py
python -m py_compile src/monitoring/prometheus_metrics.py
python -m py_compile src/dashboard/app.py

make ops-static-check
make production-feedback-sample
make production-feedback-check
make retraining-candidate-check
make feedback-ops-dag-tasks
make prometheus-check
make prometheus-rule-test
make alert-rule-metric-check
make runbook-check
make smoke
```

## 자세한 문서

세부 구현과 운영 절차는 아래 문서를 확인합니다.

```text
docs/README_FULL.md
docs/README_SUMMARY.md
docs/QUICKSTART.md
```
