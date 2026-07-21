from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text


sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine


def _escape_label_value(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _label(name: str, value: Any) -> str:
    return f'{name}="{_escape_label_value(value)}"'

def is_alert_maintenance_mode_enabled() -> bool:
    return os.getenv("ALERT_MAINTENANCE_MODE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }

def parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }

def _metric_line(name: str, value: int | float, labels: dict[str, Any] | None = None) -> str:
    if labels:
        label_text = ",".join(_label(key, val) for key, val in labels.items())
        return f"{name}{{{label_text}}} {value}"

    return f"{name} {value}"


def _add_metric(
    lines: list[str],
    name: str,
    metric_type: str,
    help_text: str,
    values: list[tuple[dict[str, Any] | None, int | float]],
) -> None:
    lines.append(f"# HELP {name} {help_text}")
    lines.append(f"# TYPE {name} {metric_type}")

    for labels, value in values:
        lines.append(_metric_line(name, value, labels))

    lines.append("")


def _float_or_zero(value: Any) -> float:
    if value is None:
        return 0.0

    return float(value)

def resolve_model_path(model_path: str | None) -> Path | None:
    if not model_path:
        return None

    path = Path(model_path)

    if path.is_absolute():
        return path

    return Path.cwd() / path


def build_readiness_status(latest_model: dict[str, Any] | None) -> dict[str, int]:
    database_ready = 1

    promoted_model_ready = 1 if latest_model else 0

    promoted_model_file_exists = 0

    if latest_model:
        promoted_model_path = latest_model.get("promoted_model_path")
        resolved_path = resolve_model_path(promoted_model_path)
        promoted_model_file_exists = (
            1 if resolved_path is not None and resolved_path.exists() else 0
        )

    api_ready = (
        1
        if database_ready == 1
        and promoted_model_ready == 1
        and promoted_model_file_exists == 1
        else 0
    )

    return {
        "api_ready": api_ready,
        "database_ready": database_ready,
        "promoted_model_ready": promoted_model_ready,
        "promoted_model_file_exists": promoted_model_file_exists,
    }

def build_metrics_text() -> str:
    engine = get_engine()
    lines: list[str] = []

    with engine.begin() as conn:
        alert_settings_exists = conn.execute(
            text("SELECT to_regclass('public.alert_settings') IS NOT NULL")
        ).scalar()

        if alert_settings_exists:
            maintenance_mode_row = conn.execute(
                text(
                    """
                    SELECT setting_value
                    FROM alert_settings
                    WHERE setting_key = 'maintenance_mode'
                    """
                )
            ).mappings().first()

            maintenance_mode_enabled = (
                parse_bool(maintenance_mode_row["setting_value"])
                if maintenance_mode_row
                else is_alert_maintenance_mode_enabled()
            )
        else:
            maintenance_mode_enabled = is_alert_maintenance_mode_enabled()
        raw_rows = conn.execute(
            text(
                """
                SELECT
                    COALESCE(source, 'unknown') AS source,
                    COUNT(*) AS count
                FROM raw_job_posts
                GROUP BY COALESCE(source, 'unknown')
                ORDER BY source
                """
            )
        ).mappings().all()

        cleaned_rows = conn.execute(
            text(
                """
                SELECT
                    COALESCE(r.source, 'unknown') AS source,
                    COUNT(*) AS count
                FROM cleaned_job_posts c
                LEFT JOIN raw_job_posts r
                    ON c.raw_id = r.id
                GROUP BY COALESCE(r.source, 'unknown')
                ORDER BY source
                """
            )
        ).mappings().all()

        skill_rows = conn.execute(
            text(
                """
                SELECT
                    skill_name,
                    COUNT(*) AS count
                FROM job_post_skills
                GROUP BY skill_name
                ORDER BY COUNT(*) DESC, skill_name
                LIMIT 20
                """
            )
        ).mappings().all()

        prediction_rows = conn.execute(
            text(
                """
                SELECT
                    COALESCE(prediction_source, 'BATCH') AS prediction_source,
                    COUNT(*) AS prediction_count,
                    AVG(confidence) AS avg_confidence,
                    COUNT(*) FILTER (WHERE is_low_confidence = true) AS low_confidence_count
                FROM model_predictions
                GROUP BY COALESCE(prediction_source, 'BATCH')
                ORDER BY prediction_source
                """
            )
        ).mappings().all()

        prediction_category_rows = conn.execute(
            text(
                """
                SELECT
                    COALESCE(prediction_source, 'BATCH') AS prediction_source,
                    COALESCE(predicted_category, 'Unknown') AS predicted_category,
                    COUNT(*) AS count
                FROM model_predictions
                GROUP BY
                    COALESCE(prediction_source, 'BATCH'),
                    COALESCE(predicted_category, 'Unknown')
                ORDER BY prediction_source, predicted_category
                """
            )
        ).mappings().all()

        api_rows = conn.execute(
            text(
                """
                SELECT
                    status,
                    COUNT(*) AS request_count,
                    AVG(latency_ms) AS avg_latency_ms
                FROM api_prediction_logs
                GROUP BY status
                ORDER BY status
                """
            )
        ).mappings().all()

        check_rows = conn.execute(
            text(
                """
                SELECT
                    check_type,
                    status,
                    COUNT(*) AS count
                FROM pipeline_check_results
                GROUP BY check_type, status
                ORDER BY check_type, status
                """
            )
        ).mappings().all()

        recent_failed_check_rows = conn.execute(
            text(
                """
                SELECT
                    check_type,
                    status,
                    COUNT(*) AS count
                FROM pipeline_check_results
                WHERE UPPER(status) NOT IN ('PASS', 'SUCCESS')
                  AND checked_at >= NOW() - INTERVAL '1 hour'
                GROUP BY check_type, status
                ORDER BY check_type, status
                """
            )
        ).mappings().all()

        registry_rows = conn.execute(
            text(
                """
                SELECT
                    status,
                    COUNT(*) AS count
                FROM model_registry
                GROUP BY status
                ORDER BY status
                """
            )
        ).mappings().all()

        latest_model = conn.execute(
            text(
                """
                SELECT
                    id,
                    model_name,
                    accuracy,
                    f1_weighted,
                    promoted_model_path
                FROM model_registry
                WHERE status = 'PROMOTED'
                ORDER BY id DESC
                LIMIT 1
                """
            )
        ).mappings().first()

        alert_event_rows = conn.execute(
            text(
                """
                SELECT
                    COALESCE(alert_name, 'unknown') AS alert_name,
                    COALESCE(severity, 'unknown') AS severity,
                    COALESCE(service, 'unknown') AS service,
                    status,
                    COUNT(*) AS count
                FROM alert_events
                GROUP BY
                    COALESCE(alert_name, 'unknown'),
                    COALESCE(severity, 'unknown'),
                    COALESCE(service, 'unknown'),
                    status
                ORDER BY alert_name, severity, service, status
                """
            )
        ).mappings().all()

        alert_current_state_rows = conn.execute(
            text(
                """
                SELECT
                    COALESCE(alert_name, 'unknown') AS alert_name,
                    COALESCE(severity, 'unknown') AS severity,
                    COALESCE(service, 'unknown') AS service,
                    status,
                    COUNT(*) AS count
                FROM alert_current_states
                GROUP BY
                    COALESCE(alert_name, 'unknown'),
                    COALESCE(severity, 'unknown'),
                    COALESCE(service, 'unknown'),
                    status
                ORDER BY alert_name, severity, service, status
                """
            )
        ).mappings().all()

        alert_acknowledgement_rows = conn.execute(
            text(
                """
                SELECT
                    COALESCE(alert_name, 'unknown') AS alert_name,
                    COALESCE(severity, 'unknown') AS severity,
                    COALESCE(service, 'unknown') AS service,
                    COALESCE(status, 'unknown') AS status,
                    COUNT(*) AS count
                FROM alert_acknowledgements
                GROUP BY
                    COALESCE(alert_name, 'unknown'),
                    COALESCE(severity, 'unknown'),
                    COALESCE(service, 'unknown'),
                    COALESCE(status, 'unknown')
                ORDER BY alert_name, severity, service, status
                """
            )
        ).mappings().all()

        alert_response_metric_rows = conn.execute(
            text(
                """
                WITH firing_alerts AS (
                    SELECT
                        fingerprint,
                        COALESCE(alert_name, 'unknown') AS alert_name,
                        COALESCE(severity, 'unknown') AS severity,
                        COALESCE(service, 'unknown') AS service,
                        MIN(COALESCE(starts_at, created_at)) AS first_fired_at
                    FROM alert_events
                    WHERE status = 'firing'
                      AND fingerprint IS NOT NULL
                    GROUP BY
                        fingerprint,
                        COALESCE(alert_name, 'unknown'),
                        COALESCE(severity, 'unknown'),
                        COALESCE(service, 'unknown')
                ),
                first_acknowledgements AS (
                    SELECT
                        fingerprint,
                        MIN(created_at) AS first_acknowledged_at
                    FROM alert_acknowledgements
                    WHERE fingerprint IS NOT NULL
                    GROUP BY fingerprint
                ),
                resolved_alerts AS (
                    SELECT
                        fingerprint,
                        MIN(COALESCE(ends_at, created_at)) AS first_resolved_at
                    FROM alert_events
                    WHERE status = 'resolved'
                      AND fingerprint IS NOT NULL
                    GROUP BY fingerprint
                )
                SELECT
                    f.alert_name,
                    f.severity,
                    f.service,
                    COUNT(*) AS alert_count,
                    COUNT(a.first_acknowledged_at) AS acknowledged_count,
                    COUNT(r.first_resolved_at) AS resolved_count,
                    ROUND(
                        AVG(
                            EXTRACT(
                                EPOCH FROM (
                                    a.first_acknowledged_at - f.first_fired_at
                                )
                            ) / 60
                        )::numeric,
                        4
                    ) AS avg_mtta_minutes,
                    ROUND(
                        AVG(
                            EXTRACT(
                                EPOCH FROM (
                                    r.first_resolved_at - f.first_fired_at
                                )
                            ) / 60
                        )::numeric,
                        4
                    ) AS avg_mttr_minutes
                FROM firing_alerts f
                LEFT JOIN first_acknowledgements a
                    ON f.fingerprint = a.fingerprint
                   AND a.first_acknowledged_at >= f.first_fired_at
                LEFT JOIN resolved_alerts r
                    ON f.fingerprint = r.fingerprint
                   AND r.first_resolved_at >= f.first_fired_at
                GROUP BY
                    f.alert_name,
                    f.severity,
                    f.service
                ORDER BY f.alert_name, f.severity, f.service
                """
            )
        ).mappings().all()

        current_unacknowledged_alert_rows = conn.execute(
            text(
                """
                SELECT
                    COALESCE(cs.alert_name, 'unknown') AS alert_name,
                    COALESCE(cs.severity, 'unknown') AS severity,
                    COALESCE(cs.service, 'unknown') AS service,
                    COUNT(*) AS count
                FROM alert_current_states cs
                LEFT JOIN alert_acknowledgements aa
                    ON cs.fingerprint = aa.fingerprint
                WHERE cs.status = 'firing'
                  AND aa.id IS NULL
                GROUP BY
                    COALESCE(cs.alert_name, 'unknown'),
                    COALESCE(cs.severity, 'unknown'),
                    COALESCE(cs.service, 'unknown')
                ORDER BY alert_name, severity, service
                """
            )
        ).mappings().all()

    _add_metric(
        lines=lines,
        name="jobskill_alert_maintenance_mode",
        metric_type="gauge",
        help_text=(
            "Whether alert maintenance mode is enabled. "
            "1 means non-critical alert rules should be suppressed."
        ),
        values=[
            (
                {},
                1 if maintenance_mode_enabled else 0,
            )
        ],
    )

    readiness_status = build_readiness_status(latest_model)

    _add_metric(
        lines=lines,
        name="jobskill_api_ready",
        metric_type="gauge",
        help_text=(
            "Whether the FastAPI service is ready to serve prediction requests. "
            "1 means database, promoted model metadata and promoted model file are ready."
        ),
        values=[
            (
                {},
                readiness_status["api_ready"],
            )
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_api_database_ready",
        metric_type="gauge",
        help_text="Whether the FastAPI service can query the PostgreSQL database.",
        values=[
            (
                {},
                readiness_status["database_ready"],
            )
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_api_promoted_model_ready",
        metric_type="gauge",
        help_text="Whether a PROMOTED model exists in model_registry.",
        values=[
            (
                {},
                readiness_status["promoted_model_ready"],
            )
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_api_promoted_model_file_exists",
        metric_type="gauge",
        help_text="Whether the promoted model file exists on the FastAPI container filesystem.",
        values=[
            (
                {},
                readiness_status["promoted_model_file_exists"],
            )
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_raw_job_posts_total",
        metric_type="gauge",
        help_text="Total raw job posts by source.",
        values=[
            ({"source": row["source"]}, int(row["count"]))
            for row in raw_rows
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_cleaned_job_posts_total",
        metric_type="gauge",
        help_text="Total cleaned job posts by source.",
        values=[
            ({"source": row["source"]}, int(row["count"]))
            for row in cleaned_rows
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_top_skills_total",
        metric_type="gauge",
        help_text="Top extracted skills count.",
        values=[
            ({"skill_name": row["skill_name"]}, int(row["count"]))
            for row in skill_rows
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_model_predictions_total",
        metric_type="gauge",
        help_text="Total model predictions by prediction source.",
        values=[
            ({"prediction_source": row["prediction_source"]}, int(row["prediction_count"]))
            for row in prediction_rows
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_model_prediction_avg_confidence",
        metric_type="gauge",
        help_text="Average prediction confidence by prediction source.",
        values=[
            (
                {"prediction_source": row["prediction_source"]},
                _float_or_zero(row["avg_confidence"]),
            )
            for row in prediction_rows
        ],
    )

    low_confidence_ratio_values: list[tuple[dict[str, Any] | None, int | float]] = []

    for row in prediction_rows:
        prediction_count = int(row["prediction_count"] or 0)
        low_confidence_count = int(row["low_confidence_count"] or 0)
        ratio = low_confidence_count / prediction_count if prediction_count > 0 else 0.0

        low_confidence_ratio_values.append(
            (
                {"prediction_source": row["prediction_source"]},
                ratio,
            )
        )

    _add_metric(
        lines=lines,
        name="jobskill_model_prediction_low_confidence_ratio",
        metric_type="gauge",
        help_text="Low confidence prediction ratio by prediction source.",
        values=low_confidence_ratio_values,
    )

    _add_metric(
        lines=lines,
        name="jobskill_model_prediction_category_total",
        metric_type="gauge",
        help_text="Total model predictions by prediction source and predicted category.",
        values=[
            (
                {
                    "prediction_source": row["prediction_source"],
                    "predicted_category": row["predicted_category"],
                },
                int(row["count"]),
            )
            for row in prediction_category_rows
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_api_prediction_requests_total",
        metric_type="gauge",
        help_text="Total FastAPI prediction requests by status.",
        values=[
            ({"status": row["status"]}, int(row["request_count"]))
            for row in api_rows
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_api_prediction_avg_latency_ms",
        metric_type="gauge",
        help_text="Average FastAPI prediction latency in milliseconds by status.",
        values=[
            (
                {"status": row["status"]},
                _float_or_zero(row["avg_latency_ms"]),
            )
            for row in api_rows
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_pipeline_check_results_total",
        metric_type="gauge",
        help_text="Total pipeline check results by check type and status.",
        values=[
            (
                {
                    "check_type": row["check_type"],
                    "status": row["status"],
                },
                int(row["count"]),
            )
            for row in check_rows
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_model_registry_records_total",
        metric_type="gauge",
        help_text="Total model registry records by status.",
        values=[
            ({"status": row["status"]}, int(row["count"]))
            for row in registry_rows
        ],
    )

    recent_failed_check_values = [
        (
            {
                "check_type": row["check_type"],
                "status": row["status"],
            },
            row["cnt"],
        )
        for row in recent_failed_check_rows
    ]

    if not recent_failed_check_values:
        recent_failed_check_values = [
            (
                {
                    "check_type": "none",
                    "status": "PASS",
                },
                0,
            )
        ]

    _add_metric(
        lines=lines,
        name="jobskill_pipeline_recent_failed_checks_total",
        metric_type="gauge",
        help_text="Recent failed pipeline checks within the alert evaluation window.",
        values=recent_failed_check_values,
    )

    _add_metric(
        lines=lines,
        name="jobskill_alert_events_total",
        metric_type="gauge",
        help_text="Total alert events by alert name, severity, service and status.",
        values=[
            (
                {
                    "alert_name": row["alert_name"],
                    "severity": row["severity"],
                    "service": row["service"],
                    "status": row["status"],
                },
                int(row["count"]),
            )
            for row in alert_event_rows
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_alert_current_states_total",
        metric_type="gauge",
        help_text="Current alert states by alert name, severity, service and status.",
        values=[
            (
                {
                    "alert_name": row["alert_name"],
                    "severity": row["severity"],
                    "service": row["service"],
                    "status": row["status"],
                },
                int(row["count"]),
            )
            for row in alert_current_state_rows
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_alert_acknowledgements_total",
        metric_type="gauge",
        help_text="Alert acknowledgements by alert name, severity, service and status.",
        values=[
            (
                {
                    "alert_name": row["alert_name"],
                    "severity": row["severity"],
                    "service": row["service"],
                    "status": row["status"],
                },
                int(row["count"]),
            )
            for row in alert_acknowledgement_rows
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_alert_avg_mtta_minutes",
        metric_type="gauge",
        help_text=(
            "Average minutes from alert firing to first acknowledgement "
            "by alert name, severity and service."
        ),
        values=[
            (
                {
                    "alert_name": row["alert_name"],
                    "severity": row["severity"],
                    "service": row["service"],
                },
                float(row["avg_mtta_minutes"]),
            )
            for row in alert_response_metric_rows
            if row["avg_mtta_minutes"] is not None
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_alert_avg_mttr_minutes",
        metric_type="gauge",
        help_text=(
            "Average minutes from alert firing to first resolved event "
            "by alert name, severity and service."
        ),
        values=[
            (
                {
                    "alert_name": row["alert_name"],
                    "severity": row["severity"],
                    "service": row["service"],
                },
                float(row["avg_mttr_minutes"]),
            )
            for row in alert_response_metric_rows
            if row["avg_mttr_minutes"] is not None
        ],
    )

    _add_metric(
        lines=lines,
        name="jobskill_alert_unacknowledged_current_total",
        metric_type="gauge",
        help_text=(
            "Current firing alerts that do not have an acknowledgement record."
        ),
        values=[
            (
                {
                    "alert_name": row["alert_name"],
                    "severity": row["severity"],
                    "service": row["service"],
                },
                int(row["count"]),
            )
            for row in current_unacknowledged_alert_rows
        ],
    )

    if latest_model:
        _add_metric(
            lines=lines,
            name="jobskill_latest_promoted_model_accuracy",
            metric_type="gauge",
            help_text="Accuracy of latest promoted model.",
            values=[
                (
                    {"model_registry_id": latest_model["id"]},
                    _float_or_zero(latest_model["accuracy"]),
                )
            ],
        )

        _add_metric(
            lines=lines,
            name="jobskill_latest_promoted_model_f1_weighted",
            metric_type="gauge",
            help_text="Weighted F1 score of latest promoted model.",
            values=[
                (
                    {"model_registry_id": latest_model["id"]},
                    _float_or_zero(latest_model["f1_weighted"]),
                )
            ],
        )
    else:
        _add_metric(
            lines=lines,
            name="jobskill_latest_promoted_model_accuracy",
            metric_type="gauge",
            help_text="Accuracy of latest promoted model.",
            values=[(None, 0.0)],
        )

        _add_metric(
            lines=lines,
            name="jobskill_latest_promoted_model_f1_weighted",
            metric_type="gauge",
            help_text="Weighted F1 score of latest promoted model.",
            values=[(None, 0.0)],
        )

    return "\n".join(lines).strip() + "\n"
