# JobSkillApiMetricsDown

## 의미

Prometheus가 FastAPI `/metrics` endpoint를 scrape하지 못하는 상태입니다.

## 영향

- Prometheus metrics 수집 중단
- Grafana dashboard 값 갱신 중단
- alert rule 평가 부정확 가능성
- FastAPI 또는 PostgreSQL 연결 문제 가능성

## 확인 명령어

```bash
docker compose ps api prometheus
curl -fsS http://localhost:8000/metrics | head
curl -fsS http://localhost:9090/-/ready
curl -fsS 'http://localhost:9090/api/v1/query?query=up%7Bjob%3D%22jobskill-api%22%7D'
docker compose logs --tail=100 api
docker compose logs --tail=100 prometheus
```

## DB 확인

```bash
docker compose ps postgres
docker compose logs --tail=100 postgres
```

## 주요 원인

- FastAPI 컨테이너 중지
- FastAPI `/metrics` endpoint 오류
- PostgreSQL 연결 실패로 `/metrics` 생성 실패
- Prometheus scrape 설정 오류
- Docker Compose network 문제

## 조치

```bash
docker compose up -d api prometheus
docker compose logs --tail=200 api
docker compose logs --tail=200 prometheus
```

FastAPI가 DB 연결 오류로 실패하면 PostgreSQL 상태를 먼저 확인합니다.

```bash
docker compose up -d postgres
docker compose logs --tail=200 postgres
```
