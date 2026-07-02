from __future__ import annotations

import os


VALID_DATA_SOURCE_MODES = {
    "sample_only",
    "crawler_only",
    "mixed",
}


def get_data_source_mode() -> str:
    mode = os.getenv("DATA_SOURCE_MODE", "mixed").strip().lower()

    if mode not in VALID_DATA_SOURCE_MODES:
        raise ValueError(
            f"Invalid DATA_SOURCE_MODE: {mode}. "
            f"Expected one of: {sorted(VALID_DATA_SOURCE_MODES)}"
        )

    return mode


def should_use_sample_data() -> bool:
    mode = get_data_source_mode()

    return mode in {"sample_only", "mixed"}


def should_use_crawler_data() -> bool:
    mode = get_data_source_mode()

    return mode in {"crawler_only", "mixed"}
