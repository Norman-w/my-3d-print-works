#!/usr/bin/env bash
# Export the OpenSCAD drawer clutch mechanism and run topology/size triage.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAD_DIR="${PROJECT_ROOT}/cad/openscad/enclosure"
SCAD_FILE="cabinet_clutch.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
OUT_DIR="${PROJECT_ROOT}/output/3d-print/cabinet-clutch"
REPORT_DIR="${PROJECT_ROOT}/output/inspection/cabinet-clutch"
INSPECT_PY="/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py"
QUALITY="${QUALITY:-2}"
SELECTED_COLUMN="${SELECTED_COLUMN:-2}"
SELECTED_ROW="${SELECTED_ROW:-2}"
TENSIONER_SCREW_OUT_MM="${TENSIONER_SCREW_OUT_MM:-4}"

# ===== 分区：模型/类型 =====
# assembly is a visual envelope. The one-by-one references keep the purchased
# motor, belt and spring separate from the printable gear/rack candidates.

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

export_part() {
    local part="$1"
    local target="$2"
    local engaged="$3"
    local explode="$4"
    local tmp="${target}.tmp.$$"
    echo "→ CLUTCH_PART=${part} ENGAGED=${engaged} → ${target}"
    (
        cd "${SCAD_DIR}"
        "${OPENSCAD_BIN}" \
            --backend Manifold \
            --export-format binstl \
            -D "QUALITY=${QUALITY}" \
            -D "CLUTCH_PART=\"${part}\"" \
            -D "ENGAGED=${engaged}" \
            -D "CLUTCH_EXPLODE=${explode}" \
            -D "SELECTED_COLUMN=${SELECTED_COLUMN}" \
            -D "SELECTED_ROW=${SELECTED_ROW}" \
            -D "TENSIONER_SCREW_OUT_MM=${TENSIONER_SCREW_OUT_MM}" \
            -o "${tmp}" \
            "${SCAD_FILE}"
    )
    [[ -s "${tmp}" ]] || die "空 STL: ${target}"
    mv -f "${tmp}" "${target}"
    if [[ -x "${INSPECT_PY}" || -f "${INSPECT_PY}" ]]; then
        python3 "${INSPECT_PY}" "${target}" --json --output "${REPORT_DIR}/$(basename "${target}" .stl).json"
    else
        echo "警告: 未找到 inspect_stl.py，跳过拓扑报告。" >&2
    fi
}

# ===== 分区：公开 API =====
[[ -x "${OPENSCAD_BIN}" ]] || die "未找到 OpenSCAD: ${OPENSCAD_BIN}"
mkdir -p "${OUT_DIR}" "${REPORT_DIR}"

export_part "cabinet" "${OUT_DIR}/cabinet_clutch_cabinet.stl" false 0
export_part "power_bus" "${OUT_DIR}/cabinet_clutch_power_bus.stl" false 0
export_part "drawer_drive" "${OUT_DIR}/cabinet_clutch_drawer_drive.stl" false 0
export_part "clutch" "${OUT_DIR}/cabinet_clutch_all_clutches.stl" false 0
export_part "clutch_detail" "${OUT_DIR}/cabinet_clutch_detail_open.stl" false 8
export_part "clutch_detail" "${OUT_DIR}/cabinet_clutch_detail_engaged.stl" true 8
export_part "assembly" "${OUT_DIR}/cabinet_clutch_assembly.stl" false 0

# ===== 分区：逐件输出 =====
# These are intentionally emitted in mechanism order so a failed fit can be
# corrected without hiding it inside a full assembly export.
export_part "left_d_axis" "${OUT_DIR}/00_left_d_axis_candidate.stl" false 0
export_part "right_round_axis" "${OUT_DIR}/00_right_round_axis_candidate.stl" false 0
export_part "tensioner_pulley_top" "${OUT_DIR}/00_tensioner_pulley_top_reference.stl" false 0
export_part "tensioner_pulley_bottom" "${OUT_DIR}/00_tensioner_pulley_bottom_reference.stl" false 0
export_part "tensioner_base" "${OUT_DIR}/00_tensioner_base_candidate.stl" false 0
export_part "tensioner_carriage" "${OUT_DIR}/00_tensioner_carriage_candidate.stl" false 0
export_part "tensioner_spring" "${OUT_DIR}/00_tensioner_spring_reference.stl" false 0
export_part "tensioner_screw" "${OUT_DIR}/00_tensioner_adjust_screw_reference.stl" false 0
export_part "tensioner_receiver" "${OUT_DIR}/00_cabinet_tensioner_receiver_candidate.stl" false 0
export_part "tensioner_slide" "${OUT_DIR}/00_tensioner_slide_assembly_reference.stl" false 0
export_part "motor" "${OUT_DIR}/01_motor_vertical_reference.stl" false 0
export_part "column" "${OUT_DIR}/02_drive_column_reference.stl" false 0
export_part "vertical_rack" "${OUT_DIR}/03_vertical_rack_candidate.stl" false 0
export_part "right_round_axis" "${OUT_DIR}/04_right_round_axis_reference.stl" false 0
export_part "bus_belt" "${OUT_DIR}/05_top_bottom_bus_belts_reference.stl" false 0
export_part "upper_spur" "${OUT_DIR}/06_upper_axis_y_spur_candidate.stl" false 0
export_part "upper_dog" "${OUT_DIR}/07_upper_downward_dog_candidate.stl" false 0
export_part "lower_dog" "${OUT_DIR}/08_lower_upward_dog_candidate.stl" false 0
export_part "rear_pulley" "${OUT_DIR}/09_rear_takeoff_timing_pulley_candidate.stl" false 0
export_part "spring" "${OUT_DIR}/10_clutch_spring_reference.stl" false 0
export_part "screw" "${OUT_DIR}/11_t_countersunk_screw_reference.stl" false 0
export_part "fork" "${OUT_DIR}/12_clutch_fork_candidate.stl" false 0
export_part "drawer_belt" "${OUT_DIR}/13_drawer_timing_belt_reference.stl" false 0
export_part "front_pulley" "${OUT_DIR}/14_front_timing_pulley_candidate.stl" false 0
export_part "front_gear" "${OUT_DIR}/15_front_pinion_candidate.stl" false 0
export_part "drawer_rack" "${OUT_DIR}/16_drawer_linear_rack_candidate.stl" false 0

echo "完成: ${OUT_DIR}"
echo "检查报告: ${REPORT_DIR}"
