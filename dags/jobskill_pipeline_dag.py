from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator


default_args = {
    "owner": "bae",
    "retries": 0,
}


def run_generate_sample_jobs():
    from scripts.generate_sample_jobs import main

    main()


def run_load_raw_jobs():
    from src.ingestion.load_raw_jobs import main

    main()


def run_preprocess_jobs():
    from src.preprocessing.preprocess_db import main

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


def run_promote_model():
    from src.training.promote_model import main

    main()


def run_batch_inference():
    from src.inference.batch_inference import main

    main()


def run_generate_pipeline_report():
    from src.reporting.generate_pipeline_report import main

    main()


with DAG(
    dag_id="jobskill_mlops_pipeline",
    description="JobSkill MLOps pipeline with validation, model promotion, lineage, and reporting",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["jobskill", "mlops", "postgresql", "mlflow"],
) as dag:

    generate_sample_jobs = PythonOperator(
        task_id="generate_sample_jobs",
        python_callable=run_generate_sample_jobs,
    )

    load_raw_jobs = PythonOperator(
        task_id="load_raw_jobs",
        python_callable=run_load_raw_jobs,
    )

    preprocess_jobs = PythonOperator(
        task_id="preprocess_jobs",
        python_callable=run_preprocess_jobs,
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

    promote_model = PythonOperator(
        task_id="promote_model",
        python_callable=run_promote_model,
    )

    batch_inference = PythonOperator(
        task_id="batch_inference",
        python_callable=run_batch_inference,
    )

    generate_pipeline_report = PythonOperator(
        task_id="generate_pipeline_report",
        python_callable=run_generate_pipeline_report,
    )

    (
        generate_sample_jobs
        >> load_raw_jobs
        >> preprocess_jobs
        >> check_training_data
        >> train_model
        >> check_model_performance
        >> promote_model
        >> batch_inference
        >> generate_pipeline_report
    )