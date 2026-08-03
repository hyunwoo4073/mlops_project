from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection


CURRENT_STATE_TABLE = "alert_current_states"
EVENT_TABLE = "alert_events"

SYNTHETIC_SERVICES = ("smoke-test", "incident-drill")
SYNTHETIC_ALERT_NAMES = ("SmokeTestAlert", "SyntheticIncidentAlert")
SYNTHETIC_FINGERPRINTS = ("smoke-test-fingerprint",)

DERIVED_ALERT_NAMES = (
    "JobSkillUnacknowledgedCurrentAlert",
    "JobSkillHighAverageMTTA",
    "JobSkillHighAverageMTTR",
)


def get_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    db_user = os.getenv("DB_USER", "jobskill")
    db_password = os.getenv("DB_PASSWORD", "jobskill")
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "jobskill")

    return (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )


def quote_values(values: Iterable[str]) -> str:
    return ", ".join("'" + value.replace("'", "''") + "'" for value in values)


def table_exists(conn: Connection, table_name: str) -> bool:
    query = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = :table_name
        )
        """
    )
    return bool(conn.execute(query, {"table_name": table_name}).scalar())


def get_columns(conn: Connection, table_name: str) -> set[str]:
    query = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
        """
    )
    return {
        row[0]
        for row in conn.execute(query, {"table_name": table_name}).fetchall()
    }


def pick_alert_name_column(columns: set[str]) -> str | None:
    if "alert_name" in columns:
        return "alert_name"
    if "alertname" in columns:
        return "alertname"
    return None


def build_synthetic_predicate(
    table_name: str,
    columns: set[str],
    include_derived: bool,
) -> str:
    predicates: list[str] = []

    if "fingerprint" in columns:
        predicates.append(
            f"fingerprint IN ({quote_values(SYNTHETIC_FINGERPRINTS)})"
        )

    if "service" in columns:
        predicates.append(
            f"COALESCE(service, '') IN ({quote_values(SYNTHETIC_SERVICES)})"
        )

    alert_name_column = pick_alert_name_column(columns)
    if alert_name_column:
        predicates.append(
            f"COALESCE({alert_name_column}, '') IN "
            f"({quote_values(SYNTHETIC_ALERT_NAMES)})"
        )
        predicates.append(f"COALESCE({alert_name_column}, '') ILIKE '%smoke%'")
        predicates.append(f"COALESCE({alert_name_column}, '') ILIKE '%drill%'")

        if include_derived and table_name == CURRENT_STATE_TABLE:
            predicates.append(
                f"COALESCE({alert_name_column}, '') IN "
                f"({quote_values(DERIVED_ALERT_NAMES)})"
            )

    if not predicates:
        return "FALSE"

    return "\n       OR ".join(f"({predicate})" for predicate in predicates)


def build_select_columns(columns: set[str]) -> str:
    preferred_columns = (
        "id",
        "alert_name",
        "alertname",
        "service",
        "severity",
        "status",
        "starts_at",
        "ends_at",
        "last_received_at",
        "updated_at",
        "fingerprint",
    )
    selected = [column for column in preferred_columns if column in columns]
    if not selected:
        return "*"
    return ", ".join(selected)


def count_rows(conn: Connection, table_name: str, predicate: str) -> int:
    query = text(f"SELECT COUNT(*) FROM {table_name} WHERE {predicate}")
    return int(conn.execute(query).scalar() or 0)


def fetch_sample_rows(
    conn: Connection,
    table_name: str,
    columns: set[str],
    predicate: str,
) -> list[dict[str, object]]:
    select_columns = build_select_columns(columns)
    order_column = "starts_at" if "starts_at" in columns else "id"
    query = text(
        f"""
        SELECT {select_columns}
        FROM {table_name}
        WHERE {predicate}
        ORDER BY {order_column} ASC NULLS LAST
        LIMIT 20
        """
    )
    return [dict(row._mapping) for row in conn.execute(query).fetchall()]


def delete_rows(conn: Connection, table_name: str, predicate: str) -> int:
    query = text(f"DELETE FROM {table_name} WHERE {predicate}")
    result = conn.execute(query)
    return int(result.rowcount or 0)


def print_rows(table_name: str, rows: list[dict[str, object]]) -> None:
    if not rows:
        return

    print(f"\n[{table_name}] matched row sample")
    for row in rows:
        printable = ", ".join(f"{key}={value}" for key, value in row.items())
        print(f"- {printable}")


def process_table(
    conn: Connection,
    table_name: str,
    mode: str,
    include_derived: bool,
) -> int:
    if not table_exists(conn, table_name):
        print(f"[SKIP] {table_name}: table does not exist")
        return 0

    columns = get_columns(conn, table_name)
    table_include_derived = include_derived and table_name == CURRENT_STATE_TABLE
    predicate = build_synthetic_predicate(
        table_name=table_name,
        columns=columns,
        include_derived=table_include_derived,
    )

    matched_count = count_rows(conn, table_name, predicate)
    print(f"[INFO] {table_name}: matched_rows={matched_count}")

    sample_rows = fetch_sample_rows(conn, table_name, columns, predicate)
    print_rows(table_name, sample_rows)

    if mode == "apply" and matched_count > 0:
        deleted_count = delete_rows(conn, table_name, predicate)
        print(f"[DELETE] {table_name}: deleted_rows={deleted_count}")

    return matched_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan, apply, or check cleanup for synthetic alert data that can "
            "pollute alert current state, MTTA, and MTTR metrics."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("plan", "apply", "check"),
        default="plan",
        help="plan prints matching rows, apply deletes them, check exits nonzero if synthetic rows remain.",
    )
    parser.add_argument(
        "--include-derived",
        action="store_true",
        help=(
            "Also clean derived current-state escalation alerts such as "
            "JobSkillUnacknowledgedCurrentAlert, JobSkillHighAverageMTTA, "
            "and JobSkillHighAverageMTTR."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    engine = create_engine(
        get_database_url(),
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
    )

    print("Synthetic Alert Hygiene")
    print("=======================")
    print(f"mode={args.mode}")
    print(f"include_derived={args.include_derived}")

    target_tables = (CURRENT_STATE_TABLE, EVENT_TABLE)
    total_matched = 0

    with engine.begin() as conn:
        for table_name in target_tables:
            total_matched += process_table(
                conn=conn,
                table_name=table_name,
                mode=args.mode,
                include_derived=args.include_derived,
            )

    if args.mode == "check" and total_matched > 0:
        print(f"[FAIL] synthetic alert rows remain: {total_matched}")
        return 1

    if args.mode == "check":
        print("[PASS] synthetic alert rows were not found")

    return 0


if __name__ == "__main__":
    sys.exit(main())

