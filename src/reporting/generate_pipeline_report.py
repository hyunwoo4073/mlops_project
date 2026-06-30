from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text


# project root를 PYTHONPATH에 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine


REPORT_PATH = Path("reports/latest_pipeline_report.md")


REPORT_QUERIES = {
    "Latest Promoted Model": """
        SELECT
            id,
            model_name,
            run_id,
            ROUND(accuracy::numeric, 4) AS accuracy,
            ROUND(f1_weighted::numeric, 4) AS f1_weighted,
            status,
            promoted_model_path,
            created_at
        FROM model_registry
        WHERE status = 'PROMOTED'
        ORDER BY created_at DESC, id DESC
        LIMIT 1
    """,
    "Model Registry History": """
        SELECT
            id,
            model_name,
            LEFT(run_id, 12) AS run_id_short,
            ROUND(accuracy::numeric, 4) AS accuracy,
            ROUND(f1_weighted::numeric, 4) AS f1_weighted,
            status,
            message,
            created_at
        FROM model_registry
        ORDER BY id DESC
        LIMIT 20
    """,
    "Prediction Lineage Summary": """
        SELECT
            mp.model_name,
            LEFT(mp.model_run_id, 12) AS model_run_id_short,
            mp.model_registry_id,
            mr.status AS registry_status,
            ROUND(mr.accuracy::numeric, 4) AS registry_accuracy,
            ROUND(mr.f1_weighted::numeric, 4) AS registry_f1_weighted,
            COUNT(*) AS prediction_count,
            ROUND(AVG(mp.confidence)::numeric, 4) AS avg_confidence,
            MIN(mp.predicted_at) AS first_predicted_at,
            MAX(mp.predicted_at) AS last_predicted_at
        FROM model_predictions mp
        LEFT JOIN model_registry mr
            ON mp.model_registry_id = mr.id
        GROUP BY
            mp.model_name,
            mp.model_run_id,
            mp.model_registry_id,
            mr.status,
            mr.accuracy,
            mr.f1_weighted
        ORDER BY prediction_count DESC
    """,
    "Latest Predictions": """
        SELECT
            mp.id,
            mp.job_post_id,
            mp.predicted_category,
            ROUND(mp.confidence::numeric, 4) AS confidence,
            mp.model_name,
            LEFT(mp.model_run_id, 12) AS model_run_id_short,
            mp.model_registry_id,
            mr.status AS registry_status,
            ROUND(mr.f1_weighted::numeric, 4) AS registry_f1_weighted,
            mp.predicted_at
        FROM model_predictions mp
        LEFT JOIN model_registry mr
            ON mp.model_registry_id = mr.id
        ORDER BY mp.id DESC
        LIMIT 20
    """,
    "Prediction Category Distribution": """
        SELECT
            mp.model_name,
            LEFT(mp.model_run_id, 12) AS model_run_id_short,
            mp.model_registry_id,
            mp.predicted_category,
            COUNT(*) AS prediction_count,
            ROUND(AVG(mp.confidence)::numeric, 4) AS avg_confidence
        FROM model_predictions mp
        GROUP BY
            mp.model_name,
            mp.model_run_id,
            mp.model_registry_id,
            mp.predicted_category
        ORDER BY
            mp.model_registry_id DESC,
            prediction_count DESC
    """,
    "Check Result Summary": """
        SELECT
            check_type,
            status,
            COUNT(*) AS check_count,
            MAX(checked_at) AS latest_checked_at
        FROM pipeline_check_results
        GROUP BY check_type, status
        ORDER BY check_type, status
    """,
    "Latest Check Details": """
        SELECT
            check_type,
            check_name,
            status,
            ROUND(metric_value::numeric, 4) AS metric_value,
            ROUND(threshold_value::numeric, 4) AS threshold_value,
            message,
            task_id,
            checked_at
        FROM pipeline_check_results
        ORDER BY id DESC
        LIMIT 30
    """,
    "Failed Checks": """
        SELECT
            check_type,
            check_name,
            status,
            ROUND(metric_value::numeric, 4) AS metric_value,
            ROUND(threshold_value::numeric, 4) AS threshold_value,
            message,
            task_id,
            checked_at
        FROM pipeline_check_results
        WHERE status = 'FAIL'
        ORDER BY id DESC
        LIMIT 30
    """,
    "Model Promotion Summary": """
        SELECT
            status,
            COUNT(*) AS count,
            ROUND(AVG(accuracy)::numeric, 4) AS avg_accuracy,
            ROUND(AVG(f1_weighted)::numeric, 4) AS avg_f1_weighted,
            MAX(created_at) AS latest_created_at
        FROM model_registry
        GROUP BY status
        ORDER BY status
    """,
    "Raw Job Count by Source": """
        SELECT
            COALESCE(source, 'unknown') AS source,
            COUNT(*) AS raw_count,
            MIN(crawled_at) AS first_crawled_at,
            MAX(crawled_at) AS latest_crawled_at
        FROM raw_job_posts
        GROUP BY COALESCE(source, 'unknown')
        ORDER BY raw_count DESC;
    """,
    "Cleaned Job Quality by Source": """
        SELECT
            COALESCE(r.source, 'unknown') AS source,
            COUNT(*) AS cleaned_count,
            COUNT(*) FILTER (WHERE c.job_category = 'Unknown') AS unknown_count,
            ROUND(
                COUNT(*) FILTER (WHERE c.job_category = 'Unknown')::numeric
                / NULLIF(COUNT(*), 0),
                4
            ) AS unknown_ratio,
            COUNT(DISTINCT c.job_category) AS category_count
        FROM cleaned_job_posts c
        JOIN raw_job_posts r
            ON c.raw_id = r.id
        GROUP BY COALESCE(r.source, 'unknown')
        ORDER BY cleaned_count DESC
    """,
    "Job Category Distribution by Source": """
        SELECT
            COALESCE(r.source, 'unknown') AS source,
            c.job_category,
            COUNT(*) AS count,
            ROUND(
                COUNT(*)::numeric
                / SUM(COUNT(*)) OVER (PARTITION BY COALESCE(r.source, 'unknown')),
                4
            ) AS source_ratio
        FROM cleaned_job_posts c
        JOIN raw_job_posts r
            ON c.raw_id = r.id
        GROUP BY
            COALESCE(r.source, 'unknown'),
            c.job_category
        ORDER BY
            source,
            count DESC
    """,
    "Skill Extraction Summary by Source": """
        SELECT
            COALESCE(r.source, 'unknown') AS source,
            COUNT(DISTINCT c.id) AS cleaned_count,
            COUNT(s.id) AS extracted_skill_count,
            ROUND(
                COUNT(s.id)::numeric
                / NULLIF(COUNT(DISTINCT c.id), 0),
                4
            ) AS avg_skills_per_job
        FROM cleaned_job_posts c
        JOIN raw_job_posts r
            ON c.raw_id = r.id
        LEFT JOIN job_post_skills s
            ON c.id = s.job_post_id
        GROUP BY COALESCE(r.source, 'unknown')
        ORDER BY source
    """,
    "Top Skills by Source": """
        SELECT
            COALESCE(r.source, 'unknown') AS source,
            s.skill_name,
            COUNT(*) AS count
        FROM job_post_skills s
        JOIN cleaned_job_posts c
            ON s.job_post_id = c.id
        JOIN raw_job_posts r
            ON c.raw_id = r.id
        GROUP BY
            COALESCE(r.source, 'unknown'),
            s.skill_name
        ORDER BY
            source,
            count DESC
        LIMIT 50
    """,
    "Prediction Summary by Source": """
        SELECT
            COALESCE(r.source, 'unknown') AS source,
            mp.predicted_category,
            COUNT(*) AS prediction_count,
            ROUND(AVG(mp.confidence)::numeric, 4) AS avg_confidence,
            COUNT(*) FILTER (WHERE mp.is_low_confidence = true) AS low_confidence_count,
            ROUND(
                COUNT(*) FILTER (WHERE mp.is_low_confidence = true)::numeric
                / NULLIF(COUNT(*), 0),
                4
            ) AS low_confidence_ratio
        FROM model_predictions mp
        JOIN cleaned_job_posts c
            ON mp.job_post_id = c.id
        JOIN raw_job_posts r
            ON c.raw_id = r.id
        GROUP BY
            COALESCE(r.source, 'unknown'),
            mp.predicted_category
        ORDER BY
            source,
            prediction_count DESC
    """,
}


def format_value(value) -> str:
    if pd.isna(value):
        return ""

    text_value = str(value)

    # 마크다운 테이블 깨짐 방지
    return text_value.replace("|", "\\|").replace("\n", " ")


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"

    columns = list(df.columns)

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"

    rows = []
    for _, row in df.iterrows():
        row_values = [format_value(row[col]) for col in columns]
        rows.append("| " + " | ".join(row_values) + " |")

    return "\n".join([header, separator, *rows])


def run_query(engine, query: str) -> pd.DataFrame:
    with engine.begin() as conn:
        return pd.read_sql(text(query), conn)


def main() -> None:
    engine = get_engine()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sections = [
        "# JobSkill MLOps Pipeline Report",
        "",
        f"- Generated at: `{generated_at}`",
        "",
        "This report summarizes model registry, prediction lineage, and pipeline check results.",
        "",
    ]

    for title, query in REPORT_QUERIES.items():
        print(f"Generating section: {title}")

        try:
            df = run_query(engine, query)
            markdown_table = dataframe_to_markdown(df)
        except Exception as exc:
            markdown_table = f"_Failed to generate section: {exc}_"

        sections.extend(
            [
                f"## {title}",
                "",
                markdown_table,
                "",
            ]
        )

    REPORT_PATH.write_text("\n".join(sections), encoding="utf-8")

    print(f"\nReport generated: {REPORT_PATH}")


if __name__ == "__main__":
    main()
