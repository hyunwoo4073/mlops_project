# jobskill-mlops 요약본

## 1. 프로젝트 한 줄 요약

채용공고 데이터를 수집·전처리해 직무 분류 모델을 학습하고, 모델 승격, API serving, production feedback 평가, Prometheus alert, runbook, dashboard, CI smoke check까지 연결한 경량 end-to-end MLOps 프로젝트입니다.

## 2. 프로젝트 목표

이 프로젝트의 목표는 단순히 모델을 학습하는 것이 아니라, 실제 운영 MLOps에서 필요한 흐름을 작게 구현하는 것입니다.

```text
데이터 수집
→ 전처리
→ 데이터 계약 검증
→ 학습 데이터 품질 검증
→ 모델 학습
→ MLflow 기록
→ 성능 검증
→ 모델 승격
→ API serving
→ 예측 결과 저장
→ 운영 feedback 저장
→ production 성능 평가
→ metric 노출
→ alert / runbook / dashboard 대응
→ CI / smoke / ops validation 검증
```

## 3. 주요 구성

```text
Airflow
- 전체 파이프라인 오케스트레이션

PostgreSQL
- raw / cleaned / skills / predictions / feedback / checks / registry 저장

MLflow
- 학습 run, metric, artifact, model 기록

FastAPI
- /predict
- /health
- /ready
- /metrics
- /alertmanager/webhook
- /runbooks

Streamlit Dashboard
- 데이터/모델/API/alert/model lifecycle/incident report 조회

Prometheus
- FastAPI metrics scrape
- Alertmanager metrics scrape
- alert rule 평가

Alertmanager
- FastAPI webhook 전달
- Slack notification
- silence 관리

Grafana
- 운영 metric dashboard
```

## 4. MLOps 관점 핵심 기능

### 데이터 품질

```text
config/data_contract.json
src/quality/check_data_contract.py
src/quality/check_training_data.py
```

검증 내용:

```text
필수 테이블
필수 컬럼
컬럼 타입
최소 row 수
null ratio
empty ratio
allowed value
Unknown label ratio
class 다양성
```

### 모델 품질

```text
src/training/train_baseline.py
src/quality/check_model_performance.py
src/quality/check_model_class_performance.py
src/training/promote_model.py
```

검증 내용:

```text
accuracy
weighted F1
class별 precision / recall / f1-score / support
promotion threshold
model_registry 저장
best model artifact 생성
```

### 모델 운영

```text
scripts/archive_promoted_model.py
scripts/rollback_promoted_model.py
scripts/check_model_lifecycle_integrity.py
src/reporting/generate_model_card.py
```

기능:

```text
promoted model archive
rollback dry-run
rollback execution
rollback action history
model lifecycle integrity check
model card 생성
```

### Serving / Prediction

```text
src/inference/api.py
src/inference/batch_inference.py
scripts/send_sample_api_requests.py
```

기능:

```text
API prediction
batch inference
prediction lineage 저장
api_prediction_logs 저장
prediction quality check
prediction drift check
```

### Production Feedback

```text
prediction_feedbacks
scripts/create_sample_prediction_feedback.py
src/quality/check_production_feedback.py
src/monitoring/prometheus_metrics.py
```

기능:

```text
예측 결과별 실제 라벨 feedback 저장
sample feedback 생성
production accuracy 계산
production weighted F1 계산
PRODUCTION_FEEDBACK check result 저장
/metrics에 production feedback metric 노출
Prometheus alert rule 연결
runbook 대응
```

## 5. 오늘 추가된 Production Feedback 흐름

```text
model_predictions
→ prediction_feedbacks
→ check_production_feedback.py
→ pipeline_check_results
→ jobskill_production_feedback_* metrics
→ Prometheus alert
→ runbook
```

추가 metric:

```text
jobskill_production_feedback_total
jobskill_production_feedback_accuracy
jobskill_production_feedback_f1_weighted
jobskill_production_feedback_category_total
```

추가 alert:

```text
JobSkillProductionFeedbackLowAccuracy
JobSkillProductionFeedbackLowF1
```

추가 runbook:

```text
docs/runbooks/jobskill_production_feedback_low_accuracy.md
```

## 6. 운영 검증 체계

```text
make smoke
make ops-static-check
make ops-check
make runbook-check
make metrics-contract-check
make alert-rule-metric-check
make prometheus-rule-test
make prometheus-external-target-check
make compose-config-check
make repo-artifact-check
```

검증 대상:

```text
Docker Compose 최종 렌더링 설정
Prometheus config
Prometheus rule syntax
Prometheus rule unit test
Alertmanager config
Runbook coverage
Metrics contract
Alert rule metric dependency
FastAPI health / readiness
FastAPI metrics
Production feedback 생성/평가/metric
Alert workflow
Smoke check
```

## 7. 포트폴리오에서 강조할 점

```text
1. Airflow + MLflow + FastAPI + Prometheus + Alertmanager + Grafana + Streamlit를 end-to-end로 연결
2. 모델 학습뿐 아니라 데이터 계약, 모델 검증, 운영 metric, alert, runbook까지 구현
3. Production Feedback Evaluation Loop로 배포 후 모델 품질을 운영 데이터 기준으로 평가
4. Prometheus rule test, metrics contract, alert dependency check로 운영 검증 자동화
5. Model archive / rollback / model card / lifecycle integrity check로 모델 운영 시나리오 구현
```

## 8. 최근 주요 업데이트

```text
2026-07-28
- Production Feedback Evaluation Loop 추가
- Production feedback metrics / alerts / runbook 추가
- smoke check에 feedback 생성/평가/metric 검증 추가
- Makefile 정리 및 production feedback 명령어 추가
- runbook coverage, rule test, alert dependency check 기준 14개 alert 검증
```
