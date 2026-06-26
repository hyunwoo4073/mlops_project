from __future__ import annotations

import os

import mlflow
from mlflow.tracking import MlflowClient

from sqlalchemy import create_engine
from src.quality.check_logger import PipelineCheckLog, save_check_results

def get_required_metric(metrics: dict, name: str) -> float:
    if name not in metrics:
        raise RuntimeError(f"Required metric not found in latest MLflow run: {name}")

    return float(metrics[name])


def main() -> None:
    tracking_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        "postgresql+psycopg2://jobskill:jobskill@postgres:5432/mlflow",
    )

    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "jobskill")
    db_user = os.getenv("DB_USER", "jobskill")
    db_password = os.getenv("DB_PASSWORD", "jobskill")

    database_url = (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "jobskill-classifier")

    min_accuracy = float(os.getenv("MIN_MODEL_ACCURACY", "0.7"))
    min_f1_weighted = float(os.getenv("MIN_MODEL_F1_WEIGHTED", "0.7"))

    mlflow.set_tracking_uri(tracking_uri)

    client = MlflowClient(tracking_uri=tracking_uri)

    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise RuntimeError(f"MLflow experiment not found: {experiment_name}")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["attributes.start_time DESC"],
        max_results=1,
    )

    if not runs:
        raise RuntimeError(f"No MLflow runs found in experiment: {experiment_name}")

    latest_run = runs[0]
    run_id = latest_run.info.run_id
    metrics = latest_run.data.metrics

    accuracy = get_required_metric(metrics, "accuracy")
    f1_weighted = get_required_metric(metrics, "f1_weighted")

    print("\n[Latest MLflow Run]")
    print(f"experiment_name : {experiment_name}")
    print(f"run_id          : {run_id}")
    print(f"accuracy        : {accuracy:.4f}")
    print(f"f1_weighted     : {f1_weighted:.4f}")

    print("\n[Model Performance Thresholds]")
    print(f"MIN_MODEL_ACCURACY    : {min_accuracy:.4f}")
    print(f"MIN_MODEL_F1_WEIGHTED : {min_f1_weighted:.4f}")

    failed_checks = []

    if accuracy < min_accuracy:
        failed_checks.append(
            f"accuracy={accuracy:.4f} < required={min_accuracy:.4f}"
        )

    if f1_weighted < min_f1_weighted:
        failed_checks.append(
            f"f1_weighted={f1_weighted:.4f} < required={min_f1_weighted:.4f}"
        )

    check_logs = [
        PipelineCheckLog(
            check_type="MODEL_PERFORMANCE",
            check_name="accuracy",
            status="PASS" if accuracy >= min_accuracy else "FAIL",
            metric_value=accuracy,
            threshold_value=min_accuracy,
            message=(
                f"accuracy={accuracy:.4f}, "
                f"required>={min_accuracy:.4f}, "
                f"run_id={run_id}"
            ),
        ),
        PipelineCheckLog(
            check_type="MODEL_PERFORMANCE",
            check_name="f1_weighted",
            status="PASS" if f1_weighted >= min_f1_weighted else "FAIL",
            metric_value=f1_weighted,
            threshold_value=min_f1_weighted,
            message=(
                f"f1_weighted={f1_weighted:.4f}, "
                f"required>={min_f1_weighted:.4f}, "
                f"run_id={run_id}"
            ),
        ),
    ]

    engine = create_engine(database_url)
    with engine.begin() as conn:
        save_check_results(conn, check_logs)

    if failed_checks:
        print("\n[Failed Model Checks]")
        for check in failed_checks:
            print(f"- {check}")

        raise SystemExit(1)

    print("\nModel performance checks passed.")


if __name__ == "__main__":
    main()
