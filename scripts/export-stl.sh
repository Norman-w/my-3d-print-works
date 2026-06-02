#!/usr/bin/env bash
# Export paddle_shell front/back STLs for slicing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENC="$ROOT/enclosure"
OUT="$ENC/stl"
SCAD="$ENC/paddle_shell.scad"

if ! command -v openscad >/dev/null 2>&1; then
  echo "错误: 未找到 openscad。请安装 OpenSCAD 并加入 PATH。" >&2
  exit 1
fi

mkdir -p "$OUT"
GEN="$ENC/generated/bezier_geometry.scad"

echo "→ 生成 OpenSCAD 腔体/外壳放样 …"
if command -v python3 >/dev/null 2>&1; then
  python3 "$ROOT/scripts/bezier_to_openscad.py" || {
    echo "错误: bezier_to_openscad.py 失败" >&2
    exit 1
  }
else
  echo "错误: 需要 python3 运行 bezier_to_openscad.py" >&2
  exit 1
fi
if [[ ! -f "$GEN" ]] || [[ ! -f "$ENC/generated/profiles.scad" ]]; then
  echo "错误: 未生成 $GEN 或 profiles.scad" >&2
  exit 1
fi
echo ""

export_half() {
  local half="$1"
  local out_file="$OUT/paddle_shell_${half}.stl"
  echo "→ 渲染 HALF=${half} …（可能需要几分钟）"
  openscad -o "$out_file" -D "HALF=\"${half}\"" "$SCAD"
  if [[ -f "$out_file" ]]; then
    ls -lh "$out_file"
  else
    echo "错误: 未生成 $out_file" >&2
    exit 1
  fi
}

echo "=== SmartPaddle STL 导出 ==="
echo "源: $SCAD"
echo "输出: $OUT/"
echo ""

export_half front
export_half back

echo ""
echo "完成。下一步:"
echo "  1. 用 Bambu Studio / PrusaSlicer 打开上述两个 STL"
echo "  2. 按 docs/print-prep.md 设置 PETG、摆放、支撑"
echo "  3. 按 docs/visual-checklist.md 截图核对"
