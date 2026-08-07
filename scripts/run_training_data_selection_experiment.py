from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_MODES = "full,recent,recent_plus_history_sample"
REPORT_PATH = Path(
    os.getenv(
        "TRAINING_DATA_SELECTION_EXPERIMENT_REPORT_PATH",
        "reports/latest_training_data_selection_experiment_report.md",
    )
)

TRANSIENT_FAILURE_PATTERNS = (
    "Temporary failure in name resolution",
    "could not translate host name",
    "server closed the connection unexpectedly",
    "connection already closed",
    "SSL SYSCALL error: EOF detected",
    "OperationalError",
)


@dataclass(frozen=True)
class ExperimentResult:
    mode: str
    status: str
    returncode: int
    duration_seconds: float | None
    accuracy: float | None
    f1_weighted: float | None
    requested_mode: str | None
    applied_mode: str | None
    before_rows: int | None
    after_rows: int | None
    recent_rows: int | None
    historical_rows: int | None
    model_path: str
    stdout_tail: str
    stderr_tail: str
    attempt: int
    transient_failure: bool


def getenv_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value == "":
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def getenv_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)

    if raw_value is None or raw_value == "":
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer. value={raw_value}") from exc


def parse_float(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text)

    if not match:
        return None

    return float(match.group(1))


def parse_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text)

    if not match:
        return None

    return int(match.group(1))


def parse_str(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)

    if not match:
        return None

    return match.group(1).strip()


def tail_text(text: str, max_lines: int = 80) -> str:
    lines = text.strip().splitlines()

    if len(lines) <= max_lines:
        return "\n".join(lines)

    return "\n".join(lines[-max_lines:])


def is_transient_failure(stdout: str, stderr: str) -> bool:
    combined = f"{stdout}\n{stderr}"

    return any(pattern in combined for pattern in TRANSIENT_FAILURE_PATTERNS)


def wait_for_postgres_dns(project_root: Path) -> None:
    command = ["getent", "hosts", "postgres"]

    max_attempts = getenv_int("TRAINING_DATA_SELECTION_DNS_RETRIES", 5)
    sleep_seconds = getenv_int("TRAINING_DATA_SELECTION_DNS_RETRY_SLEEP_SECONDS", 2)

    for attempt in range(1, max_attempts + 1):
        completed = subprocess.run(
            command,
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if completed.returncode == 0:
            return

        if attempt < max_attempts:
            time.sleep(sleep_seconds)

    raise RuntimeError(
        "postgres hostname could not be resolved inside the container. "
        f"stdout={completed.stdout.strip()} stderr={completed.stderr.strip()}"
    )


def run_one_mode_once(mode: str, project_root: Path, attempt: int) -> ExperimentResult:
    started_at = datetime.now()

    model_path = (
        Path("models")
        / "experiments"
        / f"job_classifier_{mode}_{started_at.strftime('%Y%m%d_%H%M%S')}_attempt{attempt}.pkl"
    )
    (project_root / model_path).parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["TRAINING_DATA_MODE"] = mode
    env["MODEL_PATH"] = str(model_path)

    env.setdefault("TRAINING_RECENT_DAYS", os.getenv("TRAINING_RECENT_DAYS", "90"))
    env.setdefault(
        "TRAINING_HISTORY_SAMPLE_ROWS_PER_CLASS",
        os.getenv("TRAINING_HISTORY_SAMPLE_ROWS_PER_CLASS", "100"),
    )

    command = [sys.executable, "src/training/train_baseline.py"]

    completed = subprocess.run(
        command,
        cwd=project_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    combined_output = completed.stdout + "\n" + completed.stderr
    transient_failure = completed.returncode != 0 and is_transient_failure(
        completed.stdout,
        completed.stderr,
    )

    return ExperimentResult(
        mode=mode,
        status="PASS" if completed.returncode == 0 else "FAIL",
        returncode=completed.returncode,
        duration_seconds=parse_float(
            r"training_duration_seconds:\s*([0-9.]+)",
            combined_output,
        ),
        accuracy=parse_float(r"accuracy:\s*([0-9.]+)", combined_output),
        f1_weighted=parse_float(r"f1_weighted:\s*([0-9.]+)", combined_output),
        requested_mode=parse_str(r"requested_mode:\s*([A-Za-z0-9_+-]+)", combined_output),
        applied_mode=parse_str(r"applied_mode:\s*([A-Za-z0-9_+-]+)", combined_output),
        before_rows=parse_int(r"before_rows:\s*([0-9]+)", combined_output),
        after_rows=parse_int(r"after_rows:\s*([0-9]+)", combined_output),
        recent_rows=parse_int(r"recent_rows:\s*([0-9]+)", combined_output),
        historical_rows=parse_int(r"historical_rows:\s*([0-9]+)", combined_output),
        model_path=str(model_path),
        stdout_tail=tail_text(completed.stdout),
        stderr_tail=tail_text(completed.stderr),
        attempt=attempt,
        transient_failure=transient_failure,
    )


def run_one_mode(mode: str, project_root: Path) -> ExperimentResult:
    max_attempts = getenv_int("TRAINING_DATA_SELECTION_EXPERIMENT_RETRIES", 3)
    sleep_seconds = getenv_int(
        "TRAINING_DATA_SELECTION_EXPERIMENT_RETRY_SLEEP_SECONDS",
        5,
    )

    last_result: ExperimentResult | None = None

    for attempt in range(1, max_attempts + 1):
        wait_for_postgres_dns(project_root)
        result = run_one_mode_once(mode, project_root, attempt)
        last_result = result

        if result.status == "PASS":
            return result

        if not result.transient_failure:
            return result

        if attempt < max_attempts:
            print(
                f"[RETRY] mode={mode} attempt={attempt}/{max_attempts} "
                "failed with transient DB/DNS error. Retrying..."
            )
            time.sleep(sleep_seconds)

    if last_result is None:
        raise RuntimeError(f"mode={mode} did not run.")

    return last_result


def format_value(value: object) -> str:
    if value is None:
        return ""

    if isinstance(value, float):
        return f"{value:.4f}"

    return str(value)


def markdown_table(headers: list[str], rows: list[dict[str, object]]) -> str:
    if not rows:
        return "_No rows._"

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for row in rows:
        values = [format_value(row.get(header)) for header in headers]
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def build_recommendation(results: list[ExperimentResult]) -> str:
    successful_results = [result for result in results if result.status == "PASS"]

    if not successful_results:
        return "- 모든 training data selection experiment가 실패했습니다. stdout/stderr를 확인해야 합니다."

    full_result = next(
        (result for result in successful_results if result.mode == "full"),
        None,
    )

    best_f1_result = max(
        successful_results,
        key=lambda result: result.f1_weighted if result.f1_weighted is not None else -1,
    )

    fastest_result = min(
        successful_results,
        key=lambda result: result.duration_seconds
        if result.duration_seconds is not None
        else float("inf"),
    )

    lines = []

    if full_result is None:
        lines.append("- full mode 기준 결과가 없어 운영 기준 비교가 제한됩니다.")
    else:
        lines.append(
            "- full mode는 현재 운영 기준 baseline입니다. "
            "다른 mode는 이 baseline과 성능/비용을 비교하는 shadow experiment로 해석합니다."
        )

    lines.append(
        f"- 가장 높은 weighted F1 mode: `{best_f1_result.mode}` "
        f"(f1={format_value(best_f1_result.f1_weighted)})"
    )
    lines.append(
        f"- 가장 빠른 training mode: `{fastest_result.mode}` "
        f"(duration={format_value(fastest_result.duration_seconds)}s)"
    )

    if (
        full_result is not None
        and best_f1_result.mode != "full"
        and best_f1_result.f1_weighted is not None
        and full_result.f1_weighted is not None
        and best_f1_result.f1_weighted >= full_result.f1_weighted
    ):
        lines.append(
            "- full이 아닌 mode가 full과 같거나 더 좋은 F1을 보였습니다. "
            "반복 실험 후 window/sampling retrain 후보로 검토할 수 있습니다."
        )
    else:
        lines.append(
            "- 현재는 full retrain을 기준 경로로 유지하고, selection mode는 비교 실험으로 유지하는 것이 안전합니다."
        )

    return "\n".join(lines)


def write_report(results: list[ExperimentResult]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = [
        {
            "mode": result.mode,
            "status": result.status,
            "attempt": result.attempt,
            "transient_failure": result.transient_failure,
            "requested_mode": result.requested_mode,
            "applied_mode": result.applied_mode,
            "before_rows": result.before_rows,
            "after_rows": result.after_rows,
            "recent_rows": result.recent_rows,
            "historical_rows": result.historical_rows,
            "accuracy": result.accuracy,
            "f1_weighted": result.f1_weighted,
            "duration_seconds": result.duration_seconds,
            "model_path": result.model_path,
        }
        for result in results
    ]

    lines = [
        "# JobSkill Training Data Selection Experiment Report",
        "",
        f"- Generated at: `{generated_at}`",
        "",
        "## Summary Recommendation",
        "",
        build_recommendation(results),
        "",
        "## Experiment Results",
        "",
        markdown_table(
            [
                "mode",
                "status",
                "attempt",
                "transient_failure",
                "requested_mode",
                "applied_mode",
                "before_rows",
                "after_rows",
                "recent_rows",
                "historical_rows",
                "accuracy",
                "f1_weighted",
                "duration_seconds",
                "model_path",
            ],
            rows,
        ),
        "",
        "## Interpretation",
        "",
        "- `full`은 현재 운영 기준 baseline입니다.",
        "- `recent`는 최근 window만으로 성능과 비용이 유지되는지 확인하는 실험입니다.",
        "- `recent_plus_history_sample`은 최근 데이터 전체와 과거 class-balanced sample을 결합하는 실험입니다.",
        "- 이 스크립트는 promoted model을 자동 변경하지 않습니다.",
        "- 실험 결과가 좋아도 promotion 정책은 별도 검증 후 변경해야 합니다.",
        "",
        "## Follow-up Commands",
        "",
        "```bash",
        "make training-data-selection-experiment",
        "cat reports/latest_training_data_selection_experiment_report.md",
        "make training-cost-report",
        "make ops-evidence-bundle",
        "make ops-evidence-check",
        "```",
        "",
        "## Failed Run Details",
        "",
    ]

    failed_results = [result for result in results if result.status != "PASS"]

    if not failed_results:
        lines.append("_No failed runs._")
    else:
        for result in failed_results:
            lines.extend(
                [
                    f"### {result.mode}",
                    "",
                    f"- returncode: `{result.returncode}`",
                    f"- attempt: `{result.attempt}`",
                    f"- transient_failure: `{result.transient_failure}`",
                    "",
                    "stdout tail:",
                    "",
                    "```text",
                    result.stdout_tail,
                    "```",
                    "",
                    "stderr tail:",
                    "",
                    "```text",
                    result.stderr_tail,
                    "```",
                    "",
                ]
            )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    raw_modes = os.getenv("TRAINING_DATA_EXPERIMENT_MODES", DEFAULT_MODES)
    modes = [mode.strip() for mode in raw_modes.split(",") if mode.strip()]

    if not modes:
        raise ValueError("TRAINING_DATA_EXPERIMENT_MODES produced no modes.")

    print("Training data selection experiment")
    print("==================================")
    print(f"modes={modes}")
    print(f"report_path={REPORT_PATH}")
    print("")

    results: list[ExperimentResult] = []

    for mode in modes:
        print(f"[RUN] TRAINING_DATA_MODE={mode}")
        result = run_one_mode(mode, project_root)
        results.append(result)
        print(
            f"[{result.status}] mode={mode} "
            f"attempt={result.attempt} "
            f"transient_failure={result.transient_failure} "
            f"accuracy={format_value(result.accuracy)} "
            f"f1_weighted={format_value(result.f1_weighted)} "
            f"duration_seconds={format_value(result.duration_seconds)} "
            f"after_rows={format_value(result.after_rows)}"
        )
        print("")

    write_report(results)

    print("Training data selection experiment report generated")
    print(f"path={REPORT_PATH}")

    strict = getenv_bool(
        "TRAINING_DATA_SELECTION_EXPERIMENT_STRICT",
        True,
    )
    failed_count = sum(result.status != "PASS" for result in results)

    if failed_count > 0:
        print(
            f"Training data selection experiment completed with "
            f"{failed_count} failed mode(s)."
        )

    if strict and failed_count > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
