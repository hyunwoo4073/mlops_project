from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path


DEFAULT_BUNDLE_DIR = Path("reports/ops_evidence")

CORE_REQUIRED_FILES = [
    "README.md",
    "docs/README_SUMMARY.md",
    "docs/QUICKSTART.md",
    "reports/latest_ops_validation_report.md",
    "OPS_EVIDENCE_BUNDLE.md",
    "ops_evidence_manifest.json",
]

RECOMMENDED_FILES = [
    "docs/README_FULL.md",
    "monitoring/metrics_contract.yml",
    "monitoring/prometheus/prometheus.yml",
    "monitoring/prometheus/rules/jobskill_alert_rules.yml",
    "monitoring/prometheus/tests/jobskill_alert_rules.test.yml",
    "monitoring/alertmanager/alertmanager.yml",
    "docker-compose.yml",
    "Makefile",
]


@dataclass(frozen=True)
class BundleCheckResult:
    bundle_path: Path
    total_files: int
    missing_required: list[str]
    missing_recommended: list[str]
    has_runbook: bool
    manifest_ok: bool
    manifest_error: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the latest JobSkill ops evidence bundle.",
    )
    parser.add_argument(
        "--bundle-path",
        default=None,
        help="Specific evidence bundle zip path. If omitted, the latest zip in reports/ops_evidence is used.",
    )
    parser.add_argument(
        "--bundle-dir",
        default=str(DEFAULT_BUNDLE_DIR),
        help="Directory to search for evidence bundle zip files.",
    )
    parser.add_argument(
        "--strict-recommended",
        action="store_true",
        help="Fail when recommended evidence files are missing.",
    )
    parser.add_argument(
        "--allow-missing-runbooks",
        action="store_true",
        help="Do not fail when docs/runbooks files are not included.",
    )
    return parser.parse_args()


def find_latest_bundle(bundle_dir: Path) -> Path:
    candidates = sorted(
        bundle_dir.glob("jobskill_ops_evidence_*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        raise SystemExit(f"No evidence bundle zip files found in {bundle_dir}")

    return candidates[0]


def load_manifest(zipf: zipfile.ZipFile) -> tuple[bool, str | None]:
    try:
        raw_manifest = zipf.read("ops_evidence_manifest.json")
    except KeyError:
        return False, "ops_evidence_manifest.json is missing"

    try:
        manifest = json.loads(raw_manifest.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"manifest JSON is invalid: {exc}"

    required_keys = {
        "bundle",
        "generated_at",
        "included",
        "missing_required",
        "skipped_optional",
    }
    missing_keys = required_keys - set(manifest)

    if missing_keys:
        return False, f"manifest is missing keys: {', '.join(sorted(missing_keys))}"

    if not isinstance(manifest.get("included"), list):
        return False, "manifest field 'included' must be a list"

    return True, None


def check_bundle(
    bundle_path: Path,
    strict_recommended: bool,
    allow_missing_runbooks: bool,
) -> BundleCheckResult:
    if not bundle_path.exists():
        raise SystemExit(f"Evidence bundle does not exist: {bundle_path}")

    if not zipfile.is_zipfile(bundle_path):
        raise SystemExit(f"Evidence bundle is not a valid zip file: {bundle_path}")

    with zipfile.ZipFile(bundle_path, "r") as zipf:
        names = set(zipf.namelist())

        missing_required = [
            archive_path
            for archive_path in CORE_REQUIRED_FILES
            if archive_path not in names
        ]

        missing_recommended = [
            archive_path
            for archive_path in RECOMMENDED_FILES
            if archive_path not in names
        ]

        has_runbook = any(
            name.startswith("docs/runbooks/") and name.endswith(".md")
            for name in names
        )

        if not allow_missing_runbooks and not has_runbook:
            missing_required.append("docs/runbooks/*.md")

        manifest_ok, manifest_error = load_manifest(zipf)

        if not manifest_ok:
            missing_required.append("valid ops_evidence_manifest.json")

        if strict_recommended and missing_recommended:
            missing_required.extend(missing_recommended)

        return BundleCheckResult(
            bundle_path=bundle_path,
            total_files=len(names),
            missing_required=missing_required,
            missing_recommended=missing_recommended,
            has_runbook=has_runbook,
            manifest_ok=manifest_ok,
            manifest_error=manifest_error,
        )


def print_result(result: BundleCheckResult, strict_recommended: bool) -> None:
    print("")
    print("Ops Evidence Bundle Check")
    print("=========================")
    print(f"bundle_path={result.bundle_path}")
    print(f"total_files={result.total_files}")
    print(f"manifest_ok={result.manifest_ok}")
    print(f"has_runbook={result.has_runbook}")

    if result.manifest_error:
        print(f"manifest_error={result.manifest_error}")

    print("")
    print("Core required files")
    print("-------------------")
    if result.missing_required:
        for item in result.missing_required:
            print(f"MISSING {item}")
    else:
        print("OK")

    print("")
    print("Recommended files")
    print("-----------------")
    if result.missing_recommended:
        for item in result.missing_recommended:
            status = "MISSING" if strict_recommended else "WARN"
            print(f"{status} {item}")
    else:
        print("OK")


def main() -> None:
    args = parse_args()

    bundle_path = (
        Path(args.bundle_path)
        if args.bundle_path
        else find_latest_bundle(Path(args.bundle_dir))
    )

    result = check_bundle(
        bundle_path=bundle_path,
        strict_recommended=args.strict_recommended,
        allow_missing_runbooks=args.allow_missing_runbooks,
    )

    print_result(result, strict_recommended=args.strict_recommended)

    if result.missing_required:
        raise SystemExit(1)

    print("")
    print("PASS: Ops evidence bundle check completed.")


if __name__ == "__main__":
    main()

