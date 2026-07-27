from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PROMETHEUS_URL = "http://localhost:9090"
DEFAULT_CONTRACT_PATH = PROJECT_ROOT / "monitoring" / "metrics_contract.yml"


def pass_check(message: str) -> None:
    print(f"[PASS] {message}")


def fail_check(message: str) -> None:
    print(f"[FAIL] {message}")


def http_get_json(url: str, timeout_seconds: int = 10) -> dict[str, Any]:
    request = urllib.request.Request(url=url, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            return json.loads(body)

    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to request {url}: {exc}") from exc


def load_external_metrics(contract_path: Path) -> dict[str, dict[str, Any]]:
    with contract_path.open("r", encoding="utf-8") as file:
        contract = yaml.safe_load(file)

    if not isinstance(contract, dict):
        raise ValueError(f"Invalid metrics contract: {contract_path}")

    external_metrics = contract.get("external_metrics", {})

    if external_metrics is None:
        return {}

    if not isinstance(external_metrics, dict):
        raise ValueError("external_metrics must be a mapping")

    return external_metrics


def prometheus_query(prometheus_url: str, query: str) -> dict[str, Any]:
    encoded_query = urllib.parse.urlencode({"query": query})
    url = f"{prometheus_url.rstrip('/')}/api/v1/query?{encoded_query}"
    return http_get_json(url)


def get_active_targets(prometheus_url: str) -> list[dict[str, Any]]:
    url = f"{prometheus_url.rstrip('/')}/api/v1/targets"
    response = http_get_json(url)

    if response.get("status") != "success":
        raise RuntimeError(f"Prometheus targets API failed: {response}")

    data = response.get("data", {})
    active_targets = data.get("activeTargets", [])

    if not isinstance(active_targets, list):
        raise RuntimeError("Prometheus targets API returned invalid activeTargets")

    return active_targets


def find_target_by_job(
    active_targets: list[dict[str, Any]],
    job_name: str,
) -> list[dict[str, Any]]:
    matched_targets: list[dict[str, Any]] = []

    for target in active_targets:
        labels = target.get("labels", {})

        if labels.get("job") == job_name:
            matched_targets.append(target)

    return matched_targets


def check_target_health(
    active_targets: list[dict[str, Any]],
    job_name: str,
) -> None:
    matched_targets = find_target_by_job(active_targets, job_name)

    if not matched_targets:
        raise RuntimeError(f"Prometheus target not found for job={job_name}")

    unhealthy_targets = [
        target
        for target in matched_targets
        if target.get("health") != "up"
    ]

    if unhealthy_targets:
        details = [
            {
                "scrapeUrl": target.get("scrapeUrl"),
                "health": target.get("health"),
                "lastError": target.get("lastError"),
            }
            for target in unhealthy_targets
        ]
        raise RuntimeError(
            f"Prometheus target is not healthy for job={job_name}: {details}"
        )

    for target in matched_targets:
        print(
            "[OK] Prometheus target "
            f"job={job_name} health={target.get('health')} "
            f"scrapeUrl={target.get('scrapeUrl')}"
        )


def check_metric_query(prometheus_url: str, metric_name: str) -> None:
    response = prometheus_query(prometheus_url, metric_name)

    if response.get("status") != "success":
        raise RuntimeError(f"Prometheus query failed for {metric_name}: {response}")

    result = response.get("data", {}).get("result", [])

    if not result:
        raise RuntimeError(
            f"Metric not found in Prometheus query result: {metric_name}"
        )

    print(f"[OK] Prometheus query returned metric: {metric_name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check Prometheus external scrape targets and external metrics."
    )
    parser.add_argument(
        "--prometheus-url",
        default=DEFAULT_PROMETHEUS_URL,
        help="Prometheus base URL.",
    )
    parser.add_argument(
        "--contract",
        default=str(DEFAULT_CONTRACT_PATH),
        help="Path to metrics contract YAML.",
    )

    args = parser.parse_args()

    prometheus_url = args.prometheus_url.rstrip("/")
    contract_path = Path(args.contract)

    print("")
    print("JobSkill Prometheus External Target Check")
    print(f"Prometheus: {prometheus_url}")
    print(f"Contract  : {contract_path}")
    print("")

    external_metrics = load_external_metrics(contract_path)

    if not external_metrics:
        print("[SKIP] No external_metrics defined in metrics contract")
        pass_check("Prometheus external target check skipped")
        return

    active_targets = get_active_targets(prometheus_url)

    has_error = False

    for source_name, source_config in external_metrics.items():
        print(f"[SOURCE] {source_name}")

        try:
            check_target_health(active_targets, str(source_name))

            required_metrics = source_config.get("required_metrics", [])

            if not isinstance(required_metrics, list):
                raise ValueError(
                    f"external_metrics.{source_name}.required_metrics must be a list"
                )

            for metric_name in required_metrics:
                check_metric_query(prometheus_url, str(metric_name))

        except Exception as exc:
            print(f"[ERROR] {source_name}: {exc}")
            has_error = True

        print("")

    if has_error:
        fail_check("Prometheus external target check failed")
        sys.exit(1)

    pass_check("Prometheus external target check completed")


if __name__ == "__main__":
    main()
