def label_job(title: str) -> str:
    if title is None:
        return "Unknown"

    title_text = str(title)
    title_lower = title_text.lower()

    if (
        "데이터 엔지니어" in title_text
        or "data engineer" in title_lower
        or "데이터 플랫폼" in title_text
    ):
        return "Data Engineer"

    if (
        "백엔드" in title_text
        or "backend" in title_lower
        or "서버 개발자" in title_text
    ):
        return "Backend Engineer"

    if (
        "ml engineer" in title_lower
        or "machine learning" in title_lower
        or "머신러닝" in title_text
        or "ai 엔지니어" in title_lower
        or "AI 엔지니어" in title_text
    ):
        return "ML Engineer"

    if (
        "devops" in title_lower
        or "sre" in title_lower
        or "인프라" in title_text
    ):
        return "DevOps Engineer"

    if (
        "데이터 분석" in title_text
        or "data analyst" in title_lower
        or "분석가" in title_text
        or "분석 담당자" in title_text
    ):
        return "Data Analyst"

    return "Unknown"
