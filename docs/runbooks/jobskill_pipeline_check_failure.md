# JobSkillPipelineCheckFailure

## 의미

최근 1시간 내 pipeline check 결과 중 실패가 발생한 상태입니다.

## 영향

- 데이터 품질, 모델 성능, prediction quality, drift 중 하나 이상 기준 미달
- DAG 산출물 신뢰도 저하 가능성
- 모델 promotion 또는 report 결과 확인 필요

## 확인 명령어

```bash
curl -fsS http://localhost:8000/metrics | grep jobskill_pipeline_recent_failed_checks_total
curl -fsS 'http://localhost:9090/api/v1/query?query=jobskill_pipeline_recent_failed_checks_total'
```

## DB 확인

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
WHERE UPPER(status) NOT IN ('PASS', 'SUCCESS')
ORDER BY checked_at DESC
LIMIT 20;
```

최근 check 전체 확인:

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
ORDER BY checked_at DESC
LIMIT 30;
```

## 주요 원인

- 학습 데이터 부족
- Unknown 라벨 비율 증가
- 모델 성능 기준 미달
- prediction confidence 저하
- prediction distribution drift 발생
- 외부 수집 데이터 품질 저하

## 조치

```bash
make report
make dag-errors
make dag-tasks
```

필요 시 DAG를 다시 실행합니다.

```bash
make dag-trigger
```
