from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator


default_args = {
    "owner": "bae",
    "retries": 0,
}


def run_prepare_raw_sources():
    from src.ingestion.prepare_raw_sources import main

    main()


def run_generate_sample_jobs():
    from src.common.data_source_mode import should_use_sample_data

    if not should_use_sample_data():
        print("Skip generate_sample_jobs because DATA_SOURCE_MODE does not use sample data.")
        return

    from scripts.generate_sample_jobs import main

    main()


def run_load_raw_jobs():
    from src.common.data_source_mode import should_use_sample_data

    if not should_use_sample_data():
        print("Skip load_raw_jobs because DATA_SOURCE_MODE does not use sample data.")
        return

    from src.ingestion.load_raw_jobs import main

    main()


def run_crawl_remoteok_jobs():
    from src.common.data_source_mode import should_use_crawler_data

    if not should_use_crawler_data():
        print("Skip crawl_remoteok_jobs because DATA_SOURCE_MODE does not use crawler data.")
        return

    from src.crawling.crawl_remoteok_jobs import main

    main()


def run_preprocess_jobs():
    from src.preprocessing.preprocess_db import main

    main()


def run_check_data_contract():
    from src.quality.check_data_contract import main

    main()


def run_check_training_data():
    from src.quality.check_training_data import main

    main()


def run_train_model():
    from src.training.train_baseline import main

    main()


def run_check_model_performance():
    from src.quality.check_model_performance import main

    main()


def run_check_model_class_performance():
    from src.quality.check_model_class_performance import main

    main()


def run_promote_model():
    from src.training.promote_model import main

    main()


def run_generate_model_card():
    from src.reporting.generate_model_card import main

    main()


def run_check_model_card_consistency():
    from scripts.check_model_card_consistency import main

    main()


def run_batch_inference():
    from src.inference.batch_inference import main

    main()


def run_generate_pipeline_report():
    from src.reporting.generate_pipeline_report import main

    main()


def run_check_prediction_quality():
    from src.quality.check_prediction_quality import main

    main()


def run_notify_pipeline_status():
    from src.notification.notify_pipeline_status import main
    main()


def run_check_prediction_drift():
    from src.quality.check_prediction_drift import main
    main()

with DAG(
    dag_id="jobskill_mlops_pipeline",
    description="JobSkill MLOps pipeline with validation, model promotion, lineage, reporting, and data source modes",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["jobskill", "mlops", "postgresql", "mlflow"],
) as dag:

    prepare_raw_sources = PythonOperator(
        task_id="prepare_raw_sources",
        python_callable=run_prepare_raw_sources,
    )

    generate_sample_jobs = PythonOperator(
        task_id="generate_sample_jobs",
        python_callable=run_generate_sample_jobs,
    )

    load_raw_jobs = PythonOperator(
        task_id="load_raw_jobs",
        python_callable=run_load_raw_jobs,
    )

    crawl_remoteok_jobs = PythonOperator(
        task_id="crawl_remoteok_jobs",
        python_callable=run_crawl_remoteok_jobs,
    )

    preprocess_jobs = PythonOperator(
        task_id="preprocess_jobs",
        python_callable=run_preprocess_jobs,
    )

    check_data_contract = PythonOperator(
        task_id="check_data_contract",
        python_callable=run_check_data_contract,
    )

    check_training_data = PythonOperator(
        task_id="check_training_data",
        python_callable=run_check_training_data,
    )

    train_model = PythonOperator(
        task_id="train_model",
        python_callable=run_train_model,
    )

    check_model_performance = PythonOperator(
        task_id="check_model_performance",
        python_callable=run_check_model_performance,
    )

    check_model_class_performance = PythonOperator(
        task_id="check_model_class_performance",
        python_callable=run_check_model_class_performance,
    )

    promote_model = PythonOperator(
        task_id="promote_model",
        python_callable=run_promote_model,
    )

    generate_model_card = PythonOperator(
        task_id="generate_model_card",
        python_callable=run_generate_model_card,
    )

    check_model_card_consistency = PythonOperator(
        task_id="check_model_card_consistency",
        python_callable=run_check_model_card_consistency,
    )

    batch_inference = PythonOperator(
        task_id="batch_inference",
        python_callable=run_batch_inference,
    )

    generate_pipeline_report = PythonOperator(
        task_id="generate_pipeline_report",
        python_callable=run_generate_pipeline_report,
        trigger_rule="all_done",
    )

    notify_pipeline_status = PythonOperator(
        task_id="notify_pipeline_status",
        python_callable=run_notify_pipeline_status,
        trigger_rule="all_done",
    )

    check_prediction_quality = PythonOperator(
        task_id="check_prediction_quality",
        python_callable=run_check_prediction_quality,
    )

    check_prediction_drift = PythonOperator(
        task_id="check_prediction_drift",
        python_callable=run_check_prediction_drift,
    )

    (
        prepare_raw_sources
        >> generate_sample_jobs
        >> load_raw_jobs
        >> crawl_remoteok_jobs
        >> preprocess_jobs
        >> check_data_contract
        >> check_training_data
        >> train_model
        >> check_model_performance
        >> check_model_class_performance
        >> promote_model
        >> generate_model_card
        >> check_model_card_consistency
        >> batch_inference
        >> check_prediction_quality
        >> check_prediction_drift
        >> generate_pipeline_report
        >> notify_pipeline_status
    )