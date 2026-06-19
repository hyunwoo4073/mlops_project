DROP TABLE IF EXISTS model_predictions;
DROP TABLE IF EXISTS job_post_skills;
DROP TABLE IF EXISTS cleaned_job_posts;
DROP TABLE IF EXISTS raw_job_posts;

CREATE TABLE raw_job_posts (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_job_id VARCHAR(100) NOT NULL,
    title TEXT,
    company TEXT,
    location TEXT,
    career TEXT,
    description TEXT,
    crawled_at TIMESTAMP DEFAULT now(),
    UNIQUE (source, source_job_id)
);

CREATE TABLE cleaned_job_posts (
    id BIGSERIAL PRIMARY KEY,
    raw_id BIGINT REFERENCES raw_job_posts(id),
    title TEXT,
    company TEXT,
    location TEXT,
    career TEXT,
    description TEXT,
    cleaned_title TEXT,
    cleaned_description TEXT,
    text_for_model TEXT,
    job_category VARCHAR(50),
    cleaned_at TIMESTAMP DEFAULT now()
);

CREATE TABLE job_post_skills (
    id BIGSERIAL PRIMARY KEY,
    job_post_id BIGINT REFERENCES cleaned_job_posts(id),
    skill_name VARCHAR(100)
);

CREATE TABLE model_predictions (
    id BIGSERIAL PRIMARY KEY,
    job_post_id BIGINT REFERENCES cleaned_job_posts(id),
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    predicted_category VARCHAR(50),
    confidence FLOAT,
    predicted_at TIMESTAMP DEFAULT now()
);
