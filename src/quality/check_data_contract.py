from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.common.db import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = Path(
    os.getenv("DATA_CONTRACT_PATH", "config/data_contract.json")
)

CHECK_TYPE = "DATA_CONTRACT"

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def resolve_project_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def quote_identifier(identifier: str) -> str:
    if not IDENTIFIER_PATTERN.match(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")

    return f'"{identifier}"'


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    sys.exit(1)


def pass_check(message: str) -> None:
    print(f"[PASS] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def load_contract() -> dict[str, Any]:
    contract_path = resolve_project_path(CONTRACT_PATH)

    if not contract_path.exists():
        fail(f"Data contract file not found: {contract_path}")

    with contract_path.open("r", encoding="utf-8") as file:
        contract = json.load(file)

    if "tables" not in contract or not contract["tables"]:
        fail(f"No tables defined in data contract: {contract_path}")

    return contract


def table_exists(table_name: str) -> bool:
    engine = get_engine()

    with engine.begin() as conn:
        return bool(
            conn.execute(
                text("SELECT to_regclass(:table_name) IS NOT NULL"),
                {"table_name": f"public.{table_name}"},
            ).scalar()
        )


def fetch_columns(table_name: str) -> dict[str, dict[str, Any]]:
    engine = get_engine()

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                """
            ),
            {"table_name": table_name},
        ).mappings().all()

    return {
        row["column_name"]: {
            "data_type": row["data_type"],
            "is_nullable": row["is_nullable"],
        }
        for row in rows
    }


def fetch_scalar(query: str, params: dict[str, Any] | None = None) -> Any:
    engine = get_engine()

    with engine.begin() as conn:
        return conn.execute(text(query), params or {}).scalar()


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


def record_pass(
    check_name: str,
    metric_value: float | None,
    threshold_value: float | None,
    message: str,
) -> None:
    pass_check(message)
    log_check_result(
        check_name=check_name,
        status="PASS",
        metric_value=metric_value,
        threshold_value=threshold_value,
        message=message,
    )


def record_fail(
    check_name: str,
    metric_value: float | None,
    threshold_value: float | None,
    message: str,
) -> None:
    print(f"[FAIL] {message}")
    log_check_result(
        check_name=check_name,
        status="FAIL",
        metric_value=metric_value,
        threshold_value=threshold_value,
        message=message,
    )


def get_table_row_count(table_name: str) -> int:
    table_identifier = quote_identifier(table_name)

    return int(
        fetch_scalar(
            f"""
            SELECT COUNT(*)
            FROM {table_identifier}
            """
        )
        or 0
    )


def check_table_exists(table_name: str, failures: list[str]) -> bool:
    check_name = f"{table_name}.table_exists"

    if not table_exists(table_name):
        message = f"Required table not found: {table_name}"
        record_fail(
            check_name=check_name,
            metric_value=0,
            threshold_value=1,
            message=message,
        )
        failures.append(message)
        return False

    record_pass(
        check_name=check_name,
        metric_value=1,
        threshold_value=1,
        message=f"Required table exists: {table_name}",
    )

    return True


def check_min_rows(
    table_name: str,
    table_contract: dict[str, Any],
    failures: list[str],
) -> None:
    min_rows = int(table_contract.get("min_rows", 0))

    if min_rows <= 0:
        return

    row_count = get_table_row_count(table_name)
    check_name = f"{table_name}.min_rows"

    if row_count < min_rows:
        message = (
            f"{table_name} row count is below minimum. "
            f"row_count={row_count}, min_rows={min_rows}"
        )
        record_fail(
            check_name=check_name,
            metric_value=float(row_count),
            threshold_value=float(min_rows),
            message=message,
        )
        failures.append(message)
        return

    record_pass(
        check_name=check_name,
        metric_value=float(row_count),
        threshold_value=float(min_rows),
        message=(
            f"{table_name} row count passed. "
            f"row_count={row_count}, min_rows={min_rows}"
        ),
    )


def check_required_columns(
    table_name: str,
    table_contract: dict[str, Any],
    columns: dict[str, dict[str, Any]],
    failures: list[str],
) -> None:
    required_columns = table_contract.get("required_columns", [])

    for column_contract in required_columns:
        column_name = column_contract["name"]
        expected_types = column_contract.get("types", [])
        check_name = f"{table_name}.{column_name}.required_column"

        if column_name not in columns:
            message = f"{table_name}.{column_name} required column is missing."
            record_fail(
                check_name=check_name,
                metric_value=0,
                threshold_value=1,
                message=message,
            )
            failures.append(message)
            continue

        actual_type = columns[column_name]["data_type"]

        if expected_types and actual_type not in expected_types:
            message = (
                f"{table_name}.{column_name} type mismatch. "
                f"actual={actual_type}, expected={expected_types}"
            )
            record_fail(
                check_name=check_name,
                metric_value=0,
                threshold_value=1,
                message=message,
            )
            failures.append(message)
            continue

        record_pass(
            check_name=check_name,
            metric_value=1,
            threshold_value=1,
            message=(
                f"{table_name}.{column_name} column exists. "
                f"data_type={actual_type}"
            ),
        )


def calculate_ratio(
    table_name: str,
    condition_sql: str,
) -> float:
    table_identifier = quote_identifier(table_name)

    result = fetch_scalar(
        f"""
        SELECT
            COALESCE(
                COUNT(*) FILTER (WHERE {condition_sql})::double precision
                / NULLIF(COUNT(*), 0),
                0
            ) AS ratio
        FROM {table_identifier}
        """
    )

    return float(result or 0)


def check_null_ratios(
    table_name: str,
    table_contract: dict[str, Any],
    columns: dict[str, dict[str, Any]],
    failures: list[str],
) -> None:
    for null_check in table_contract.get("null_checks", []):
        column_name = null_check["column"]
        max_null_ratio = float(null_check["max_null_ratio"])
        check_name = f"{table_name}.{column_name}.null_ratio"

        if column_name not in columns:
            message = f"{table_name}.{column_name} null check skipped because column is missing."
            record_fail(
                check_name=check_name,
                metric_value=None,
                threshold_value=max_null_ratio,
                message=message,
            )
            failures.append(message)
            continue

        column_identifier = quote_identifier(column_name)
        null_ratio = calculate_ratio(
            table_name=table_name,
            condition_sql=f"{column_identifier} IS NULL",
        )

        if null_ratio > max_null_ratio:
            message = (
                f"{table_name}.{column_name} null ratio exceeded. "
                f"actual={null_ratio:.4f}, threshold={max_null_ratio:.4f}"
            )
            record_fail(
                check_name=check_name,
                metric_value=null_ratio,
                threshold_value=max_null_ratio,
                message=message,
            )
            failures.append(message)
            continue

        record_pass(
            check_name=check_name,
            metric_value=null_ratio,
            threshold_value=max_null_ratio,
            message=(
                f"{table_name}.{column_name} null ratio passed. "
                f"actual={null_ratio:.4f}, threshold={max_null_ratio:.4f}"
            ),
        )


def check_empty_ratios(
    table_name: str,
    table_contract: dict[str, Any],
    columns: dict[str, dict[str, Any]],
    failures: list[str],
) -> None:
    for empty_check in table_contract.get("non_empty_checks", []):
        column_name = empty_check["column"]
        max_empty_ratio = float(empty_check["max_empty_ratio"])
        check_name = f"{table_name}.{column_name}.empty_ratio"

        if column_name not in columns:
            message = f"{table_name}.{column_name} empty check skipped because column is missing."
            record_fail(
                check_name=check_name,
                metric_value=None,
                threshold_value=max_empty_ratio,
                message=message,
            )
            failures.append(message)
            continue

        column_identifier = quote_identifier(column_name)
        empty_ratio = calculate_ratio(
            table_name=table_name,
            condition_sql=(
                f"{column_identifier} IS NULL "
                f"OR BTRIM({column_identifier}::text) = ''"
            ),
        )

        if empty_ratio > max_empty_ratio:
            message = (
                f"{table_name}.{column_name} empty ratio exceeded. "
                f"actual={empty_ratio:.4f}, threshold={max_empty_ratio:.4f}"
            )
            record_fail(
                check_name=check_name,
                metric_value=empty_ratio,
                threshold_value=max_empty_ratio,
                message=message,
            )
            failures.append(message)
            continue

        record_pass(
            check_name=check_name,
            metric_value=empty_ratio,
            threshold_value=max_empty_ratio,
            message=(
                f"{table_name}.{column_name} empty ratio passed. "
                f"actual={empty_ratio:.4f}, threshold={max_empty_ratio:.4f}"
            ),
        )


def check_allowed_value_ratios(
    table_name: str,
    table_contract: dict[str, Any],
    columns: dict[str, dict[str, Any]],
    failures: list[str],
) -> None:
    for value_check in table_contract.get("allowed_value_checks", []):
        column_name = value_check["column"]
        allowed_values = value_check["allowed_values"]
        max_invalid_ratio = float(value_check["max_invalid_ratio"])
        check_name = f"{table_name}.{column_name}.allowed_values"

        if column_name not in columns:
            message = f"{table_name}.{column_name} allowed value check skipped because column is missing."
            record_fail(
                check_name=check_name,
                metric_value=None,
                threshold_value=max_invalid_ratio,
                message=message,
            )
            failures.append(message)
            continue

        column_identifier = quote_identifier(column_name)

        invalid_count = int(
            fetch_scalar(
                f"""
                SELECT COUNT(*)
                FROM {quote_identifier(table_name)}
                WHERE {column_identifier} IS NULL
                   OR {column_identifier}::text NOT IN :allowed_values
                """,
                {"allowed_values": tuple(allowed_values)},
            )
            or 0
        )

        row_count = get_table_row_count(table_name)
        invalid_ratio = invalid_count / row_count if row_count > 0 else 0.0

        if invalid_ratio > max_invalid_ratio:
            message = (
                f"{table_name}.{column_name} invalid value ratio exceeded. "
                f"invalid_count={invalid_count}, row_count={row_count}, "
                f"actual={invalid_ratio:.4f}, threshold={max_invalid_ratio:.4f}"
            )
            record_fail(
                check_name=check_name,
                metric_value=invalid_ratio,
                threshold_value=max_invalid_ratio,
                message=message,
            )
            failures.append(message)
            continue

        record_pass(
            check_name=check_name,
            metric_value=invalid_ratio,
            threshold_value=max_invalid_ratio,
            message=(
                f"{table_name}.{column_name} allowed value check passed. "
                f"invalid_count={invalid_count}, row_count={row_count}, "
                f"actual={invalid_ratio:.4f}, threshold={max_invalid_ratio:.4f}"
            ),
        )


def validate_table(
    table_name: str,
    table_contract: dict[str, Any],
    failures: list[str],
) -> None:
    print("")
    print(f"Validating table: {table_name}")

    if not check_table_exists(table_name, failures):
        return

    columns = fetch_columns(table_name)

    check_required_columns(
        table_name=table_name,
        table_contract=table_contract,
        columns=columns,
        failures=failures,
    )

    check_min_rows(
        table_name=table_name,
        table_contract=table_contract,
        failures=failures,
    )

    check_null_ratios(
        table_name=table_name,
        table_contract=table_contract,
        columns=columns,
        failures=failures,
    )

    check_empty_ratios(
        table_name=table_name,
        table_contract=table_contract,
        columns=columns,
        failures=failures,
    )

    check_allowed_value_ratios(
        table_name=table_name,
        table_contract=table_contract,
        columns=columns,
        failures=failures,
    )


def main() -> None:
    print("")
    print("JobSkill Data Contract Check")
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Contract    : {resolve_project_path(CONTRACT_PATH)}")

    contract = load_contract()
    failures: list[str] = []

    for table_name, table_contract in contract["tables"].items():
        validate_table(
            table_name=table_name,
            table_contract=table_contract,
            failures=failures,
        )

    if failures:
        print("")
        print("Data contract failures:")
        for failure in failures:
            print(f"- {failure}")

        fail(f"Data contract check failed: {len(failures)} failures")

    print("")
    pass_check("Data contract check completed")


if __name__ == "__main__":
    main()
