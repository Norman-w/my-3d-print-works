#!/usr/bin/env bash
# Export the literal Z+ side gear with its lower Y− rounded-triangle dog.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAD_FILE="${PROJECT_ROOT}/cad/openscad/ch1_03c_spline_gear_dog.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
INSPECT_PY="${INSPECT_PY:-/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py}"
OUT_STL="${PROJECT_ROOT}/output/3d-print/spline-gear-dog"
OUT_PNG="${PROJECT_ROOT}/output/previews/spline-gear-dog"
STL_NAME="ch1_03c_spline_gear_dog_solid"

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

need_bin() {
    [[ -x "${OPENSCAD_BIN}" ]] || die "找不到 OpenSCAD: ${OPENSCAD_BIN}"
}

export_stl() {
    local dest="${OUT_STL}/${STL_NAME}.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ STL ${STL_NAME}"
    "${OPENSCAD_BIN}" \
        --backend Manifold \
        --export-format binstl \
        -D 'SPLINE_GEAR_DOG_MODEL="solid"' \
        -o "${tmp}" \
        "${SCAD_FILE}"
    [[ -s "${tmp}" ]] || die "空 STL: ${dest}"
    mv -f "${tmp}" "${dest}"
}

render_png() {
    local model="$1"
    local name="$2"
    local projection="$3"
    local camera="$4"
    local target="${OUT_PNG}/${name}.png"
    echo "→ PNG ${name}"
    "${OPENSCAD_BIN}" \
        --backend Manifold \
        --render \
        --viewall \
        --autocenter \
        --projection="${projection}" \
        --camera="${camera}" \
        --imgsize=1600,1000 \
        --colorscheme=BeforeDawn \
        -D "SPLINE_GEAR_DOG_MODEL=\"${model}\"" \
        -o "${target}" \
        "${SCAD_FILE}"
    [[ -s "${target}" ]] || die "空 PNG: ${target}"
}

# ===== 分区：公开 API =====
need_bin
mkdir -p "${OUT_STL}" "${OUT_PNG}"

export_stl

# thumbnail_iso：同时看见 Y 向长花键轴、Z+ 侧齿轮、Y− 侧圆角三角狗牙和母槽。
# thumbnail_xz：正视 XZ 齿轮截面，确认小齿轮确实位于花键轴 Z+。
# thumbnail_y：沿 X 看齿轮/狗牙在 Y 方向的上下叠放。
render_png "thumbnail" "${STL_NAME}_thumbnail_iso" p "0,0,0,55,0,35,45"
render_png "thumbnail" "${STL_NAME}_thumbnail_xz" o "0,0,0,90,0,0,45"
render_png "thumbnail" "${STL_NAME}_thumbnail_y" o "0,0,0,0,90,0,45"

if [[ -f "${INSPECT_PY}" ]]; then
    echo "→ inspect ${STL_NAME}.stl"
    python3 "${INSPECT_PY}" \
        --require-watertight \
        --output "${OUT_STL}/${STL_NAME}.json" \
        "${OUT_STL}/${STL_NAME}.stl"
else
    echo "跳过 STL 检查：找不到 ${INSPECT_PY}"
fi

echo "完成：齿轮+下置狗牙 STL、缩略图和检查 JSON 已写入 output。"

# ===== 分区：方法/工具 =====
# OPENSCAD_BIN、INSPECT_PY 可通过环境变量覆盖。
