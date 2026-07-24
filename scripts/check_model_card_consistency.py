from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient
from sqlalchemy import text

from src.common.db import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_CARD_PATH = PROJECT_ROOT / "reports" / "latest_model_card.md"

CHECK_TYPE = "MODEL_CARD_CONSISTENCY"

MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "postgresql+psycopg2://jobskill:jobskill@localhost:5432/mlflow",
)


def get_value(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]

    return default


def fetch_current_promoted_model() -> dict[str, Any]:
    engine = get_engine()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT *
                FROM model_registry
                WHERE status = 'PROMOTED'
                ORDER BY id DESC
                LIMIT 1
                """
            )
        ).mappings().first()

    if row is None:
        raise RuntimeError("No PROMOTED model found in model_registry.")

    return dict(row)


def fetch_mlflow_run_params(run_id: str | None) -> dict[str, str]:
    if not run_id:
        return {}

    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
        run = client.get_run(run_id)

        return dict(run.data.params)

    except Exception as exc:
        print(f"[WARN] Failed to fetch MLflow run params: {exc}")
        return {}


def read_model_card() -> str:
    if not MODEL_CARD_PATH.exists():
        raise RuntimeError(f"Model Card file not found: {MODEL_CARD_PATH}")

    return MODEL_CARD_PATH.read_text(encoding="utf-8")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def log_check_result(
    check_name: str,
    status: str,
    message: str,
    metric_value: float | None = None,
    threshold_value: float | None = None,
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


def pass_check(check_name: str, message: str) -> None:
    print(f"[PASS] {message}")
    log_check_result(
        check_name=check_name,
        status="PASS",
        message=message,
    )


def fail_check(check_name: str, message: str, failures: list[str]) -> None:
    print(f"[FAIL] {message}")
    failures.append(message)

    log_check_result(
        check_name=check_name,
        status="FAIL",
        message=message,
    )


def assert_contains(
    content: str,
    expected_value: Any,
    check_name: str,
    description: str,
    failures: list[str],
) -> None:
    expected_text = normalize_text(expected_value)

    if not expected_text:
        fail_check(
            check_name=check_name,
            message=f"{description} is empty.",
            failures=failures,
        )
        return

    if expected_text not in content:
        fail_check(
            check_name=check_name,
            message=f"Model Card does not contain {description}: {expected_text}",
            failures=failures,
        )
        return

    pass_check(
        check_name=check_name,
        message=f"Model Card contains {description}: {expected_text}",
    )


def assert_section_exists(
    content: str,
    section_title: str,
    check_name: str,
    failures: list[str],
) -> None:
    if section_title not in content:
        fail_check(
            check_name=check_name,
            message=f"Model Card section not found: {section_title}",
            failures=failures,
        )
        return

    pass_check(
        check_name=check_name,
        message=f"Model Card section exists: {section_title}",
    )


def main() -> None:
    print("")
    print("JobSkill Model Card Consistency Check")
    print(f"model_card_path : {MODEL_CARD_PATH}")
    print(f"mlflow_uri      : {MLFLOW_TRACKING_URI}")
    print("")

    promoted_model = fetch_current_promoted_model()
    content = read_model_card()

    model_registry_id = get_value(promoted_model, "id")
    model_name = get_value(promoted_model, "model_name", default="job_classifier")
    run_id = get_value(promoted_model, "run_id", "model_run_id")
    accuracy = get_value(promoted_model, "accuracy")
    f1_weighted = get_value(promoted_model, "f1_weighted")

    mlflow_params = fetch_mlflow_run_params(run_id)
    training_dataset_hash = mlflow_params.get("training_dataset_hash")
    training_dataset_row_count = mlflow_params.get("training_dataset_row_count")

    print(f"model_registry_id        : {model_registry_id}")
    print(f"model_name               : {model_name}")
    print(f"run_id                   : {run_id}")
    print(f"accuracy                 : {accuracy}")
    print(f"f1_weighted              : {f1_weighted}")
    print(f"training_dataset_hash    : {training_dataset_hash}")
    print(f"training_dataset_row_cnt : {training_dataset_row_count}")
    print("")

    failures: list[str] = []

    assert_contains(
        content=content,
        expected_value=model_registry_id,
        check_name="model_registry_id",
        description="current promoted model_registry_id",
        failures=failures,
    )

    assert_contains(
        content=content,
        expected_value=model_name,
        check_name="model_name",
        description="current promoted model_name",
        failures=failures,
    )

    assert_contains(
        content=content,
        expected_value=run_id,
        check_name="run_id",
        description="current promoted MLflow run_id",
        failures=failures,
    )

    if accuracy is not None:
        assert_contains(
            content=content,
            expected_value=round(float(accuracy), 4),
            check_name="accuracy",
            description="current promoted accuracy",
            failures=failures,
        )

    if f1_weighted is not None:
        assert_contains(
            content=content,
            expected_value=round(float(f1_weighted), 4),
            check_name="f1_weighted",
            description="current promoted f1_weighted",
            failures=failures,
        )

    if training_dataset_hash:
        assert_contains(
            content=content,
            expected_value=training_dataset_hash,
            check_name="training_dataset_hash",
            description="training dataset hash",
            failures=failures,
        )

    if training_dataset_row_count:
        assert_contains(
            content=content,
            expected_value=training_dataset_row_count,
            check_name="training_dataset_row_count",
            description="training dataset row count",
            failures=failures,
        )

    required_sections = {
        "document_title": "# JobSkill Promoted Model Card",
        "model_summary": "## 1. Model Summary",
        "performance": "## 2. Performance",
        "evaluation_details": "### Evaluation Details",
        "training_dataset": "## 3. Training Dataset",
        "mlflow_metadata": "## 4. MLflow Run Metadata",
        "model_lifecycle": "## 5. Model Lifecycle",
        "operational_notes": "## 6. Operational Notes",
    }

    for check_name, section_title in required_sections.items():
        assert_section_exists(
            content=content,
            section_title=section_title,
            check_name=check_name,
            failures=failures,
        )

    if failures:
        print("")
        print("Model Card consistency failures:")
        for failure in failures:
            print(f"- {failure}")

        raise RuntimeError(
            f"Model Card consistency check failed: {len(failures)} failures"
        )

    print("")
    print("[PASS] Model Card consistency check completed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)
