from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy import create_engine, text


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str


def get_database_url() -> str:
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "jobskill")
    db_user = os.getenv("DB_USER", "jobskill")
    db_password = os.getenv("DB_PASSWORD", "jobskill")

    return (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )


def fetch_one(conn, query: str, params: dict | None = None):
    return conn.execute(text(query), params or {}).scalar_one()


def main() -> None:
    min_training_rows = int(os.getenv("MIN_TRAINING_ROWS", "50"))
    min_category_count = int(os.getenv("MIN_CATEGORY_COUNT", "2"))
    max_unknown_ratio = float(os.getenv("MAX_UNKNOWN_RATIO", "0.5"))

    engine = create_engine(get_database_url())

    results: list[CheckResult] = []

    with engine.begin() as conn:
        raw_count = fetch_one(conn, "SELECT COUNT(*) FROM raw_job_posts")
        cleaned_count = fetch_one(conn, "SELECT COUNT(*) FROM cleaned_job_posts")
        skill_count = fetch_one(conn, "SELECT COUNT(*) FROM job_post_skills")

        empty_text_count = fetch_one(
            conn,
            """
            SELECT COUNT(*)
            FROM cleaned_job_posts
            WHERE text_for_model IS NULL
               OR LENGTH(TRIM(text_for_model)) = 0
            """,
        )

        empty_category_count = fetch_one(
            conn,
            """
            SELECT COUNT(*)
            FROM cleaned_job_posts
            WHERE job_category IS NULL
               OR LENGTH(TRIM(job_category)) = 0
            """,
        )

        category_count = fetch_one(
            conn,
            """
            SELECT COUNT(DISTINCT job_category)
            FROM cleaned_job_posts
            WHERE job_category IS NOT NULL
              AND LENGTH(TRIM(job_category)) > 0
            """,
        )

        unknown_count = fetch_one(
            conn,
            """
            SELECT COUNT(*)
            FROM cleaned_job_posts
            WHERE LOWER(job_category) = 'unknown'
            """,
        )

        duplicate_text_count = fetch_one(
            conn,
            """
            SELECT COUNT(*)
            FROM (
                SELECT text_for_model
                FROM cleaned_job_posts
                GROUP BY text_for_model
                HAVING COUNT(*) > 1
            ) t
            """,
        )

    unknown_ratio = unknown_count / cleaned_count if cleaned_count > 0 else 1.0

    results.append(
        CheckResult(
            name="raw_job_posts_count",
            passed=raw_count > 0,
            message=f"raw_job_posts count = {raw_count}",
        )
    )

    results.append(
        CheckResult(
            name="cleaned_job_posts_count",
            passed=cleaned_count >= min_training_rows,
            message=(
                f"cleaned_job_posts count = {cleaned_count}, "
                f"required >= {min_training_rows}"
            ),
        )
    )

    results.append(
        CheckResult(
            name="job_post_skills_count",
            passed=skill_count > 0,
            message=f"job_post_skills count = {skill_count}",
        )
    )

    results.append(
        CheckResult(
            name="text_for_model_not_empty",
            passed=empty_text_count == 0,
            message=f"empty text_for_model count = {empty_text_count}",
        )
    )

    results.append(
        CheckResult(
            name="job_category_not_empty",
            passed=empty_category_count == 0,
            message=f"empty job_category count = {empty_category_count}",
        )
    )

    results.append(
        CheckResult(
            name="category_diversity",
            passed=category_count >= min_category_count,
            message=(
                f"distinct category count = {category_count}, "
                f"required >= {min_category_count}"
            ),
        )
    )

    results.append(
        CheckResult(
            name="unknown_ratio",
            passed=unknown_ratio <= max_unknown_ratio,
            message=(
                f"unknown count = {unknown_count}, "
                f"unknown ratio = {unknown_ratio:.4f}, "
                f"allowed <= {max_unknown_ratio}"
            ),
        )
    )

    # 중복은 우선 경고성 지표로만 출력하고 실패 조건에는 넣지 않음.
    print("\n[Data Quality Summary]")
    print(f"raw_job_posts      : {raw_count}")
    print(f"cleaned_job_posts  : {cleaned_count}")
    print(f"job_post_skills    : {skill_count}")
    print(f"distinct categories: {category_count}")
    print(f"unknown ratio      : {unknown_ratio:.4f}")
    print(f"duplicate texts    : {duplicate_text_count}")

    failed_results = []

    print("\n[Check Results]")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} | {result.name} | {result.message}")

        if not result.passed:
            failed_results.append(result)

    if failed_results:
        print("\n[Failed Checks]")
        for result in failed_results:
            print(f"- {result.name}: {result.message}")

        raise SystemExit(1)

    print("\nAll data quality checks passed.")


if __name__ == "__main__":
    main()
