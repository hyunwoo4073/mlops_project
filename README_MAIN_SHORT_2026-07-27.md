# jobskill-mlops project

[![Python CI](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml)
[![Smoke Check](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml)

채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow, MLflow, FastAPI, Streamlit, Prometheus, Alertmanager, Grafana를 연결해 **데이터 수집부터 모델 운영 검증, 알림, runbook 대응까지 구성한 경량 end-to-end MLOps 프로젝트**입니다.

## 문서

```text
README.md
- 프로젝트 메인 소개

docs/README_SUMMARY.md
- 프로젝트 핵심 요약

docs/QUICKSTART.md
- 로컬 실행 및 검증 가이드

docs/runbooks/
- alert별 운영 대응 문서
```

처음 보는 경우 아래 순서로 읽는 것을 권장합니다.

```text
1. docs/README_SUMMARY.md
2. docs/QUICKSTART.md
3. README.md 또는 docs/README_FULL.md
```

## 핵심 기능

```text
데이터 소스 모드(sample_only / crawler_only / mixed)
Remote OK crawler retry / fallback
Data Contract Check
MLflow training dataset tracking
MLflow evaluation artifact 저장
Class-level model performance gate
Best model promotion
Model Card 생성
Promoted model archive / rollback
FastAPI serving
Batch inference
Prediction quality / drift gate
Prometheus metrics
Prometheus alert rules
Alertmanager Slack notification
Alertmanager notification failure monitoring
Runbook coverage check
Metrics contract check
Alert rule metric dependency check
Ops validation check
```

## 빠른 실행

```bash
docker compose up -d postgres
docker compose run --rm airflow-init
docker compose up -d airflow-apiserver airflow-scheduler airflow-dag-processor airflow-triggerer
docker compose up -d mlflow api dashboard alertmanager prometheus grafana
```

상태 확인:

```bash
docker compose ps
curl -fsS http://localhost:8000/health | jq
curl -fsS http://localhost:8000/ready | jq
```

자세한 실행 순서는 `docs/QUICKSTART.md`를 참고합니다.

## 주요 검증 명령어

```bash
make runbook-check
make metrics-contract-check
make alert-rule-metric-check
make prometheus-rule-test
make ops-check
```

## 접속 정보

```text
Airflow      : http://localhost:8080
MLflow       : http://localhost:5000
FastAPI      : http://localhost:8000
Streamlit    : http://localhost:8501
Prometheus   : http://localhost:9090
Alertmanager : http://localhost:9093
Grafana      : http://localhost:3000
```

## 최근 개선

```text
Alertmanager notification failure monitoring
external_metrics 기반 multi-source metrics contract
multi-source alert rule metric dependency check
DB row가 없어도 required metric을 0으로 노출하는 metric 안정화
README 요약본 / Quick Start 문서 분리
```

## 상세 문서

상세 구현 내역과 트러블슈팅은 `docs/README_FULL.md` 또는 기존 상세 README를 참고합니다.
