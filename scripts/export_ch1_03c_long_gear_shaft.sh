#!/usr/bin/env bash
# Export the X1C fine variants of the CH1 03C long gear shaft.
# The legacy 12T / 3 mm artifacts remain available under their old names;
# pass LONG_GEAR_PRESET="standard" to OpenSCAD when a reproducible legacy
# export is needed.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAD_FILE="${PROJECT_ROOT}/cad/openscad/ch1_03c_long_gear_shaft.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
INSPECT_PY="${INSPECT_PY:-/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py}"
OUT_STL="${PROJECT_ROOT}/output/3d-print/long-gear-shaft"
OUT_PNG="${PROJECT_ROOT}/output/previews/long-gear-shaft"

# ===== 分区：模型/类型 =====
PARTS=(
    "x1c_fine|solid|ch1_03c_long_gear_shaft_solid_x1c_fine"
    "x1c_fine|sleeve|ch1_03c_long_gear_shaft_sleeve_x1c_fine"
)

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

need_bin() {
    [[ -x "${OPENSCAD_BIN}" ]] || die "找不到 OpenSCAD: ${OPENSCAD_BIN}"
}

export_stl() {
    local preset="$1"
    local model="$2"
    local name="$3"
    local dest="${OUT_STL}/${name}.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ STL ${name}"
    "${OPENSCAD_BIN}" \
        --backend Manifold \
        --export-format binstl \
        -D "LONG_GEAR_PRESET=\"${preset}\"" \
        -D "LONG_GEAR_MODEL=\"${model}\"" \
        -o "${tmp}" \
        "${SCAD_FILE}"
    [[ -s "${tmp}" ]] || die "空 STL: ${dest}"
    mv -f "${tmp}" "${dest}"
}

render_png() {
    local preset="$1"
    local model="$2"
    local name="$3"
    local projection="$4"
    local camera="$5"
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
        -D "LONG_GEAR_PRESET=\"${preset}\"" \
        -D "LONG_GEAR_MODEL=\"${model}\"" \
        -o "${target}" \
        "${SCAD_FILE}"
    [[ -s "${target}" ]] || die "空 PNG: ${target}"
}

# ===== 分区：公开 API =====
need_bin
mkdir -p "${OUT_STL}" "${OUT_PNG}"

for item in "${PARTS[@]}"; do
    IFS='|' read -r preset model name <<< "${item}"
    export_stl "${preset}" "${model}" "${name}"
done

# Y 轴长度方向的前后视图会显示端轴与齿段关系；顶视图直接观察 XZ 齿形截面。
for item in "${PARTS[@]}"; do
    IFS='|' read -r preset model name <<< "${item}"
    render_png "${preset}" "${model}" "${name}_iso" p "0,0,0,55,0,35,215"
    render_png "${preset}" "${model}" "${name}_top_xz" o "0,0,0,0,0,0,215"
    render_png "${preset}" "${model}" "${name}_side_y" o "0,0,0,90,0,0,215"
done

if [[ -f "${INSPECT_PY}" ]]; then
    for item in "${PARTS[@]}"; do
        IFS='|' read -r _ _ name <<< "${item}"
        echo "→ inspect ${name}.stl"
        python3 "${INSPECT_PY}" \
            --require-watertight \
            --output "${OUT_STL}/${name}.json" \
            "${OUT_STL}/${name}.stl"
    done
else
    echo "跳过 STL 检查：找不到 ${INSPECT_PY}"
fi

echo "完成：长齿轮轴两个版本、三视图预览和检查 JSON 已写入 output。"

# ===== 分区：方法/工具 =====
# OPENSCAD_BIN、INSPECT_PY 可通过环境变量覆盖。
