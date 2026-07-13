# JobSkill Promoted Model Low Performance

## 의미

현재 promoted model의 accuracy 또는 weighted F1 score가 기준보다 낮은 상태입니다.

## 영향

- 낮은 성능의 모델이 batch/API inference에 사용될 가능성
- 데이터 라벨 품질 또는 학습 데이터 분포 문제 가능성
- 모델 재학습 또는 기준값 조정 검토 필요

## 확인 명령어

```bash
curl -fsS http://localhost:8000/metrics | grep jobskill_latest_promoted_model
curl -fsS 'http://localhost:9090/api/v1/query?query=jobskill_latest_promoted_model_f1_weighted'
curl -fsS 'http://localhost:9090/api/v1/query?query=jobskill_latest_promoted_model_accuracy'
```

## DB 확인

```sql
SELECT
    id,
    model_name,
    run_id,
    accuracy,
    f1_weighted,
    status,
    promoted_model_path,
    created_at
FROM model_registry
ORDER BY id DESC
LIMIT 10;
```

최근 promoted model 확인:

```sql
SELECT
    id,
    model_name,
    run_id,
    accuracy,
    f1_weighted,
    status,
    promoted_model_path,
    created_at
FROM model_registry
WHERE status = 'PROMOTED'
ORDER BY id DESC
LIMIT 1;
```

## 주요 원인

- 학습 데이터 수 부족
- class imbalance 증가
- rare class 제외 후 남은 class 부족
- 라벨링 rule 부정확
- RemoteOK 수집 데이터 품질 저하

## 조치

```bash
make report
make dag-trigger
```

모델 성능 기준값을 확인합니다.

```bash
grep -E "MIN_MODEL_ACCURACY|MIN_MODEL_F1_WEIGHTED" .env
```

필요 시 학습 데이터와 라벨링 rule을 점검합니다.
