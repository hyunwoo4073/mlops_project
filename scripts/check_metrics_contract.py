from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CONTRACT_PATH = PROJECT_ROOT / "monitoring" / "metrics_contract.yml"
DEFAULT_FASTAPI_METRICS_URL = "http://localhost:8000/metrics"


@dataclass(frozen=True)
class MetricSource:
    name: str
    url: str
    required_metrics: list[str]


def pass_check(message: str) -> None:
    print(f"[PASS] {message}")


def fail_check(message: str) -> None:
    print(f"[FAIL] {message}")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid metrics contract format: {path}")

    return data


def normalize_required_metrics(value: Any, context: str) -> list[str]:
    if value is None:
        return []

    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")

    metrics: list[str] = []

    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{context} contains non-string item: {item!r}")

        metric = item.strip()

        if metric:
            metrics.append(metric)

    duplicated_metrics = sorted(
        {
            metric
            for metric in metrics
            if metrics.count(metric) > 1
        }
    )

    if duplicated_metrics:
        raise ValueError(
            f"Duplicated metrics in {context}: "
            + ", ".join(duplicated_metrics)
        )

    return metrics


def load_metric_sources(contract_path: Path, fastapi_url: str) -> list[MetricSource]:
    contract = load_yaml(contract_path)

    metric_sources: list[MetricSource] = []

    fastapi_required_metrics = normalize_required_metrics(
        contract.get("required_metrics", []),
        "required_metrics",
    )

    if not fastapi_required_metrics:
        raise ValueError("No required_metrics found in metrics_contract.yml")

    metric_sources.append(
        MetricSource(
            name="fastapi",
            url=fastapi_url,
            required_metrics=fastapi_required_metrics,
        )
    )

    external_metrics = contract.get("external_metrics", {})

    if external_metrics is None:
        external_metrics = {}

    if not isinstance(external_metrics, dict):
        raise ValueError("external_metrics must be a mapping")

    for source_name, source_config in external_metrics.items():
        if not isinstance(source_config, dict):
            raise ValueError(f"external_metrics.{source_name} must be a mapping")

        source_url = source_config.get("url")

        if not source_url:
            raise ValueError(f"external_metrics.{source_name}.url is required")

        source_required_metrics = normalize_required_metrics(
            source_config.get("required_metrics", []),
            f"external_metrics.{source_name}.required_metrics",
        )

        if not source_required_metrics:
            raise ValueError(
                f"external_metrics.{source_name}.required_metrics must not be empty"
            )

        metric_sources.append(
            MetricSource(
                name=str(source_name),
                url=str(source_url),
                required_metrics=source_required_metrics,
            )
        )

    all_metrics: list[str] = []

    for source in metric_sources:
        all_metrics.extend(source.required_metrics)

    duplicated_across_sources = sorted(
        {
            metric
            for metric in all_metrics
            if all_metrics.count(metric) > 1
        }
    )

    if duplicated_across_sources:
        raise ValueError(
            "Duplicated metrics across metric sources: "
            + ", ".join(duplicated_across_sources)
        )

    return metric_sources


def fetch_metrics_text(url: str, timeout_seconds: int = 10) -> str:
    request = urllib.request.Request(url=url, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read().decode("utf-8", errors="replace")

    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to fetch metrics from {url}: {exc}") from exc


def parse_exposed_metric_names(metrics_text: str) -> set[str]:
    metric_names: set[str] = set()

    for raw_line in metrics_text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        match = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{|\s)", line)

        if match:
            metric_names.add(match.group(1))

    return metric_names


def check_metric_source(source: MetricSource, skip_url: bool) -> tuple[bool, set[str]]:
    print("")
    print(f"[SOURCE] {source.name}")
    print(f"URL     : {source.url}")

    if skip_url:
        for metric in source.required_metrics:
            print(f"[SKIP] {metric}")
        return True, set()

    metrics_text = fetch_metrics_text(source.url)
    exposed_metric_names = parse_exposed_metric_names(metrics_text)

    missing_metrics: set[str] = set()

    for metric in source.required_metrics:
        if metric in exposed_metric_names:
            print(f"[OK] {metric}")
        else:
            print(f"[MISSING] {metric}")
            missing_metrics.add(metric)

    if missing_metrics:
        print("")
        print(f"[DEBUG] exposed metric names from {source.name}:")
        for metric in sorted(exposed_metric_names):
            print(f"  - {metric}")

    return not missing_metrics, missing_metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate required metrics from FastAPI and external metric sources."
    )
    parser.add_argument(
        "--contract",
        default=str(DEFAULT_CONTRACT_PATH),
        help="Path to metrics contract YAML.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_FASTAPI_METRICS_URL,
        help="FastAPI /metrics URL.",
    )
    parser.add_argument(
        "--skip-url",
        action="store_true",
        help="Only validate metrics_contract.yml structure, without fetching metrics endpoints.",
    )

    args = parser.parse_args()

    contract_path = Path(args.contract)

    print("")
    print("JobSkill Metrics Contract Check")
    print(f"Contract: {contract_path}")
    print(f"Metrics : {args.url}")
    print(f"Skip URL: {args.skip_url}")

    try:
        metric_sources = load_metric_sources(contract_path, args.url)
    except Exception as exc:
        fail_check(str(exc))
        sys.exit(1)

    total_required_metrics = sum(
        len(source.required_metrics)
        for source in metric_sources
    )

    all_missing_metrics: dict[str, set[str]] = {}
    has_error = False

    for source in metric_sources:
        try:
            source_passed, missing_metrics = check_metric_source(
                source=source,
                skip_url=args.skip_url,
            )
        except Exception as exc:
            print(f"[ERROR] {source.name}: {exc}")
            has_error = True
            continue

        if not source_passed:
            all_missing_metrics[source.name] = missing_metrics
            has_error = True

    if all_missing_metrics:
        print("")
        print("[DEBUG] missing required metrics by source:")
        for source_name, missing_metrics in all_missing_metrics.items():
            print(f"  {source_name}: {', '.join(sorted(missing_metrics))}")

    if has_error:
        fail_check("Missing required metrics")
        sys.exit(1)

    print("")
    pass_check(
        f"Metrics contract check completed: "
        f"{total_required_metrics} metrics across {len(metric_sources)} sources"
    )


if __name__ == "__main__":
    main()
