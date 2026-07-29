# jobskill-mlops project

[![Python CI](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml)
[![Smoke Check](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml)

채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow, MLflow, PostgreSQL, FastAPI, Streamlit, Prometheus, Alertmanager, Grafana를 연결해 end-to-end MLOps 운영 흐름을 구성하는 프로젝트입니다.

이 프로젝트는 단순 모델 학습이 아니라, 데이터 수집·전처리·품질 검증·모델 학습·성능 검증·모델 승격·API 추론·운영 지표 노출·Alert/Runbook·Dashboard·Rollback·Production Feedback·Retraining Candidate 판단까지 포함합니다.

## 문서 구성

```text
README.md
- 포트폴리오 메인 화면에서 빠르게 볼 수 있는 소개 문서입니다.

docs/README_FULL.md
- 전체 구현 상세, 운영 기능, 검증 절차, 트러블슈팅을 포함한 상세 문서입니다.

docs/README_SUMMARY.md
- 프로젝트 목적, 핵심 아키텍처, 주요 기능, 운영 검증 흐름을 빠르게 파악하기 위한 요약본입니다.

docs/QUICKSTART.md
- 로컬 실행, 서비스 기동, DAG 실행, API/모니터링 검증을 순서대로 따라 하기 위한 실행 가이드입니다.
```

## 핵심 기능

```text
Data Pipeline
- sample / crawler / mixed 데이터 소스 모드
- Remote OK 채용공고 수집 retry / fallback
- PostgreSQL raw / cleaned / skills 테이블 적재
- Data Contract Check와 학습 데이터 품질 검증

Model Lifecycle
- TF-IDF + Logistic Regression 학습
- MLflow run / dataset / evaluation artifact 기록
- class-level model performance gate
- promoted model registry
- promoted model archive
- rollback plan / rollback CLI
- model lifecycle integrity check

Serving & Dashboard
- FastAPI /predict, /health, /ready, /metrics
- API prediction log와 prediction lineage 저장
- Streamlit Dashboard 기반 모델, 데이터, API, Alert, Incident, Model Card 확인
- Production Feedback 입력, 평가, 이력, 재학습 후보 판단

Monitoring & Alerting
- Prometheus metric 수집
- Alertmanager webhook / Slack notification
- alert event/current state 저장
- runbook URL / Grafana / Prometheus link 연결
- alert acknowledgement, silence, maintenance mode, MTTA/MTTR
- Prometheus rule test, runbook coverage, metrics contract, alert dependency check
```

## 최신 업데이트

```text
2026-07-29
- Streamlit Dashboard에 Production Feedback 탭 추가
- Dashboard에서 prediction feedback 입력/수정 기능 추가
- Dashboard에서 production feedback 평가 실행 기능 추가
- Evaluation History 탭으로 accuracy / weighted F1 추세 확인 기능 추가
- Retraining Candidate 탭으로 재학습 후보 판단 기능 추가
- RETRAINING_CANDIDATE 판단 결과를 pipeline_check_results에 저장
- Retraining candidate metric을 FastAPI /metrics에 노출
- JobSkillRetrainingCandidateDetected Prometheus alert rule 추가
- 재학습 후보 감지 runbook과 rule test / maintenance mode suppression test 추가

2026-07-28
- Production Feedback Evaluation Loop 추가
- prediction_feedbacks 테이블, feedback API, 샘플 feedback 생성, production feedback 평가 추가
- production feedback metric, Prometheus alert, Korean runbook, smoke/static validation 반영

2026-07-27
- Alertmanager notification failure monitoring 추가
- external metrics contract와 multi-source alert rule metric dependency check 개선
- required metric 0-value 노출 안정화
```

## 전체 흐름

```text
데이터 수집/생성
→ raw 적재
→ 전처리 / 라벨링 / 기술스택 추출
→ Data Contract Check
→ 학습 데이터 품질 검증
→ 모델 학습 / MLflow 기록
→ 모델 성능 검증 / class-level gate
→ 모델 승격 / archive / rollback 준비
→ batch inference / API inference
→ prediction quality / drift check
→ production feedback 입력
→ production feedback 평가
→ retraining candidate 판단
→ metric 노출
→ Prometheus alert
→ Alertmanager / Slack / Runbook 대응
→ Dashboard / Grafana 운영 확인
```

## 로컬 실행 요약

```bash
cp .env.example .env
mkdir -p .secrets
cp .secrets.example/slack_webhook_url.example .secrets/slack_webhook_url

docker compose up -d postgres
make create-tables

docker compose up -d airflow-apiserver airflow-scheduler airflow-dag-processor airflow-triggerer mlflow api dashboard prometheus alertmanager grafana
make dag-trigger
make api-sample
make production-feedback-sample
make production-feedback-check
```

접속 URL:

```text
Airflow      : http://localhost:8080
MLflow       : http://localhost:5000
FastAPI      : http://localhost:8000
Streamlit    : http://localhost:8501
Prometheus   : http://localhost:9090
Alertmanager : http://localhost:9093
Grafana      : http://localhost:3000
```

## 운영 검증

```bash
make metrics-contract-check
make prometheus-check
make prometheus-rule-test
make runbook-check
make alert-rule-metric-check
make ops-static-check
make smoke
```

## 주요 문서

- [전체 상세 README](docs/README_FULL.md)
- [요약 README](docs/README_SUMMARY.md)
- [Quick Start](docs/QUICKSTART.md)
- [Runbooks](docs/runbooks/)
- [Sample Pipeline Report](docs/sample_pipeline_report.md)
```
