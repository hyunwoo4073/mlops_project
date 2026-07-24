#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Repository Artifact Guard"
echo "========================="
echo ""

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[FAIL] Not inside a Git repository."
    exit 1
fi

FORBIDDEN_PATTERNS=(
    "^mlartifacts/"
    "^models/"
    "^data/"
    "^airflow_logs/"
    "^\\.env$"
    "^\\.env\\."
    "^\\.secrets/"
    "^simple_auth_manager_passwords\\.json$"
    "^reports/latest_model_card\\.md$"
    "^reports/model_cards/"
    "__pycache__/"
    "\\.pyc$"
    "^\\.pytest_cache/"
    "^\\.ruff_cache/"
    "^\\.mypy_cache/"
)

ALLOW_PATTERNS=(
    "^\\.env\\.example$"
    "^\\.secrets\\.example/"
    "^docs/"
)

found=0

check_file() {
    local file_path="$1"
    local source_name="$2"

    for allow_pattern in "${ALLOW_PATTERNS[@]}"; do
        if [[ "$file_path" =~ $allow_pattern ]]; then
            return 0
        fi
    done

    for forbidden_pattern in "${FORBIDDEN_PATTERNS[@]}"; do
        if [[ "$file_path" =~ $forbidden_pattern ]]; then
            echo "[FAIL] Forbidden generated/runtime file detected from ${source_name}: ${file_path}"
            found=1
            return 0
        fi
    done
}

echo "[1/3] Checking tracked files..."
while IFS= read -r file_path; do
    check_file "$file_path" "tracked files"
done < <(git ls-files)

echo "[2/3] Checking staged files..."
while IFS= read -r file_path; do
    check_file "$file_path" "staged files"
done < <(git diff --cached --name-only --diff-filter=ACMRT)

echo "[3/3] Checking untracked files..."
while IFS= read -r file_path; do
    check_file "$file_path" "untracked files"
done < <(git ls-files --others --exclude-standard)

echo ""

if [[ "$found" -ne 0 ]]; then
    cat <<'EOF'
[FAIL] Repository artifact guard failed.

Generated/runtime files should not be committed.

Recommended fixes:

  git rm -r --cached mlartifacts models data airflow_logs 2>/dev/null || true
  git rm --cached reports/latest_model_card.md 2>/dev/null || true
  git rm -r --cached reports/model_cards 2>/dev/null || true

Then update .gitignore and run:

  make repo-artifact-check

EOF
    exit 1
fi

echo "[PASS] No forbidden generated/runtime artifacts detected."
