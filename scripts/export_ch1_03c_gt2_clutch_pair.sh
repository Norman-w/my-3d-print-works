#!/usr/bin/env bash
# Export the printable 15T child wheel and integrated 12T GT2 mother wheel.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAD_FILE="${PROJECT_ROOT}/cad/openscad/ch1_03c_gt2_clutch_pair.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
INSPECT_PY="${INSPECT_PY:-/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py}"
OUT_STL="${PROJECT_ROOT}/output/3d-print/gt2-clutch-pair"
OUT_PNG="${PROJECT_ROOT}/output/previews/gt2-clutch-pair"

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

need_bin() {
    [[ -x "${OPENSCAD_BIN}" ]] || die "找不到 OpenSCAD: ${OPENSCAD_BIN}"
    [[ -f "${SCAD_FILE}" ]] || die "找不到 SCAD: ${SCAD_FILE}"
}

export_stl() {
    local model="$1"
    local name="$2"
    local dest="${OUT_STL}/${name}.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ STL ${name}"
    "${OPENSCAD_BIN}" \
        --backend Manifold \
        --export-format binstl \
        -D "GT2_CLUTCH_MODEL=\"${model}\"" \
        -o "${tmp}" \
        "${SCAD_FILE}"
    [[ -s "${tmp}" ]] || die "空 STL: ${dest}"
    mv -f "${tmp}" "${dest}"
}

render_png() {
    local name="$1"
    local projection="$2"
    local camera="$3"
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
        -D 'GT2_CLUTCH_MODEL="assembly"' \
        -o "${target}" \
        "${SCAD_FILE}"
    [[ -s "${target}" ]] || die "空 PNG: ${target}"
}

inspect_stl() {
    local name="$1"
    local stl="${OUT_STL}/${name}.stl"
    [[ -f "${INSPECT_PY}" ]] || {
        echo "跳过 STL 检查：找不到 ${INSPECT_PY}"
        return 0
    }
    echo "→ inspect ${name}.stl"
    python3 "${INSPECT_PY}" \
        --require-watertight \
        --output "${OUT_STL}/${name}.json" \
        "${stl}"
}

# ===== 分区：公开 API =====
need_bin
mkdir -p "${OUT_STL}" "${OUT_PNG}"

export_stl "male" "ch1_03c_gt2_clutch_male_15t"
export_stl "female" "ch1_03c_gt2_clutch_female_12t"
inspect_stl "ch1_03c_gt2_clutch_male_15t"
inspect_stl "ch1_03c_gt2_clutch_female_12t"

# assembly_* are diagnostic views only; the translucent belt envelope and long
# shaft context are intentionally not part of either printable STL.
render_png "ch1_03c_gt2_clutch_pair_assembly_iso" p "0,0,0,55,0,35,52"
render_png "ch1_03c_gt2_clutch_pair_assembly_xz" o "0,0,0,90,0,0,52"
render_png "ch1_03c_gt2_clutch_pair_assembly_y" o "0,0,0,0,90,0,52"

echo "完成：GT2 打印版子轮、母轮、检查 JSON 和装配缩略图已写入 output。"

# ===== 分区：方法/工具 =====
# OPENSCAD_BIN、INSPECT_PY 可通过环境变量覆盖。
