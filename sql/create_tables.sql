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

CREATE TABLE IF NOT EXISTS pipeline_check_results (
    id BIGSERIAL PRIMARY KEY,

    check_type VARCHAR(50) NOT NULL,
    check_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,

    metric_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    message TEXT,

    dag_id VARCHAR(250),
    task_id VARCHAR(250),
    run_id VARCHAR(250),

    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pipeline_check_results_type
ON pipeline_check_results(check_type);

CREATE INDEX IF NOT EXISTS idx_pipeline_check_results_status
ON pipeline_check_results(status);

CREATE INDEX IF NOT EXISTS idx_pipeline_check_results_run_id
ON pipeline_check_results(run_id);

CREATE TABLE IF NOT EXISTS model_registry (
    id BIGSERIAL PRIMARY KEY,

    model_name VARCHAR(100) NOT NULL,
    run_id VARCHAR(250),
    experiment_name VARCHAR(250),

    accuracy DOUBLE PRECISION,
    f1_weighted DOUBLE PRECISION,

    model_path TEXT,
    promoted_model_path TEXT,

    status VARCHAR(30) NOT NULL,
    message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_model_registry_model_name
ON model_registry(model_name);

CREATE INDEX IF NOT EXISTS idx_model_registry_status
ON model_registry(status);

CREATE INDEX IF NOT EXISTS idx_model_registry_created_at
ON model_registry(created_at);

ALTER TABLE model_predictions
ADD COLUMN IF NOT EXISTS model_name VARCHAR(100);

ALTER TABLE model_predictions
ADD COLUMN IF NOT EXISTS model_run_id VARCHAR(250);

ALTER TABLE model_predictions
ADD COLUMN IF NOT EXISTS model_registry_id BIGINT;

ALTER TABLE model_predictions
ADD COLUMN IF NOT EXISTS model_path TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_model_predictions_model_registry'
    ) THEN
        ALTER TABLE model_predictions
        ADD CONSTRAINT fk_model_predictions_model_registry
        FOREIGN KEY (model_registry_id)
        REFERENCES model_registry(id);
    END IF;
END $$;

ALTER TABLE model_predictions
ADD COLUMN IF NOT EXISTS confidence_level VARCHAR(20);

ALTER TABLE model_predictions
ADD COLUMN IF NOT EXISTS is_low_confidence BOOLEAN DEFAULT FALSE;

ALTER TABLE model_predictions
ADD COLUMN IF NOT EXISTS top_predictions JSONB;

ALTER TABLE raw_job_posts
ADD COLUMN IF NOT EXISTS external_id VARCHAR(250);

ALTER TABLE raw_job_posts
ADD COLUMN IF NOT EXISTS source VARCHAR(100);

ALTER TABLE raw_job_posts
ADD COLUMN IF NOT EXISTS source_url TEXT;

ALTER TABLE raw_job_posts
ADD COLUMN IF NOT EXISTS tags TEXT;

ALTER TABLE raw_job_posts
ADD COLUMN IF NOT EXISTS crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS uq_raw_job_posts_source_external_id
ON raw_job_posts(source, external_id)
WHERE source IS NOT NULL
  AND external_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_raw_job_posts_source_source_job_id
ON raw_job_posts(source, source_job_id);

CREATE TABLE IF NOT EXISTS api_prediction_logs (
    id BIGSERIAL PRIMARY KEY,

    prediction_id BIGINT,
    request_title TEXT,
    request_description TEXT,
    request_job_post_id BIGINT,

    response_category VARCHAR(100),
    response_confidence DOUBLE PRECISION,
    response_confidence_level VARCHAR(20),
    response_is_low_confidence BOOLEAN,
    response_top_predictions JSONB,
    response_skills JSONB,

    model_name VARCHAR(100),
    model_run_id VARCHAR(250),
    model_registry_id BIGINT,
    model_path TEXT,

    status VARCHAR(30) NOT NULL,
    error_message TEXT,
    latency_ms DOUBLE PRECISION,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_api_prediction_logs_prediction
        FOREIGN KEY (prediction_id)
        REFERENCES model_predictions(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_api_prediction_logs_prediction_id
ON api_prediction_logs(prediction_id);

CREATE INDEX IF NOT EXISTS idx_api_prediction_logs_status
ON api_prediction_logs(status);

CREATE INDEX IF NOT EXISTS idx_api_prediction_logs_created_at
ON api_prediction_logs(created_at);

CREATE INDEX IF NOT EXISTS idx_api_prediction_logs_model_registry_id
ON api_prediction_logs(model_registry_id);

ALTER TABLE model_predictions
ADD COLUMN IF NOT EXISTS prediction_source VARCHAR(30) DEFAULT 'BATCH';

UPDATE model_predictions
SET prediction_source = 'BATCH'
WHERE prediction_source IS NULL;

CREATE INDEX IF NOT EXISTS idx_model_predictions_prediction_source
ON model_predictions(prediction_source);