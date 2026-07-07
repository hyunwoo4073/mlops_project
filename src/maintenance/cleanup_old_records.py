from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import text


sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    return int(value)


def count_old_api_logs(conn, retention_days: int) -> int:
    return int(
        conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM api_prediction_logs
                WHERE created_at < NOW() - make_interval(days => :retention_days)
                """
            ),
            {"retention_days": retention_days},
        ).scalar()
        or 0
    )


def count_old_api_predictions(conn, retention_days: int) -> int:
    return int(
        conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM model_predictions
                WHERE prediction_source = 'API'
                  AND predicted_at < NOW() - make_interval(days => :retention_days)
                """
            ),
            {"retention_days": retention_days},
        ).scalar()
        or 0
    )


def count_old_pipeline_checks(conn, retention_days: int) -> int:
    return int(
        conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM pipeline_check_results
                WHERE checked_at < NOW() - make_interval(days => :retention_days)
                """
            ),
            {"retention_days": retention_days},
        ).scalar()
        or 0
    )


def delete_old_api_logs(conn, retention_days: int) -> int:
    result = conn.execute(
        text(
            """
            DELETE FROM api_prediction_logs
            WHERE created_at < NOW() - make_interval(days => :retention_days)
            """
        ),
        {"retention_days": retention_days},
    )

    return int(result.rowcount or 0)


def delete_old_api_predictions(conn, retention_days: int) -> int:
    result = conn.execute(
        text(
            """
            DELETE FROM model_predictions
            WHERE prediction_source = 'API'
              AND predicted_at < NOW() - make_interval(days => :retention_days)
            """
        ),
        {"retention_days": retention_days},
    )

    return int(result.rowcount or 0)


def delete_old_pipeline_checks(conn, retention_days: int) -> int:
    result = conn.execute(
        text(
            """
            DELETE FROM pipeline_check_results
            WHERE checked_at < NOW() - make_interval(days => :retention_days)
            """
        ),
        {"retention_days": retention_days},
    )

    return int(result.rowcount or 0)


def main() -> None:
    dry_run = _env_bool("CLEANUP_DRY_RUN", default=True)

    api_log_retention_days = _env_int("API_LOG_RETENTION_DAYS", 30)
    api_prediction_retention_days = _env_int("API_PREDICTION_RETENTION_DAYS", 30)
    pipeline_check_retention_days = _env_int("PIPELINE_CHECK_RETENTION_DAYS", 90)

    engine = get_engine()

    print()
    print("[Cleanup Old Records]")
    print(f"CLEANUP_DRY_RUN                 : {dry_run}")
    print(f"API_LOG_RETENTION_DAYS          : {api_log_retention_days}")
    print(f"API_PREDICTION_RETENTION_DAYS   : {api_prediction_retention_days}")
    print(f"PIPELINE_CHECK_RETENTION_DAYS   : {pipeline_check_retention_days}")
    print()

    with engine.begin() as conn:
        old_api_log_count = count_old_api_logs(conn, api_log_retention_days)
        old_api_prediction_count = count_old_api_predictions(
            conn,
            api_prediction_retention_days,
        )
        old_pipeline_check_count = count_old_pipeline_checks(
            conn,
            pipeline_check_retention_days,
        )

        print("[Cleanup Target Counts]")
        print(f"old_api_logs          : {old_api_log_count}")
        print(f"old_api_predictions   : {old_api_prediction_count}")
        print(f"old_pipeline_checks   : {old_pipeline_check_count}")
        print()

        if dry_run:
            print("[DRY RUN] No records were deleted.")
            return

        # api_prediction_logs가 model_predictions를 참조하므로,
        # API logs를 먼저 삭제한 뒤 오래된 API prediction row를 삭제한다.
        deleted_api_logs = delete_old_api_logs(conn, api_log_retention_days)
        deleted_api_predictions = delete_old_api_predictions(
            conn,
            api_prediction_retention_days,
        )
        deleted_pipeline_checks = delete_old_pipeline_checks(
            conn,
            pipeline_check_retention_days,
        )

    print("[Cleanup Deleted Counts]")
    print(f"deleted_api_logs          : {deleted_api_logs}")
    print(f"deleted_api_predictions   : {deleted_api_predictions}")
    print(f"deleted_pipeline_checks   : {deleted_pipeline_checks}")
    print()
    print("cleanup_old_records completed.")


if __name__ == "__main__":
    main()
