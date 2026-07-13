# JobSkillApiHighLatency

## 의미

FastAPI prediction 요청 평균 latency가 기준보다 높은 상태입니다.

## 영향

- API 응답 지연
- 사용자 요청 처리 성능 저하
- 모델 로딩 또는 DB 저장 병목 가능성
- 컨테이너 리소스 부족 가능성

## 확인 명령어

```bash
curl -fsS http://localhost:8000/metrics | grep jobskill_api_prediction_avg_latency_ms
curl -fsS 'http://localhost:9090/api/v1/query?query=jobskill_api_prediction_avg_latency_ms'
docker compose logs --tail=100 api
```

## DB 확인

```sql
SELECT
    status,
    COUNT(*) AS request_count,
    ROUND(AVG(latency_ms)::numeric, 2) AS avg_latency_ms,
    ROUND(MAX(latency_ms)::numeric, 2) AS max_latency_ms
FROM api_prediction_logs
GROUP BY status
ORDER BY status;
```

최근 느린 요청 확인:

```sql
SELECT
    id,
    request_title,
    response_category,
    status,
    ROUND(latency_ms::numeric, 2) AS latency_ms,
    created_at
FROM api_prediction_logs
ORDER BY latency_ms DESC
LIMIT 20;
```

## 주요 원인

- 모델 reload 반복
- PostgreSQL insert 지연
- 컨테이너 리소스 부족
- 동시 요청 증가
- DB connection 문제

## 조치

```bash
docker compose logs --tail=200 api
docker compose ps api postgres
docker stats
```

필요 시 API 컨테이너를 재기동합니다.

```bash
docker compose up -d --force-recreate api
```
