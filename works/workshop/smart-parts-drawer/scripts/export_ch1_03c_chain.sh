#!/usr/bin/env bash
# Export CH1 03C OpenSCAD chain to STL, PNG, and the web preview folder.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/resolve_preview_tools.sh"
SCAD_DIR="${PROJECT_ROOT}/cad/openscad"
SCAD_FILE="ch1_03c_roller_chain.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
OUT_STL="${PROJECT_ROOT}/output/3d-print"
OUT_PNG="${PROJECT_ROOT}/output/previews"
WEB_STL="${PROJECT_ROOT}/web/assets/stl"
WEB_PNG="${PROJECT_ROOT}/web/assets/previews"

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
    local quality="${3:-3}"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ STL PART=${part} QUALITY=${quality} → ${dest}"
    (
        cd "$SCAD_DIR"
        "$OPENSCAD_BIN" \
            -D "PART=\"${part}\"" \
            -D "QUALITY=${quality}" \
            -o "$tmp" \
            "$SCAD_FILE"
    )
    [[ -s "$tmp" ]] || die "空 STL: $dest"
    mv -f "$tmp" "$dest"
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
  "defaultQuality": 2,
  "note": "预览为 20 节闭环包络，不是 210 节实物全长。外购件，不要当 FDM 打印件。拖条改精度后会重新加载对应 STL。",
  "qualities": [
    {"level": 1, "label": "最快", "hint": "草稿，加载最快", "fa": 22, "fs": 0.70, "dir": "q1"},
    {"level": 2, "label": "较快", "hint": "预览默认", "fa": 14, "fs": 0.40, "dir": "q2"},
    {"level": 3, "label": "标准", "hint": "平衡", "fa": 8, "fs": 0.22, "dir": "q3"},
    {"level": 4, "label": "较真", "hint": "更圆滑", "fa": 5, "fs": 0.14, "dir": "q4"},
    {"level": 5, "label": "最真", "hint": "最高还原，文件最大", "fa": 3, "fs": 0.08, "dir": "q5"}
  ],
  "models": [
    {"name": "plates", "displayName": "内外链板", "file": "ch1_03c_plates.stl", "color": "#8A919C", "visible": true},
    {"name": "rollers", "displayName": "滚子", "file": "ch1_03c_rollers.stl", "color": "#E8EDF2", "visible": true},
    {"name": "pins", "displayName": "销轴/轴套", "file": "ch1_03c_pins.stl", "color": "#B08D57", "visible": true}
  ]
}
EOF
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

# ===== 分区：公开 API =====
need_bin
mkdir -p "$OUT_STL" "$OUT_PNG" "$WEB_STL" "$WEB_PNG"

for quality in 1 2 3 4 5; do
    mkdir -p "${OUT_STL}/q${quality}" "${WEB_STL}/q${quality}"
    for part in plates rollers pins; do
        export_stl "$part" "${OUT_STL}/q${quality}/ch1_03c_${part}.stl" "$quality"
        cp -f "${OUT_STL}/q${quality}/ch1_03c_${part}.stl" "${WEB_STL}/q${quality}/"
    done
done

export_stl assembly "${OUT_STL}/ch1_03c_chain.stl" 3
for part in plates rollers pins; do
    cp -f "${OUT_STL}/q2/ch1_03c_${part}.stl" "${WEB_STL}/ch1_03c_${part}.stl"
    cp -f "${OUT_STL}/q2/ch1_03c_${part}.stl" "${OUT_STL}/ch1_03c_${part}.stl"
done

export_png ch1_03c_iso --viewall --autocenter --projection=p --camera=0,0,0,55,0,35,72
export_png ch1_03c_top --viewall --autocenter --projection=o --camera=0,0,0,0,0,0,56
export_png ch1_03c_front --viewall --autocenter --projection=o --camera=0,0,0,90,0,0,56

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
