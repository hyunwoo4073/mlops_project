# JobSkill Production Feedback 성능 저하 Runbook

## 1. Alert 개요

대상 Alert:

- `JobSkillProductionFeedbackLowAccuracy`
- `JobSkillProductionFeedbackLowF1`

이 Alert는 운영 예측 결과에 연결된 피드백 데이터를 기준으로 모델 성능이 낮아졌을 때 발생한다.

현재 기준:

- `jobskill_production_feedback_total >= 10`
- `jobskill_production_feedback_accuracy < 0.7`
- 또는 `jobskill_production_feedback_f1_weighted < 0.7`

즉, 최소 10건 이상의 피드백이 쌓인 상태에서 정확도나 Weighted F1 점수가 기준보다 낮으면 모델 품질 저하 가능성이 있다고 판단한다.

## 2. 영향 범위

가능한 영향은 다음과 같다.

- FastAPI 예측 결과의 신뢰도 저하
- 잘못된 직무 카테고리 예측 증가
- 특정 클래스에 대한 오분류 증가
- 최근 데이터 분포 변화에 대한 모델 적응 실패
- 재학습 또는 모델 롤백 필요 가능성 증가

## 3. 우선 확인할 지표

FastAPI `/metrics`에서 Production Feedback 관련 metric을 확인한다.

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_production_feedback"
```

확인해야 할 metric:

```text
jobskill_production_feedback_total
jobskill_production_feedback_accuracy
jobskill_production_feedback_f1_weighted
jobskill_production_feedback_category_total
```

예상 예시:

```text
jobskill_production_feedback_total 30
jobskill_production_feedback_accuracy 0.8
jobskill_production_feedback_f1_weighted 0.78
jobskill_production_feedback_category_total{actual_category="Data Engineer",predicted_category="Data Engineer"} 10
```

## 4. 최근 피드백 데이터 확인

최근 피드백과 예측 결과를 함께 확인한다.

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    pf.id,
    pf.prediction_id,
    mp.predicted_category,
    pf.actual_category,
    CASE
        WHEN mp.predicted_category = pf.actual_category THEN 'CORRECT'
        ELSE 'WRONG'
    END AS result,
    mp.confidence,
    pf.feedback_source,
    pf.created_by,
    pf.updated_at
FROM prediction_feedbacks pf
JOIN model_predictions mp
    ON pf.prediction_id = mp.id
ORDER BY pf.updated_at DESC
LIMIT 30;
"
```

확인 포인트:

- 오분류가 특정 카테고리에 몰려 있는지
- `feedback_source`가 `sample`인지 실제 사용자 또는 운영 피드백인지
- confidence가 높은데도 틀리는 경우가 많은지
- 최근 입력 데이터가 기존 학습 데이터와 달라졌는지

## 5. Production Feedback 평가 결과 확인

`check_production_feedback.py`가 저장한 최신 평가 결과를 확인한다.

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
LIMIT 10;
"
```

확인할 항목:

- `production_feedback_count`
- `production_accuracy`
- `production_f1_weighted`

`status = FAIL`이면 해당 기준을 만족하지 못한 것이다.

## 6. 주요 원인별 확인 방법

### 6-1. 피드백 라벨이 테스트 데이터이거나 품질이 낮은 경우

샘플 피드백이 대부분이면 실제 장애가 아니라 테스트 상황일 수 있다.

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    feedback_source,
    created_by,
    COUNT(*) AS count
FROM prediction_feedbacks
GROUP BY feedback_source, created_by
ORDER BY count DESC;
"
```

판단 기준:

- `feedback_source = 'sample'` 비중이 높으면 테스트 Alert일 가능성이 있다.
- 실제 운영 피드백과 샘플 피드백을 분리해서 봐야 한다.
- 샘플 피드백은 성능 저하 시나리오 테스트 목적으로 일부러 틀리게 만들 수 있다.

### 6-2. 특정 카테고리에서 오분류가 집중되는 경우

실제 라벨과 예측 라벨의 confusion table을 확인한다.

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    pf.actual_category,
    mp.predicted_category,
    COUNT(*) AS count
FROM prediction_feedbacks pf
JOIN model_predictions mp
    ON pf.prediction_id = mp.id
GROUP BY pf.actual_category, mp.predicted_category
ORDER BY pf.actual_category, count DESC;
"
```

판단 기준:

- 특정 `actual_category`가 반복적으로 다른 클래스로 예측되면 해당 클래스 학습 데이터가 부족할 수 있다.
- 예를 들어 `Data Engineer`가 계속 `Backend Engineer`로 예측되면 데이터 또는 feature 표현이 부족할 수 있다.

### 6-3. 최근 예측 데이터 분포가 달라진 경우

예측 결과 분포를 확인한다.

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    prediction_source,
    predicted_category,
    COUNT(*) AS count,
    ROUND(AVG(confidence)::numeric, 4) AS avg_confidence
FROM model_predictions
GROUP BY prediction_source, predicted_category
ORDER BY prediction_source, count DESC;
"
```

판단 기준:

- 특정 카테고리 예측이 갑자기 증가했는지 확인한다.
- 평균 confidence가 낮아졌는지 확인한다.
- API 예측과 Batch 예측의 분포 차이가 큰지 확인한다.

### 6-4. Promoted model이 오래되었거나 잘못 승격된 경우

현재 승격된 모델 정보를 확인한다.

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

판단 기준:

- 최근 데이터 대비 모델이 오래되었는지 확인한다.
- 이전 모델보다 현재 모델 성능이 낮은지 확인한다.
- `promoted_model_path`의 파일이 실제로 존재하는지도 확인한다.

## 7. 즉시 조치 절차

### Step 1. Production Feedback 평가 재실행

```bash
make production-feedback-check
```

### Step 2. metric 재확인

```bash
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_production_feedback"
```

### Step 3. 오분류 목록 확인

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

### Step 4. 조치 방향 결정

| 상황 | 조치 |
|---|---|
| 대부분 샘플 피드백으로 인한 Alert | 테스트 Alert로 판단하고 실제 `feedback_source` 기준으로 재확인 |
| 특정 클래스만 반복적으로 틀림 | 해당 클래스 학습 데이터 보강 후 재학습 |
| 전체 accuracy와 F1이 모두 낮음 | 모델 재학습 후보로 판단 |
| 최근 승격 모델이 이전보다 나쁨 | 모델 롤백 검토 |
| metric이 0이거나 누락됨 | `/metrics`, DB 테이블, API 로그, Prometheus scrape 상태 확인 |

## 8. 재학습 후보 판단

Alert가 실제 성능 저하로 판단되면 DAG를 다시 실행한다.

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

재학습 후 다시 확인한다.

```bash
make production-feedback-check
curl -fsS http://localhost:8000/metrics | grep -E "jobskill_production_feedback"
```

## 9. 롤백 후보 판단

최근 승격된 모델이 문제라고 판단되면 rollback plan을 먼저 확인한다.

```bash
make model-rollback-plan
```

롤백 대상 archive id를 정한 뒤 실행한다.

```bash
MODEL_ROLLBACK_ARCHIVE_ID=<archive_id> \
MODEL_ROLLBACK_REASON="Production feedback 성능 저하로 인한 promoted model rollback" \
make model-rollback
```

롤백 후 확인한다.

```bash
make model-lifecycle-check
make production-feedback-check
```

## 10. Alert 해소 확인

Prometheus에서 현재 expression 결과를 확인한다.

```bash
curl -fsS "http://localhost:9090/api/v1/query?query=jobskill_production_feedback_accuracy" | jq
curl -fsS "http://localhost:9090/api/v1/query?query=jobskill_production_feedback_f1_weighted" | jq
```

Alert 목록 확인:

```bash
curl -fsS "http://localhost:9090/api/v1/alerts" | jq '.data.alerts[] | select(.labels.alertname | startswith("JobSkillProductionFeedback"))'
```

Alertmanager 확인:

```bash
curl -fsS http://localhost:9093/api/v2/alerts | jq '.[] | select(.labels.alertname | startswith("JobSkillProductionFeedback"))'
```

## 11. 검증 명령어

수정 후 아래 명령어를 실행한다.

```bash
make prometheus-check
make prometheus-rule-test
make runbook-check
make alert-rule-metric-check
make ops-static-check
```

## 12. 예방 방안

- 샘플 피드백과 실제 운영 피드백을 구분한다.
- `feedback_source`를 기준으로 성능을 분리해서 볼 수 있도록 관리한다.
- 특정 클래스 오분류가 반복되면 해당 클래스 학습 데이터를 보강한다.
- Production Feedback metric을 Dashboard와 Alert에서 지속적으로 확인한다.
- 모델 승격 후에는 API 예측과 feedback 성능을 같이 확인한다.
- 새 모델이 운영 feedback 기준으로 나빠지면 재학습 또는 롤백을 검토한다.