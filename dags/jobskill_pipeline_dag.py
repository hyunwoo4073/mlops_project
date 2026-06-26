from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


PROJECT_ROOT = "/opt/airflow/project"
PYTHON_BIN = "python"


default_args = {
    "owner": "bae",
    "retries": 0,
}


with DAG(
    dag_id="jobskill_mlops_pipeline",
    description="JobSkill MLOps pipeline with PostgreSQL and MLflow",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["jobskill", "mlops", "postgresql", "mlflow"],
) as dag:

    generate_sample_jobs = BashOperator(
        task_id="generate_sample_jobs",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON_BIN} scripts/generate_sample_jobs.py",
    )

    load_raw_jobs = BashOperator(
        task_id="load_raw_jobs",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON_BIN} src/ingestion/load_raw_jobs.py",
    )

    preprocess_jobs = BashOperator(
        task_id="preprocess_jobs",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON_BIN} src/preprocessing/preprocess_db.py",
    )

    train_model = BashOperator(
        task_id="train_model",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON_BIN} src/training/train_baseline.py",
    )

    batch_inference = BashOperator(
        task_id="batch_inference",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON_BIN} src/inference/batch_inference.py",
    )

    check_training_data = BashOperator(
        task_id="check_training_data",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON_BIN} src/quality/check_training_data.py",
    )

    check_model_performance = BashOperator(
        task_id="check_model_performance",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON_BIN} src/quality/check_model_performance.py",
    )

    promote_model = BashOperator(
        task_id="promote_model",
        bash_command=f"cd {PROJECT_ROOT} && {PYTHON_BIN} src/training/promote_model.py",
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
    )