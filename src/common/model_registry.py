from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, text


@dataclass
class ModelMetadata:
    model_name: str
    run_id: str | None
    model_registry_id: int | None
    model_path: Path
    status: str


def get_database_url() -> str:
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "jobskill")
    db_user = os.getenv("DB_USER", "jobskill")
    db_password = os.getenv("DB_PASSWORD", "jobskill")

    return (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )


def get_current_model_metadata() -> ModelMetadata:
    model_name = os.getenv("MODEL_NAME", "job_classifier")

    fallback_model_path = Path(
        os.getenv("MODEL_PATH", "models/job_classifier.pkl")
    )

    default_best_model_path = Path(
        os.getenv("BEST_MODEL_PATH", "models/best/job_classifier.pkl")
    )

    engine = create_engine(get_database_url())

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    id,
                    model_name,
                    run_id,
                    promoted_model_path,
                    status
                FROM model_registry
                WHERE model_name = :model_name
                  AND status = 'PROMOTED'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"model_name": model_name},
        ).mappings().first()

    if row is not None:
        promoted_path = Path(row["promoted_model_path"])

        if promoted_path.exists():
            return ModelMetadata(
                model_name=row["model_name"],
                run_id=row["run_id"],
                model_registry_id=row["id"],
                model_path=promoted_path,
                status=row["status"],
            )

    if default_best_model_path.exists():
        return ModelMetadata(
            model_name=model_name,
            run_id=None,
            model_registry_id=None,
            model_path=default_best_model_path,
            status="BEST_FILE_ONLY",
        )

    if fallback_model_path.exists():
        return ModelMetadata(
            model_name=model_name,
            run_id=None,
            model_registry_id=None,
            model_path=fallback_model_path,
            status="FALLBACK_CANDIDATE",
        )

    raise FileNotFoundError(
        f"No model file found. Checked: {default_best_model_path}, {fallback_model_path}"
    )
