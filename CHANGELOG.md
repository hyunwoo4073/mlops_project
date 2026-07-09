# Changelog

## v0.2.0 - Observability and Alerting Release

### Added

* FastAPI `/metrics` 엔드포인트 추가
* `src/monitoring/prometheus_metrics.py` 기반 Prometheus text format 운영 지표 생성
* PostgreSQL에 저장된 MLOps 운영 데이터를 `/metrics`로 노출
* Prometheus 기반 metrics scrape 구성
* Prometheus `jobskill-api` target 추가
* Prometheus alert rule 추가
* API metrics scrape 실패 감지 alert 추가
* API prediction low confidence ratio alert 추가
* batch prediction low confidence ratio alert 추가
* API prediction latency alert 추가
* pipeline check failure alert 추가
* latest promoted model accuracy / f1 기준 alert 추가
* Alertmanager 서비스 추가
* Alertmanager webhook receiver 구성
* FastAPI `/alertmanager/webhook` 엔드포인트 추가
* Alertmanager firing/resolved 이벤트 수신 기능 추가
* `alert_events` 테이블 추가
* alert firing/resolved 이벤트 이력 저장
* `alert_current_states` 테이블 추가
* alert fingerprint 기준 현재 alert 상태 upsert 저장
* `/metrics`에 alert event 누적 지표 추가
* `/metrics`에 current alert state 지표 추가
* Streamlit Dashboard에 Alert History 탭 추가
* Grafana datasource provisioning 추가
* Grafana dashboard provisioning 추가
* Grafana JobSkill MLOps Overview dashboard 추가
* Grafana Alert Events 패널 추가
* `docs/images/grafana.png` 스크린샷 추가
* `make metrics` 명령어 추가
* `make prometheus` / `make prometheus-logs` 명령어 추가
* `make prometheus-check` 명령어 추가
* `make alertmanager` / `make alertmanager-logs` 명령어 추가
* `make alertmanager-check` 명령어 추가
* `make grafana` / `make grafana-logs` 명령어 추가
* smoke check에 FastAPI metrics 검증 추가
* smoke check에 Prometheus health / target / alert rule 검증 추가
* smoke check에 Alertmanager health / webhook / alert table 검증 추가
* smoke check에 Grafana health 검증 추가
* GitHub Actions smoke workflow에 monitoring services 기동 검증 추가

### Monitoring Metrics

Exposed metrics include:

```text
jobskill_raw_job_posts_total
jobskill_cleaned_job_posts_total
jobskill_top_skills_total
jobskill_model_predictions_total
jobskill_model_prediction_avg_confidence
jobskill_model_prediction_low_confidence_ratio
jobskill_model_prediction_category_total
jobskill_api_prediction_requests_total
jobskill_api_prediction_avg_latency_ms
jobskill_pipeline_check_results_total
jobskill_pipeline_recent_failed_checks_total
jobskill_model_registry_records_total
jobskill_latest_promoted_model_accuracy
jobskill_latest_promoted_model_f1_weighted
jobskill_alert_events_total
jobskill_alert_current_states_total
```

### Alerting Flow

```text
FastAPI /metrics
→ Prometheus scrape
→ Prometheus alert rules
→ Alertmanager
→ FastAPI /alertmanager/webhook
→ PostgreSQL alert_events
→ PostgreSQL alert_current_states
→ Streamlit Alert History
→ Grafana Alert Events panels
```

### Monitoring Services

```text
FastAPI       : http://localhost:8000/metrics
Prometheus    : http://localhost:9090
Alertmanager  : http://localhost:9093
Grafana       : http://localhost:3000
```

---

## v0.1.1 - Pipeline Hardening Release

### Added

* `DATA_SOURCE_MODE` 기반 데이터 소스 실행 모드 추가

  * `sample_only`
  * `crawler_only`
  * `mixed`
* DAG 시작 단계에 `prepare_raw_sources` task 추가
* RemoteOK crawler retry / fallback 처리 추가
* `crawler_only` 학습 시 rare class 자동 제외 처리 추가
* `MIN_SAMPLES_PER_CLASS` 환경변수 추가
* `TEST_SIZE` 기반 stratified split 보정 추가
* FastAPI 요청/응답/실패/latency 로그 테이블 분리
* `api_prediction_logs` 테이블 추가
* `model_predictions.prediction_source` 컬럼 추가
* API prediction과 BATCH prediction 저장 경로 분리
* batch inference는 BATCH prediction만 삭제 후 재생성하도록 수정
* batch inference 이후 prediction quality gate 추가
* prediction quality 결과를 `pipeline_check_results`에 저장
* prediction distribution drift gate 추가
* rule label 분포와 batch prediction 분포 비교 기능 추가
* PSI 기반 prediction drift check 추가
* `PREDICTION_DRIFT` check type 추가
* pipeline notification 기능 추가
* Slack Webhook 기반 notification 옵션 추가
* `ALERT_ENABLED` / `ALERT_ONLY_ON_FAILURE` / `SLACK_WEBHOOK_URL` 환경변수 추가
* sample API request script 추가
* `scripts/send_sample_api_requests.py` 추가
* smoke check에서 FastAPI sample prediction request 검증 추가
* smoke check에서 `api_prediction_logs` 저장 여부 검증 추가
* smoke check에서 `model_predictions.prediction_source = API` 저장 여부 검증 추가
* retention cleanup script 추가
* `src/maintenance/cleanup_old_records.py` 추가
* API log / API prediction / pipeline check result 보관 기간 기반 cleanup 추가
* `CLEANUP_DRY_RUN` 기반 dry-run cleanup 모드 추가
* `make api-sample` 명령어 추가
* `make notify` 명령어 추가
* `make cleanup` 명령어 추가
* `make drift-check` 명령어 추가
* Streamlit Dashboard 추가
* Docker Compose dashboard 서비스 추가
* `docs/images/dashboard.png` 스크린샷 추가
* GitHub Actions Docker Compose smoke check workflow 추가
* GitHub Actions smoke workflow에서 sample 기반 최소 파이프라인 실행 후 promoted model 생성 검증 추가
* GitHub Actions smoke workflow에서 API / Dashboard smoke check 수행
* `.gitattributes` 기반 line ending 관리 추가
* `requirements-dev.txt` 추가
* `pyproject.toml` 추가
* Ruff 기반 코드 품질 검사 추가

### Updated

* `check_prediction_quality.py` SQL JOIN 순서 수정
* batch inference INSERT column mismatch 수정
* `api_prediction_logs` FK로 인한 batch inference TRUNCATE 실패 구조 개선
* latest promoted model 기준으로 notification message 조회 방식 개선
* `reports/latest_pipeline_report.md`와 `docs/sample_pipeline_report.md` 역할 분리
* README에 dashboard, notification, smoke check, API sample validation 반영

### Pipeline

Current DAG flow:

```text
prepare_raw_sources
→ generate_sample_jobs
→ load_raw_jobs
→ crawl_remoteok_jobs
→ preprocess_jobs
→ check_training_data
→ train_model
→ check_model_performance
→ promote_model
→ batch_inference
→ check_prediction_quality
→ check_prediction_drift
→ generate_pipeline_report
→ notify_pipeline_status
```

---

## v0.1.0 - MVP Release

### Added

* Airflow 기반 JobSkill MLOps 파이프라인 구성
* PostgreSQL 기반 원천/정제/스킬/예측/검증/모델 메타데이터 저장 구조 구성
* sample data generator 기반 샘플 채용공고 생성
* RemoteOK 기반 외부 채용공고 수집
* raw job post 적재 구조 구성
* preprocessing pipeline 구성
* 텍스트 정제 로직 추가
* 직무 라벨링 로직 추가
* 기술스택 추출 로직 추가
* 학습 데이터 품질 검증 단계 추가
* `pipeline_check_results` 테이블 기반 검증 결과 저장
* scikit-learn 기반 TF-IDF + Logistic Regression baseline 모델 학습
* MLflow tracking 연동
* MLflow artifact 저장 구조 구성
* 모델 성능 검증 단계 추가
* model performance gate 추가
* best model promotion 단계 추가
* `model_registry` 테이블 기반 promoted / rejected 모델 이력 저장
* batch inference 결과 저장
* FastAPI 기반 inference API 추가
* API inference 결과 저장
* prediction confidence / confidence level / low confidence 여부 저장
* top-k prediction 저장
* prediction lineage 저장
* Markdown 기반 pipeline report 생성
* Makefile 기반 실행 명령어 표준화
* smoke check script 추가
* GitHub Actions 기반 Python CI 추가

### Pipeline

Initial DAG flow:

```text
generate_sample_jobs
→ load_raw_jobs
→ crawl_remoteok_jobs
→ preprocess_jobs
→ check_training_data
→ train_model
→ check_model_performance
→ promote_model
→ batch_inference
→ check_prediction_quality
→ generate_pipeline_report
```

### Core Tables

```text
raw_job_posts
cleaned_job_posts
job_post_skills
model_predictions
pipeline_check_results
model_registry
```

### Services

```text
PostgreSQL
Airflow
MLflow
FastAPI
```
