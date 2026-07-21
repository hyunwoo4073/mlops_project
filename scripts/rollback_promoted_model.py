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
ROLLBACK_BACKUP_DIR = Path(os.getenv("MODEL_ROLLBACK_BACKUP_DIR", "models/rollback_backup"))

ROLLBACK_ARCHIVE_ID = os.getenv("MODEL_ROLLBACK_ARCHIVE_ID")
ROLLBACK_DRY_RUN = os.getenv("MODEL_ROLLBACK_DRY_RUN", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
    "on",
}

CREATED_BY = os.getenv("MODEL_ROLLBACK_CREATED_BY", "local-user")
ROLLBACK_REASON = os.getenv(
    "MODEL_ROLLBACK_REASON",
    "Manual rollback to archived promoted model.",
)


def resolve_project_path(path: str | Path | None) -> Path:
    if path is None:
        raise ValueError("Path is None.")

    resolved_path = Path(path)

    if resolved_path.is_absolute():
        return resolved_path

    return PROJECT_ROOT / resolved_path


def to_project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def ensure_rollback_table() -> None:
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS model_rollback_actions (
                    id BIGSERIAL PRIMARY KEY,
                    archive_id BIGINT,
                    target_model_registry_id BIGINT,
                    previous_model_registry_id BIGINT,
                    archived_model_path TEXT,
                    restored_model_path TEXT,
                    backup_model_path TEXT,
                    rollback_reason TEXT,
                    created_by VARCHAR(100) DEFAULT 'system',
                    status VARCHAR(50) DEFAULT 'SUCCESS',
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_model_rollback_actions_archive_id
                ON model_rollback_actions(archive_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_model_rollback_actions_target_model_registry_id
                ON model_rollback_actions(target_model_registry_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_model_rollback_actions_previous_model_registry_id
                ON model_rollback_actions(previous_model_registry_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_model_rollback_actions_created_at
                ON model_rollback_actions(created_at)
            """)
        )


def fetch_latest_promoted_model() -> dict[str, Any] | None:
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

    return dict(row) if row else None


def fetch_target_archive() -> dict[str, Any]:
    engine = get_engine()

    if ROLLBACK_ARCHIVE_ID:
        query = text("""
            SELECT
                a.*,
                mr.status AS target_registry_status
            FROM model_promotion_archives a
            LEFT JOIN model_registry mr
                ON mr.id = a.model_registry_id
            WHERE a.id = :archive_id
            LIMIT 1
        """)
        params = {"archive_id": int(ROLLBACK_ARCHIVE_ID)}
    else:
        query = text("""
            SELECT
                a.*,
                mr.status AS target_registry_status
            FROM model_promotion_archives a
            LEFT JOIN model_registry mr
                ON mr.id = a.model_registry_id
            ORDER BY a.id DESC
            LIMIT 1
        """)
        params = {}

    with engine.begin() as conn:
        row = conn.execute(query, params).mappings().first()

    if row is None:
        if ROLLBACK_ARCHIVE_ID:
            raise RuntimeError(
                f"No model archive found for MODEL_ROLLBACK_ARCHIVE_ID={ROLLBACK_ARCHIVE_ID}"
            )

        raise RuntimeError("No model archive found in model_promotion_archives.")

    return dict(row)


def build_backup_path(previous_promoted_model: dict[str, Any] | None) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    previous_registry_id = (
        previous_promoted_model.get("id")
        if previous_promoted_model
        else "unknown"
    )

    filename = f"job_classifier_before_rollback_registry_{previous_registry_id}_{timestamp}.pkl"

    return resolve_project_path(ROLLBACK_BACKUP_DIR) / filename


def validate_rollback_target(target_archive: dict[str, Any]) -> Path:
    archived_model_path = target_archive.get("archived_model_path")

    if not archived_model_path:
        raise RuntimeError(
            f"Archive id={target_archive.get('id')} has empty archived_model_path."
        )

    resolved_archive_path = resolve_project_path(archived_model_path)

    if not resolved_archive_path.exists():
        raise FileNotFoundError(
            f"Archived model file not found: {resolved_archive_path}"
        )

    target_model_registry_id = target_archive.get("model_registry_id")

    if not target_model_registry_id:
        raise RuntimeError(
            f"Archive id={target_archive.get('id')} has empty model_registry_id."
        )

    return resolved_archive_path


def copy_model_for_rollback(
    archived_model_path: Path,
    best_model_path: Path,
    backup_model_path: Path,
) -> None:
    if not best_model_path.exists():
        raise FileNotFoundError(f"Current best model file not found: {best_model_path}")

    backup_model_path.parent.mkdir(parents=True, exist_ok=True)
    best_model_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(best_model_path, backup_model_path)
    shutil.copy2(archived_model_path, best_model_path)


def update_model_registry_for_rollback(
    target_model_registry_id: int,
) -> None:
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE model_registry
                SET status = 'ROLLED_BACK'
                WHERE status = 'PROMOTED'
                  AND id <> :target_model_registry_id
            """),
            {"target_model_registry_id": target_model_registry_id},
        )

        conn.execute(
            text("""
                UPDATE model_registry
                SET
                    status = 'PROMOTED',
                    promoted_model_path = :promoted_model_path
                WHERE id = :target_model_registry_id
            """),
            {
                "target_model_registry_id": target_model_registry_id,
                "promoted_model_path": to_project_relative(
                    resolve_project_path(BEST_MODEL_PATH)
                ),
            },
        )


def save_rollback_action(
    target_archive: dict[str, Any],
    previous_promoted_model: dict[str, Any] | None,
    archived_model_path: Path,
    best_model_path: Path,
    backup_model_path: Path,
    status: str,
) -> None:
    engine = get_engine()

    metadata = {
        "target_archive": {
            key: str(value)
            for key, value in target_archive.items()
        },
        "previous_promoted_model": {
            key: str(value)
            for key, value in previous_promoted_model.items()
        } if previous_promoted_model else {},
        "dry_run": ROLLBACK_DRY_RUN,
    }

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO model_rollback_actions (
                    archive_id,
                    target_model_registry_id,
                    previous_model_registry_id,
                    archived_model_path,
                    restored_model_path,
                    backup_model_path,
                    rollback_reason,
                    created_by,
                    status,
                    metadata
                )
                VALUES (
                    :archive_id,
                    :target_model_registry_id,
                    :previous_model_registry_id,
                    :archived_model_path,
                    :restored_model_path,
                    :backup_model_path,
                    :rollback_reason,
                    :created_by,
                    :status,
                    CAST(:metadata AS JSONB)
                )
            """),
            {
                "archive_id": target_archive.get("id"),
                "target_model_registry_id": target_archive.get("model_registry_id"),
                "previous_model_registry_id": (
                    previous_promoted_model.get("id")
                    if previous_promoted_model
                    else None
                ),
                "archived_model_path": to_project_relative(archived_model_path),
                "restored_model_path": to_project_relative(best_model_path),
                "backup_model_path": to_project_relative(backup_model_path),
                "rollback_reason": ROLLBACK_REASON,
                "created_by": CREATED_BY,
                "status": status,
                "metadata": json.dumps(metadata, ensure_ascii=False),
            },
        )


def print_plan(
    target_archive: dict[str, Any],
    previous_promoted_model: dict[str, Any] | None,
    archived_model_path: Path,
    best_model_path: Path,
    backup_model_path: Path,
) -> None:
    print("")
    print("Model Rollback Plan")
    print("===================")
    print(f"dry_run                  : {ROLLBACK_DRY_RUN}")
    print(f"archive_id               : {target_archive.get('id')}")
    print(f"target_model_registry_id : {target_archive.get('model_registry_id')}")
    print(f"target_model_name        : {target_archive.get('model_name')}")
    print(f"target_accuracy          : {target_archive.get('accuracy')}")
    print(f"target_f1_weighted       : {target_archive.get('f1_weighted')}")
    print(f"target_registry_status   : {target_archive.get('target_registry_status')}")
    print(f"archived_model_path      : {archived_model_path}")

    if previous_promoted_model:
        print(f"current_promoted_id      : {previous_promoted_model.get('id')}")
        print(f"current_model_name       : {previous_promoted_model.get('model_name')}")
        print(f"current_accuracy         : {previous_promoted_model.get('accuracy')}")
        print(f"current_f1_weighted      : {previous_promoted_model.get('f1_weighted')}")
    else:
        print("current_promoted_id      : None")

    print(f"best_model_path          : {best_model_path}")
    print(f"backup_model_path        : {backup_model_path}")
    print(f"created_by               : {CREATED_BY}")
    print(f"reason                   : {ROLLBACK_REASON}")


def main() -> None:
    ensure_rollback_table()

    target_archive = fetch_target_archive()
    previous_promoted_model = fetch_latest_promoted_model()

    archived_model_path = validate_rollback_target(target_archive)
    best_model_path = resolve_project_path(BEST_MODEL_PATH)
    backup_model_path = build_backup_path(previous_promoted_model)

    print_plan(
        target_archive=target_archive,
        previous_promoted_model=previous_promoted_model,
        archived_model_path=archived_model_path,
        best_model_path=best_model_path,
        backup_model_path=backup_model_path,
    )

    if ROLLBACK_DRY_RUN:
        print("")
        print("[DRY-RUN] Rollback was not applied.")
        print("[DRY-RUN] Set MODEL_ROLLBACK_DRY_RUN=false and MODEL_ROLLBACK_ARCHIVE_ID=<id> to apply.")
        return

    if not ROLLBACK_ARCHIVE_ID:
        raise RuntimeError(
            "MODEL_ROLLBACK_ARCHIVE_ID is required when MODEL_ROLLBACK_DRY_RUN=false."
        )

    copy_model_for_rollback(
        archived_model_path=archived_model_path,
        best_model_path=best_model_path,
        backup_model_path=backup_model_path,
    )

    update_model_registry_for_rollback(
        target_model_registry_id=int(target_archive["model_registry_id"])
    )

    save_rollback_action(
        target_archive=target_archive,
        previous_promoted_model=previous_promoted_model,
        archived_model_path=archived_model_path,
        best_model_path=best_model_path,
        backup_model_path=backup_model_path,
        status="SUCCESS",
    )

    print("")
    print("[OK] Promoted model rollback completed")
    print(f"restored_model_path : {best_model_path}")
    print(f"backup_model_path   : {backup_model_path}")


if __name__ == "__main__":
    main()
