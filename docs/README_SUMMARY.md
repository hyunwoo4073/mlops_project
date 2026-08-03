# jobskill-mlops Summary

## 한 줄 요약

채용공고 직무 분류 모델을 중심으로 데이터 적재, 학습, 검증, 배포, feedback 평가, 재학습 후보 판단, monitoring, alert, runbook, 운영 검증 산출물, CI evidence artifact, failure diagnostics까지 연결한 로컬 MLOps 포트폴리오 프로젝트입니다.

## 핵심 가치

```text
단순 모델 학습 프로젝트가 아니라
운영 가능한 MLOps 흐름과 CI 기반 검증/증빙 산출물까지 재현하는 프로젝트
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
→ GitHub Actions Artifact / Failure Diagnostics
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
13. evidence bundle 내부 필수 파일 검증
14. GitHub Actions artifact 기반 성공/실패 산출물 분리
```

## 2026-08-03 개선 요약

```text
Ops Evidence Bundle Validation
- 생성된 evidence ZIP 내부 README, QuickStart, ops report, manifest, runbook 포함 여부 검증

CI Ops Evidence Artifact
- smoke workflow 성공 후 ops evidence bundle 생성/검증
- GitHub Actions artifact로 jobskill-ops-evidence 업로드

CI Failure Diagnostics
- CI 실패 시 compose 상태, 서비스 로그, DB 상태, alert 상태, endpoint 응답 수집
- GitHub Actions artifact로 jobskill-ci-diagnostics 업로드

Compatibility Fix
- Python 3.11 기준 generate_ops_validation_report.py f-string syntax 오류 수정
```

## 검토자용 실행 명령

```bash
make up
make ops-static-check
make smoke
make ops-check
make ops-report
make ops-evidence-bundle
make ops-evidence-check
```

## CI 산출물

```text
jobskill-ops-evidence
- 성공 시 업로드
- 운영 검증 report와 evidence bundle 포함

jobskill-ci-diagnostics
- 실패 시 업로드
- 서비스 로그, DB 상태, alert 상태, HTTP endpoint 응답 포함
```
