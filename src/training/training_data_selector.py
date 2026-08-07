from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


SUPPORTED_TRAINING_DATA_MODES = {
    "full",
    "lookback",
    "recent",
    "recent_plus_history_sample",
}

TEMPORAL_DATA_TYPES = {
    "date",
    "timestamp without time zone",
    "timestamp with time zone",
}

DEFAULT_CLEANED_TIME_COLUMNS = [
    "training_event_at",
    "posted_at",
    "published_at",
    "created_at",
    "updated_at",
    "ingested_at",
    "loaded_at",
    "processed_at",
]

DEFAULT_RAW_TIME_COLUMNS = [
    "posted_at",
    "published_at",
    "collected_at",
    "crawled_at",
    "scraped_at",
    "created_at",
    "updated_at",
    "ingested_at",
    "loaded_at",
]


@dataclass(frozen=True)
class TrainingDataSelectionConfig:
    mode: str
    date_column: str
    lookback_days: int
    recent_days: int
    history_sample_rows_per_class: int
    random_state: int
    min_rows_after_selection: int


@dataclass(frozen=True)
class TrainingDataSelectionResult:
    df: pd.DataFrame
    requested_mode: str
    applied_mode: str
    date_column: str
    before_rows: int
    after_rows: int
    recent_rows: int
    historical_rows: int
    warning: str | None
    details: dict[str, Any]


@dataclass(frozen=True)
class TrainingEventTimeSource:
    expression: str
    source_columns: list[str]
    cleaned_temporal_columns: list[str]
    raw_temporal_columns: list[str]


def getenv_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value == "":
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer. value={raw_value}") from exc


def parse_column_candidates(name: str, defaults: list[str]) -> list[str]:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value.strip() == "":
        return defaults

    return [value.strip() for value in raw_value.split(",") if value.strip()]


def load_training_data_selection_config() -> TrainingDataSelectionConfig:
    mode = os.getenv("TRAINING_DATA_MODE", "full").strip().lower()

    if mode not in SUPPORTED_TRAINING_DATA_MODES:
        raise ValueError(
            "TRAINING_DATA_MODE must be one of "
            f"{sorted(SUPPORTED_TRAINING_DATA_MODES)}. value={mode}"
        )

    return TrainingDataSelectionConfig(
        mode=mode,
        date_column=os.getenv("TRAINING_DATE_COLUMN", "training_event_at"),
        lookback_days=getenv_int(
            "TRAINING_LOOKBACK_DAYS",
            getenv_int("RETRAINING_LOOKBACK_DAYS", 180),
        ),
        recent_days=getenv_int(
            "TRAINING_RECENT_DAYS",
            getenv_int("RETRAINING_RECENT_DAYS", 90),
        ),
        history_sample_rows_per_class=getenv_int(
            "TRAINING_HISTORY_SAMPLE_ROWS_PER_CLASS",
            100,
        ),
        random_state=getenv_int("TRAINING_RANDOM_STATE", 42),
        min_rows_after_selection=getenv_int("TRAINING_MIN_ROWS_AFTER_SELECTION", 5),
    )


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def get_table_columns(engine: Engine, table_name: str) -> dict[str, str]:
    query = """
        SELECT
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
    """

    with engine.begin() as conn:
        rows = conn.execute(text(query), {"table_name": table_name}).mappings().all()

    return {
        str(row["column_name"]): str(row["data_type"])
        for row in rows
    }


def temporal_columns(
    columns: dict[str, str],
    candidates: list[str],
) -> list[str]:
    return [
        candidate
        for candidate in candidates
        if candidate in columns
        and columns[candidate].lower() in TEMPORAL_DATA_TYPES
    ]


def column_expression(alias: str, column_name: str) -> str:
    return f"{alias}.{quote_ident(column_name)}::timestamp"


def resolve_training_event_time_source(engine: Engine) -> TrainingEventTimeSource:
    cleaned_columns = get_table_columns(engine, "cleaned_job_posts")
    raw_columns = get_table_columns(engine, "raw_job_posts")

    cleaned_candidates = parse_column_candidates(
        "TRAINING_CLEANED_TIME_COLUMNS",
        DEFAULT_CLEANED_TIME_COLUMNS,
    )
    raw_candidates = parse_column_candidates(
        "TRAINING_RAW_TIME_COLUMNS",
        DEFAULT_RAW_TIME_COLUMNS,
    )

    cleaned_temporal_columns = temporal_columns(cleaned_columns, cleaned_candidates)
    raw_temporal_columns = temporal_columns(raw_columns, raw_candidates)

    source_expressions: list[str] = []
    source_columns: list[str] = []

    if cleaned_temporal_columns:
        selected_column = cleaned_temporal_columns[0]
        source_expressions.append(column_expression("c", selected_column))
        source_columns.append(f"cleaned_job_posts.{selected_column}")

    if raw_temporal_columns:
        selected_column = raw_temporal_columns[0]
        source_expressions.append(column_expression("r", selected_column))
        source_columns.append(f"raw_job_posts.{selected_column}")

    if not source_expressions:
        return TrainingEventTimeSource(
            expression="NULL::timestamp AS training_event_at",
            source_columns=[],
            cleaned_temporal_columns=cleaned_temporal_columns,
            raw_temporal_columns=raw_temporal_columns,
        )

    if len(source_expressions) == 1:
        expression = f"{source_expressions[0]} AS training_event_at"
    else:
        expression = f"COALESCE({', '.join(source_expressions)}) AS training_event_at"

    return TrainingEventTimeSource(
        expression=expression,
        source_columns=source_columns,
        cleaned_temporal_columns=cleaned_temporal_columns,
        raw_temporal_columns=raw_temporal_columns,
    )


def build_training_query(engine: Engine) -> str:
    event_time_source = resolve_training_event_time_source(engine)

    return f"""
        SELECT
            c.id,
            c.raw_id,
            COALESCE(r.source, 'unknown') AS source,
            c.text_for_model,
            c.job_category,
            {event_time_source.expression}
        FROM cleaned_job_posts c
        LEFT JOIN raw_job_posts r
        ON c.raw_id = r.id
        WHERE c.job_category IS NOT NULL
        AND c.job_category != 'Unknown'
        AND c.text_for_model IS NOT NULL
    """

def _category_distribution(df: pd.DataFrame) -> dict[str, int]:
    if "job_category" not in df.columns:
        return {}

    return {
        str(category): int(count)
        for category, count in (
            df["job_category"]
            .fillna("NULL")
            .value_counts()
            .sort_index()
            .items()
        )
    }


def _source_distribution(df: pd.DataFrame) -> dict[str, int]:
    if "source" not in df.columns:
        return {}

    return {
        str(source): int(count)
        for source, count in (
            df["source"]
            .fillna("NULL")
            .value_counts()
            .sort_index()
            .items()
        )
    }


def _fallback_full(
    df: pd.DataFrame,
    *,
    requested_mode: str,
    config: TrainingDataSelectionConfig,
    warning: str,
) -> TrainingDataSelectionResult:
    return TrainingDataSelectionResult(
        df=df.copy(),
        requested_mode=requested_mode,
        applied_mode="full",
        date_column=config.date_column,
        before_rows=len(df),
        after_rows=len(df),
        recent_rows=0,
        historical_rows=0,
        warning=warning,
        details={
            "reason": warning,
            "category_distribution": _category_distribution(df),
            "source_distribution": _source_distribution(df),
        },
    )


def _prepare_event_time(
    df: pd.DataFrame,
    config: TrainingDataSelectionConfig,
) -> pd.Series | None:
    if config.date_column not in df.columns:
        return None

    event_time = pd.to_datetime(df[config.date_column], errors="coerce")

    if event_time.notna().sum() == 0:
        return None

    return event_time


def select_training_data(
    df: pd.DataFrame,
    config: TrainingDataSelectionConfig | None = None,
) -> TrainingDataSelectionResult:
    resolved_config = config or load_training_data_selection_config()
    requested_mode = resolved_config.mode

    if df.empty:
        return TrainingDataSelectionResult(
            df=df.copy(),
            requested_mode=requested_mode,
            applied_mode=requested_mode,
            date_column=resolved_config.date_column,
            before_rows=0,
            after_rows=0,
            recent_rows=0,
            historical_rows=0,
            warning="Input dataframe is empty.",
            details={},
        )

    if requested_mode == "full":
        selected_df = df.copy()
        return TrainingDataSelectionResult(
            df=selected_df,
            requested_mode=requested_mode,
            applied_mode="full",
            date_column=resolved_config.date_column,
            before_rows=len(df),
            after_rows=len(selected_df),
            recent_rows=0,
            historical_rows=0,
            warning=None,
            details={
                "category_distribution": _category_distribution(selected_df),
                "source_distribution": _source_distribution(selected_df),
            },
        )

    event_time = _prepare_event_time(df, resolved_config)

    if event_time is None:
        return _fallback_full(
            df,
            requested_mode=requested_mode,
            config=resolved_config,
            warning=(
                f"TRAINING_DATA_MODE={requested_mode} requires "
                f"{resolved_config.date_column}, but no usable datetime values were found. "
                "Falling back to full training data."
            ),
        )

    now = event_time.max()

    if requested_mode == "lookback":
        cutoff = now - timedelta(days=resolved_config.lookback_days)
        selected_df = df[event_time >= cutoff].copy()

    elif requested_mode == "recent":
        cutoff = now - timedelta(days=resolved_config.recent_days)
        selected_df = df[event_time >= cutoff].copy()

    elif requested_mode == "recent_plus_history_sample":
        recent_cutoff = now - timedelta(days=resolved_config.recent_days)
        recent_df = df[event_time >= recent_cutoff].copy()
        historical_df = df[event_time < recent_cutoff].copy()

        if not historical_df.empty and "job_category" in historical_df.columns:
            sampled_groups = []

            for _, group in historical_df.groupby("job_category", group_keys=False):
                sampled_groups.append(
                    group.sample(
                        n=min(
                            len(group),
                            resolved_config.history_sample_rows_per_class,
                        ),
                        random_state=resolved_config.random_state,
                    )
                )

            if sampled_groups:
                sampled_history_df = pd.concat(sampled_groups, ignore_index=True)
            else:
                sampled_history_df = historical_df.head(0).copy()
        else:
            sampled_history_df = historical_df.head(0).copy()

        selected_df = pd.concat([recent_df, sampled_history_df], ignore_index=True)

        if "id" in selected_df.columns:
            selected_df = selected_df.drop_duplicates(subset=["id"], keep="first")

    else:
        raise ValueError(f"Unsupported TRAINING_DATA_MODE: {requested_mode}")

    if len(selected_df) < resolved_config.min_rows_after_selection:
        return _fallback_full(
            df,
            requested_mode=requested_mode,
            config=resolved_config,
            warning=(
                f"Selected training rows are too small. "
                f"selected={len(selected_df)}, "
                f"min={resolved_config.min_rows_after_selection}. "
                "Falling back to full training data."
            ),
        )

    selected_event_time = pd.to_datetime(
        selected_df[resolved_config.date_column],
        errors="coerce",
    )
    recent_cutoff = now - timedelta(days=resolved_config.recent_days)
    recent_rows = int((selected_event_time >= recent_cutoff).sum())
    historical_rows = int((selected_event_time < recent_cutoff).sum())

    return TrainingDataSelectionResult(
        df=selected_df.copy(),
        requested_mode=requested_mode,
        applied_mode=requested_mode,
        date_column=resolved_config.date_column,
        before_rows=len(df),
        after_rows=len(selected_df),
        recent_rows=recent_rows,
        historical_rows=historical_rows,
        warning=None,
        details={
            "max_event_time": str(now),
            "lookback_days": resolved_config.lookback_days,
            "recent_days": resolved_config.recent_days,
            "history_sample_rows_per_class": (
                resolved_config.history_sample_rows_per_class
            ),
            "category_distribution": _category_distribution(selected_df),
            "source_distribution": _source_distribution(selected_df),
        },
    )


def print_training_data_selection_result(
    result: TrainingDataSelectionResult,
) -> None:
    print("")
    print("[Training data selection]")
    print(f"requested_mode: {result.requested_mode}")
    print(f"applied_mode: {result.applied_mode}")
    print(f"date_column: {result.date_column}")
    print(f"before_rows: {result.before_rows}")
    print(f"after_rows: {result.after_rows}")
    print(f"recent_rows: {result.recent_rows}")
    print(f"historical_rows: {result.historical_rows}")

    if result.warning:
        print(f"warning: {result.warning}")

    print()


def log_training_data_selection_to_mlflow(
    result: TrainingDataSelectionResult,
    *,
    mlflow_module: Any,
) -> None:
    mlflow_module.log_param("training_data_requested_mode", result.requested_mode)
    mlflow_module.log_param("training_data_applied_mode", result.applied_mode)
    mlflow_module.log_param("training_data_date_column", result.date_column)
    mlflow_module.log_metric("training_data_before_selection_rows", result.before_rows)
    mlflow_module.log_metric("training_data_after_selection_rows", result.after_rows)
    mlflow_module.log_metric("training_data_recent_rows", result.recent_rows)
    mlflow_module.log_metric("training_data_historical_rows", result.historical_rows)

    if result.warning:
        mlflow_module.set_tag("training_data_selection_warning", result.warning[:250])

    mlflow_module.log_text(
        json.dumps(
            {
                "requested_mode": result.requested_mode,
                "applied_mode": result.applied_mode,
                "date_column": result.date_column,
                "before_rows": result.before_rows,
                "after_rows": result.after_rows,
                "recent_rows": result.recent_rows,
                "historical_rows": result.historical_rows,
                "warning": result.warning,
                "details": result.details,
            },
            ensure_ascii=False,
            indent=2,
        ),
        artifact_file="training_data_selection.json",
    )
