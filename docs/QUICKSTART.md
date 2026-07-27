# JobSkill MLOps Quick Start

이 문서는 `jobskill-mlops` 프로젝트를 처음 실행하거나 초기화 후 다시 띄울 때 따라 하기 위한 실행 가이드입니다.

## 0. 문서 구조

```text
README.md
- 상세 구현 기록과 전체 설명

docs/README_SUMMARY.md
- 프로젝트 요약과 핵심 기능 파악

docs/QUICKSTART.md
- 로컬 실행, 검증, 알림 테스트 순서
```

## 1. 사전 준비

필요한 도구:

```text
Docker
Docker Compose
Python 3.12 권장
make
curl
jq
```

프로젝트 루트로 이동:

```bash
cd ~/jobskill-mlops
```

## 2. Secret 파일 준비

Slack 알림을 테스트하려면 `.secrets/slack_webhook_url` 파일이 필요합니다.

```bash
mkdir -p .secrets
vi .secrets/slack_webhook_url
```

파일에는 Slack Incoming Webhook URL만 한 줄로 넣습니다.

```text
https://hooks.slack.com/services/...
```

비어 있는 placeholder만 필요하면:

```bash
mkdir -p .secrets
touch .secrets/slack_webhook_url
```

Airflow simple auth password 파일이 필요한 경우:

```bash
cat > simple_auth_manager_passwords.json <<'EOF'
{
  "airflow": "airflow"
}
EOF
```

## 3. 로컬 산출물 디렉터리 준비

```bash
mkdir -p   data   models/best   mlartifacts   reports/model_cards   airflow_logs
```

권한 정리:

```bash
sudo chown -R "$USER":0   data   models   mlartifacts   reports   airflow_logs

sudo chmod -R u+rwX,g+rwX   data   models   mlartifacts   reports   airflow_logs
```

Airflow 컨테이너 UID가 `50000`이면 ACL도 부여합니다.

```bash
sudo setfacl -R -m u:50000:rwX,u:$(id -u):rwX   data   models   mlartifacts   reports   airflow_logs

sudo setfacl -R -d -m u:50000:rwX,u:$(id -u):rwX   data   models   mlartifacts   reports   airflow_logs
```

## 4. 완전 초기화가 필요한 경우

기존 Docker volume과 로컬 runtime artifact를 지우고 처음부터 시작합니다.

```bash
docker compose down -v --remove-orphans

sudo rm -rf   data   models   mlartifacts   reports   airflow_logs

mkdir -p   data   models/best   mlartifacts   reports/model_cards   airflow_logs
```

주의:

```text
data/
models/
mlartifacts/
reports/
airflow_logs/
Docker volume
```

위 항목은 삭제됩니다.

## 5. 이미지 빌드

```bash
docker compose build --no-cache airflow-image api
```

또는 Makefile을 사용합니다.

```bash
make build
```

## 6. PostgreSQL 먼저 기동

```bash
docker compose up -d postgres
```

로그 확인:

```bash
docker compose logs -f postgres
```

정상 메시지:

```text
database system is ready to accept connections
```

DB 생성 확인:

```bash
docker compose exec postgres psql -U jobskill -d postgres -c "
SELECT datname
FROM pg_database
ORDER BY datname;
"
```

아래 DB가 있어야 합니다.

```text
airflow
jobskill
mlflow
```

Airflow DB 접속 확인:

```bash
docker compose exec postgres psql   "postgresql://airflow:airflow@localhost:5432/airflow"   -c "SELECT current_user, current_database();"
```

## 7. Airflow metadata DB migrate

```bash
docker compose run --rm airflow-init
```

Airflow 서비스 기동:

```bash
docker compose up -d   airflow-apiserver   airflow-scheduler   airflow-dag-processor   airflow-triggerer
```

확인:

```bash
docker compose exec airflow-apiserver bash -lc 'airflow db check'
docker compose exec airflow-scheduler bash -lc 'airflow dags list-import-errors'
```

## 8. 나머지 서비스 기동

```bash
docker compose up -d   mlflow   api   dashboard   alertmanager   prometheus   grafana
```

전체 상태 확인:

```bash
docker compose ps
```

## 9. 서비스 접속 정보

```text
Airflow      : http://localhost:8080
MLflow       : http://localhost:5000
FastAPI      : http://localhost:8000
Streamlit    : http://localhost:8501
Prometheus   : http://localhost:9090
Alertmanager : http://localhost:9093
Grafana      : http://localhost:3000
```

## 10. API 상태 확인

```bash
curl -fsS http://localhost:8000/health | jq
curl -fsS http://localhost:8000/ready | jq
```

초기화 직후에는 promoted model이 없어서 `/ready`가 실패할 수 있습니다. 이 경우 모델 학습과 promotion을 먼저 실행합니다.

## 11. 최소 파이프라인 수동 실행

Airflow DAG를 쓰기 전에 수동으로 한 번 실행해 기능을 확인할 수 있습니다.

```bash
docker compose exec airflow-scheduler bash -lc "
cd /opt/airflow/project &&

python src/data/generate_sample_jobs.py &&
python src/data/load_raw_jobs.py &&
python src/preprocessing/preprocess_jobs.py &&

python src/quality/check_data_contract.py &&
python src/quality/check_training_data.py &&

python src/training/train_baseline.py &&
python src/quality/check_model_performance.py &&
python src/quality/check_model_class_performance.py &&
python src/training/promote_model.py &&

python src/reporting/generate_model_card.py
"
```

그 다음 API readiness 확인:

```bash
curl -fsS http://localhost:8000/ready | jq
```

## 12. 샘플 API 요청

```bash
make api-sample
```

확인:

```bash
docker compose exec postgres psql -U jobskill -d jobskill -c "
SELECT prediction_source, COUNT(*)
FROM model_predictions
GROUP BY prediction_source;
"
```

## 13. Metrics 확인

FastAPI metric:

```bash
curl -fsS http://localhost:8000/metrics | head -50
```

Alertmanager metric:

```bash
curl -fsS http://localhost:9093/metrics | grep alertmanager_notifications_failed_total
```

Prometheus query:

```bash
curl -G "http://localhost:9090/api/v1/query"   --data-urlencode 'query=alertmanager_notifications_failed_total' | jq
```

## 14. 운영 검증 명령

Runbook coverage:

```bash
make runbook-check
```

Metrics contract:

```bash
make metrics-contract-check
```

Alert rule metric dependency:

```bash
make alert-rule-metric-check
```

Prometheus rule test:

```bash
make prometheus-rule-test
```

전체 운영 검증:

```bash
make ops-check
```

## 15. Alertmanager Slack 알림 테스트

Alertmanager에 직접 테스트 alert를 보냅니다.

```bash
curl -XPOST http://localhost:9093/api/v2/alerts   -H "Content-Type: application/json"   -d '[
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
```

Slack에 알림이 도착하면 Alertmanager → Slack 경로가 정상입니다.

## 16. Alertmanager Notification Failure 테스트

Slack webhook을 임시로 잘못된 값으로 바꾸면 Alertmanager notification failure metric이 증가해야 합니다.

백업:

```bash
cp .secrets/slack_webhook_url /tmp/slack_webhook_url.backup
```

실패 유도:

```bash
echo "https://hooks.slack.com/services/broken/test/url" > .secrets/slack_webhook_url
docker compose up -d --force-recreate alertmanager
```

테스트 alert 전송:

```bash
curl -XPOST http://localhost:9093/api/v2/alerts   -H "Content-Type: application/json"   -d '[
    {
      "labels": {
        "alertname": "JobSkillSlackFailureTest",
        "severity": "warning",
        "service": "jobskill-mlops",
        "source": "manual-test"
      },
      "annotations": {
        "summary": "Slack failure test",
        "description": "This alert should make Alertmanager Slack notification fail."
      },
      "startsAt": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
    }
  ]'
```

Metric 확인:

```bash
curl -fsS http://localhost:9093/metrics | grep alertmanager_notifications_failed_total
```

Prometheus alert 확인:

```bash
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname=="JobSkillAlertmanagerNotificationFailure")'
```

복구:

```bash
cp /tmp/slack_webhook_url.backup .secrets/slack_webhook_url
docker compose up -d --force-recreate alertmanager
```

## 17. 자주 보는 Makefile 명령

```bash
make build
make up
make ps
make dag-errors
make api-sample
make metrics
make runbook-check
make metrics-contract-check
make alert-rule-metric-check
make prometheus-rule-test
make ops-check
make dashboard
```

## 18. Git에 올리면 안 되는 것

```text
.env
.secrets/
simple_auth_manager_passwords.json
data/
models/
mlartifacts/
airflow_logs/
reports/latest_model_card.md
reports/model_cards/
```

커밋 전 확인:

```bash
git status --short
```

## 19. 문제 해결 힌트

### `/ready` 실패

```text
PROMOTED model_registry 없음
models/best/job_classifier.pkl 없음
```

모델 학습과 promotion을 먼저 실행합니다.

### `metrics-contract-check`에서 metric missing

```text
값이 0인 metric과 metric이 없는 것은 다릅니다.
required metric은 DB row가 없어도 0으로 노출되어야 합니다.
```

확인:

```bash
curl -fsS http://localhost:8000/metrics | grep <metric_name>
```

### `alert-rule-metric-check`에서 receiver/integration missing

`receiver`, `integration`은 metric이 아니라 PromQL grouping label입니다.  
checker에서 `by (...)` 안의 label을 metric으로 오인하지 않도록 parser가 수정되어 있어야 합니다.

### Alertmanager Slack 알림이 안 옴

```bash
docker compose logs --tail=200 alertmanager
docker compose exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
cat .secrets/slack_webhook_url
```

## 20. 추천 검증 순서

처음 실행 또는 초기화 후에는 아래 순서로 확인합니다.

```bash
docker compose ps
curl -fsS http://localhost:8000/health | jq
curl -fsS http://localhost:8000/ready | jq
make api-sample
make runbook-check
make metrics-contract-check
make alert-rule-metric-check
make prometheus-rule-test
make ops-check
```
