#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
GENERATOR="${PROJECT_DIR}/tools/assembly_package/generate.py"

if [[ ! -f "${GENERATOR}" ]]; then
  echo "SmartPaddle assembly-package generator not found: ${GENERATOR}" >&2
  exit 2
fi

# SMARTPADDLE_PYTHON is an optional, task-specific override. The default path
# keeps the one-line command usable in normal development environments.
PYTHON_BIN="${SMARTPADDLE_PYTHON:-python3}"
if "${PYTHON_BIN}" -c 'import reportlab' >/dev/null 2>&1; then
  exec "${PYTHON_BIN}" "${GENERATOR}" --qa "$@"
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run --quiet --with reportlab --with pypdf --with pillow \
    python "${GENERATOR}" --qa "$@" \
    2> >(grep -v '^WARN Skipping file for' >&2)
fi

echo "Python package 'reportlab' is required." >&2
echo "Install it with: python3 -m pip install reportlab pypdf pillow" >&2
exit 2
