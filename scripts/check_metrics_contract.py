from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = PROJECT_ROOT / "monitoring/metrics_contract.yml"
DEFAULT_METRICS_URL = "http://localhost:8000/metrics"


REQUIRED_METRIC_PATTERN = re.compile(r"^\s*-\s*([a-zA-Z_:][a-zA-Z0-9_:]*)\s*$")
METRIC_LINE_PATTERN = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{.*\})?\s+[-+0-9.eE]+$")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    sys.exit(1)


def pass_check(message: str) -> None:
    print(f"[PASS] {message}")


def load_required_metrics(contract_path: Path) -> list[str]:
    if not contract_path.exists():
        fail(f"Metrics contract file not found: {contract_path}")

    required_metrics: list[str] = []

    for line in contract_path.read_text(encoding="utf-8").splitlines():
        match = REQUIRED_METRIC_PATTERN.match(line)

        if match:
            required_metrics.append(match.group(1))

    if not required_metrics:
        fail(f"No required metrics found in contract file: {contract_path}")

    duplicated_metrics = sorted(
        {
            metric
            for metric in required_metrics
            if required_metrics.count(metric) > 1
        }
    )

    if duplicated_metrics:
        fail(f"Duplicated required metrics: {', '.join(duplicated_metrics)}")

    return required_metrics


def fetch_metrics_body(metrics_url: str) -> str:
    try:
        with urlopen(metrics_url, timeout=10) as response:
            status_code = response.status
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        fail(f"Metrics endpoint returned HTTP {exc.code}: {metrics_url}")
    except URLError as exc:
        fail(f"Metrics endpoint request failed: {metrics_url} ({exc})")

    if status_code != 200:
        fail(f"Metrics endpoint returned HTTP {status_code}: {metrics_url}")

    if not body.strip():
        fail(f"Metrics endpoint returned empty body: {metrics_url}")

    return body


def extract_exposed_metric_names(metrics_body: str) -> set[str]:
    metric_names: set[str] = set()

    for line in metrics_body.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        match = METRIC_LINE_PATTERN.match(line)

        if match:
            metric_names.add(match.group(1))

    return metric_names


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate required JobSkill Prometheus metrics."
    )
    parser.add_argument(
        "--contract",
        default=str(DEFAULT_CONTRACT_PATH),
        help="Path to metrics contract YAML file.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_METRICS_URL,
        help="FastAPI /metrics URL.",
    )

    args = parser.parse_args()

    contract_path = Path(args.contract)
    metrics_url = args.url

    print("")
    print("JobSkill Metrics Contract Check")
    print(f"Contract: {contract_path}")
    print(f"Metrics : {metrics_url}")

    required_metrics = load_required_metrics(contract_path)
    metrics_body = fetch_metrics_body(metrics_url)
    exposed_metric_names = extract_exposed_metric_names(metrics_body)

    missing_metrics = [
        metric
        for metric in required_metrics
        if metric not in exposed_metric_names
    ]

    for metric in required_metrics:
        if metric in exposed_metric_names:
            print(f"[OK] {metric}")
        else:
            print(f"[MISSING] {metric}")

    if missing_metrics:
        print("")
        print("[DEBUG] exposed metric names:")
        for metric in sorted(exposed_metric_names):
            print(f"  - {metric}")

        fail(f"Missing required metrics: {', '.join(missing_metrics)}")

    print("")
    pass_check(f"Metrics contract check completed: {len(required_metrics)} metrics")


if __name__ == "__main__":
    main()
