from __future__ import annotations

import os
from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

PROJECT_ROOT = "/opt/airflow/project"
LOCAL_TZ = "Asia/Seoul"


def get_feedback_ops_schedule() -> str | None:
    raw_schedule = os.getenv("FEEDBACK_OPS_DAG_SCHEDULE", "0 9 * * *").strip()

    if raw_schedule.lower() in {"", "none", "null", "manual", "off"}:
        return None

    return raw_schedule


def get_env_value(name: str, default: str) -> str:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return value.strip()


common_task_env = {
    "PYTHONPATH": PROJECT_ROOT,
}

production_feedback_env = {
    **common_task_env,
    "PRODUCTION_FEEDBACK_STRICT": get_env_value(
        "PRODUCTION_FEEDBACK_STRICT",
        "false",
    ),
    "MIN_PRODUCTION_FEEDBACK_ROWS": get_env_value(
        "MIN_PRODUCTION_FEEDBACK_ROWS",
        "10",
    ),
    "MIN_PRODUCTION_ACCURACY": get_env_value(
        "MIN_PRODUCTION_ACCURACY",
        "0.70",
    ),
    "MIN_PRODUCTION_F1_WEIGHTED": get_env_value(
        "MIN_PRODUCTION_F1_WEIGHTED",
        "0.70",
    ),
    "PRODUCTION_FEEDBACK_WINDOW_DAYS": get_env_value(
        "PRODUCTION_FEEDBACK_WINDOW_DAYS",
        "30",
    ),
}

retraining_candidate_env = {
    **common_task_env,
    "RETRAINING_CANDIDATE_STRICT": get_env_value(
        "RETRAINING_CANDIDATE_STRICT",
        "false",
    ),
    "MIN_PRODUCTION_FEEDBACK_ROWS": get_env_value(
        "MIN_PRODUCTION_FEEDBACK_ROWS",
        "10",
    ),
    "MIN_PRODUCTION_ACCURACY": get_env_value(
        "MIN_PRODUCTION_ACCURACY",
        "0.70",
    ),
    "MIN_PRODUCTION_F1_WEIGHTED": get_env_value(
        "MIN_PRODUCTION_F1_WEIGHTED",
        "0.70",
    ),
    "PRODUCTION_FEEDBACK_TREND_DROP_THRESHOLD": get_env_value(
        "PRODUCTION_FEEDBACK_TREND_DROP_THRESHOLD",
        "0.05",
    ),
    "PRODUCTION_FEEDBACK_MIN_HISTORY_POINTS": get_env_value(
        "PRODUCTION_FEEDBACK_MIN_HISTORY_POINTS",
        "3",
    ),
}

with DAG(
    dag_id="jobskill_feedback_ops",
    description=(
        "Evaluate production feedback quality and persist retraining candidate "
        "decisions for operational monitoring."
    ),
    start_date=pendulum.datetime(2026, 1, 1, tz=LOCAL_TZ),
    schedule=get_feedback_ops_schedule(),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=20),
    default_args={
        "owner": "bae",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["jobskill", "production-feedback", "retraining", "ops"],
) as dag:
    show_feedback_ops_config = BashOperator(
        task_id="show_feedback_ops_config",
        bash_command="""
        echo "Feedback Ops DAG Configuration"
        echo "================================"
        echo "FEEDBACK_OPS_DAG_SCHEDULE=${FEEDBACK_OPS_DAG_SCHEDULE:-0 9 * * *}"
        echo "PRODUCTION_FEEDBACK_STRICT=${PRODUCTION_FEEDBACK_STRICT:-false}"
        echo "RETRAINING_CANDIDATE_STRICT=${RETRAINING_CANDIDATE_STRICT:-false}"
        echo "MIN_PRODUCTION_FEEDBACK_ROWS=${MIN_PRODUCTION_FEEDBACK_ROWS:-10}"
        echo "MIN_PRODUCTION_ACCURACY=${MIN_PRODUCTION_ACCURACY:-0.70}"
        echo "MIN_PRODUCTION_F1_WEIGHTED=${MIN_PRODUCTION_F1_WEIGHTED:-0.70}"
        echo "PRODUCTION_FEEDBACK_WINDOW_DAYS=${PRODUCTION_FEEDBACK_WINDOW_DAYS:-30}"
        echo "PRODUCTION_FEEDBACK_TREND_DROP_THRESHOLD=${PRODUCTION_FEEDBACK_TREND_DROP_THRESHOLD:-0.05}"
        echo "PRODUCTION_FEEDBACK_MIN_HISTORY_POINTS=${PRODUCTION_FEEDBACK_MIN_HISTORY_POINTS:-3}"
        """.strip(),
        append_env=True,
    )

    check_production_feedback = BashOperator(
        task_id="check_production_feedback",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            "python src/quality/check_production_feedback.py"
        ),
        env=production_feedback_env,
        append_env=True,
    )

    check_retraining_candidate = BashOperator(
        task_id="check_retraining_candidate",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            "python src/quality/check_retraining_candidate.py"
        ),
        env=retraining_candidate_env,
        append_env=True,
    )

    show_feedback_ops_config >> check_production_feedback >> check_retraining_candidate
