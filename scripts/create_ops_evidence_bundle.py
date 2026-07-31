from __future__ import annotations

import argparse
import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path("reports/ops_evidence")
DEFAULT_BUNDLE_PREFIX = "jobskill_ops_evidence"


REQUIRED_PATHS = [
    Path("README.md"),
    Path("docs/README_SUMMARY.md"),
    Path("docs/QUICKSTART.md"),
    Path("reports/latest_ops_validation_report.md"),
]

OPTIONAL_PATHS = [
    Path("docs/README_FULL.md"),
    Path("reports/latest_pipeline_report.md"),
    Path("reports/latest_model_card.md"),
    Path("reports/latest_incident_response_report.md"),
    Path("monitoring/metrics_contract.yml"),
    Path("monitoring/prometheus/prometheus.yml"),
    Path("monitoring/prometheus/rules/jobskill_alert_rules.yml"),
    Path("monitoring/prometheus/tests/jobskill_alert_rules.test.yml"),
    Path("monitoring/alertmanager/alertmanager.yml"),
    Path("docker-compose.yml"),
    Path("Makefile"),
]

OPTIONAL_DIRS = [
    Path("docs/runbooks"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an ops evidence bundle for the JobSkill MLOps project.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where the evidence bundle zip will be created.",
    )
    parser.add_argument(
        "--allow-missing-required",
        action="store_true",
        help="Create the bundle even when required evidence files are missing.",
    )
    parser.add_argument(
        "--include-runtime-logs",
        action="store_true",
        help="Include local airflow_logs directory if it exists. This can make the bundle large.",
    )
    return parser.parse_args()


def normalize_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def add_file_to_zip(zipf: zipfile.ZipFile, path: Path, manifest: list[dict[str, str]]) -> None:
    archive_name = normalize_path(path)

    zipf.write(path, archive_name)
    manifest.append(
        {
            "type": "file",
            "source": normalize_path(path),
            "archive_path": archive_name,
        }
    )


def add_directory_to_zip(zipf: zipfile.ZipFile, directory: Path, manifest: list[dict[str, str]]) -> None:
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            add_file_to_zip(zipf, path, manifest)


def collect_missing_required() -> list[Path]:
    return [path for path in REQUIRED_PATHS if not path.exists()]


def build_summary(
    bundle_name: str,
    manifest: list[dict[str, str]],
    missing_required: list[Path],
    skipped_optional: list[Path],
) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# JobSkill MLOps Ops Evidence Bundle",
        "",
        f"- Bundle: `{bundle_name}`",
        f"- Generated at: `{generated_at}`",
        "",
        "## Purpose",
        "",
        "This bundle collects the latest local operations evidence for the JobSkill MLOps project.",
        "It is intended for portfolio review, troubleshooting, handoff, and regression tracking.",
        "",
        "## Included Evidence",
        "",
    ]

    for item in manifest:
        lines.append(f"- `{item['archive_path']}`")

    lines.extend(
        [
            "",
            "## Missing Required Evidence",
            "",
        ]
    )

    if missing_required:
        for path in missing_required:
            lines.append(f"- `{normalize_path(path)}`")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Skipped Optional Evidence",
            "",
        ]
    )

    if skipped_optional:
        for path in skipped_optional:
            lines.append(f"- `{normalize_path(path)}`")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Recommended Verification Commands",
            "",
            "```bash",
            "make ops-static-check",
            "make smoke",
            "make ops-check",
            "make ops-report",
            "make ops-evidence-bundle",
            "```",
            "",
        ]
    )

    return "\n".join(lines)


def write_manifest_files(
    working_dir: Path,
    bundle_name: str,
    manifest: list[dict[str, str]],
    missing_required: list[Path],
    skipped_optional: list[Path],
) -> list[Path]:
    working_dir.mkdir(parents=True, exist_ok=True)

    summary_path = working_dir / "OPS_EVIDENCE_BUNDLE.md"
    summary_path.write_text(
        build_summary(bundle_name, manifest, missing_required, skipped_optional),
        encoding="utf-8",
    )

    manifest_path = working_dir / "ops_evidence_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "bundle": bundle_name,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "included": manifest,
                "missing_required": [normalize_path(path) for path in missing_required],
                "skipped_optional": [normalize_path(path) for path in skipped_optional],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return [summary_path, manifest_path]


def create_bundle(args: argparse.Namespace) -> Path:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_name = f"{DEFAULT_BUNDLE_PREFIX}_{timestamp}.zip"
    bundle_path = output_dir / bundle_name

    missing_required = collect_missing_required()

    if missing_required and not args.allow_missing_required:
        missing = "\n".join(f"- {path}" for path in missing_required)
        raise SystemExit(
            "Required evidence files are missing. Generate them first or use "
            "--allow-missing-required.\n"
            f"{missing}"
        )

    manifest: list[dict[str, str]] = []
    skipped_optional: list[Path] = []

    temp_manifest_dir = output_dir / ".bundle_manifest_tmp"
    if temp_manifest_dir.exists():
        shutil.rmtree(temp_manifest_dir)

    try:
        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            for path in REQUIRED_PATHS:
                if path.exists():
                    add_file_to_zip(zipf, path, manifest)

            for path in OPTIONAL_PATHS:
                if path.exists():
                    add_file_to_zip(zipf, path, manifest)
                else:
                    skipped_optional.append(path)

            for directory in OPTIONAL_DIRS:
                if directory.exists():
                    add_directory_to_zip(zipf, directory, manifest)
                else:
                    skipped_optional.append(directory)

            if args.include_runtime_logs:
                runtime_logs_dir = Path("airflow_logs")
                if runtime_logs_dir.exists():
                    add_directory_to_zip(zipf, runtime_logs_dir, manifest)
                else:
                    skipped_optional.append(runtime_logs_dir)

            manifest_files = write_manifest_files(
                temp_manifest_dir,
                bundle_name,
                manifest,
                missing_required,
                skipped_optional,
            )
            for manifest_file in manifest_files:
                archive_name = manifest_file.name
                zipf.write(manifest_file, archive_name)
    finally:
        if temp_manifest_dir.exists():
            shutil.rmtree(temp_manifest_dir)

    return bundle_path


def main() -> None:
    args = parse_args()
    bundle_path = create_bundle(args)

    print("Ops evidence bundle created")
    print(f"path={bundle_path}")


if __name__ == "__main__":
    main()

