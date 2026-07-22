from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.common.db import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BEST_MODEL_PATH = Path(os.getenv("BEST_MODEL_PATH", "models/best/job_classifier.pkl"))

ARCHIVE_TABLE_NAME = "model_promotion_archives"
ROLLBACK_TABLE_NAME = "model_rollback_actions"


def resolve_project_path(path_value: str | Path | None) -> Path | None:
    if not path_value:
        return None

    path = Path(path_value)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def pass_check(message: str) -> None:
    print(f"[PASS] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    sys.exit(1)


def table_exists(table_name: str) -> bool:
    engine = get_engine()

    with engine.begin() as conn:
        return bool(
            conn.execute(
                text("SELECT to_regclass(:table_name) IS NOT NULL"),
                {"table_name": f"public.{table_name}"},
            ).scalar()
        )


def fetch_all(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    engine = get_engine()

    with engine.begin() as conn:
        rows = conn.execute(text(query), params or {}).mappings().all()

    return [dict(row) for row in rows]


def check_required_tables() -> None:
    required_tables = [
        "model_registry",
        ARCHIVE_TABLE_NAME,
        ROLLBACK_TABLE_NAME,
    ]

    for table_name in required_tables:
        if not table_exists(table_name):
            fail(f"Required table not found: {table_name}")

        pass_check(f"Required table exists: {table_name}")


def check_promoted_model() -> dict[str, Any]:
    promoted_rows = fetch_all(
        """
        SELECT *
        FROM model_registry
        WHERE status = 'PROMOTED'
        ORDER BY id DESC
        """
    )

    promoted_count = len(promoted_rows)

    if promoted_count == 0:
        fail("No PROMOTED model found in model_registry.")

    if promoted_count > 1:
        promoted_ids = [str(row.get("id")) for row in promoted_rows]
        fail(
            "More than one PROMOTED model found in model_registry: "
            + ", ".join(promoted_ids)
        )

    promoted_model = promoted_rows[0]
    pass_check(f"Exactly one PROMOTED model found: id={promoted_model.get('id')}")

    promoted_model_path = promoted_model.get("promoted_model_path")

    if not promoted_model_path:
        fail(
            f"PROMOTED model id={promoted_model.get('id')} has empty promoted_model_path."
        )

    resolved_promoted_model_path = resolve_project_path(promoted_model_path)

    if resolved_promoted_model_path is None:
        fail("Could not resolve promoted_model_path.")

    if not resolved_promoted_model_path.exists():
        fail(f"promoted_model_path file not found: {resolved_promoted_model_path}")

    pass_check(f"promoted_model_path exists: {resolved_promoted_model_path}")

    best_model_path = resolve_project_path(BEST_MODEL_PATH)

    if best_model_path is None:
        fail("Could not resolve BEST_MODEL_PATH.")

    if not best_model_path.exists():
        fail(f"BEST_MODEL_PATH file not found: {best_model_path}")

    pass_check(f"BEST_MODEL_PATH exists: {best_model_path}")

    if best_model_path.resolve() != resolved_promoted_model_path.resolve():
        warn(
            "BEST_MODEL_PATH and promoted_model_path are different. "
            f"BEST_MODEL_PATH={best_model_path}, "
            f"promoted_model_path={resolved_promoted_model_path}"
        )
    else:
        pass_check("BEST_MODEL_PATH matches promoted_model_path")

    return promoted_model


def check_model_archive_integrity() -> None:
    archive_rows = fetch_all(
        """
        SELECT
            id,
            model_registry_id,
            model_name,
            archived_model_path,
            source_model_path,
            created_at
        FROM model_promotion_archives
        ORDER BY id DESC
        """
    )

    if not archive_rows:
        warn("No promoted model archive rows found.")
        return

    registry_ids = {
        row["id"]
        for row in fetch_all(
            """
            SELECT id
            FROM model_registry
            """
        )
    }

    for archive in archive_rows:
        archive_id = archive.get("id")
        model_registry_id = archive.get("model_registry_id")
        archived_model_path = archive.get("archived_model_path")

        if not model_registry_id:
            fail(f"Archive id={archive_id} has empty model_registry_id.")

        if model_registry_id not in registry_ids:
            fail(
                f"Archive id={archive_id} references missing model_registry_id="
                f"{model_registry_id}."
            )

        if not archived_model_path:
            fail(f"Archive id={archive_id} has empty archived_model_path.")

        resolved_archive_path = resolve_project_path(archived_model_path)

        if resolved_archive_path is None:
            fail(f"Archive id={archive_id} archived_model_path could not be resolved.")

        if not resolved_archive_path.exists():
            fail(
                f"Archive id={archive_id} archived model file not found: "
                f"{resolved_archive_path}"
            )

        pass_check(
            f"Archive id={archive_id} is valid: "
            f"registry_id={model_registry_id}, path={resolved_archive_path}"
        )

    pass_check(f"Model archive integrity completed: {len(archive_rows)} rows")


def check_model_rollback_integrity() -> None:
    rollback_rows = fetch_all(
        """
        SELECT
            id,
            archive_id,
            target_model_registry_id,
            previous_model_registry_id,
            archived_model_path,
            restored_model_path,
            backup_model_path,
            status,
            created_at
        FROM model_rollback_actions
        ORDER BY id DESC
        """
    )

    if not rollback_rows:
        warn("No model rollback action rows found.")
        return

    archive_ids = {
        row["id"]
        for row in fetch_all(
            """
            SELECT id
            FROM model_promotion_archives
            """
        )
    }

    registry_ids = {
        row["id"]
        for row in fetch_all(
            """
            SELECT id
            FROM model_registry
            """
        )
    }

    for rollback in rollback_rows:
        rollback_id = rollback.get("id")
        archive_id = rollback.get("archive_id")
        target_model_registry_id = rollback.get("target_model_registry_id")
        previous_model_registry_id = rollback.get("previous_model_registry_id")
        status = str(rollback.get("status") or "").upper()

        if archive_id not in archive_ids:
            fail(
                f"Rollback action id={rollback_id} references missing archive_id="
                f"{archive_id}."
            )

        if target_model_registry_id not in registry_ids:
            fail(
                f"Rollback action id={rollback_id} references missing "
                f"target_model_registry_id={target_model_registry_id}."
            )

        if previous_model_registry_id and previous_model_registry_id not in registry_ids:
            fail(
                f"Rollback action id={rollback_id} references missing "
                f"previous_model_registry_id={previous_model_registry_id}."
            )

        archived_model_path = resolve_project_path(rollback.get("archived_model_path"))
        restored_model_path = resolve_project_path(rollback.get("restored_model_path"))
        backup_model_path = resolve_project_path(rollback.get("backup_model_path"))

        if archived_model_path is None or not archived_model_path.exists():
            fail(
                f"Rollback action id={rollback_id} archived model file not found: "
                f"{archived_model_path}"
            )

        if restored_model_path is None or not restored_model_path.exists():
            fail(
                f"Rollback action id={rollback_id} restored model file not found: "
                f"{restored_model_path}"
            )

        if status == "SUCCESS":
            if backup_model_path is None or not backup_model_path.exists():
                fail(
                    f"Rollback action id={rollback_id} backup model file not found: "
                    f"{backup_model_path}"
                )

        pass_check(
            f"Rollback action id={rollback_id} is valid: "
            f"archive_id={archive_id}, target_registry_id={target_model_registry_id}"
        )

    pass_check(f"Model rollback integrity completed: {len(rollback_rows)} rows")


def main() -> None:
    print("")
    print("JobSkill Model Lifecycle Integrity Check")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Best model  : {resolve_project_path(BEST_MODEL_PATH)}")

    check_required_tables()
    check_promoted_model()
    check_model_archive_integrity()
    check_model_rollback_integrity()

    print("")
    pass_check("Model lifecycle integrity check completed")


if __name__ == "__main__":
    main()
