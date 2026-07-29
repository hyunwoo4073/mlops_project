# JobSkill MLOps 요약

## 1. 프로젝트 목적

`jobskill-mlops`는 채용공고 데이터를 기반으로 직무 분류 모델을 만들고, 실제 운영에 가까운 MLOps 흐름을 경량 Docker Compose 환경에서 구현한 프로젝트입니다.

핵심 목표는 단순 학습 코드가 아니라 아래 전체 흐름을 연결하는 것입니다.

```text
데이터 수집
→ 전처리
→ 품질 검증
→ 모델 학습
→ MLflow 추적
→ 성능 검증
→ 모델 승격
→ API 추론
→ 운영 지표 노출
→ Alert / Runbook
→ Dashboard 운영
→ Production Feedback
→ Retraining Candidate 판단
```

## 2. 주요 구성

```text
PostgreSQL
- jobskill DB: 프로젝트 데이터, 예측, 검증 결과, 모델 registry 저장
- airflow DB: Airflow metadata 저장
- mlflow DB: MLflow backend store

Airflow
- 전체 파이프라인 오케스트레이션
- 수집, 적재, 전처리, 검증, 학습, 승격, 예측, 리포트 task 실행

MLflow
- 학습 run, metric, model artifact, dataset profile, evaluation artifact 저장

FastAPI
- /predict 단건 예측
- /health, /ready readiness/liveness
- /metrics Prometheus 지표 노출
- /alertmanager/webhook alert 수신
- /runbooks runbook HTML 서빙

Streamlit Dashboard
- 모델/데이터/API 품질 조회
- Model Lifecycle / Evaluation / Card 조회
- Alert History / Current Alerts / Incident Report 조회
- Production Feedback 입력, 평가, 이력, 재학습 후보 판단

Prometheus / Alertmanager / Grafana
- 운영 metric 수집
- alert rule 평가
- Slack notification
- Grafana dashboard 시각화
```

## 3. 핵심 MLOps 기능

```text
Data Quality
- Data Contract Check
- training data quality check
- source별 품질 리포트

Model Quality
- MLflow dataset tracking
- classification report / confusion matrix artifact
- model performance gate
- class-level performance gate
- prediction quality gate
- prediction drift gate

Model Operations
- best model promotion
- promoted model archive
- rollback dry-run / rollback CLI
- model lifecycle integrity check
- model card 생성

Serving Operations
- FastAPI serving model reload
- API prediction log 저장
- API readiness metric
- latency / confidence / error 상태 확인

Alert Operations
- Prometheus alert rule
- Alertmanager webhook + Slack
- runbook URL 연결
- acknowledgement / silence / maintenance mode
- MTTA / MTTR metric
- incident response report
```

## 4. Production Feedback Loop

운영 예측 결과가 실제로 맞았는지 확인하기 위한 feedback 기반 품질 관리 기능입니다.

```text
model_predictions
→ prediction_feedbacks
→ check_production_feedback.py
→ PRODUCTION_FEEDBACK check 저장
→ jobskill_production_feedback_* metric 노출
→ Production Feedback alert
→ runbook 대응
```

주요 metric:

```text
jobskill_production_feedback_total
jobskill_production_feedback_accuracy
jobskill_production_feedback_f1_weighted
jobskill_production_feedback_category_total
```

주요 alert:

```text
JobSkillProductionFeedbackLowAccuracy
JobSkillProductionFeedbackLowF1
```

## 5. Production Feedback Dashboard

Streamlit Dashboard의 `Production Feedback` 탭에서 아래 기능을 제공합니다.

```text
Feedback Input
- 최근 prediction 선택
- actual_category 입력
- feedback_source / note / created_by 저장
- prediction_feedbacks upsert

Evaluation Runner
- Dashboard에서 production feedback 평가 실행
- production_feedback_count / accuracy / weighted_f1 저장

Evaluation History
- accuracy / weighted F1 trend 확인
- feedback count trend 확인
- PASS / FAIL / SKIPPED 이력 확인

Retraining Candidate
- feedback 수 충분성 확인
- 최신 accuracy / weighted F1 기준 확인
- 최근 성능 하락 추세 확인
- 오분류 집중 패턴 확인
- 재학습 후보 여부 판단
```

## 6. Retraining Candidate Loop

Production Feedback 평가 결과를 기반으로 현재 promoted model이 재학습 후보인지 판단합니다.

```text
PRODUCTION_FEEDBACK 평가 이력
→ Retraining Candidate 판단
→ RETRAINING_CANDIDATE check 저장
→ retraining candidate metric 노출
→ Prometheus alert
→ runbook 대응
```

저장되는 check type:

```text
RETRAINING_CANDIDATE
```

주요 metric:

```text
jobskill_retraining_candidate_flag
jobskill_retraining_candidate_feedback_count
jobskill_retraining_candidate_accuracy
jobskill_retraining_candidate_f1_weighted
jobskill_retraining_candidate_accuracy_delta
jobskill_retraining_candidate_f1_delta
```

주요 alert:

```text
JobSkillRetrainingCandidateDetected
```

## 7. 운영 검증 체계

서비스 기동 전후로 아래 검증을 수행합니다.

```bash
make metrics-contract-check
make prometheus-check
make prometheus-rule-test
make runbook-check
make alert-rule-metric-check
make ops-static-check
make smoke
```

검증 대상:

```text
Python syntax
Docker Compose rendered config
Prometheus config / alert rule
Prometheus rule unit test
Alertmanager config
Runbook coverage
Metrics contract
Alert rule metric dependency
API / Dashboard / Prometheus / Alertmanager / Grafana smoke path
```

## 8. 포트폴리오에서 강조할 점

```text
1. 단순 모델 학습이 아니라 운영 가능한 MLOps loop를 구현함
2. MLflow, Airflow, FastAPI, Streamlit, Prometheus, Alertmanager, Grafana를 end-to-end로 연결함
3. 모델 승격, archive, rollback, lifecycle integrity check를 구현함
4. alert, runbook, acknowledgement, silence, MTTA/MTTR, incident report까지 운영 대응 흐름을 구현함
5. production feedback 기반 운영 성능 평가와 retraining candidate alert까지 연결함
```
