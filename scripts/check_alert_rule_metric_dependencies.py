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

DEFAULT_RULES_PATH = PROJECT_ROOT / "monitoring" / "prometheus" / "rules" / "jobskill_alert_rules.yml"
DEFAULT_CONTRACT_PATH = PROJECT_ROOT / "monitoring" / "metrics_contract.yml"
DEFAULT_FASTAPI_METRICS_URL = "http://localhost:8000/metrics"

# PromQL functions, aggregators, operators, and keywords that are not metric names.
PROMQL_RESERVED_WORDS = {
    "abs",
    "absent",
    "absent_over_time",
    "avg",
    "avg_over_time",
    "bottomk",
    "ceil",
    "changes",
    "clamp",
    "clamp_max",
    "clamp_min",
    "count",
    "count_over_time",
    "count_values",
    "day_of_month",
    "day_of_week",
    "day_of_year",
    "days_in_month",
    "delta",
    "deriv",
    "exp",
    "floor",
    "histogram_avg",
    "histogram_count",
    "histogram_fraction",
    "histogram_quantile",
    "histogram_sum",
    "holt_winters",
    "hour",
    "idelta",
    "increase",
    "irate",
    "label_join",
    "label_replace",
    "last_over_time",
    "ln",
    "log2",
    "log10",
    "max",
    "max_over_time",
    "min",
    "min_over_time",
    "minute",
    "month",
    "predict_linear",
    "present_over_time",
    "quantile",
    "quantile_over_time",
    "rate",
    "resets",
    "round",
    "scalar",
    "sgn",
    "sort",
    "sort_desc",
    "sqrt",
    "stddev",
    "stddev_over_time",
    "stdvar",
    "stdvar_over_time",
    "sum",
    "sum_over_time",
    "time",
    "timestamp",
    "topk",
    "vector",
    "year",
    "and",
    "or",
    "unless",
    "bool",
    "by",
    "without",
    "on",
    "ignoring",
    "group_left",
    "group_right",
    "offset",
}

# Prometheus built-in or scrape-level metrics that are allowed without the app contract.
EXTERNAL_BUILTIN_METRICS = {
    "up",
}


@dataclass(frozen=True)
class MetricContractEntry:
    name: str
    source: str
    url: str | None


def pass_check(message: str) -> None:
    print(f"[PASS] {message}")


def fail_check(message: str) -> None:
    print(f"[FAIL] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML object: {path}")

    return data


def normalize_metric_list(value: Any, context: str) -> list[str]:
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

    return metrics


def load_metric_contract(contract_path: Path, default_url: str) -> dict[str, MetricContractEntry]:
    contract = load_yaml(contract_path)

    metric_map: dict[str, MetricContractEntry] = {}

    fastapi_metrics = normalize_metric_list(
        contract.get("required_metrics", []),
        "required_metrics",
    )

    for metric in fastapi_metrics:
        metric_map[metric] = MetricContractEntry(
            name=metric,
            source="fastapi",
            url=default_url,
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
        source_required_metrics = normalize_metric_list(
            source_config.get("required_metrics", []),
            f"external_metrics.{source_name}.required_metrics",
        )

        for metric in source_required_metrics:
            metric_map[metric] = MetricContractEntry(
                name=metric,
                source=str(source_name),
                url=str(source_url) if source_url else None,
            )

    duplicated_metrics = sorted(
        {
            metric
            for metric in metric_map
            if list(metric_map.keys()).count(metric) > 1
        }
    )

    if duplicated_metrics:
        raise ValueError(
            "Duplicated metrics found in contract: "
            + ", ".join(duplicated_metrics)
        )

    return metric_map


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


def load_exposed_metrics_by_source(
    metric_contract: dict[str, MetricContractEntry],
    default_url: str,
    skip_url: bool,
) -> dict[str, set[str]]:
    if skip_url:
        return {}

    source_urls: dict[str, str] = {
        "fastapi": default_url,
    }

    for entry in metric_contract.values():
        if entry.url:
            source_urls[entry.source] = entry.url

    exposed_by_source: dict[str, set[str]] = {}

    for source, url in source_urls.items():
        metrics_text = fetch_metrics_text(url)
        exposed_by_source[source] = parse_exposed_metric_names(metrics_text)

    return exposed_by_source


def extract_alert_rules(rules_path: Path) -> list[dict[str, str]]:
    rules_yaml = load_yaml(rules_path)

    alert_rules: list[dict[str, str]] = []

    for group in rules_yaml.get("groups", []):
        if not isinstance(group, dict):
            continue

        for rule in group.get("rules", []):
            if not isinstance(rule, dict):
                continue

            alert_name = rule.get("alert")
            expr = rule.get("expr")

            if alert_name and expr:
                alert_rules.append(
                    {
                        "alert": str(alert_name),
                        "expr": str(expr),
                    }
                )

    return alert_rules


def strip_promql_non_metric_parts(expr: str) -> str:
    cleaned = expr

    # Remove quoted strings.
    cleaned = re.sub(r'"(?:\\.|[^"\\])*"', "", cleaned)
    cleaned = re.sub(r"'(?:\\.|[^'\\])*'", "", cleaned)

    # Remove label matcher blocks: metric{label="value"} -> metric
    cleaned = re.sub(r"\{[^{}]*\}", "", cleaned)

    # Remove range selectors: metric[5m] -> metric
    cleaned = re.sub(r"\[[^\[\]]*\]", "", cleaned)

    # Remove grouping labels: sum by (receiver, integration) -> sum
    cleaned = re.sub(r"\b(?:by|without)\s*\([^)]*\)", "", cleaned)

    # Remove vector matching labels: on (...) / ignoring (...) / group_left (...)
    cleaned = re.sub(r"\b(?:on|ignoring|group_left|group_right)\s*\([^)]*\)", "", cleaned)

    return cleaned


def extract_metric_names_from_expr(expr: str) -> set[str]:
    cleaned = strip_promql_non_metric_parts(expr)

    tokens = set(
        re.findall(
            r"\b[a-zA-Z_:][a-zA-Z0-9_:]*\b",
            cleaned,
        )
    )

    return {
        token
        for token in tokens
        if token not in PROMQL_RESERVED_WORDS
        and not token.startswith("__")
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check whether Prometheus alert rules reference known metrics."
    )
    parser.add_argument(
        "--rules",
        default=str(DEFAULT_RULES_PATH),
        help="Path to Prometheus alert rule file.",
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
        help="Only check metric contract references, without checking live /metrics endpoints.",
    )

    args = parser.parse_args()

    rules_path = Path(args.rules)
    contract_path = Path(args.contract)

    print("")
    print("JobSkill Alert Rule Metric Dependency Check")
    print(f"Rules   : {rules_path}")
    print(f"Contract: {contract_path}")
    print(f"Metrics : {args.url}")
    print(f"Skip URL: {args.skip_url}")
    print("")

    metric_contract = load_metric_contract(contract_path, args.url)
    exposed_by_source = load_exposed_metrics_by_source(
        metric_contract=metric_contract,
        default_url=args.url,
        skip_url=args.skip_url,
    )

    alert_rules = extract_alert_rules(rules_path)

    has_error = False
    missing_from_contract: dict[str, list[str]] = {}
    missing_from_metrics: dict[str, list[str]] = {}

    for rule in alert_rules:
        alert_name = rule["alert"]
        expr = rule["expr"]
        metric_names = sorted(extract_metric_names_from_expr(expr))

        print(f"[ALERT] {alert_name}")

        if not metric_names:
            print("  [WARN] No metric references found")
            print("")
            continue

        for metric in metric_names:
            if metric in EXTERNAL_BUILTIN_METRICS:
                print(f"  [OK] {metric} external")
                continue

            contract_entry = metric_contract.get(metric)

            if not contract_entry:
                print(f"  [MISSING_CONTRACT] {metric}")
                missing_from_contract.setdefault(alert_name, []).append(metric)
                has_error = True
                continue

            if args.skip_url:
                print(f"  [OK] {metric} contract source={contract_entry.source}")
                continue

            exposed_metrics = exposed_by_source.get(contract_entry.source, set())

            if metric not in exposed_metrics:
                print(
                    f"  [MISSING_METRICS] {metric} "
                    f"source={contract_entry.source}"
                )
                missing_from_metrics.setdefault(alert_name, []).append(metric)
                has_error = True
                continue

            print(f"  [OK] {metric} source={contract_entry.source}")

        print("")

    if missing_from_contract:
        print("[DEBUG] metrics missing from contract:")
        for alert_name, metrics in missing_from_contract.items():
            print(f"  {alert_name}: {', '.join(metrics)}")

    if missing_from_metrics:
        print("[DEBUG] metrics missing from live endpoints:")
        for alert_name, metrics in missing_from_metrics.items():
            print(f"  {alert_name}: {', '.join(metrics)}")

    if has_error:
        fail_check("Some alert rule metrics are missing from contract or live endpoints")
        sys.exit(1)

    pass_check(f"Alert rule metric dependency check completed: {len(alert_rules)} alerts")


if __name__ == "__main__":
    main()
