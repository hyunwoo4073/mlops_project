from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from src.common.db import get_engine


CHECK_TYPE = "TRAINING_DATA_SELECTION_POLICY"

EXPERIMENT_REPORT_PATH = Path(
    os.getenv(
        "TRAINING_DATA_SELECTION_EXPERIMENT_REPORT_PATH",
        "reports/latest_training_data_selection_experiment_report.md",
    )
)

POLICY_REPORT_PATH = Path(
    os.getenv(
        "TRAINING_DATA_SELECTION_POLICY_REPORT_PATH",
        "reports/latest_training_data_selection_policy_report.md",
    )
)


@dataclass(frozen=True)
class ExperimentRow:
    mode: str
    status: str
    requested_mode: str
    applied_mode: str
    after_rows: int | None
    accuracy: float | None
    f1_weighted: float | None
    duration_seconds: float | None


@dataclass(frozen=True)
class PolicyDecision:
    mode: str
    status: str
    recommendation: str
    accuracy_delta: float | None
    f1_delta: float | None
    duration_ratio: float | None
    row_ratio: float | None
    reasons: list[str]


def getenv_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value == "":
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def getenv_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value == "":
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float. value={raw_value}") from exc


def getenv_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value == "":
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer. value={raw_value}") from exc


def parse_float(value: str) -> float | None:
    value = value.strip()

    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str) -> int | None:
    value = value.strip()

    if value == "":
        return None

    try:
        return int(value)
    except ValueError:
        return None


def safe_ratio(
    numerator: float | int | None,
    denominator: float | int | None,
) -> float | None:
    if numerator is None or denominator is None:
        return None

    if denominator == 0:
        return None

    return float(numerator) / float(denominator)


def find_markdown_table(markdown: str) -> list[dict[str, str]]:
    lines = markdown.splitlines()
    table_start = None

    for index, line in enumerate(lines):
        if line.strip().startswith("| mode |"):
            table_start = index
            break

    if table_start is None:
        raise ValueError(
            "Experiment result table not found. "
            "Run make training-data-selection-experiment first."
        )

    headers = [
        value.strip().replace("\\_", "_")
        for value in lines[table_start].strip().strip("|").split("|")
    ]

    rows: list[dict[str, str]] = []

    for line in lines[table_start + 2:]:
        stripped = line.strip()

        if not stripped.startswith("|"):
            break

        values = [
            value.strip().replace("\\_", "_")
            for value in stripped.strip("|").split("|")
        ]

        if len(values) != len(headers):
            continue

        rows.append(dict(zip(headers, values, strict=False)))

    return rows


def load_experiment_rows() -> list[ExperimentRow]:
    if not EXPERIMENT_REPORT_PATH.exists():
        raise FileNotFoundError(
            f"Experiment report not found: {EXPERIMENT_REPORT_PATH}"
        )

    markdown = EXPERIMENT_REPORT_PATH.read_text(encoding="utf-8")
    raw_rows = find_markdown_table(markdown)

    rows: list[ExperimentRow] = []

    for row in raw_rows:
        rows.append(
            ExperimentRow(
                mode=row.get("mode", ""),
                status=row.get("status", ""),
                requested_mode=row.get("requested_mode", ""),
                applied_mode=row.get("applied_mode", ""),
                after_rows=parse_int(row.get("after_rows", "")),
                accuracy=parse_float(row.get("accuracy", "")),
                f1_weighted=parse_float(row.get("f1_weighted", "")),
                duration_seconds=parse_float(row.get("duration_seconds", "")),
            )
        )

    return rows


def load_class_distribution() -> dict[str, int]:
    engine = get_engine()

    query = text(
        """
        SELECT
            job_category,
            COUNT(*) AS row_count
        FROM cleaned_job_posts
        WHERE job_category IS NOT NULL
          AND job_category != 'Unknown'
        GROUP BY job_category
        ORDER BY job_category
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(query).mappings().all()

    return {
        str(row["job_category"]): int(row["row_count"])
        for row in rows
    }


def load_event_time_coverage() -> dict[str, int]:
    engine = get_engine()

    query = text(
        """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(r.crawled_at) AS usable_event_time_rows,
            COUNT(DISTINCT DATE(r.crawled_at)) AS distinct_event_dates
        FROM cleaned_job_posts c
        LEFT JOIN raw_job_posts r
        ON c.raw_id = r.id
        WHERE c.job_category IS NOT NULL
          AND c.job_category != 'Unknown'
          AND c.text_for_model IS NOT NULL
        """
    )

    with engine.begin() as conn:
        row = conn.execute(query).mappings().one()

    return {
        "total_rows": int(row["total_rows"] or 0),
        "usable_event_time_rows": int(row["usable_event_time_rows"] or 0),
        "distinct_event_dates": int(row["distinct_event_dates"] or 0),
    }


def build_evidence_reasons(
    *,
    baseline: ExperimentRow,
    candidate: ExperimentRow,
    class_distribution: dict[str, int],
    event_time_coverage: dict[str, int],
) -> list[str]:
    reasons: list[str] = []

    min_baseline_rows = getenv_int(
        "TRAINING_SELECTION_MIN_BASELINE_ROWS",
        3000,
    )
    min_rows_per_class = getenv_int(
        "TRAINING_SELECTION_MIN_ROWS_PER_CLASS",
        300,
    )
    min_distinct_event_dates = getenv_int(
        "TRAINING_SELECTION_MIN_DISTINCT_EVENT_DATES",
        90,
    )
    require_row_reduction = getenv_bool(
        "TRAINING_SELECTION_REQUIRE_ROW_REDUCTION",
        True,
    )
    max_row_ratio = getenv_float(
        "TRAINING_SELECTION_MAX_ROW_RATIO",
        0.90,
    )

    if baseline.after_rows is None:
        reasons.append("baseline row count is unavailable.")
    elif baseline.after_rows < min_baseline_rows:
        reasons.append(
            "baseline rows are too small. "
            f"rows={baseline.after_rows}, min={min_baseline_rows}"
        )

    small_classes = {
        category: row_count
        for category, row_count in class_distribution.items()
        if row_count < min_rows_per_class
    }

    if small_classes:
        reasons.append(
            "class coverage is too small. "
            f"min_rows_per_class={min_rows_per_class}, "
            f"small_classes={small_classes}"
        )

    usable_event_time_rows = event_time_coverage.get("usable_event_time_rows", 0)
    total_event_time_rows = event_time_coverage.get("total_rows", 0)
    distinct_event_dates = event_time_coverage.get("distinct_event_dates", 0)

    if total_event_time_rows <= 0:
        reasons.append("event-time coverage is unavailable.")
    elif usable_event_time_rows < total_event_time_rows:
        reasons.append(
            "some training rows have no usable event time. "
            f"usable={usable_event_time_rows}, total={total_event_time_rows}"
        )

    if distinct_event_dates < min_distinct_event_dates:
        reasons.append(
            "event-time coverage is too small. "
            f"distinct_event_dates={distinct_event_dates}, "
            f"min={min_distinct_event_dates}"
        )

    row_ratio = safe_ratio(candidate.after_rows, baseline.after_rows)

    if require_row_reduction:
        if row_ratio is None:
            reasons.append("row reduction check is unavailable.")
        elif row_ratio > max_row_ratio:
            reasons.append(
                "row reduction is not enough. "
                f"row_ratio={row_ratio:.4f}, "
                f"max_row_ratio={max_row_ratio:.4f}"
            )

    return reasons


def decide_candidate(
    *,
    baseline: ExperimentRow,
    candidate: ExperimentRow,
    class_distribution: dict[str, int],
    event_time_coverage: dict[str, int],
    max_accuracy_drop: float,
    max_f1_drop: float,
    max_duration_ratio: float,
    max_row_ratio: float,
) -> PolicyDecision:
    reasons: list[str] = []

    evidence_reasons = build_evidence_reasons(
        baseline=baseline,
        candidate=candidate,
        class_distribution=class_distribution,
        event_time_coverage=event_time_coverage,
    )

    if candidate.status != "PASS":
        reasons.append(f"candidate status is not PASS. status={candidate.status}")

    if candidate.requested_mode != candidate.applied_mode:
        reasons.append(
            "candidate mode fell back. "
            f"requested={candidate.requested_mode}, applied={candidate.applied_mode}"
        )

    if baseline.accuracy is None or candidate.accuracy is None:
        accuracy_delta = None
        reasons.append("accuracy comparison is unavailable.")
    else:
        accuracy_delta = candidate.accuracy - baseline.accuracy

        if accuracy_delta < -max_accuracy_drop:
            reasons.append(
                "accuracy drop exceeds threshold. "
                f"delta={accuracy_delta:.4f}, threshold=-{max_accuracy_drop:.4f}"
            )

    if baseline.f1_weighted is None or candidate.f1_weighted is None:
        f1_delta = None
        reasons.append("weighted F1 comparison is unavailable.")
    else:
        f1_delta = candidate.f1_weighted - baseline.f1_weighted

        if f1_delta < -max_f1_drop:
            reasons.append(
                "weighted F1 drop exceeds threshold. "
                f"delta={f1_delta:.4f}, threshold=-{max_f1_drop:.4f}"
            )

    duration_ratio = safe_ratio(
        candidate.duration_seconds,
        baseline.duration_seconds,
    )
    row_ratio = safe_ratio(
        candidate.after_rows,
        baseline.after_rows,
    )

    has_cost_benefit = False

    if duration_ratio is not None and duration_ratio <= max_duration_ratio:
        has_cost_benefit = True

    if row_ratio is not None and row_ratio <= max_row_ratio:
        has_cost_benefit = True

    if not has_cost_benefit:
        reasons.append(
            "candidate does not show enough cost benefit. "
            f"duration_ratio={duration_ratio}, row_ratio={row_ratio}"
        )

    if evidence_reasons:
        return PolicyDecision(
            mode=candidate.mode,
            status="PASS",
            recommendation="INSUFFICIENT_EXPERIMENT_DATA",
            accuracy_delta=accuracy_delta,
            f1_delta=f1_delta,
            duration_ratio=duration_ratio,
            row_ratio=row_ratio,
            reasons=evidence_reasons + reasons,
        )

    if reasons:
        return PolicyDecision(
            mode=candidate.mode,
            status="PASS",
            recommendation="KEEP_FULL_RETRAIN",
            accuracy_delta=accuracy_delta,
            f1_delta=f1_delta,
            duration_ratio=duration_ratio,
            row_ratio=row_ratio,
            reasons=reasons,
        )

    return PolicyDecision(
        mode=candidate.mode,
        status="WARN",
        recommendation="CANDIDATE_FOR_SHADOW_PROMOTION",
        accuracy_delta=accuracy_delta,
        f1_delta=f1_delta,
        duration_ratio=duration_ratio,
        row_ratio=row_ratio,
        reasons=[],
    )


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


def get_table_columns(conn, table_name: str) -> set[str]:
    rows = conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).mappings().all()

    return {str(row["column_name"]) for row in rows}


def insert_pipeline_check(
    *,
    check_name: str,
    status: str,
    metric_value: float | None,
    threshold_value: float | None,
    message: str,
) -> None:
    if not getenv_bool("TRAINING_DATA_SELECTION_POLICY_WRITE_DB", True):
        return

    engine = get_engine()

    with engine.begin() as conn:
        columns = get_table_columns(conn, "pipeline_check_results")

        values = {
            "check_type": CHECK_TYPE,
            "check_name": check_name,
            "status": status,
            "metric_value": metric_value,
            "threshold_value": threshold_value,
            "message": message[:500],
            "dag_id": "manual",
            "task_id": "check_training_data_selection_policy",
            "run_id": "",
            "checked_at": datetime.now(),
        }

        insert_columns = [
            column
            for column in [
                "check_type",
                "check_name",
                "status",
                "metric_value",
                "threshold_value",
                "message",
                "dag_id",
                "task_id",
                "run_id",
                "checked_at",
            ]
            if column in columns
        ]

        if not insert_columns:
            return

        column_sql = ", ".join(insert_columns)
        value_sql = ", ".join(f":{column}" for column in insert_columns)

        conn.execute(
            text(
                f"""
                INSERT INTO pipeline_check_results ({column_sql})
                VALUES ({value_sql})
                """
            ),
            {column: values[column] for column in insert_columns},
        )


def write_decisions_to_db(decisions: list[PolicyDecision]) -> None:
    max_accuracy_drop = getenv_float("TRAINING_SELECTION_MAX_ACCURACY_DROP", 0.02)
    max_f1_drop = getenv_float("TRAINING_SELECTION_MAX_F1_DROP", 0.02)
    max_duration_ratio = getenv_float("TRAINING_SELECTION_MAX_DURATION_RATIO", 0.90)
    max_row_ratio = getenv_float("TRAINING_SELECTION_MAX_ROW_RATIO", 0.90)

    for decision in decisions:
        insert_pipeline_check(
            check_name=f"{decision.mode}_accuracy_delta",
            status=decision.status,
            metric_value=decision.accuracy_delta,
            threshold_value=-max_accuracy_drop,
            message=f"{decision.recommendation}: accuracy_delta={decision.accuracy_delta}",
        )

        insert_pipeline_check(
            check_name=f"{decision.mode}_f1_delta",
            status=decision.status,
            metric_value=decision.f1_delta,
            threshold_value=-max_f1_drop,
            message=f"{decision.recommendation}: f1_delta={decision.f1_delta}",
        )

        insert_pipeline_check(
            check_name=f"{decision.mode}_duration_ratio",
            status=decision.status,
            metric_value=decision.duration_ratio,
            threshold_value=max_duration_ratio,
            message=f"{decision.recommendation}: duration_ratio={decision.duration_ratio}",
        )

        insert_pipeline_check(
            check_name=f"{decision.mode}_row_ratio",
            status=decision.status,
            metric_value=decision.row_ratio,
            threshold_value=max_row_ratio,
            message=f"{decision.recommendation}: row_ratio={decision.row_ratio}",
        )


def preferred_candidate(decisions: list[PolicyDecision]) -> PolicyDecision | None:
    candidates = [
        decision
        for decision in decisions
        if decision.recommendation == "CANDIDATE_FOR_SHADOW_PROMOTION"
    ]

    if not candidates:
        return None

    # 성능 보존을 우선하고, 같은 수준이면 row reduction이 큰 후보를 고른다.
    return sorted(
        candidates,
        key=lambda decision: (
            decision.f1_delta if decision.f1_delta is not None else -999.0,
            -(decision.row_ratio if decision.row_ratio is not None else 999.0),
        ),
        reverse=True,
    )[0]


def write_report(
    *,
    rows: list[ExperimentRow],
    decisions: list[PolicyDecision],
    class_distribution: dict[str, int],
    event_time_coverage: dict[str, int],
    max_accuracy_drop: float,
    max_f1_drop: float,
    max_duration_ratio: float,
    max_row_ratio: float,
) -> None:
    POLICY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    candidate = preferred_candidate(decisions)

    if candidate is None:
        summary = "No candidate mode passed the policy. Keep full retrain as the operating baseline."
    else:
        summary = (
            f"{candidate.mode} is the preferred shadow-validation candidate. "
            "Do not change promoted model automatically."
        )

    experiment_rows = [
        {
            "mode": row.mode,
            "status": row.status,
            "requested_mode": row.requested_mode,
            "applied_mode": row.applied_mode,
            "after_rows": row.after_rows,
            "accuracy": row.accuracy,
            "f1_weighted": row.f1_weighted,
            "duration_seconds": row.duration_seconds,
        }
        for row in rows
    ]

    decision_rows = [
        {
            "mode": decision.mode,
            "status": decision.status,
            "recommendation": decision.recommendation,
            "accuracy_delta": decision.accuracy_delta,
            "f1_delta": decision.f1_delta,
            "duration_ratio": decision.duration_ratio,
            "row_ratio": decision.row_ratio,
            "reason_count": len(decision.reasons),
        }
        for decision in decisions
    ]

    class_rows = [
        {
            "job_category": category,
            "row_count": row_count,
        }
        for category, row_count in class_distribution.items()
    ]

    lines = [
        "# JobSkill Training Data Selection Policy Report",
        "",
        f"- Generated at: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- Source report: `{EXPERIMENT_REPORT_PATH}`",
        "",
        "## Summary Recommendation",
        "",
        f"- {summary}",
        "",
        "## Policy Thresholds",
        "",
        f"- max_accuracy_drop: `{max_accuracy_drop}`",
        f"- max_f1_drop: `{max_f1_drop}`",
        f"- max_duration_ratio: `{max_duration_ratio}`",
        f"- max_row_ratio: `{max_row_ratio}`",
        "",
        "## Evidence Thresholds",
        "",
        f"- min_baseline_rows: `{getenv_int('TRAINING_SELECTION_MIN_BASELINE_ROWS', 3000)}`",
        f"- min_rows_per_class: `{getenv_int('TRAINING_SELECTION_MIN_ROWS_PER_CLASS', 300)}`",
        f"- min_distinct_event_dates: `{getenv_int('TRAINING_SELECTION_MIN_DISTINCT_EVENT_DATES', 90)}`",
        f"- require_row_reduction: `{getenv_bool('TRAINING_SELECTION_REQUIRE_ROW_REDUCTION', True)}`",
        "",
        "## Event Time Coverage",
        "",
        f"- total_rows: `{event_time_coverage.get('total_rows', 0)}`",
        f"- usable_event_time_rows: `{event_time_coverage.get('usable_event_time_rows', 0)}`",
        f"- distinct_event_dates: `{event_time_coverage.get('distinct_event_dates', 0)}`",
        "",
        "## Class Distribution",
        "",
        markdown_table(
            ["job_category", "row_count"],
            class_rows,
        ),
        "",
        "## Experiment Results",
        "",
        markdown_table(
            [
                "mode",
                "status",
                "requested_mode",
                "applied_mode",
                "after_rows",
                "accuracy",
                "f1_weighted",
                "duration_seconds",
            ],
            experiment_rows,
        ),
        "",
        "## Policy Decisions",
        "",
        markdown_table(
            [
                "mode",
                "status",
                "recommendation",
                "accuracy_delta",
                "f1_delta",
                "duration_ratio",
                "row_ratio",
                "reason_count",
            ],
            decision_rows,
        ),
        "",
        "## Decision Reasons",
        "",
    ]

    for decision in decisions:
        lines.append(f"### {decision.mode}")
        lines.append("")

        if not decision.reasons:
            lines.append("- Candidate satisfies the configured policy and evidence thresholds.")
        else:
            for reason in decision.reasons:
                lines.append(f"- {reason}")

        lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            "- `INSUFFICIENT_EXPERIMENT_DATA` means the experiment does not have enough row count, class coverage, event-time coverage, or row reduction to recommend a non-full mode.",
            "- `KEEP_FULL_RETRAIN` means evidence is sufficient, but the candidate failed the configured performance or cost-benefit policy.",
            "- `CANDIDATE_FOR_SHADOW_PROMOTION` means the mode is worth repeated shadow validation.",
            "- This check does not promote or replace any model artifact.",
            "",
        ]
    )

    POLICY_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    max_accuracy_drop = getenv_float("TRAINING_SELECTION_MAX_ACCURACY_DROP", 0.02)
    max_f1_drop = getenv_float("TRAINING_SELECTION_MAX_F1_DROP", 0.02)
    max_duration_ratio = getenv_float("TRAINING_SELECTION_MAX_DURATION_RATIO", 0.90)
    max_row_ratio = getenv_float("TRAINING_SELECTION_MAX_ROW_RATIO", 0.90)

    rows = load_experiment_rows()
    baseline = next((row for row in rows if row.mode == "full"), None)

    if baseline is None:
        raise ValueError("full baseline row not found in experiment report.")

    class_distribution = load_class_distribution()
    event_time_coverage = load_event_time_coverage()

    decisions = [
        decide_candidate(
            baseline=baseline,
            candidate=row,
            class_distribution=class_distribution,
            event_time_coverage=event_time_coverage,
            max_accuracy_drop=max_accuracy_drop,
            max_f1_drop=max_f1_drop,
            max_duration_ratio=max_duration_ratio,
            max_row_ratio=max_row_ratio,
        )
        for row in rows
        if row.mode != "full"
    ]

    write_report(
        rows=rows,
        decisions=decisions,
        class_distribution=class_distribution,
        event_time_coverage=event_time_coverage,
        max_accuracy_drop=max_accuracy_drop,
        max_f1_drop=max_f1_drop,
        max_duration_ratio=max_duration_ratio,
        max_row_ratio=max_row_ratio,
    )

    write_decisions_to_db(decisions)

    print("Training data selection policy check completed")
    print(f"experiment_report_path={EXPERIMENT_REPORT_PATH}")
    print(f"policy_report_path={POLICY_REPORT_PATH}")
    print(f"class_distribution={class_distribution}")
    print(f"event_time_coverage={event_time_coverage}")

    for decision in decisions:
        print(
            f"{decision.mode}: status={decision.status}, "
            f"recommendation={decision.recommendation}, "
            f"f1_delta={format_value(decision.f1_delta)}, "
            f"duration_ratio={format_value(decision.duration_ratio)}, "
            f"row_ratio={format_value(decision.row_ratio)}"
        )

    if getenv_bool("TRAINING_DATA_SELECTION_POLICY_STRICT", False):
        if any(decision.status != "PASS" for decision in decisions):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
