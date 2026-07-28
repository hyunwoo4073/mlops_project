from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


AIRFLOW_SERVICES = {
    "airflow-apiserver",
    "airflow-scheduler",
    "airflow-dag-processor",
    "airflow-triggerer",
    "airflow-init",
}

REQUIRED_SERVICE_ENV = {
    "airflow-apiserver": [
        "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN",
    ],
    "airflow-scheduler": [
        "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN",
    ],
    "airflow-dag-processor": [
        "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN",
    ],
    "airflow-triggerer": [
        "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN",
    ],
    "airflow-init": [
        "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN",
    ],
    "mlflow": [
        "MLFLOW_TRACKING_URI",
        "MLFLOW_ARTIFACT_ROOT",
    ],
    "api": [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "BEST_MODEL_PATH",
    ],
    "dashboard": [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ],
}


def pass_check(message: str) -> None:
    print(f"[PASS] {message}")


def fail_check(message: str) -> None:
    print(f"[FAIL] {message}")


def run_compose_config(project_root: Path) -> tuple[str, str]:
    result = subprocess.run(
        ["docker", "compose", "config"],
        cwd=project_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "docker compose config failed\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    return result.stdout, result.stderr


def load_compose_config(compose_config_text: str) -> dict[str, Any]:
    data = yaml.safe_load(compose_config_text)

    if not isinstance(data, dict):
        raise ValueError("docker compose config output is not a valid mapping")

    return data


def normalize_environment(environment: Any) -> dict[str, str]:
    if environment is None:
        return {}

    if isinstance(environment, dict):
        return {
            str(key): "" if value is None else str(value)
            for key, value in environment.items()
        }

    if isinstance(environment, list):
        env: dict[str, str] = {}

        for item in environment:
            if not isinstance(item, str):
                continue

            if "=" in item:
                key, value = item.split("=", 1)
                env[key] = value
            else:
                env[item] = ""

        return env

    raise ValueError(f"Unsupported environment format: {environment!r}")


def validate_non_empty_env(
    service_name: str,
    env: dict[str, str],
    required_keys: list[str],
) -> list[str]:
    errors: list[str] = []

    for key in required_keys:
        if key not in env:
            errors.append(f"{service_name}: missing environment key {key}")
            continue

        if env[key].strip() == "":
            errors.append(f"{service_name}: empty environment value {key}")

    return errors


def validate_port_env(service_name: str, env: dict[str, str]) -> list[str]:
    errors: list[str] = []

    for key, value in env.items():
        if not key.endswith("_PORT"):
            continue

        if value.strip() == "":
            errors.append(f"{service_name}: empty port value {key}")
            continue

        try:
            port = int(value)
        except ValueError:
            errors.append(f"{service_name}: invalid port value {key}={value}")
            continue

        if port <= 0 or port > 65535:
            errors.append(f"{service_name}: out-of-range port value {key}={value}")

    return errors


def validate_database_url(service_name: str, key: str, value: str) -> list[str]:
    errors: list[str] = []

    if value.strip() == "":
        return [f"{service_name}: empty database URL {key}"]

    if "${" in value:
        errors.append(f"{service_name}: unresolved variable in {key}={value}")

    suspicious_patterns = [
        r"://:@",
        r"@:",
        r":/$",
        r"://[^@]*@/",
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, value):
            errors.append(f"{service_name}: suspicious database URL {key}={value}")
            break

    parsed = urlparse(value)

    if not parsed.scheme:
        errors.append(f"{service_name}: database URL has no scheme {key}={value}")

    if not parsed.hostname:
        errors.append(f"{service_name}: database URL has no hostname {key}={value}")

    if parsed.port is None:
        errors.append(f"{service_name}: database URL has no valid port {key}={value}")

    if not parsed.path or parsed.path == "/":
        errors.append(f"{service_name}: database URL has no database name {key}={value}")

    return errors


def validate_service_urls(service_name: str, env: dict[str, str]) -> list[str]:
    errors: list[str] = []

    url_keys = [
        "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN",
        "MLFLOW_TRACKING_URI",
    ]

    for key in url_keys:
        if key not in env:
            continue

        errors.extend(validate_database_url(service_name, key, env[key]))

    return errors


def validate_no_blank_default_warnings(stderr_text: str) -> list[str]:
    errors: list[str] = []

    for line in stderr_text.splitlines():
        if "Defaulting to a blank string" in line:
            errors.append(f"compose variable warning: {line}")

    return errors


def validate_compose_config(
    compose_data: dict[str, Any],
    compose_stderr: str,
) -> list[str]:
    errors: list[str] = []

    errors.extend(validate_no_blank_default_warnings(compose_stderr))

    services = compose_data.get("services", {})

    if not isinstance(services, dict):
        return ["compose config has no services mapping"]

    for service_name, required_keys in REQUIRED_SERVICE_ENV.items():
        service = services.get(service_name)

        if not isinstance(service, dict):
            errors.append(f"missing service: {service_name}")
            continue

        env = normalize_environment(service.get("environment"))

        errors.extend(validate_non_empty_env(service_name, env, required_keys))
        errors.extend(validate_port_env(service_name, env))
        errors.extend(validate_service_urls(service_name, env))

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate rendered Docker Compose config."
    )
    parser.add_argument(
        "--project-root",
        default=str(PROJECT_ROOT),
        help="Project root where docker compose config should run.",
    )

    args = parser.parse_args()

    project_root = Path(args.project_root)

    print("")
    print("JobSkill Compose Rendered Config Check")
    print(f"Project root: {project_root}")
    print("")

    try:
        compose_stdout, compose_stderr = run_compose_config(project_root)
        compose_data = load_compose_config(compose_stdout)
        errors = validate_compose_config(compose_data, compose_stderr)

    except Exception as exc:
        fail_check(str(exc))
        sys.exit(1)

    if errors:
        print("[ERRORS]")
        for error in errors:
            print(f"  - {error}")

        print("")
        fail_check("Compose rendered config check failed")
        sys.exit(1)

    print("[OK] docker compose config rendered successfully")
    print("[OK] no blank-string variable warnings detected")
    print("[OK] required service environment values are present")
    print("[OK] database URLs are structurally valid")
    print("")
    pass_check("Compose rendered config check completed")


if __name__ == "__main__":
    main()
