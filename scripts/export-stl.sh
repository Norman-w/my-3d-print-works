#!/usr/bin/env bash
# Export paddle shell STLs: four parts + optional assembled front/back halves.
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

export_part() {
  local half="$1"
  local out_file="$2"
  echo "→ 渲染 HALF=${half} …"
  openscad -o "$out_file" -D "HALF=\"${half}\"" "$SCAD"
  if [[ -f "$out_file" ]]; then
    ls -lh "$out_file"
  else
    echo "错误: 未生成 $out_file" >&2
    exit 1
  fi
}

echo "=== SmartPaddle STL 导出（四零件 + 半壳组装）==="
echo "源: $SCAD"
echo "输出: $OUT/"
echo ""

export_part blade_front "$OUT/paddle_blade_front.stl"
export_part blade_back  "$OUT/paddle_blade_back.stl"
export_part handle_front "$OUT/paddle_handle_front.stl"
export_part handle_back  "$OUT/paddle_handle_back.stl"

# 兼容旧流程：前壳 = 拍面前半 + 拍柄前半
export_part front "$OUT/paddle_shell_front.stl"
export_part back  "$OUT/paddle_shell_back.stl"

echo ""
echo "完成。四零件:"
echo "  paddle_blade_front.stl / paddle_blade_back.stl"
echo "  paddle_handle_front.stl / paddle_handle_back.stl"
echo "半壳组装（前后各一片）:"
echo "  paddle_shell_front.stl / paddle_shell_back.stl"
