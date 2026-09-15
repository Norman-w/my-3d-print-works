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
MANIFEST_PY="/Users/norman/.codex/skills/stl-http-preview/scripts/write_preview_manifest.py"
# The single canonical viewer is the preview server root. All view presets
# switch content/camera/opacity in this page instead of opening sub-pages.
PREVIEW_DIR="${PROJECT_ROOT}/output/3d-preview"
LEGACY_PREVIEW_DIR="${PREVIEW_DIR}/cabinet-clutch"
PREVIEW_SOURCE_DIR="${PROJECT_ROOT}/web/cabinet-clutch-preview"
QUALITY="${QUALITY:-2}"
SELECTED_COLUMN="${SELECTED_COLUMN:-2}"
SELECTED_ROW="${SELECTED_ROW:-2}"

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

patch_native_preview_manifest() {
    python3 - "${PREVIEW_DIR}/manifest.json" <<'PY'
from pathlib import Path
import json
import sys

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
payload["up"] = "y"
labels = {
    "cabinet-clutch/cabinet_clutch_cabinet": {
        "name": "柜体·世界坐标背景",
        "color": "#6f8f9a",
        "opacity": 0.18,
        "visible": True,
    },
    "cabinet-clutch/cabinet_clutch_cabinet_context": {
        "name": "柜体·格口与抽屉背景",
        "color": "#8fa9b8",
        "opacity": 0.32,
        "visible": True,
        "role": "diagnostic",
    },
    "cabinet-clutch/cabinet_clutch_assembly": {
        "name": "总装配合并检查体（可选）",
        "color": "#7f8ea3",
        "opacity": 0.28,
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/cabinet_clutch_all_clutches": {
        "name": "离合器合并检查体（可选）",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/cabinet_clutch_detail_open": {
        "name": "离合细节·打开状态（可选）",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/cabinet_clutch_detail_engaged": {
        "name": "离合细节·闭合状态（可选）",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/cabinet_clutch_drawer_drive": {
        "name": "抽屉驱动合并检查体（可选）",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/cabinet_clutch_power_bus": {
        "name": "动力母线合并检查体（可选）",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/00_tensioner_t_solid_reference": {
        "name": "张紧机构·SKP 参数重建",
        "color": "#aebdce",
    },
}
group_map = {
    "cabinet_clutch_cabinet": "00·柜体与格口",
    "cabinet_clutch_cabinet_context": "00·柜体与格口",
    "00_left_d_axis_candidate": "01·动力母线",
    "00_tensioner_t_solid_reference": "01·动力母线",
    "01_motor_vertical_reference": "01·动力母线",
    "02_drive_column_reference": "01·动力母线",
    "03_vertical_rack_candidate": "01·动力母线",
    "cabinet_clutch_power_bus": "01·动力母线",
    "06_upper_axis_z_spur_candidate": "02·离合机构",
    "07_upper_downward_dog_candidate": "02·离合机构",
    "08_lower_upward_dog_candidate": "02·离合机构",
    "09_rear_takeoff_timing_pulley_candidate": "02·离合机构",
    "10_clutch_spring_reference": "02·离合机构",
    "11_t_countersunk_screw_reference": "02·离合机构",
    "12_clutch_fork_candidate": "02·离合机构",
    "cabinet_clutch_all_clutches": "02·离合机构",
    "cabinet_clutch_detail_open": "02·离合机构",
    "cabinet_clutch_detail_engaged": "02·离合机构",
    "13_drawer_timing_belt_reference": "03·抽屉驱动",
    "14_front_timing_pulley_candidate": "03·抽屉驱动",
    "15_front_pinion_candidate": "03·抽屉驱动",
    "16_drawer_linear_rack_candidate": "03·抽屉驱动",
    "cabinet_clutch_drawer_drive": "03·抽屉驱动",
    "cabinet_clutch_assembly": "99·总装配检查体",
}
name_map = {
    "cabinet_clutch_cabinet": "柜体外壳（可见背景）",
    "cabinet_clutch_cabinet_context": "柜体格口与抽屉背景",
    "00_left_d_axis_candidate": "左侧驱动轴 · D 型",
    "00_tensioner_t_solid_reference": "右侧张紧滑台 · SKP 参数化",
    "01_motor_vertical_reference": "抽屉开合电机 · 竖直",
    "02_drive_column_reference": "传动轴 · 代表列",
    "03_vertical_rack_candidate": "Y 向长花键齿轮杆 · 两端 D 轴",
    "06_upper_axis_z_spur_candidate": "离合上方齿轮 · Z 轴",
    "07_upper_downward_dog_candidate": "上方离合齿 · 向下",
    "08_lower_upward_dog_candidate": "下方离合齿 · 向上",
    "09_rear_takeoff_timing_pulley_candidate": "后方取力同步轮",
    "10_clutch_spring_reference": "离合压簧",
    "11_t_countersunk_screw_reference": "T 形沉头螺丝",
    "12_clutch_fork_candidate": "离合拨叉",
    "13_drawer_timing_belt_reference": "抽屉同步皮带",
    "14_front_timing_pulley_candidate": "前方同步轮",
    "15_front_pinion_candidate": "抽屉底部驱动齿轮",
    "16_drawer_linear_rack_candidate": "抽屉底部直线齿排",
    "cabinet_clutch_power_bus": "动力母线合并检查体（可选）",
    "cabinet_clutch_all_clutches": "离合机构合并检查体（可选）",
    "cabinet_clutch_drawer_drive": "抽屉驱动合并检查体（可选）",
    "cabinet_clutch_detail_open": "离合细节 · 打开状态（可选）",
    "cabinet_clutch_detail_engaged": "离合细节 · 闭合状态（可选）",
    "cabinet_clutch_assembly": "总装配合并检查体（可选）",
}
for part in payload.get("parts", []):
    patch = labels.get(part.get("id"))
    if patch:
        part.update(patch)
    stem = str(part.get("id", "")).rsplit("/", 1)[-1]
    if stem in group_map:
        part["group"] = group_map[stem]
    if stem in name_map:
        part["name"] = name_map[stem]
group_order = [
    "00·柜体与格口",
    "01·动力母线",
    "02·离合机构",
    "03·抽屉驱动",
    "99·总装配检查体",
]
counts = {group_id: 0 for group_id in group_order}
for part in payload.get("parts", []):
    group_id = str(part.get("group") or "未分组")
    counts[group_id] = counts.get(group_id, 0) + 1
ordered_group_ids = [group_id for group_id in group_order if counts.get(group_id)]
ordered_group_ids += sorted(group_id for group_id in counts if group_id not in group_order)
payload["groups"] = [
    {"id": group_id, "name": group_id, "count": counts[group_id]}
    for group_id in ordered_group_ids
]
payload["groupCount"] = len(payload["groups"])
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
path.write_text(text, encoding="utf-8")
path.with_name("parts.json").write_text(text, encoding="utf-8")
print(f"已固定原生世界坐标: {path} (up=y)")
PY
}

# ===== 分区：公开 API =====
[[ -x "${OPENSCAD_BIN}" ]] || die "未找到 OpenSCAD: ${OPENSCAD_BIN}"
mkdir -p "${OUT_DIR}" "${REPORT_DIR}"

# Remove the old child-page output and the unrelated legacy root page/assets.
# These are generated preview artifacts, not source models; the root viewer
# below is the only supported browser entry for this assembly.
if [[ -d "${LEGACY_PREVIEW_DIR}" ]]; then
    rm -rf "${LEGACY_PREVIEW_DIR}"
fi
rm -f "${PREVIEW_DIR}/drive.html"
rm -rf "${PREVIEW_DIR}/js"

# Remove only the derived slide/tensioner/bus-belt artifacts from the previous
# design. Source files and unrelated mechanism outputs are left untouched.
OLD_TENSIONER_OUTPUTS=(
    "00_right_round_axis_candidate.stl"
    "00_right_round_axis_reference.stl"
    "00_tensioner_pulley_top_reference.stl"
    "00_tensioner_pulley_bottom_reference.stl"
    "00_tensioner_stage_top_reference.stl"
    "00_tensioner_stage_top_static_reference.stl"
    "00_tensioner_spindle_top_reference.stl"
    "00_tensioner_stage_bottom_reference.stl"
    "00_tensioner_bearing_reference.stl"
    "00_tensioner_base_candidate.stl"
    "00_tensioner_carriage_candidate.stl"
    "00_tensioner_spring_reference.stl"
    "00_tensioner_adjust_screw_reference.stl"
    "00_cabinet_tensioner_receiver_candidate.stl"
    "00_tensioner_slide_assembly_reference.stl"
    "04_right_round_axis_reference.stl"
    "05_top_bottom_bus_belts_reference.stl"
    "05_top_bottom_bus_belts_base_reference.stl"
    "05_top_bottom_bus_belts_teeth_reference.stl"
)
for old_file in "${OLD_TENSIONER_OUTPUTS[@]}"; do
    rm -f "${OUT_DIR}/${old_file}" "${REPORT_DIR}/${old_file%.stl}.json"
done

export_part "cabinet" "${OUT_DIR}/cabinet_clutch_cabinet.stl" false 0
export_part "cabinet_context" "${OUT_DIR}/cabinet_clutch_cabinet_context.stl" false 0
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
export_part "tensioner_t_solid" "${OUT_DIR}/00_tensioner_t_solid_reference.stl" false 0
export_part "motor" "${OUT_DIR}/01_motor_vertical_reference.stl" false 0
export_part "column" "${OUT_DIR}/02_drive_column_reference.stl" false 0
export_part "vertical_rack" "${OUT_DIR}/03_vertical_rack_candidate.stl" false 0
export_part "upper_spur" "${OUT_DIR}/06_upper_axis_z_spur_candidate.stl" false 0
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

# ===== 分区：原生世界坐标预览 =====
# cabinet_clutch.scad is authored in X=width, Y=height, Z=depth directly.
# Regenerate the root manifest so STL mtimes bust the browser cache, then
# install the single world-assembly viewer at the server root.
[[ -f "${MANIFEST_PY}" ]] || die "未找到 STL 预览清单脚本: ${MANIFEST_PY}"
[[ -f "${PREVIEW_SOURCE_DIR}/index.html" ]] || die "未找到离合预览模板: ${PREVIEW_SOURCE_DIR}/index.html"
[[ -f "${PREVIEW_SOURCE_DIR}/app.js" ]] || die "未找到离合预览模板: ${PREVIEW_SOURCE_DIR}/app.js"
python3 "${MANIFEST_PY}" \
    --stl-dir "${OUT_DIR}" \
    --preview-dir "${PREVIEW_DIR}" \
    --title "SmartPartsDrawer 离合张紧机构" \
    --role printed \
    --no-recursive
patch_native_preview_manifest
cp "${PREVIEW_SOURCE_DIR}/index.html" "${PREVIEW_DIR}/index.html"
cp "${PREVIEW_SOURCE_DIR}/app.js" "${PREVIEW_DIR}/app.js"

echo "完成: ${OUT_DIR}"
echo "检查报告: ${REPORT_DIR}"
echo "世界总装配预览: http://127.0.0.1:8765/"
