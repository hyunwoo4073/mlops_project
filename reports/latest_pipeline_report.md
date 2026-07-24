# JobSkill MLOps Pipeline Report

- Generated at: `2026-07-24 07:42:48`

This report summarizes model registry, prediction lineage, and pipeline check results.

## Latest Promoted Model

| id | model_name | run_id | accuracy | f1_weighted | status | promoted_model_path | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | job_classifier | c9070684499a477a8609d1ccc2c9c168 | 0.9556 | 0.9558 | PROMOTED | models/best/job_classifier.pkl | 2026-07-24 07:42:39.471435 |

## Model Registry History

| id | model_name | run_id_short | accuracy | f1_weighted | status | message | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | job_classifier | c9070684499a | 0.9556 | 0.9558 | PROMOTED | No existing promoted model. Promoting current model. | 2026-07-24 07:42:39.471435 |

## Prediction Lineage Summary

| model_name | model_run_id_short | model_registry_id | registry_status | registry_accuracy | registry_f1_weighted | prediction_count | avg_confidence | first_predicted_at | last_predicted_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| job_classifier | c9070684499a | 1 | PROMOTED | 0.9556 | 0.9558 | 300 | 0.769 | 2026-07-24 07:42:45.138902 | 2026-07-24 07:42:45.138902 |

## Latest Predictions

| id | job_post_id | predicted_category | confidence | model_name | model_run_id_short | model_registry_id | registry_status | registry_f1_weighted | predicted_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | 300 | ML Engineer | 0.2786 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 299 | 299 | Data Analyst | 0.4442 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 298 | 298 | Data Analyst | 0.6461 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 297 | 297 | Data Analyst | 0.5393 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 296 | 296 | Data Analyst | 0.3222 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 295 | 295 | Backend Engineer | 0.3915 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 294 | 294 | Backend Engineer | 0.4571 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 293 | 293 | Data Analyst | 0.4347 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 292 | 292 | Data Analyst | 0.4172 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 291 | 291 | Data Analyst | 0.6349 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 290 | 290 | Data Analyst | 0.6766 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 289 | 289 | Backend Engineer | 0.5208 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 288 | 288 | Data Analyst | 0.4768 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 287 | 287 | Backend Engineer | 0.5055 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 286 | 286 | Backend Engineer | 0.4728 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 285 | 285 | Data Analyst | 0.4964 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 284 | 284 | Data Analyst | 0.6346 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 283 | 283 | DevOps Engineer | 0.3241 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 282 | 282 | Backend Engineer | 0.456 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |
| 281 | 281 | Backend Engineer | 0.3063 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-07-24 07:42:45.138902 |

## Prediction Category Distribution

| model_name | model_run_id_short | model_registry_id | predicted_category | prediction_count | avg_confidence |
| --- | --- | --- | --- | --- | --- |
| job_classifier | c9070684499a | 1 | Data Analyst | 81 | 0.7273 |
| job_classifier | c9070684499a | 1 | Backend Engineer | 67 | 0.7398 |
| job_classifier | c9070684499a | 1 | DevOps Engineer | 51 | 0.8216 |
| job_classifier | c9070684499a | 1 | ML Engineer | 51 | 0.7791 |
| job_classifier | c9070684499a | 1 | Data Engineer | 50 | 0.8116 |

## Check Result Summary

| check_type | status | check_count | latest_checked_at |
| --- | --- | --- | --- |
| DATA_CONTRACT | PASS | 31 | 2026-07-24 07:42:08.641061 |
| DATA_QUALITY | PASS | 7 | 2026-07-24 07:42:09.266441 |
| MODEL_CARD_CONSISTENCY | PASS | 15 | 2026-07-24 07:42:43.339305 |
| MODEL_CLASS_PERFORMANCE | PASS | 16 | 2026-07-24 07:42:37.582524 |
| MODEL_PERFORMANCE | PASS | 2 | 2026-07-24 07:42:35.367422 |
| PREDICTION_DRIFT | PASS | 3 | 2026-07-24 07:42:47.173482 |
| PREDICTION_QUALITY | PASS | 4 | 2026-07-24 07:42:46.101567 |

## Latest Check Details

| check_type | check_name | status | metric_value | threshold_value | message | task_id | checked_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PREDICTION_DRIFT | prediction_distribution_psi | PASS | 0.0047 | 0.25 | prediction_distribution_psi=0.0047, allowed <= 0.2500 |  | 2026-07-24 07:42:47.173482 |
| PREDICTION_DRIFT | prediction_distribution_rows | PASS | 300.0 | 1.0 | prediction_total=300, required >= 1 |  | 2026-07-24 07:42:47.173482 |
| PREDICTION_DRIFT | label_distribution_rows | PASS | 300.0 | 1.0 | label_total=300, required >= 1 |  | 2026-07-24 07:42:47.173482 |
| PREDICTION_QUALITY | null_confidence_count | PASS | 0.0 | 0.0 | null_confidence_count=0, required = 0 | check_prediction_quality | 2026-07-24 07:42:46.101567 |
| PREDICTION_QUALITY | low_confidence_ratio | PASS | 0.1133 | 0.4 | low_confidence_count=34, prediction_count=300, low_confidence_ratio=0.1133, allowed <= 0.4000 | check_prediction_quality | 2026-07-24 07:42:46.101567 |
| PREDICTION_QUALITY | avg_prediction_confidence | PASS | 0.769 | 0.6 | avg_confidence=0.7690, required >= 0.6000 | check_prediction_quality | 2026-07-24 07:42:46.101567 |
| PREDICTION_QUALITY | prediction_count | PASS | 300.0 | 1.0 | prediction_count=300, required >= 1 | check_prediction_quality | 2026-07-24 07:42:46.101567 |
| MODEL_CARD_CONSISTENCY | operational_notes | PASS |  |  | Model Card section exists: ## 6. Operational Notes | check_model_card_consistency | 2026-07-24 07:42:43.339305 |
| MODEL_CARD_CONSISTENCY | model_lifecycle | PASS |  |  | Model Card section exists: ## 5. Model Lifecycle | check_model_card_consistency | 2026-07-24 07:42:43.329891 |
| MODEL_CARD_CONSISTENCY | mlflow_metadata | PASS |  |  | Model Card section exists: ## 4. MLflow Run Metadata | check_model_card_consistency | 2026-07-24 07:42:43.320208 |
| MODEL_CARD_CONSISTENCY | training_dataset | PASS |  |  | Model Card section exists: ## 3. Training Dataset | check_model_card_consistency | 2026-07-24 07:42:43.309832 |
| MODEL_CARD_CONSISTENCY | evaluation_details | PASS |  |  | Model Card section exists: ### Evaluation Details | check_model_card_consistency | 2026-07-24 07:42:43.296429 |
| MODEL_CARD_CONSISTENCY | performance | PASS |  |  | Model Card section exists: ## 2. Performance | check_model_card_consistency | 2026-07-24 07:42:43.287497 |
| MODEL_CARD_CONSISTENCY | model_summary | PASS |  |  | Model Card section exists: ## 1. Model Summary | check_model_card_consistency | 2026-07-24 07:42:43.276383 |
| MODEL_CARD_CONSISTENCY | document_title | PASS |  |  | Model Card section exists: # JobSkill Promoted Model Card | check_model_card_consistency | 2026-07-24 07:42:43.266652 |
| MODEL_CARD_CONSISTENCY | training_dataset_row_count | PASS |  |  | Model Card contains training dataset row count: 300 | check_model_card_consistency | 2026-07-24 07:42:43.257585 |
| MODEL_CARD_CONSISTENCY | training_dataset_hash | PASS |  |  | Model Card contains training dataset hash: c9e0d7e389bf902596db2ed93e7a2e95df74f15bbcbe46be4c5bfd94e701dda7 | check_model_card_consistency | 2026-07-24 07:42:43.247855 |
| MODEL_CARD_CONSISTENCY | f1_weighted | PASS |  |  | Model Card contains current promoted f1_weighted: 0.9558 | check_model_card_consistency | 2026-07-24 07:42:43.238343 |
| MODEL_CARD_CONSISTENCY | accuracy | PASS |  |  | Model Card contains current promoted accuracy: 0.9556 | check_model_card_consistency | 2026-07-24 07:42:43.228524 |
| MODEL_CARD_CONSISTENCY | run_id | PASS |  |  | Model Card contains current promoted MLflow run_id: c9070684499a477a8609d1ccc2c9c168 | check_model_card_consistency | 2026-07-24 07:42:43.218868 |
| MODEL_CARD_CONSISTENCY | model_name | PASS |  |  | Model Card contains current promoted model_name: job_classifier | check_model_card_consistency | 2026-07-24 07:42:43.208167 |
| MODEL_CARD_CONSISTENCY | model_registry_id | PASS |  |  | Model Card contains current promoted model_registry_id: 1 | check_model_card_consistency | 2026-07-24 07:42:43.180122 |
| MODEL_CLASS_PERFORMANCE | ML_Engineer.f1 | PASS | 0.9677 | 0.7 | ML Engineer f1 passed. f1=0.9677, threshold=0.7000 | check_model_class_performance | 2026-07-24 07:42:37.582524 |
| MODEL_CLASS_PERFORMANCE | ML_Engineer.recall | PASS | 1.0 | 0.6 | ML Engineer recall passed. recall=1.0000, threshold=0.6000 | check_model_class_performance | 2026-07-24 07:42:37.568986 |
| MODEL_CLASS_PERFORMANCE | ML_Engineer.support | PASS | 15.0 | 1.0 | ML Engineer support passed. support=15, threshold=1 | check_model_class_performance | 2026-07-24 07:42:37.558170 |
| MODEL_CLASS_PERFORMANCE | DevOps_Engineer.f1 | PASS | 0.9697 | 0.7 | DevOps Engineer f1 passed. f1=0.9697, threshold=0.7000 | check_model_class_performance | 2026-07-24 07:42:37.544311 |
| MODEL_CLASS_PERFORMANCE | DevOps_Engineer.recall | PASS | 0.9412 | 0.6 | DevOps Engineer recall passed. recall=0.9412, threshold=0.6000 | check_model_class_performance | 2026-07-24 07:42:37.530223 |
| MODEL_CLASS_PERFORMANCE | DevOps_Engineer.support | PASS | 17.0 | 1.0 | DevOps Engineer support passed. support=17, threshold=1 | check_model_class_performance | 2026-07-24 07:42:37.521420 |
| MODEL_CLASS_PERFORMANCE | Data_Engineer.f1 | PASS | 0.9655 | 0.7 | Data Engineer f1 passed. f1=0.9655, threshold=0.7000 | check_model_class_performance | 2026-07-24 07:42:37.513062 |
| MODEL_CLASS_PERFORMANCE | Data_Engineer.recall | PASS | 0.9333 | 0.6 | Data Engineer recall passed. recall=0.9333, threshold=0.6000 | check_model_class_performance | 2026-07-24 07:42:37.501143 |

## Failed Checks

_No rows._

## Model Promotion Summary

| status | count | avg_accuracy | avg_f1_weighted | latest_created_at |
| --- | --- | --- | --- | --- |
| PROMOTED | 1 | 0.9556 | 0.9558 | 2026-07-24 07:42:39.471435 |

## Raw Job Count by Source

| source | raw_count | first_crawled_at | latest_crawled_at |
| --- | --- | --- | --- |
| sample | 250 | 2026-07-24 07:42:04.417891 | 2026-07-24 07:42:04.417891 |
| remoteok | 50 | 2026-07-24 07:42:06.537394 | 2026-07-24 07:42:06.537394 |

## Cleaned Job Quality by Source

| source | cleaned_count | unknown_count | unknown_ratio | category_count |
| --- | --- | --- | --- | --- |
| sample | 250 | 0 | 0.0 | 5 |
| remoteok | 50 | 0 | 0.0 | 5 |

## Job Category Distribution by Source

| source | job_category | count | source_ratio |
| --- | --- | --- | --- |
| remoteok | Data Analyst | 25 | 0.5 |
| remoteok | Backend Engineer | 16 | 0.32 |
| remoteok | DevOps Engineer | 6 | 0.12 |
| remoteok | ML Engineer | 2 | 0.04 |
| remoteok | Data Engineer | 1 | 0.02 |
| sample | DevOps Engineer | 52 | 0.208 |
| sample | Backend Engineer | 50 | 0.2 |
| sample | Data Analyst | 50 | 0.2 |
| sample | Data Engineer | 50 | 0.2 |
| sample | ML Engineer | 48 | 0.192 |

## Skill Extraction Summary by Source

| source | cleaned_count | extracted_skill_count | avg_skills_per_job |
| --- | --- | --- | --- |
| remoteok | 50 | 44 | 0.88 |
| sample | 250 | 1387 | 5.548 |

## Top Skills by Source

| source | skill_name | count |
| --- | --- | --- |
| remoteok | Excel | 21 |
| remoteok | SQL | 7 |
| remoteok | Java | 7 |
| remoteok | JavaScript | 5 |
| remoteok | Python | 4 |
| sample | Linux | 97 |
| sample | AWS | 97 |
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
| sample | TensorFlow | 29 |
| sample | Elasticsearch | 29 |
| sample | GCP | 28 |
| sample | PyTorch | 27 |
| sample | Prometheus | 26 |
| sample | Java | 25 |
| sample | Grafana | 25 |
| sample | Flink | 25 |
| sample | Spark | 25 |
| sample | Excel | 25 |
| sample | scikit-learn | 24 |
| sample | FastAPI | 23 |
| sample | Airflow | 22 |
| sample | Spring Boot | 22 |
| sample | Hive | 21 |
| sample | MLflow | 18 |
| sample | dbt | 18 |
| sample | Hadoop | 15 |

## Prediction Summary by Source

| source | predicted_category | prediction_count | avg_confidence | low_confidence_count | low_confidence_ratio |
| --- | --- | --- | --- | --- | --- |
| remoteok | Data Analyst | 31 | 0.5609 | 15 | 0.4839 |
| remoteok | Backend Engineer | 17 | 0.4588 | 17 | 1.0 |
| remoteok | DevOps Engineer | 1 | 0.3241 | 1 | 1.0 |
| remoteok | ML Engineer | 1 | 0.2786 | 1 | 1.0 |
| sample | DevOps Engineer | 50 | 0.8315 | 0 | 0.0 |
| sample | Backend Engineer | 50 | 0.8354 | 0 | 0.0 |
| sample | Data Engineer | 50 | 0.8116 | 0 | 0.0 |
| sample | ML Engineer | 50 | 0.7891 | 0 | 0.0 |
| sample | Data Analyst | 50 | 0.8305 | 0 | 0.0 |
