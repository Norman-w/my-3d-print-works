#!/usr/bin/env bash
# STL → 二维正交视图 + 尺寸分析（自动创建 venv）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/scripts/.venv-analyze"
REQ="$ROOT/scripts/requirements-analyze.txt"

if [[ ! -d "$VENV" ]]; then
  echo "创建虚拟环境 $VENV …"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -U pip
  "$VENV/bin/pip" install -q -r "$REQ"
fi

"$VENV/bin/python" "$ROOT/scripts/analyze_stl_views.py" "$@"
stl_exit=$?
"$VENV/bin/python" "$ROOT/scripts/analyze_bezier_views.py" "$@" || true
exit $stl_exit
