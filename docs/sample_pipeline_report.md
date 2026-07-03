# JobSkill MLOps Pipeline Report

- Generated at: `2026-07-03 04:26:23`

This report summarizes model registry, prediction lineage, and pipeline check results.

## Latest Promoted Model

| id | model_name | run_id | accuracy | f1_weighted | status | promoted_model_path | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | job_classifier | 472340fc8ca14b50a382dd46f61108bf | 1.0 | 1.0 | PROMOTED | models/best/job_classifier.pkl | 2026-06-26 06:30:29.537676 |

## Model Registry History

| id | model_name | run_id_short | accuracy | f1_weighted | status | message | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12 | job_classifier | 99dc0f69fb56 | 0.9333 | 0.9338 | REJECTED | Current model was not promoted. current f1_weighted=0.9338, best f1_weighted=1.0000, current accuracy=0.9333, best accuracy=1.0000. | 2026-07-02 08:10:34.204635 |
| 11 | job_classifier | 9ee1953de09a | 0.9333 | 0.9338 | REJECTED | Current model was not promoted. current f1_weighted=0.9338, best f1_weighted=1.0000, current accuracy=0.9333, best accuracy=1.0000. | 2026-07-02 08:08:31.070159 |
| 10 | job_classifier | 376280f012fb | 0.9333 | 0.9338 | REJECTED | Current model was not promoted. current f1_weighted=0.9338, best f1_weighted=1.0000, current accuracy=0.9333, best accuracy=1.0000. | 2026-07-02 07:53:34.058187 |
| 9 | job_classifier | f4475bf76d1e | 0.8922 | 0.8935 | REJECTED | Current model was not promoted. current f1_weighted=0.8935, best f1_weighted=1.0000, current accuracy=0.8922, best accuracy=1.0000. | 2026-07-02 07:33:14.544653 |
| 8 | job_classifier | fb0ab8d9570b | 0.9216 | 0.9214 | REJECTED | Current model was not promoted. current f1_weighted=0.9214, best f1_weighted=1.0000, current accuracy=0.9216, best accuracy=1.0000. | 2026-07-02 07:22:09.761663 |
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
| job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 1.0 | 300 | 0.6699 | 2026-07-02 08:10:36.051814 | 2026-07-02 08:10:36.051814 |

## Latest Predictions

| id | job_post_id | predicted_category | confidence | model_name | model_run_id_short | model_registry_id | registry_status | registry_f1_weighted | predicted_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | 300 | Data Analyst | 0.2417 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 299 | 299 | Data Analyst | 0.2181 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 298 | 298 | Data Analyst | 0.2406 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 297 | 297 | Data Analyst | 0.2206 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 296 | 296 | Data Analyst | 0.2636 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 295 | 295 | Data Analyst | 0.3641 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 294 | 294 | Data Analyst | 0.3322 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 293 | 293 | ML Engineer | 0.2387 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 292 | 292 | Data Analyst | 0.2542 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 291 | 291 | Data Analyst | 0.2206 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 290 | 290 | Data Analyst | 0.2253 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 289 | 289 | Data Analyst | 0.2508 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 288 | 288 | Data Analyst | 0.2455 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 287 | 287 | Data Analyst | 0.2783 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 286 | 286 | Backend Engineer | 0.2596 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 285 | 285 | Data Analyst | 0.3322 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 284 | 284 | Data Analyst | 0.2307 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 283 | 283 | ML Engineer | 0.2206 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 282 | 282 | ML Engineer | 0.2342 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |
| 281 | 281 | Backend Engineer | 0.2177 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-07-02 08:10:36.051814 |

## Prediction Category Distribution

| model_name | model_run_id_short | model_registry_id | predicted_category | prediction_count | avg_confidence |
| --- | --- | --- | --- | --- | --- |
| job_classifier | 472340fc8ca1 | 1 | Data Analyst | 82 | 0.5876 |
| job_classifier | 472340fc8ca1 | 1 | ML Engineer | 61 | 0.5869 |
| job_classifier | 472340fc8ca1 | 1 | Backend Engineer | 55 | 0.7719 |
| job_classifier | 472340fc8ca1 | 1 | Data Engineer | 52 | 0.7357 |
| job_classifier | 472340fc8ca1 | 1 | DevOps Engineer | 50 | 0.7252 |

## Check Result Summary

| check_type | status | check_count | latest_checked_at |
| --- | --- | --- | --- |
| DATA_QUALITY | FAIL | 5 | 2026-06-26 06:12:21.333917 |
| DATA_QUALITY | PASS | 121 | 2026-07-02 08:10:11.532182 |
| MODEL_PERFORMANCE | FAIL | 3 | 2026-07-02 07:31:10.014846 |
| MODEL_PERFORMANCE | PASS | 27 | 2026-07-02 08:10:32.328787 |
| PREDICTION_QUALITY | FAIL | 2 | 2026-07-02 07:50:14.684391 |
| PREDICTION_QUALITY | PASS | 6 | 2026-07-02 08:10:36.254854 |

## Latest Check Details

| check_type | check_name | status | metric_value | threshold_value | message | task_id | checked_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PREDICTION_QUALITY | null_confidence_count | PASS | 0.0 | 0.0 | null_confidence_count=0, required = 0 | check_prediction_quality | 2026-07-02 08:10:36.254854 |
| PREDICTION_QUALITY | low_confidence_ratio | PASS | 0.2033 | 0.4 | low_confidence_count=61, prediction_count=300, low_confidence_ratio=0.2033, allowed <= 0.4000 | check_prediction_quality | 2026-07-02 08:10:36.254854 |
| PREDICTION_QUALITY | avg_prediction_confidence | PASS | 0.6699 | 0.6 | avg_confidence=0.6699, required >= 0.6000 | check_prediction_quality | 2026-07-02 08:10:36.254854 |
| PREDICTION_QUALITY | prediction_count | PASS | 300.0 | 1.0 | prediction_count=300, required >= 1 | check_prediction_quality | 2026-07-02 08:10:36.254854 |
| MODEL_PERFORMANCE | f1_weighted | PASS | 0.9338 | 0.7 | f1_weighted=0.9338, required>=0.7000, run_id=99dc0f69fb56420cb6aba6dbd51d3aec | check_model_performance | 2026-07-02 08:10:32.328787 |
| MODEL_PERFORMANCE | accuracy | PASS | 0.9333 | 0.7 | accuracy=0.9333, required>=0.7000, run_id=99dc0f69fb56420cb6aba6dbd51d3aec | check_model_performance | 2026-07-02 08:10:32.328787 |
| DATA_QUALITY | unknown_ratio | PASS |  |  | unknown count = 0, unknown ratio = 0.0000, allowed <= 0.5 | check_training_data | 2026-07-02 08:10:11.532182 |
| DATA_QUALITY | category_diversity | PASS |  |  | distinct category count = 5, required >= 2 | check_training_data | 2026-07-02 08:10:11.532182 |
| DATA_QUALITY | job_category_not_empty | PASS |  |  | empty job_category count = 0 | check_training_data | 2026-07-02 08:10:11.532182 |
| DATA_QUALITY | text_for_model_not_empty | PASS |  |  | empty text_for_model count = 0 | check_training_data | 2026-07-02 08:10:11.532182 |
| DATA_QUALITY | job_post_skills_count | PASS |  |  | job_post_skills count = 1408 | check_training_data | 2026-07-02 08:10:11.532182 |
| DATA_QUALITY | cleaned_job_posts_count | PASS |  |  | cleaned_job_posts count = 300, required >= 50 | check_training_data | 2026-07-02 08:10:11.532182 |
| DATA_QUALITY | raw_job_posts_count | PASS |  |  | raw_job_posts count = 300 | check_training_data | 2026-07-02 08:10:11.532182 |
| MODEL_PERFORMANCE | f1_weighted | PASS | 0.9338 | 0.7 | f1_weighted=0.9338, required>=0.7000, run_id=9ee1953de09a448082d0577975ee6dd1 | check_model_performance | 2026-07-02 08:08:29.224688 |
| MODEL_PERFORMANCE | accuracy | PASS | 0.9333 | 0.7 | accuracy=0.9333, required>=0.7000, run_id=9ee1953de09a448082d0577975ee6dd1 | check_model_performance | 2026-07-02 08:08:29.224688 |
| DATA_QUALITY | unknown_ratio | PASS |  |  | unknown count = 0, unknown ratio = 0.0000, allowed <= 0.5 | check_training_data | 2026-07-02 08:08:08.873243 |
| DATA_QUALITY | category_diversity | PASS |  |  | distinct category count = 5, required >= 2 | check_training_data | 2026-07-02 08:08:08.873243 |
| DATA_QUALITY | job_category_not_empty | PASS |  |  | empty job_category count = 0 | check_training_data | 2026-07-02 08:08:08.873243 |
| DATA_QUALITY | text_for_model_not_empty | PASS |  |  | empty text_for_model count = 0 | check_training_data | 2026-07-02 08:08:08.873243 |
| DATA_QUALITY | job_post_skills_count | PASS |  |  | job_post_skills count = 1408 | check_training_data | 2026-07-02 08:08:08.873243 |
| DATA_QUALITY | cleaned_job_posts_count | PASS |  |  | cleaned_job_posts count = 300, required >= 50 | check_training_data | 2026-07-02 08:08:08.873243 |
| DATA_QUALITY | raw_job_posts_count | PASS |  |  | raw_job_posts count = 300 | check_training_data | 2026-07-02 08:08:08.873243 |
| MODEL_PERFORMANCE | f1_weighted | PASS | 0.9338 | 0.7 | f1_weighted=0.9338, required>=0.7000, run_id=376280f012fb45b188a19db1a757ca39 | check_model_performance | 2026-07-02 07:53:32.349949 |
| MODEL_PERFORMANCE | accuracy | PASS | 0.9333 | 0.7 | accuracy=0.9333, required>=0.7000, run_id=376280f012fb45b188a19db1a757ca39 | check_model_performance | 2026-07-02 07:53:32.349949 |
| DATA_QUALITY | unknown_ratio | PASS |  |  | unknown count = 0, unknown ratio = 0.0000, allowed <= 0.5 | check_training_data | 2026-07-02 07:53:10.468262 |
| DATA_QUALITY | category_diversity | PASS |  |  | distinct category count = 5, required >= 2 | check_training_data | 2026-07-02 07:53:10.468262 |
| DATA_QUALITY | job_category_not_empty | PASS |  |  | empty job_category count = 0 | check_training_data | 2026-07-02 07:53:10.468262 |
| DATA_QUALITY | text_for_model_not_empty | PASS |  |  | empty text_for_model count = 0 | check_training_data | 2026-07-02 07:53:10.468262 |
| DATA_QUALITY | job_post_skills_count | PASS |  |  | job_post_skills count = 1408 | check_training_data | 2026-07-02 07:53:10.468262 |
| DATA_QUALITY | cleaned_job_posts_count | PASS |  |  | cleaned_job_posts count = 300, required >= 50 | check_training_data | 2026-07-02 07:53:10.468262 |

## Failed Checks

| check_type | check_name | status | metric_value | threshold_value | message | task_id | checked_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PREDICTION_QUALITY | low_confidence_ratio | FAIL | 1.0 | 0.4 | low_confidence_count=1, prediction_count=1, low_confidence_ratio=1.0000, allowed <= 0.4000 |  | 2026-07-02 07:50:14.684391 |
| PREDICTION_QUALITY | avg_prediction_confidence | FAIL | 0.3871 | 0.6 | avg_confidence=0.3871, required >= 0.6000 |  | 2026-07-02 07:50:14.684391 |
| MODEL_PERFORMANCE | f1_weighted | FAIL | 0.5333 | 0.7 | f1_weighted=0.5333, required>=0.7000, run_id=07b45511d81c4761a50f2a7833745c41 | check_model_performance | 2026-07-02 07:31:10.014846 |
| MODEL_PERFORMANCE | accuracy | FAIL | 0.6667 | 0.7 | accuracy=0.6667, required>=0.7000, run_id=07b45511d81c4761a50f2a7833745c41 | check_model_performance | 2026-07-02 07:31:10.014846 |
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
| REJECTED | 11 | 0.9588 | 0.9592 | 2026-07-02 08:10:34.204635 |

## Raw Job Count by Source

| source | raw_count | first_crawled_at | latest_crawled_at |
| --- | --- | --- | --- |
| sample | 250 | 2026-07-02 07:53:06.458791 | 2026-07-02 07:53:06.458791 |
| remoteok | 50 | 2026-07-02 08:10:09.754637 | 2026-07-02 08:10:09.754637 |

## Cleaned Job Quality by Source

| source | cleaned_count | unknown_count | unknown_ratio | category_count |
| --- | --- | --- | --- | --- |
| sample | 250 | 0 | 0.0 | 5 |
| remoteok | 50 | 0 | 0.0 | 4 |

## Job Category Distribution by Source

| source | job_category | count | source_ratio |
| --- | --- | --- | --- |
| remoteok | Data Analyst | 34 | 0.68 |
| remoteok | DevOps Engineer | 8 | 0.16 |
| remoteok | ML Engineer | 7 | 0.14 |
| remoteok | Data Engineer | 1 | 0.02 |
| sample | DevOps Engineer | 52 | 0.208 |
| sample | Backend Engineer | 50 | 0.2 |
| sample | Data Engineer | 50 | 0.2 |
| sample | Data Analyst | 50 | 0.2 |
| sample | ML Engineer | 48 | 0.192 |

## Skill Extraction Summary by Source

| source | cleaned_count | extracted_skill_count | avg_skills_per_job |
| --- | --- | --- | --- |
| remoteok | 50 | 21 | 0.42 |
| sample | 250 | 1387 | 5.548 |

## Top Skills by Source

| source | skill_name | count |
| --- | --- | --- |
| remoteok | Excel | 14 |
| remoteok | Python | 3 |
| remoteok | SQL | 2 |
| remoteok | Spark | 1 |
| remoteok | JavaScript | 1 |
| sample | AWS | 97 |
| sample | Linux | 97 |
| sample | Docker | 92 |
| sample | SQL | 88 |
| sample | PostgreSQL | 82 |
| sample | MySQL | 81 |
| sample | Kubernetes | 79 |
| sample | Python | 76 |
| sample | Pandas | 62 |
| sample | Kafka | 52 |
| sample | Redis | 52 |
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
| remoteok | Data Analyst | 32 | 0.2545 | 32 | 1.0 |
| remoteok | ML Engineer | 11 | 0.2288 | 11 | 1.0 |
| remoteok | Backend Engineer | 5 | 0.227 | 5 | 1.0 |
| remoteok | Data Engineer | 2 | 0.2357 | 2 | 1.0 |
| sample | DevOps Engineer | 50 | 0.7252 | 3 | 0.06 |
| sample | ML Engineer | 50 | 0.6656 | 8 | 0.16 |
| sample | Backend Engineer | 50 | 0.8264 | 0 | 0.0 |
| sample | Data Engineer | 50 | 0.7557 | 0 | 0.0 |
| sample | Data Analyst | 50 | 0.8008 | 0 | 0.0 |
