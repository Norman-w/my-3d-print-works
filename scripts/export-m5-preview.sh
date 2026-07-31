#!/usr/bin/env bash
# 已废弃独立 M5 管线 —— 转调完整导出（含 Step6 尾板干涉）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "export-m5-preview.sh 已并入 ./scripts/export-stl.sh（含 Step6）"
exec "$ROOT/scripts/export-stl.sh" "$@"
