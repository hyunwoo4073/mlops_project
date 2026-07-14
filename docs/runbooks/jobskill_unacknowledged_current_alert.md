# JobSkillUnacknowledgedCurrentAlert

## 의미

현재 firing 상태인 alert 중 acknowledgement가 저장되지 않은 alert가 존재합니다.

즉, Alertmanager가 alert를 수신했고 Slack 또는 Dashboard에서 확인 가능한 상태지만, 운영자가 Streamlit Dashboard에서 확인자와 조치 메모를 남기지 않은 상태입니다.

## 영향

- 실제 장애 또는 품질 저하 alert가 운영자 확인 없이 방치될 수 있습니다.
- Alert 대응 이력과 MTTA 계산이 누락될 수 있습니다.
- 포트폴리오 관점에서는 alert lifecycle이 firing/resolved까지만 남고, 운영 대응 기록이 비어 있게 됩니다.

## 확인 위치

Streamlit Dashboard:

```text
http://localhost:8501
```

확인 탭:

```text
Current Alerts
→ Firing Alerts
→ Acknowledge Alert
→ Recent Acknowledgements
```

Prometheus Alerts:

```text
http://localhost:9090/alerts
```

## DB 확인

현재 firing alert 확인:

```sql
SELECT
    fingerprint,
    status,
    alert_name,
    severity,
    service,
    summary,
    updated_at
FROM alert_current_states
WHERE status = 'firing'
ORDER BY updated_at DESC;
```

acknowledgement 없는 firing alert 확인:

```sql
SELECT
    cs.fingerprint,
    cs.alert_name,
    cs.severity,
    cs.service,
    cs.status,
    cs.summary,
    cs.updated_at
FROM alert_current_states cs
LEFT JOIN alert_acknowledgements aa
    ON cs.fingerprint = aa.fingerprint
WHERE cs.status = 'firing'
  AND aa.id IS NULL
ORDER BY cs.updated_at DESC;
```

최근 acknowledgement 확인:

```sql
SELECT
    id,
    alert_name,
    severity,
    service,
    status,
    acknowledged_by,
    note,
    created_at
FROM alert_acknowledgements
ORDER BY id DESC
LIMIT 20;
```

## 주요 원인

- Slack 알림은 확인했지만 Streamlit Dashboard에서 acknowledgement를 저장하지 않음
- 테스트 alert를 수동으로 발생시킨 뒤 확인 이력을 남기지 않음
- 실제 firing alert가 장시간 유지되고 있음
- Alertmanager resolved 이벤트가 아직 들어오지 않음
- acknowledgement 저장 테이블 생성이 누락됨

## 조치

1. Streamlit Dashboard에 접속합니다.

```text
http://localhost:8501
```

2. `Current Alerts` 탭으로 이동합니다.

3. `Firing Alerts` 목록에서 현재 firing alert를 확인합니다.

4. `Acknowledge Alert` 영역에서 대상 alert를 선택합니다.

5. 확인자와 조치 메모를 입력합니다.

예시:

```text
API low confidence alert 확인.
샘플 API 테스트 요청으로 인해 low confidence ratio가 높게 측정됨.
alert threshold 조정 또는 테스트 데이터 정리 예정.
```

6. `Save acknowledgement` 버튼을 클릭합니다.

7. `Recent Acknowledgements`에 기록이 추가됐는지 확인합니다.

8. Prometheus에서 `JobSkillUnacknowledgedCurrentAlert`가 resolved 되는지 확인합니다.

## 관련 명령어

acknowledgement 없는 firing alert 확인:

```bash
docker compose exec postgres psql -U jobskill -d jobskill -c "
SELECT
    cs.alert_name,
    cs.severity,
    cs.service,
    cs.status,
    cs.updated_at
FROM alert_current_states cs
LEFT JOIN alert_acknowledgements aa
    ON cs.fingerprint = aa.fingerprint
WHERE cs.status = 'firing'
  AND aa.id IS NULL
ORDER BY cs.updated_at DESC;
"
```

metrics 확인:

```bash
curl -fsS http://localhost:8000/metrics | grep jobskill_alert_unacknowledged_current_total
```
