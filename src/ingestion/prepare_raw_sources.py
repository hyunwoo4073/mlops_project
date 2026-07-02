from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text


sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.data_source_mode import get_data_source_mode
from src.common.db import get_engine


def main() -> None:
    engine = get_engine()
    mode = get_data_source_mode()

    print("\n[Prepare Raw Sources]")
    print(f"DATA_SOURCE_MODE: {mode}")

    with engine.begin() as conn:
        # raw 데이터를 지우기 전에 raw를 참조하는 파생 테이블을 먼저 초기화한다.
        conn.execute(
            text(
                """
                TRUNCATE TABLE
                    model_predictions,
                    job_post_skills,
                    cleaned_job_posts
                RESTART IDENTITY
                CASCADE
                """
            )
        )

        if mode == "sample_only":
            result = conn.execute(
                text(
                    """
                    DELETE FROM raw_job_posts
                    WHERE COALESCE(source, 'sample') <> 'sample'
                    """
                )
            )

            print(f"deleted_non_sample_raw_rows: {result.rowcount}")

        elif mode == "crawler_only":
            result = conn.execute(
                text(
                    """
                    DELETE FROM raw_job_posts
                    WHERE COALESCE(source, 'sample') = 'sample'
                    """
                )
            )

            print(f"deleted_sample_raw_rows: {result.rowcount}")

        else:
            print("mixed mode: keep sample and crawler raw rows")

    print("prepare_raw_sources completed")


if __name__ == "__main__":
    main()
