import os
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


def get_db_url() -> str:
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    db = os.getenv("DB_NAME", "jobskill")
    user = os.getenv("DB_USER", "jobskill")
    password = os.getenv("DB_PASSWORD", "jobskill")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def get_engine():
    return create_engine(get_db_url())
