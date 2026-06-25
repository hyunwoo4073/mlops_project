import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text


sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine
from src.preprocessing.clean_text import clean_text
from src.preprocessing.extract_skills import extract_skills
from src.preprocessing.label_jobs import label_job


def main():
    engine = get_engine()

    raw_query = """
        SELECT
            id AS raw_id,
            source,
            source_job_id,
            title,
            company,
            location,
            career,
            description
        FROM raw_job_posts
        ORDER BY id
    """

    df = pd.read_sql(raw_query, engine)

    if df.empty:
        raise ValueError("raw_job_posts is empty. Run load_raw_jobs.py first.")

    df["cleaned_title"] = df["title"].apply(clean_text)
    df["cleaned_description"] = df["description"].apply(clean_text)
    df["text_for_model"] = df["cleaned_title"] + " " + df["cleaned_description"]
    df["job_category"] = df["title"].apply(label_job)
    df["skills"] = df["text_for_model"].apply(extract_skills)

    cleaned_rows = df[
        [
            "raw_id",
            "title",
            "company",
            "location",
            "career",
            "description",
            "cleaned_title",
            "cleaned_description",
            "text_for_model",
            "job_category",
        ]
    ].to_dict(orient="records")

    insert_cleaned_sql = text("""
        INSERT INTO cleaned_job_posts (
            raw_id,
            title,
            company,
            location,
            career,
            description,
            cleaned_title,
            cleaned_description,
            text_for_model,
            job_category
        )
        VALUES (
            :raw_id,
            :title,
            :company,
            :location,
            :career,
            :description,
            :cleaned_title,
            :cleaned_description,
            :text_for_model,
            :job_category
        )
        RETURNING id
    """)

    insert_skill_sql = text("""
        INSERT INTO job_post_skills (
            job_post_id,
            skill_name
        )
        VALUES (
            :job_post_id,
            :skill_name
        )
    """)

    with engine.begin() as conn:
        # MVP 단계에서는 전처리 결과를 매번 새로 만든다.
        conn.execute(text("""
            TRUNCATE TABLE
                model_predictions,
                job_post_skills,
                cleaned_job_posts
            RESTART IDENTITY
            CASCADE
        """))

        id_map = {}

        # bulk insert + RETURNING이 꼬일 수 있어서 한 건씩 insert
        for row in cleaned_rows:
            result = conn.execute(insert_cleaned_sql, row)
            inserted_id = result.scalar_one()
            id_map[row["raw_id"]] = inserted_id

        skill_rows = []

        for _, row in df.iterrows():
            job_post_id = id_map[row["raw_id"]]

            for skill in row["skills"]:
                skill_rows.append({
                    "job_post_id": job_post_id,
                    "skill_name": skill,
                })

        if skill_rows:
            conn.execute(insert_skill_sql, skill_rows)

    print(f"Inserted cleaned rows: {len(cleaned_rows)}")
    print(f"Inserted skill rows: {len(skill_rows)}")
    print()
    print(df["job_category"].value_counts())


if __name__ == "__main__":
    main()