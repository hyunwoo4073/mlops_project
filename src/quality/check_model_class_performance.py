from __future__ import annotations

import os
import re
import sys
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient
from sqlalchemy import text

from src.common.db import get_engine


CHECK_TYPE = "MODEL_CLASS_PERFORMANCE"

MIN_CLASS_F1 = float(os.getenv("MIN_CLASS_F1", "0.70"))
MIN_CLASS_RECALL = float(os.getenv("MIN_CLASS_RECALL", "0.60"))
MIN_CLASS_SUPPORT = float(os.getenv("MIN_CLASS_SUPPORT", "1"))

MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "postgresql+psycopg2://jobskill:jobskill@localhost:5432/mlflow",
)
MLFLOW_EXPERIMENT_NAME = os.getenv(
    "MLFLOW_EXPERIMENT_NAME",
    "jobskill-classifier",
)


def normalize_label(metric_name: str, prefix: str) -> str:
    return metric_name.replace(prefix, "", 1)


def pretty_label(label_key: str) -> str:
    return label_key.replace("_", " ")


def fetch_latest_mlflow_run() -> Any:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()

    experiment = mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME)

    if experiment is None:
        raise RuntimeError(f"MLflow experiment not found: {MLFLOW_EXPERIMENT_NAME}")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["attributes.start_time DESC"],
        max_results=1,
    )

    if not runs:
        raise RuntimeError(f"No MLflow runs found in experiment: {MLFLOW_EXPERIMENT_NAME}")

    return runs[0]


def log_check_result(
    check_name: str,
    status: str,
    metric_value: float | None,
    threshold_value: float | None,
    message: str,
) -> None:
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO pipeline_check_results (
                    check_type,
                    check_name,
                    status,
                    metric_value,
                    threshold_value,
                    message,
                    dag_id,
                    task_id,
                    run_id
                )
                VALUES (
                    :check_type,
                    :check_name,
                    :status,
                    :metric_value,
                    :threshold_value,
                    :message,
                    :dag_id,
                    :task_id,
                    :run_id
                )
                """
            ),
            {
                "check_type": CHECK_TYPE,
                "check_name": check_name,
                "status": status,
                "metric_value": metric_value,
                "threshold_value": threshold_value,
                "message": message,
                "dag_id": os.getenv("AIRFLOW_CTX_DAG_ID"),
                "task_id": os.getenv("AIRFLOW_CTX_TASK_ID"),
                "run_id": os.getenv("AIRFLOW_CTX_DAG_RUN_ID"),
            },
        )


def pass_check(
    check_name: str,
    metric_value: float | None,
    threshold_value: float | None,
    message: str,
) -> None:
    print(f"[PASS] {message}")
    log_check_result(
        check_name=check_name,
        status="PASS",
        metric_value=metric_value,
        threshold_value=threshold_value,
        message=message,
    )


def fail_check(
    check_name: str,
    metric_value: float | None,
    threshold_value: float | None,
    message: str,
    failures: list[str],
) -> None:
    print(f"[FAIL] {message}")
    failures.append(message)

    log_check_result(
        check_name=check_name,
        status="FAIL",
        metric_value=metric_value,
        threshold_value=threshold_value,
        message=message,
    )


def collect_class_metrics(metrics: dict[str, float]) -> dict[str, dict[str, float]]:
    class_metrics: dict[str, dict[str, float]] = {}

    metric_patterns = {
        "precision": "eval_precision_",
        "recall": "eval_recall_",
        "f1": "eval_f1_",
        "support": "eval_support_",
    }

    for metric_name, metric_value in metrics.items():
        for metric_key, prefix in metric_patterns.items():
            if metric_name.startswith(prefix):
                label_key = normalize_label(metric_name, prefix)

                class_metrics.setdefault(label_key, {})
                class_metrics[label_key][metric_key] = float(metric_value)

    return class_metrics


def validate_metric_name_safety(class_metrics: dict[str, dict[str, float]]) -> None:
    safe_pattern = re.compile(r"^[A-Za-z0-9_]+$")

    for label_key in class_metrics:
        if not safe_pattern.match(label_key):
            raise RuntimeError(f"Unsafe class metric label found: {label_key}")


def main() -> None:
    print("")
    print("JobSkill Class-level Model Performance Check")
    print(f"MLflow tracking URI : {MLFLOW_TRACKING_URI}")
    print(f"MLflow experiment   : {MLFLOW_EXPERIMENT_NAME}")
    print(f"MIN_CLASS_F1        : {MIN_CLASS_F1}")
    print(f"MIN_CLASS_RECALL    : {MIN_CLASS_RECALL}")
    print(f"MIN_CLASS_SUPPORT   : {MIN_CLASS_SUPPORT}")

    run = fetch_latest_mlflow_run()
    run_id = run.info.run_id
    metrics = dict(run.data.metrics)

    print(f"latest_run_id       : {run_id}")
    print(f"run_status          : {run.info.status}")
    print("")

    class_metrics = collect_class_metrics(metrics)
    validate_metric_name_safety(class_metrics)

    if not class_metrics:
        message = (
            "No class-level evaluation metrics found in latest MLflow run. "
            "Expected metrics such as eval_f1_Data_Engineer and eval_recall_Data_Engineer. "
            "Run train_baseline.py after adding model evaluation artifact logging."
        )

        fail_check(
            check_name="class_metrics_exist",
            metric_value=0,
            threshold_value=1,
            message=message,
            failures=[],
        )

        raise RuntimeError(message)

    failures: list[str] = []

    pass_check(
        check_name="class_metrics_exist",
        metric_value=float(len(class_metrics)),
        threshold_value=1,
        message=f"Class-level metrics found for {len(class_metrics)} labels.",
    )

    for label_key, values in sorted(class_metrics.items()):
        label = pretty_label(label_key)

        support = float(values.get("support", 0.0))
        precision = float(values.get("precision", 0.0))
        recall = float(values.get("recall", 0.0))
        f1 = float(values.get("f1", 0.0))

        print(
            f"{label}: "
            f"precision={precision:.4f}, "
            f"recall={recall:.4f}, "
            f"f1={f1:.4f}, "
            f"support={support:.0f}"
        )

        if support < MIN_CLASS_SUPPORT:
            message = (
                f"{label} support is below minimum. "
                f"support={support:.0f}, threshold={MIN_CLASS_SUPPORT:.0f}"
            )
            fail_check(
                check_name=f"{label_key}.support",
                metric_value=support,
                threshold_value=MIN_CLASS_SUPPORT,
                message=message,
                failures=failures,
            )
        else:
            pass_check(
                check_name=f"{label_key}.support",
                metric_value=support,
                threshold_value=MIN_CLASS_SUPPORT,
                message=(
                    f"{label} support passed. "
                    f"support={support:.0f}, threshold={MIN_CLASS_SUPPORT:.0f}"
                ),
            )

        if recall < MIN_CLASS_RECALL:
            message = (
                f"{label} recall is below threshold. "
                f"recall={recall:.4f}, threshold={MIN_CLASS_RECALL:.4f}"
            )
            fail_check(
                check_name=f"{label_key}.recall",
                metric_value=recall,
                threshold_value=MIN_CLASS_RECALL,
                message=message,
                failures=failures,
            )
        else:
            pass_check(
                check_name=f"{label_key}.recall",
                metric_value=recall,
                threshold_value=MIN_CLASS_RECALL,
                message=(
                    f"{label} recall passed. "
                    f"recall={recall:.4f}, threshold={MIN_CLASS_RECALL:.4f}"
                ),
            )

        if f1 < MIN_CLASS_F1:
            message = (
                f"{label} f1 is below threshold. "
                f"f1={f1:.4f}, threshold={MIN_CLASS_F1:.4f}"
            )
            fail_check(
                check_name=f"{label_key}.f1",
                metric_value=f1,
                threshold_value=MIN_CLASS_F1,
                message=message,
                failures=failures,
            )
        else:
            pass_check(
                check_name=f"{label_key}.f1",
                metric_value=f1,
                threshold_value=MIN_CLASS_F1,
                message=(
                    f"{label} f1 passed. "
                    f"f1={f1:.4f}, threshold={MIN_CLASS_F1:.4f}"
                ),
            )

    if failures:
        print("")
        print("Class-level model performance failures:")
        for failure in failures:
            print(f"- {failure}")

        raise RuntimeError(
            f"Class-level model performance check failed: {len(failures)} failures"
        )

    print("")
    print("[PASS] Class-level model performance check completed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)
