# JobSkill Alertmanager Notification Failure

## 의미

Alertmanager가 Slack 또는 다른 notification receiver로 알림을 전송하는 과정에서 실패가 발생했습니다.

이 alert는 Prometheus가 Alertmanager 자체 metric인 `alertmanager_notifications_failed_total`을 수집하고, 최근 5분 동안 notification failure counter가 증가했을 때 발생합니다.

## 영향

Prometheus alert rule은 firing 되었지만 운영자가 Slack에서 알림을 받지 못할 수 있습니다.

영향 범위:

```text
Prometheus alert rule 평가 정상
Alertmanager alert 수신 가능
FastAPI webhook 저장 가능
Slack notification 전송 실패 가능
운영자 실시간 인지 지연 가능
```

## 확인 명령어

Alertmanager 상태 확인:

```bash
curl -fsS http://localhost:9093/api/v2/status | jq
```

Alertmanager notification failure metric 확인:

```bash
curl -fsS http://localhost:9093/metrics | grep alertmanager_notifications_failed_total
```

Prometheus query 확인:

```bash
curl -G "http://localhost:9090/api/v1/query" \
  --data-urlencode 'query=increase(alertmanager_notifications_failed_total[5m])' | jq
```

Alertmanager 로그 확인:

```bash
docker compose logs --tail=200 alertmanager
```

Slack webhook secret 파일 확인:

```bash
ls -l .secrets/slack_webhook_url
wc -c .secrets/slack_webhook_url
```

컨테이너 내부 secret mount 확인:

```bash
docker compose exec alertmanager sh -lc "
ls -l /etc/alertmanager/secrets/slack_webhook_url &&
wc -c /etc/alertmanager/secrets/slack_webhook_url
"
```

Alertmanager 설정 확인:

```bash
docker compose exec alertmanager cat /etc/alertmanager/alertmanager.yml
```

Alertmanager 설정 문법 확인:

```bash
docker compose exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
```

## DB 확인

Alertmanager가 FastAPI webhook에는 정상 전달했는지 확인합니다.

```bash
docker compose exec postgres psql -U jobskill -d jobskill -c "
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
"
```

현재 alert 상태 확인:

```bash
docker compose exec postgres psql -U jobskill -d jobskill -c "
SELECT
    status,
    alert_name,
    severity,
    service,
    updated_at
FROM alert_current_states
ORDER BY updated_at DESC
LIMIT 20;
"
```

## 주요 원인

```text
Slack webhook URL 누락
Slack webhook URL 오타
Slack webhook secret 파일이 비어 있음
Alertmanager receiver 설정 오류
api_url_file 경로 오류
Slack webhook 폐기 또는 권한 문제
Slack API 일시 장애
Alertmanager 컨테이너에서 secret 파일 mount 실패
```

## 조치

### 1. Slack webhook secret 파일 확인

```bash
cat .secrets/slack_webhook_url
```

파일이 비어 있으면 Slack Incoming Webhook URL을 다시 입력합니다.

```bash
vi .secrets/slack_webhook_url
```

### 2. Alertmanager 컨테이너에 secret 파일이 mount되었는지 확인

```bash
docker compose exec alertmanager sh -lc "
cat /etc/alertmanager/secrets/slack_webhook_url
"
```

### 3. Alertmanager 설정 검증

```bash
docker compose exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
```

### 4. Alertmanager 재기동

```bash
docker compose up -d --force-recreate alertmanager
```

### 5. 수동 테스트 alert 전송

```bash
curl -XPOST http://localhost:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  -d '[
    {
      "labels": {
        "alertname": "JobSkillAlertmanagerNotificationFailureTest",
        "severity": "warning",
        "service": "alertmanager",
        "source": "manual-test"
      },
      "annotations": {
        "summary": "Alertmanager notification failure recovery test",
        "description": "Manual Slack notification path test after recovery."
      },
      "startsAt": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
    }
  ]'
```

### 6. Slack 수신 확인

Slack 채널에 테스트 알림이 도착하면 복구된 것으로 판단합니다.

## 복구 확인

Alertmanager notification failure counter 증가가 멈췄는지 확인합니다.

```bash
curl -G "http://localhost:9090/api/v1/query" \
  --data-urlencode 'query=increase(alertmanager_notifications_failed_total[5m])' | jq
```

결과가 `0`이면 최근 5분 동안 notification failure가 없는 상태입니다.

## 예방

```text
.secrets/slack_webhook_url를 Git에 커밋하지 않음
.secrets.example/slack_webhook_url.example만 제공
Alertmanager config 변경 후 amtool check-config 실행
Prometheus rule 변경 후 promtool check rules 실행
notification failure metric을 Prometheus에서 지속 감시
```
