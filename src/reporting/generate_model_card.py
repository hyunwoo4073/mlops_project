from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient
from sqlalchemy import text

from src.common.db import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports"
MODEL_CARD_DIR = REPORT_DIR / "model_cards"
LATEST_MODEL_CARD_PATH = REPORT_DIR / "latest_model_card.md"


def get_value(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]

    return default


def fetch_latest_promoted_model() -> dict[str, Any]:
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


def fetch_latest_archive(model_registry_id: int | None) -> dict[str, Any] | None:
    if model_registry_id is None:
        return None

    engine = get_engine()

    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT to_regclass('public.model_promotion_archives') IS NOT NULL")
        ).scalar()

        if not exists:
            return None

        row = conn.execute(
            text(
                """
                SELECT *
                FROM model_promotion_archives
                WHERE model_registry_id = :model_registry_id
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"model_registry_id": model_registry_id},
        ).mappings().first()

    return dict(row) if row else None


def fetch_latest_rollback_action(model_registry_id: int | None) -> dict[str, Any] | None:
    if model_registry_id is None:
        return None

    engine = get_engine()

    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT to_regclass('public.model_rollback_actions') IS NOT NULL")
        ).scalar()

        if not exists:
            return None

        row = conn.execute(
            text(
                """
                SELECT *
                FROM model_rollback_actions
                WHERE target_model_registry_id = :model_registry_id
                   OR previous_model_registry_id = :model_registry_id
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"model_registry_id": model_registry_id},
        ).mappings().first()

    return dict(row) if row else None


def setup_mlflow_client() -> MlflowClient:
    tracking_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        "postgresql+psycopg2://jobskill:jobskill@localhost:5432/mlflow",
    )

    mlflow.set_tracking_uri(tracking_uri)

    return MlflowClient(tracking_uri=tracking_uri)


def fetch_mlflow_run(run_id: str | None) -> dict[str, Any]:
    if not run_id:
        return {
            "params": {},
            "metrics": {},
            "tags": {},
            "artifact_uri": None,
            "status": "UNKNOWN",
            "error": "run_id is empty",
        }

    try:
        client = setup_mlflow_client()
        run = client.get_run(run_id)

        return {
            "params": dict(run.data.params),
            "metrics": dict(run.data.metrics),
            "tags": dict(run.data.tags),
            "artifact_uri": run.info.artifact_uri,
            "status": run.info.status,
            "error": None,
        }
    except Exception as exc:
        return {
            "params": {},
            "metrics": {},
            "tags": {},
            "artifact_uri": None,
            "status": "UNKNOWN",
            "error": str(exc),
        }


def load_training_dataset_profile(run_id: str | None) -> dict[str, Any] | None:
    if not run_id:
        return None

    try:
        client = setup_mlflow_client()

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = client.download_artifacts(
                run_id=run_id,
                path="training_dataset_profile.json",
                dst_path=temp_dir,
            )

            profile_path = Path(local_path)

            if not profile_path.exists():
                return None

            with profile_path.open("r", encoding="utf-8") as file:
                return json.load(file)

    except Exception:
        return None


def load_mlflow_json_artifact(run_id: str | None, artifact_path: str) -> dict[str, Any] | None:
    if not run_id:
        return None

    try:
        client = setup_mlflow_client()

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = client.download_artifacts(
                run_id=run_id,
                path=artifact_path,
                dst_path=temp_dir,
            )

            artifact_file = Path(local_path)

            if not artifact_file.exists():
                return None

            with artifact_file.open("r", encoding="utf-8") as file:
                return json.load(file)

    except Exception:
        return None


def format_value(value: Any) -> str:
    if value is None:
        return "N/A"

    if isinstance(value, float):
        return f"{value:.4f}"

    return str(value)


def format_json_block(value: Any) -> str:
    if value is None:
        return "```json\n{}\n```"

    return (
        "```json\n"
        + json.dumps(value, ensure_ascii=False, indent=2, default=str)
        + "\n```"
    )


def build_model_card(
    promoted_model: dict[str, Any],
    archive: dict[str, Any] | None,
    rollback_action: dict[str, Any] | None,
    mlflow_run: dict[str, Any],
    dataset_profile: dict[str, Any] | None,
    classification_report_artifact: dict[str, Any] | None,
    evaluation_distribution: dict[str, Any] | None,
) -> str:
    model_registry_id = get_value(promoted_model, "id")
    model_name = get_value(promoted_model, "model_name", default="job_classifier")
    run_id = get_value(promoted_model, "run_id", "model_run_id")
    model_path = get_value(
        promoted_model,
        "promoted_model_path",
        "model_path",
        default="models/best/job_classifier.pkl",
    )
    accuracy = get_value(promoted_model, "accuracy")
    f1_weighted = get_value(promoted_model, "f1_weighted")
    created_at = get_value(promoted_model, "created_at")

    params = mlflow_run.get("params", {})
    metrics = mlflow_run.get("metrics", {})
    tags = mlflow_run.get("tags", {})

    training_dataset_hash = params.get("training_dataset_hash")
    training_dataset_row_count = params.get("training_dataset_row_count")
    training_dataset_source = params.get("training_dataset_source")
    training_dataset_name = params.get("training_dataset_name")

    archive_path = get_value(archive or {}, "archived_model_path")
    rollback_status = get_value(rollback_action or {}, "status")
    rollback_created_at = get_value(rollback_action or {}, "created_at")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# JobSkill Promoted Model Card",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "## 1. Model Summary",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Model registry ID | `{format_value(model_registry_id)}` |",
        f"| Model name | `{format_value(model_name)}` |",
        f"| Status | `PROMOTED` |",
        f"| MLflow run ID | `{format_value(run_id)}` |",
        f"| Model path | `{format_value(model_path)}` |",
        f"| Registry created at | `{format_value(created_at)}` |",
        "",
        "## 2. Performance",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| accuracy | {format_value(accuracy or metrics.get('accuracy'))} |",
        f"| f1_weighted | {format_value(f1_weighted or metrics.get('f1_weighted'))} |",
        "",
        "### Evaluation Details",
        "",
        "#### Classification Report",
        "",
        format_json_block(classification_report_artifact),
        "",
        "#### Evaluation Distribution",
        "",
        format_json_block(evaluation_distribution),
        "",
        "Artifacts:",
        "",
        "- `evaluation/classification_report.json`",
        "- `evaluation/classification_report.csv`",
        "- `evaluation/classification_report.txt`",
        "- `evaluation/confusion_matrix.csv`",
        "- `evaluation/evaluation_distribution.json`",
        "",
        "## 3. Training Dataset",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Dataset name | `{format_value(training_dataset_name)}` |",
        f"| Dataset source | `{format_value(training_dataset_source)}` |",
        f"| Dataset row count | `{format_value(training_dataset_row_count)}` |",
        f"| Dataset hash | `{format_value(training_dataset_hash)}` |",
        f"| MLflow dataset logging | `{format_value(tags.get('training_dataset_logged_with'))}` |",
        "",
        "### Training Dataset Profile",
        "",
        format_json_block(dataset_profile),
        "",
        "## 4. MLflow Run Metadata",
        "",
        "### Params",
        "",
        format_json_block(params),
        "",
        "### Metrics",
        "",
        format_json_block(metrics),
        "",
        "## 5. Model Lifecycle",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Latest archive path | `{format_value(archive_path)}` |",
        f"| Latest rollback status | `{format_value(rollback_status)}` |",
        f"| Latest rollback created at | `{format_value(rollback_created_at)}` |",
        f"| MLflow artifact URI | `{format_value(mlflow_run.get('artifact_uri'))}` |",
        f"| MLflow run status | `{format_value(mlflow_run.get('status'))}` |",
        "",
        "## 6. Operational Notes",
        "",
        "- This model is the current `PROMOTED` model in `model_registry`.",
        "- FastAPI serving uses the promoted model artifact path.",
        "- Training dataset metadata is tracked in MLflow with dataset hash and profile artifact.",
        "- Model archive and rollback history are checked separately through model lifecycle operations.",
        "- If prediction quality, drift, or API readiness checks fail, review the pipeline checks and alert runbooks before keeping this model in production.",
        "",
    ]

    if mlflow_run.get("error"):
        lines.extend(
            [
                "## 7. Warnings",
                "",
                f"- MLflow run metadata could not be fully loaded: `{mlflow_run['error']}`",
                "",
            ]
        )

    return "\n".join(lines)


def write_model_card(
    model_registry_id: int | None,
    content: str,
) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_CARD_DIR.mkdir(parents=True, exist_ok=True)

    if model_registry_id is None:
        model_card_path = MODEL_CARD_DIR / "model_card_unknown.md"
    else:
        model_card_path = MODEL_CARD_DIR / f"model_card_registry_{model_registry_id}.md"

    model_card_path.write_text(content, encoding="utf-8")
    LATEST_MODEL_CARD_PATH.write_text(content, encoding="utf-8")

    return model_card_path, LATEST_MODEL_CARD_PATH


def main() -> None:
    promoted_model = fetch_latest_promoted_model()

    model_registry_id = get_value(promoted_model, "id")
    run_id = get_value(promoted_model, "run_id", "model_run_id")

    archive = fetch_latest_archive(model_registry_id)
    rollback_action = fetch_latest_rollback_action(model_registry_id)
    mlflow_run = fetch_mlflow_run(run_id)
    dataset_profile = load_training_dataset_profile(run_id)
    classification_report_artifact = load_mlflow_json_artifact(
        run_id,
        "evaluation/classification_report.json",
    )
    evaluation_distribution = load_mlflow_json_artifact(
        run_id,
        "evaluation/evaluation_distribution.json",
    )

    content = build_model_card(
        promoted_model=promoted_model,
        archive=archive,
        rollback_action=rollback_action,
        mlflow_run=mlflow_run,
        dataset_profile=dataset_profile,
        classification_report_artifact=classification_report_artifact,
        evaluation_distribution=evaluation_distribution,
    )

    model_card_path, latest_path = write_model_card(
        model_registry_id=model_registry_id,
        content=content,
    )

    print("")
    print("JobSkill Promoted Model Card")
    print(f"model_registry_id : {model_registry_id}")
    print(f"run_id            : {run_id}")
    print(f"model_card_path   : {model_card_path}")
    print(f"latest_path       : {latest_path}")
    print("")
    print("[PASS] Model card generated")


if __name__ == "__main__":
    main()
