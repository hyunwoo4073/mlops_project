# JobSkill Training Duration High

## 의미

`JobSkillTrainingDurationHigh` alert는 최근 baseline model full retrain 시간이 설정한 기준보다 길어졌다는 의미입니다.

이 alert는 모델 성능 장애라기보다, 데이터 증가에 따라 full retrain 비용이 운영 기준을 초과하기 시작했다는 신호입니다.

## Alert 조건

```text
jobskill_alert_maintenance_mode == 0
and
jobskill_training_duration_threshold_seconds > 0
and
jobskill_training_duration_seconds > jobskill_training_duration_threshold_seconds
```

## 주요 Metric

```text
jobskill_training_duration_seconds
jobskill_training_duration_threshold_seconds
jobskill_training_rows
jobskill_training_category_count
jobskill_training_throughput_rows_per_second
jobskill_training_model_size_bytes
jobskill_training_incremental_experiment_by_duration
```

## 1차 확인

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_training_"
```

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    check_type,
    check_name,
    status,
    metric_value,
    threshold_value,
    message,
    run_id,
    checked_at
FROM pipeline_check_results
WHERE check_type = 'TRAINING_COST'
ORDER BY checked_at DESC, check_name
LIMIT 30;
"
```

## 리포트 확인

```bash
make training-cost-report
cat reports/latest_training_cost_report.md
```

## 판단 기준

```text
training_duration_seconds가 기준 이하
- full retrain 유지

training_duration_seconds가 기준 초과
- window retrain 검토
- recent + historical sampling retrain 검토

training_incremental_experiment_by_duration = 1
- incremental retraining shadow experiment 검토
```

## 대응 절차

1. 최근 학습 row 수와 학습 시간을 확인합니다.
2. `reports/latest_training_cost_report.md`에서 추세를 확인합니다.
3. `reports/latest_retraining_strategy_report.md`에서 window/sampling 가능 여부를 확인합니다.
4. 데이터가 급증한 경우 source별 데이터 유입량을 확인합니다.
5. 현재 운영 모델은 즉시 교체하지 않고 full retrain 유지 여부를 먼저 판단합니다.
6. 기준 초과가 반복되면 window retrain 또는 sampling retrain 개선으로 넘어갑니다.
7. 학습 시간이 incremental 기준까지 도달하면 incremental retraining은 shadow experiment로만 검토합니다.

## 관련 명령어

```bash
make retraining-strategy-check
make retraining-strategy-report
make training-cost-report
make ops-report
make ops-evidence-bundle
make ops-evidence-check
```

## 주의사항

```text
이 alert는 모델 예측 품질 저하를 직접 의미하지 않습니다.
학습 비용 증가에 대한 운영 경고입니다.
현재 모델 promotion 정책을 즉시 바꾸지 말고, report와 validation 결과를 함께 확인해야 합니다.
```

