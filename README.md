# jobskill-mlops project

[![Python CI](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/pytest.yml)
[![Smoke Check](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml/badge.svg)](https://github.com/hyunwoo4073/mlops_project/actions/workflows/smoke.yml)

채용공고 데이터를 기반으로 직무 분류 모델을 학습하고, Airflow와 MLflow를 이용해 데이터 수집, 원천 적재, 전처리, 데이터 품질 검증, 모델 학습, 성능 검증, 모델 승격, 일괄 예측, API 추론, 리포트 생성까지 연결하는 경량 MLOps 파이프라인 프로젝트입니다.

이 프로젝트는 단순 모델 학습이 아니라, 학습 전 데이터 품질 검증, data contract validation, MLflow training dataset tracking, model evaluation artifacts, class-level model performance gate, best model promotion, promoted model archive, model rollback CLI, promoted model card 생성, Model Lifecycle Dashboard, Model Evaluation Dashboard, Model Card Dashboard Viewer, model lifecycle integrity check, 예측 결과 lineage 저장, FastAPI serving model 자동 reload, source별 데이터 품질 리포트, 데이터 소스 모드 분리, 외부 수집 실패 fallback, API 요청/응답 로그, prediction quality gate, prediction drift gate, 운영 로그 retention cleanup, FastAPI `/metrics` 운영 지표 노출, Prometheus 기반 metrics 수집, Prometheus alert rule 평가, Alertmanager webhook alert 수신, alert event/current state 저장, Alertmanager 기반 Slack 알림 전송, Alertmanager direct alert API 기반 Slack 알림 검증, Docker Compose DB 역할 분리, PostgreSQL init DB 초기화/복구 절차, alert별 runbook 문서화, FastAPI 기반 runbook HTML 서빙, Slack/Streamlit 대시보드의 runbook 링크 연결, alert acknowledgement 저장, MTTA/MTTR 기반 alert response metrics, alert response escalation rule, dashboard 기반 alert maintenance mode 제어, Alertmanager silence/Snooze, incident response report 생성/조회/다운로드, alert workflow smoke check, Prometheus alert rule unit test, FastAPI health/readiness check, API readiness metrics, API not ready alert/runbook, runbook coverage check, metrics contract validation, alert rule metric dependency check, static ops validation check, ops validation check, Grafana 기반 모니터링 대시보드, Streamlit 기반 운영 대시보드와 Alert History, Pipeline Notification, 샘플 API 요청 검증, Makefile 기반 실행 명령어 표준화, smoke check 자동 검증, GitHub Actions 기반 테스트/코드 품질/서비스 기동/API 예측 로그/모니터링 경로 검증까지 포함한 end-to-end MLOps 흐름을 구성하는 것을 목표로 합니다.

## 주요 업데이트 내역

```text
2026-07-24
- Docker Compose의 Airflow metadata DB 접속 설정을 `DB_*` 공용 변수에서 `AIRFLOW_DB_*` 전용 변수로 분리
- `DB_*`는 프로젝트 애플리케이션 DB(`jobskill`) 전용, `AIRFLOW_DB_*`는 Airflow metadata DB(`airflow`) 전용으로 역할 정리
- Airflow `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`을 `airflow:airflow@postgres:5432/airflow` 기준으로 정리
- MLflow 서비스가 `MLFLOW_TRACKING_URI`와 `MLFLOW_ARTIFACT_ROOT`를 사용하도록 Docker Compose 설정 정리
- Docker Compose dashboard 서비스에 `scripts`, `reports`, `models`, `mlartifacts` mount를 정리해 Model Card 생성/조회 경로 안정화
- PostgreSQL init SQL을 `docker/postgres/init/01-init-databases.sql` 하나로 통합
- `airflow` role, `airflow` DB, `mlflow` DB 생성과 owner/privilege 설정을 init SQL에서 일괄 처리하도록 구성
- 기존 `01-create-airflow-db.sql`와 신규 init SQL이 동시에 `airflow` DB를 생성해 발생하던 `database "airflow" already exists` 초기화 오류 정리
- Docker volume 초기화(`docker compose down -v`) 후 Postgres / Airflow metadata DB / MLflow backend DB를 재생성하는 로컬 복구 절차 정리
- Airflow `db check` 기준으로 `postgres` DNS resolution 문제와 password authentication 문제를 분리해 원인 분석
- Postgres volume 내부 role password와 `.env` 값이 불일치할 수 있는 상황을 초기화 절차로 정리
- Airflow 기동 후 MLflow, FastAPI, Dashboard, Alertmanager, Prometheus, Grafana를 순차 기동하는 검증 흐름 정리
- `.secrets/slack_webhook_url` 기반 Alertmanager Slack receiver 설정 확인
- Alertmanager `/api/v2/alerts` direct alert POST 방식으로 Slack 알림 수신 테스트 완료
- Alertmanager → Slack 알림 경로가 정상 동작함을 확인하고 README 운영 검증 절차에 반영

2026-07-23
- MLflow training dataset tracking 추가
- 학습 데이터 row count, source distribution, label distribution, text length 통계를 MLflow param / metric / artifact로 저장
- 학습 데이터 hash를 생성해 MLflow run과 training dataset metadata를 연결
- MLflow Dataset API 기반 `mlflow.log_input()` 기록을 추가하고, 미지원 환경에서는 params/artifact fallback으로 동작하도록 구성
- 모델 학습 후 classification report, confusion matrix, actual/predicted distribution을 MLflow evaluation artifact로 저장
- class별 precision, recall, f1-score, support를 MLflow metric으로 기록
- `src/reporting/generate_model_card.py` 기반 promoted model card 생성 기능 추가
- `reports/latest_model_card.md`와 `reports/model_cards/model_card_registry_{model_registry_id}.md` 생성
- Model Card에 promoted model 정보, MLflow run metadata, training dataset profile, evaluation artifact, archive/rollback 정보를 포함
- `src/quality/check_model_class_performance.py` 기반 class-level model performance gate 추가
- MLflow의 `eval_f1_*`, `eval_recall_*`, `eval_support_*` metric을 조회해 promotion 이전 class별 성능 기준 검증
- class-level performance gate 결과를 `pipeline_check_results`에 `MODEL_CLASS_PERFORMANCE` 타입으로 저장
- Airflow DAG에 `check_model_class_performance` task 추가 및 `check_model_performance → check_model_class_performance → promote_model` 흐름으로 변경
- Airflow DAG에 `generate_model_card` task 추가 및 `promote_model → generate_model_card → batch_inference` 흐름으로 변경
- Streamlit Dashboard에 `Model Evaluation` 탭 추가
- Model Evaluation 탭에서 class별 support, recall, f1-score, threshold, pass/fail 상태 시각화
- Streamlit Dashboard에 `Model Card` 탭 추가
- Dashboard에서 Model Card 생성, 미리보기, Markdown 다운로드 기능 추가
- Docker Compose dashboard 서비스에 `./reports:/opt/airflow/project/reports` mount 추가
- Makefile에 `model-card`, `model-class-performance-check` 명령어 추가

2026-07-10
- Alertmanager Slack receiver 구성 추가
- Alertmanager에서 FastAPI webhook 저장과 Slack 알림 전송을 동시에 수행하도록 receiver 통합
- Slack Incoming Webhook URL을 Git에 포함하지 않도록 `.secrets/slack_webhook_url` 파일 mount 방식 적용
- Git에 올릴 수 있는 예시 파일 구조로 `.secrets.example/slack_webhook_url.example` 사용 방식 정리
- Alertmanager secret file permission 이슈 해결 내용 반영
- `channel` override 없이 Slack Incoming Webhook 기본 채널을 사용하는 설정 예시 추가
- Alertmanager direct alert API 기반 Slack 알림 테스트 절차 추가
- Alertmanager Slack 알림 화면 캡처 `docs/images/alert.png` 추가
- alert별 운영 대응 문서 `docs/runbooks/*.md` 추가
- Prometheus alert rule에 `runbook_url`, `dashboard_url`, `prometheus_url` annotation 추가
- FastAPI `GET /runbooks` / `GET /runbooks/{filename}` endpoint 추가
- Markdown runbook을 브라우저에서 읽기 쉽도록 FastAPI에서 HTML로 렌더링
- raw Markdown 확인용 `GET /runbooks/{filename}/raw` endpoint 추가
- Slack 알림 메시지에 Runbook / Grafana / Prometheus 클릭 링크 추가
- FastAPI webhook은 firing/resolved alert를 모두 저장하고, Slack은 firing 중심으로 전송하도록 알림 노이즈 조정
- API low confidence alert의 최소 예측 건수와 지속 시간을 조정해 테스트 데이터로 인한 alert flapping 완화
- Streamlit Dashboard에서 Current Alerts와 Alert History를 분리
- Streamlit Current Alerts / Alert History에 Runbook, Grafana, Prometheus 링크 컬럼 추가
- Grafana Dashboard에서 current alert state와 historical alert event 패널 구분
- API 이미지 빌드 경량화를 위해 `requirements-api.txt` 분리
- Streamlit Current Alerts에서 alert acknowledgement 저장 기능 추가
- `alert_acknowledgements` 테이블로 alert 확인자와 조치 메모 저장
- Alert History에 MTTA / MTTR 기반 Alert Response Metrics 추가
- FastAPI `/metrics`에 alert acknowledgement count, average MTTA/MTTR, unacknowledged current alert 지표 추가
- 미확인 firing alert, 높은 MTTA, 높은 MTTR을 감지하는 alert response escalation rule 추가
- escalation alert 대응용 runbook `jobskill_unacknowledged_current_alert.md`, `jobskill_alert_response_slo_breach.md` 추가
- `alert_settings` 테이블 기반 runtime alert maintenance mode 추가
- Streamlit Dashboard에서 maintenance mode를 ON/OFF할 수 있도록 제어 UI 추가
- Prometheus alert rule에 `jobskill_alert_maintenance_mode == 0` 조건을 적용해 점검/테스트 중 non-critical alert 억제
- Streamlit Current Alerts에서 특정 alert를 Alertmanager silence로 등록하는 기능 추가
- `alert_silence_actions` 테이블로 silence 생성 이력 저장
- Alertmanager Silence API 기반으로 alertname / service / severity 조합을 일정 시간 mute할 수 있도록 개선
- Incident Response Report 생성 스크립트 `src/reporting/generate_incident_response_report.py` 추가
- `reports/latest_incident_response_report.md` 생성 기능 추가
- Streamlit Dashboard에서 Incident Response Report 생성 / 미리보기 / 다운로드 기능 추가
- Makefile에 `incident-report` / `alert-workflow-check` 명령어 추가 및 help 문구 정리
- `scripts/check_alert_workflow.sh` 기반 alert workflow smoke check 추가
- GitHub Actions Smoke Check에서 alert workflow smoke check 실행 단계 추가
- alert workflow smoke check로 `/metrics`, runbook endpoint, Alertmanager health, Prometheus query, alert 관련 테이블, webhook 저장 경로 검증
- Streamlit Dashboard에서 Active Alertmanager silence 조회와 수동 expire 처리 기능 추가
- `alert_silence_actions.action_type`으로 silence CREATE / EXPIRE 이력 구분
- `scripts/run_incident_drill.py` 기반 synthetic incident response drill 추가
- incident drill로 firing alert, acknowledgement, silence, resolved event, incident response report 생성 흐름 자동 재현
- `monitoring/prometheus/tests/jobskill_alert_rules.test.yml` 기반 Prometheus alert rule unit test 추가
- Prometheus rule test 파일을 `rules/`가 아닌 `tests/` 디렉터리로 분리해 Prometheus 서버가 test yaml을 rule로 로드하지 않도록 정리
- Makefile에 `prometheus-rule-test` 명령어 추가
- FastAPI `/health` / `/ready` endpoint 추가로 liveness와 readiness 분리
- Docker Compose API healthcheck를 `/health` 기준으로 구성
- FastAPI `/metrics`에 API readiness 지표 `jobskill_api_ready`, `jobskill_api_database_ready`, `jobskill_api_promoted_model_ready`, `jobskill_api_promoted_model_file_exists` 추가
- `JobSkillApiNotReady` Prometheus alert rule 추가
- API readiness 장애 대응 runbook `docs/runbooks/jobskill_api_not_ready.md` 추가
- alert workflow smoke check에 API readiness metric 검증 추가
- `scripts/check_ops_validation.sh` 기반 통합 운영 검증 스크립트 추가
- Makefile에 `ops-check` 명령어 추가
- `scripts/check_runbook_coverage.py` 기반 runbook coverage check 추가
- Makefile에 `runbook-check` 명령어 추가
- Prometheus alert rule의 모든 `runbook_url` annotation과 실제 `docs/runbooks/*.md` 파일 존재 여부 검증
- `monitoring/metrics_contract.yml` 기반 필수 Prometheus metric contract 정의
- `scripts/check_metrics_contract.py` 기반 metrics contract check 추가
- Makefile에 `metrics-contract-check` 명령어 추가
- `jobskill_model_registry_records_total` 등 실제 `/metrics`에 노출되는 metric 이름 기준으로 contract 정리
- `jobskill_pipeline_recent_failed_checks_total`을 실패 check가 없어도 0으로 노출하도록 metric 안정성 개선
- `scripts/check_alert_rule_metric_dependencies.py` 기반 alert rule metric dependency check 추가
- Makefile에 `alert-rule-metric-check` 명령어 추가
- Prometheus alert rule이 참조하는 metric이 metrics contract와 실제 `/metrics`에 존재하는지 검증
- `scripts/check_static_ops_validation.sh` 기반 static ops validation check 추가
- Makefile에 `ops-static-check` 명령어 추가
- GitHub Actions Smoke Check에 서비스 기동 전 static ops validation 단계 추가
- CI runtime 환경에서 Alertmanager secret file placeholder를 생성하도록 `.secrets/slack_webhook_url` 준비 절차 추가
- `scripts/archive_promoted_model.py` 기반 promoted model archive 기능 추가
- `model_promotion_archives` 테이블로 archived model artifact 이력 저장
- Makefile에 `model-archive` 명령어 추가
- 현재 `models/best/job_classifier.pkl`을 `models/promoted_archive/`에 registry id와 timestamp 기준으로 스냅샷 저장
- `scripts/rollback_promoted_model.py` 기반 promoted model rollback CLI 추가
- `model_rollback_actions` 테이블로 rollback 실행 이력 저장
- Makefile에 `model-rollback-plan` / `model-rollback` 명령어 추가
- rollback 기본 동작을 dry-run으로 구성해 실행 전 복구 대상, 현재 promoted model, backup 경로를 먼저 확인하도록 개선
- 실제 rollback 시 현재 best model을 `models/rollback_backup/`에 백업하고 archived model을 `models/best/job_classifier.pkl`로 복원
- rollback 대상 model_registry row를 `PROMOTED`로, 기존 current promoted row를 `ROLLED_BACK`으로 갱신
- `MODEL_ROLLBACK_ARCHIVE_ID`, `MODEL_ROLLBACK_CREATED_BY`, `MODEL_ROLLBACK_REASON` 값을 Docker 컨테이너 내부로 전달하도록 Makefile target 개선- Streamlit Dashboard에 `Model Lifecycle` 탭 추가
- Model Lifecycle Dashboard에서 current promoted model, promoted model archive 이력, rollback action 이력 조회 기능 추가
- Rollback Plan Helper로 선택한 archive 기준 rollback 대상 model_registry_id와 현재 promoted model 비교
- Incident Report 탭이 Recent Predictions를 중복 호출하던 dashboard tab routing 오류 수정
- `scripts/check_model_lifecycle_integrity.py` 기반 model lifecycle integrity check 추가
- Makefile에 `model-lifecycle-check` 명령어 추가
- model lifecycle integrity check로 PROMOTED 모델 단일성, promoted_model_path, best model file, archive artifact, rollback backup artifact 정합성 검증
- `scripts/check_ops_validation.sh`에 model lifecycle integrity check 포함
- `config/data_contract.json` 기반 data contract 정의 추가
- `src/quality/check_data_contract.py` 기반 data contract check 추가
- Makefile에 `data-contract-check` 명령어 추가
- Airflow DAG에 `check_data_contract` task 추가 및 `preprocess_jobs → check_data_contract → check_training_data` 흐름으로 변경
- data contract check 결과를 `pipeline_check_results`에 `DATA_CONTRACT` 타입으로 저장
- raw_job_posts / cleaned_job_posts / job_post_skills의 필수 테이블, 필수 컬럼, 타입, null ratio, empty ratio, allowed value 검증
- `job_post_skills`는 optional 산출물로 `min_rows=0`을 적용하고 `job_post_id`, `skill_name` schema 기준으로 contract 정리
- Docker Compose Airflow 서비스에 `./config:/opt/airflow/project/config:ro` mount 추가


2026-07-09
- Prometheus alert rule 추가
- API metrics down, API/BATCH low confidence ratio, API latency, pipeline check failure, promoted model 성능 저하 alert 조건 정의
- `monitoring/prometheus/rules/jobskill_alert_rules.yml` 추가
- Prometheus 설정에 `rule_files`와 Alertmanager target 추가
- `prometheus-check` 명령어로 Prometheus config / alert rule 검증 추가
- Alertmanager Docker Compose 서비스 추가
- `monitoring/alertmanager/alertmanager.yml` 기반 webhook receiver 구성
- FastAPI `POST /alertmanager/webhook` endpoint 추가
- Alertmanager firing/resolved alert를 PostgreSQL `alert_events` 테이블에 저장
- alert fingerprint 기준 현재 상태를 관리하는 `alert_current_states` 테이블 추가
- `/metrics`에 `jobskill_alert_events_total` / `jobskill_alert_current_states_total` 지표 추가
- Streamlit Dashboard에 Alert History 탭 추가
- Grafana Dashboard에 Alert Events 패널 추가
- smoke check에 Prometheus alert rules / Alertmanager health / alert webhook / alert_events / alert_current_states 검증 추가

2026-07-08
- FastAPI `/metrics` 엔드포인트 추가
- `src/monitoring/prometheus_metrics.py` 기반 Prometheus text format 운영 지표 생성
- 모델 예측 수, 평균 confidence, low confidence 비율, API 요청 수/latency, pipeline check 결과, latest promoted model 성능 지표 노출
- `monitoring/prometheus/prometheus.yml` 추가
- Docker Compose Prometheus 서비스 추가
- Makefile에 `metrics` / `prometheus` / `prometheus-logs` 명령어 추가
- Prometheus target `jobskill-api` scrape 구성
- Grafana datasource / dashboard provisioning 구성 추가
- `monitoring/grafana/provisioning` 및 `monitoring/grafana/dashboards/jobskill-mlops-overview.json` 추가
- Docker Compose Grafana 서비스 추가
- Makefile에 `grafana` / `grafana-logs` 명령어 추가
- Grafana dashboard 화면 캡처 `docs/images/grafana.png` 추가
- smoke check에 FastAPI metrics / Prometheus / Grafana health 검증 추가
- README에 Prometheus / Grafana 실행 방법, 접속 정보, 주요 query, 스크린샷 반영

2026-07-03
- Makefile 기반 실행 명령어 표준화 추가
- scripts/smoke_check.sh 기반 로컬 smoke check 추가
- smoke check에 FastAPI sample prediction request 검증 추가
- smoke check에서 api_prediction_logs 저장 여부 검증 추가
- smoke check에서 model_predictions.prediction_source=API 저장 여부 검증 추가
- scripts/send_sample_api_requests.py 추가
- FastAPI /predict 샘플 요청 자동 실행 기능 추가
- API prediction log와 API prediction row 검증 흐름 추가
- src/notification/notify_pipeline_status.py 추가
- Pipeline Notification 메시지 생성 기능 추가
- Slack Webhook 기반 알림 전송 옵션 추가
- ALERT_ENABLED / ALERT_ONLY_ON_FAILURE / SLACK_WEBHOOK_URL 환경변수 추가
- Makefile에 smoke / notify / api-sample 명령어 추가
- src/maintenance/cleanup_old_records.py 기반 retention cleanup 스크립트 추가
- CLEANUP_DRY_RUN 기반 안전한 dry-run cleanup 모드 추가
- API 로그 / API prediction / pipeline check 결과 보관 기간 환경변수 추가
- src/quality/check_prediction_drift.py 기반 prediction distribution drift check 추가
- PREDICTION_DRIFT 검증 결과를 pipeline_check_results에 저장
- MAX_PREDICTION_DISTRIBUTION_PSI / MIN_DRIFT_CHECK_ROWS 환경변수 추가
- Airflow DAG에 check_prediction_drift task 추가
- Makefile에 cleanup / drift-check 명령어 추가
- GitHub Actions 기반 Docker Compose smoke check workflow 추가
- Smoke workflow에서 API 기동 전 sample 기반 최소 파이프라인 실행 및 promoted model 생성 검증 추가
- GitHub Actions smoke workflow에서 API / Dashboard smoke check 수행
- README 상단 GitHub Actions badge 추가
- CHANGELOG.md 기반 MVP release 기록 추가
- .gitattributes 기반 line ending 관리 추가
- GitHub Actions 기반 pytest 자동 실행 workflow 추가
- Ruff 기반 코드 품질 검사 CI 추가
- requirements-dev.txt / pyproject.toml 추가
- reports/latest_pipeline_report.md와 docs/sample_pipeline_report.md 역할 분리
- 포트폴리오용 sample pipeline report 문서화
- Streamlit 기반 MLOps Dashboard 추가
- Docker Compose dashboard 서비스 추가
- Dashboard 화면 캡처 docs/images/dashboard.png 추가
- README에 Dashboard 실행 방법 / 접속 정보 / 스크린샷 반영
- 다음 개선 예정에서 완료 항목 정리

2026-07-02
- DATA_SOURCE_MODE 기반 데이터 소스 실행 모드 추가
- sample_only / crawler_only / mixed 모드 분리
- DAG 시작 단계에 prepare_raw_sources task 추가
- Remote OK crawler retry / fallback 처리 추가
- crawler_only 학습 시 rare class 자동 제외 처리 추가
- FastAPI 요청/응답/실패/latency 로그 테이블 분리
- model_predictions에 prediction_source 추가
- API prediction과 BATCH prediction 저장 경로 분리
- batch inference는 BATCH 예측만 삭제 후 재생성하도록 수정
- batch inference 이후 prediction quality gate 추가
- prediction quality 결과를 pipeline_check_results에 저장
- API quality / prediction quality 리포트 항목 추가
- FK 제약조건 및 SQL 문법 오류 트러블슈팅 정리
```


## 프로젝트 목표

이 프로젝트는 채용공고 데이터를 사용해 아래 흐름을 구성합니다.

```text
데이터 소스 모드 결정(sample_only / crawler_only / mixed)
→ 샘플 채용공고 데이터 생성 또는 skip
→ 외부 채용공고 수집 또는 skip
→ 외부 수집 실패 시 retry / fallback 처리
→ PostgreSQL raw 테이블 적재
→ 텍스트 정제 / 직무 라벨링 / 기술스택 추출
→ PostgreSQL cleaned / skills 테이블 저장
→ Data Contract Check로 테이블/컬럼/type/null/empty/allowed value 검증
→ 학습 데이터 품질 체크
→ 검증 결과 저장
→ rare class 필터링 후 모델 학습
→ TF-IDF + Logistic Regression 모델 학습
→ MLflow 실험 기록
→ training dataset metadata / dataset hash 저장
→ classification report / confusion matrix / evaluation distribution 저장
→ class별 precision / recall / f1-score / support 저장
→ 모델 artifact 저장
→ 모델 성능 기준 체크
→ class-level model performance gate로 직무별 성능 기준 검증
→ 성능 검증 결과 저장
→ best model promotion
→ model_registry 저장
→ promoted model card 생성
→ promoted model archive로 현재 best model artifact 스냅샷 보존
→ rollback plan으로 archived model 복구 대상과 현재 promoted model 비교
→ rollback 실행 시 이전 archived model을 best model로 복원
→ rollback action 이력 저장
→ model lifecycle integrity check로 model_registry / archive / rollback artifact 정합성 검증
→ promoted model 기반 batch inference
→ BATCH prediction 저장
→ batch prediction quality gate
→ prediction distribution drift gate
→ FastAPI 단건 예측
→ FastAPI `/health` / `/ready`로 liveness와 readiness 분리
→ API readiness metric으로 DB / promoted model / model file 준비 상태 노출
→ API prediction 저장
→ FastAPI 요청/응답 로그 저장
→ 샘플 API 요청으로 API prediction / API log 저장 검증
→ prediction lineage 저장
→ source별 / prediction quality / API quality 리포트 생성
→ Pipeline Notification으로 모델/검증/예측/API 상태 요약
→ retention cleanup으로 오래된 API 로그/예측/검증 결과 정리
→ FastAPI `/metrics`로 운영 지표 노출
→ Prometheus로 운영 지표 수집
→ Prometheus alert rule로 주요 운영 이상 조건 평가
→ Prometheus alert rule unit test로 firing 조건과 maintenance mode 억제 조건 검증
→ API not ready alert로 serving 준비 상태 장애 감지
→ Docker Compose DB 역할 분리와 PostgreSQL init SQL로 jobskill / airflow / mlflow DB 초기화
→ Alertmanager로 firing/resolved alert 전달
→ FastAPI `/alertmanager/webhook`으로 alert 이벤트 수신
→ alert_events / alert_current_states에 alert 이력과 현재 상태 저장
→ Alertmanager Slack receiver로 운영 알림 전송
→ Alertmanager direct alert API로 Slack 알림 경로 수동 검증
→ Prometheus alert annotation으로 Runbook / Grafana / Prometheus 링크 제공
→ FastAPI `/runbooks`로 alert별 runbook HTML 서빙
→ Slack과 Streamlit Dashboard에서 runbook 링크 기반 운영 대응
→ Streamlit Dashboard에서 alert acknowledgement와 조치 메모 저장
→ Alert History에서 MTTA / MTTR 기반 alert response metrics 확인
→ Prometheus alert rule로 미확인 alert와 대응 지연 상황 감지
→ Streamlit Dashboard에서 alert maintenance mode ON/OFF 제어
→ maintenance mode 기반 non-critical alert 억제
→ Streamlit Dashboard에서 특정 alert를 Alertmanager silence로 등록
→ alert_silence_actions에 silence 생성 이력 저장
→ alert event / acknowledgement / silence / MTTA / MTTR 기반 incident response report 생성
→ Streamlit Dashboard에서 incident response report 생성 / 미리보기 / 다운로드
→ incident drill로 alert 발생부터 resolved/report까지 데모 시나리오 자동 생성
→ alert workflow smoke check로 alert 운영 기능 자동 검증
→ data contract check로 raw/cleaned/skill 데이터 계약 검증
→ model lifecycle integrity check로 모델 운영 상태 검증
→ runbook coverage check로 alert별 대응 문서 누락 검증
→ metrics contract check로 필수 Prometheus metric 노출 여부 검증
→ alert rule metric dependency check로 alert rule이 참조하는 metric 누락 검증
→ static ops validation으로 서비스 기동 전 운영 설정/문서/metric dependency 정적 검증
→ ops-check로 Prometheus, Alertmanager, FastAPI readiness, runbook, smoke check 통합 검증
→ Grafana Dashboard로 Prometheus 지표와 alert event/current state 패널 시각화
→ Streamlit Dashboard로 모델/데이터/API 품질 지표, Model Evaluation, Model Card, Alert History 시각화
→ FastAPI serving model 자동 reload
→ Airflow DAG로 전체 파이프라인 실행
```

## Architecture

```mermaid
flowchart LR
    MODE[DATA_SOURCE_MODE] --> PREP[prepare_raw_sources]

    PREP --> A[Sample Job CSV]
    PREP --> CR[Remote OK Crawler]

    A --> B[raw_job_posts]
    EXT[Remote OK Job Feed] --> CR
    CR --> RF[Retry / Fallback]
    RF --> B

    B --> C[Preprocessing]
    C --> D[cleaned_job_posts]
    C --> E[job_post_skills]

    D --> DC[Data Contract Check]
    E --> DC
    DC --> Q1[Data Quality Check]
    DC --> QR[pipeline_check_results]
    Q1 --> QR

    Q1 --> F[Train Model]
    F --> G[MLflow Tracking]
    F --> H[models/job_classifier.pkl]

    G --> Q2[Model Performance Check]
    Q2 --> QR

    Q2 --> P[Promote Model]
    P --> MR[model_registry]
    P --> BM[models/best/job_classifier.pkl]
    P --> MPA[model_promotion_archives]
    BM --> MARCHIVE[models/promoted_archive]
    MARCHIVE --> ROLLBACK[Model Rollback CLI]
    ROLLBACK --> MR
    ROLLBACK --> BM
    ROLLBACK --> MROLLBACK[model_rollback_actions]
    MPA --> MLDASH[Model Lifecycle Dashboard]
    MROLLBACK --> MLDASH
    MR --> MLDASH
    MPA --> MLCHECK[Model Lifecycle Integrity Check]
    MROLLBACK --> MLCHECK
    BM --> MLCHECK

    MR --> I[Batch Inference]
    BM --> I
    I --> J[model_predictions]
    I --> Q3[Prediction Quality Check]
    Q3 --> Q4[Prediction Drift Check]
    Q4 --> QR

    MR --> K[FastAPI /predict]
    BM --> K
    K --> HREADY[FastAPI /health / /ready]
    K --> J
    K --> AL[api_prediction_logs]
    K --> AE[alert_events]
    K --> ACS[alert_current_states]
    K --> MET[FastAPI /metrics]
    AM -->|webhook| K
    DASH --> AACK[alert_acknowledgements]
    DASH --> ASET[alert_settings]
    DASH --> ASIL[alert_silence_actions]
    DASH --> IR[Incident Response Report]
    DASH -->|silence API| AM

    QR --> R[Pipeline Report]
    MR --> R
    J --> R
    AL --> R
    D --> R

    B --> DASH[Streamlit Dashboard]
    D --> DASH
    J --> DASH
    AL --> DASH
    AE --> DASH
    ACS --> DASH
    QR --> DASH
    MR --> DASH

    QR --> N[Pipeline Notification]
    MR --> N
    J --> N
    AL --> N
    N --> SLACK[Slack Webhook Optional]

    J --> MNT[Retention Cleanup]
    AL --> MNT
    QR --> MNT

    MET --> PROM[Prometheus]
    MET --> READYMET[API Readiness Metrics]
    READYMET --> PROM
    PROM --> RULES[Prometheus Alert Rules]
    RULES --> RTEST[Prometheus Rule Tests]
    RULES --> AM[Alertmanager]
    AM --> ASLACK[Slack Alert Notification]
    AM --> RUNBOOK[FastAPI Runbook HTML]
    ASLACK --> RUNBOOK
    DASH --> RUNBOOK
    AM --> AE
    AM --> ACS
    PROM --> GRAFANA[Grafana Dashboard]
    AE --> MET
    ACS --> MET
    AACK --> MET
    ASET --> MET
    ASIL --> IR
    AE --> IR
    ACS --> IR
    AACK --> IR

    subgraph Orchestration
        L[Airflow DAG / PythonOperator]
    end

    subgraph CI
        CI1[GitHub Actions]
        CI2[pytest]
        CI3[Ruff]
        CI4[Docker Compose Smoke Check]
        CI5[Sample API Request Validation]
        CI6[Metrics / Prometheus / Alertmanager / Grafana Health Check]
        CI7[Alert Workflow Smoke Check]
        CI8[Prometheus Rule Unit Test]
        CI9[Ops Validation Check]
        CI10[Runbook Coverage Check]
        CI11[Metrics Contract Check]
        CI12[Alert Rule Metric Dependency Check]
        CI13[Static Ops Validation Check]
        CI14[Data Contract Check]
        CI15[Model Lifecycle Integrity Check]
        CI1 --> CI2
        CI1 --> CI3
        CI1 --> CI4
        CI4 --> CI5
        CI4 --> CI6
        CI4 --> CI7
        CI4 --> CI8
        CI4 --> CI9
        CI4 --> CI10
        CI4 --> CI11
        CI4 --> CI12
        CI4 --> CI13
        CI4 --> CI14
        CI4 --> CI15
    end

    L --> PREP
    L --> A
    L --> CR
    L --> C
    L --> DC
    L --> Q1
    L --> F
    L --> Q2
    L --> P
    L --> I
    L --> Q3
    L --> Q4
    L --> R
    L --> N
```

## 현재 구성

```text
Docker Compose
├── PostgreSQL
│   ├── jobskill DB  : 프로젝트 데이터 / 예측 / 검증 / 모델 registry 저장
│   ├── airflow DB   : Airflow 메타데이터 저장
│   ├── mlflow DB    : MLflow 실험/런 메타데이터 저장
│   └── init SQL     : jobskill / airflow / mlflow DB와 role/owner/privilege 초기화
├── Airflow 3.x
│   ├── airflow-apiserver
│   ├── airflow-scheduler
│   ├── airflow-dag-processor
│   └── airflow-triggerer
├── MLflow
│   ├── backend store  : PostgreSQL mlflow DB
│   └── artifact store : ./mlartifacts
├── FastAPI
│   ├── /health
│   ├── /ready
│   ├── /predict
│   ├── /model
│   ├── /reload-model
│   ├── /metrics
│   ├── /alertmanager/webhook
│   └── /runbooks
├── Streamlit Dashboard
│   ├── Model Lifecycle 탭 제공
│   ├── Model Evaluation 탭 제공
│   ├── Model Card 탭 제공
│   ├── current promoted model 조회
│   ├── promoted model archive 이력 조회
│   ├── rollback action 이력 조회
│   ├── archive 기준 rollback plan helper 제공
│   ├── class-level model performance gate 결과 조회
│   ├── 직무별 support / recall / f1-score / threshold / pass-fail 상태 시각화
│   ├── promoted model card 생성 / 미리보기 / 다운로드
│   ├── source별 데이터 품질 조회
│   ├── batch prediction quality 조회
│   ├── pipeline check 결과 조회
│   ├── FastAPI prediction logs 조회
│   ├── Current Alerts 조회
│   ├── Alert Maintenance Mode ON/OFF 제어
│   ├── Alertmanager Silence 생성 및 이력 조회
│   ├── Current Alerts Runbook / Grafana / Prometheus 링크 제공
│   ├── alert acknowledgement / 조치 메모 저장
│   ├── Alert History 조회
│   ├── Alert Response Metrics(MTTA / MTTR) 조회
│   ├── Incident Response Report 생성 / 미리보기 / 다운로드
│   └── recent predictions 조회
├── Pipeline Notification
│   ├── latest promoted model 요약
│   ├── pipeline check summary 요약
│   ├── failed check 요약
│   ├── prediction quality 요약
│   ├── prediction drift 요약
│   ├── API status / latency 요약
│   └── Slack Webhook 전송 옵션
├── Model Lifecycle Operations
│   ├── current promoted model archive 생성
│   ├── model_promotion_archives 기반 archive 이력 저장
│   ├── rollback dry-run plan 확인
│   ├── archived model artifact를 best model path로 복원
│   ├── rollback 전 current best model backup 생성
│   ├── model_registry PROMOTED / ROLLED_BACK 상태 갱신
│   ├── model_rollback_actions 기반 rollback 이력 저장
│   ├── model lifecycle integrity check로 DB/file artifact 정합성 검증
│   ├── MLflow dataset / evaluation artifact 기반 Model Card 생성
│   └── reports/latest_model_card.md 기반 promoted model 운영 문서화
├── Data Contract
│   ├── config/data_contract.json 기반 데이터 계약 정의
│   ├── raw_job_posts / cleaned_job_posts / job_post_skills schema 검증
│   ├── 필수 컬럼 / 타입 / 최소 row count 검증
│   ├── null ratio / empty ratio / allowed value 검증
│   ├── DATA_CONTRACT 결과를 pipeline_check_results에 저장
│   └── Airflow DAG에서 preprocess 이후, training data check 이전에 실행
├── Maintenance
│   ├── api_prediction_logs retention cleanup
│   ├── API prediction row retention cleanup
│   ├── pipeline_check_results retention cleanup
│   └── dry-run 기반 삭제 대상 사전 확인
├── Runtime / DB Initialization
│   ├── DB_* 환경변수는 jobskill application DB 전용으로 사용
│   ├── AIRFLOW_DB_* 환경변수는 Airflow metadata DB 전용으로 사용
│   ├── MLFLOW_TRACKING_URI는 MLflow backend DB 전용으로 사용
│   ├── docker/postgres/init/01-init-databases.sql 기반 DB 초기화
│   └── Docker volume 초기화 후 로컬 실행 산출물 재생성 절차 문서화
├── Monitoring / Alerting
│   ├── FastAPI /health liveness endpoint 제공
│   ├── FastAPI /ready readiness endpoint 제공
│   ├── FastAPI /metrics 운영 지표 노출
│   ├── API readiness metrics 노출
│   ├── Prometheus jobskill-api scrape
│   ├── Prometheus alert rule 평가
│   ├── Alertmanager webhook routing
│   ├── Alertmanager Slack notification routing
│   ├── FastAPI /alertmanager/webhook alert 수신
│   ├── FastAPI /runbooks alert runbook HTML 서빙
│   ├── alert_events / alert_current_states 저장
│   ├── alert_acknowledgements / alert_settings / alert_silence_actions 저장
│   ├── alert acknowledgement / MTTA / MTTR metrics 노출
│   ├── alert response escalation rule 평가
│   ├── API not ready alert rule 평가
│   ├── Prometheus alert rule unit test
│   ├── alert maintenance mode 기반 non-critical alert 억제
│   ├── alert별 runbook 문서 관리
│   ├── Grafana datasource provisioning
│   └── Grafana JobSkill MLOps Overview dashboard
└── Local / CI Validation
    ├── Makefile 명령어 표준화
    ├── scripts/smoke_check.sh
    ├── scripts/check_alert_workflow.sh
    ├── scripts/check_runbook_coverage.py
    ├── scripts/check_metrics_contract.py
    ├── scripts/check_alert_rule_metric_dependencies.py
    ├── scripts/check_static_ops_validation.sh
    ├── scripts/check_ops_validation.sh
    ├── scripts/check_model_lifecycle_integrity.py
    ├── scripts/archive_promoted_model.py
    ├── scripts/rollback_promoted_model.py
    ├── scripts/run_incident_drill.py
    ├── scripts/send_sample_api_requests.py
    ├── src/quality/check_data_contract.py
    ├── config/data_contract.json
    ├── monitoring/metrics_contract.yml
    ├── GitHub Actions Python CI
    ├── GitHub Actions Smoke Check
    ├── Alert Workflow Smoke Check
    ├── Data Contract Check
    ├── Model Lifecycle Integrity Check
    ├── Runbook Coverage Check
    ├── Metrics Contract Check
    ├── Alert Rule Metric Dependency Check
    ├── Static Ops Validation Check
    ├── Prometheus Rule Unit Test
    └── Ops Validation Check
```

## 기술 스택

```text
Language        : Python
Workflow        : Apache Airflow 3.x
Database        : PostgreSQL
ML Lifecycle    : MLflow, MLflow Dataset Tracking
Preprocessing   : pandas
Model           : scikit-learn
API             : FastAPI
Dashboard       : Streamlit, Plotly, Grafana
Documentation   : Markdown Model Card, Incident Report, Runbook
Runbook         : Markdown, FastAPI HTML Rendering
Data Contract   : JSON, PostgreSQL information_schema
Monitoring      : Prometheus, Prometheus Text Format
Alerting        : Prometheus Alert Rules, Alertmanager, FastAPI Webhook, Slack Incoming Webhook
Notification    : Slack Incoming Webhook, requests
Maintenance     : Retention Cleanup Script
Crawler         : requests, BeautifulSoup
Test            : pytest
Code Quality    : Ruff
CI              : GitHub Actions
Command Runner  : Makefile, Shell Script
Container       : Docker Compose
```

## 디렉터리 구조

```text
.
├── README.md
├── CHANGELOG.md
├── Makefile
├── docker-compose.yml
├── requirements.txt
├── requirements-api.txt
├── requirements-dev.txt
├── pyproject.toml
├── pytest.ini
├── .env.example
├── .gitattributes
├── .gitignore
├── .secrets.example/
│   └── slack_webhook_url.example
├── config/
│   └── data_contract.json
├── .github/
│   └── workflows/
│       ├── pytest.yml
│       └── smoke.yml
├── dags/
│   └── jobskill_pipeline_dag.py
├── docker/
│   ├── airflow/
│   │   └── Dockerfile
│   ├── api/
│   │   └── Dockerfile
│   └── postgres/
│       └── init/
│           └── 01-init-databases.sql
├── sql/
│   ├── create_tables.sql
│   └── report_queries.sql
├── scripts/
│   ├── generate_sample_jobs.py
│   ├── send_sample_api_requests.py
│   ├── check_alert_workflow.sh
│   ├── check_runbook_coverage.py
│   ├── check_metrics_contract.py
│   ├── check_alert_rule_metric_dependencies.py
│   ├── check_static_ops_validation.sh
│   ├── check_ops_validation.sh
│   ├── check_model_lifecycle_integrity.py
│   ├── archive_promoted_model.py
│   ├── rollback_promoted_model.py
│   ├── run_incident_drill.py
│   └── smoke_check.sh
├── monitoring/
│   ├── metrics_contract.yml
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   ├── rules/
│   │   │   └── jobskill_alert_rules.yml
│   │   └── tests/
│   │       └── jobskill_alert_rules.test.yml
│   ├── alertmanager/
│   │   └── alertmanager.yml
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/
│       │   │   └── prometheus.yml
│       │   └── dashboards/
│       │       └── dashboard.yml
│       └── dashboards/
│           └── jobskill-mlops-overview.json
├── src/
│   ├── common/
│   │   ├── db.py
│   │   ├── data_source_mode.py
│   │   ├── model_registry.py
│   │   └── prediction_quality.py
│   ├── crawling/
│   │   └── crawl_remoteok_jobs.py
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── app.py
│   ├── ingestion/
│   │   ├── prepare_raw_sources.py
│   │   └── load_raw_jobs.py
│   ├── notification/
│   │   ├── __init__.py
│   │   └── notify_pipeline_status.py
│   ├── maintenance/
│   │   ├── __init__.py
│   │   └── cleanup_old_records.py
│   ├── monitoring/
│   │   ├── __init__.py
│   │   └── prometheus_metrics.py
│   ├── preprocessing/
│   │   ├── clean_text.py
│   │   ├── extract_skills.py
│   │   ├── label_jobs.py
│   │   └── preprocess_db.py
│   ├── quality/
│   │   ├── check_logger.py
│   │   ├── check_training_data.py
│   │   ├── check_data_contract.py
│   │   ├── check_model_performance.py
│   │   ├── check_model_class_performance.py
│   │   ├── check_prediction_quality.py
│   │   └── check_prediction_drift.py
│   ├── reporting/
│   │   ├── generate_pipeline_report.py
│   │   ├── generate_model_card.py
│   │   └── generate_incident_response_report.py
│   ├── training/
│   │   ├── train_baseline.py
│   │   └── promote_model.py
│   └── inference/
│       ├── api.py
│       └── batch_inference.py
├── tests/
│   └── unit/
├── data/
│   ├── raw/
│   └── processed/
├── models/
│   ├── best/
│   ├── promoted_archive/
│   └── rollback_backup/
├── reports/
│   ├── latest_pipeline_report.md
│   ├── latest_incident_response_report.md
│   ├── latest_model_card.md
│   └── model_cards/
├── mlartifacts/
├── airflow_logs/
├── docs/
│   ├── sample_pipeline_report.md
│   ├── runbooks/
│   │   ├── jobskill_alertmanager_slack_notification.md
│   │   ├── jobskill_api_high_latency.md
│   │   ├── jobskill_api_metrics_down.md
│   │   ├── jobskill_high_low_confidence_ratio.md
│   │   ├── jobskill_pipeline_check_failure.md
│   │   ├── jobskill_promoted_model_low_performance.md
│   │   ├── jobskill_unacknowledged_current_alert.md
│   │   ├── jobskill_api_not_ready.md
│   │   └── jobskill_alert_response_slo_breach.md
│   └── images/
│       ├── Airflow DAG success.png
│       ├── dashboard.png
│       ├── fastapi.png
│       ├── grafana.png
│       ├── alert.png
│       ├── mlflow.png
│       └── postgresql.png
└── notebooks/
```

> `data/`, `models/`, `mlartifacts/`, `airflow_logs/`, `.env`, `simple_auth_manager_passwords.json` 등은 로컬 실행 중 생성되는 산출물이므로 Git에는 포함하지 않습니다.  
> 포트폴리오 확인용 스크린샷은 `docs/images/`에 저장하고 README에서 상대경로로 참조합니다.

## 주요 컴포넌트

### 1. 데이터 생성

`scripts/generate_sample_jobs.py`

직무별 템플릿을 기반으로 샘플 채용공고 데이터를 생성합니다.

생성 대상 직무:

```text
Data Engineer
Backend Engineer
ML Engineer
DevOps Engineer
Data Analyst
```

생성 파일:

```text
data/raw/sample_jobs.csv
```

### 1-1. 데이터 소스 모드

`src/common/data_source_mode.py`  
`src/ingestion/prepare_raw_sources.py`

파이프라인 실행 시 사용할 데이터 소스를 환경변수로 제어합니다.

```env
DATA_SOURCE_MODE=mixed
```

지원 모드:

```text
sample_only  : 샘플 CSV 데이터만 사용
crawler_only : Remote OK 수집 데이터만 사용
mixed        : 샘플 데이터와 Remote OK 수집 데이터를 함께 사용
```

DAG 시작 단계에서 `prepare_raw_sources` task가 실행되어 선택한 모드에 맞게 raw/source 데이터를 정리합니다.

```text
sample_only
→ sample 외 source raw 제거
→ sample 생성/적재 task 실행
→ crawler task skip

crawler_only
→ sample raw 제거
→ sample 생성/적재 task skip
→ crawler task 실행

mixed
→ sample과 crawler 데이터를 함께 유지
→ sample 생성/적재 task 실행
→ crawler task 실행
```

### 2. 외부 채용공고 수집

`src/crawling/crawl_remoteok_jobs.py`

Remote OK의 public job feed를 사용해 실제 원격 채용공고 데이터를 수집하고 `raw_job_posts`에 upsert합니다.

저장 정보:

```text
source
source_job_id
external_id
source_url
title
company
location
description
tags
crawled_at
```

수집 단계에서는 비개발/비데이터 직무가 학습 데이터에 과도하게 유입되지 않도록 필터링을 수행합니다.

```text
수집 대상:
Data Engineer
Backend Engineer
ML Engineer
DevOps Engineer
Data Analyst

필터링 기준:
title, description, tags 기반 직무 라벨 추론
Unknown으로 분류되는 공고는 raw 적재 전 제외
```


### 2-1. 외부 수집 retry / fallback

Remote OK API 호출 실패에 대비해 crawler에 retry와 fallback 처리를 추가했습니다.

환경변수:

```env
REMOTEOK_MAX_RETRIES=3
REMOTEOK_RETRY_SLEEP_SECONDS=3
REMOTEOK_REQUEST_TIMEOUT_SECONDS=30
REMOTEOK_FALLBACK_TO_EXISTING_RAW=true
REMOTEOK_MIN_FETCHED_JOBS=1
```

동작 방식:

```text
1. Remote OK API 호출
2. 실패 시 지정 횟수만큼 retry
3. retry 이후에도 실패하면 기존 raw_job_posts의 remoteok 데이터 확인
4. 기존 데이터가 있으면 fallback으로 기존 데이터를 사용해 파이프라인 계속 진행
5. 기존 데이터도 없으면 crawler task 실패
```

이를 통해 외부 API 일시 장애가 전체 DAG 실패로 바로 이어지지 않도록 개선했습니다.

### 3. Raw 데이터 적재

`src/ingestion/load_raw_jobs.py`

생성된 CSV 데이터를 PostgreSQL의 `raw_job_posts` 테이블에 적재합니다.

샘플 데이터와 외부 수집 데이터는 `source`로 구분합니다.

```text
source = sample
source = remoteok
```

### 4. 전처리

`src/preprocessing/preprocess_db.py`

`raw_job_posts` 데이터를 읽어 아래 처리를 수행합니다.

```text
텍스트 정제
직무 라벨링
기술스택 추출
전처리 결과 저장
```

Remote OK 데이터는 중요한 힌트가 `tags`에 포함되는 경우가 많기 때문에, 전처리와 라벨링에는 `title`, `description`, `tags`를 함께 사용합니다.

```text
text_for_model = cleaned_title + cleaned_description + cleaned_tags
job_category  = label_job(title, description + tags)
```

저장 테이블:

```text
cleaned_job_posts
job_post_skills
```

전처리 재실행 시 기존 전처리/예측 결과를 초기화합니다.

```sql
TRUNCATE TABLE
    model_predictions,
    job_post_skills,
    cleaned_job_posts
RESTART IDENTITY
CASCADE;
```

`model_predictions`와 `job_post_skills`가 `cleaned_job_posts`를 참조하므로, 단순히 `cleaned_job_posts`만 먼저 삭제하면 FK 제약조건 오류가 발생할 수 있습니다.

### 5. 직무 라벨링 규칙

`src/preprocessing/label_jobs.py`

기존 단순 키워드 기반 라벨링을 직무별 weighted keyword scoring 방식으로 개선했습니다.

개선 내용:

```text
제목 키워드 가중치 반영
description / tags 기반 라벨링 보강
직무별 주요 기술 키워드 확장
영문/한글 직무 표현 동시 지원
Unknown 라벨 비율 감소
```

라벨 대상:

```text
Data Engineer
Backend Engineer
ML Engineer
DevOps Engineer
Data Analyst
Unknown
```

### 6. 데이터 품질 체크

`src/quality/check_training_data.py`

전처리 결과가 모델 학습에 적합한지 확인합니다.

검증 항목:

```text
raw_job_posts 데이터 존재 여부
cleaned_job_posts 최소 학습 데이터 수
job_post_skills 추출 결과 존재 여부
text_for_model 누락 여부
job_category 누락 여부
직무 카테고리 다양성
Unknown 라벨 비율
```

데이터 품질 기준을 통과하지 못하면 DAG를 실패시켜, 부적절한 데이터로 모델 학습이 진행되지 않도록 합니다.

### 6-1. Data Contract Check

`config/data_contract.json`  
`src/quality/check_data_contract.py`

Raw / cleaned / skill extraction 결과가 파이프라인에서 기대하는 데이터 계약을 만족하는지 검증합니다.

검증 항목:

```text
필수 테이블 존재 여부
필수 컬럼 존재 여부
컬럼 타입 검증
최소 row count 검증
필수 컬럼 null ratio 검증
필수 text 컬럼 empty ratio 검증
job_category 허용값 검증
```

현재 contract 대상:

```text
raw_job_posts
- source, source_job_id, title, description 필수 컬럼 검증
- source null ratio 0 기준 검증
- title / description null·empty ratio 기준 검증

cleaned_job_posts
- raw_id, text_for_model, job_category 필수 컬럼 검증
- text_for_model / job_category null·empty ratio 0 기준 검증
- job_category가 허용 라벨 목록 안에 있는지 검증

job_post_skills
- optional skill extraction 산출물로 관리
- 현재 row가 0이어도 pipeline을 실패시키지 않도록 min_rows=0 적용
- id, job_post_id, skill_name schema 기준으로 검증
```

실행:

```bash
make data-contract-check
```

검증 결과는 `pipeline_check_results` 테이블에 `DATA_CONTRACT` 타입으로 저장됩니다.

DAG에서는 전처리 이후, 학습 데이터 품질 체크 이전에 실행합니다.

```text
preprocess_jobs
    ↓
check_data_contract
    ↓
check_training_data
```

이를 통해 전처리 결과의 schema, 필수 컬럼, 라벨 값이 깨진 상태에서 모델 학습 단계로 넘어가지 않도록 방지합니다.

### 7. 검증 결과 저장

`src/quality/check_logger.py`

데이터 품질 체크, 모델 성능 체크, class-level model performance gate, prediction quality gate, prediction drift gate 결과를 PostgreSQL의 `pipeline_check_results` 테이블에 저장합니다.

저장 대상:

```text
DATA_CONTRACT
DATA_QUALITY
MODEL_PERFORMANCE
MODEL_CLASS_PERFORMANCE
PREDICTION_QUALITY
PREDICTION_DRIFT
```

저장 컬럼:

```text
check_type
check_name
status
metric_value
threshold_value
message
dag_id
task_id
run_id
checked_at
```

이를 통해 Airflow DAG 실행 시점마다 어떤 검증 항목이 통과 또는 실패했는지 추적할 수 있습니다.

### 8. 모델 학습

`src/training/train_baseline.py`

PostgreSQL의 `cleaned_job_posts` 테이블에서 학습 데이터를 읽어 모델을 학습합니다.

모델 구성:

```text
TF-IDF Vectorizer
+ Logistic Regression
```

학습 결과:

```text
models/job_classifier.pkl
MLflow experiment/run 기록
MLflow model artifact 저장
MLflow training dataset metadata 저장
MLflow evaluation artifact 저장
```


`crawler_only` 모드에서는 실제 외부 데이터 분포가 치우칠 수 있으므로, stratified split이 불가능한 rare class를 학습 전에 제외합니다.

```text
MIN_SAMPLES_PER_CLASS보다 적은 라벨
→ 학습 데이터에서 제외
→ 남은 라벨 기준으로 stratified train/test split 수행
```

관련 환경변수:

```env
MIN_SAMPLES_PER_CLASS=2
TEST_SIZE=0.3
```

학습 과정에서는 모델 artifact뿐 아니라 학습 데이터와 평가 산출물도 함께 기록합니다.

```text
training_dataset_profile.json
training_dataset_hash
classification_report.json
classification_report.csv
classification_report.txt
confusion_matrix.csv
evaluation_distribution.json
class-level precision / recall / f1-score / support metrics
```

이를 통해 특정 MLflow run이 어떤 데이터 분포로 학습되었고, 직무 카테고리별로 어떤 평가 결과를 냈는지 추적할 수 있습니다.


### 9. MLflow Tracking

MLflow는 PostgreSQL의 `mlflow` DB를 backend store로 사용합니다.

```text
MLFLOW_TRACKING_URI=postgresql+psycopg2://jobskill:jobskill@postgres:5432/mlflow
```

Artifact는 로컬 `mlartifacts/` 디렉터리에 저장됩니다.

```text
MLFLOW_ARTIFACT_ROOT=/opt/airflow/project/mlartifacts
```

MLflow UI:

```text
http://localhost:5000
```


MLflow run에는 모델 성능뿐 아니라 학습 데이터와 평가 산출물도 함께 기록합니다.

저장 항목:

```text
training_dataset_name
training_dataset_source
training_dataset_row_count
training_dataset_hash
training_dataset_profile.json
classification_report.json
classification_report.csv
classification_report.txt
confusion_matrix.csv
evaluation_distribution.json
eval_precision_{label}
eval_recall_{label}
eval_f1_{label}
eval_support_{label}
```

Artifact 구조 예시:

```text
mlartifacts/{run_id}/artifacts/
├── model/
├── training_dataset_profile.json
└── evaluation/
    ├── classification_report.json
    ├── classification_report.csv
    ├── classification_report.txt
    ├── confusion_matrix.csv
    └── evaluation_distribution.json
```

이를 통해 특정 MLflow run이 어떤 학습 데이터 분포와 어떤 class-level 성능을 기준으로 생성되었는지 추적할 수 있습니다.

<img src="docs/images/mlflow.png" width="900">

### 10. 모델 성능 체크

`src/quality/check_model_performance.py`

MLflow에 기록된 최신 학습 run의 metric을 조회해 모델 성능 기준을 검증합니다.

검증 항목:

```text
accuracy >= MIN_MODEL_ACCURACY
f1_weighted >= MIN_MODEL_F1_WEIGHTED
```

모델 성능이 기준보다 낮으면 DAG를 실패시켜, 낮은 품질의 모델이 promotion 또는 batch inference 단계로 넘어가지 않도록 합니다.

### 10-1. Class-level Model Performance Gate

`src/quality/check_model_class_performance.py`

MLflow에 저장된 class-level evaluation metric을 조회해 모델 승격 이전에 직무 카테고리별 성능 기준을 검증합니다.

검증 metric:

```text
eval_f1_{label}
eval_recall_{label}
eval_support_{label}
```

환경변수:

```env
MIN_CLASS_F1=0.70
MIN_CLASS_RECALL=0.60
MIN_CLASS_SUPPORT=1
```

실행:

```bash
make model-class-performance-check
```

DAG 흐름:

```text
train_model
    ↓
check_model_performance
    ↓
check_model_class_performance
    ↓
promote_model
```

전체 `accuracy`와 `f1_weighted`가 기준을 통과하더라도 특정 직무 카테고리의 recall 또는 f1-score가 낮으면 모델 승격을 차단합니다.

검증 결과는 `pipeline_check_results`에 `MODEL_CLASS_PERFORMANCE` 타입으로 저장됩니다.


### 11. 모델 승격

`src/training/promote_model.py`

MLflow에 기록된 최신 학습 run의 성능을 기준으로 기존 best model과 비교합니다.

승격 조건:

```text
기존 promoted model이 없는 경우
또는 최신 모델의 f1_weighted가 기존 best model보다 높은 경우
또는 f1_weighted가 같고 accuracy가 더 높은 경우
```

승격된 모델은 아래 경로에 저장됩니다.

```text
models/best/job_classifier.pkl
```

승격 결과는 PostgreSQL의 `model_registry` 테이블에 저장됩니다.

```text
PROMOTED
REJECTED
```

이를 통해 기준 미달 모델이나 기존 best보다 낮은 성능의 모델이 추론 단계에 사용되지 않도록 제어합니다.

### 11-1. Model Promotion Archive

`scripts/archive_promoted_model.py`

현재 `PROMOTED` 상태의 모델과 `models/best/job_classifier.pkl` 파일을 archive 디렉터리에 스냅샷으로 저장합니다.

실행:

```bash
make model-archive
```

생성 파일 예시:

```text
models/promoted_archive/job_classifier_registry_12_20260721_153000.pkl
```

Archive 이력은 `model_promotion_archives` 테이블에 저장됩니다.

저장 항목:

```text
model_registry_id
model_name
model_version
model_run_id
source_model_path
archived_model_path
accuracy
f1_weighted
archive_reason
created_by
created_at
```

이 기능은 새로운 모델이 best model path를 덮어쓰기 전에 현재 promoted model artifact를 보존하기 위한 운영 기능입니다. 추후 모델 품질 이슈가 발생했을 때 `Model Rollback CLI`가 이 archive를 기준으로 이전 안정 버전을 복구할 수 있습니다.

Archive 이력 확인:

```bash
docker compose exec postgres psql -U jobskill -d jobskill -c "
SELECT
    id,
    model_registry_id,
    model_name,
    archived_model_path,
    accuracy,
    f1_weighted,
    created_by,
    created_at
FROM model_promotion_archives
ORDER BY id DESC
LIMIT 10;
"
```

### 11-2. Model Rollback CLI

`scripts/rollback_promoted_model.py`

`model_promotion_archives`에 저장된 archived model artifact를 사용해 이전 promoted model로 되돌리는 rollback 스크립트입니다.

Rollback은 기본적으로 dry-run으로 동작합니다. 먼저 rollback plan을 확인합니다.

```bash
make model-rollback-plan
```

특정 archive를 기준으로 plan을 확인하려면 archive id를 지정합니다.

```bash
MODEL_ROLLBACK_ARCHIVE_ID=3 make model-rollback-plan
```

실제 rollback 실행:

```bash
MODEL_ROLLBACK_ARCHIVE_ID=3 make model-rollback
```

Rollback 수행 내용:

```text
현재 models/best/job_classifier.pkl 백업
archived model artifact를 models/best/job_classifier.pkl로 복원
기존 PROMOTED model_registry row를 ROLLED_BACK 처리
rollback 대상 model_registry row를 PROMOTED 처리
model_rollback_actions 테이블에 rollback 이력 저장
```

Rollback plan 예시:

```text
Model Rollback Plan
===================
dry_run                  : True
archive_id               : 1
target_model_registry_id : 1
target_model_name        : job_classifier
target_accuracy          : 1.0
target_f1_weighted       : 1.0
target_registry_status   : PROMOTED
archived_model_path      : /opt/airflow/project/models/promoted_archive/job_classifier_registry_1_20260721_063458.pkl
current_promoted_id      : 1
current_model_name       : job_classifier
current_accuracy         : 1.0
current_f1_weighted      : 1.0
best_model_path          : /opt/airflow/project/models/best/job_classifier.pkl
backup_model_path        : /opt/airflow/project/models/rollback_backup/job_classifier_before_rollback_registry_1_20260721_071155.pkl
```

`dry_run=True`일 때는 실제 파일 복사, `model_registry` 상태 변경, `model_rollback_actions` 저장을 수행하지 않습니다. 실제 rollback은 `MODEL_ROLLBACK_DRY_RUN=false`와 `MODEL_ROLLBACK_ARCHIVE_ID`가 함께 설정된 경우에만 수행합니다.

Rollback 이력 확인:

```bash
docker compose exec postgres psql -U jobskill -d jobskill -c "
SELECT
    id,
    archive_id,
    target_model_registry_id,
    previous_model_registry_id,
    archived_model_path,
    restored_model_path,
    backup_model_path,
    rollback_reason,
    created_by,
    status,
    created_at
FROM model_rollback_actions
ORDER BY id DESC
LIMIT 10;
"
```

Rollback 후 API serving model을 다시 로드합니다.

```bash
curl -X POST http://localhost:8000/reload-model
curl -fsS http://localhost:8000/model | jq
curl -fsS http://localhost:8000/ready | jq
```

이 기능은 새로 승격한 모델에 품질 문제가 생겼을 때 이전 archived promoted model로 되돌리기 위한 모델 운영 복구 절차입니다.

### 11-3. Model Lifecycle Dashboard

`src/dashboard/app.py`

Streamlit Dashboard의 `Model Lifecycle` 탭에서 현재 promoted model, promoted model archive 이력, rollback action 이력을 확인할 수 있습니다.

확인 가능한 항목:

```text
Current Promoted Model
Model Lifecycle Summary
Promoted Model Archives
Rollback Plan Helper
Recent Rollback Actions
```

Rollback Plan Helper에서는 선택한 archive를 기준으로 현재 promoted model과 rollback 대상 `model_registry_id`를 비교하고, 실제 rollback에 사용할 CLI 명령어를 제공합니다.

예시:

```bash
MODEL_ROLLBACK_ARCHIVE_ID=1 make model-rollback-plan

MODEL_ROLLBACK_ARCHIVE_ID=1 make model-rollback

curl -X POST http://localhost:8000/reload-model
curl -fsS http://localhost:8000/model | jq
curl -fsS http://localhost:8000/ready | jq
```

실제 rollback은 모델 파일 복구와 DB 상태 변경을 포함하므로 Dashboard에서 직접 실행하지 않고 CLI에서 명시적으로 수행합니다.

### 11-4. Model Lifecycle Integrity Check

`scripts/check_model_lifecycle_integrity.py`

모델 운영 상태가 DB와 파일 시스템 기준으로 일관적인지 검증합니다.

실행:

```bash
make model-lifecycle-check
```

검증 항목:

```text
model_registry 테이블 존재 여부
model_promotion_archives 테이블 존재 여부
model_rollback_actions 테이블 존재 여부
PROMOTED 모델이 정확히 1개인지 확인
PROMOTED model의 promoted_model_path 존재 여부 확인
models/best/job_classifier.pkl 존재 여부 확인
BEST_MODEL_PATH와 promoted_model_path 일치 여부 확인
archive row의 model_registry_id 유효성 확인
archive row의 archived_model_path 파일 존재 여부 확인
rollback action의 archive_id / target_model_registry_id / previous_model_registry_id 유효성 확인
rollback action의 archived/restored/backup model file 존재 여부 확인
```

이 검증은 DB와 실제 모델 파일이 필요하므로 `ops-static-check`에는 포함하지 않고, 서비스 기동 후 실행하는 `ops-check`에 포함합니다.

### 11-5. Model Card Report

`src/reporting/generate_model_card.py`

현재 `PROMOTED` 상태의 모델을 기준으로 운영 문서인 Model Card를 생성합니다.

실행:

```bash
make model-card
```

생성 파일:

```text
reports/latest_model_card.md
reports/model_cards/model_card_registry_{model_registry_id}.md
```

포함 항목:

```text
현재 PROMOTED 모델 정보
MLflow run ID
accuracy / f1_weighted
classification report
evaluation distribution
training dataset profile
training dataset hash
MLflow params / metrics
model archive 정보
rollback action 정보
운영 참고사항
```

Model Card는 MLflow run, model_registry, training dataset metadata, evaluation artifact, archive/rollback 이력을 하나의 Markdown 문서로 통합합니다.

DAG에서는 모델 승격 이후, batch inference 이전에 생성합니다.

```text
promote_model
    ↓
generate_model_card
    ↓
batch_inference
```


### 12. Prediction Lineage

`src/common/model_registry.py`

batch inference와 FastAPI 예측은 `model_registry`에서 현재 PROMOTED 상태의 모델 metadata를 조회합니다.

예측 결과에는 아래 모델 정보를 함께 저장합니다.

```text
model_name
model_version
model_run_id
model_registry_id
model_path
```

이를 통해 `model_predictions`의 각 예측 결과가 어떤 MLflow run과 어떤 promoted model에서 생성되었는지 추적할 수 있습니다.

```text
model_registry
    ↓
model_predictions
```

### 13. 예측 품질 정보

`src/common/prediction_quality.py`

FastAPI와 batch inference 예측 결과에 단순 예측값뿐 아니라 예측 품질 정보를 함께 저장합니다.

저장 정보:

```text
confidence
confidence_level
is_low_confidence
top_predictions
```

예측 품질 기준:

```text
HIGH   : confidence >= 0.8
MEDIUM : confidence >= 0.6
LOW    : confidence < 0.6
```

이를 통해 예측 결과가 낮은 신뢰도인지, 상위 후보군이 어떻게 분포하는지 확인할 수 있습니다.

### 13-1. Prediction Quality Gate

`src/quality/check_prediction_quality.py`

batch inference 이후 예측 결과 품질을 검증합니다.

검증 항목:

```text
prediction_count
avg_prediction_confidence
low_confidence_ratio
null_confidence_count
```

환경변수:

```env
MIN_AVG_PREDICTION_CONFIDENCE=0.6
MAX_LOW_CONFIDENCE_RATIO=0.4
MIN_PREDICTION_ROWS=1
```

검증 결과는 `pipeline_check_results`에 `PREDICTION_QUALITY` 타입으로 저장됩니다.

DAG 흐름:

```text
batch_inference
    ↓
check_prediction_quality
    ↓
check_prediction_drift
    ↓
generate_pipeline_report
    ↓
notify_pipeline_status
```

예측 품질 기준을 통과하지 못하면 DAG를 실패시켜, 낮은 품질의 예측 결과가 정상 산출물처럼 리포트되지 않도록 합니다.


### 13-2. Prediction Drift Gate

`src/quality/check_prediction_drift.py`

batch inference 이후 rule label 분포와 batch prediction 분포를 비교해 예측 분포가 크게 달라졌는지 검증합니다.

비교 대상:

```text
cleaned_job_posts.job_category
model_predictions.predicted_category where prediction_source = BATCH
```

검증 항목:

```text
label_distribution_rows
prediction_distribution_rows
prediction_distribution_psi
```

환경변수:

```env
MAX_PREDICTION_DISTRIBUTION_PSI=0.25
MIN_DRIFT_CHECK_ROWS=1
```

PSI 기준은 예측 분포가 기준 분포에서 얼마나 벗어났는지 확인하는 용도로 사용합니다.

```text
0.1 이하  : 거의 안정적
0.1~0.25 : 약간의 분포 변화
0.25 이상: 의미 있는 분포 변화로 간주
```

검증 결과는 `pipeline_check_results`에 `PREDICTION_DRIFT` 타입으로 저장됩니다.

DAG 흐름:

```text
batch_inference
    ↓
check_prediction_quality
    ↓
check_prediction_drift
    ↓
generate_pipeline_report
    ↓
notify_pipeline_status
```

예측 confidence가 높더라도 특정 직무로 예측이 과도하게 쏠리는 상황을 감지할 수 있도록 구성했습니다.


### 14. Batch Inference

`src/inference/batch_inference.py`

현재 promoted model을 이용해 `cleaned_job_posts` 전체 데이터에 대해 일괄 예측을 수행하고, 결과를 `model_predictions` 테이블에 저장합니다.

```text
cleaned_job_posts
→ promoted model predict
→ prediction quality 계산
→ model_predictions 저장
```

batch inference 결과에는 예측값, confidence, top-k 후보, model lineage가 함께 저장됩니다.

`model_predictions.prediction_source`에는 `BATCH`가 저장됩니다.

```text
prediction_source = BATCH
```

API 예측 로그가 `model_predictions`를 FK로 참조할 수 있기 때문에, batch inference 재실행 시 `model_predictions` 전체를 TRUNCATE하지 않습니다. 대신 batch 결과만 삭제 후 재생성합니다.

```sql
DELETE FROM model_predictions
WHERE COALESCE(prediction_source, 'BATCH') = 'BATCH';
```

### 15. FastAPI

`src/inference/api.py`

현재 promoted model을 로드해 단건 예측 API를 제공합니다.

주요 기능:

```text
GET  /
GET  /health
GET  /ready
GET  /model
GET  /metrics
GET  /runbooks
GET  /runbooks/{filename}
GET  /runbooks/{filename}/raw
POST /reload-model
POST /predict
POST /alertmanager/webhook
```

`/predict`는 아래 작업을 수행합니다.

```text
직무 카테고리 예측
confidence 반환
confidence_level 반환
low confidence 여부 반환
top-k prediction 반환
기술스택 추출
model_predictions 테이블 저장
api_prediction_logs 테이블 저장
model lineage 저장
latency_ms 저장
성공/실패 status 저장
```

API 예측은 `model_predictions.prediction_source = API`로 저장되며, API 요청/응답 로그는 `api_prediction_logs`에 별도로 저장됩니다.

```text
model_predictions
→ 모델 예측 결과 저장

api_prediction_logs
→ FastAPI 요청/응답/실패/latency 로그 저장
```

FastAPI는 시작 시점에 모델을 로드하며, 요청 시점에 현재 promoted model metadata를 확인합니다. 모델 파일 또는 registry 정보가 변경되면 새 모델을 자동으로 reload합니다.

<img src="docs/images/fastapi.png" width="900">


### 15-1. Sample API Requests

`scripts/send_sample_api_requests.py`

FastAPI `/predict` 엔드포인트가 정상적으로 동작하고, API 예측 결과와 요청 로그가 PostgreSQL에 저장되는지 확인하기 위한 샘플 요청 스크립트입니다.

검증 내용:

```text
GET /
GET /model
POST /predict
API prediction 저장
api_prediction_logs 저장
prediction_source=API 저장
```

실행:

```bash
make api-sample
```

또는 직접 실행:

```bash
python scripts/send_sample_api_requests.py
```

실행 후 아래 테이블에 API 요청 결과가 저장됩니다.

```text
model_predictions.prediction_source = API
api_prediction_logs.status = SUCCESS
```

이 스크립트는 로컬 검증뿐 아니라 smoke check에서도 사용되어, API가 단순히 기동된 상태를 넘어 실제 예측 요청과 DB 저장까지 정상 동작하는지 확인합니다.



### 15-2. FastAPI Health / Readiness Check

`src/inference/api.py`

FastAPI는 liveness와 readiness를 분리해서 제공합니다.

```text
GET /health
GET /ready
```

`/health`는 FastAPI 프로세스가 살아 있는지 확인하는 liveness endpoint입니다.

```bash
curl -fsS http://localhost:8000/health
```

`/ready`는 실제 예측 요청을 받을 준비가 되었는지 확인하는 readiness endpoint입니다.

확인 항목:

```text
PostgreSQL 연결 가능 여부
PROMOTED model_registry 존재 여부
promoted model file 존재 여부
```

```bash
curl -fsS http://localhost:8000/ready
```

`/ready`는 DB 연결 실패, promoted model 누락, model file 누락 시 `503 Service Unavailable`을 반환합니다.

Docker Compose healthcheck는 프로세스 생존 여부를 보기 위해 `/health`를 사용하고, smoke check는 `/ready`까지 확인해 API가 실제 요청을 받을 준비가 되었는지 검증합니다.

### 15-3. Prometheus Metrics

`src/monitoring/prometheus_metrics.py`  
`GET /metrics`

FastAPI `/metrics` 엔드포인트를 통해 PostgreSQL에 저장된 MLOps 운영 지표를 Prometheus text format으로 노출합니다.

노출 지표 예시:

```text
raw job count by source
total alert events
firing alert events
alert events by status
alert events by severity
alert events by alert name
cleaned job count by source
top skill count
prediction count by source
average prediction confidence
low confidence prediction ratio
prediction category distribution
API request count by status
API average latency
pipeline check result count
model registry count
latest promoted model accuracy / f1_weighted
alert event count by alert name / severity / service / status
current alert state count by alert name / severity / service / status
alert acknowledgement count by alert name / severity / service / status
average MTTA by alert name / severity / service
average MTTR by alert name / severity / service
current unacknowledged firing alert count
alert maintenance mode state
API readiness state
API database readiness state
API promoted model readiness state
API promoted model file existence state
```

확인:

```bash
curl -fsS http://localhost:8000/metrics | head -50
```

또는 Makefile 명령어:

```bash
make metrics
```

예시 지표:

```text
jobskill_model_predictions_total{prediction_source="BATCH"} 350
jobskill_model_predictions_total{prediction_source="API"} 10
jobskill_model_prediction_low_confidence_ratio{prediction_source="BATCH"} 0.3171
jobskill_api_prediction_requests_total{status="SUCCESS"} 10
jobskill_latest_promoted_model_f1_weighted{model_registry_id="12"} 0.9338
jobskill_alert_events_total{alert_name="JobSkillApiHighLowConfidenceRatio",severity="warning",service="jobskill-api",status="firing"} 1
jobskill_alert_current_states_total{alert_name="JobSkillApiHighLowConfidenceRatio",severity="warning",service="jobskill-api",status="firing"} 1
jobskill_alert_acknowledgements_total{alert_name="JobSkillApiHighLowConfidenceRatio",severity="warning",service="jobskill-api",status="firing"} 1
jobskill_alert_avg_mtta_minutes{alert_name="JobSkillApiHighLowConfidenceRatio",severity="warning",service="jobskill-api"} 2.5
jobskill_alert_avg_mttr_minutes{alert_name="JobSkillApiHighLowConfidenceRatio",severity="warning",service="jobskill-api"} 8.0
jobskill_alert_unacknowledged_current_total{alert_name="JobSkillPipelineCheckFailure",severity="warning",service="jobskill-pipeline"} 1
jobskill_alert_maintenance_mode 0
jobskill_api_ready 1
jobskill_api_database_ready 1
jobskill_api_promoted_model_ready 1
jobskill_api_promoted_model_file_exists 1
```

이 엔드포인트는 Prometheus를 붙이기 전 단계에서 서비스가 외부 모니터링 시스템에 제공할 운영 지표를 표준화하는 역할을 합니다.

### 15-4. Alert Runbook API

`src/inference/api.py`  
`docs/runbooks/*.md`

Prometheus alert가 발생했을 때 Slack이나 Streamlit Dashboard에서 바로 대응 문서를 열 수 있도록 FastAPI에서 runbook을 제공합니다.

제공 endpoint:

```text
GET /runbooks
GET /runbooks/{filename}
GET /runbooks/{filename}/raw
```

동작 방식:

```text
docs/runbooks/*.md
→ FastAPI가 Markdown 파일 조회
→ /runbooks/{filename}에서 HTML로 렌더링
→ /runbooks/{filename}/raw에서 원본 Markdown 반환
→ Slack / Streamlit Dashboard에서 클릭 가능한 링크로 사용
```

확인:

```bash
curl -fsS http://localhost:8000/runbooks
curl -fsS http://localhost:8000/runbooks/jobskill_pipeline_check_failure.md | head
curl -fsS http://localhost:8000/runbooks/jobskill_pipeline_check_failure.md/raw | head
```

브라우저에서 아래 URL을 열면 Markdown 원문이 아니라 HTML로 렌더링된 runbook 문서를 확인할 수 있습니다.

```text
http://localhost:8000/runbooks/jobskill_pipeline_check_failure.md
```

현재 관리하는 runbook:

```text
jobskill_api_metrics_down.md
jobskill_api_not_ready.md
jobskill_high_low_confidence_ratio.md
jobskill_api_high_latency.md
jobskill_pipeline_check_failure.md
jobskill_promoted_model_low_performance.md
jobskill_alertmanager_slack_notification.md
jobskill_unacknowledged_current_alert.md
jobskill_alert_response_slo_breach.md
```

API 이미지 빌드 시에는 전체 개발/학습용 `requirements.txt` 대신 serving에 필요한 패키지만 담은 `requirements-api.txt`를 사용해 빌드 시간을 줄입니다.


### 16. Pipeline Report

`src/reporting/generate_pipeline_report.py`

모델 registry, prediction lineage, pipeline check 결과를 조회해 Markdown 리포트를 생성합니다.

생성 파일:

```text
reports/latest_pipeline_report.md
```

리포트 포함 내용:

```text
Latest Promoted Model
Model Registry History
Prediction Lineage Summary
Latest Predictions
Prediction Category Distribution
Check Result Summary
Latest Check Details
Failed Checks
Model Promotion Summary
Raw Job Count by Source
Cleaned Job Quality by Source
Job Category Distribution by Source
Skill Extraction Summary by Source
Top Skills by Source
Prediction Summary by Source
Prediction Quality Check Results
Prediction Quality Summary
Prediction Quality by Category
Prediction Drift Check Results
API Request Quality Summary
API Low Confidence Summary
Recent API Prediction Logs
```

이를 통해 현재 서빙 모델, 모델 승격 이력, 예측 lineage, 데이터/모델 검증 결과, source별 데이터 품질을 한 번에 확인할 수 있습니다.


### 16-1. Streamlit Dashboard

`src/dashboard/app.py`

PostgreSQL에 저장된 MLOps 파이프라인 실행 결과와 alert 상태를 조회하는 대시보드입니다.

확인 가능한 항목:

```text
Model Lifecycle
Model Evaluation
Model Card
Current promoted model
Promoted model archives
Rollback plan helper
Rollback action history
Class-level model performance summary
Source data quality
Batch prediction quality
Pipeline check results
FastAPI prediction logs
Current Alerts
Alert History
Incident Response Report
Recent predictions
```

Docker Compose 서비스:

```text
dashboard
```

실행:

```bash
docker compose up -d dashboard
```

접속:

```text
http://localhost:8501
```


Model Evaluation 탭에서는 `MODEL_CLASS_PERFORMANCE` 검증 결과를 조회해 직무 카테고리별 support, recall, f1-score와 threshold, pass/fail 상태를 확인할 수 있습니다.

확인 가능한 항목:

```text
Latest class-level performance check time
Passed / failed class gate count
Class-level performance summary
Class gate status distribution
F1 score by class
Recall by class
Raw MODEL_CLASS_PERFORMANCE check results
```

Model Card 탭에서는 현재 `PROMOTED` 모델 기준으로 생성된 `reports/latest_model_card.md`를 조회할 수 있습니다.

제공 기능:

```text
Model Card 파일 존재 여부 확인
Model Card 생성 시간 확인
Dashboard에서 Model Card 재생성
Markdown Model Card 다운로드
Model Card Preview
```

Model Card 생성 버튼은 Dashboard 컨테이너에서 `reports/latest_model_card.md`를 쓰므로, Docker Compose dashboard 서비스에는 아래 mount가 필요합니다.

```yaml
- ./reports:/opt/airflow/project/reports
```

Alert 관련 화면은 현재 상태와 이벤트 이력을 분리해서 보여줍니다.

```text
Current Alerts
→ alert_current_states 기준
→ fingerprint별 현재 firing/resolved 상태 확인
→ 동일 alert가 반복 수신되어도 현재 상태는 1건으로 관리

Alert History
→ alert_events 기준
→ Alertmanager가 전송한 firing/resolved 이벤트 이력 확인
→ 같은 alert가 반복 전송되면 이벤트 이력에는 여러 건으로 누적
```

Current Alerts 탭에서 확인 가능한 항목:

```text
Alert Maintenance Mode
Maintenance Mode ON/OFF
Current Alert States
Currently Firing
Resolved States
Warning Firing
Critical Firing
Currently Firing Alerts
Silence Alert
Acknowledge Alert
Recent Acknowledgements
Recent Silence Actions
Active Alertmanager Silences
All Current Alert States
Runbook 링크
Grafana 링크
Prometheus 링크
```

Current Alerts와 Alert History는 `annotations` JSONB에 저장된 `runbook_url`, `dashboard_url`, `prometheus_url`을 컬럼으로 노출합니다. 기존 alert row에 annotation이 없더라도 alert name 기준 fallback URL을 생성해 과거 alert에서도 대응 링크를 확인할 수 있습니다.

Current Alerts에서는 firing alert를 선택해 확인자와 조치 메모를 저장할 수 있습니다. 저장된 acknowledgement는 `alert_acknowledgements` 테이블에 남고, Alert History에서는 이를 기반으로 MTTA와 MTTR을 계산해 alert 대응 속도를 확인합니다.

Current Alerts에서는 특정 firing alert를 선택해 Alertmanager silence를 생성할 수 있습니다. 이 기능은 전체 maintenance mode를 켜지 않고도 특정 `alertname` / `service` / `severity` 조합만 30분, 1시간, 2시간 또는 사용자 지정 시간 동안 mute할 때 사용합니다. 생성된 silence 이력은 `alert_silence_actions` 테이블에 저장됩니다.

또한 Current Alerts 상단에서 Alert Maintenance Mode를 ON/OFF할 수 있습니다. 이 값은 `alert_settings` 테이블에 저장되고 FastAPI `/metrics`의 `jobskill_alert_maintenance_mode` 지표로 노출되어, Prometheus가 non-critical alert rule을 억제할 때 사용합니다.

Alert History 탭에서 확인 가능한 항목:

```text
Total Alert Events
Firing Events
Resolved Events
Latest Event
Alert Response Metrics
Average MTTA
Average MTTR
Recent Alert Response Details
Alert Event Status Distribution
Alert Event Severity Distribution
Alert Event Summary
Recent Alert Event History
```

Incident Report 탭에서 확인 가능한 항목:

```text
Generate incident report
Report Preview
Download Markdown report
reports/latest_incident_response_report.md 생성 시각
```

Incident Response Report는 alert event, current alert state, acknowledgement, silence action, MTTA/MTTR, pipeline failure, API quality를 종합해 Markdown 문서로 생성합니다.

Model Lifecycle 탭에서는 현재 `PROMOTED` 모델, promoted model archive 이력, rollback action 이력, archive 기준 rollback plan helper를 제공합니다. 기존 단순 Latest Model 화면을 확장해 모델 운영 복구 흐름까지 Dashboard에서 확인할 수 있도록 구성했습니다.

<img src="docs/images/dashboard.png" width="900">


### 16-2. Pipeline Notification

`src/notification/notify_pipeline_status.py`

PostgreSQL에 저장된 파이프라인 실행 결과를 조회해 운영 상태 요약 메시지를 생성합니다.

확인 항목:

```text
Latest promoted model
Recent pipeline check summary
Recent failed checks
Prediction count / confidence summary
API request status / latency summary
```

환경변수:

```env
ALERT_ENABLED=false
ALERT_ONLY_ON_FAILURE=false
SLACK_WEBHOOK_URL=
ALERT_MAINTENANCE_MODE=false
ALERTMANAGER_URL=http://alertmanager:9093
ALERT_SILENCE_DEFAULT_MINUTES=30
ALERT_MAINTENANCE_MODE=false
```

동작 방식:

```text
ALERT_ENABLED=false
→ Slack 전송 없이 콘솔에 메시지만 출력

ALERT_ENABLED=true
→ SLACK_WEBHOOK_URL이 있으면 Slack으로 전송

ALERT_ONLY_ON_FAILURE=true
→ failed check가 있을 때만 전송
```

실행:

```bash
make notify
```

또는 직접 실행:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/notification/notify_pipeline_status.py"
```

`SLACK_WEBHOOK_URL`은 실제 운영 또는 개인 Slack 테스트 시 `.env`에만 추가하고 Git에는 포함하지 않습니다. `.env.example`에는 빈 값만 유지합니다.

### 16-3. Maintenance Cleanup

`src/maintenance/cleanup_old_records.py`

API 요청 로그, API 예측 결과, pipeline check 결과가 무한히 쌓이지 않도록 보관 기간 기반 cleanup 스크립트를 제공합니다.

정리 대상:

```text
api_prediction_logs
model_predictions 중 prediction_source = API
pipeline_check_results
```

환경변수:

```env
CLEANUP_DRY_RUN=true
API_LOG_RETENTION_DAYS=30
API_PREDICTION_RETENTION_DAYS=30
PIPELINE_CHECK_RETENTION_DAYS=90
```

기본값은 `CLEANUP_DRY_RUN=true`이므로 실제 삭제 없이 삭제 대상 건수만 확인합니다. 실제 삭제가 필요할 때만 `.env`에서 `CLEANUP_DRY_RUN=false`로 변경합니다.

실행:

```bash
make cleanup
```

또는 직접 실행:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/maintenance/cleanup_old_records.py"
```



### 16-4. Prometheus

`monitoring/prometheus/prometheus.yml`

FastAPI `/metrics` 엔드포인트를 Prometheus가 주기적으로 scrape하도록 구성합니다.

수집 대상:

```text
api:8000/metrics
```

실행:

```bash
make prometheus
```

접속:

```text
http://localhost:9090
```

Target 확인:

```text
http://localhost:9090/targets
```

주요 Prometheus query:

```text
jobskill_model_predictions_total
jobskill_model_prediction_avg_confidence
jobskill_model_prediction_low_confidence_ratio
jobskill_api_prediction_requests_total
jobskill_api_prediction_avg_latency_ms
jobskill_pipeline_check_results_total
jobskill_pipeline_recent_failed_checks_total
jobskill_latest_promoted_model_f1_weighted
jobskill_model_registry_records_total
jobskill_alert_events_total
jobskill_alert_current_states_total
jobskill_alert_acknowledgements_total
jobskill_alert_avg_mtta_minutes
jobskill_alert_avg_mttr_minutes
jobskill_alert_unacknowledged_current_total
jobskill_alert_maintenance_mode
jobskill_api_ready
jobskill_api_database_ready
jobskill_api_promoted_model_ready
jobskill_api_promoted_model_file_exists
```

`jobskill-api` target이 `UP`이면 FastAPI `/metrics` endpoint를 정상적으로 수집하고 있는 상태입니다.

### 16-5. Grafana Dashboard

`monitoring/grafana/provisioning/datasources/prometheus.yml`  
`monitoring/grafana/provisioning/dashboards/dashboard.yml`  
`monitoring/grafana/dashboards/jobskill-mlops-overview.json`

Prometheus가 수집한 JobSkill MLOps metrics를 Grafana에서 시각화합니다.

실행:

```bash
make grafana
```

접속:

```text
http://localhost:3000
```

기본 계정:

```text
admin / admin
```

확인 가능한 지표:

```text
Batch/API prediction count
latest promoted model accuracy/f1
average prediction confidence
low confidence ratio
prediction category distribution
pipeline check results
API average latency
raw job count by source
historical alert events
historical firing alert events
historical alert events by status
historical alert events by severity
historical alert events by alert name
current alert states
current firing alerts
current alerts by status
current firing alerts by name
alert acknowledgement count
current unacknowledged alerts
average MTTA by alert
average MTTR by alert
```

Grafana에서는 alert 지표를 두 종류로 분리해서 봅니다.

```text
jobskill_alert_events_total
→ 누적 alert event 이력
→ historical alert event 패널에서 사용

jobskill_alert_current_states_total
→ fingerprint 기준 현재 alert 상태
→ current alert state 패널에서 사용
```

대시보드는 provisioning으로 자동 등록되며, Grafana 접속 후 아래 경로에서 확인할 수 있습니다.

```text
Dashboards
→ JobSkill MLOps
→ JobSkill MLOps Overview
```

<img src="docs/images/grafana.png" width="900">

### 16-6. Prometheus Alert Rules

`monitoring/prometheus/rules/jobskill_alert_rules.yml`

Prometheus가 수집한 JobSkill 운영 지표를 기준으로 alert 조건을 평가합니다.

검증 대상:

```text
FastAPI /metrics scrape 실패
FastAPI readiness 실패
API prediction low confidence ratio 증가
BATCH prediction low confidence ratio 증가
API prediction latency 증가
최근 pipeline check failure 발생
latest promoted model accuracy / f1_weighted 저하
미확인 firing alert 지속
평균 MTTA 증가
평균 MTTR 증가
```

Prometheus 설정은 `rule_files`로 alert rule 파일을 로드하고, firing/resolved alert를 Alertmanager로 전달합니다.

```yaml
rule_files:
  - /etc/prometheus/rules/*.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - "alertmanager:9093"
```

설정 검증:

```bash
make prometheus-check
```

Prometheus alert rule에는 Slack과 Dashboard에서 바로 운영 대응 문서로 이동할 수 있도록 annotation 링크를 포함합니다.

```yaml
annotations:
  summary: "..."
  description: "..."
  runbook_url: "http://localhost:8000/runbooks/jobskill_pipeline_check_failure.md"
  dashboard_url: "http://localhost:8501"
  prometheus_url: "http://localhost:9090/alerts"
```

대부분의 non-critical alert rule은 maintenance mode가 꺼져 있을 때만 firing되도록 아래 조건을 함께 사용합니다.

```promql
and on() jobskill_alert_maintenance_mode == 0
```

`JobSkillApiMetricsDown`은 FastAPI `/metrics` 자체가 scrape되지 않는 상황을 감지해야 하므로 maintenance mode 억제 대상에서 제외합니다.

`JobSkillApiNotReady`는 FastAPI 프로세스는 살아 있지만 DB, promoted model metadata, promoted model file 준비 상태가 실패한 상황을 감지합니다. 이 alert도 실제 serving 준비 상태 장애를 의미하므로 maintenance mode 억제 대상에서 제외합니다.

Alert별 runbook 매핑:

```text
JobSkillApiMetricsDown
→ /runbooks/jobskill_api_metrics_down.md

JobSkillApiNotReady
→ /runbooks/jobskill_api_not_ready.md

JobSkillApiHighLowConfidenceRatio
JobSkillBatchHighLowConfidenceRatio
→ /runbooks/jobskill_high_low_confidence_ratio.md

JobSkillApiHighLatency
→ /runbooks/jobskill_api_high_latency.md

JobSkillPipelineCheckFailure
→ /runbooks/jobskill_pipeline_check_failure.md

JobSkillPromotedModelLowAccuracy
JobSkillPromotedModelLowF1
→ /runbooks/jobskill_promoted_model_low_performance.md

JobSkillUnacknowledgedCurrentAlert
→ /runbooks/jobskill_unacknowledged_current_alert.md

JobSkillHighAverageMTTA
JobSkillHighAverageMTTR
→ /runbooks/jobskill_alert_response_slo_breach.md
```

Prometheus UI에서 alert rule 상태를 확인할 수 있습니다.

```text
http://localhost:9090/rules
http://localhost:9090/alerts
```


### 16-6-1. Prometheus Alert Rule Tests

`monitoring/prometheus/tests/jobskill_alert_rules.test.yml`

Prometheus alert rule이 의도한 조건에서 firing되는지 `promtool test rules`로 검증합니다.

검증 항목:

```text
API /metrics down alert
API not ready alert
API low confidence ratio alert
API low confidence 최소 요청 수 조건
maintenance mode 기반 alert 억제
BATCH low confidence ratio alert
API latency alert
pipeline check failure alert
promoted model accuracy / f1 저하 alert
unacknowledged current alert escalation
high average MTTA / MTTR escalation
```

실행:

```bash
make prometheus-rule-test
```

Prometheus 설정 검증과 함께 실행할 수 있습니다.

```bash
make prometheus-check
make prometheus-rule-test
```

테스트 파일은 Prometheus 서버가 rule file로 읽지 않도록 `monitoring/prometheus/rules/`가 아니라 `monitoring/prometheus/tests/` 아래에 둡니다.

```text
monitoring/prometheus/
├── rules/
│   └── jobskill_alert_rules.yml
└── tests/
    └── jobskill_alert_rules.test.yml
```

이 테스트는 실제 서비스를 띄우지 않고 synthetic time series를 사용해 alert rule expression과 `for` 조건을 검증합니다. 이를 통해 alert rule 수정 시 threshold, label, annotation, maintenance mode 조건이 깨지는 문제를 빠르게 확인할 수 있습니다.

### 16-7. Alertmanager Webhook

`monitoring/alertmanager/alertmanager.yml`  
`src/inference/api.py`

Prometheus alert rule에서 발생한 firing/resolved alert를 Alertmanager가 수신하고, FastAPI webhook endpoint와 Slack receiver로 전달합니다.

Alertmanager receiver:

```text
jobskill-webhook-and-slack
```

Webhook endpoint:

```text
POST /alertmanager/webhook
```

동작 흐름:

```text
Prometheus alert rule 평가
→ Alertmanager로 alert 전달
→ Alertmanager webhook receiver 실행
→ FastAPI /alertmanager/webhook 호출
→ PostgreSQL alert_events에 이벤트 이력 저장
→ PostgreSQL alert_current_states에 fingerprint 기준 현재 상태 upsert
→ Slack Incoming Webhook으로 alert 알림 전송
```

FastAPI webhook은 `send_resolved: true`로 구성해 firing/resolved 이벤트를 모두 DB에 저장합니다. Slack은 운영 알림 노이즈를 줄이기 위해 firing 중심으로 전송하도록 구성할 수 있습니다.

설정 검증:

```bash
make alertmanager-check
```

Alertmanager UI:

```text
http://localhost:9093
```

### 16-8. Alertmanager Slack Notification

`monitoring/alertmanager/alertmanager.yml`  
`.secrets/slack_webhook_url`

Alertmanager receiver는 FastAPI webhook 저장과 Slack 알림 전송을 동시에 수행합니다.

```text
Prometheus Alert Rule
→ Alertmanager
→ FastAPI webhook 저장
→ Slack notification 전송
→ Runbook / Grafana / Prometheus 링크 제공
```

Slack webhook URL은 secret이므로 Git에 포함하지 않습니다. 실제 URL은 로컬의 `.secrets/slack_webhook_url` 파일에만 저장하고, Docker Compose에서 read-only volume으로 Alertmanager 컨테이너에 mount합니다.

실제 secret 파일 생성:

```bash
mkdir -p .secrets
cp .secrets.example/slack_webhook_url.example .secrets/slack_webhook_url
vi .secrets/slack_webhook_url
chmod 644 .secrets/slack_webhook_url
```

예시 파일:

```text
.secrets.example/slack_webhook_url.example
```

예시 내용:

```text
https://hooks.slack.com/services/REPLACE/THIS/WITH_REAL_WEBHOOK_URL
```

`.secrets.example`은 Git에 포함할 수 있는 placeholder이고, `.secrets`는 실제 secret을 담는 로컬 전용 디렉터리입니다.

```text
.secrets.example/
└── slack_webhook_url.example   # Git에 포함 가능, 실제 URL 아님

.secrets/
└── slack_webhook_url           # Git 제외, 실제 Slack webhook URL 저장
```

`.gitignore`에는 아래 항목을 포함합니다.

```gitignore
.secrets/
```

Docker Compose mount 예시:

```yaml
volumes:
  - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
  - ./.secrets/slack_webhook_url:/etc/alertmanager/secrets/slack_webhook_url:ro
  - alertmanager-data:/alertmanager
```

Alertmanager Slack 설정 예시:

```yaml
receivers:
  - name: "jobskill-webhook-and-slack"
    webhook_configs:
      - url: "http://api:8000/alertmanager/webhook"
        send_resolved: true

    slack_configs:
      - api_url_file: "/etc/alertmanager/secrets/slack_webhook_url"
        send_resolved: false
        title: "[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}"
        text: |
          *Service:* {{ .CommonLabels.service }}
          *Severity:* {{ .CommonLabels.severity }}
          *Status:* {{ .Status }}

          {{ range .Alerts }}
          *Summary:* {{ .Annotations.summary }}
          *Description:* {{ .Annotations.description }}
          *Runbook:* <{{ .Annotations.runbook_url }}|Open runbook>
          *Dashboard:* <{{ .Annotations.dashboard_url }}|Open Grafana>
          *Prometheus:* <{{ .Annotations.prometheus_url }}|Open Prometheus>
          *Instance:* {{ .Labels.instance }}
          *Starts At:* {{ .StartsAt }}
          *Ends At:* {{ .EndsAt }}
          {{ end }}
```

> Slack Incoming Webhook은 생성 시 특정 채널에 고정되는 경우가 있으므로, 초기 테스트에서는 `channel:` override를 넣지 않고 webhook 기본 채널로 전송되도록 구성합니다.

> FastAPI webhook은 resolved 이벤트까지 저장하지만, Slack은 `send_resolved: false`로 두면 resolved 알림이 반복적으로 올라오는 노이즈를 줄일 수 있습니다.

Slack webhook 직접 테스트:

```bash
curl -X POST   -H "Content-Type: application/json"   --data '{"text":"JobSkill Slack webhook direct test"}'   "$(cat .secrets/slack_webhook_url)"
```

Alertmanager direct alert 테스트:

```bash
curl -X POST "http://localhost:9093/api/v2/alerts"   -H "Content-Type: application/json"   -d '[
    {
      "labels": {
        "alertname": "JobSkillSlackReceiverTest",
        "severity": "warning",
        "service": "slack-test",
        "instance": "manual"
      },
      "annotations": {
        "summary": "Slack receiver test alert",
        "description": "Testing Alertmanager Slack receiver.",
        "runbook_url": "http://localhost:8000/runbooks/jobskill_alertmanager_slack_notification.md",
        "dashboard_url": "http://localhost:3000",
        "prometheus_url": "http://localhost:9090/alerts"
      },
      "startsAt": "2026-07-10T00:00:00Z"
    }
  ]'
```

테스트 확인 흐름:

```bash
docker compose up -d --force-recreate alertmanager

curl -XPOST http://localhost:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  -d '[
    {
      "labels": {
        "alertname": "JobSkillTestAlert",
        "severity": "warning",
        "service": "jobskill-mlops",
        "source": "manual-test"
      },
      "annotations": {
        "summary": "JobSkill MLOps alert test",
        "description": "This is a manual Alertmanager notification test."
      },
      "startsAt": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
    }
  ]'

curl -s http://localhost:9093/api/v2/alerts | jq
```

이 테스트는 Prometheus rule firing을 기다리지 않고 Alertmanager receiver와 Slack notification 경로를 직접 검증하기 위한 절차입니다.

Slack 알림 예시:

<img src="docs/images/alert.png" width="900">

### 16-9. Alert Runbooks

`docs/runbooks/`  
`src/inference/api.py`

Alert 발생 시 단순 알림에서 끝나지 않고 원인 확인과 조치까지 이어지도록 alert별 runbook을 관리합니다.

Runbook 문서:

```text
docs/runbooks/jobskill_api_metrics_down.md
docs/runbooks/jobskill_api_not_ready.md
docs/runbooks/jobskill_high_low_confidence_ratio.md
docs/runbooks/jobskill_api_high_latency.md
docs/runbooks/jobskill_pipeline_check_failure.md
docs/runbooks/jobskill_promoted_model_low_performance.md
docs/runbooks/jobskill_alertmanager_slack_notification.md
docs/runbooks/jobskill_unacknowledged_current_alert.md
docs/runbooks/jobskill_alert_response_slo_breach.md
```

각 runbook은 아래 구조로 작성합니다.

```text
의미
영향
확인 명령어
DB 확인
주요 원인
조치
```

FastAPI는 runbook Markdown을 HTML로 렌더링해 브라우저에서 읽기 쉬운 문서로 제공합니다.

```text
http://localhost:8000/runbooks/jobskill_pipeline_check_failure.md
```

원본 Markdown은 `/raw` 경로에서 확인할 수 있습니다.

```text
http://localhost:8000/runbooks/jobskill_pipeline_check_failure.md/raw
```

Prometheus alert rule의 `runbook_url` annotation, Slack 알림 메시지, Streamlit Current Alerts/Alert History에서 동일한 runbook URL을 사용합니다.


### 16-10. Alert Events / Current Alert States

`alert_events`  
`alert_current_states`

Alertmanager webhook으로 수신한 alert 이벤트를 PostgreSQL에 저장합니다.

```text
alert_events
→ 모든 firing/resolved 이벤트를 append-only 형태로 저장

alert_current_states
→ Alertmanager fingerprint 기준 현재 상태만 upsert
```

이를 통해 단순히 알림을 전송하는 것에서 끝나지 않고, 어떤 alert가 언제 firing/resolved 되었는지 이력으로 추적하면서 현재 열려 있는 alert 상태도 별도로 확인할 수 있습니다.

확인 가능한 항목:

```text
alert_name
severity
service
status
fingerprint
summary
description
starts_at
ends_at
created_at / updated_at
```

DB 확인:

```sql
SELECT
    status,
    alert_name,
    severity,
    service,
    COUNT(*) AS cnt,
    MAX(created_at) AS latest_created_at
FROM alert_events
GROUP BY status, alert_name, severity, service
ORDER BY latest_created_at DESC;
```

```sql
SELECT
    status,
    alert_name,
    severity,
    service,
    COUNT(*) AS cnt,
    MAX(updated_at) AS latest_updated_at
FROM alert_current_states
GROUP BY status, alert_name, severity, service
ORDER BY latest_updated_at DESC;
```

Alert event와 current state는 FastAPI `/metrics`에서도 Prometheus 지표로 노출됩니다.

```text
jobskill_alert_events_total
jobskill_alert_current_states_total
```

### 16-11. Alert Acknowledgement / Response Metrics

`alert_acknowledgements`  
`src/dashboard/app.py`  
`src/monitoring/prometheus_metrics.py`

Streamlit Dashboard에서 firing alert를 선택하고 확인자와 조치 메모를 저장할 수 있습니다.

```text
Current Alerts
→ Acknowledge Alert
→ alert 선택
→ 확인자 / 조치 메모 입력
→ Save acknowledgement
```

저장된 acknowledgement는 `alert_acknowledgements` 테이블에 기록됩니다.

저장 항목:

```text
fingerprint
alert_name
severity
service
status
acknowledged_by
note
created_at
```

Alert History에서는 alert firing 시각, acknowledgement 저장 시각, resolved 시각을 비교해 MTTA와 MTTR을 계산합니다.

```text
MTTA = alert firing 시각부터 acknowledgement 저장까지 걸린 시간
MTTR = alert firing 시각부터 resolved 이벤트 수신까지 걸린 시간
```

FastAPI `/metrics`에서 아래 지표를 노출합니다.

```text
jobskill_alert_acknowledgements_total
jobskill_alert_avg_mtta_minutes
jobskill_alert_avg_mttr_minutes
jobskill_alert_unacknowledged_current_total
```

이를 통해 단순 alert 이력 저장을 넘어, alert 대응 속도와 미확인 alert 상태를 Prometheus/Grafana에서도 확인할 수 있습니다.

### 16-12. Alert Response Escalation

`monitoring/prometheus/rules/jobskill_alert_rules.yml`

Alert response metrics를 기반으로 알림 대응 품질 자체를 다시 alert rule로 감지합니다.

추가 alert:

```text
JobSkillUnacknowledgedCurrentAlert
→ firing 상태인데 acknowledgement가 없는 alert가 일정 시간 이상 남아 있을 때 발생

JobSkillHighAverageMTTA
→ 평균 acknowledgement 시간이 기준보다 높을 때 발생

JobSkillHighAverageMTTR
→ 평균 resolved 시간이 기준보다 높을 때 발생
```

이 alert들은 운영자가 alert를 확인하지 않았거나, alert 해소가 늦어지는 상황을 감지하기 위한 escalation rule입니다.

관련 runbook:

```text
docs/runbooks/jobskill_unacknowledged_current_alert.md
docs/runbooks/jobskill_alert_response_slo_breach.md
```

### 16-13. Alert Maintenance Mode

`alert_settings`  
`src/dashboard/app.py`  
`src/monitoring/prometheus_metrics.py`

테스트나 점검 중 불필요한 Slack 알림과 alert history 오염을 줄이기 위해 runtime maintenance mode를 제공합니다.

상태 저장 위치:

```text
alert_settings.setting_key = maintenance_mode
alert_settings.setting_value = true / false
```

Streamlit Dashboard의 Current Alerts 탭에서 maintenance mode를 ON/OFF할 수 있습니다.

```text
Current Alerts
→ Alert Maintenance Mode
→ Enable maintenance mode
→ Disable maintenance mode
```

FastAPI `/metrics`는 DB의 maintenance mode 값을 읽어 아래 지표로 노출합니다.

```text
jobskill_alert_maintenance_mode 0
jobskill_alert_maintenance_mode 1
```

Prometheus alert rule은 이 값이 0일 때만 non-critical alert가 발생하도록 구성합니다.

```promql
and on() jobskill_alert_maintenance_mode == 0
```

`JobSkillApiMetricsDown`은 `/metrics` scrape 실패를 감지해야 하므로 maintenance mode 억제 대상에서 제외합니다.


### 16-14. Alert Silence / Snooze

`src/dashboard/app.py`  
`alert_silence_actions`  
`monitoring/alertmanager/alertmanager.yml`

Streamlit Current Alerts 화면에서 특정 alert를 선택해 Alertmanager silence를 생성할 수 있습니다.

```text
Current Alerts
→ Silence Alert
→ alert 선택
→ 30 minutes / 1 hour / 2 hours / Custom
→ 처리자 / 사유 입력
→ Create silence
```

이 기능은 전체 maintenance mode를 켜지 않고도 특정 alert만 일정 시간 mute할 때 사용합니다.

```text
Maintenance Mode
→ 테스트/점검 중 non-critical alert rule 전체 억제

Alert Silence / Snooze
→ 특정 alertname / service / severity 조합만 Alertmanager 단계에서 notification 억제
```

Silence 생성 시 Alertmanager `/api/v2/silences` API를 호출하고, 생성 이력은 PostgreSQL에 저장합니다.

또한 Active Alertmanager silence 목록을 Dashboard에서 조회하고, 잘못 생성했거나 테스트가 끝난 silence를 수동으로 expire 처리할 수 있습니다.

```text
Current Alerts
→ Manage Alertmanager Silences
→ active silence 선택
→ 해제 사유 입력
→ Expire selected silence
```

silence 생성과 해제 이력은 `action_type`으로 구분합니다.

```text
action_type = CREATE
action_type = EXPIRE
```

저장 테이블:

```text
alert_silence_actions
```

저장 항목:

```text
silence_id
fingerprint
alert_name
severity
service
instance
duration_minutes
starts_at
ends_at
created_by
reason
created_at
```

Alertmanager silence 확인:

```bash
curl -fsS http://localhost:9093/api/v2/silences | jq
```

DB 이력 확인:

```sql
SELECT
    id,
    silence_id,
    alert_name,
    severity,
    service,
    duration_minutes,
    created_by,
    reason,
    created_at
FROM alert_silence_actions
ORDER BY id DESC
LIMIT 10;
```

### 16-15. Incident Response Report

`src/reporting/generate_incident_response_report.py`  
`reports/latest_incident_response_report.md`  
`src/dashboard/app.py`

Alert 대응 이력과 운영 상태를 Markdown 리포트로 생성합니다.

생성 파일:

```text
reports/latest_incident_response_report.md
```

리포트 포함 내용:

```text
current firing alerts
current alert summary
recent alert events
recent acknowledgements
recent silence actions
alert response metrics
MTTA / MTTR detail
recent pipeline failures
API quality summary
recommended next actions
```

실행:

```bash
make incident-report
```

또는 직접 실행:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/reporting/generate_incident_response_report.py"
```

Streamlit Dashboard의 `Incident Report` 탭에서는 아래 기능을 제공합니다.

```text
Generate incident report
Report Preview
Download Markdown report
```

이 리포트는 단순 alert 목록이 아니라, alert 발생 이후 운영자가 어떤 확인, silence, 대응 메모를 남겼는지와 MTTA/MTTR이 어땠는지를 한 번에 정리하는 incident response summary 역할을 합니다.


### 16-16. Incident Response Drill

`scripts/run_incident_drill.py`

Alert 운영 흐름을 시연하고 검증하기 위한 synthetic incident scenario를 생성합니다.

실행:

```bash
make incident-drill
```

동작 흐름:

```text
기존 drill alert row 정리
→ synthetic firing alert를 FastAPI webhook에 전송
→ alert_events / alert_current_states 저장
→ acknowledgement 이력 저장
→ Alertmanager silence 생성
→ alert_silence_actions 저장
→ synthetic resolved alert를 FastAPI webhook에 전송
→ incident response report 생성
```

이 기능은 실제 장애를 기다리지 않고도 alert 발생, 확인, silence, resolved, report 생성까지의 운영 대응 흐름을 한 번에 재현하기 위한 데모/검증 도구입니다.

생성되는 데이터:

```text
alert_events
alert_current_states
alert_acknowledgements
alert_silence_actions
reports/latest_incident_response_report.md
```

컨테이너 내부 실행 시에는 Docker Compose service name 기준 URL을 사용합니다.

```text
API_URL=http://api:8000
ALERTMANAGER_URL=http://alertmanager:9093
```

### 16-17. Alert Workflow Smoke Check

`scripts/check_alert_workflow.sh`  
`.github/workflows/smoke.yml`  
`Makefile`

Alerting / Incident 대응 기능이 정상 동작하는지 검증하는 전용 smoke check입니다.

검증 항목:

```text
FastAPI /metrics
API readiness metrics
Prometheus query API
Alertmanager status
Runbook endpoint
alert 관련 PostgreSQL table
alert_settings maintenance_mode row
jobskill_api_ready / jobskill_api_database_ready / jobskill_api_promoted_model_ready / jobskill_api_promoted_model_file_exists metric
FastAPI /alertmanager/webhook synthetic alert 저장
alert_events 저장 여부
alert_current_states upsert 여부
```

실행:

```bash
make alert-workflow-check
```

또는 직접 실행:

```bash
bash scripts/check_alert_workflow.sh
```

GitHub Actions Smoke Check에서는 기본 `smoke_check.sh` 실행 후 `check_alert_workflow.sh`를 추가로 실행합니다.

```text
smoke_check.sh
→ API / Dashboard / Prometheus / Alertmanager / Grafana 기본 상태 검증

check_alert_workflow.sh
→ alert 운영 기능 전용 검증
```

이 검증은 synthetic Alertmanager payload를 FastAPI webhook에 직접 전송해 `alert_events`와 `alert_current_states` 저장 경로가 정상 동작하는지 확인합니다. 테스트 후 생성된 smoke alert row는 자동 삭제해 Alert History가 불필요하게 오염되지 않도록 합니다.



### 16-18. Runbook Coverage Check

`scripts/check_runbook_coverage.py`  
`Makefile`

Prometheus alert rule에 정의된 모든 alert가 대응 runbook을 가지고 있는지 검증합니다.

실행:

```bash
make runbook-check
```

검증 항목:

```text
모든 alert rule에 runbook_url annotation 존재 여부
runbook_url이 /runbooks/*.md 형식인지 확인
docs/runbooks/*.md 파일 존재 여부 확인
선택적으로 FastAPI /runbooks/{filename} endpoint 응답 확인
```

API endpoint까지 함께 검증하려면 아래처럼 실행합니다.

```bash
RUNBOOK_CHECK_API=true API_URL=http://localhost:8000 python scripts/check_runbook_coverage.py
```

이 검증은 alert rule을 추가하거나 수정할 때 운영 대응 문서가 누락되는 문제를 방지하기 위한 문서화 검증입니다.

### 16-19. Metrics Contract Check

`monitoring/metrics_contract.yml`  
`scripts/check_metrics_contract.py`  
`Makefile`

FastAPI `/metrics`가 운영상 필요한 Prometheus metric을 안정적으로 노출하는지 검증합니다.

실행:

```bash
make metrics-contract-check
```

검증 기준은 `monitoring/metrics_contract.yml`에 정의합니다.

```text
API readiness metrics
model prediction metrics
API request metrics
pipeline check metrics
model registry metrics
alert event metrics
alert response metrics
alert control metrics
```

이 검증은 metric 값이 0인지 1인지를 판단하는 것이 아니라, Prometheus alert rule, Grafana dashboard, smoke check에서 사용하는 필수 metric 이름이 `/metrics`에 실제로 노출되는지 확인합니다.

예를 들어 실패한 pipeline check가 없더라도 운영상 필요한 metric은 0 값으로 노출되어야 합니다.

```text
jobskill_pipeline_recent_failed_checks_total{check_type="none",status="PASS"} 0
```

또한 model registry 관련 metric은 실제 exporter에서 노출하는 이름인 `jobskill_model_registry_records_total`을 기준으로 관리합니다.

### 16-20. Alert Rule Metric Dependency Check

`scripts/check_alert_rule_metric_dependencies.py`  
`monitoring/metrics_contract.yml`  
`Makefile`

Prometheus alert rule이 참조하는 metric이 `metrics_contract.yml`에 등록되어 있고, 실제 FastAPI `/metrics`에 노출되는지 검증합니다.

실행:

```bash
make alert-rule-metric-check
```

검증 항목:

```text
alert rule expr에서 metric 이름 추출
Prometheus 기본 metric up 예외 처리
metrics_contract.yml 등록 여부 확인
FastAPI /metrics 노출 여부 확인
```

이 검증은 alert rule이 존재하지 않는 metric을 참조해 조용히 firing되지 않는 문제를 방지하기 위한 운영 검증입니다.

서비스를 띄우지 않는 CI 정적 검증에서는 `/metrics` endpoint 확인을 생략하고, alert rule이 metrics contract에 등록된 metric만 참조하는지 확인합니다.

```bash
python scripts/check_alert_rule_metric_dependencies.py --skip-metrics-endpoint
```

### 16-21. Static Ops Validation Check

`scripts/check_static_ops_validation.sh`  
`.github/workflows/smoke.yml`  
`Makefile`

서비스를 기동하지 않고 운영 관련 설정과 문서화 상태를 검증합니다.

실행:

```bash
make ops-static-check
```

검증 항목:

```text
주요 Python 파일 문법 확인
Prometheus config / alert rule 문법 확인
Prometheus alert rule unit test
Alertmanager config 확인
Runbook coverage check
Alert rule metric dependency check
```

`ops-static-check`는 FastAPI `/metrics` endpoint를 호출하지 않고, alert rule이 `metrics_contract.yml`에 등록된 metric만 참조하는지 확인합니다. 따라서 GitHub Actions에서 Docker Compose 서비스를 모두 띄우기 전에 빠르게 실행할 수 있습니다.

```text
make ops-static-check
→ 서비스 기동 전 정적 검증

make ops-check
→ 서비스 기동 후 동적 운영 검증
```

GitHub Actions Smoke Check에서는 Docker Compose 서비스 기동 전에 static ops validation을 먼저 실행해 Prometheus rule, Alertmanager config, runbook, metric dependency 문제가 있을 경우 빠르게 실패하도록 구성합니다.

### 16-22. Ops Validation Check

`scripts/check_ops_validation.sh`  
`Makefile`

로컬 운영 검증을 한 번에 실행하기 위한 통합 검증 명령어입니다.

실행:

```bash
make ops-check
```

검증 항목:

```text
주요 Python 파일 문법 확인
Prometheus config / alert rule 검증
Prometheus alert rule unit test
Alertmanager config 검증
Runbook coverage check
Metrics contract check
Alert rule metric dependency check
FastAPI /health 확인
FastAPI /ready 확인
FastAPI /metrics 확인
Runbook API coverage check
Data contract check
Model lifecycle integrity check
service smoke check 실행
alert workflow smoke check 실행
```

이 명령은 Prometheus, Alertmanager, FastAPI, runbook, alert workflow가 함께 정상 동작하는지 확인하기 위한 로컬 운영 검증용 command입니다.

실행 전 주요 서비스가 떠 있어야 합니다.

```bash
docker compose up -d postgres api alertmanager prometheus grafana dashboard airflow-scheduler
make create-tables
make ops-check
```

### 17. Airflow DAG

`dags/jobskill_pipeline_dag.py`

전체 파이프라인을 아래 순서로 실행합니다.

```text
prepare_raw_sources
    ↓
generate_sample_jobs
    ↓
load_raw_jobs
    ↓
crawl_remoteok_jobs
    ↓
preprocess_jobs
    ↓
check_data_contract
    ↓
check_training_data
    ↓
train_model
    ↓
check_model_performance
    ↓
promote_model
    ↓
batch_inference
    ↓
check_prediction_quality
    ↓
check_prediction_drift
    ↓
generate_pipeline_report
    ↓
notify_pipeline_status
```

DAG 이름:

```text
jobskill_mlops_pipeline
```

초기 DAG는 BashOperator로 각 Python 스크립트를 실행하는 방식이었지만, 현재는 PythonOperator 기반으로 개선했습니다.

```text
기존:
BashOperator
→ python src/xxx.py

개선:
PythonOperator
→ 각 모듈의 main() 함수 직접 호출
```

마지막 단계에서는 `notify_pipeline_status` task를 통해 모델/검증/예측/API 상태 요약 메시지를 생성합니다. Slack webhook이 설정되어 있지 않으면 콘솔 출력만 수행합니다.

<img src="docs/images/Airflow%20DAG%20success.png" width="900">

### 18. 테스트 코드

`tests/unit/`

주요 전처리/예측 품질 로직에 대해 pytest 기반 단위 테스트를 추가했습니다.

테스트 대상:

```text
직무 라벨링 규칙
confidence level 계산
low confidence 판단
top-k prediction 생성
```

실행:

```bash
pytest
```

컨테이너 내부 실행:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && pytest"
```


### 18-1. GitHub Actions / Ruff

`.github/workflows/pytest.yml`  
`pyproject.toml`  
`requirements-dev.txt`

push 또는 pull request 발생 시 GitHub Actions에서 단위 테스트와 코드 품질 검사를 자동 실행합니다.

실행 조건:

```text
push to main
push to feature/**
pull request to main
```

실행 항목:

```text
ruff check src dags scripts tests
pytest
```

현재 Ruff는 초기 도입 단계이므로 전체 스타일 규칙이 아니라, 런타임 오류로 이어질 가능성이 높은 기본 규칙만 검사합니다.

활성화한 Ruff 규칙:

```text
E9  : syntax error
F63 : invalid comparison / usage
F7  : control-flow related issue
F82 : undefined name
```

## PostgreSQL 테이블

현재 사용하는 주요 테이블은 아래와 같습니다.

```text
raw_job_posts
cleaned_job_posts
job_post_skills
model_predictions
api_prediction_logs
pipeline_check_results
model_registry
model_promotion_archives
model_rollback_actions
alert_events
alert_current_states
alert_acknowledgements
alert_settings
alert_silence_actions
```

역할:

```text
raw_job_posts
- 원천 채용공고 저장
- sample / remoteok 등 source 구분
- external_id / source_job_id 기반 외부 데이터 추적

cleaned_job_posts
- 정제된 채용공고 저장
- 직무 라벨 저장
- 모델 입력용 text_for_model 저장

job_post_skills
- 채용공고별 추출된 기술스택 저장

model_predictions
- FastAPI 또는 batch inference 예측 결과 저장
- prediction_source로 API / BATCH 구분
- 예측에 사용된 모델 lineage 저장
- confidence / top-k prediction 저장

api_prediction_logs
- FastAPI 요청/응답/실패/latency 로그 저장
- model_predictions.prediction_id와 연결
- API 운영 관점의 request/response 추적

pipeline_check_results
- 데이터 계약 체크 결과 저장
- 데이터 품질 체크 결과 저장
- 모델 성능 체크 결과 저장
- 예측 품질 체크 결과 저장
- 예측 분포 drift 체크 결과 저장

model_registry
- MLflow run 기반 모델 승격 결과 저장
- promoted / rejected / rolled_back 모델 이력 관리

model_promotion_archives
- 현재 promoted model artifact를 archive 디렉터리에 스냅샷으로 저장한 이력 관리
- model_registry_id / archived_model_path / accuracy / f1_weighted / created_by 저장
- rollback 대상 artifact를 추적하는 기준 테이블

model_rollback_actions
- archived model을 best model path로 복원한 rollback 실행 이력 저장
- rollback 대상 archive, 이전 promoted model, backup path, 복원 path, 처리자, 사유 저장
- 모델 품질 이슈 발생 시 복구 조치 audit trail로 사용

alert_events
- Alertmanager webhook으로 수신한 firing/resolved alert 이벤트 이력 저장
- alert_name / severity / service / status 기준 alert history 추적
- labels / annotations / raw_payload를 JSONB로 저장

alert_current_states
- Alertmanager fingerprint 기준 현재 alert 상태 저장
- 동일 alert 반복 수신 시 upsert로 현재 상태 갱신
- 현재 firing/resolved 상태를 Streamlit Dashboard와 Prometheus metrics에서 조회

alert_acknowledgements
- 운영자가 Streamlit Dashboard에서 저장한 alert 확인 이력 저장
- alert fingerprint / alert name / severity / service / status와 확인자, 조치 메모 저장
- MTTA 계산과 미확인 alert 판단에 사용

alert_settings
- alert maintenance mode 같은 runtime alert 설정 저장
- Dashboard에서 ON/OFF한 값을 FastAPI `/metrics`가 읽어 Prometheus에 노출
- non-critical alert rule 억제 조건에 사용

alert_silence_actions
- Streamlit Dashboard에서 생성한 Alertmanager silence 이력 저장
- silence_id / alert_name / service / severity / duration / 처리자 / 사유 저장
- 특정 alert를 일정 시간 mute한 운영 대응 이력 추적
```

FK 관계:

```text
raw_job_posts
    ↑
    └── cleaned_job_posts.raw_id

cleaned_job_posts
    ↑
    ├── job_post_skills.job_post_id
    └── model_predictions.job_post_id

model_registry
    ↑
    ├── model_predictions.model_registry_id
    ├── model_promotion_archives.model_registry_id
    └── model_rollback_actions.target_model_registry_id / previous_model_registry_id

model_predictions
    ↑
    └── api_prediction_logs.prediction_id

Alertmanager Webhook
    ├── alert_events
    └── alert_current_states

Streamlit Dashboard
    ├── alert_acknowledgements
    ├── alert_settings
    └── alert_silence_actions

Model Lifecycle Operations
    ├── model_promotion_archives
    └── model_rollback_actions
```

<img src="docs/images/postgresql.png" width="900">

## 환경 변수

`.env.example`을 복사해서 `.env`를 생성합니다.

```bash
cp .env.example .env
```

예시:

```env
DB_HOST=postgres
DB_PORT=5432
DB_NAME=jobskill
DB_USER=jobskill
DB_PASSWORD=jobskill

AIRFLOW_DB_HOST=postgres
AIRFLOW_DB_PORT=5432
AIRFLOW_DB_NAME=airflow
AIRFLOW_DB_USER=airflow
AIRFLOW_DB_PASSWORD=airflow

MLFLOW_DB_NAME=mlflow
MLFLOW_TRACKING_URI=postgresql+psycopg2://jobskill:jobskill@postgres:5432/mlflow
MLFLOW_ARTIFACT_ROOT=/opt/airflow/project/mlartifacts
MLFLOW_EXPERIMENT_NAME=jobskill-classifier

MODEL_NAME=job_classifier
MODEL_PATH=models/job_classifier.pkl
BEST_MODEL_PATH=models/best/job_classifier.pkl
MODEL_ARCHIVE_DIR=models/promoted_archive
MODEL_ARCHIVE_CREATED_BY=local-user
MODEL_ARCHIVE_REASON=Manual promoted model archive before rollback feature.
MODEL_ROLLBACK_BACKUP_DIR=models/rollback_backup
MODEL_ROLLBACK_ARCHIVE_ID=
MODEL_ROLLBACK_DRY_RUN=true
MODEL_ROLLBACK_CREATED_BY=local-user
MODEL_ROLLBACK_REASON=Manual rollback to archived promoted model.

DATA_CONTRACT_PATH=config/data_contract.json

AIRFLOW_JWT_SECRET=change_me
AIRFLOW_API_SECRET_KEY=change_me
AIRFLOW_FERNET_KEY=change_me

MIN_TRAINING_ROWS=50
MIN_CATEGORY_COUNT=2
MAX_UNKNOWN_RATIO=0.5
MIN_SAMPLES_PER_CLASS=2
TEST_SIZE=0.3

MIN_MODEL_ACCURACY=0.7
MIN_MODEL_F1_WEIGHTED=0.7
MIN_CLASS_F1=0.70
MIN_CLASS_RECALL=0.60
MIN_CLASS_SUPPORT=1

LOW_CONFIDENCE_THRESHOLD=0.6
PREDICTION_TOP_K=3
MIN_AVG_PREDICTION_CONFIDENCE=0.6
MAX_LOW_CONFIDENCE_RATIO=0.4
MIN_PREDICTION_ROWS=1

MAX_PREDICTION_DISTRIBUTION_PSI=0.25
MIN_DRIFT_CHECK_ROWS=1

CLEANUP_DRY_RUN=true
API_LOG_RETENTION_DAYS=30
API_PREDICTION_RETENTION_DAYS=30
PIPELINE_CHECK_RETENTION_DAYS=90

ALERT_ENABLED=false
ALERT_ONLY_ON_FAILURE=false
SLACK_WEBHOOK_URL=
ALERT_MAINTENANCE_MODE=false
ALERTMANAGER_URL=http://alertmanager:9093
ALERT_SILENCE_DEFAULT_MINUTES=30

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

REMOTEOK_API_URL=https://remoteok.com/api
REMOTEOK_CRAWL_LIMIT=50
REMOTEOK_SCAN_LIMIT=1000
REMOTEOK_FILTER_ENABLED=true
REMOTEOK_MIN_RELEVANCE_SCORE=2
REMOTEOK_MAX_RETRIES=3
REMOTEOK_RETRY_SLEEP_SECONDS=3
REMOTEOK_REQUEST_TIMEOUT_SECONDS=30
REMOTEOK_FALLBACK_TO_EXISTING_RAW=true
REMOTEOK_MIN_FETCHED_JOBS=1

DATA_SOURCE_MODE=mixed
```

로컬 Python에서 직접 실행할 경우에는 `DB_HOST=localhost`로 변경합니다.

```env
DB_HOST=localhost
```

Docker Compose 내부에서 실행할 경우에는 `DB_HOST=postgres`를 사용합니다.

```env
DB_HOST=postgres
```

Airflow metadata DB는 프로젝트 애플리케이션 DB와 분리해서 관리합니다. `DB_*`는 FastAPI, Streamlit Dashboard, pipeline script가 사용하는 `jobskill` DB 접속 정보이고, `AIRFLOW_DB_*`는 Airflow apiserver / scheduler / dag-processor / triggerer가 사용하는 `airflow` metadata DB 접속 정보입니다.

```text
DB_*         → jobskill application DB
AIRFLOW_DB_* → airflow metadata DB
MLFLOW_*     → mlflow backend / artifact store
```

Docker Compose에서 Airflow connection string은 아래 형태로 해석되어야 합니다.

```text
postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
```

`DATA_CONTRACT_PATH`는 data contract 정의 파일 경로입니다. Docker Compose에서는 `./config:/opt/airflow/project/config:ro`로 mount해 Airflow 컨테이너에서 `config/data_contract.json`을 읽습니다.

`MODEL_ARCHIVE_DIR`은 promoted model archive 파일을 저장할 디렉터리이고, `MODEL_ROLLBACK_BACKUP_DIR`은 rollback 수행 전 현재 best model을 백업하는 디렉터리입니다. `MODEL_ROLLBACK_DRY_RUN=true`가 기본값이므로 rollback은 먼저 plan만 확인하고, 실제 rollback은 `MODEL_ROLLBACK_ARCHIVE_ID=<archive_id>`와 `MODEL_ROLLBACK_DRY_RUN=false`가 함께 지정된 경우에만 수행합니다.

`ALERT_MAINTENANCE_MODE`는 `alert_settings` 테이블이 없거나 초기화되지 않은 경우에 사용하는 fallback 값입니다. 정상 운영 중에는 Streamlit Dashboard에서 변경한 `alert_settings.maintenance_mode` 값이 우선 사용됩니다. `ALERTMANAGER_URL`은 Dashboard 컨테이너가 Alertmanager Silence API를 호출할 때 사용하고, `ALERT_SILENCE_DEFAULT_MINUTES`는 사용자 지정 silence 기본 시간을 지정합니다.

## 보안 및 Secret 관리

이 프로젝트는 포트폴리오 공개 저장소를 전제로 하므로, 실제 secret 값은 Git에 포함하지 않습니다.

Airflow 3.x 실행에 필요한 JWT secret, API secret, Fernet key는 `.env` 파일에서만 관리하고, `docker-compose.yml`에서는 환경변수 참조 방식으로 사용합니다.

```yaml
AIRFLOW__API_AUTH__JWT_SECRET: ${AIRFLOW_JWT_SECRET}
AIRFLOW__API__SECRET_KEY: ${AIRFLOW_API_SECRET_KEY}
AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
```

`.env.example`에는 실제 값이 아니라 placeholder만 작성합니다.

```env
AIRFLOW_JWT_SECRET=change_me
AIRFLOW_API_SECRET_KEY=change_me
AIRFLOW_FERNET_KEY=change_me
```

Secret 값은 아래와 같이 생성할 수 있습니다.

```bash
python - <<'PY'
from cryptography.fernet import Fernet
import secrets

print("AIRFLOW_JWT_SECRET=" + secrets.token_urlsafe(64))
print("AIRFLOW_API_SECRET_KEY=" + secrets.token_urlsafe(64))
print("AIRFLOW_FERNET_KEY=" + Fernet.generate_key().decode())
PY
```

`.env`, Airflow 로그인 파일, 실행 로그, 모델 artifact, Slack Webhook URL 등은 Git에 포함하지 않습니다.

```gitignore
.env
.env.*
!.env.example
simple_auth_manager_passwords.json
airflow_logs/
models/
mlartifacts/
.secrets/
```

Alertmanager Slack 알림용 webhook URL은 `.env`가 아니라 별도 파일로 관리합니다. 실제 secret 파일은 Git에 올리지 않고, Git에는 예시 파일만 포함합니다.

```text
.secrets.example/slack_webhook_url.example
→ Git에 포함 가능한 placeholder

.secrets/slack_webhook_url
→ Git 제외, 실제 Slack Incoming Webhook URL 저장
```

로컬 설정 예시:

```bash
mkdir -p .secrets
cp .secrets.example/slack_webhook_url.example .secrets/slack_webhook_url
vi .secrets/slack_webhook_url
chmod 644 .secrets/slack_webhook_url
```

`chmod 644`를 사용하는 이유는 Alertmanager 컨테이너가 bind mount된 secret 파일을 읽어야 하기 때문입니다. Git에는 `.secrets/`가 제외되므로 실제 webhook URL은 저장소에 포함되지 않습니다.

개발 중 README와 Compose 설정에 로컬 개발용 secret 값이 포함된 이력이 있었기 때문에, 공개 저장소 정리 과정에서 `git-filter-repo`를 사용해 Git history에서도 해당 값을 제거했습니다.

```bash
git filter-repo --replace-text replacements.txt --force
```

History rewrite 이후에는 원격 저장소에 force push가 필요합니다.

```bash
git push origin --force --all
git push origin --force --tags
```

이미 Git에 노출된 secret은 폐기하고 새 secret을 생성해 `.env`에 반영했습니다.

## Airflow 3.x 설정 주의사항

Airflow 3.x에서는 scheduler가 task 실행 상태를 `airflow-apiserver`의 execution API에 전달합니다.

따라서 Docker Compose 환경에서는 아래 설정이 필요합니다.

```yaml
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-apiserver:8080/execution/
```

이 값은 컨테이너 내부 통신 기준입니다.  
따라서 호스트 포트를 `8081:8080`으로 변경하더라도 execution API URL은 `8080`을 유지해야 합니다.

```text
브라우저 접속       : http://localhost:8081
컨테이너 내부 통신 : http://airflow-apiserver:8080/execution/
```

또한 scheduler, apiserver, dag-processor, triggerer 간 JWT secret 값이 다르면 아래 오류가 발생할 수 있습니다.

```text
Invalid auth token: Signature verification failed
```

이를 방지하기 위해 Airflow 공통 환경변수에 secret 값을 고정합니다.  
단, 실제 secret 값은 Git에 올리지 않고 `.env`에서만 관리합니다.

```yaml
AIRFLOW__API_AUTH__JWT_SECRET: ${AIRFLOW_JWT_SECRET}
AIRFLOW__API__SECRET_KEY: ${AIRFLOW_API_SECRET_KEY}
AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
```

Airflow 설정 반영 여부는 아래 명령으로 확인합니다.

```bash
docker compose exec airflow-scheduler airflow config get-value api_auth jwt_secret
docker compose exec airflow-apiserver airflow config get-value api_auth jwt_secret

docker compose exec airflow-scheduler airflow config get-value api secret_key
docker compose exec airflow-apiserver airflow config get-value api secret_key

docker compose exec airflow-scheduler airflow config get-value core execution_api_server_url
```

정상 조건:

```text
scheduler jwt_secret == apiserver jwt_secret
scheduler api_secret == apiserver api_secret
execution_api_server_url == http://airflow-apiserver:8080/execution/
```

## 실행 방법

### 1. 필요한 디렉터리 생성

```bash
mkdir -p config data/raw data/processed models/best models/promoted_archive models/rollback_backup mlartifacts airflow_logs reports docs/images
```

권한 설정:

```bash
sudo chown -R 50000:0 data models mlartifacts airflow_logs reports
sudo chmod -R g+rwX data models mlartifacts airflow_logs reports
```

### 2. Airflow 이미지 빌드

```bash
docker compose build airflow-image
```

### 3. API 이미지 빌드

API 이미지는 serving에 필요한 최소 패키지를 담은 `requirements-api.txt`를 사용합니다.  
전체 학습/개발용 패키지를 담은 `requirements.txt`를 그대로 설치하지 않아 API 이미지 빌드 시간을 줄입니다.

```bash
docker compose build api
```

### 4. PostgreSQL init SQL 확인

PostgreSQL 초기화는 `docker/postgres/init/01-init-databases.sql` 하나에서 관리합니다.

```text
docker/postgres/init/
└── 01-init-databases.sql
```

이 init SQL은 아래 항목을 생성하거나 정리합니다.

```text
airflow role
airflow metadata DB
mlflow backend DB
jobskill / airflow / mlflow DB owner
DB privilege
```

초기화 SQL이 여러 파일로 나뉘어 있고, 둘 이상의 파일이 `airflow` DB를 생성하면 `database "airflow" already exists` 오류가 발생할 수 있습니다. 로컬 초기화 기준으로는 `01-init-databases.sql` 하나만 유지합니다.

### 5. PostgreSQL 실행

```bash
docker compose up -d postgres
```

DB 생성 확인:

```bash
docker compose exec postgres psql -U jobskill -d postgres -c "
SELECT datname
FROM pg_database
ORDER BY datname;
"
```

아래 DB가 보여야 합니다.

```text
airflow
jobskill
mlflow
```

Airflow metadata DB 접속 확인:

```bash
docker compose exec postgres psql \
  "postgresql://airflow:airflow@localhost:5432/airflow" \
  -c "SELECT current_user, current_database();"
```

### 6. 프로젝트 테이블 생성

```bash
docker exec -i jobskill-postgres psql -U jobskill -d jobskill < sql/create_tables.sql
```

### 7. Airflow 메타DB migrate

```bash
docker compose run --rm airflow-init
```

확인:

```bash
docker compose exec airflow-apiserver bash -lc 'airflow db check'
docker compose exec airflow-scheduler bash -lc 'airflow dags list-import-errors'
```

### 8. 전체 서비스 실행

```bash
docker compose up -d --no-build --force-recreate \
  airflow-apiserver \
  airflow-scheduler \
  airflow-dag-processor \
  airflow-triggerer \
  mlflow \
  api \
  dashboard \
  alertmanager \
  prometheus \
  grafana
```

### 9. 컨테이너 상태 확인

```bash
docker compose ps
```

### 10. 로컬 초기화 / 복구 절차

로컬 개발 중 Docker volume이나 DB role password가 꼬인 경우에는 아래 순서로 초기화합니다. 이 명령은 PostgreSQL volume과 로컬 실행 산출물을 삭제하므로, 필요한 데이터는 먼저 백업합니다.

```bash
docker compose down -v --remove-orphans

sudo rm -rf data models mlartifacts reports airflow_logs

mkdir -p \
  data \
  models/best \
  models/promoted_archive \
  models/rollback_backup \
  mlartifacts \
  reports/model_cards \
  airflow_logs \
  .secrets

touch .secrets/slack_webhook_url

sudo chown -R "$USER":0 data models mlartifacts reports airflow_logs
sudo chmod -R u+rwX,g+rwX data models mlartifacts reports airflow_logs
```

컨테이너의 Airflow UID가 `50000`인 경우 ACL도 함께 부여합니다.

```bash
sudo setfacl -R -m u:50000:rwX,u:$(id -u):rwX data models mlartifacts reports airflow_logs
sudo setfacl -R -d -m u:50000:rwX,u:$(id -u):rwX data models mlartifacts reports airflow_logs
```

이후 다시 실행합니다.

```bash
docker compose build --no-cache airflow-image api
docker compose up -d postgres
docker compose run --rm airflow-init
docker compose up -d airflow-apiserver airflow-scheduler airflow-dag-processor airflow-triggerer
docker compose up -d mlflow api dashboard alertmanager prometheus grafana
```

## Makefile 명령어

자주 사용하는 Docker Compose, Airflow, 테스트, 리포트, smoke check 명령어는 `Makefile`로 표준화했습니다.

명령어 목록 확인:

```bash
make help
```

주요 명령어:

```bash
make build
make up
make ps
make dag-errors
make dag-tasks
make dag-trigger
make report
make incident-report
make incident-drill
make model-archive
make model-rollback-plan
make model-rollback
make model-lifecycle-check
make data-contract-check
make model-class-performance-check
make model-card
make dashboard
make metrics
make prometheus
make prometheus-check
make prometheus-rule-test
make alertmanager
make alertmanager-logs
make alertmanager-check
make grafana
make grafana-logs
make api-sample
make notify
make drift-check
make cleanup
make smoke
make alert-workflow-check
make runbook-check
make metrics-contract-check
make alert-rule-metric-check
make ops-static-check
make ops-check
make ci
```

대표 실행 흐름:

```bash
make build
make up
make dag-trigger
make smoke
make dashboard
```

`make ci`는 로컬에서 Ruff와 pytest를 함께 실행합니다.

```bash
make ci
```

`make smoke`는 로컬 Docker Compose 서비스의 기본 기동성과 주요 엔드포인트, API 샘플 예측 요청, API 로그 저장 여부를 확인합니다.

```bash
make smoke
```


`make alert-workflow-check`는 alert 운영 기능 전용 smoke check를 실행합니다.

```bash
make alert-workflow-check
```

`make runbook-check`는 Prometheus alert rule의 runbook annotation과 실제 runbook 파일 존재 여부를 검증합니다.

```bash
make runbook-check
```

`make metrics-contract-check`는 FastAPI `/metrics`가 운영 필수 metric을 노출하는지 검증합니다.

```bash
make metrics-contract-check
```

`make alert-rule-metric-check`는 Prometheus alert rule이 참조하는 metric이 metrics contract와 실제 `/metrics`에 존재하는지 검증합니다.

```bash
make alert-rule-metric-check
```

`make ops-static-check`는 서비스 기동 없이 Prometheus rule, Alertmanager config, runbook, metric dependency를 정적으로 검증합니다.

```bash
make ops-static-check
```

`make ops-check`는 Prometheus rule test, Alertmanager config check, FastAPI health/readiness, runbook coverage, metrics contract, smoke check, alert workflow smoke check를 한 번에 검증합니다.

```bash
make ops-check
```

`make incident-report`는 alert event, acknowledgement, silence, MTTA/MTTR, pipeline/API 상태를 종합한 incident response report를 생성합니다.

```bash
make incident-report
```

`make incident-drill`은 synthetic incident scenario를 생성해 firing, acknowledgement, silence, resolved, incident report 흐름을 재현합니다.

```bash
make incident-drill
```

`make model-archive`는 현재 promoted model artifact를 archive 디렉터리에 스냅샷으로 저장하고 `model_promotion_archives`에 이력을 남깁니다.

```bash
make model-archive
```

`make model-rollback-plan`은 archived model을 기준으로 rollback할 때 어떤 모델 파일과 registry 상태가 변경되는지 dry-run으로 확인합니다.

```bash
MODEL_ROLLBACK_ARCHIVE_ID=1 make model-rollback-plan
```

`make model-rollback`은 지정한 archive id의 모델 파일을 `models/best/job_classifier.pkl`로 복원하고, 기존 promoted model을 `ROLLED_BACK` 상태로 변경합니다.

```bash
MODEL_ROLLBACK_ARCHIVE_ID=1 make model-rollback
```

`make model-lifecycle-check`는 model registry, archive, rollback 이력과 실제 모델 파일이 일관적인지 검증합니다.

```bash
make model-lifecycle-check
```

`make data-contract-check`는 raw / cleaned / skill extraction 테이블이 `config/data_contract.json`의 데이터 계약을 만족하는지 검증합니다.

```bash
make data-contract-check
```

`make model-class-performance-check`는 MLflow에 저장된 class-level evaluation metric을 조회해 직무별 f1, recall, support 기준을 검증합니다.

```bash
make model-class-performance-check
```

`make model-card`는 현재 PROMOTED 모델 기준의 Model Card를 생성합니다.

```bash
make model-card
```


`make api-sample`은 FastAPI에 샘플 `/predict` 요청을 보내고 API 예측 로그가 쌓이는지 확인합니다.

```bash
make api-sample
```

`make notify`는 pipeline check, prediction quality, prediction drift, API summary를 기반으로 알림 메시지를 생성합니다.

```bash
make notify
```

`make drift-check`는 rule label 분포와 batch prediction 분포를 비교해 prediction distribution drift를 검증합니다.

```bash
make drift-check
```

`make cleanup`은 오래된 API 로그, API prediction row, pipeline check 결과의 삭제 대상 건수를 확인합니다. 기본값은 dry-run입니다.

```bash
make cleanup
```

`make metrics`는 FastAPI `/metrics`에서 노출되는 Prometheus format 지표를 확인합니다.

```bash
make metrics
```

`make prometheus`는 Prometheus를 실행하고 FastAPI `/metrics`를 scrape합니다.

```bash
make prometheus
```

`make prometheus-check`는 Prometheus 설정과 alert rule 문법을 검증합니다.

```bash
make prometheus-check
```

`make prometheus-rule-test`는 synthetic time series 기반으로 Prometheus alert rule unit test를 실행합니다.

```bash
make prometheus-rule-test
```

`make alertmanager`는 Alertmanager를 실행합니다.

```bash
make alertmanager
```

`make alertmanager-logs`는 Alertmanager 로그를 확인합니다.

```bash
make alertmanager-logs
```

`make alertmanager-check`는 Alertmanager 설정 문법을 검증합니다.

```bash
make alertmanager-check
```

`make grafana`는 Grafana를 실행하고 Prometheus datasource와 JobSkill dashboard를 자동 provisioning합니다.

```bash
make grafana
```

## 접속 정보

### Airflow UI

호스트 포트를 `8081:8080`으로 사용한 경우:

```text
http://localhost:8081
```

호스트 포트를 `8080:8080`으로 사용한 경우:

```text
http://localhost:8080
```

### MLflow UI

```text
http://localhost:5000
```

### FastAPI

```text
http://localhost:8000/docs
```

### Streamlit Dashboard

```text
http://localhost:8501
```

### Prometheus

```text
http://localhost:9090
```

### Alertmanager

```text
http://localhost:9093
```

### Grafana

```text
http://localhost:3000
```


## Streamlit Dashboard 실행

### Docker Compose 실행

```bash
docker compose up -d dashboard
```

접속:

```text
http://localhost:8501
```

로그 확인:

```bash
docker compose logs --tail=100 dashboard
```

### 로컬 실행

로컬에서 직접 실행하려면 Streamlit과 Plotly가 필요합니다.

```bash
pip install streamlit plotly
```

로컬 실행 시 PostgreSQL 컨테이너에 호스트 기준으로 접속해야 하므로 `DB_HOST=localhost`를 사용합니다.

```bash
DB_HOST=localhost streamlit run src/dashboard/app.py
```

## Airflow DAG 실행

### DAG 목록 확인

```bash
docker compose exec airflow-scheduler airflow dags list
```

### DAG import error 확인

```bash
docker compose exec airflow-scheduler airflow dags list-import-errors
```

### DAG task 목록 확인

```bash
docker compose exec airflow-scheduler airflow tasks list jobskill_mlops_pipeline
```

### DAG unpause

```bash
docker compose exec airflow-scheduler airflow dags unpause jobskill_mlops_pipeline
```

### DAG trigger

```bash
docker compose exec airflow-scheduler airflow dags trigger jobskill_mlops_pipeline
```

### DAG run 확인

```bash
docker compose exec airflow-scheduler airflow dags list-runs jobskill_mlops_pipeline
```

### DAG run별 task 상태 확인

```bash
docker compose exec airflow-scheduler airflow tasks states-for-dag-run jobskill_mlops_pipeline "<run_id>"
```

## 실행 결과 확인

Airflow DAG를 통해 전체 파이프라인이 아래 순서로 실행됩니다.

```text
prepare_raw_sources
    ↓
generate_sample_jobs
    ↓
load_raw_jobs
    ↓
crawl_remoteok_jobs
    ↓
preprocess_jobs
    ↓
check_data_contract
    ↓
check_training_data
    ↓
train_model
    ↓
check_model_performance
    ↓
check_model_class_performance
    ↓
promote_model
    ↓
generate_model_card
    ↓
batch_inference
    ↓
check_prediction_quality
    ↓
check_prediction_drift
    ↓
generate_pipeline_report
    ↓
notify_pipeline_status
```

정상 상태 예시:

```text
prepare_raw_sources         success
generate_sample_jobs         success
load_raw_jobs                success
crawl_remoteok_jobs          success
preprocess_jobs              success
check_data_contract           success
check_training_data          success
train_model                  success
check_model_performance      success
check_model_class_performance success
promote_model                success
generate_model_card          success
batch_inference              success
check_prediction_quality      success
check_prediction_drift        success
generate_pipeline_report     success
notify_pipeline_status        success
```

파이프라인 실행 후 PostgreSQL에는 데이터, 검증 결과, 모델 승격 결과, 예측 결과가 저장됩니다.

```sql
SELECT COUNT(*) FROM raw_job_posts;
SELECT COUNT(*) FROM cleaned_job_posts;
SELECT COUNT(*) FROM job_post_skills;
SELECT COUNT(*) FROM pipeline_check_results;
SELECT COUNT(*) FROM model_registry;
SELECT COUNT(*) FROM model_predictions;
SELECT COUNT(*) FROM api_prediction_logs;
SELECT COUNT(*) FROM alert_events;
SELECT COUNT(*) FROM alert_current_states;
```

## Smoke Check

서비스 실행 후 주요 컴포넌트가 정상 동작하는지 확인하기 위해 smoke check 스크립트를 제공합니다.

실행:

```bash
make smoke
```

또는 직접 실행:

```bash
./scripts/smoke_check.sh
```

검증 항목:

```text
Docker Compose config
Container status
PostgreSQL connection
Project table existence
Core table counts
Airflow DAG import errors
Airflow pipeline task list
MLflow UI
FastAPI health
FastAPI readiness
FastAPI model info
FastAPI metrics
FastAPI metrics content
FastAPI readiness metrics
FastAPI runbook endpoint
FastAPI sample prediction requests
api_prediction_logs 저장 확인
model_predictions API row 저장 확인
Prometheus UI / target 확인
Prometheus alert rules 확인
Prometheus alert rule unit test
Alertmanager health 확인
Alertmanager webhook endpoint 확인
alert_events 저장 확인
alert_current_states 저장 확인
Grafana health
Streamlit dashboard
```

Alert workflow smoke check는 별도 스크립트로 alert 운영 기능을 더 깊게 검증합니다.

```bash
make alert-workflow-check
```

검증 항목:

```text
FastAPI /metrics alert response metric
Runbook endpoint
Alertmanager status
Prometheus query API
alert_events / alert_current_states / alert_acknowledgements / alert_settings / alert_silence_actions table
alert_settings maintenance_mode row
Synthetic Alertmanager webhook payload 저장
Smoke alert row cleanup
```

운영 기능 전체를 로컬에서 한 번에 검증하려면 `make ops-check`를 사용합니다.

```bash
make ops-check
```

Slack 알림 전송 자체는 실제 secret이 필요하므로 GitHub Actions smoke check에는 포함하지 않습니다. CI에서는 Alertmanager health, webhook endpoint, alert_events / alert_current_states 저장까지만 검증하고, Slack 전송은 로컬 secret 설정 후 수동 테스트로 확인합니다.

GitHub Actions smoke workflow에서도 동일한 스크립트를 사용합니다.  
단, GitHub Actions runner는 빈 환경이므로 API를 기동하기 전에 sample data 기반 최소 파이프라인을 먼저 실행해 promoted model을 생성한 뒤 smoke check를 수행합니다.

```text
PostgreSQL 실행
→ 프로젝트 테이블 생성
→ Airflow / MLflow 실행
→ sample_only 기반 최소 파이프라인 실행
→ promoted model 생성 확인
→ API / Dashboard / Alertmanager / Prometheus / Grafana 실행
→ FastAPI metrics endpoint 확인
→ Prometheus scrape target 및 alert rule 확인
→ Alertmanager health / webhook / alert event 저장 확인
→ Grafana health 확인
→ FastAPI sample prediction request 실행
→ api_prediction_logs / API prediction row 저장 확인
→ smoke_check.sh 실행
→ check_alert_workflow.sh 실행
```

## 로컬 Python 스크립트 실행 순서

Airflow 없이 개별 스크립트로 실행할 수도 있습니다.

```bash
python src/ingestion/prepare_raw_sources.py
python scripts/generate_sample_jobs.py
python src/ingestion/load_raw_jobs.py
python src/crawling/crawl_remoteok_jobs.py
python src/preprocessing/preprocess_db.py
python src/quality/check_data_contract.py
python src/quality/check_training_data.py
python src/training/train_baseline.py
python src/quality/check_model_performance.py
python src/quality/check_model_class_performance.py
python src/training/promote_model.py
python src/reporting/generate_model_card.py
python src/inference/batch_inference.py
python src/quality/check_prediction_quality.py
python src/quality/check_prediction_drift.py
python src/reporting/generate_pipeline_report.py
python src/notification/notify_pipeline_status.py
python src/maintenance/cleanup_old_records.py
```

컨테이너 내부에서 실행할 경우:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/ingestion/prepare_raw_sources.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python scripts/generate_sample_jobs.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/ingestion/load_raw_jobs.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/crawling/crawl_remoteok_jobs.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/preprocessing/preprocess_db.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_data_contract.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_training_data.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/training/train_baseline.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_model_performance.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_model_class_performance.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/training/promote_model.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/reporting/generate_model_card.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/inference/batch_inference.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_prediction_quality.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_prediction_drift.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/reporting/generate_pipeline_report.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/notification/notify_pipeline_status.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/maintenance/cleanup_old_records.py"
```

## FastAPI 실행

### 로컬 실행

```bash
uvicorn src.inference.api:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Compose 실행

```bash
docker compose up -d api
```

API 문서:

```text
http://localhost:8000/docs
```

Runbook HTML:

```text
http://localhost:8000/runbooks
http://localhost:8000/runbooks/jobskill_pipeline_check_failure.md
```

### API 엔드포인트

```text
GET  /
GET  /health
GET  /ready
GET  /model
GET  /metrics
GET  /runbooks
GET  /runbooks/{filename}
GET  /runbooks/{filename}/raw
POST /reload-model
POST /predict
POST /alertmanager/webhook
```

모델 정보 확인:

```bash
curl http://localhost:8000/model
```

모델 강제 reload:

```bash
curl -X POST http://localhost:8000/reload-model
```

예시 요청:

```json
{
  "title": "데이터 엔지니어 채용",
  "description": "Python SQL Airflow Kafka Spark 기반 데이터 파이프라인 개발자를 찾습니다.",
  "job_post_id": null
}
```

curl 테스트:

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "데이터 엔지니어 채용",
    "description": "Python SQL Airflow Kafka Spark 기반 데이터 파이프라인 개발자를 찾습니다.",
    "job_post_id": null
  }'
```

예시 응답:

```json
{
  "job_category": "Data Engineer",
  "confidence": 0.91,
  "confidence_level": "HIGH",
  "is_low_confidence": false,
  "top_predictions": [
    {
      "category": "Data Engineer",
      "probability": 0.91
    },
    {
      "category": "Backend Engineer",
      "probability": 0.05
    },
    {
      "category": "ML Engineer",
      "probability": 0.02
    }
  ],
  "skills": ["Airflow", "Kafka", "Python", "Spark", "SQL"],
  "prediction_id": 1,
  "prediction_source": "API",
  "api_log_id": 1,
  "model_name": "job_classifier",
  "model_run_id": "472340fc8ca14b50a382dd46f61108bf",
  "model_registry_id": 1,
  "model_path": "models/best/job_classifier.pkl"
}
```


### Sample API Requests

샘플 요청 스크립트를 통해 여러 직무 예시를 `/predict`로 전송할 수 있습니다.

```bash
make api-sample
```

직접 실행:

```bash
python scripts/send_sample_api_requests.py
```

환경변수로 API 주소를 바꿀 수 있습니다.

```bash
API_BASE_URL=http://localhost:8000 python scripts/send_sample_api_requests.py
```

실행 후 `api_prediction_logs`와 `model_predictions.prediction_source=API` row가 생성됩니다.

## PostgreSQL 확인 명령어

PostgreSQL 접속:

```bash
docker exec -it jobskill-postgres psql -U jobskill -d jobskill
```

테이블 확인:

```sql
\dt
```

데이터 건수 확인:

```sql
SELECT COUNT(*) FROM raw_job_posts;
SELECT COUNT(*) FROM cleaned_job_posts;
SELECT COUNT(*) FROM job_post_skills;
SELECT COUNT(*) FROM pipeline_check_results;
SELECT COUNT(*) FROM model_registry;
SELECT COUNT(*) FROM model_predictions;
SELECT COUNT(*) FROM api_prediction_logs;
```

source별 raw 데이터 확인:

```sql
SELECT
    source,
    COUNT(*) AS cnt
FROM raw_job_posts
GROUP BY source
ORDER BY source;
```

source별 라벨 품질 확인:

```sql
SELECT
    COALESCE(r.source, 'unknown') AS source,
    COUNT(*) AS cleaned_count,
    COUNT(*) FILTER (WHERE c.job_category = 'Unknown') AS unknown_count,
    ROUND(
        COUNT(*) FILTER (WHERE c.job_category = 'Unknown')::numeric
        / NULLIF(COUNT(*), 0),
        4
    ) AS unknown_ratio
FROM cleaned_job_posts c
JOIN raw_job_posts r
    ON c.raw_id = r.id
GROUP BY COALESCE(r.source, 'unknown')
ORDER BY cleaned_count DESC;
```

직무별 건수 확인:

```sql
SELECT job_category, COUNT(*)
FROM cleaned_job_posts
GROUP BY job_category
ORDER BY job_category;
```

기술스택 상위 목록 확인:

```sql
SELECT skill_name, COUNT(*)
FROM job_post_skills
GROUP BY skill_name
ORDER BY COUNT(*) DESC
LIMIT 20;
```

검증 결과 확인:

```sql
SELECT
    check_type,
    check_name,
    status,
    metric_value,
    threshold_value,
    message,
    checked_at
FROM pipeline_check_results
ORDER BY id DESC
LIMIT 20;
```

모델 registry 확인:

```sql
SELECT
    id,
    model_name,
    run_id,
    accuracy,
    f1_weighted,
    status,
    promoted_model_path,
    created_at
FROM model_registry
ORDER BY id DESC
LIMIT 10;
```

예측 결과 확인:

```sql
SELECT
    predicted_category,
    COUNT(*) AS cnt,
    ROUND(AVG(confidence)::numeric, 4) AS avg_confidence
FROM model_predictions
GROUP BY predicted_category
ORDER BY predicted_category;
```

예측 결과와 model lineage 확인:

```sql
SELECT
    mp.id,
    mp.job_post_id,
    mp.predicted_category,
    ROUND(mp.confidence::numeric, 4) AS confidence,
    mp.confidence_level,
    mp.is_low_confidence,
    mp.model_name,
    mp.model_version,
    mp.model_run_id,
    mp.model_registry_id,
    mr.status AS registry_status,
    mr.f1_weighted,
    mp.model_path,
    mp.predicted_at
FROM model_predictions mp
LEFT JOIN model_registry mr
    ON mp.model_registry_id = mr.id
ORDER BY mp.id DESC
LIMIT 20;
```

라벨과 예측 결과 비교:

```sql
SELECT
    mp.id,
    cjp.title,
    cjp.job_category AS rule_label,
    mp.predicted_category,
    ROUND(mp.confidence::numeric, 4) AS confidence,
    mp.model_name,
    mp.model_run_id,
    mp.predicted_at
FROM model_predictions mp
JOIN cleaned_job_posts cjp
    ON mp.job_post_id = cjp.id
ORDER BY mp.id
LIMIT 20;
```


API / BATCH 예측 구분 확인:

```sql
SELECT
    prediction_source,
    COUNT(*) AS cnt
FROM model_predictions
GROUP BY prediction_source
ORDER BY prediction_source;
```

API 요청 로그 확인:

```sql
SELECT
    id,
    prediction_id,
    request_title,
    response_category,
    response_confidence_level,
    status,
    ROUND(latency_ms::numeric, 2) AS latency_ms,
    created_at
FROM api_prediction_logs
ORDER BY id DESC
LIMIT 10;
```

Prediction quality check 결과 확인:

```sql
SELECT
    check_type,
    check_name,
    status,
    ROUND(metric_value::numeric, 4) AS metric_value,
    ROUND(threshold_value::numeric, 4) AS threshold_value,
    message,
    checked_at
FROM pipeline_check_results
WHERE check_type = 'PREDICTION_QUALITY'
ORDER BY id DESC
LIMIT 20;
```

Prediction drift check 결과 확인:

```sql
SELECT
    check_type,
    check_name,
    status,
    ROUND(metric_value::numeric, 4) AS metric_value,
    ROUND(threshold_value::numeric, 4) AS threshold_value,
    message,
    checked_at
FROM pipeline_check_results
WHERE check_type = 'PREDICTION_DRIFT'
ORDER BY id DESC
LIMIT 20;
```


Alert event 이력 확인:

```sql
SELECT
    id,
    status,
    alert_name,
    severity,
    service,
    summary,
    created_at
FROM alert_events
ORDER BY id DESC
LIMIT 20;
```

현재 alert 상태 확인:

```sql
SELECT
    fingerprint,
    status,
    alert_name,
    severity,
    service,
    starts_at,
    ends_at,
    last_received_at,
    updated_at
FROM alert_current_states
ORDER BY updated_at DESC
LIMIT 20;
```

## Pipeline Report 생성

리포트 생성:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/reporting/generate_pipeline_report.py"
```

생성 결과:

```text
reports/latest_pipeline_report.md
```

리포트에서 확인 가능한 내용:

```text
현재 promoted model
모델 승격/거절 이력
예측 결과 lineage
데이터 품질 체크 결과
모델 성능 체크 결과
source별 Unknown 비율
source별 라벨 분포
source별 skill 추출 결과
source별 prediction confidence
prediction quality gate 결과
prediction distribution drift 결과
API 요청 성공/실패율
API low confidence 비율
최근 API prediction logs
```


### Sample Pipeline Report

포트폴리오용 샘플 리포트는 아래 문서에서 확인할 수 있습니다.

```text
docs/sample_pipeline_report.md
```

`reports/latest_pipeline_report.md`는 DAG 실행 시점마다 갱신되는 runtime output입니다.  
GitHub에서 고정된 예시 산출물을 보여주기 위해 `docs/sample_pipeline_report.md`를 별도로 관리합니다.

## 테스트 실행

로컬 실행:

```bash
pytest
```

컨테이너 내부 실행:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && pytest"
```

테스트 대상:

```text
직무 라벨링 규칙
예측 confidence level
low confidence 판단
top-k prediction 생성
```

### GitHub Actions

GitHub Actions는 두 가지 workflow로 구성합니다.

```text
.github/workflows/pytest.yml
.github/workflows/smoke.yml
```

#### Python CI

push 또는 pull request 발생 시 pytest와 Ruff를 자동 실행합니다.

실행 조건:

```text
push to main
push to feature/**
pull request to main
```

실행 항목:

```bash
ruff check src dags scripts tests
pytest
```

로컬에서도 동일하게 확인할 수 있습니다.

```bash
pip install -r requirements-dev.txt
ruff check src dags scripts tests
pytest
```

#### Smoke Check

Docker Compose 기반 전체 서비스 기동성을 확인하는 smoke check workflow입니다.

실행 조건:

```text
workflow_dispatch
push to main
push to feature/**
```

검증 흐름:

```text
Docker Compose image build
Static ops validation run
PostgreSQL start
Airflow / MLflow metadata DB prepare
Project table create
Airflow metadata DB init
Airflow / MLflow start
sample_only minimal pipeline run
promoted model existence check
FastAPI / Dashboard / Alertmanager / Prometheus / Grafana start
FastAPI metrics validation
Prometheus target and alert rule validation
Alertmanager health / webhook / alert event table validation
Grafana health validation
Sample API prediction request run
api_prediction_logs and API prediction rows validation
scripts/smoke_check.sh run
scripts/check_alert_workflow.sh run
```

GitHub Actions의 빈 runner에서는 promoted model이 존재하지 않으므로, API를 시작하기 전에 최소 파이프라인을 먼저 실행해 `models/best/job_classifier.pkl`과 `model_registry`의 promoted model을 생성합니다. 이후 `/metrics`, Prometheus target/alert rule, Alertmanager webhook, Grafana health, sample API request를 확인해 운영 지표 노출/수집/알림 이벤트 저장/시각화 경로와 API 예측 결과 저장까지 함께 검증합니다.

## Release / Changelog

프로젝트의 주요 완성 단위는 `CHANGELOG.md`에 기록합니다.

현재 기준 모니터링 릴리스:

```text
v0.2.0 - Monitoring & Alerting Release
v0.1.0 - MVP Release
```

릴리스 기준:

```text
Airflow end-to-end DAG 구성
PostgreSQL 기반 데이터/예측/검증/모델 메타데이터 저장
MLflow tracking / artifact 연동
모델 성능 gate와 promotion
Batch inference / API inference 저장 분리
Prediction quality gate
Pipeline report
Streamlit Dashboard
Makefile
Local smoke check
GitHub Actions Python CI
GitHub Actions Docker Compose smoke check
Sample API request validation
Pipeline Notification
Prediction drift gate
Retention cleanup script
FastAPI /metrics endpoint
Prometheus scrape 구성
Grafana dashboard provisioning
Prometheus alert rules
Alertmanager webhook routing
Alert event DB logging
Current alert state tracking
Streamlit Alert History
Grafana Alert Events panels
Incident response report
Incident response drill
Prometheus alert rule unit test
FastAPI health/readiness check
API readiness metrics and alert
Runbook coverage check
Metrics contract check
Alert rule metric dependency check
Static ops validation check
Ops validation check
```

태그 생성 예시:

```bash
git tag -a v0.2.0 -m "v0.2.0 monitoring and alerting release"
git push origin v0.2.0
```

## Git 제외 대상

아래 파일과 디렉터리는 Git에 올리지 않습니다.

```text
.env
.env.*
!.env.example
.venv/
__pycache__/
data/raw/*.csv
data/processed/*.csv
models/
mlartifacts/
mlflow.db
mlruns/
airflow_logs/
reports/*
!reports/.gitkeep
simple_auth_manager_passwords.json
```

포트폴리오용 스크린샷은 Git에 포함합니다.

```text
docs/images/
```

`reports/latest_pipeline_report.md`는 실행 결과 예시로 보여주고 싶으면 커밋해도 되고, 매 실행마다 바뀌는 산출물로 관리하려면 `.gitignore`에 추가합니다.

## Line Ending 관리

WSL / Windows 환경에서 shell script, Makefile, workflow 파일의 줄바꿈이 CRLF로 바뀌면 실행 문제가 생길 수 있습니다.

이를 방지하기 위해 `.gitattributes`에서 주요 파일의 line ending을 LF로 고정합니다.

```gitattributes
*.sh text eol=lf
Makefile text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.py text eol=lf
*.md text eol=lf
```

변경 후 기존 파일을 재정규화할 수 있습니다.

```bash
git add --renormalize .
```

## 트러블슈팅

### 1. MLflow command error

에러:

```text
airflow command error: argument GROUP_OR_COMMAND: invalid choice: 'mlflow'
```

원인:

```text
apache/airflow 이미지의 기본 entrypoint가 airflow이기 때문에
mlflow ui 명령이 airflow mlflow ui처럼 해석됨
```

해결:

```yaml
mlflow:
  image: jobskill-airflow:3.2.2
  entrypoint: /bin/bash
  command:
    - -c
    - |
      mlflow ui \
        --backend-store-uri postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@postgres:5432/${MLFLOW_DB_NAME} \
        --default-artifact-root /opt/airflow/project/mlartifacts \
        --host 0.0.0.0 \
        --port 5000
```

### 2. Airflow task 권한 오류

증상:

```text
PermissionError: [Errno 13] Permission denied: 'data/raw/sample_jobs.csv'
```

해결:

```bash
sudo chown -R 50000:0 data models mlartifacts airflow_logs reports
sudo chmod -R g+rwX data models mlartifacts airflow_logs reports
```

### 3. cleaned_job_posts 삭제 시 FK 오류

증상:

```text
DELETE FROM cleaned_job_posts
ForeignKeyViolation
```

원인:

```text
model_predictions 또는 job_post_skills가 cleaned_job_posts를 참조 중
```

해결:

```sql
TRUNCATE TABLE
    model_predictions,
    job_post_skills,
    cleaned_job_posts
RESTART IDENTITY
CASCADE;
```

Remote OK raw 데이터를 삭제하려면 파생 테이블을 먼저 비워야 합니다.

```sql
TRUNCATE TABLE
    model_predictions,
    job_post_skills,
    cleaned_job_posts
RESTART IDENTITY
CASCADE;

DELETE FROM raw_job_posts
WHERE source = 'remoteok';
```

### 4. Airflow execution API connection refused

증상:

```text
httpx.ConnectError: [Errno 111] Connection refused
```

해결:

```yaml
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-apiserver:8080/execution/
```

확인:

```bash
docker compose exec airflow-scheduler airflow config get-value core execution_api_server_url
```

정상:

```text
http://airflow-apiserver:8080/execution/
```

### 5. Invalid auth token

증상:

```text
Invalid auth token: Signature verification failed
```

원인:

```text
scheduler / apiserver / dag-processor / triggerer 간 JWT secret 불일치
```

해결:

```yaml
AIRFLOW__API_AUTH__JWT_SECRET: ${AIRFLOW_JWT_SECRET}
AIRFLOW__API__SECRET_KEY: ${AIRFLOW_API_SECRET_KEY}
```

확인:

```bash
docker compose exec airflow-scheduler airflow config get-value api_auth jwt_secret
docker compose exec airflow-apiserver airflow config get-value api_auth jwt_secret

docker compose exec airflow-scheduler airflow config get-value api secret_key
docker compose exec airflow-apiserver airflow config get-value api secret_key
```

정상 조건:

```text
scheduler jwt_secret == apiserver jwt_secret
scheduler api_secret == apiserver api_secret
```

### 6. 8080 port already allocated

증상:

```text
Bind for 0.0.0.0:8080 failed: port is already allocated
```

해결 1. 기존 컨테이너 제거:

```bash
docker ps | grep 8080
docker rm -f <container_name>
```

해결 2. 호스트 포트 변경:

```yaml
ports:
  - "8081:8080"
```

이 경우 Airflow UI는 아래로 접속합니다.

```text
http://localhost:8081
```

단, execution API URL은 그대로 둡니다.

```yaml
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-apiserver:8080/execution/
```

### 7. docker-compose.yml environment must be a mapping

증상:

```text
services.airflow-apiserver.environment must be a mapping
services.airflow-scheduler.environment must be a mapping
```

정상:

```yaml
environment:
  KEY: value
  KEY2: value2
```

잘못된 예:

```yaml
environment:
  - KEY=value
```

확인:

```bash
docker compose config
```

### 8. Batch inference 입력 데이터 없음

증상:

```text
ValueError: No cleaned job posts found. Run preprocess_db.py first.
```

해결:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/preprocessing/preprocess_db.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_training_data.py"
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/inference/batch_inference.py"
```

또는 전체 DAG를 다시 실행합니다.

```bash
docker compose exec airflow-scheduler airflow dags trigger jobskill_mlops_pipeline
```

### 9. 모델 승격 결과 확인

모델 promotion 결과는 `model_registry` 테이블에서 확인합니다.

```bash
docker exec -it jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    model_name,
    run_id,
    accuracy,
    f1_weighted,
    status,
    message,
    created_at
FROM model_registry
ORDER BY id DESC
LIMIT 10;
"
```

같은 성능의 모델을 반복 실행하면 `REJECTED`가 나올 수 있습니다. 이는 기존 best model보다 성능이 개선되지 않았다는 의미이므로 정상 동작입니다.

### 10. API 모델 reload 확인

현재 API가 사용하는 모델 정보는 `/model`에서 확인합니다.

```bash
curl http://localhost:8000/model
```

강제로 reload하려면 아래 API를 호출합니다.

```bash
curl -X POST http://localhost:8000/reload-model
```

예측 시점에 promoted model 정보가 바뀌면 API는 새 모델을 reload합니다. reload 로그는 API 컨테이너 로그에서 확인할 수 있습니다.

```bash
docker compose logs --tail=100 api
```

### 11. 크롤링 데이터 Unknown 비율이 높은 경우

Remote OK는 개발/데이터 직무 외의 공고도 포함될 수 있습니다.

확인:

```sql
SELECT
    job_category,
    COUNT(*) AS cnt
FROM cleaned_job_posts
GROUP BY job_category
ORDER BY cnt DESC;
```

source별 Unknown 비율 확인:

```sql
SELECT
    COALESCE(r.source, 'unknown') AS source,
    COUNT(*) AS cleaned_count,
    COUNT(*) FILTER (WHERE c.job_category = 'Unknown') AS unknown_count,
    ROUND(
        COUNT(*) FILTER (WHERE c.job_category = 'Unknown')::numeric
        / NULLIF(COUNT(*), 0),
        4
    ) AS unknown_ratio
FROM cleaned_job_posts c
JOIN raw_job_posts r
    ON c.raw_id = r.id
GROUP BY COALESCE(r.source, 'unknown')
ORDER BY cleaned_count DESC;
```

해결 방향:

```text
crawler에서 label_jobs.py 기준으로 Unknown 공고 제외
preprocess_db.py에서 tags를 description과 함께 라벨링에 사용
label_jobs.py의 직무별 keyword 확장
```


### 12. crawler_only 학습 시 stratified split 실패

증상:

```text
ValueError: The least populated classes in y have only 1 member
```

원인:

```text
crawler_only 모드에서는 실제 수집 데이터 분포가 치우쳐 특정 직무 라벨이 1건만 존재할 수 있음
stratify=y를 사용하는 train_test_split은 클래스별 최소 2건 이상이 필요함
```

해결:

```text
train_baseline.py에서 MIN_SAMPLES_PER_CLASS보다 적은 rare class를 학습 데이터에서 제외
TEST_SIZE를 class 개수 이상으로 보정
```

환경변수:

```env
MIN_SAMPLES_PER_CLASS=2
TEST_SIZE=0.3
```

### 13. api_prediction_logs FK로 인한 batch inference TRUNCATE 실패

증상:

```text
cannot truncate a table referenced in a foreign key constraint
Table "api_prediction_logs" references "model_predictions"
```

원인:

```text
api_prediction_logs.prediction_id가 model_predictions.id를 참조하므로
model_predictions만 단독 TRUNCATE할 수 없음
```

해결:

```text
model_predictions에 prediction_source 컬럼 추가
API 예측은 prediction_source = API
batch 예측은 prediction_source = BATCH
batch inference는 BATCH row만 DELETE 후 재생성
```

```sql
DELETE FROM model_predictions
WHERE COALESCE(prediction_source, 'BATCH') = 'BATCH';
```

### 14. batch inference INSERT 컬럼 개수 불일치

증상:

```text
INSERT has more expressions than target columns
```

원인:

```text
VALUES에는 prediction_source를 넣었지만
INSERT INTO model_predictions 컬럼 목록에 prediction_source가 빠져 있었음
```

해결:

```sql
INSERT INTO model_predictions (
    job_post_id,
    prediction_source,
    model_name,
    model_version,
    model_run_id,
    model_registry_id,
    model_path,
    predicted_category,
    confidence,
    confidence_level,
    is_low_confidence,
    top_predictions
)
```

### 15. check_prediction_quality SQL JOIN 문법 오류

증상:

```text
syntax error at or near "JOIN"
```

원인:

```text
SQL 작성 시 WHERE가 JOIN보다 먼저 배치됨
```

잘못된 예:

```sql
FROM model_predictions mp
WHERE COALESCE(mp.prediction_source, 'BATCH') = 'BATCH'
JOIN cleaned_job_posts c
    ON mp.job_post_id = c.id
```

정상:

```sql
FROM model_predictions mp
JOIN cleaned_job_posts c
    ON mp.job_post_id = c.id
WHERE COALESCE(mp.prediction_source, 'BATCH') = 'BATCH'
```

### 16. Prediction quality gate 실패

증상:

```text
avg_prediction_confidence failed
low_confidence_ratio failed
```

원인:

```text
batch inference 결과의 평균 confidence가 기준보다 낮거나
low confidence 비율이 허용 기준보다 높음
```

확인:

```bash
docker compose exec airflow-scheduler bash -lc "cd /opt/airflow/project && python src/quality/check_prediction_quality.py"
```

임시 기준 완화:

```env
MIN_AVG_PREDICTION_CONFIDENCE=0.3
MAX_LOW_CONFIDENCE_RATIO=0.8
```

단, 포트폴리오 관점에서는 기준을 낮추는 것보다 source별 / category별 confidence 리포트로 품질 이슈를 드러내는 것이 더 자연스럽습니다.



### 17. Prediction drift gate 실패

증상:

```text
Prediction drift check failed: prediction_distribution_psi
```

원인:

```text
cleaned_job_posts의 rule label 분포와 batch prediction의 predicted_category 분포가 크게 달라짐
모델이 특정 직무로 예측을 과도하게 몰아주거나, 학습/추론 데이터 분포가 달라졌을 가능성이 있음
```

확인:

```bash
make drift-check
```

DB 확인:

```sql
SELECT
    check_name,
    status,
    ROUND(metric_value::numeric, 4) AS metric_value,
    ROUND(threshold_value::numeric, 4) AS threshold_value,
    message,
    checked_at
FROM pipeline_check_results
WHERE check_type = 'PREDICTION_DRIFT'
ORDER BY id DESC
LIMIT 10;
```

임시 기준 완화:

```env
MAX_PREDICTION_DISTRIBUTION_PSI=0.5
```

단, 운영 관점에서는 기준을 완화하기 전에 label 분포와 prediction 분포가 왜 달라졌는지 확인하는 것이 좋습니다.

### 18. Maintenance cleanup이 실제 삭제되지 않는 경우

증상:

```text
[DRY RUN] No records were deleted.
```

원인:

```text
기본값이 CLEANUP_DRY_RUN=true이기 때문에 삭제 대상 건수만 확인하고 실제 삭제하지 않음
```

실제 삭제가 필요할 때만 `.env`에서 아래처럼 변경합니다.

```env
CLEANUP_DRY_RUN=false
```

환경변수 변경 후 컨테이너를 재생성합니다.

```bash
docker compose up -d --force-recreate airflow-scheduler
make cleanup
```

주의:

```text
api_prediction_logs가 model_predictions를 참조하므로,
cleanup은 api_prediction_logs를 먼저 정리한 뒤 API prediction row를 정리합니다.
```


### 19. docker-compose.yml dashboard 들여쓰기 오류

증상:

```text
mapping key "image" already defined
mapping key "container_name" already defined
```

원인:

```text
dashboard 서비스가 services 하위가 아니라 api 서비스 내부에 잘못 들여쓰기됨
```

잘못된 예:

```yaml
  api:
    ...
    depends_on:
      postgres:
        condition: service_healthy

    dashboard:
    image: jobskill-airflow:3.2.2
```

정상:

```yaml
  api:
    ...
    depends_on:
      postgres:
        condition: service_healthy

  dashboard:
    image: jobskill-airflow:3.2.2
```

확인:

```bash
docker compose config
```

### 20. Streamlit command not found

증상:

```text
streamlit: command not found
```

원인:

```text
dashboard 서비스가 사용하는 jobskill-airflow 이미지에 streamlit / plotly가 설치되지 않음
```

해결:

```text
requirements.txt에 streamlit, plotly 추가
Airflow 이미지 재빌드
dashboard 서비스 재실행
```

```bash
docker compose build airflow-image
docker compose up -d dashboard
```

### 21. GitHub Actions에서 pytest import 실패

증상:

```text
ModuleNotFoundError
```

원인:

```text
workflow에서 테스트에 필요한 의존성을 충분히 설치하지 않음
```

해결:

```text
requirements-dev.txt에 pytest / ruff 추가
테스트가 pandas, sklearn 등 프로젝트 의존성을 직접 import하면 requirements.txt도 함께 설치
```

예시:

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
```


### 22. GitHub Actions에 Smoke Check workflow가 보이지 않는 경우

증상:

```text
Actions 화면에 pytest.yml만 보이고 smoke.yml이 보이지 않음
```

확인:

```bash
git fetch origin
git ls-tree -r origin/main --name-only | grep ".github/workflows"
git show origin/main:.github/workflows/smoke.yml
```

정상 조건:

```text
.github/workflows/pytest.yml
.github/workflows/smoke.yml
```

`workflow_dispatch`만 있는 workflow는 기본 브랜치에 workflow 파일이 반영되어야 Actions 화면에 보입니다.  
초기 등록 확인을 쉽게 하기 위해 아래처럼 `push` trigger를 임시로 추가할 수 있습니다.

```yaml
on:
  workflow_dispatch:
  push:
    branches:
      - main
      - "feature/**"
```

### 23. GitHub Actions smoke check에서 FastAPI health 실패

증상:

```text
[CHECK] FastAPI health
curl: (7) Failed to connect to localhost port 8000
[FAIL] FastAPI health
```

원인:

```text
GitHub Actions runner는 빈 환경이므로 API 기동 시점에 promoted model이 아직 존재하지 않음
FastAPI가 시작 시점에 모델을 로드하지 못해 컨테이너가 종료됨
```

해결:

```text
smoke workflow에서 API를 시작하기 전에 sample_only 기반 최소 파이프라인을 먼저 실행
models/best/job_classifier.pkl 생성 확인
model_registry의 PROMOTED row 생성 확인
이후 API와 Dashboard 실행
```

확인 명령:

```bash
test -f models/best/job_classifier.pkl

docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT id, model_name, status, promoted_model_path, created_at
FROM model_registry
ORDER BY id DESC
LIMIT 5;
"
```

### 24. feature 브랜치 push 시 upstream branch 없음

증상:

```text
fatal: The current branch feature/xxx has no upstream branch.
```

해결:

```bash
git push --set-upstream origin feature/xxx
```

이후부터는 같은 브랜치에서 `git push`만 실행하면 됩니다.


### 25. Pipeline Notification에서 메시지가 두 번 출력되는 경우

증상:

```text
[Pipeline Notification Message]
...
[Notification skipped] SLACK_WEBHOOK_URL is not set.
...
동일한 메시지가 한 번 더 출력됨
```

원인:

```text
main()에서 메시지를 한 번 출력하고,
SLACK_WEBHOOK_URL이 없을 때 send_slack_message()에서도 같은 메시지를 다시 출력함
```

해결:

```text
SLACK_WEBHOOK_URL이 없을 때는 skip 메시지만 출력하고 message 본문은 재출력하지 않도록 수정
```

정상 출력:

```text
[Pipeline Notification Message]
...
[Notification skipped] SLACK_WEBHOOK_URL is not set.
```

### 26. Pipeline Notification에서 Latest Model이 REJECTED로 보이는 경우

증상:

```text
Latest Model
- status=REJECTED
```

원인:

```text
model_registry를 ORDER BY id DESC LIMIT 1로 조회하면
가장 최근 학습 결과가 기존 best보다 낮아 REJECTED된 경우에도 최신 row로 표시됨
```

해결:

```text
알림에서 실제 serving 대상 모델을 보여주려면 status='PROMOTED' 조건으로 latest promoted model을 조회
```

예시:

```sql
SELECT *
FROM model_registry
WHERE status = 'PROMOTED'
ORDER BY id DESC
LIMIT 1;
```

### 27. Slack 알림이 전송되지 않는 경우

증상:

```text
[Notification skipped] SLACK_WEBHOOK_URL is not set.
```

원인:

```text
.env에 SLACK_WEBHOOK_URL이 없거나,
docker-compose.yml에서 airflow 컨테이너 환경변수로 전달되지 않음
```

확인:

```bash
docker compose exec airflow-scheduler bash -lc 'echo $ALERT_ENABLED'
docker compose exec airflow-scheduler bash -lc 'echo $ALERT_ONLY_ON_FAILURE'
docker compose exec airflow-scheduler bash -lc 'echo $SLACK_WEBHOOK_URL'
```

해결:

```text
.env에 SLACK_WEBHOOK_URL 추가
docker-compose.yml의 Airflow 공통 environment에 ALERT_* / SLACK_WEBHOOK_URL 전달
Airflow 컨테이너 force recreate
```

```bash
docker compose up -d --force-recreate \
  airflow-scheduler \
  airflow-apiserver \
  airflow-dag-processor \
  airflow-triggerer
```

### 28. smoke check에서 API prediction log 검증 실패

증상:

```text
[CHECK] API prediction logs
[FAIL] API prediction logs
```

원인:

```text
FastAPI /predict 요청은 성공하지 않았거나,
api_prediction_logs에 SUCCESS row가 저장되지 않음
```

확인:

```bash
make api-sample

docker exec -it jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT id, prediction_id, request_title, response_category, status, created_at
FROM api_prediction_logs
ORDER BY id DESC
LIMIT 10;
"
```

해결 방향:

```text
FastAPI 컨테이너 로그 확인
/model에서 promoted model 로드 여부 확인
/predict 응답 확인
api_prediction_logs INSERT 로직 확인
```

```bash
docker compose logs --tail=100 api
curl http://localhost:8000/model
```



### 29. curl /metrics 확인 시 Failed writing body가 나오는 경우

증상:

```text
curl: Failed writing body
```

원인:

```text
curl http://localhost:8000/metrics | head -50 처럼 사용할 때
head가 먼저 종료되면서 curl이 나머지 출력 쓰기에 실패해 발생하는 메시지
```

해결:

```bash
curl -fsS http://localhost:8000/metrics -o /tmp/jobskill_metrics.txt
head -50 /tmp/jobskill_metrics.txt
```

또는 진행률 표시 없이 확인합니다.

```bash
curl -s http://localhost:8000/metrics | head -50
```

### 30. Prometheus target이 DOWN인 경우

증상:

```text
Prometheus /targets에서 jobskill-api가 DOWN으로 표시됨
```

확인:

```bash
docker compose ps api prometheus
curl -fsS http://localhost:8000/metrics | head
make prometheus-logs
```

원인:

```text
api 컨테이너가 기동되지 않았거나
Prometheus 설정의 target이 Docker Compose 내부 서비스명 기준이 아님
```

정상 설정:

```yaml
scrape_configs:
  - job_name: "jobskill-api"
    metrics_path: "/metrics"
    static_configs:
      - targets:
          - "api:8000"
```

Docker Compose 내부에서는 `localhost:8000`이 아니라 `api:8000`을 사용해야 합니다.

### 31. Grafana dashboard가 보이지 않는 경우

증상:

```text
Grafana에는 접속되지만 JobSkill MLOps Overview dashboard가 보이지 않음
```

확인:

```bash
docker compose ps grafana
make grafana-logs
```

확인할 파일:

```text
monitoring/grafana/provisioning/datasources/prometheus.yml
monitoring/grafana/provisioning/dashboards/dashboard.yml
monitoring/grafana/dashboards/jobskill-mlops-overview.json
```

Grafana 컨테이너에 provisioning 파일이 정상 mount되어야 합니다.

```yaml
volumes:
  - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
  - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
```

### 32. docker-compose.yml에서 prometheus/grafana 추가 후 mapping key 중복 오류

증상:

```text
yaml: unmarshal errors:
  mapping key "image" already defined
  mapping key "container_name" already defined
```

원인:

```text
prometheus 또는 grafana 서비스가 api/dashboard 같은 다른 서비스 내부에 잘못 들여쓰기됨
```

정상 구조:

```yaml
services:
  api:
    image: ...

  prometheus:
    image: prom/prometheus:v2.55.1

  grafana:
    image: grafana/grafana:11.3.0
```

검증:

```bash
docker compose config
```


### 33. promtool 실행 시 unexpected promtool 오류

증상:

```text
Error parsing command line arguments: unexpected promtool
prometheus: error: unexpected promtool
```

원인:

```text
prom/prometheus 이미지의 기본 entrypoint가 prometheus이므로
명령 뒤에 promtool을 붙이면 prometheus promtool ... 형태로 해석됨
```

해결:

```bash
docker run --rm   --entrypoint promtool   -v "$(pwd)/monitoring/prometheus:/etc/prometheus:ro"   prom/prometheus:v2.55.1   check config /etc/prometheus/prometheus.yml
```

Makefile에서는 `--entrypoint promtool`을 사용합니다.

### 34. Prometheus PipelineCheckFailure alert가 계속 firing인 경우

원인:

```text
전체 누적 pipeline_check_results 중 과거 FAIL이 남아 있으면
status != PASS 조건이 계속 참이 되어 alert가 계속 firing될 수 있음
```

해결:

```text
전체 누적 실패가 아니라 최근 1시간 실패 기준 지표를 사용
```

사용 지표:

```text
jobskill_pipeline_recent_failed_checks_total
```

예시 rule:

```promql
sum(jobskill_pipeline_recent_failed_checks_total) > 0
```

### 35. Alertmanager webhook은 성공했는데 현재 alert 상태가 중복되어 보이는 경우

`alert_events`는 모든 이벤트를 누적 저장하는 이력 테이블입니다. 같은 alert가 반복 전송되면 row가 계속 쌓이는 것이 정상입니다.

현재 상태만 보고 싶으면 `alert_current_states`를 확인합니다.

```sql
SELECT
    fingerprint,
    status,
    alert_name,
    severity,
    service,
    updated_at
FROM alert_current_states
ORDER BY updated_at DESC;
```

### 36. Grafana Alert Events 패널 값이 안 보이는 경우

먼저 FastAPI `/metrics`에서 alert 지표가 노출되는지 확인합니다.

```bash
curl -fsS http://localhost:8000/metrics | grep jobskill_alert_events_total
curl -fsS http://localhost:8000/metrics | grep jobskill_alert_current_states_total
```

Prometheus에서 지표가 수집되는지도 확인합니다.

```bash
curl -fsS 'http://localhost:9090/api/v1/query?query=jobskill_alert_events_total'
curl -fsS 'http://localhost:9090/api/v1/query?query=jobskill_alert_current_states_total'
```

Prometheus에 값이 있는데 Grafana에 보이지 않으면 Grafana를 재기동합니다.

```bash
docker compose up -d --force-recreate grafana
```


## What I Learned

이 프로젝트를 통해 아래 내용을 실습했습니다.

```text
Airflow 3.x 기반 DAG orchestration 구성
Airflow scheduler, apiserver, dag-processor, triggerer 분리 실행
Airflow execution API와 JWT secret 설정 문제 해결
LocalExecutor 기반 task 실행 구조 확인
BashOperator 기반 DAG를 PythonOperator 기반 DAG로 개선
PostgreSQL을 서비스 DB, Airflow metadata DB, MLflow backend store로 분리 구성
MLflow backend store와 artifact store 분리
scikit-learn 모델 학습 결과를 MLflow에 기록
데이터 품질 체크를 통한 학습 전 검증 로직 구성
MLflow metric 기반 모델 성능 gate 구성
데이터 품질/모델 성능 검증 결과를 PostgreSQL에 저장
기준 미달 데이터/모델이 후속 task로 넘어가지 않도록 DAG 제어
기존 best model과 신규 학습 모델의 성능 비교 및 promotion 로직 구성
promoted model 기반 batch inference 구성
FastAPI 기반 단건 추론 API 구성
FastAPI serving model 자동 reload 구성
예측 결과에 model lineage와 prediction quality 저장
Remote OK 외부 채용공고 수집 및 필터링 구성
source별 데이터 품질 리포트 구성
pytest 기반 단위 테스트 추가
Docker Compose 기반 MLOps 개발 환경 구성
Git history에 포함된 secret 제거 및 secret rotation 수행
DATA_SOURCE_MODE 기반 sample/crawler/mixed 실행 모드 구성
외부 API 수집 실패에 대한 retry / fallback 처리 구성
FastAPI 요청/응답/실패/latency 로그 테이블 분리
API prediction과 batch prediction 저장 경로 분리
FK 제약조건을 고려한 batch inference 재실행 방식 개선
prediction quality gate를 통한 batch inference 결과 검증
source/category별 prediction confidence 분석 리포트 구성
GitHub Actions 기반 pytest 자동 실행 구성
Ruff 기반 코드 품질 검사 CI 구성
Streamlit / Plotly 기반 MLOps Dashboard 구성
FastAPI sample request script를 통한 API 예측 흐름 검증
smoke check에서 API prediction log 저장 여부 검증
Pipeline Notification 기반 모델/검증/예측/API 상태 요약 구성
Slack Webhook 기반 알림 전송 옵션 구성
포트폴리오용 dashboard 스크린샷 및 sample pipeline report 문서화
Makefile 기반 프로젝트 실행 명령어 표준화
로컬 smoke check script를 통한 서비스 기동성 검증
GitHub Actions에서 Docker Compose 기반 smoke check workflow 구성
CI 빈 환경에서 promoted model 생성 전 API 기동 시 실패하는 문제 해결
CHANGELOG와 Git tag 기반 MVP 릴리스 관리
prediction distribution drift check를 통한 예측 분포 변화 감지 구성
PSI 기반 label/prediction distribution 비교 로직 구성
retention cleanup을 통한 API 로그/예측/검증 결과 보관 정책 구성
dry-run 기반 안전한 운영 유지보수 스크립트 구성
FastAPI /metrics 기반 Prometheus text format 운영 지표 노출 구성
Prometheus scrape config를 통한 JobSkill API metrics 수집 구성
Grafana datasource/dashboard provisioning 구성
Grafana 기반 MLOps 운영 지표 시각화 구성
Prometheus alert rule 기반 운영 이상 조건 정의
Alertmanager webhook receiver 구성
FastAPI /alertmanager/webhook 기반 alert 수신 API 구성
alert_events 기반 alert 이벤트 이력 저장 구성
alert_current_states 기반 fingerprint 현재 상태 upsert 구성
FastAPI /metrics에 alert event/current state 지표 추가
Streamlit Dashboard Alert History 탭 구성
Grafana Alert Events 패널 구성
Streamlit Dashboard에서 alert acknowledgement와 조치 메모 저장 구성
MTTA / MTTR 기반 alert response metrics 구성
Prometheus alert response escalation rule 구성
runtime alert maintenance mode 구성
Streamlit Dashboard 기반 Alertmanager silence 생성 기능 구성
alert_silence_actions 기반 silence 이력 저장 구성
incident response report 생성 및 Dashboard preview/download 구성
alert workflow smoke check 기반 alert 운영 기능 자동 검증 구성
Makefile help / validation command 정리
MLflow training dataset tracking 기반 학습 데이터 lineage 구성
MLflow evaluation artifact 기반 모델 평가 산출물 관리
class-level model performance gate 기반 모델 승격 전 세부 성능 검증
Model Card 기반 promoted model 운영 문서화
Streamlit Dashboard 기반 Model Evaluation / Model Card 조회 구성
```

## 현재 완료된 범위

```text
샘플 채용공고 데이터 생성
Remote OK 외부 채용공고 수집 추가
크롤링 데이터 source / external_id / source_url 저장
크롤링 데이터 필터링 추가
PostgreSQL raw/cleaned/skills 테이블 저장
전처리 결과 기반 데이터 품질 체크 추가
데이터 품질 체크 결과 저장 테이블 추가
label_jobs.py weighted keyword scoring 개선
description / tags 기반 라벨링 개선
TF-IDF + Logistic Regression 모델 학습
MLflow PostgreSQL backend store 연동
MLflow artifact 저장
MLflow metric 기반 모델 성능 체크 추가
모델 성능 체크 결과 저장 테이블 추가
best model promotion 로직 추가
model_registry 테이블 추가
promoted model 기반 batch inference 추가
prediction lineage 저장 구조 추가
prediction quality 저장 구조 추가
FastAPI /predict API 구성
FastAPI /model API 추가
FastAPI /reload-model API 추가
FastAPI serving model 자동 reload 추가
Pipeline report 생성 추가
source별 데이터 품질 리포트 추가
pytest 단위 테스트 추가
Airflow 3.x Docker Compose 구성
Airflow DAG PythonOperator 전환
Airflow execution API / JWT 설정 이슈 해결
Airflow DAG 전체 실행 검증
Git history secret 제거
실행용 secret rotation
README 스크린샷 추가
포트폴리오용 README 보안 정리
DATA_SOURCE_MODE 기반 데이터 소스 모드 분리
prepare_raw_sources task 추가
sample_only / crawler_only / mixed 실행 모드 추가
Remote OK retry / fallback 처리 추가
crawler_only 학습 rare class 제외 처리 추가
api_prediction_logs 테이블 추가
FastAPI 요청/응답/실패/latency 로그 저장 추가
model_predictions prediction_source 추가
API / BATCH prediction 저장 구분 추가
batch inference BATCH row만 삭제 후 재생성하도록 개선
check_prediction_quality.py 추가
prediction quality gate DAG 추가
API quality / prediction quality 리포트 항목 추가
FK / SQL / INSERT 컬럼 불일치 트러블슈팅 정리
GitHub Actions 기반 pytest 자동 실행 workflow 추가
Ruff 기반 코드 품질 검사 추가
requirements-dev.txt / pyproject.toml 추가
포트폴리오용 sample pipeline report 추가
runtime report와 documentation sample 분리
Streamlit Dashboard 추가
Docker Compose dashboard 서비스 추가
Dashboard 스크린샷 docs/images/dashboard.png 추가
README에 Dashboard 실행 방법 / 접속 정보 / 스크린샷 반영
scripts/send_sample_api_requests.py 추가
FastAPI sample prediction request 검증 추가
smoke check에 API prediction log 저장 검증 추가
src/notification/notify_pipeline_status.py 추가
Pipeline Notification 메시지 생성 기능 추가
Slack Webhook 알림 옵션 추가
Makefile notify / api-sample 명령어 추가
src/maintenance/cleanup_old_records.py 추가
retention cleanup dry-run 기능 추가
API 로그 / API prediction / pipeline check 결과 보관 기간 환경변수 추가
src/quality/check_prediction_drift.py 추가
prediction distribution drift gate 추가
PREDICTION_DRIFT 결과 저장 추가
Airflow DAG에 check_prediction_drift task 추가
Makefile cleanup / drift-check 명령어 추가
src/monitoring/prometheus_metrics.py 추가
FastAPI /metrics 엔드포인트 추가
Prometheus Docker Compose 서비스 추가
monitoring/prometheus/prometheus.yml 추가
Grafana Docker Compose 서비스 추가
Grafana datasource / dashboard provisioning 추가
Grafana dashboard 스크린샷 docs/images/grafana.png 추가
Makefile metrics / prometheus / grafana 명령어 추가
smoke check에 metrics / Prometheus / Grafana 검증 추가
Prometheus alert rule 추가
monitoring/prometheus/rules/jobskill_alert_rules.yml 추가
Prometheus config rule_files / alertmanager target 추가
Makefile prometheus-check 명령어 추가
Alertmanager Docker Compose 서비스 추가
monitoring/alertmanager/alertmanager.yml 추가
Makefile alertmanager / alertmanager-check 명령어 추가
FastAPI /alertmanager/webhook endpoint 추가
alert_events 테이블 추가
alert_current_states 테이블 추가
Alertmanager firing/resolved 이벤트 DB 저장 추가
fingerprint 기준 current alert state upsert 추가
jobskill_alert_events_total 지표 추가
jobskill_alert_current_states_total 지표 추가
Streamlit Dashboard Alert History 탭 추가
Grafana Alert Events 패널 추가
smoke check에 Prometheus alert rules / Alertmanager / alert event 검증 추가
alert_acknowledgements 테이블 추가
alert_settings 테이블 추가
alert_silence_actions 테이블 추가
Streamlit Dashboard alert acknowledgement 기능 추가
MTTA / MTTR alert response metrics 추가
Alert response escalation rule 추가
Alert maintenance mode 추가
Alertmanager silence 생성 기능 추가
Incident response report 생성 기능 추가
Dashboard incident report view 추가
scripts/check_alert_workflow.sh 추가
Makefile incident-report / alert-workflow-check 명령어 추가
GitHub Actions Smoke Check에 alert workflow smoke check 추가
Makefile help 문구 및 validation command 정리
promoted model archive 기능 추가
model_promotion_archives 테이블 추가
scripts/archive_promoted_model.py 추가
Makefile model-archive 명령어 추가
promoted model rollback CLI 추가
model_rollback_actions 테이블 추가
scripts/rollback_promoted_model.py 추가
Makefile model-rollback-plan / model-rollback 명령어 추가
rollback dry-run plan과 archive id 기반 복구 흐름 추가
rollback 전 current best model backup 경로 추가
MLflow training dataset profile / dataset hash 저장 추가
MLflow classification report / confusion matrix / evaluation distribution artifact 저장 추가
class별 precision / recall / f1-score / support metric 저장 추가
check_model_class_performance.py 추가
MODEL_CLASS_PERFORMANCE 결과 저장 추가
Airflow DAG에 check_model_class_performance task 추가
generate_model_card.py 추가
reports/latest_model_card.md 생성 기능 추가
Airflow DAG에 generate_model_card task 추가
Streamlit Dashboard Model Evaluation 탭 추가
Streamlit Dashboard Model Card 탭 추가
Makefile model-class-performance-check / model-card 명령어 추가
```


## 오늘 작업 요약

```text
Docker Compose DB 역할 분리
DB_*는 jobskill application DB 전용으로 정리
AIRFLOW_DB_*는 Airflow metadata DB 전용으로 추가
Airflow SQL_ALCHEMY_CONN을 airflow 전용 계정/DB 기준으로 정리
MLflow backend-store-uri를 MLFLOW_TRACKING_URI 기준으로 정리
Dashboard 컨테이너의 reports / mlartifacts / scripts mount 정리
Airflow apiserver의 postgres DNS resolution 문제와 DB password authentication 문제 원인 분리
Postgres volume 내부 airflow role password와 .env 설정 불일치 원인 확인
PostgreSQL init SQL 중복 실행으로 database "airflow" already exists 오류 발생 원인 확인
docker/postgres/init을 01-init-databases.sql 단일 파일 구조로 정리
airflow role / airflow DB / mlflow DB 생성과 owner/privilege 설정을 init SQL에 통합
docker compose down -v 기반 로컬 DB 초기화 절차 정리
data / models / mlartifacts / reports / airflow_logs 재생성 및 권한/ACL 정리 절차 정리
Airflow metadata DB migrate 및 airflow db check 정상화
Airflow 기동 후 MLflow / FastAPI / Dashboard / Alertmanager / Prometheus / Grafana 순차 기동 절차 정리
.secrets/slack_webhook_url 기반 Alertmanager Slack receiver 설정 확인
Alertmanager direct alert API로 Slack 알림 수신 테스트 완료
Alertmanager → Slack notification 경로 정상 확인
README에 Docker Compose DB 분리, Postgres 초기화/복구, Alertmanager Slack 알림 검증 절차 반영
```

## 다음 개선 예정

```text
Repository Artifact Guard 추가
mlartifacts / models / data / airflow_logs / generated reports가 Git에 포함되지 않도록 자동 검증
Model Card Consistency Check 고도화
Model Card title, run_id, model_registry_id, dataset hash, evaluation artifact section 정합성 검증
Notification Channel Health Check 추가
Slack webhook file 존재 여부, Alertmanager receiver 설정, direct alert API 테스트를 자동 검증
Data Contract Dashboard 추가
Streamlit Dashboard에서 DATA_CONTRACT 결과 조회 / 실패 항목 drill-down 제공
Model Evaluation Dashboard에 기간 필터와 run_id 선택 기능 추가
Model Evaluation Dashboard에서 MLflow evaluation artifact 직접 미리보기
Model Card Dashboard에서 read-only 모드와 generate 모드 분리
Postgres reset / bootstrap 절차를 Makefile 명령어로 표준화
Alert History / Current Alerts 필터와 기간 조건 추가
alert_events / alert_acknowledgements / alert_silence_actions retention cleanup 정책 추가
Incident Response Report를 Airflow DAG 또는 정기 리포트로 자동 생성
Airflow DAG params 기반 DATA_SOURCE_MODE 선택 실행 개선
Airflow task retry / timeout / failure callback 정책 정리
prediction drift 결과를 dashboard에 별도 chart로 시각화
cleanup 결과를 pipeline report 또는 notification에 포함
크롤링 source 추가 또는 수집 데이터 다양화
모델 성능 개선을 위한 데이터 라벨링/피처 개선
```
