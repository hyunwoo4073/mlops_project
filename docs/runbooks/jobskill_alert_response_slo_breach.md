# JobSkillAlertResponseSloBreach

## 의미

Alert response metric이 기준보다 나빠진 상태입니다.

현재 사용하는 기준은 다음과 같습니다.

```text
Average MTTA > 10 minutes
Average MTTR > 30 minutes
```

MTTA는 alert firing 시점부터 acknowledgement 저장 시점까지 걸린 시간입니다.

MTTR은 alert firing 시점부터 resolved 이벤트 수신 시점까지 걸린 시간입니다.

## 영향

- alert가 발생해도 운영자가 늦게 확인하고 있을 수 있습니다.
- alert가 해소되기까지 시간이 오래 걸리고 있을 수 있습니다.
- 반복적인 품질 저하, API 장애, pipeline failure 등이 장시간 방치될 수 있습니다.
- 운영 대응 품질을 보여주는 Grafana/Streamlit 지표가 악화됩니다.

## 확인 위치

Streamlit Dashboard:

```text
http://localhost:8501
```

확인 탭:

```text
Alert History
→ Alert Response Metrics
→ Recent Alert Response Details
```

Grafana Dashboard:

```text
http://localhost:3000
```

Prometheus:

```text
http://localhost:9090/graph
```

확인할 Prometheus query:

```text
jobskill_alert_avg_mtta_minutes
jobskill_alert_avg_mttr_minutes
jobskill_alert_acknowledgements_total
jobskill_alert_unacknowledged_current_total
```

## DB 확인

alert response 상세 확인:

```sql
WITH firing_alerts AS (
    SELECT
        fingerprint,
        COALESCE(alert_name, 'unknown') AS alert_name,
        COALESCE(severity, 'unknown') AS severity,
        COALESCE(service, 'unknown') AS service,
        MIN(COALESCE(starts_at, created_at)) AS first_fired_at
    FROM alert_events
    WHERE status = 'firing'
      AND fingerprint IS NOT NULL
    GROUP BY
        fingerprint,
        COALESCE(alert_name, 'unknown'),
        COALESCE(severity, 'unknown'),
        COALESCE(service, 'unknown')
),
first_acknowledgements AS (
    SELECT
        fingerprint,
        MIN(created_at) AS first_acknowledged_at
    FROM alert_acknowledgements
    WHERE fingerprint IS NOT NULL
    GROUP BY fingerprint
),
resolved_alerts AS (
    SELECT
        fingerprint,
        MIN(COALESCE(ends_at, created_at)) AS first_resolved_at
    FROM alert_events
    WHERE status = 'resolved'
      AND fingerprint IS NOT NULL
    GROUP BY fingerprint
)
SELECT
    f.alert_name,
    f.severity,
    f.service,
    f.first_fired_at,
    a.first_acknowledged_at,
    r.first_resolved_at,
    ROUND(
        (
            EXTRACT(EPOCH FROM (a.first_acknowledged_at - f.first_fired_at)) / 60
        )::numeric,
        2
    ) AS mtta_minutes,
    ROUND(
        (
            EXTRACT(EPOCH FROM (r.first_resolved_at - f.first_fired_at)) / 60
        )::numeric,
        2
    ) AS mttr_minutes
FROM firing_alerts f
LEFT JOIN first_acknowledgements a
    ON f.fingerprint = a.fingerprint
LEFT JOIN resolved_alerts r
    ON f.fingerprint = r.fingerprint
ORDER BY f.first_fired_at DESC
LIMIT 20;
```

## 주요 원인

- firing alert를 Dashboard에서 늦게 acknowledgement 처리함
- 테스트 alert를 발생시켜놓고 acknowledgement를 나중에 저장함
- resolved 이벤트가 늦게 들어옴
- 실제 장애 또는 품질 저하가 오래 지속됨
- Alertmanager 또는 Prometheus 재기동으로 alert lifecycle이 예상보다 길게 기록됨
- 오래된 테스트 alert 기록이 평균값에 영향을 줌

## 조치

1. Streamlit Dashboard에서 `Alert History` 탭을 확인합니다.

2. `Alert Response Metrics` 영역에서 MTTA/MTTR이 높은 alert를 확인합니다.

3. `Recent Alert Response Details`에서 어떤 alert가 평균을 끌어올리는지 확인합니다.

4. 실제 장애라면 해당 alert의 Runbook에 따라 원인을 조치합니다.

5. 테스트 alert 때문에 지표가 오염된 경우에는 테스트 데이터 여부를 구분합니다.

6. 필요하다면 response SLO 기준을 조정합니다.

현재 Prometheus rule 기준:

```text
Average MTTA > 10 minutes
Average MTTR > 30 minutes
```

기준 조정 위치:

```text
monitoring/prometheus/rules/jobskill_alert_rules.yml
```

## 관련 명령어

metrics 확인:

```bash
curl -fsS http://localhost:8000/metrics | grep -E "mtta|mttr|acknowledgements|unacknowledged"
```

Prometheus query 확인:

```bash
curl -fsS 'http://localhost:9090/api/v1/query?query=jobskill_alert_avg_mtta_minutes'
curl -fsS 'http://localhost:9090/api/v1/query?query=jobskill_alert_avg_mttr_minutes'
```
