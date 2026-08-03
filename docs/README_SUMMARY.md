# jobskill-mlops Summary

## 한 줄 요약

채용공고 직무 분류 모델을 중심으로 데이터 적재, 학습, 검증, 배포, feedback 평가, 재학습 후보 판단, monitoring, alert, runbook, 운영 검증 산출물까지 연결한 로컬 MLOps 포트폴리오 프로젝트입니다.

## 핵심 가치

```text
단순 모델 학습 프로젝트가 아니라
운영 가능한 MLOps 흐름을 로컬 Docker Compose 환경에서 재현하는 프로젝트
```

## 전체 흐름

```text
Job Posting Data
→ PostgreSQL
→ Airflow
→ Data Quality / Data Contract
→ Model Training
→ MLflow
→ Model Promotion
→ FastAPI / Batch Inference
→ Production Feedback
→ Retraining Candidate
→ Prometheus / Alertmanager
→ Streamlit / Grafana
→ Ops Check / Ops Report / Evidence Bundle
```

## 기술 스택

```text
Python
Airflow
PostgreSQL
MLflow
scikit-learn
FastAPI
Streamlit
Prometheus
Alertmanager
Grafana
Docker Compose
GitHub Actions
```

## 주요 구현 포인트

```text
1. Airflow 기반 end-to-end ML pipeline
2. MLflow 기반 학습 이력, artifact, model registry 관리
3. Data Contract / Quality Gate / Class-level Performance Gate
4. promoted model archive와 rollback CLI
5. FastAPI serving과 prediction log 저장
6. production feedback 기반 운영 성능 재평가
7. retraining candidate 판단 자동화
8. Prometheus metric과 alert rule 구성
9. Alertmanager webhook, Slack alert, runbook 연결
10. Streamlit/Grafana 운영 대시보드
11. smoke/static/ops validation 자동화
12. ops report와 evidence bundle 산출물 생성
```

## 2026-07-31 개선 요약

```text
Makefile 정리
- 명령어를 목적별 카테고리로 재정렬

Static Ops Validation 정리
- Python compile, shell syntax, config, runbook, metric dependency 검증 구조화

Smoke Check 정리
- 서비스 E2E 검증을 카테고리별로 정리
- firing-only SmokeTestAlert 제거
- alert webhook lifecycle 검증 추가

Alert Hygiene 추가
- synthetic alert plan / cleanup / check 도구 추가
- 테스트 alert가 MTTA/MTTR metric을 오염시키지 않도록 개선

Ops Report / Evidence Bundle 추가
- 현재 운영 상태를 Markdown report로 저장
- README, runbook, monitoring config, ops report를 ZIP 증빙으로 패키징
```

## 검토자용 실행 명령

```bash
make up
make ops-static-check
make smoke
make ops-check
make ops-report
make ops-evidence-bundle
```

## 산출물

```text
reports/latest_ops_validation_report.md
reports/ops_evidence/jobskill_ops_evidence_*.zip
reports/latest_model_card.md
reports/latest_incident_response_report.md
docs/runbooks/*.md
```
