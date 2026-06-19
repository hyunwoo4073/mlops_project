import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text


sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine


CSV_PATH = "data/raw/sample_jobs.csv"


def main():
    engine = get_engine()

    df = pd.read_csv(CSV_PATH)

    required_columns = [
        "source",
        "source_job_id",
        "title",
        "company",
        "location",
        "career",
        "description",
    ]

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    insert_sql = text("""
        INSERT INTO raw_job_posts (
            source,
            source_job_id,
            title,
            company,
            location,
            career,
            description
        )
        VALUES (
            :source,
            :source_job_id,
            :title,
            :company,
            :location,
            :career,
            :description
        )
        ON CONFLICT (source, source_job_id)
        DO UPDATE SET
            title = EXCLUDED.title,
            company = EXCLUDED.company,
            location = EXCLUDED.location,
            career = EXCLUDED.career,
            description = EXCLUDED.description
    """)

    rows = df[required_columns].to_dict(orient="records")

    with engine.begin() as conn:
        conn.execute(insert_sql, rows)

    print(f"Loaded {len(rows)} rows into raw_job_posts")


if __name__ == "__main__":
    main()
