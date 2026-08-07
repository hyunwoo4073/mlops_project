# jobskill-mlops Summary

## 프로젝트 한 줄 요약

`jobskill-mlops`는 채용공고 데이터를 수집하고 직무 분류 모델을 학습한 뒤, 운영 feedback과 evidence 기반으로 재학습 전략까지 판단하는 end-to-end MLOps 포트폴리오 프로젝트입니다.

## 전체 흐름

```text
Remote OK crawler
→ raw_job_posts 적재
→ preprocessing
→ cleaned_job_posts 생성
→ data contract / quality check
→ MLflow training
→ model evaluation / class performance gate
→ model promotion / archive / rollback
→ FastAPI serving / batch inference
→ production feedback
→ retraining candidate / strategy / cost benchmark
→ training data selection experiment
→ evidence gate
→ ops evidence bundle
```

## 핵심 운영 포인트

```text
1. 실제 ingestion과 실험용 seed 분리
   - 실제 경로는 Remote OK crawler
   - local policy validation은 remoteok_seed source의 historical seed data 사용

2. Event-time 기반 retraining selection
   - raw_job_posts.crawled_at을 training_event_at으로 표준화
   - full / lookback / recent / recent_plus_history_sample mode 지원

3. Selection experiment
   - full baseline과 reduced-data retrain mode를 shadow experiment로 비교
   - accuracy, weighted F1, selected rows, recent/historical rows, duration 기록

4. Evidence Gate
   - 데이터 부족 또는 row reduction 없음 상태에서는 candidate 추천 금지
   - INSUFFICIENT_EXPERIMENT_DATA / KEEP_FULL_RETRAIN / CANDIDATE_FOR_SHADOW_PROMOTION 상태 분리

5. 운영 evidence
   - training event time report
   - training selection experiment report
   - training selection policy report
   - training cost report
   - ops validation report
   - ops evidence zip bundle
```

## 2026-08-07 검증 결과 요약

```text
Event Time Coverage
- source_columns=['raw_job_posts.crawled_at']
- usable_event_time_rows=5370
- distinct_event_dates=242

Selection Preview
- full=5370 rows
- lookback=4512 rows
- recent=3171 rows
- recent_plus_history_sample=3671 rows

Experiment Result
- full: accuracy=0.9913, f1_weighted=0.9913
- recent: accuracy=0.9811, f1_weighted=0.9812
- recent_plus_history_sample: accuracy=0.9891, f1_weighted=0.9891
```

## 현재 해석

```text
full
- 최고 성능 baseline
- 운영 retrain 기본 경로 유지

recent
- row reduction이 가장 큼
- 성능 하락도 더 큼
- aggressive row-reduction shadow 후보

recent_plus_history_sample
- row reduction이 있고 F1 하락이 작음
- 우선 shadow validation 후보
```

## 검토자에게 보여줄 포인트

이 프로젝트는 단일 모델 학습 결과만 보여주는 것이 아니라, 모델 운영 이후에 feedback, retraining strategy, training cost, training data selection policy, evidence gate를 연결해 “언제, 어떤 데이터로, 어떤 방식으로 다시 학습할 것인가”를 판단하는 운영형 MLOps 구조를 포함합니다.
