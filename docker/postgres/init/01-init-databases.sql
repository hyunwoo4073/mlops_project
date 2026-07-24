-- Create Airflow role if it does not exist.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles WHERE rolname = 'airflow'
    ) THEN
        CREATE ROLE airflow LOGIN PASSWORD 'airflow';
    ELSE
        ALTER ROLE airflow WITH LOGIN PASSWORD 'airflow';
    END IF;
END
$$;

-- Create Airflow metadata database if it does not exist.
SELECT 'CREATE DATABASE airflow OWNER airflow'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'airflow'
)
\gexec

-- Create MLflow backend database if it does not exist.
SELECT 'CREATE DATABASE mlflow OWNER jobskill'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'mlflow'
)
\gexec

-- Ensure ownership and privileges.
ALTER DATABASE airflow OWNER TO airflow;
ALTER DATABASE mlflow OWNER TO jobskill;
ALTER DATABASE jobskill OWNER TO jobskill;

GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;
GRANT ALL PRIVILEGES ON DATABASE mlflow TO jobskill;
GRANT ALL PRIVILEGES ON DATABASE jobskill TO jobskill;
