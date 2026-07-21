from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_RULES_PATH = PROJECT_ROOT / "monitoring/prometheus/rules/jobskill_alert_rules.yml"
DEFAULT_CONTRACT_PATH = PROJECT_ROOT / "monitoring/metrics_contract.yml"
DEFAULT_METRICS_URL = "http://localhost:8000/metrics"

ALLOWED_EXTERNAL_METRICS = {
    "up",
}

PROMQL_RESERVED_WORDS = {
    "and",
    "or",
    "unless",
    "on",
    "ignoring",
    "group_left",
    "group_right",
    "by",
    "without",
    "bool",
    "offset",
}

PROMQL_FUNCTIONS = {
    "abs",
    "absent",
    "avg",
    "avg_over_time",
    "ceil",
    "changes",
    "clamp",
    "clamp_max",
    "clamp_min",
    "count",
    "count_over_time",
    "day_of_month",
    "day_of_week",
    "days_in_month",
    "delta",
    "deriv",
    "exp",
    "floor",
    "histogram_quantile",
    "hour",
    "idelta",
    "increase",
    "irate",
    "label_join",
    "label_replace",
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
    "quantile",
    "quantile_over_time",
    "rate",
    "resets",
    "round",
    "scalar",
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
}

ALERT_PATTERN = re.compile(r"^\s*-\s*alert:\s*([A-Za-z0-9_]+)\s*$")
METRIC_TOKEN_PATTERN = re.compile(r"\b[a-zA-Z_:][a-zA-Z0-9_:]*\b")
REQUIRED_METRIC_PATTERN = re.compile(r"^\s*-\s*([a-zA-Z_:][a-zA-Z0-9_:]*)\s*$")
METRIC_LINE_PATTERN = re.compile(
    r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{.*\})?\s+[-+0-9.eE]+$"
)


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    sys.exit(1)


def pass_check(message: str) -> None:
    print(f"[PASS] {message}")


def load_required_metrics(contract_path: Path) -> set[str]:
    if not contract_path.exists():
        fail(f"Metrics contract file not found: {contract_path}")

    metrics: list[str] = []

    for line in contract_path.read_text(encoding="utf-8").splitlines():
        match = REQUIRED_METRIC_PATTERN.match(line)

        if match:
            metrics.append(match.group(1))

    if not metrics:
        fail(f"No required metrics found in contract file: {contract_path}")

    duplicated_metrics = sorted(
        {
            metric
            for metric in metrics
            if metrics.count(metric) > 1
        }
    )

    if duplicated_metrics:
        fail(f"Duplicated contract metrics: {', '.join(duplicated_metrics)}")

    return set(metrics)


def parse_alert_blocks(rules_path: Path) -> dict[str, list[str]]:
    if not rules_path.exists():
        fail(f"Alert rules file not found: {rules_path}")

    alert_blocks: dict[str, list[str]] = {}

    current_alert: str | None = None
    current_lines: list[str] = []

    for line in rules_path.read_text(encoding="utf-8").splitlines():
        alert_match = ALERT_PATTERN.match(line)

        if alert_match:
            if current_alert:
                alert_blocks[current_alert] = current_lines

            current_alert = alert_match.group(1)
            current_lines = []
            continue

        if current_alert:
            current_lines.append(line)

    if current_alert:
        alert_blocks[current_alert] = current_lines

    if not alert_blocks:
        fail(f"No alert blocks found in {rules_path}")

    return alert_blocks


def extract_expr_lines(alert_lines: list[str]) -> list[str]:
    expr_lines: list[str] = []
    in_expr = False

    for line in alert_lines:
        stripped = line.strip()

        if stripped.startswith("expr:"):
            in_expr = True

            after_expr = stripped.removeprefix("expr:").strip()

            if after_expr and after_expr not in {"|", ">"}:
                expr_lines.append(after_expr)

            continue

        if in_expr and (
            stripped.startswith("for:")
            or stripped.startswith("labels:")
            or stripped.startswith("annotations:")
        ):
            break

        if in_expr:
            expr_lines.append(line)

    return expr_lines


def remove_quoted_text(expression: str) -> str:
    expression = re.sub(r'"[^"]*"', '""', expression)
    expression = re.sub(r"'[^']*'", "''", expression)

    return expression


def remove_label_selectors(expression: str) -> str:
    return re.sub(r"\{[^{}]*\}", "", expression)


def extract_metric_names_from_expr(expression: str) -> set[str]:
    expression = remove_quoted_text(expression)
    expression = remove_label_selectors(expression)

    metric_names: set[str] = set()

    for token in METRIC_TOKEN_PATTERN.findall(expression):
        if token in PROMQL_RESERVED_WORDS:
            continue

        if token in PROMQL_FUNCTIONS:
            continue

        if token in {"true", "false"}:
            continue

        metric_names.add(token)

    return metric_names


def extract_alert_metric_dependencies(
    alert_blocks: dict[str, list[str]],
) -> dict[str, set[str]]:
    alert_metric_dependencies: dict[str, set[str]] = {}

    for alert_name, alert_lines in alert_blocks.items():
        expr_lines = extract_expr_lines(alert_lines)

        if not expr_lines:
            fail(f"{alert_name}: expr not found")

        expression = "\n".join(expr_lines)

        metric_names = extract_metric_names_from_expr(expression)

        if not metric_names:
            fail(f"{alert_name}: no metric dependency found in expr")

        alert_metric_dependencies[alert_name] = metric_names

    return alert_metric_dependencies


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
        description="Validate Prometheus alert rule metric dependencies."
    )
    parser.add_argument(
        "--rules",
        default=str(DEFAULT_RULES_PATH),
        help="Path to Prometheus alert rules YAML.",
    )
    parser.add_argument(
        "--contract",
        default=str(DEFAULT_CONTRACT_PATH),
        help="Path to metrics contract YAML.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_METRICS_URL,
        help="FastAPI /metrics URL.",
    )
    parser.add_argument(
        "--skip-metrics-endpoint",
        action="store_true",
        help="Skip checking the live /metrics endpoint.",
    )

    args = parser.parse_args()

    rules_path = Path(args.rules)
    contract_path = Path(args.contract)
    metrics_url = args.url

    print("")
    print("JobSkill Alert Rule Metric Dependency Check")
    print(f"Rules   : {rules_path}")
    print(f"Contract: {contract_path}")
    print(f"Metrics : {metrics_url}")
    print(f"Skip URL: {args.skip_metrics_endpoint}")

    contract_metrics = load_required_metrics(contract_path)
    alert_blocks = parse_alert_blocks(rules_path)
    alert_dependencies = extract_alert_metric_dependencies(alert_blocks)

    exposed_metric_names: set[str] = set()

    if not args.skip_metrics_endpoint:
        metrics_body = fetch_metrics_body(metrics_url)
        exposed_metric_names = extract_exposed_metric_names(metrics_body)

    missing_from_contract: dict[str, set[str]] = {}
    missing_from_metrics_endpoint: dict[str, set[str]] = {}

    for alert_name, metric_names in alert_dependencies.items():
        print("")
        print(f"[ALERT] {alert_name}")

        for metric_name in sorted(metric_names):
            if metric_name in ALLOWED_EXTERNAL_METRICS:
                print(f"  [OK] {metric_name} external")
                continue

            if metric_name not in contract_metrics:
                missing_from_contract.setdefault(alert_name, set()).add(metric_name)
                print(f"  [MISSING_CONTRACT] {metric_name}")
                continue

            if not args.skip_metrics_endpoint and metric_name not in exposed_metric_names:
                missing_from_metrics_endpoint.setdefault(alert_name, set()).add(metric_name)
                print(f"  [MISSING_METRICS] {metric_name}")
                continue

            print(f"  [OK] {metric_name}")

    if missing_from_contract:
        print("")
        print("[DEBUG] metrics missing from contract:")
        for alert_name, metric_names in missing_from_contract.items():
            print(f"  {alert_name}: {', '.join(sorted(metric_names))}")

        fail("Some alert rule metrics are missing from metrics_contract.yml")

    if missing_from_metrics_endpoint:
        print("")
        print("[DEBUG] metrics missing from /metrics:")
        for alert_name, metric_names in missing_from_metrics_endpoint.items():
            print(f"  {alert_name}: {', '.join(sorted(metric_names))}")

        fail("Some alert rule metrics are missing from FastAPI /metrics")

    print("")
    pass_check(
        f"Alert rule metric dependency check completed: "
        f"{len(alert_dependencies)} alerts"
    )


if __name__ == "__main__":
    main()
