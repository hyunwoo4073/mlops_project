from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.common.db import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BEST_MODEL_PATH = Path(os.getenv("BEST_MODEL_PATH", "models/best/job_classifier.pkl"))
ARCHIVE_DIR = Path(os.getenv("MODEL_ARCHIVE_DIR", "models/promoted_archive"))

CREATED_BY = os.getenv("MODEL_ARCHIVE_CREATED_BY", "local-user")
ARCHIVE_REASON = os.getenv(
    "MODEL_ARCHIVE_REASON",
    "Manual promoted model archive before rollback feature.",
)


def resolve_project_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def ensure_archive_table() -> None:
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS model_promotion_archives (
                    id BIGSERIAL PRIMARY KEY,
                    model_registry_id BIGINT,
                    model_name VARCHAR(200),
                    model_version VARCHAR(100),
                    model_run_id VARCHAR(200),
                    source_model_path TEXT,
                    archived_model_path TEXT NOT NULL,
                    accuracy DOUBLE PRECISION,
                    f1_weighted DOUBLE PRECISION,
                    archive_reason TEXT,
                    created_by VARCHAR(100) DEFAULT 'system',
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_model_promotion_archives_registry_id
                ON model_promotion_archives(model_registry_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_model_promotion_archives_model_name
                ON model_promotion_archives(model_name)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_model_promotion_archives_created_at
                ON model_promotion_archives(created_at)
            """)
        )


def fetch_latest_promoted_model() -> dict[str, Any]:
    engine = get_engine()

    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT *
                FROM model_registry
                WHERE status = 'PROMOTED'
                ORDER BY id DESC
                LIMIT 1
            """)
        ).mappings().first()

    if row is None:
        raise RuntimeError("No PROMOTED model found in model_registry.")

    return dict(row)


def build_archive_path(model_registry_row: dict[str, Any]) -> Path:
    model_name = model_registry_row.get("model_name") or "job_classifier"
    registry_id = model_registry_row.get("id") or "unknown"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{model_name}_registry_{registry_id}_{timestamp}.pkl"

    return resolve_project_path(ARCHIVE_DIR) / filename


def archive_model_file(source_path: Path, archive_path: Path) -> None:
    if not source_path.exists():
        raise FileNotFoundError(f"Best model file not found: {source_path}")

    archive_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(source_path, archive_path)


def save_archive_record(
    model_registry_row: dict[str, Any],
    source_path: Path,
    archive_path: Path,
) -> None:
    engine = get_engine()

    metadata = {
        "model_registry": {
            key: str(value)
            for key, value in model_registry_row.items()
        }
    }

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO model_promotion_archives (
                    model_registry_id,
                    model_name,
                    model_version,
                    model_run_id,
                    source_model_path,
                    archived_model_path,
                    accuracy,
                    f1_weighted,
                    archive_reason,
                    created_by,
                    metadata
                )
                VALUES (
                    :model_registry_id,
                    :model_name,
                    :model_version,
                    :model_run_id,
                    :source_model_path,
                    :archived_model_path,
                    :accuracy,
                    :f1_weighted,
                    :archive_reason,
                    :created_by,
                    CAST(:metadata AS JSONB)
                )
            """),
            {
                "model_registry_id": model_registry_row.get("id"),
                "model_name": model_registry_row.get("model_name"),
                "model_version": model_registry_row.get("model_version"),
                "model_run_id": (
                    model_registry_row.get("model_run_id")
                    or model_registry_row.get("run_id")
                    or model_registry_row.get("mlflow_run_id")
                ),
                "source_model_path": str(source_path.relative_to(PROJECT_ROOT))
                if source_path.is_relative_to(PROJECT_ROOT)
                else str(source_path),
                "archived_model_path": str(archive_path.relative_to(PROJECT_ROOT))
                if archive_path.is_relative_to(PROJECT_ROOT)
                else str(archive_path),
                "accuracy": model_registry_row.get("accuracy"),
                "f1_weighted": model_registry_row.get("f1_weighted"),
                "archive_reason": ARCHIVE_REASON,
                "created_by": CREATED_BY,
                "metadata": json.dumps(metadata, ensure_ascii=False),
            },
        )


def main() -> None:
    ensure_archive_table()

    source_path = resolve_project_path(BEST_MODEL_PATH)
    model_registry_row = fetch_latest_promoted_model()
    archive_path = build_archive_path(model_registry_row)

    archive_model_file(source_path=source_path, archive_path=archive_path)
    save_archive_record(
        model_registry_row=model_registry_row,
        source_path=source_path,
        archive_path=archive_path,
    )

    print("[OK] Promoted model archived")
    print(f"model_registry_id : {model_registry_row.get('id')}")
    print(f"model_name        : {model_registry_row.get('model_name')}")
    print(f"source_model_path : {source_path}")
    print(f"archived_path     : {archive_path}")


if __name__ == "__main__":
    main()
