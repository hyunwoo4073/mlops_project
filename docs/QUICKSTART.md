# jobskill-mlops Quick Start

## 1. 서비스 기동

```bash
make up
```

상태 확인:

```bash
docker compose ps
```

## 2. 기본 검증

```bash
make smoke
make ops-static-check
```

## 3. Remote OK crawler 기반 raw data 확인

raw table schema 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'raw_job_posts'
ORDER BY ordinal_position;
"
```

`crawled_at` 분포 확인:

```bash
docker exec jobskill-postgres psql -U jobskill -d jobskill -c "
SELECT
    source,
    COUNT(*) AS row_count,
    MIN(crawled_at) AS min_crawled_at,
    MAX(crawled_at) AS max_crawled_at,
    COUNT(DISTINCT DATE(crawled_at)) AS distinct_crawled_dates
FROM raw_job_posts
GROUP BY source
ORDER BY source;
"
```

## 4. Event Time Check

```bash
make training-event-time-check
cat reports/latest_training_event_time_report.md
```

확인할 값:

```text
source_columns
usable_event_time_rows
null_event_time_rows
min_event_time
max_event_time
distinct_event_dates
Selection Mode Preview
```

정상 예시:

```text
source_columns=['raw_job_posts.crawled_at']
usable_event_time_rows=5370
distinct_event_dates=242
recent after_rows=3171
recent_plus_history_sample after_rows=3671
```

## 5. Training Data Selection Experiment

```bash
make training-data-selection-experiment
cat reports/latest_training_data_selection_experiment_report.md
```

확인할 값:

```text
requested_mode
applied_mode
before_rows
after_rows
recent_rows
historical_rows
accuracy
f1_weighted
duration_seconds
```

해석 기준:

```text
full
- baseline 성능

recent
- 최근 window만 사용
- row reduction이 가장 클 수 있음

recent_plus_history_sample
- 최근 데이터 전체 + 과거 class-balanced sample
- 성능 보존과 비용 절감 균형 후보
```

## 6. Training Selection Policy Check

```bash
make training-data-selection-policy-check
cat reports/latest_training_data_selection_policy_report.md
```

Evidence Gate 판단 상태:

```text
INSUFFICIENT_EXPERIMENT_DATA
- 데이터 근거 부족으로 판단 보류

KEEP_FULL_RETRAIN
- evidence는 충분하지만 candidate 조건 미달

CANDIDATE_FOR_SHADOW_PROMOTION
- 반복 shadow validation 후보
```

## 7. Training Cost Report

```bash
make training-cost-report
cat reports/latest_training_cost_report.md
```

## 8. Ops Evidence 생성

```bash
make ops-report
make ops-evidence-bundle
make ops-evidence-check
```

ZIP 포함 확인:

```bash
unzip -l reports/ops_evidence/jobskill_ops_evidence_*.zip | grep -E "training_event_time|training_data_selection_experiment|training_data_selection_policy|training_cost"
```

## 9. 전체 권장 검증 순서

```bash
make training-event-time-check
make training-data-selection-experiment
make training-data-selection-policy-check
make training-cost-report
make ops-report
make ops-evidence-bundle
make ops-evidence-check
```

## 10. pandas FutureWarning 검증

`recent_plus_history_sample` 실행 중 아래 warning이 없어야 합니다.

```text
FutureWarning: DataFrameGroupBy.apply operated on the grouping columns
```

확인:

```bash
make training-event-time-check
make training-data-selection-experiment
```

## 11. Git 반영 예시

```bash
git add \
  README.md \
  docs/README_FULL.md \
  docs/README_SUMMARY.md \
  docs/QUICKSTART.md

git commit -m "docs: update training selection evidence workflow" \
  -m "Document training event time resolution, selection experiments, evidence gate decisions, historical seed validation, and pandas warning cleanup."
```
