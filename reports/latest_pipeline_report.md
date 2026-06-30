# JobSkill MLOps Pipeline Report

- Generated at: `2026-06-30 04:21:15`

This report summarizes model registry, prediction lineage, and pipeline check results.

## Latest Promoted Model

| id | model_name | run_id | accuracy | f1_weighted | status | promoted_model_path | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | job_classifier | 472340fc8ca14b50a382dd46f61108bf | 1.0 | 1.0 | PROMOTED | models/best/job_classifier.pkl | 2026-06-26 06:30:29.537676 |

## Model Registry History

| id | model_name | run_id_short | accuracy | f1_weighted | status | message | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 7 | job_classifier | 89b55c318886 | 0.9333 | 0.9345 | REJECTED | Current model was not promoted. current f1_weighted=0.9345, best f1_weighted=1.0000, current accuracy=0.9333, best accuracy=1.0000. | 2026-06-30 04:20:49.331334 |
| 6 | job_classifier | 6c9f91019c54 | 1.0 | 1.0 | REJECTED | Current model was not promoted. current f1_weighted=1.0000, best f1_weighted=1.0000, current accuracy=1.0000, best accuracy=1.0000. | 2026-06-29 07:08:53.378370 |
| 5 | job_classifier | 85df23f1b882 | 1.0 | 1.0 | REJECTED | Current model was not promoted. current f1_weighted=1.0000, best f1_weighted=1.0000, current accuracy=1.0000, best accuracy=1.0000. | 2026-06-29 06:03:39.989501 |
| 4 | job_classifier | 4befd5bea450 | 1.0 | 1.0 | REJECTED | Current model was not promoted. current f1_weighted=1.0000, best f1_weighted=1.0000, current accuracy=1.0000, best accuracy=1.0000. | 2026-06-26 07:53:51.288972 |
| 3 | job_classifier | 0fd6133b2154 | 1.0 | 1.0 | REJECTED | Current model was not promoted. current f1_weighted=1.0000, best f1_weighted=1.0000, current accuracy=1.0000, best accuracy=1.0000. | 2026-06-26 06:50:44.870308 |
| 2 | job_classifier | c913334225d5 | 1.0 | 1.0 | REJECTED | Current model was not promoted. current f1_weighted=1.0000, best f1_weighted=1.0000, current accuracy=1.0000, best accuracy=1.0000. | 2026-06-26 06:32:03.180113 |
| 1 | job_classifier | 472340fc8ca1 | 1.0 | 1.0 | PROMOTED | No existing promoted model. Promoting current model. | 2026-06-26 06:30:29.537676 |

## Prediction Lineage Summary

| model_name | model_run_id_short | model_registry_id | registry_status | registry_accuracy | registry_f1_weighted | prediction_count | avg_confidence | first_predicted_at | last_predicted_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 1.0 | 300 | 0.6721 | 2026-06-30 04:20:51.378777 | 2026-06-30 04:20:51.378777 |

## Latest Predictions

| id | job_post_id | predicted_category | confidence | model_name | model_run_id_short | model_registry_id | registry_status | registry_f1_weighted | predicted_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | 300 | Data Analyst | 0.8588 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 299 | 299 | ML Engineer | 0.7096 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 298 | 298 | Backend Engineer | 0.881 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 297 | 297 | DevOps Engineer | 0.777 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 296 | 296 | DevOps Engineer | 0.7126 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 295 | 295 | Data Analyst | 0.7905 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 294 | 294 | DevOps Engineer | 0.6869 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 293 | 293 | Data Engineer | 0.812 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 292 | 292 | ML Engineer | 0.5521 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 291 | 291 | DevOps Engineer | 0.7904 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 290 | 290 | Backend Engineer | 0.8704 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 289 | 289 | Data Analyst | 0.8572 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 288 | 288 | Data Analyst | 0.7863 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 287 | 287 | Data Engineer | 0.6926 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 286 | 286 | Data Engineer | 0.8408 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 285 | 285 | Data Engineer | 0.8498 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 284 | 284 | Backend Engineer | 0.8526 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 283 | 283 | Data Analyst | 0.7902 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 282 | 282 | Data Analyst | 0.8383 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |
| 281 | 280 | Data Analyst | 0.7592 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-30 04:20:51.378777 |

## Prediction Category Distribution

| model_name | model_run_id_short | model_registry_id | predicted_category | prediction_count | avg_confidence |
| --- | --- | --- | --- | --- | --- |
| job_classifier | 472340fc8ca1 | 1 | Data Analyst | 94 | 0.5487 |
| job_classifier | 472340fc8ca1 | 1 | ML Engineer | 56 | 0.6193 |
| job_classifier | 472340fc8ca1 | 1 | Backend Engineer | 50 | 0.8264 |
| job_classifier | 472340fc8ca1 | 1 | Data Engineer | 50 | 0.7557 |
| job_classifier | 472340fc8ca1 | 1 | DevOps Engineer | 50 | 0.7252 |

## Check Result Summary

| check_type | status | check_count | latest_checked_at |
| --- | --- | --- | --- |
| DATA_QUALITY | FAIL | 5 | 2026-06-26 06:12:21.333917 |
| DATA_QUALITY | PASS | 65 | 2026-06-30 04:20:13.235163 |
| MODEL_PERFORMANCE | FAIL | 1 | 2026-06-26 06:12:53.224724 |
| MODEL_PERFORMANCE | PASS | 17 | 2026-06-30 04:20:47.061448 |

## Latest Check Details

| check_type | check_name | status | metric_value | threshold_value | message | task_id | checked_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MODEL_PERFORMANCE | f1_weighted | PASS | 0.9345 | 0.7 | f1_weighted=0.9345, required>=0.7000, run_id=89b55c31888641939f741856f549d09a | check_model_performance | 2026-06-30 04:20:47.061448 |
| MODEL_PERFORMANCE | accuracy | PASS | 0.9333 | 0.7 | accuracy=0.9333, required>=0.7000, run_id=89b55c31888641939f741856f549d09a | check_model_performance | 2026-06-30 04:20:47.061448 |
| DATA_QUALITY | unknown_ratio | PASS |  |  | unknown count = 0, unknown ratio = 0.0000, allowed <= 0.5 | check_training_data | 2026-06-30 04:20:13.235163 |
| DATA_QUALITY | category_diversity | PASS |  |  | distinct category count = 5, required >= 2 | check_training_data | 2026-06-30 04:20:13.235163 |
| DATA_QUALITY | job_category_not_empty | PASS |  |  | empty job_category count = 0 | check_training_data | 2026-06-30 04:20:13.235163 |
| DATA_QUALITY | text_for_model_not_empty | PASS |  |  | empty text_for_model count = 0 | check_training_data | 2026-06-30 04:20:13.235163 |
| DATA_QUALITY | job_post_skills_count | PASS |  |  | job_post_skills count = 1412 | check_training_data | 2026-06-30 04:20:13.235163 |
| DATA_QUALITY | cleaned_job_posts_count | PASS |  |  | cleaned_job_posts count = 300, required >= 50 | check_training_data | 2026-06-30 04:20:13.235163 |
| DATA_QUALITY | raw_job_posts_count | PASS |  |  | raw_job_posts count = 300 | check_training_data | 2026-06-30 04:20:13.235163 |
| MODEL_PERFORMANCE | f1_weighted | PASS | 1.0 | 0.7 | f1_weighted=1.0000, required>=0.7000, run_id=6c9f91019c544173be2c5c6c97a77454 | check_model_performance | 2026-06-29 07:08:51.790167 |
| MODEL_PERFORMANCE | accuracy | PASS | 1.0 | 0.7 | accuracy=1.0000, required>=0.7000, run_id=6c9f91019c544173be2c5c6c97a77454 | check_model_performance | 2026-06-29 07:08:51.790167 |
| DATA_QUALITY | unknown_ratio | PASS |  |  | unknown count = 47, unknown ratio = 0.1880, allowed <= 0.5 | check_training_data | 2026-06-29 07:08:24.445963 |
| DATA_QUALITY | category_diversity | PASS |  |  | distinct category count = 6, required >= 2 | check_training_data | 2026-06-29 07:08:24.445963 |
| DATA_QUALITY | job_category_not_empty | PASS |  |  | empty job_category count = 0 | check_training_data | 2026-06-29 07:08:24.445963 |
| DATA_QUALITY | text_for_model_not_empty | PASS |  |  | empty text_for_model count = 0 | check_training_data | 2026-06-29 07:08:24.445963 |
| DATA_QUALITY | job_post_skills_count | PASS |  |  | job_post_skills count = 1387 | check_training_data | 2026-06-29 07:08:24.445963 |
| DATA_QUALITY | cleaned_job_posts_count | PASS |  |  | cleaned_job_posts count = 250, required >= 50 | check_training_data | 2026-06-29 07:08:24.445963 |
| DATA_QUALITY | raw_job_posts_count | PASS |  |  | raw_job_posts count = 250 | check_training_data | 2026-06-29 07:08:24.445963 |
| MODEL_PERFORMANCE | f1_weighted | PASS | 1.0 | 0.7 | f1_weighted=1.0000, required>=0.7000, run_id=85df23f1b882422f804b204d96af9834 | check_model_performance | 2026-06-29 06:03:37.029773 |
| MODEL_PERFORMANCE | accuracy | PASS | 1.0 | 0.7 | accuracy=1.0000, required>=0.7000, run_id=85df23f1b882422f804b204d96af9834 | check_model_performance | 2026-06-29 06:03:37.029773 |
| DATA_QUALITY | unknown_ratio | PASS |  |  | unknown count = 47, unknown ratio = 0.1880, allowed <= 0.5 | check_training_data | 2026-06-29 06:03:11.538617 |
| DATA_QUALITY | category_diversity | PASS |  |  | distinct category count = 6, required >= 2 | check_training_data | 2026-06-29 06:03:11.538617 |
| DATA_QUALITY | job_category_not_empty | PASS |  |  | empty job_category count = 0 | check_training_data | 2026-06-29 06:03:11.538617 |
| DATA_QUALITY | text_for_model_not_empty | PASS |  |  | empty text_for_model count = 0 | check_training_data | 2026-06-29 06:03:11.538617 |
| DATA_QUALITY | job_post_skills_count | PASS |  |  | job_post_skills count = 1387 | check_training_data | 2026-06-29 06:03:11.538617 |
| DATA_QUALITY | cleaned_job_posts_count | PASS |  |  | cleaned_job_posts count = 250, required >= 50 | check_training_data | 2026-06-29 06:03:11.538617 |
| DATA_QUALITY | raw_job_posts_count | PASS |  |  | raw_job_posts count = 250 | check_training_data | 2026-06-29 06:03:11.538617 |
| DATA_QUALITY | unknown_ratio | PASS |  |  | unknown count = 47, unknown ratio = 0.1880, allowed <= 0.5 |  | 2026-06-29 06:02:37.081303 |
| DATA_QUALITY | category_diversity | PASS |  |  | distinct category count = 6, required >= 2 |  | 2026-06-29 06:02:37.081303 |
| DATA_QUALITY | job_category_not_empty | PASS |  |  | empty job_category count = 0 |  | 2026-06-29 06:02:37.081303 |

## Failed Checks

| check_type | check_name | status | metric_value | threshold_value | message | task_id | checked_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MODEL_PERFORMANCE | accuracy | FAIL | 1.0 | 1.1 | accuracy=1.0000, required>=1.1000, run_id=01a6a0334fc048ddbcb009cd8f1fa2c6 |  | 2026-06-26 06:12:53.224724 |
| DATA_QUALITY | unknown_ratio | FAIL |  |  | unknown count = 0, unknown ratio = 1.0000, allowed <= 0.5 |  | 2026-06-26 06:12:21.333917 |
| DATA_QUALITY | category_diversity | FAIL |  |  | distinct category count = 0, required >= 2 |  | 2026-06-26 06:12:21.333917 |
| DATA_QUALITY | job_post_skills_count | FAIL |  |  | job_post_skills count = 0 |  | 2026-06-26 06:12:21.333917 |
| DATA_QUALITY | cleaned_job_posts_count | FAIL |  |  | cleaned_job_posts count = 0, required >= 50 |  | 2026-06-26 06:12:21.333917 |
| DATA_QUALITY | raw_job_posts_count | FAIL |  |  | raw_job_posts count = 0 |  | 2026-06-26 06:12:21.333917 |

## Model Promotion Summary

| status | count | avg_accuracy | avg_f1_weighted | latest_created_at |
| --- | --- | --- | --- | --- |
| PROMOTED | 1 | 1.0 | 1.0 | 2026-06-26 06:30:29.537676 |
| REJECTED | 6 | 0.9889 | 0.9891 | 2026-06-30 04:20:49.331334 |

## Raw Job Count by Source

| source | raw_count | first_crawled_at | latest_crawled_at |
| --- | --- | --- | --- |
| sample | 250 | 2026-06-30 04:20:10.151233 | 2026-06-30 04:20:10.151233 |
| remoteok | 50 | 2026-06-30 01:50:25.010339 | 2026-06-30 01:50:25.010339 |

## Cleaned Job Quality by Source

| source | cleaned_count | unknown_count | unknown_ratio | category_count |
| --- | --- | --- | --- | --- |
| sample | 250 | 0 | 0.0 | 5 |
| remoteok | 50 | 0 | 0.0 | 4 |

## Job Category Distribution by Source

| source | job_category | count | source_ratio |
| --- | --- | --- | --- |
| remoteok | Data Analyst | 32 | 0.64 |
| remoteok | DevOps Engineer | 8 | 0.16 |
| remoteok | ML Engineer | 7 | 0.14 |
| remoteok | Backend Engineer | 3 | 0.06 |
| sample | DevOps Engineer | 52 | 0.208 |
| sample | Data Analyst | 50 | 0.2 |
| sample | Data Engineer | 50 | 0.2 |
| sample | Backend Engineer | 50 | 0.2 |
| sample | ML Engineer | 48 | 0.192 |

## Skill Extraction Summary by Source

| source | cleaned_count | extracted_skill_count | avg_skills_per_job |
| --- | --- | --- | --- |
| remoteok | 50 | 25 | 0.5 |
| sample | 250 | 1387 | 5.548 |

## Top Skills by Source

| source | skill_name | count |
| --- | --- | --- |
| remoteok | Excel | 18 |
| remoteok | JavaScript | 3 |
| remoteok | Python | 2 |
| remoteok | GCP | 1 |
| remoteok | SQL | 1 |
| sample | AWS | 97 |
| sample | Linux | 97 |
| sample | Docker | 92 |
| sample | SQL | 88 |
| sample | PostgreSQL | 82 |
| sample | MySQL | 81 |
| sample | Kubernetes | 79 |
| sample | Python | 76 |
| sample | Pandas | 62 |
| sample | Redis | 52 |
| sample | Kafka | 52 |
| sample | Spring | 38 |
| sample | Tableau | 34 |
| sample | Azure | 30 |
| sample | Elasticsearch | 29 |
| sample | TensorFlow | 29 |
| sample | GCP | 28 |
| sample | PyTorch | 27 |
| sample | Prometheus | 26 |
| sample | Excel | 25 |
| sample | Grafana | 25 |
| sample | Spark | 25 |
| sample | Flink | 25 |
| sample | Java | 25 |
| sample | scikit-learn | 24 |
| sample | FastAPI | 23 |
| sample | Airflow | 22 |
| sample | Spring Boot | 22 |
| sample | Hive | 21 |
| sample | dbt | 18 |
| sample | MLflow | 18 |
| sample | Hadoop | 15 |

## Prediction Summary by Source

| source | predicted_category | prediction_count | avg_confidence | low_confidence_count | low_confidence_ratio |
| --- | --- | --- | --- | --- | --- |
| remoteok | Data Analyst | 44 | 0.2623 | 0 | 0.0 |
| remoteok | ML Engineer | 6 | 0.2332 | 0 | 0.0 |
| sample | DevOps Engineer | 50 | 0.7252 | 0 | 0.0 |
| sample | Data Analyst | 50 | 0.8008 | 0 | 0.0 |
| sample | ML Engineer | 50 | 0.6656 | 0 | 0.0 |
| sample | Data Engineer | 50 | 0.7557 | 0 | 0.0 |
| sample | Backend Engineer | 50 | 0.8264 | 0 | 0.0 |
