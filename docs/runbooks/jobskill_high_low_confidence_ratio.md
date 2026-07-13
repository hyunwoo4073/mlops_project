# JobSkill High Low Confidence Ratio

## 의미

API 또는 batch prediction 결과 중 low confidence 비율이 기준보다 높은 상태입니다.

## 영향

- 모델 예측 신뢰도 저하
- 학습 데이터 분포와 현재 입력 데이터 분포 차이 가능성
- rule label 또는 feature 품질 문제 가능성
- 실제 운영에서는 모델 재학습 또는 데이터 품질 점검 필요

## 확인 명령어

```bash
curl -fsS http://localhost:8000/metrics | grep jobskill_model_prediction_low_confidence_ratio
curl -fsS 'http://localhost:9090/api/v1/query?query=jobskill_model_prediction_low_confidence_ratio'
```

## DB 확인

```sql
SELECT
    prediction_source,
    COUNT(*) AS cnt,
    ROUND(AVG(confidence)::numeric, 4) AS avg_confidence,
    COUNT(*) FILTER (WHERE is_low_confidence = true) AS low_confidence_count,
    ROUND(
        COUNT(*) FILTER (WHERE is_low_confidence = true)::numeric
        / NULLIF(COUNT(*), 0),
        4
    ) AS low_confidence_ratio
FROM model_predictions
GROUP BY prediction_source
ORDER BY prediction_source;
```

최근 low confidence 예측 확인:

```sql
SELECT
    id,
    prediction_source,
    predicted_category,
    confidence,
    confidence_level,
    is_low_confidence,
    top_predictions,
    predicted_at
FROM model_predictions
WHERE is_low_confidence = true
ORDER BY id DESC
LIMIT 20;
```

## 주요 원인

- 입력 텍스트가 짧거나 정보 부족
- 학습 데이터에 없는 유형의 공고 유입
- 특정 직무 라벨 데이터 부족
- 모델 성능 저하
- 외부 수집 데이터 품질 저하
- 직무 라벨링 rule과 모델 예측 분포 차이

## 조치

```bash
make report
make drift-check
make api-sample
```

필요 시 전체 파이프라인을 다시 실행합니다.

```bash
make dag-trigger
```
