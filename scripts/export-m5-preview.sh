#!/usr/bin/env bash
# 从真实 M4 拍柄 STL 生成 M5 尾段预览网格
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/scripts/.venv-m5"
PY="$VENV/bin/python"
OUT="$ROOT/enclosure/m5/build"
mkdir -p "$OUT"

echo "=== M5 from real handle STLs ==="
if [[ ! -x "$PY" ]]; then
  echo "→ 创建 venv…"
  uv venv "$VENV"
fi
if ! "$PY" -c "import trimesh, manifold3d" 2>/dev/null; then
  echo "→ 安装 trimesh / manifold3d…"
  uv pip install --python "$PY" trimesh manifold3d numpy
fi

"$PY" "$ROOT/scripts/build-m5-from-real-handle.py"

echo ""
echo "预览（必须 HTTP）：  ./scripts/preview-m5.sh"
