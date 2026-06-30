from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text


# project root를 PYTHONPATH에 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine
from src.preprocessing.label_jobs import get_label_scores, label_job

REMOTEOK_API_URL = os.getenv("REMOTEOK_API_URL", "https://remoteok.com/api")
CRAWL_LIMIT = int(os.getenv("REMOTEOK_CRAWL_LIMIT", "50"))
SCAN_LIMIT = int(os.getenv("REMOTEOK_SCAN_LIMIT", "200"))
FILTER_ENABLED = os.getenv("REMOTEOK_FILTER_ENABLED", "true").lower() == "true"
MIN_RELEVANCE_SCORE = int(os.getenv("REMOTEOK_MIN_RELEVANCE_SCORE", "2"))

SOURCE_NAME = "remoteok"

RELEVANT_KEYWORDS: dict[str, int] = {
    # 직무명
    "data engineer": 5,
    "backend": 5,
    "back-end": 5,
    "software engineer": 5,
    "developer": 4,
    "devops": 5,
    "sre": 5,
    "ml engineer": 5,
    "machine learning": 5,
    "data analyst": 5,
    "analytics": 4,

    # 데이터 / 백엔드 / ML / DevOps 기술
    "python": 3,
    "sql": 3,
    "spark": 4,
    "airflow": 4,
    "kafka": 4,
    "hadoop": 4,
    "etl": 4,
    "data pipeline": 4,
    "java": 3,
    "spring": 3,
    "api": 3,
    "fastapi": 3,
    "django": 3,
    "node": 3,
    "typescript": 3,
    "javascript": 2,
    "postgresql": 3,
    "mysql": 2,
    "redis": 2,
    "docker": 3,
    "kubernetes": 4,
    "k8s": 4,
    "terraform": 3,
    "ansible": 3,
    "prometheus": 3,
    "grafana": 3,
    "tensorflow": 4,
    "pytorch": 4,
    "mlflow": 4,
    "tableau": 3,
    "power bi": 3,
    "dashboard": 3,
}

EXCLUDE_KEYWORDS = {
    "warehouse",
    "counsel",
    "legal",
    "attorney",
    "nurse",
    "doctor",
    "sales representative",
    "customer support",
    "administrative assistant",
    "human resources",
    "recruiter",
    "accountant",
    "finance",
}

def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    text_value = text.lower()
    text_value = re.sub(r"\s+", " ", text_value)

    return text_value.strip()


def calculate_relevance_score(job: dict[str, Any]) -> int:
    search_text = normalize_text(
        " ".join(
            [
                str(job.get("title", "")),
                str(job.get("description", "")),
                str(job.get("tags", "")),
            ]
        )
    )

    if not search_text:
        return 0

    for exclude_keyword in EXCLUDE_KEYWORDS:
        if exclude_keyword in search_text:
            return 0

    score = 0

    for keyword, weight in RELEVANT_KEYWORDS.items():
        if keyword in search_text:
            score += weight

    return score


def infer_job_category(job: dict[str, Any]) -> str:
    title = str(job.get("title", ""))

    # Remote OK의 tags도 라벨링 힌트로 같이 사용한다.
    description = " ".join(
        [
            str(job.get("description", "")),
            str(job.get("tags", "")),
        ]
    )

    return label_job(title=title, description=description)


def is_relevant_job(job: dict[str, Any]) -> bool:
    if not FILTER_ENABLED:
        return True

    inferred_category = infer_job_category(job)

    if inferred_category == "Unknown":
        return False

    return True


def clean_html(raw_html: str | None) -> str:
    if not raw_html:
        return ""

    soup = BeautifulSoup(raw_html, "html.parser")
    text_value = soup.get_text(" ", strip=True)
    text_value = re.sub(r"\s+", " ", text_value)

    return text_value.strip()


def normalize_tags(tags: Any) -> str:
    if tags is None:
        return ""

    if isinstance(tags, list):
        return ",".join(str(tag).strip() for tag in tags if str(tag).strip())

    return str(tags)


def fetch_remoteok_jobs() -> list[dict[str, Any]]:
    headers = {
        "User-Agent": "jobskill-mlops-portfolio/1.0",
        "Accept": "application/json",
    }

    response = requests.get(
        REMOTEOK_API_URL,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload, list):
        raise ValueError("Unexpected Remote OK response format. Expected list.")

    jobs = []

    scanned_count = 0
    filtered_out_count = 0

    for item in payload:
        if not isinstance(item, dict):
            continue

        if scanned_count >= SCAN_LIMIT:
            break

        scanned_count += 1

        # Remote OK feed 첫 row가 metadata인 경우가 있어서 position/company 없는 row는 제외
        title = item.get("position") or item.get("title")
        company = item.get("company")
        description = item.get("description")

        if not title or not company:
            continue

        external_id = str(
            item.get("id")
            or item.get("slug")
            or item.get("url")
            or f"{company}-{title}"
        )

        source_url = (
            item.get("url")
            or item.get("apply_url")
            or item.get("job_url")
            or ""
        )

        location = item.get("location") or item.get("region") or "Remote"
        tags = normalize_tags(item.get("tags"))

        job = {
            "source": SOURCE_NAME,
            "source_job_id": external_id,
            "external_id": external_id,
            "source_url": source_url,
            "title": str(title).strip(),
            "company": str(company).strip(),
            "location": str(location).strip(),
            "description": clean_html(description),
            "tags": tags,
        }

        inferred_category = infer_job_category(job)
        job["inferred_category"] = inferred_category

        if not is_relevant_job(job):
            filtered_out_count += 1
            continue

        jobs.append(job)

        if len(jobs) >= CRAWL_LIMIT:
            break

    print(f"scanned_jobs     : {scanned_count}")
    print(f"filtered_out_jobs: {filtered_out_count}")

    return jobs


def insert_raw_jobs(jobs: list[dict[str, Any]]) -> int:
    if not jobs:
        return 0

    engine = get_engine()

    insert_sql = text(
        """
        INSERT INTO raw_job_posts (
            source,
            source_job_id,
            external_id,
            source_url,
            title,
            company,
            location,
            description,
            tags,
            crawled_at
        )
        VALUES (
            :source,
            :source_job_id,
            :external_id,
            :source_url,
            :title,
            :company,
            :location,
            :description,
            :tags,
            :crawled_at
        )
        ON CONFLICT (source, source_job_id)
        DO UPDATE SET
            title = EXCLUDED.title,
            company = EXCLUDED.company,
            location = EXCLUDED.location,
            description = EXCLUDED.description,
            tags = EXCLUDED.tags,
            external_id = EXCLUDED.external_id,
            source_url = EXCLUDED.source_url,
            crawled_at = EXCLUDED.crawled_at
        """
    )

    now = datetime.now()

    payload = []
    for job in jobs:
        payload.append(
        {
            "source": job["source"],
            "source_job_id": job["source_job_id"],
            "external_id": job["external_id"],
            "source_url": job["source_url"],
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "description": job["description"],
            "tags": job["tags"],
            "crawled_at": now,
        }
    )

    with engine.begin() as conn:
        conn.execute(insert_sql, payload)

    return len(payload)


def main() -> None:
    print("\n[Remote OK Crawler]")
    print(f"api_url    : {REMOTEOK_API_URL}")
    print(f"crawl_limit: {CRAWL_LIMIT}")

    jobs = fetch_remoteok_jobs()

    print(f"fetched_jobs: {len(jobs)}")

    inserted_count = insert_raw_jobs(jobs)

    print(f"upserted_raw_jobs: {inserted_count}")

    if jobs:
        print("\n[Sample Crawled Job]")
        print(f"title             : {jobs[0]['title']}")
        print(f"company           : {jobs[0]['company']}")
        print(f"location          : {jobs[0]['location']}")
        print(f"inferred_category : {jobs[0].get('inferred_category')}")
        print(f"source_url        : {jobs[0]['source_url']}")


if __name__ == "__main__":
    main()
