from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.common.db import get_engine
from src.training.training_data_selector import (
    build_training_query,
    load_training_data_selection_config,
    resolve_training_event_time_source,
    select_training_data,
)

REPORT_PATH = Path(
    os.getenv(
        "TRAINING_EVENT_TIME_REPORT_PATH",
        "reports/latest_training_event_time_report.md",
    )
)


def getenv_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown_table(headers: list[str], rows: list[dict[str, object]]) -> str:
    if not rows:
        return "_No rows._"

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        values = [format_value(row.get(header)) for header in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_mode_rows(df: pd.DataFrame) -> list[dict[str, object]]:
    config = load_training_data_selection_config()
    rows: list[dict[str, object]] = []

    for mode in ["full", "lookback", "recent", "recent_plus_history_sample"]:
        result = select_training_data(df, replace(config, mode=mode))
        rows.append(
            {
                "mode": mode,
                "applied_mode": result.applied_mode,
                "before_rows": result.before_rows,
                "after_rows": result.after_rows,
                "recent_rows": result.recent_rows,
                "historical_rows": result.historical_rows,
                "warning": result.warning or "",
            }
        )
    return rows


def write_report(
    *,
    event_source,
    total_rows: int,
    usable_event_time_rows: int,
    null_event_time_rows: int,
    min_event_time: object,
    max_event_time: object,
    distinct_event_dates: int,
    mode_rows: list[dict[str, object]],
    status: str,
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# JobSkill Training Event Time Report",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Status: `{status}`",
        "",
        "## Event Time Source",
        "",
        f"- source_columns: `{event_source.source_columns}`",
        f"- cleaned_temporal_columns: `{event_source.cleaned_temporal_columns}`",
        f"- raw_temporal_columns: `{event_source.raw_temporal_columns}`",
        f"- expression: `{event_source.expression}`",
        "",
        "## Event Time Coverage",
        "",
        f"- total_rows: `{total_rows}`",
        f"- usable_event_time_rows: `{usable_event_time_rows}`",
        f"- null_event_time_rows: `{null_event_time_rows}`",
        f"- min_event_time: `{min_event_time}`",
        f"- max_event_time: `{max_event_time}`",
        f"- distinct_event_dates: `{distinct_event_dates}`",
        "",
        "## Selection Mode Preview",
        "",
        markdown_table(
            [
                "mode",
                "applied_mode",
                "before_rows",
                "after_rows",
                "recent_rows",
                "historical_rows",
                "warning",
            ],
            mode_rows,
        ),
        "",
        "## Interpretation",
        "",
        "- `usable_event_time_rows`가 0이면 recent/window/sampling mode는 full로 fallback됩니다.",
        "- `source_columns`가 비어 있으면 cleaned/raw 테이블에서 사용할 수 있는 timestamp/date 컬럼을 찾지 못한 상태입니다.",
        "- `recent`와 `recent_plus_history_sample`이 의미 있게 달라지려면 `training_event_at`이 실제 날짜 값을 가져야 합니다.",
        "",
        "## Follow-up Commands",
        "",
        "```bash",
        "make training-event-time-check",
        "make training-data-selection-experiment",
        "cat reports/latest_training_data_selection_experiment_report.md",
        "```",
        "",
    ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    strict = getenv_bool("TRAINING_EVENT_TIME_STRICT", False)
    engine = get_engine()
    event_source = resolve_training_event_time_source(engine)

    df = pd.read_sql(build_training_query(engine), engine)
    if "training_event_at" not in df.columns:
        raise ValueError("training_event_at column was not produced by build_training_query().")

    event_time = pd.to_datetime(df["training_event_at"], errors="coerce")
    total_rows = len(df)
    usable_event_time_rows = int(event_time.notna().sum())
    null_event_time_rows = int(event_time.isna().sum())

    if usable_event_time_rows > 0:
        min_event_time = str(event_time.min())
        max_event_time = str(event_time.max())
        distinct_event_dates = int(event_time.dt.date.nunique())
        status = "PASS"
    else:
        min_event_time = ""
        max_event_time = ""
        distinct_event_dates = 0
        status = "WARN"

    mode_rows = build_mode_rows(df)
    write_report(
        event_source=event_source,
        total_rows=total_rows,
        usable_event_time_rows=usable_event_time_rows,
        null_event_time_rows=null_event_time_rows,
        min_event_time=min_event_time,
        max_event_time=max_event_time,
        distinct_event_dates=distinct_event_dates,
        mode_rows=mode_rows,
        status=status,
    )

    print("Training event time check completed")
    print(f"status={status}")
    print(f"source_columns={event_source.source_columns}")
    print(f"usable_event_time_rows={usable_event_time_rows}")
    print(f"report_path={REPORT_PATH}")

    if strict and status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

