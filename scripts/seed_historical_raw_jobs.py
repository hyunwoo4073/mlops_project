from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text


sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.common.db import get_engine


SEED_SOURCE = os.getenv("HISTORICAL_SEED_SOURCE", "remoteok_seed")
SEED_ROWS = int(os.getenv("HISTORICAL_SEED_ROWS", "5000"))
HISTORY_DAYS = int(os.getenv("HISTORICAL_SEED_HISTORY_DAYS", "240"))
RANDOM_SEED = int(os.getenv("HISTORICAL_SEED_RANDOM_SEED", "42"))

END_DATE_TEXT = os.getenv("HISTORICAL_SEED_END_DATE", "")

if END_DATE_TEXT:
    END_DATE = datetime.strptime(END_DATE_TEXT, "%Y-%m-%d")
else:
    END_DATE = datetime.now()


@dataclass(frozen=True)
class JobTemplate:
    category: str
    titles: list[str]
    companies: list[str]
    locations: list[str]
    skills: list[str]
    sentences: list[str]


TEMPLATES = [
    JobTemplate(
        category="Data Engineer",
        titles=[
            "Data Engineer",
            "데이터 엔지니어",
            "데이터 플랫폼 엔지니어",
            "ETL 파이프라인 엔지니어",
            "빅데이터 엔지니어",
        ],
        companies=[
            "A데이터랩",
            "B커머스",
            "C핀테크",
            "D모빌리티",
            "E클라우드",
        ],
        locations=[
            "Seoul",
            "Pangyo",
            "Remote",
            "Hybrid",
        ],
        skills=[
            "Python",
            "SQL",
            "Spark",
            "Airflow",
            "Kafka",
            "Hadoop",
            "Hive",
            "Trino",
            "Docker",
            "Kubernetes",
        ],
        sentences=[
            "대용량 데이터 파이프라인을 설계하고 운영합니다.",
            "Kafka 기반 이벤트 데이터를 처리합니다.",
            "Spark와 Airflow 기반 워크플로우를 최적화합니다.",
            "데이터 품질 검증과 장애 대응 체계를 개선합니다.",
        ],
    ),
    JobTemplate(
        category="Data Analyst",
        titles=[
            "Data Analyst",
            "데이터 분석가",
            "Product Analyst",
            "비즈니스 데이터 분석가",
            "서비스 데이터 분석가",
        ],
        companies=[
            "F플랫폼",
            "G리테일",
            "H게임즈",
            "I콘텐츠",
            "J마케팅",
        ],
        locations=[
            "Seoul",
            "Remote",
            "Busan",
            "Hybrid",
        ],
        skills=[
            "SQL",
            "Python",
            "Tableau",
            "Looker",
            "GA4",
            "Amplitude",
            "Statistics",
            "A/B Test",
        ],
        sentences=[
            "서비스 지표를 분석하고 대시보드를 구축합니다.",
            "A/B 테스트 결과를 해석합니다.",
            "고객 행동 데이터를 분석하여 인사이트를 도출합니다.",
            "비즈니스 KPI를 정의하고 리포트를 자동화합니다.",
        ],
    ),
    JobTemplate(
        category="Backend Engineer",
        titles=[
            "Backend Engineer",
            "백엔드 엔지니어",
            "서버 개발자",
            "Java Backend Engineer",
            "API 서버 개발자",
        ],
        companies=[
            "K페이",
            "L커머스",
            "M테크",
            "N헬스케어",
            "O물류",
        ],
        locations=[
            "Seoul",
            "Pangyo",
            "Remote",
            "Daejeon",
        ],
        skills=[
            "Java",
            "Spring",
            "REST API",
            "MySQL",
            "PostgreSQL",
            "Redis",
            "Kafka",
            "JPA",
            "Docker",
            "Kubernetes",
        ],
        sentences=[
            "대규모 트래픽을 처리하는 백엔드 API를 개발합니다.",
            "Spring 기반 서비스의 안정성을 개선합니다.",
            "Redis와 Kafka를 활용한 비동기 구조를 설계합니다.",
            "도메인 모델과 데이터베이스 스키마를 개선합니다.",
        ],
    ),
    JobTemplate(
        category="ML Engineer",
        titles=[
            "ML Engineer",
            "머신러닝 엔지니어",
            "AI Engineer",
            "MLOps Engineer",
            "추천 시스템 엔지니어",
        ],
        companies=[
            "P에이아이",
            "Q로보틱스",
            "R비전",
            "S모델링",
            "T리서치",
        ],
        locations=[
            "Seoul",
            "Remote",
            "Hybrid",
            "Pangyo",
        ],
        skills=[
            "Python",
            "PyTorch",
            "scikit-learn",
            "MLflow",
            "Docker",
            "Kubernetes",
            "Airflow",
            "FastAPI",
            "Feature Store",
        ],
        sentences=[
            "머신러닝 모델 학습과 배포 파이프라인을 구축합니다.",
            "MLflow를 활용하여 실험과 모델 버전을 관리합니다.",
            "모델 성능 모니터링과 재학습 기준을 설계합니다.",
            "API 기반 모델 서빙 시스템을 운영합니다.",
        ],
    ),
    JobTemplate(
        category="DevOps Engineer",
        titles=[
            "DevOps Engineer",
            "데브옵스 엔지니어",
            "Cloud Engineer",
            "인프라 엔지니어",
            "SRE",
        ],
        companies=[
            "U클라우드",
            "V인프라",
            "W테크옵스",
            "X플랫폼",
            "Y시스템즈",
        ],
        locations=[
            "Seoul",
            "Remote",
            "Hybrid",
            "Incheon",
        ],
        skills=[
            "Linux",
            "Docker",
            "Kubernetes",
            "Prometheus",
            "Grafana",
            "Terraform",
            "AWS",
            "GitHub Actions",
            "Helm",
            "Ansible",
        ],
        sentences=[
            "Kubernetes 기반 서비스 운영 환경을 구축합니다.",
            "Prometheus와 Grafana 기반 모니터링 체계를 개선합니다.",
            "CI/CD 파이프라인과 배포 자동화를 담당합니다.",
            "장애 대응과 인프라 안정성 개선 업무를 수행합니다.",
        ],
    ),
]


CAREERS = [
    "신입",
    "1년 이상",
    "2년 이상",
    "3년 이상",
    "4년 이상",
    "5년 이상",
    "7년 이상",
]


def build_crawled_at() -> datetime:
    recent_bias = random.random() < 0.30

    if recent_bias:
        days_back = random.randint(0, min(90, HISTORY_DAYS))
    else:
        days_back = random.randint(0, HISTORY_DAYS)

    seconds_back = random.randint(0, 86399)

    return END_DATE - timedelta(days=days_back, seconds=seconds_back)


def build_description(template: JobTemplate, selected_skills: list[str]) -> str:
    selected_sentences = random.sample(
        template.sentences,
        random.randint(2, min(4, len(template.sentences))),
    )

    return " ".join(
        [
            *selected_sentences,
            f"주요 기술 스택은 {', '.join(selected_skills)} 입니다.",
            f"이 공고는 {template.category} 직무에 해당합니다.",
        ]
    )


def build_job(index: int) -> dict[str, object]:
    template = TEMPLATES[index % len(TEMPLATES)]
    selected_skills = random.sample(
        template.skills,
        random.randint(4, min(7, len(template.skills))),
    )

    source_job_id = f"{SEED_SOURCE}-{index + 1:06d}"
    title = random.choice(template.titles)
    crawled_at = build_crawled_at()

    return {
        "source": SEED_SOURCE,
        "source_job_id": source_job_id,
        "external_id": source_job_id,
        "source_url": f"https://example.com/{SEED_SOURCE}/jobs/{source_job_id}",
        "title": title,
        "company": random.choice(template.companies),
        "location": random.choice(template.locations),
        "career": random.choice(CAREERS),
        "description": build_description(template, selected_skills),
        "tags": ",".join(selected_skills),
        "crawled_at": crawled_at,
    }


def insert_seed_jobs(jobs: list[dict[str, object]]) -> int:
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
            career,
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
            :career,
            :description,
            :tags,
            :crawled_at
        )
        ON CONFLICT (source, source_job_id)
        DO UPDATE SET
            title = EXCLUDED.title,
            company = EXCLUDED.company,
            location = EXCLUDED.location,
            career = EXCLUDED.career,
            description = EXCLUDED.description,
            tags = EXCLUDED.tags,
            external_id = EXCLUDED.external_id,
            source_url = EXCLUDED.source_url,
            crawled_at = EXCLUDED.crawled_at
        """
    )

    with engine.begin() as conn:
        conn.execute(insert_sql, jobs)

    return len(jobs)


def main() -> None:
    random.seed(RANDOM_SEED)

    print("[Historical Raw Job Seed]")
    print(f"source      : {SEED_SOURCE}")
    print(f"rows        : {SEED_ROWS}")
    print(f"history_days: {HISTORY_DAYS}")
    print(f"end_date    : {END_DATE.strftime('%Y-%m-%d')}")

    jobs = [build_job(index) for index in range(SEED_ROWS)]
    inserted_count = insert_seed_jobs(jobs)

    print(f"seeded_raw_jobs: {inserted_count}")

    print()
    print("[Sample Seed Job]")
    sample = jobs[0]
    print(f"source_job_id: {sample['source_job_id']}")
    print(f"title        : {sample['title']}")
    print(f"company      : {sample['company']}")
    print(f"career       : {sample['career']}")
    print(f"crawled_at   : {sample['crawled_at']}")
    print(f"tags         : {sample['tags']}")


if __name__ == "__main__":
    main()
