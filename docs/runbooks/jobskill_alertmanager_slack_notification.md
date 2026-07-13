# JobSkill Alertmanager Slack Notification

## 의미

Alertmanager가 Prometheus alert를 수신한 뒤 Slack Incoming Webhook으로 알림을 전송하는 경로입니다.

## 영향

- Slack 알림 실패 시 운영자가 alert를 즉시 인지하지 못할 수 있음
- Alertmanager UI / Streamlit / Grafana에서는 alert가 보이지만 Slack에는 오지 않을 수 있음

## 확인 명령어

Alertmanager 상태 확인:

```bash
docker compose ps alertmanager
curl -fsS http://localhost:9093/-/ready
docker compose logs --tail=200 alertmanager
```

Slack webhook secret 파일 확인:

```bash
docker compose exec alertmanager sh -lc '
ls -l /etc/alertmanager/alertmanager.yml
ls -l /etc/alertmanager/secrets/slack_webhook_url
wc -c /etc/alertmanager/secrets/slack_webhook_url
'
```

Alertmanager 설정 확인:

```bash
docker compose exec alertmanager sh -lc '
grep -n "slack_configs\|api_url_file\|webhook_configs" /etc/alertmanager/alertmanager.yml
'
```

## Slack webhook 직접 테스트

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  --data '{"text":"JobSkill Slack webhook direct test"}' \
  "$(cat .secrets/slack_webhook_url)"
```

정상 응답:

```text
ok
```

## Alertmanager direct alert 테스트

```bash
curl -X POST "http://localhost:9093/api/v2/alerts" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "labels": {
        "alertname": "JobSkillSlackRunbookTest",
        "severity": "warning",
        "service": "slack-test",
        "instance": "manual"
      },
      "annotations": {
        "summary": "Slack runbook test alert",
        "description": "Testing Slack notification path from Alertmanager.",
        "runbook_url": "docs/runbooks/jobskill_alertmanager_slack_notification.md",
        "dashboard_url": "http://localhost:3000",
        "prometheus_url": "http://localhost:9090/alerts"
      },
      "startsAt": "2026-07-10T00:00:00Z"
    }
  ]'
```

## 주요 원인

- `.secrets/slack_webhook_url` 파일 없음
- `slack_webhook_url` 파일 권한 문제
- Alertmanager 컨테이너에 secret 파일 mount 누락
- `alertmanager.yml`에 `slack_configs` 누락
- Slack webhook URL 폐기 또는 오타
- Slack channel override 문제
- 기존 firing alert의 `repeat_interval` 대기

## 조치

secret 파일 권한 확인:

```bash
chmod 644 .secrets/slack_webhook_url
```

Alertmanager 재기동:

```bash
docker compose up -d --force-recreate alertmanager
```

로그 확인:

```bash
docker compose logs --tail=300 alertmanager | grep -iE "slack|notify|error|fail|permission|channel|auth|webhook"
```

Slack Incoming Webhook이 특정 채널에 고정되어 있으면 `channel:` 설정을 제거하고 테스트합니다.
