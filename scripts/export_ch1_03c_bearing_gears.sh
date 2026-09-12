#!/usr/bin/env bash
# Export the 12T and 8T 03C low-load bearing gears.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAD_DIR="${PROJECT_ROOT}/cad/openscad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
INSPECT_PY="${INSPECT_PY:-/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py}"
OUT_STL="${PROJECT_ROOT}/output/3d-print"
OUT_PNG="${PROJECT_ROOT}/output/previews"

# ===== 分区：模型/类型 =====
PARTS=(
    "ch1_03c_bearing_12t.scad|ch1_03c_bearing_12t"
    "ch1_03c_bearing_8t.scad|ch1_03c_bearing_8t"
)

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

need_bin() {
    [[ -x "$OPENSCAD_BIN" ]] || die "找不到 OpenSCAD: $OPENSCAD_BIN"
}

export_stl() {
    local source="$1"
    local name="$2"
    local dest="${OUT_STL}/${name}.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ STL ${name} → ${dest}"
    (
        cd "$SCAD_DIR"
        "$OPENSCAD_BIN" \
            --backend Manifold \
            --export-format binstl \
            -o "$tmp" \
            "$source"
    )
    [[ -s "$tmp" ]] || die "空 STL: $dest"
    mv -f "$tmp" "$dest"
}

export_png() {
    local source="$1"
    local name="$2"
    local projection="$3"
    local camera="$4"
    local dest="${OUT_PNG}/${name}.png"
    echo "→ PNG ${name}"
    (
        cd "$SCAD_DIR"
        "$OPENSCAD_BIN" \
            --preview \
            --imgsize=1600,1000 \
            --colorscheme="Tomorrow Night" \
            --viewall \
            --autocenter \
            --projection="$projection" \
            --camera="$camera" \
            -o "$dest" \
            "$source"
    )
    [[ -s "$dest" ]] || die "空 PNG: $dest"
}

# ===== 分区：公开 API =====
need_bin
mkdir -p "$OUT_STL" "$OUT_PNG"

for item in "${PARTS[@]}"; do
    IFS='|' read -r source name <<< "$item"
    export_stl "$source" "$name"
done

export_png "ch1_03c_bearing_12t.scad" "ch1_03c_bearing_12t_iso" p "0,0,0,55,0,35,42"
export_png "ch1_03c_bearing_12t.scad" "ch1_03c_bearing_12t_top" o "0,0,0,0,0,0,34"
export_png "ch1_03c_bearing_12t.scad" "ch1_03c_bearing_12t_front" o "0,0,0,90,0,0,34"
export_png "ch1_03c_bearing_8t.scad" "ch1_03c_bearing_8t_iso" p "0,0,0,55,0,35,28"
export_png "ch1_03c_bearing_8t.scad" "ch1_03c_bearing_8t_top" o "0,0,0,0,0,0,24"
export_png "ch1_03c_bearing_8t.scad" "ch1_03c_bearing_8t_front" o "0,0,0,90,0,0,24"

if [[ -f "$INSPECT_PY" ]]; then
    for item in "${PARTS[@]}"; do
        IFS='|' read -r _ name <<< "$item"
        echo "→ inspect ${name}.stl"
        python3 "$INSPECT_PY" --require-watertight "${OUT_STL}/${name}.stl"
    done
else
    echo "跳过 STL 检查：找不到 $INSPECT_PY"
fi

echo "完成：12T 和 8T 轴承版 STL、三视图预览已写入 output。"

# ===== 分区：方法/工具 =====
# OPENSCAD_BIN、INSPECT_PY 可通过环境变量覆盖；默认按本机 OpenSCAD/技能路径运行。
