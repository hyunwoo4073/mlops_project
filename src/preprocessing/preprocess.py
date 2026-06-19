import os
import pandas as pd

from clean_text import clean_text
from extract_skills import extract_skills
from label_jobs import label_job


RAW_PATH = "data/raw/sample_jobs.csv"
PROCESSED_PATH = "data/processed/cleaned_jobs.csv"


def main():
    if not os.path.exists(RAW_PATH):
        raise FileNotFoundError(f"Raw file not found: {RAW_PATH}")

    df = pd.read_csv(RAW_PATH)

    df["cleaned_title"] = df["title"].apply(clean_text)
    df["cleaned_description"] = df["description"].apply(clean_text)
    df["job_category"] = df["title"].apply(label_job)

    df["text_for_model"] = df["cleaned_title"] + " " + df["cleaned_description"]
    df["skills"] = df["text_for_model"].apply(lambda x: ",".join(extract_skills(x)))

    df = df.drop_duplicates(subset=["source", "source_job_id"])

    os.makedirs("data/processed", exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False, encoding="utf-8-sig")

    print(f"Saved processed data: {PROCESSED_PATH}")
    print(df[["title", "job_category", "skills"]])


if __name__ == "__main__":
    main()
