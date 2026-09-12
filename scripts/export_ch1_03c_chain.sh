#!/usr/bin/env bash
# Export CH1 03C OpenSCAD chain to STL, PNG, and the web preview folder.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAD_DIR="${PROJECT_ROOT}/cad/openscad"
SCAD_FILE="ch1_03c_roller_chain.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
OUT_STL="${PROJECT_ROOT}/output/3d-print"
OUT_PNG="${PROJECT_ROOT}/output/previews"
WEB_STL="${PROJECT_ROOT}/web/assets/stl"
WEB_PNG="${PROJECT_ROOT}/web/assets/previews"
INSPECT_PY="${HOME}/.cursor/skills/openscad-stl-print/scripts/inspect_stl.py"

# ===== 分区：模型/类型 =====
# 导出零件名：plates / rollers / pins / assembly

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

need_bin() {
    [[ -x "$OPENSCAD_BIN" ]] || die "找不到 OpenSCAD: $OPENSCAD_BIN"
}

export_stl() {
    local part="$1"
    local dest="$2"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ STL PART=${part} → ${dest}"
    (
        cd "$SCAD_DIR"
        "$OPENSCAD_BIN" \
            -D "PART=\"${part}\"" \
            -o "$tmp" \
            "$SCAD_FILE"
    )
    [[ -s "$tmp" ]] || die "空 STL: $dest"
    mv -f "$tmp" "$dest"
}

export_png() {
    local name="$1"
    shift
    local dest="${OUT_PNG}/${name}.png"
    echo "→ PNG ${name}"
    (
        cd "$SCAD_DIR"
        "$OPENSCAD_BIN" \
            --preview \
            --imgsize=1600,1000 \
            --colorscheme="Tomorrow Night" \
            "$@" \
            -o "$dest" \
            "$SCAD_FILE"
    )
    [[ -s "$dest" ]] || die "空 PNG: $dest"
}

write_manifest() {
    cat > "${WEB_STL}/ch1_03c_manifest.json" <<'EOF'
{
  "title": "CH1 03C 单排滚子链条",
  "units": "mm",
  "source": "docs/parts/CH1-03C-roller-chain.md",
  "sku": "单排03C-1X210L长1米",
  "pitchMm": 4.7625,
  "previewLinks": 20,
  "skuLinks": 210,
  "mode": "loop",
  "note": "预览为 20 节闭环包络，不是 210 节实物全长。外购件，不要当 FDM 打印件。",
  "models": [
    {"name": "plates", "displayName": "内外链板", "file": "ch1_03c_plates.stl", "color": "#8A919C", "visible": true},
    {"name": "rollers", "displayName": "滚子", "file": "ch1_03c_rollers.stl", "color": "#E8EDF2", "visible": true},
    {"name": "pins", "displayName": "销轴/轴套", "file": "ch1_03c_pins.stl", "color": "#B08D57", "visible": true}
  ]
}
EOF
}

# ===== 分区：公开 API =====
need_bin
mkdir -p "$OUT_STL" "$OUT_PNG" "$WEB_STL" "$WEB_PNG"

export_stl plates "${OUT_STL}/ch1_03c_plates.stl"
export_stl rollers "${OUT_STL}/ch1_03c_rollers.stl"
export_stl pins "${OUT_STL}/ch1_03c_pins.stl"
export_stl assembly "${OUT_STL}/ch1_03c_chain.stl"

export_png ch1_03c_iso --viewall --autocenter --projection=p --camera=0,0,0,55,0,35,72
export_png ch1_03c_top --viewall --autocenter --projection=o --camera=0,0,0,0,0,0,56
export_png ch1_03c_front --viewall --autocenter --projection=o --camera=0,0,0,90,0,0,56

cp -f "${OUT_STL}/ch1_03c_"*.stl "$WEB_STL/"
cp -f "${OUT_PNG}/ch1_03c_"*.png "$WEB_PNG/"
write_manifest

# ===== 分区：业务逻辑 =====
if [[ -f "$INSPECT_PY" ]]; then
    python3 "$INSPECT_PY" "${OUT_STL}/ch1_03c_chain.stl"
else
    echo "跳过 STL 检查：找不到 $INSPECT_PY"
fi

echo "完成:"
echo "  STL  ${OUT_STL}/ch1_03c_chain.stl"
echo "  预览 ${OUT_PNG}/ch1_03c_iso.png"
echo "  Web  ${PROJECT_ROOT}/web/chain-viewer.html"

# ===== 分区：方法/工具 =====
# OpenSCAD 路径可用 OPENSCAD_BIN 覆盖。
