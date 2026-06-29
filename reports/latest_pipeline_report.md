# JobSkill MLOps Pipeline Report

- Generated at: `2026-06-29 05:55:56`

This report summarizes model registry, prediction lineage, and pipeline check results.

## Latest Promoted Model

| id | model_name | run_id | accuracy | f1_weighted | status | promoted_model_path | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | job_classifier | 472340fc8ca14b50a382dd46f61108bf | 1.0 | 1.0 | PROMOTED | models/best/job_classifier.pkl | 2026-06-26 06:30:29.537676 |

## Model Registry History

| id | model_name | run_id_short | accuracy | f1_weighted | status | message | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | job_classifier | 4befd5bea450 | 1.0 | 1.0 | REJECTED | Current model was not promoted. current f1_weighted=1.0000, best f1_weighted=1.0000, current accuracy=1.0000, best accuracy=1.0000. | 2026-06-26 07:53:51.288972 |
| 3 | job_classifier | 0fd6133b2154 | 1.0 | 1.0 | REJECTED | Current model was not promoted. current f1_weighted=1.0000, best f1_weighted=1.0000, current accuracy=1.0000, best accuracy=1.0000. | 2026-06-26 06:50:44.870308 |
| 2 | job_classifier | c913334225d5 | 1.0 | 1.0 | REJECTED | Current model was not promoted. current f1_weighted=1.0000, best f1_weighted=1.0000, current accuracy=1.0000, best accuracy=1.0000. | 2026-06-26 06:32:03.180113 |
| 1 | job_classifier | 472340fc8ca1 | 1.0 | 1.0 | PROMOTED | No existing promoted model. Promoting current model. | 2026-06-26 06:30:29.537676 |

## Prediction Lineage Summary

| model_name | model_run_id_short | model_registry_id | registry_status | registry_accuracy | registry_f1_weighted | prediction_count | avg_confidence | first_predicted_at | last_predicted_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 1.0 | 250 | 0.7548 | 2026-06-26 07:53:54.949643 | 2026-06-26 07:53:54.949643 |

## Latest Predictions

| id | job_post_id | predicted_category | confidence | model_name | model_run_id_short | model_registry_id | registry_status | registry_f1_weighted | predicted_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 250 | 250 | Data Analyst | 0.8588 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 249 | 249 | ML Engineer | 0.7096 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 248 | 248 | Backend Engineer | 0.881 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 247 | 247 | DevOps Engineer | 0.777 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 246 | 246 | DevOps Engineer | 0.7126 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 245 | 245 | Data Analyst | 0.7905 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 244 | 244 | DevOps Engineer | 0.6869 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 243 | 243 | Data Engineer | 0.812 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 242 | 242 | ML Engineer | 0.5521 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 241 | 241 | DevOps Engineer | 0.7904 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 240 | 240 | Backend Engineer | 0.8704 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 239 | 239 | Data Analyst | 0.8572 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 238 | 238 | Data Analyst | 0.7863 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 237 | 237 | Data Engineer | 0.6926 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 236 | 236 | Data Engineer | 0.8408 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 235 | 235 | Data Engineer | 0.8498 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 234 | 234 | Backend Engineer | 0.8526 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 233 | 233 | Data Analyst | 0.7902 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 232 | 232 | Data Analyst | 0.8383 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |
| 231 | 231 | ML Engineer | 0.5994 | job_classifier | 472340fc8ca1 | 1 | PROMOTED | 1.0 | 2026-06-26 07:53:54.949643 |

## Prediction Category Distribution

| model_name | model_run_id_short | model_registry_id | predicted_category | prediction_count | avg_confidence |
| --- | --- | --- | --- | --- | --- |
| job_classifier | 472340fc8ca1 | 1 | Data Analyst | 50 | 0.8008 |
| job_classifier | 472340fc8ca1 | 1 | Backend Engineer | 50 | 0.8264 |
| job_classifier | 472340fc8ca1 | 1 | ML Engineer | 50 | 0.6656 |
| job_classifier | 472340fc8ca1 | 1 | Data Engineer | 50 | 0.7557 |
| job_classifier | 472340fc8ca1 | 1 | DevOps Engineer | 50 | 0.7252 |

## Check Result Summary

| check_type | status | check_count | latest_checked_at |
| --- | --- | --- | --- |
| DATA_QUALITY | FAIL | 5 | 2026-06-26 06:12:21.333917 |
| DATA_QUALITY | PASS | 37 | 2026-06-26 07:53:21.472839 |
| MODEL_PERFORMANCE | FAIL | 1 | 2026-06-26 06:12:53.224724 |
| MODEL_PERFORMANCE | PASS | 11 | 2026-06-26 07:53:48.362594 |

## Latest Check Details

| check_type | check_name | status | metric_value | threshold_value | message | task_id | checked_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MODEL_PERFORMANCE | f1_weighted | PASS | 1.0 | 0.7 | f1_weighted=1.0000, required>=0.7000, run_id=4befd5bea4504aba8e8af48d9ab45fe3 | check_model_performance | 2026-06-26 07:53:48.362594 |
| MODEL_PERFORMANCE | accuracy | PASS | 1.0 | 0.7 | accuracy=1.0000, required>=0.7000, run_id=4befd5bea4504aba8e8af48d9ab45fe3 | check_model_performance | 2026-06-26 07:53:48.362594 |
| DATA_QUALITY | unknown_ratio | PASS |  |  | unknown count = 80, unknown ratio = 0.3200, allowed <= 0.5 | check_training_data | 2026-06-26 07:53:21.472839 |
| DATA_QUALITY | category_diversity | PASS |  |  | distinct category count = 6, required >= 2 | check_training_data | 2026-06-26 07:53:21.472839 |
| DATA_QUALITY | job_category_not_empty | PASS |  |  | empty job_category count = 0 | check_training_data | 2026-06-26 07:53:21.472839 |
| DATA_QUALITY | text_for_model_not_empty | PASS |  |  | empty text_for_model count = 0 | check_training_data | 2026-06-26 07:53:21.472839 |
| DATA_QUALITY | job_post_skills_count | PASS |  |  | job_post_skills count = 1387 | check_training_data | 2026-06-26 07:53:21.472839 |
| DATA_QUALITY | cleaned_job_posts_count | PASS |  |  | cleaned_job_posts count = 250, required >= 50 | check_training_data | 2026-06-26 07:53:21.472839 |
| DATA_QUALITY | raw_job_posts_count | PASS |  |  | raw_job_posts count = 250 | check_training_data | 2026-06-26 07:53:21.472839 |
| MODEL_PERFORMANCE | f1_weighted | PASS | 1.0 | 0.7 | f1_weighted=1.0000, required>=0.7000, run_id=0fd6133b21544df48c40af529f4e70d4 | check_model_performance | 2026-06-26 06:50:42.428271 |
| MODEL_PERFORMANCE | accuracy | PASS | 1.0 | 0.7 | accuracy=1.0000, required>=0.7000, run_id=0fd6133b21544df48c40af529f4e70d4 | check_model_performance | 2026-06-26 06:50:42.428271 |
| DATA_QUALITY | unknown_ratio | PASS |  |  | unknown count = 80, unknown ratio = 0.3200, allowed <= 0.5 | check_training_data | 2026-06-26 06:50:26.145995 |
| DATA_QUALITY | category_diversity | PASS |  |  | distinct category count = 6, required >= 2 | check_training_data | 2026-06-26 06:50:26.145995 |
| DATA_QUALITY | job_category_not_empty | PASS |  |  | empty job_category count = 0 | check_training_data | 2026-06-26 06:50:26.145995 |
| DATA_QUALITY | text_for_model_not_empty | PASS |  |  | empty text_for_model count = 0 | check_training_data | 2026-06-26 06:50:26.145995 |
| DATA_QUALITY | job_post_skills_count | PASS |  |  | job_post_skills count = 1387 | check_training_data | 2026-06-26 06:50:26.145995 |
| DATA_QUALITY | cleaned_job_posts_count | PASS |  |  | cleaned_job_posts count = 250, required >= 50 | check_training_data | 2026-06-26 06:50:26.145995 |
| DATA_QUALITY | raw_job_posts_count | PASS |  |  | raw_job_posts count = 250 | check_training_data | 2026-06-26 06:50:26.145995 |
| DATA_QUALITY | unknown_ratio | PASS |  |  | unknown count = 80, unknown ratio = 0.3200, allowed <= 0.5 |  | 2026-06-26 06:49:50.540889 |
| DATA_QUALITY | category_diversity | PASS |  |  | distinct category count = 6, required >= 2 |  | 2026-06-26 06:49:50.540889 |
| DATA_QUALITY | job_category_not_empty | PASS |  |  | empty job_category count = 0 |  | 2026-06-26 06:49:50.540889 |
| DATA_QUALITY | text_for_model_not_empty | PASS |  |  | empty text_for_model count = 0 |  | 2026-06-26 06:49:50.540889 |
| DATA_QUALITY | job_post_skills_count | PASS |  |  | job_post_skills count = 1387 |  | 2026-06-26 06:49:50.540889 |
| DATA_QUALITY | cleaned_job_posts_count | PASS |  |  | cleaned_job_posts count = 250, required >= 50 |  | 2026-06-26 06:49:50.540889 |
| DATA_QUALITY | raw_job_posts_count | PASS |  |  | raw_job_posts count = 250 |  | 2026-06-26 06:49:50.540889 |
| MODEL_PERFORMANCE | f1_weighted | PASS | 1.0 | 0.7 | f1_weighted=1.0000, required>=0.7000, run_id=c913334225d546e0a79b0f5634b4977b | check_model_performance | 2026-06-26 06:32:00.136763 |
| MODEL_PERFORMANCE | accuracy | PASS | 1.0 | 0.7 | accuracy=1.0000, required>=0.7000, run_id=c913334225d546e0a79b0f5634b4977b | check_model_performance | 2026-06-26 06:32:00.136763 |
| DATA_QUALITY | unknown_ratio | PASS |  |  | unknown count = 80, unknown ratio = 0.3200, allowed <= 0.5 | check_training_data | 2026-06-26 06:31:41.316639 |
| DATA_QUALITY | category_diversity | PASS |  |  | distinct category count = 6, required >= 2 | check_training_data | 2026-06-26 06:31:41.316639 |
| DATA_QUALITY | job_category_not_empty | PASS |  |  | empty job_category count = 0 | check_training_data | 2026-06-26 06:31:41.316639 |

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
| REJECTED | 3 | 1.0 | 1.0 | 2026-06-26 07:53:51.288972 |
