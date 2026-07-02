from __future__ import annotations

import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests import RequestException
from sqlalchemy import text


# project root를 PYTHONPATH에 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.db import get_engine
from src.preprocessing.label_jobs import label_job


REMOTEOK_API_URL = os.getenv("REMOTEOK_API_URL", "https://remoteok.com/api")

CRAWL_LIMIT = int(os.getenv("REMOTEOK_CRAWL_LIMIT", "50"))
SCAN_LIMIT = int(os.getenv("REMOTEOK_SCAN_LIMIT", "1000"))
FILTER_ENABLED = os.getenv("REMOTEOK_FILTER_ENABLED", "true").lower() == "true"

MAX_RETRIES = int(os.getenv("REMOTEOK_MAX_RETRIES", "3"))
RETRY_SLEEP_SECONDS = int(os.getenv("REMOTEOK_RETRY_SLEEP_SECONDS", "3"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REMOTEOK_REQUEST_TIMEOUT_SECONDS", "30"))

FALLBACK_TO_EXISTING_RAW = (
    os.getenv("REMOTEOK_FALLBACK_TO_EXISTING_RAW", "true").lower() == "true"
)

MIN_FETCHED_JOBS = int(os.getenv("REMOTEOK_MIN_FETCHED_JOBS", "1"))

SOURCE_NAME = "remoteok"


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


def infer_job_category(job: dict[str, Any]) -> str:
    title = str(job.get("title", ""))

    # Remote OK는 tags에 직무/기술 힌트가 많이 들어있으므로 description과 같이 사용한다.
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

    return inferred_category != "Unknown"


def request_remoteok_payload() -> list[dict[str, Any]]:
    headers = {
        "User-Agent": "jobskill-mlops-portfolio/1.0",
        "Accept": "application/json",
    }

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"request_attempt: {attempt}/{MAX_RETRIES}")

            response = requests.get(
                REMOTEOK_API_URL,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()

            payload = response.json()

            if not isinstance(payload, list):
                raise ValueError("Unexpected Remote OK response format. Expected list.")

            return payload

        except (RequestException, ValueError) as exc:
            last_error = exc
            print(f"request_failed : {type(exc).__name__}: {exc}")

            if attempt < MAX_RETRIES:
                print(f"retry_after_seconds: {RETRY_SLEEP_SECONDS}")
                time.sleep(RETRY_SLEEP_SECONDS)

    raise RuntimeError(
        f"Failed to fetch Remote OK jobs after {MAX_RETRIES} attempts."
    ) from last_error


def fetch_remoteok_jobs() -> list[dict[str, Any]]:
    payload = request_remoteok_payload()

    jobs = []
    scanned_count = 0
    filtered_out_count = 0
    invalid_count = 0

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
            invalid_count += 1
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
    print(f"invalid_jobs     : {invalid_count}")
    print(f"filtered_out_jobs: {filtered_out_count}")
    print(f"selected_jobs    : {len(jobs)}")

    return jobs


def count_existing_remoteok_rows() -> int:
    engine = get_engine()

    with engine.begin() as conn:
        count = conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM raw_job_posts
                WHERE source = :source
                """
            ),
            {"source": SOURCE_NAME},
        ).scalar_one()

    return int(count)


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


def fallback_to_existing_raw(reason: str) -> bool:
    if not FALLBACK_TO_EXISTING_RAW:
        return False

    existing_count = count_existing_remoteok_rows()

    if existing_count <= 0:
        print("fallback_available: false")
        print("existing_remoteok_rows: 0")
        return False

    print("\n[Remote OK Fallback]")
    print(f"reason                : {reason}")
    print("fallback_available    : true")
    print(f"existing_remoteok_rows: {existing_count}")
    print("action                : keep existing raw_job_posts rows and continue")

    return True


def main() -> None:
    print("\n[Remote OK Crawler]")
    print(f"api_url       : {REMOTEOK_API_URL}")
    print(f"crawl_limit   : {CRAWL_LIMIT}")
    print(f"scan_limit    : {SCAN_LIMIT}")
    print(f"filter        : {FILTER_ENABLED}")
    print(f"max_retries   : {MAX_RETRIES}")
    print(f"retry_sleep   : {RETRY_SLEEP_SECONDS}")
    print(f"timeout       : {REQUEST_TIMEOUT_SECONDS}")
    print(f"fallback      : {FALLBACK_TO_EXISTING_RAW}")
    print(f"min_fetched   : {MIN_FETCHED_JOBS}")

    try:
        jobs = fetch_remoteok_jobs()

    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"

        if fallback_to_existing_raw(reason=reason):
            return

        raise

    if len(jobs) < MIN_FETCHED_JOBS:
        reason = (
            f"Fetched jobs below minimum. "
            f"selected_jobs={len(jobs)}, required={MIN_FETCHED_JOBS}"
        )

        if fallback_to_existing_raw(reason=reason):
            return

        raise ValueError(reason)

    print(f"fetched_jobs: {len(jobs)}")

    upserted_count = insert_raw_jobs(jobs)

    print(f"upserted_raw_jobs: {upserted_count}")

    if jobs:
        print("\n[Sample Crawled Job]")
        print(f"title             : {jobs[0]['title']}")
        print(f"company           : {jobs[0]['company']}")
        print(f"location          : {jobs[0]['location']}")
        print(f"inferred_category : {jobs[0].get('inferred_category')}")
        print(f"source_url        : {jobs[0]['source_url']}")


if __name__ == "__main__":
    main()