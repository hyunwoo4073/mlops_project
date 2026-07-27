# JobSkill MLOps Project Summary

## 한 줄 요약

채용공고 데이터를 수집·전처리해 직무 분류 모델을 학습하고, Airflow, MLflow, FastAPI, Streamlit, Prometheus, Alertmanager, Grafana를 연결해 **학습부터 운영 검증, 모니터링, 알림, 문서화까지 구성한 end-to-end 경량 MLOps 프로젝트**입니다.

## 문서 읽는 순서

```text
1. docs/README_SUMMARY.md
   - 프로젝트가 무엇을 하는지 빠르게 파악

2. docs/QUICKSTART.md
   - 로컬에서 직접 실행하고 검증

3. README.md 또는 docs/README_FULL.md
   - 상세 구현, 트러블슈팅, 운영 기능 확인
```

## 핵심 목표

```text
데이터 수집
→ 데이터 품질 검증
→ 모델 학습
→ MLflow 실험 추적
→ 모델 성능 검증
→ 모델 승격
→ API / Batch 예측
→ 운영 metric 노출
→ Prometheus alert 평가
→ Alertmanager / Slack 알림
→ Runbook 기반 대응
→ Dashboard / Report 확인
→ Smoke / Ops 검증 자동화
```

## 주요 구성 요소

| 영역 | 구성 |
|---|---|
| Orchestration | Airflow 3.x |
| Database | PostgreSQL |
| ML Tracking | MLflow |
| Model | TF-IDF + Logistic Regression |
| Serving | FastAPI |
| Dashboard | Streamlit, Grafana |
| Monitoring | Prometheus |
| Alerting | Alertmanager, Slack Incoming Webhook |
| Validation | Data Contract, Metrics Contract, Alert Rule Dependency, Smoke Check |
| Documentation | README, Quick Start, Model Card, Runbook, Incident Report |

## 구현된 주요 기능

### 1. 데이터 파이프라인

```text
sample_only / crawler_only / mixed 데이터 소스 모드
Remote OK 채용공고 수집
수집 실패 retry / fallback
raw_job_posts 적재
cleaned_job_posts 전처리
job_post_skills 기술스택 추출
```

### 2. 데이터 품질 / 계약 검증

```text
training data quality check
data contract check
raw / cleaned / skill 테이블 schema 검증
필수 컬럼, null ratio, empty ratio, allowed value 검증
검증 결과 pipeline_check_results 저장
```

### 3. 모델 학습 / 평가 / 거버넌스

```text
TF-IDF + Logistic Regression 학습
MLflow run 기록
training dataset profile 저장
training dataset hash 저장
classification report 저장
confusion matrix 저장
evaluation distribution 저장
class-level precision / recall / f1-score / support 저장
model performance gate
class-level model performance gate
best model promotion
model registry 저장
promoted model archive
model rollback CLI
model lifecycle integrity check
Model Card 생성
```

### 4. API / 예측 운영

```text
FastAPI /predict
FastAPI /health
FastAPI /ready
FastAPI /metrics
FastAPI /model
FastAPI /reload-model
API prediction log 저장
prediction lineage 저장
confidence / low confidence / top-k prediction 저장
batch inference
prediction quality gate
prediction drift gate
```

### 5. 모니터링 / 알림

```text
FastAPI Prometheus metrics 노출
Prometheus scrape 구성
Prometheus alert rule 구성
Prometheus rule unit test
Alertmanager webhook routing
Alertmanager Slack notification
Alertmanager direct alert API 기반 수동 Slack 알림 검증
Alertmanager notification failure monitoring
Slack notification 전송 실패 감지
Runbook URL / Grafana URL / Prometheus URL alert annotation
```

### 6. Alert 운영 기능

```text
alert_events 저장
alert_current_states 저장
alert_acknowledgements 저장
alert_settings 기반 maintenance mode
alert_silence_actions 저장
Alertmanager silence / snooze
MTTA / MTTR metric
alert response escalation rule
incident response report
incident drill
alert workflow smoke check
```

### 7. 운영 검증 자동화

```text
runbook coverage check
metrics contract check
external metrics contract check
alert rule metric dependency check
multi-source metric dependency check
static ops validation
ops validation
repository artifact guard
Prometheus rule test
GitHub Actions smoke check
```

## 최근 개선 요약

### Alertmanager Notification Failure Monitoring

Alertmanager가 Slack으로 알림을 보내지 못하는 상황을 `alertmanager_notifications_failed_total` metric으로 감지합니다.

```text
Metric:
alertmanager_notifications_failed_total

Alert:
JobSkillAlertmanagerNotificationFailure

Runbook:
docs/runbooks/jobskill_alertmanager_notification_failure.md
```

### External Metrics Contract

FastAPI metric과 Alertmanager metric을 하나의 contract에서 관리하되 source를 분리합니다.

```yaml
required_metrics:
  - jobskill_api_ready
  - jobskill_alert_maintenance_mode

external_metrics:
  alertmanager:
    url: http://localhost:9093/metrics
    required_metrics:
      - alertmanager_notifications_failed_total
```

### Stable Zero Metrics

DB 초기화 직후 row가 없어도 required metric이 0으로 노출되도록 개선했습니다.

```text
jobskill_alert_acknowledgements_total 0
jobskill_alert_avg_mtta_minutes 0
jobskill_alert_unacknowledged_current_total 0
```

## 주요 검증 명령어

```bash
make runbook-check
make metrics-contract-check
make alert-rule-metric-check
make prometheus-rule-test
make ops-check
```

## 포트폴리오에서 강조할 점

```text
1. 단순 ML 모델 학습이 아니라 운영 가능한 MLOps 흐름을 구성함
2. 데이터 품질, 모델 성능, class-level 성능을 promotion 전에 검증함
3. MLflow dataset/evaluation artifact로 모델 재현성과 추적성을 강화함
4. Prometheus / Alertmanager / Slack / Runbook으로 운영 장애 대응 흐름을 구성함
5. metric contract와 alert rule dependency check로 모니터링 설정 자체를 검증함
6. DB 초기화, Docker Compose 기동, runtime artifact 관리까지 운영 관점으로 정리함
```

## 현재 프로젝트 상태

```text
MVP 수준:
완료

운영 검증:
Prometheus / Alertmanager / Runbook / Metrics Contract / Rule Test 기반으로 구성 완료

문서화:
상세 README, 요약본, Quick Start, Runbook, Model Card, Incident Report로 분리 중

다음 개선:
문서 구조 정리, external target scrape check, dashboard 기반 검증 결과 시각화
```
