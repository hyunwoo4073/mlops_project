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

CREATE TABLE IF NOT EXISTS alert_events (
    id BIGSERIAL PRIMARY KEY,

    receiver VARCHAR(100),
    status VARCHAR(30) NOT NULL,

    alert_name VARCHAR(200),
    severity VARCHAR(50),
    service VARCHAR(100),
    instance VARCHAR(200),
    fingerprint VARCHAR(200),

    starts_at TIMESTAMP,
    ends_at TIMESTAMP,
    generator_url TEXT,

    summary TEXT,
    description TEXT,

    labels JSONB,
    annotations JSONB,
    raw_payload JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alert_events_status
ON alert_events(status);

CREATE INDEX IF NOT EXISTS idx_alert_events_alert_name
ON alert_events(alert_name);

CREATE INDEX IF NOT EXISTS idx_alert_events_severity
ON alert_events(severity);

CREATE INDEX IF NOT EXISTS idx_alert_events_service
ON alert_events(service);

CREATE INDEX IF NOT EXISTS idx_alert_events_created_at
ON alert_events(created_at);

CREATE TABLE IF NOT EXISTS alert_current_states (
    id BIGSERIAL PRIMARY KEY,

    fingerprint VARCHAR(200) NOT NULL UNIQUE,

    status VARCHAR(30) NOT NULL,
    alert_name VARCHAR(200),
    severity VARCHAR(50),
    service VARCHAR(100),
    instance VARCHAR(200),

    starts_at TIMESTAMP,
    ends_at TIMESTAMP,
    last_received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    summary TEXT,
    description TEXT,

    labels JSONB,
    annotations JSONB,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alert_current_states_status
ON alert_current_states(status);

CREATE INDEX IF NOT EXISTS idx_alert_current_states_alert_name
ON alert_current_states(alert_name);

CREATE INDEX IF NOT EXISTS idx_alert_current_states_severity
ON alert_current_states(severity);

CREATE INDEX IF NOT EXISTS idx_alert_current_states_service
ON alert_current_states(service);

CREATE INDEX IF NOT EXISTS idx_alert_current_states_updated_at
ON alert_current_states(updated_at);

CREATE TABLE IF NOT EXISTS alert_acknowledgements (
    id BIGSERIAL PRIMARY KEY,

    fingerprint VARCHAR(200),
    alert_name VARCHAR(200),
    severity VARCHAR(50),
    service VARCHAR(100),
    status VARCHAR(30),

    acknowledged_by VARCHAR(100) DEFAULT 'local-user',
    note TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alert_acknowledgements_fingerprint
ON alert_acknowledgements(fingerprint);

CREATE INDEX IF NOT EXISTS idx_alert_acknowledgements_alert_name
ON alert_acknowledgements(alert_name);

CREATE INDEX IF NOT EXISTS idx_alert_acknowledgements_created_at
ON alert_acknowledgements(created_at);

CREATE TABLE IF NOT EXISTS alert_settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value VARCHAR(100) NOT NULL,
    description TEXT,
    updated_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO alert_settings (
    setting_key,
    setting_value,
    description,
    updated_by
)
VALUES (
    'maintenance_mode',
    'false',
    'Suppress non-critical Prometheus alert rules during testing or maintenance.',
    'system'
)
ON CONFLICT (setting_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS alert_silence_actions (
    id BIGSERIAL PRIMARY KEY,

    silence_id VARCHAR(200),
    fingerprint VARCHAR(200),

    alert_name VARCHAR(200),
    severity VARCHAR(50),
    service VARCHAR(100),
    instance VARCHAR(200),

    duration_minutes INTEGER NOT NULL,
    starts_at TIMESTAMP,
    ends_at TIMESTAMP,

    created_by VARCHAR(100) DEFAULT 'local-user',
    reason TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alert_silence_actions_silence_id
ON alert_silence_actions(silence_id);

CREATE INDEX IF NOT EXISTS idx_alert_silence_actions_fingerprint
ON alert_silence_actions(fingerprint);

CREATE INDEX IF NOT EXISTS idx_alert_silence_actions_alert_name
ON alert_silence_actions(alert_name);

CREATE INDEX IF NOT EXISTS idx_alert_silence_actions_created_at
ON alert_silence_actions(created_at);