#!/usr/bin/env bash
# Export the M7-LB1 lightboard variant: solid blade, hollow handle.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENC="$ROOT/enclosure"
OUT="$ENC/stl/lightboard"
SCAD="$ENC/paddle_shell.scad"
QUALITY_MODE="${QUALITY_MODE:-normal}"
SCAD_DEFS=()

ensure_openscad() {
  local app_bin="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
  local app_version
  if [[ ! -x "$app_bin" ]]; then
    echo "错误: 正式导出要求 $app_bin" >&2
    return 1
  fi
  app_version="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' /Applications/OpenSCAD.app/Contents/Info.plist)"
  if [[ "$app_version" != "2026.04.26" ]]; then
    echo "错误: OpenSCAD 版本为 $app_version，正式导出要求 2026.04.26" >&2
    return 1
  fi
  if ! lipo -archs "$app_bin" | tr ' ' '\n' | grep -qx arm64; then
    echo "错误: OpenSCAD 2026.04.26 不含 arm64 架构" >&2
    return 1
  fi
  OPENSCAD_BIN="/usr/bin/arch"
  OPENSCAD_FLAGS="-arm64 $app_bin --backend=Manifold --export-format binstl"
  echo "→ OpenSCAD: 2026.04.26 arm64 + Manifold + binary STL"
}

detect_python() {
  if command -v python3 >/dev/null 2>&1 && python3 -V >/dev/null 2>&1; then
    PYTHON_CMD=(python3)
    return 0
  fi
  if command -v python >/dev/null 2>&1 && python -V >/dev/null 2>&1; then
    PYTHON_CMD=(python)
    return 0
  fi
  return 1
}

setup_quality_mode() {
  case "$QUALITY_MODE" in
    quick)
      SCAD_DEFS+=(-D '$fn=28' -D 'LOFT_SLICES=24')
      echo "→ 渲染质量: quick（预览）"
      ;;
    normal)
      echo "→ 渲染质量: normal（默认）"
      ;;
    *)
      echo "错误: 未知 QUALITY_MODE=$QUALITY_MODE（可选: quick / normal）" >&2
      exit 1
      ;;
  esac
}

ensure_openscad
detect_python || { echo "错误: 需要 Python 3" >&2; exit 1; }
setup_quality_mode

GEN="$ENC/generated/bezier_geometry.scad"
echo "→ 生成 OpenSCAD 腔体/外壳放样 …"
PYTHONUTF8=1 "${PYTHON_CMD[@]}" "$ROOT/scripts/bezier_to_openscad.py"
if [[ ! -f "$GEN" || ! -f "$ENC/generated/profiles.scad" ]]; then
  echo "错误: 未生成 $GEN 或 profiles.scad" >&2
  exit 1
fi

mkdir -p "$OUT/preview" "$OUT/print"
rm -f \
  "$OUT"/paddle_m7_lb1_*.stl \
  "$OUT"/preview/*.stl \
  "$OUT"/print/paddle_m7_lb1_*.stl \
  "$OUT"/print/paddle_m7_lb1_*.3mf \
  "$OUT"/print/print_plates.json \
  "$OUT"/preview/lightboard_manifest.json

export_part() {
  local half="$1"
  local out_file="$2"
  echo "→ 渲染 HALF=${half} …"
  $OPENSCAD_BIN $OPENSCAD_FLAGS -o "$out_file" ${SCAD_DEFS[@]+"${SCAD_DEFS[@]}"} \
    -D "HALF=\"${half}\"" "$SCAD"
  if [[ ! -s "$out_file" ]]; then
    echo "错误: 未生成 $out_file" >&2
    exit 1
  fi
  ls -lh "$out_file"
}

echo "=== SmartPaddle M7-LB1 光板版 STL 完整导出 ==="
echo "源: $SCAD"
echo "输出: $OUT/"

export_part lightboard_skin_front "$OUT/paddle_m7_lb1_layer1_handle_skin_front.stl"
export_part lightboard_core_front "$OUT/paddle_m7_lb1_layer2_core_front.stl"
export_part lightboard_core_back "$OUT/paddle_m7_lb1_layer3_core_back.stl"
export_part lightboard_skin_back "$OUT/paddle_m7_lb1_layer4_handle_skin_back.stl"
export_part lightboard_monolithic_front "$OUT/paddle_m7_lb1_monolithic_front.stl"
export_part lightboard_monolithic_back "$OUT/paddle_m7_lb1_monolithic_back.stl"
export_part lightboard_assembly "$OUT/paddle_m7_lb1_assembly.stl"
export_part lightboard_exploded "$OUT/paddle_m7_lb1_exploded.stl"
export_part m6_fasteners "$OUT/paddle_m7_lb1_fasteners.stl"
export_part m6_fasteners_front "$OUT/preview/fasteners_front.stl"
export_part m6_fasteners_back "$OUT/preview/fasteners_back.stl"
export_part m6_fasteners_through "$OUT/preview/fasteners_through.stl"
export_part m6_fasteners_blade "$OUT/preview/fasteners_blade.stl"
export_part m6_silicone_plugs "$OUT/preview/silicone_plugs.stl"
export_part m6_stage_planform "$OUT/preview/stage_planform.stl"
export_part lightboard_stage_solid_blade "$OUT/preview/stage_solid_blade.stl"
export_part lightboard_stage_handle_cavity "$OUT/preview/stage_handle_cavity.stl"
export_part lightboard_grip_sleeve "$OUT/preview/grip_sleeve.stl"
export_part lightboard_grip_sleeve_print "$OUT/print/paddle_m7_lb1_grip_sleeve_tpu95a.stl"

echo "→ 基于 M7-LB1 四层生成两张刚体打印拼板 …"
"${PYTHON_CMD[@]}" "$ROOT/scripts/build_print_plates.py" \
  --stl-root "$OUT" \
  --prefix paddle_m7_lb1 \
  --metadata "$OUT/print/print_plates.json"

echo "→ 为两张拼板生成 arranged-model 3MF …"
"${PYTHON_CMD[@]}" "$ROOT/scripts/build_3mf_package.py" \
  --stl-root "$OUT" \
  --metadata "$OUT/print/print_plates.json" \
  --plate layers_1_2 \
  --output "$OUT/print/paddle_m7_lb1_print_plate_layers_1_2.3mf"
"${PYTHON_CMD[@]}" "$ROOT/scripts/build_3mf_package.py" \
  --stl-root "$OUT" \
  --metadata "$OUT/print/print_plates.json" \
  --plate layers_3_4 \
  --output "$OUT/print/paddle_m7_lb1_print_plate_layers_3_4.3mf"
"${PYTHON_CMD[@]}" "$ROOT/scripts/build_3mf_package.py" \
  --stl-root "$OUT" \
  --metadata "$OUT/print/print_plates.json" \
  --single-source "print/paddle_m7_lb1_grip_sleeve_tpu95a.stl" \
  --label "M7-LB1 TPU95A 拍柄把套" \
  --output "$OUT/print/paddle_m7_lb1_grip_sleeve_tpu95a.3mf"

echo "→ 写入 M7-LB1 光板工艺 manifest …"
"${PYTHON_CMD[@]}" "$ROOT/scripts/write_lightboard_manifest.py"

echo "完成：M7-LB1 光板版 SCAD → STL → 3MF"
