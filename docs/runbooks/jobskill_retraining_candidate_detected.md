# JobSkill 재학습 후보 감지 Runbook

## 1. Alert 개요

대상 Alert:

- `JobSkillRetrainingCandidateDetected`

이 Alert는 Production Feedback 기반 판단 결과 현재 promoted model이 재학습 후보로 분류되었을 때 발생한다.

Alert 조건:

```text
jobskill_alert_maintenance_mode == 0
and
jobskill_retraining_candidate_flag == 1
```

즉, 점검 모드가 아니고 최신 재학습 후보 판단 결과가 `candidate` 상태이면 Alert가 발생한다.

## 2. 의미

이 Alert는 모델이 즉시 장애 상태라는 의미가 아니라, 운영 feedback 기준으로 현재 모델을 재학습 또는 롤백 후보로 검토해야 한다는 의미다.

재학습 후보 판단에는 일반적으로 아래 신호가 포함된다.

- Production Feedback 수가 충분히 쌓임
- 최신 Production Accuracy가 기준보다 낮음
- 최신 Weighted F1이 기준보다 낮음
- 최근 평가 이력에서 Accuracy 또는 Weighted F1이 하락 추세
- 오분류가 특정 actual/predicted 조합에 집중됨
- Dashboard에서 저장한 `RETRAINING_CANDIDATE` 판단 결과가 FAIL 상태

## 3. 영향 범위

가능한 영향은 다음과 같다.

- FastAPI 예측 결과 품질 저하
- 특정 직무 카테고리 반복 오분류
- 최근 데이터 분포 변화에 대한 모델 적응 실패
- promoted model 재학습 필요성 증가
- 이전 promoted model로 rollback 검토 필요성 증가

## 4. 우선 확인할 metric

FastAPI `/metrics`에서 retraining candidate 관련 metric을 확인한다.

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_retraining_candidate"
```

확인해야 할 metric:

```text
jobskill_retraining_candidate_flag
jobskill_retraining_candidate_feedback_count
jobskill_retraining_candidate_accuracy
jobskill_retraining_candidate_f1_weighted
jobskill_retraining_candidate_accuracy_delta
jobskill_retraining_candidate_f1_delta
```

예상 예시:

```text
jobskill_retraining_candidate_flag 1
jobskill_retraining_candidate_feedback_count 30
jobskill_retraining_candidate_accuracy 0.6333
jobskill_retraining_candidate_f1_weighted 0.6100
jobskill_retraining_candidate_accuracy_delta -0.0800
jobskill_retraining_candidate_f1_delta -0.0700
```

## 5. 최신 재학습 후보 판단 결과 확인

`pipeline_check_results`에서 `RETRAINING_CANDIDATE` 결과를 확인한다.

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    check_type,
    check_name,
    status,
    metric_value,
    threshold_value,
    message,
    dag_id,
    task_id,
    run_id,
    checked_at
FROM pipeline_check_results
WHERE check_type = 'RETRAINING_CANDIDATE'
ORDER BY checked_at DESC
LIMIT 30;
"
```

확인 포인트:

- `retraining_candidate_flag`가 `FAIL`인지 확인
- `retraining_feedback_count`가 충분한지 확인
- `retraining_accuracy`가 기준보다 낮은지 확인
- `retraining_f1_weighted`가 기준보다 낮은지 확인
- `retraining_accuracy_delta`, `retraining_f1_delta`가 음수로 크게 떨어졌는지 확인

## 6. Production Feedback 평가 결과 확인

재학습 후보 판단의 원천이 되는 Production Feedback 평가 결과를 확인한다.

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    check_name,
    status,
    metric_value,
    threshold_value,
    message,
    checked_at
FROM pipeline_check_results
WHERE check_type = 'PRODUCTION_FEEDBACK'
ORDER BY checked_at DESC
LIMIT 20;
"
```

확인할 항목:

- `production_feedback_count`
- `production_accuracy`
- `production_f1_weighted`

## 7. 최근 오분류 확인

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    pf.prediction_id,
    mp.predicted_category,
    pf.actual_category,
    mp.confidence,
    pf.feedback_source,
    pf.feedback_note,
    pf.updated_at
FROM prediction_feedbacks pf
JOIN model_predictions mp
    ON pf.prediction_id = mp.id
WHERE mp.predicted_category <> pf.actual_category
ORDER BY pf.updated_at DESC
LIMIT 30;
"
```

확인 포인트:

- 특정 카테고리만 반복적으로 틀리는지
- confidence가 높은데도 틀리는 예측이 많은지
- `feedback_source = 'sample'`이 대부분인지
- 실제 운영 feedback인지 테스트 feedback인지

## 8. 오분류 집중도 확인

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    pf.actual_category,
    mp.predicted_category,
    COUNT(*) AS count
FROM prediction_feedbacks pf
JOIN model_predictions mp
    ON pf.prediction_id = mp.id
WHERE mp.predicted_category <> pf.actual_category
GROUP BY
    pf.actual_category,
    mp.predicted_category
ORDER BY count DESC
LIMIT 20;
"
```

판단 기준:

- 특정 actual/predicted 조합에 오분류가 몰리면 해당 클래스 학습 데이터 보강 필요
- 여러 클래스에서 전반적으로 틀리면 전체 재학습 필요성 증가
- sample feedback에만 몰려 있으면 실제 운영 성능 저하가 아닐 수 있음

## 9. Promoted model 상태 확인

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    id,
    model_name,
    status,
    accuracy,
    f1_weighted,
    promoted_model_path,
    created_at
FROM model_registry
WHERE status = 'PROMOTED'
ORDER BY id DESC
LIMIT 5;
"
```

확인 포인트:

- 현재 promoted model이 오래되었는지
- 최근 학습/승격된 모델인지
- 기존 평가 성능과 production feedback 성능 차이가 큰지
- promoted model file이 실제 존재하는지

## 10. 즉시 조치 절차

### Step 1. Production Feedback 평가 재실행

```bash
make production-feedback-check
```

### Step 2. Dashboard에서 판단 결과 재저장

Streamlit Dashboard 접속:

```text
http://localhost:8501
```

이동:

```text
Production Feedback
→ Retraining Candidate
→ Save retraining candidate decision
```

### Step 3. metric 재확인

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_retraining_candidate"
```

### Step 4. Alert 상태 확인

```bash
curl -fsS "http://localhost:9090/api/v1/alerts" | jq '.data.alerts[] | select(.labels.alertname == "JobSkillRetrainingCandidateDetected")'
```

## 11. 조치 방향 결정

| 상황 | 조치 |
|---|---|
| feedback 수가 부족함 | 판단 보류, feedback 추가 수집 |
| sample feedback이 대부분임 | 테스트 Alert로 판단하고 실제 feedback 기준으로 재확인 |
| 특정 클래스만 반복 오분류 | 해당 클래스 학습 데이터 보강 후 재학습 |
| accuracy와 F1 모두 낮음 | 재학습 후보로 판단 |
| 최근 지표가 급격히 하락 | 데이터 분포 변화 가능성 확인 |
| 새 promoted model이 이전보다 나쁨 | rollback 검토 |
| model file 또는 registry 정합성 문제 | model lifecycle integrity check 실행 |

## 12. 재학습 실행 후보

Alert가 실제 운영 성능 저하로 판단되면 DAG를 다시 실행한다.

```bash
make dag-trigger
```

또는 최소 학습 흐름만 수동 실행한다.

```bash
docker compose exec -T airflow-scheduler bash -lc "
cd /opt/airflow/project &&
python src/training/train_baseline.py &&
python src/quality/check_model_performance.py &&
python src/training/promote_model.py
"
```

재학습 후 확인:

```bash
make production-feedback-check
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_production_feedback|jobskill_retraining_candidate"
```

## 13. 롤백 후보

최근 promoted model이 문제라고 판단되면 rollback plan을 먼저 확인한다.

```bash
make model-rollback-plan
```

롤백 대상 archive id를 정한 뒤 실행한다.

```bash
MODEL_ROLLBACK_ARCHIVE_ID=<archive_id> \
MODEL_ROLLBACK_REASON="Retraining candidate alert로 인한 promoted model rollback 검토" \
make model-rollback
```

롤백 후 확인:

```bash
make model-lifecycle-check
make production-feedback-check
```

## 14. Alert 해소 확인

```bash
curl -fsS "http://localhost:9090/api/v1/query?query=jobskill_retraining_candidate_flag" | jq
curl -fsS "http://localhost:9090/api/v1/alerts" | jq '.data.alerts[] | select(.labels.alertname == "JobSkillRetrainingCandidateDetected")'
```

`jobskill_retraining_candidate_flag`가 0이거나 alert가 사라지면 해소된 상태다.

## 15. 검증 명령어

수정 후 아래 명령어를 실행한다.

```bash
make metrics-contract-check
make prometheus-check
make prometheus-rule-test
make runbook-check
make alert-rule-metric-check
make ops-static-check
```

## 16. 예방 방안

- sample feedback과 실제 운영 feedback을 구분한다.
- feedback 수가 충분히 쌓이기 전에는 재학습 판단을 보류한다.
- 특정 클래스 오분류가 반복되면 해당 클래스 학습 데이터를 보강한다.
- 모델 승격 후 Production Feedback 기준 성능을 반드시 확인한다.
- Evaluation History에서 accuracy/F1 추세를 주기적으로 확인한다.
- 새 모델이 운영 feedback 기준으로 나빠지면 rollback 후보를 함께 검토한다.
