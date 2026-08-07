# jobskill-mlops project

[![Python CI](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml)
[![Smoke Check](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml)

채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow와 MLflow를 이용해 데이터 수집, 원천 적재, 전처리, 데이터 품질 검증, 모델 학습, 성능 검증, 모델 승격, API 추론, 운영 모니터링, 재학습 판단, evidence report 생성까지 연결하는 경량 MLOps 파이프라인 프로젝트입니다.

이 프로젝트는 단순한 모델 학습 예제가 아니라, 데이터 수집부터 모델 운영 이후의 feedback/evidence 기반 재학습 판단까지 end-to-end 흐름을 구성하는 것을 목표로 합니다.

## 문서 구성

```text
README.md
- 프로젝트 메인 소개와 빠른 실행 흐름을 담는 짧은 문서입니다.

docs/README_FULL.md
- 전체 구현 상세, 운영 기능, 트러블슈팅, 검증 절차를 담는 상세 문서입니다.

docs/README_SUMMARY.md
- 포트폴리오 검토자가 빠르게 구조와 핵심 기능을 파악하기 위한 요약본입니다.

docs/QUICKSTART.md
- 로컬 실행, 검증 명령어, 리포트 확인 순서를 담는 실행 가이드입니다.
```

## 핵심 기능

```text
Data Ingestion
- Remote OK crawler 기반 채용공고 수집
- raw_job_posts 적재 및 crawled_at 기반 event-time 관리
- crawler 실패 시 기존 raw data fallback

Training Pipeline
- Airflow DAG 기반 수집 → 전처리 → 품질 검증 → 학습 → 평가 → 승격 → batch inference
- MLflow 기반 학습 metric, model artifact, evaluation artifact, training dataset tracking
- model promotion, archive, rollback, model card 생성

Retraining Operations
- production feedback 기반 재학습 후보 판단
- retraining strategy / training cost benchmark
- training data selection policy
- event-time 기반 full / lookback / recent / recent+history-sample retrain 실험
- evidence gate 기반 reduced retraining mode 추천 제어

Serving and Dashboard
- FastAPI `/predict`, `/metrics`, `/health`, `/ready`
- Streamlit dashboard 기반 Model Lifecycle, Model Evaluation, Production Feedback, Alert History 조회

Monitoring and Evidence
- Prometheus / Alertmanager / Grafana 기반 운영 모니터링
- alert rule unit test, metrics contract validation, runbook coverage check
- ops validation report와 ops evidence bundle 생성
```

## 2026-08-07 주요 업데이트

```text
Training Event Time Resolution
- raw_job_posts.crawled_at을 training_event_at으로 표준화
- 5,370 rows 전체가 usable event time을 가지며 242개 날짜에 분포하는 것을 확인
- full=5,370, recent=3,171, recent_plus_history_sample=3,671 rows로 실제 row reduction 확인

Training Data Selection Experiment
- full / recent / recent_plus_history_sample shadow experiment runner 구성
- postgres DNS 일시 실패에 대비해 retry와 transient failure detection 추가
- mode별 accuracy, weighted F1, selected rows, training duration, model path report 생성

Training Selection Evidence Gate
- baseline row 수, class별 row 수, distinct event dates, actual row reduction을 확인
- 근거 부족 시 INSUFFICIENT_EXPERIMENT_DATA로 판단
- full 유지, shadow promotion 후보, 판단 보류 상태를 분리

Remote OK / Historical Seed 역할 분리
- Remote OK crawler는 실제 ingestion 경로로 유지
- local policy validation을 위한 historical seed는 별도 source(remoteok_seed)로 분리

Pandas FutureWarning 제거
- recent_plus_history_sample sampling에서 groupby.apply를 제거하고 for-loop + pd.concat 방식으로 변경
```

## 빠른 실행

서비스 기동:

```bash
make up
```

기본 smoke check:

```bash
make smoke
```

event-time과 training selection 실험:

```bash
make training-event-time-check
make training-data-selection-experiment
make training-data-selection-policy-check
```

운영 evidence 생성:

```bash
make training-cost-report
make ops-report
make ops-evidence-bundle
make ops-evidence-check
```

## 주요 리포트

```text
reports/latest_training_event_time_report.md
- training_event_at source와 event-time coverage 확인

reports/latest_training_data_selection_experiment_report.md
- full/recent/sample mode별 성능과 row reduction 비교

reports/latest_training_data_selection_policy_report.md
- Evidence Gate 기반 reduced retraining mode 추천 여부 판단

reports/latest_training_cost_report.md
- 학습 시간, row 수, throughput, model size 확인

reports/latest_ops_validation_report.md
- 운영 검증 결과 요약

reports/ops_evidence/jobskill_ops_evidence_*.zip
- README, QuickStart, runbook, Prometheus rule/test, metrics contract, validation report를 묶은 포트폴리오 evidence bundle
```

## 현재 운영 판단 기준

```text
full
- 최고 성능 baseline
- 기본 운영 retrain 경로로 유지

recent
- row reduction이 가장 큰 aggressive 비용 절감 후보
- 성능 하락이 더 크므로 반복 shadow validation 필요

recent_plus_history_sample
- row reduction과 성능 보존의 균형이 좋은 우선 shadow validation 후보
- promoted model 자동 변경은 하지 않음
```

## 상세 문서

전체 구현 상세는 `docs/README_FULL.md`, 빠른 검토용 요약은 `docs/README_SUMMARY.md`, 실행 중심 가이드는 `docs/QUICKSTART.md`를 확인합니다.
