# JobSkill MLOps Pipeline Report

- Generated at: `2026-08-05 05:01:33`

This report summarizes model registry, prediction lineage, and pipeline check results.

## Latest Promoted Model

| id | model_name | run_id | accuracy | f1_weighted | status | promoted_model_path | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | job_classifier | c9070684499a477a8609d1ccc2c9c168 | 0.9556 | 0.9558 | PROMOTED | models/best/job_classifier.pkl | 2026-07-24 07:42:39.471435 |

## Model Registry History

| id | model_name | run_id_short | accuracy | f1_weighted | status | message | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | job_classifier | e4a7e306d45d | 0.8739 | 0.8736 | REJECTED | Current model was not promoted. current f1_weighted=0.8736, best f1_weighted=0.9558, current accuracy=0.8739, best accuracy=0.9556. | 2026-08-05 05:01:24.706285 |
| 2 | job_classifier | bb2f342e322d | 0.8762 | 0.8792 | REJECTED | Current model was not promoted. current f1_weighted=0.8792, best f1_weighted=0.9558, current accuracy=0.8762, best accuracy=0.9556. | 2026-08-04 08:23:13.850942 |
| 1 | job_classifier | c9070684499a | 0.9556 | 0.9558 | PROMOTED | No existing promoted model. Promoting current model. | 2026-07-24 07:42:39.471435 |

## Prediction Lineage Summary

| model_name | model_run_id_short | model_registry_id | registry_status | registry_accuracy | registry_f1_weighted | prediction_count | avg_confidence | first_predicted_at | last_predicted_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| job_classifier | c9070684499a | 1 | PROMOTED | 0.9556 | 0.9558 | 370 | 0.7185 | 2026-08-05 05:01:30.637370 | 2026-08-05 05:01:30.637370 |

## Latest Predictions

| id | job_post_id | predicted_category | confidence | model_name | model_run_id_short | model_registry_id | registry_status | registry_f1_weighted | predicted_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 370 | 370 | Data Analyst | 0.6795 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 369 | 369 | Data Analyst | 0.7035 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 368 | 368 | Data Analyst | 0.6534 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 367 | 367 | Backend Engineer | 0.394 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 366 | 366 | Backend Engineer | 0.4166 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 365 | 365 | Backend Engineer | 0.4166 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 364 | 364 | Data Analyst | 0.4674 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 363 | 363 | Data Analyst | 0.5234 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 362 | 362 | Backend Engineer | 0.3062 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 361 | 361 | Backend Engineer | 0.3954 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 360 | 360 | Data Analyst | 0.4101 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 359 | 359 | Data Analyst | 0.5503 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 358 | 358 | Data Analyst | 0.5882 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 357 | 357 | Data Analyst | 0.5074 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 356 | 356 | Data Analyst | 0.4681 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 355 | 355 | Data Analyst | 0.5584 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 354 | 354 | Data Analyst | 0.4993 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 353 | 353 | Data Analyst | 0.482 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 352 | 352 | Data Analyst | 0.6269 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |
| 351 | 351 | Backend Engineer | 0.4644 | job_classifier | c9070684499a | 1 | PROMOTED | 0.9558 | 2026-08-05 05:01:30.637370 |

## Prediction Category Distribution

| model_name | model_run_id_short | model_registry_id | predicted_category | prediction_count | avg_confidence |
| --- | --- | --- | --- | --- | --- |
| job_classifier | c9070684499a | 1 | Data Analyst | 138 | 0.6442 |
| job_classifier | c9070684499a | 1 | Backend Engineer | 80 | 0.6841 |
| job_classifier | c9070684499a | 1 | DevOps Engineer | 51 | 0.8216 |
| job_classifier | c9070684499a | 1 | ML Engineer | 51 | 0.7791 |
| job_classifier | c9070684499a | 1 | Data Engineer | 50 | 0.8116 |

## Check Result Summary

| check_type | status | check_count | latest_checked_at |
| --- | --- | --- | --- |
| DATA_CONTRACT | PASS | 93 | 2026-08-05 05:00:52.590236 |
| DATA_QUALITY | PASS | 21 | 2026-08-05 05:00:53.321198 |
| MODEL_CARD_CONSISTENCY | PASS | 45 | 2026-08-05 05:01:28.772724 |
| MODEL_CLASS_PERFORMANCE | PASS | 48 | 2026-08-05 05:01:22.590204 |
| MODEL_PERFORMANCE | PASS | 6 | 2026-08-05 05:01:20.858684 |
| PREDICTION_DRIFT | PASS | 9 | 2026-08-05 05:01:32.587079 |
| PREDICTION_QUALITY | PASS | 12 | 2026-08-05 05:01:31.471031 |
| PRODUCTION_FEEDBACK | PASS | 66 | 2026-08-04 08:09:12.354584 |
| PRODUCTION_FEEDBACK | SKIPPED | 1 | 2026-08-05 04:30:58.764560 |
| RETRAINING_CANDIDATE | PASS | 84 | 2026-08-04 08:09:13.895839 |
| RETRAINING_CANDIDATE | SKIPPED | 6 | 2026-08-05 04:31:00.769765 |
| RETRAINING_STRATEGY | PASS | 24 | 2026-08-04 08:08:47.929844 |
| RETRAINING_STRATEGY | WARN | 9 | 2026-08-04 08:08:47.929844 |
| TRAINING_COST | PASS | 12 | 2026-08-05 05:01:17.866329 |

## Latest Check Details

| check_type | check_name | status | metric_value | threshold_value | message | task_id | checked_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PREDICTION_DRIFT | prediction_distribution_psi | PASS | 0.0315 | 0.25 | prediction_distribution_psi=0.0315, allowed <= 0.2500 |  | 2026-08-05 05:01:32.587079 |
| PREDICTION_DRIFT | prediction_distribution_rows | PASS | 370.0 | 1.0 | prediction_total=370, required >= 1 |  | 2026-08-05 05:01:32.587079 |
| PREDICTION_DRIFT | label_distribution_rows | PASS | 370.0 | 1.0 | label_total=370, required >= 1 |  | 2026-08-05 05:01:32.587079 |
| PREDICTION_QUALITY | null_confidence_count | PASS | 0.0 | 0.0 | null_confidence_count=0, required = 0 | check_prediction_quality | 2026-08-05 05:01:31.471031 |
| PREDICTION_QUALITY | low_confidence_ratio | PASS | 0.2568 | 0.4 | low_confidence_count=95, prediction_count=370, low_confidence_ratio=0.2568, allowed <= 0.4000 | check_prediction_quality | 2026-08-05 05:01:31.471031 |
| PREDICTION_QUALITY | avg_prediction_confidence | PASS | 0.7185 | 0.6 | avg_confidence=0.7185, required >= 0.6000 | check_prediction_quality | 2026-08-05 05:01:31.471031 |
| PREDICTION_QUALITY | prediction_count | PASS | 370.0 | 1.0 | prediction_count=370, required >= 1 | check_prediction_quality | 2026-08-05 05:01:31.471031 |
| MODEL_CARD_CONSISTENCY | operational_notes | PASS |  |  | Model Card section exists: ## 6. Operational Notes | check_model_card_consistency | 2026-08-05 05:01:28.772724 |
| MODEL_CARD_CONSISTENCY | model_lifecycle | PASS |  |  | Model Card section exists: ## 5. Model Lifecycle | check_model_card_consistency | 2026-08-05 05:01:28.759942 |
| MODEL_CARD_CONSISTENCY | mlflow_metadata | PASS |  |  | Model Card section exists: ## 4. MLflow Run Metadata | check_model_card_consistency | 2026-08-05 05:01:28.749391 |
| MODEL_CARD_CONSISTENCY | training_dataset | PASS |  |  | Model Card section exists: ## 3. Training Dataset | check_model_card_consistency | 2026-08-05 05:01:28.740632 |
| MODEL_CARD_CONSISTENCY | evaluation_details | PASS |  |  | Model Card section exists: ### Evaluation Details | check_model_card_consistency | 2026-08-05 05:01:28.728795 |
| MODEL_CARD_CONSISTENCY | performance | PASS |  |  | Model Card section exists: ## 2. Performance | check_model_card_consistency | 2026-08-05 05:01:28.715271 |
| MODEL_CARD_CONSISTENCY | model_summary | PASS |  |  | Model Card section exists: ## 1. Model Summary | check_model_card_consistency | 2026-08-05 05:01:28.704483 |
| MODEL_CARD_CONSISTENCY | document_title | PASS |  |  | Model Card section exists: # JobSkill Promoted Model Card | check_model_card_consistency | 2026-08-05 05:01:28.693017 |
| MODEL_CARD_CONSISTENCY | training_dataset_row_count | PASS |  |  | Model Card contains training dataset row count: 300 | check_model_card_consistency | 2026-08-05 05:01:28.680094 |
| MODEL_CARD_CONSISTENCY | training_dataset_hash | PASS |  |  | Model Card contains training dataset hash: c9e0d7e389bf902596db2ed93e7a2e95df74f15bbcbe46be4c5bfd94e701dda7 | check_model_card_consistency | 2026-08-05 05:01:28.666040 |
| MODEL_CARD_CONSISTENCY | f1_weighted | PASS |  |  | Model Card contains current promoted f1_weighted: 0.9558 | check_model_card_consistency | 2026-08-05 05:01:28.656239 |
| MODEL_CARD_CONSISTENCY | accuracy | PASS |  |  | Model Card contains current promoted accuracy: 0.9556 | check_model_card_consistency | 2026-08-05 05:01:28.647068 |
| MODEL_CARD_CONSISTENCY | run_id | PASS |  |  | Model Card contains current promoted MLflow run_id: c9070684499a477a8609d1ccc2c9c168 | check_model_card_consistency | 2026-08-05 05:01:28.638716 |
| MODEL_CARD_CONSISTENCY | model_name | PASS |  |  | Model Card contains current promoted model_name: job_classifier | check_model_card_consistency | 2026-08-05 05:01:28.629906 |
| MODEL_CARD_CONSISTENCY | model_registry_id | PASS |  |  | Model Card contains current promoted model_registry_id: 1 | check_model_card_consistency | 2026-08-05 05:01:28.621925 |
| MODEL_CLASS_PERFORMANCE | ML_Engineer.f1 | PASS | 0.8 | 0.7 | ML Engineer f1 passed. f1=0.8000, threshold=0.7000 | check_model_class_performance | 2026-08-05 05:01:22.590204 |
| MODEL_CLASS_PERFORMANCE | ML_Engineer.recall | PASS | 0.6667 | 0.6 | ML Engineer recall passed. recall=0.6667, threshold=0.6000 | check_model_class_performance | 2026-08-05 05:01:22.578074 |
| MODEL_CLASS_PERFORMANCE | ML_Engineer.support | PASS | 18.0 | 1.0 | ML Engineer support passed. support=18, threshold=1 | check_model_class_performance | 2026-08-05 05:01:22.565881 |
| MODEL_CLASS_PERFORMANCE | DevOps_Engineer.f1 | PASS | 0.9189 | 0.7 | DevOps Engineer f1 passed. f1=0.9189, threshold=0.7000 | check_model_class_performance | 2026-08-05 05:01:22.554747 |
| MODEL_CLASS_PERFORMANCE | DevOps_Engineer.recall | PASS | 0.85 | 0.6 | DevOps Engineer recall passed. recall=0.8500, threshold=0.6000 | check_model_class_performance | 2026-08-05 05:01:22.544434 |
| MODEL_CLASS_PERFORMANCE | DevOps_Engineer.support | PASS | 20.0 | 1.0 | DevOps Engineer support passed. support=20, threshold=1 | check_model_class_performance | 2026-08-05 05:01:22.534717 |
| MODEL_CLASS_PERFORMANCE | Data_Engineer.f1 | PASS | 0.9032 | 0.7 | Data Engineer f1 passed. f1=0.9032, threshold=0.7000 | check_model_class_performance | 2026-08-05 05:01:22.524285 |
| MODEL_CLASS_PERFORMANCE | Data_Engineer.recall | PASS | 0.8235 | 0.6 | Data Engineer recall passed. recall=0.8235, threshold=0.6000 | check_model_class_performance | 2026-08-05 05:01:22.515346 |

## Failed Checks

_No rows._

## Model Promotion Summary

| status | count | avg_accuracy | avg_f1_weighted | latest_created_at |
| --- | --- | --- | --- | --- |
| PROMOTED | 1 | 0.9556 | 0.9558 | 2026-07-24 07:42:39.471435 |
| REJECTED | 2 | 0.875 | 0.8764 | 2026-08-05 05:01:24.706285 |

## Raw Job Count by Source

| source | raw_count | first_crawled_at | latest_crawled_at |
| --- | --- | --- | --- |
| sample | 250 | 2026-07-24 07:42:04.417891 | 2026-07-24 07:42:04.417891 |
| remoteok | 120 | 2026-07-24 07:42:06.537394 | 2026-08-05 05:00:48.924405 |

## Cleaned Job Quality by Source

| source | cleaned_count | unknown_count | unknown_ratio | category_count |
| --- | --- | --- | --- | --- |
| sample | 250 | 0 | 0.0 | 5 |
| remoteok | 120 | 0 | 0.0 | 5 |

## Job Category Distribution by Source

| source | job_category | count | source_ratio |
| --- | --- | --- | --- |
| remoteok | Data Analyst | 62 | 0.5167 |
| remoteok | Backend Engineer | 26 | 0.2167 |
| remoteok | DevOps Engineer | 14 | 0.1167 |
| remoteok | ML Engineer | 12 | 0.1 |
| remoteok | Data Engineer | 6 | 0.05 |
| sample | DevOps Engineer | 52 | 0.208 |
| sample | Backend Engineer | 50 | 0.2 |
| sample | Data Engineer | 50 | 0.2 |
| sample | Data Analyst | 50 | 0.2 |
| sample | ML Engineer | 48 | 0.192 |

## Skill Extraction Summary by Source

| source | cleaned_count | extracted_skill_count | avg_skills_per_job |
| --- | --- | --- | --- |
| remoteok | 120 | 88 | 0.7333 |
| sample | 250 | 1387 | 5.548 |

## Top Skills by Source

| source | skill_name | count |
| --- | --- | --- |
| remoteok | Excel | 46 |
| remoteok | Java | 15 |
| remoteok | Linux | 7 |
| remoteok | SQL | 7 |
| remoteok | JavaScript | 6 |
| remoteok | Python | 5 |
| remoteok | TypeScript | 1 |
| remoteok | Spark | 1 |
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
| remoteok | Data Analyst | 88 | 0.5384 | 63 | 0.7159 |
| remoteok | Backend Engineer | 30 | 0.4319 | 30 | 1.0 |
| remoteok | DevOps Engineer | 1 | 0.3241 | 1 | 1.0 |
| remoteok | ML Engineer | 1 | 0.2786 | 1 | 1.0 |
| sample | DevOps Engineer | 50 | 0.8315 | 0 | 0.0 |
| sample | ML Engineer | 50 | 0.7891 | 0 | 0.0 |
| sample | Backend Engineer | 50 | 0.8354 | 0 | 0.0 |
| sample | Data Engineer | 50 | 0.8116 | 0 | 0.0 |
| sample | Data Analyst | 50 | 0.8305 | 0 | 0.0 |
