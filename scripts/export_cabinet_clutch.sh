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
OUT_CHAIN="${PROJECT_ROOT}/output/3d-print/cabinet-chain"
OUT_CABINET="${PROJECT_ROOT}/output/3d-print/cabinet"
OUT_MOTOR="${PROJECT_ROOT}/output/3d-print/motor-library"
OUT_MOUNT="${PROJECT_ROOT}/output/3d-print/motor-mount"
OUT_CHAIN_HARDWARE="${PROJECT_ROOT}/output/3d-print/chain-hardware"
OUT_CHAIN_CLUTCH="${PROJECT_ROOT}/output/3d-print/chain-clutch"
REPORT_DIR="${PROJECT_ROOT}/output/inspection/cabinet-clutch"
INSPECT_PY="/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py"
MANIFEST_PY="/Users/norman/.codex/skills/stl-http-preview/scripts/write_preview_manifest.py"
# The single canonical viewer is the preview server root. All view presets
# switch content/camera/opacity in this page instead of opening sub-pages.
PREVIEW_DIR="${PROJECT_ROOT}/output/3d-preview"
LEGACY_PREVIEW_DIR="${PREVIEW_DIR}/cabinet-clutch"
PREVIEW_SOURCE_DIR="${PROJECT_ROOT}/web/cabinet-preview"
QUALITY="${QUALITY:-2}"
SELECTED_COLUMN="${SELECTED_COLUMN:-2}"
SELECTED_ROW="${SELECTED_ROW:-2}"
SHOW_LEGACY_STATIONS="${SHOW_LEGACY_STATIONS:-false}"

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
            -D "SHOW_LEGACY_STATIONS=${SHOW_LEGACY_STATIONS}" \
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
        "name": "动力母线整件 · 电机直连 +X 末列",
        "color": "#65788d",
        "opacity": 0.86,
        "visible": True,
        "role": "diagnostic",
    },
    "cabinet-clutch/00_tensioner_t_solid_reference": {
        "name": "张紧机构·SKP 参数重建（动力母线整件内含）",
        "color": "#aebdce",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet/cabinet_back_panel": {
        "name": "可拆背板",
        "color": "#c4a574",
        "visible": False,
        "role": "printed",
    },
    "cabinet-clutch/07_upper_downward_dog_candidate": {
        "name": "中心格新版公轮 · 圆角三角插销（06同一实体，别名）",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/09_rear_takeoff_timing_pulley_candidate": {
        "name": "中心格新版后端2GT母轮（08同一实体，别名）",
        "visible": False,
        "role": "diagnostic",
    },
}
chain_labels = {
    "cabinet-chain/cabinet_chain_motor": {
        "name": "蛇形链条唯一驱动电机本体（右下张紧位）",
        "color": "#424a54",
        "role": "purchased",
    },
    "cabinet-chain/cabinet_chain_motor_shaft": {
        "name": "蛇形链条驱动 D 输出轴（右下，随动力轮转动）",
        "color": "#d6d9dc",
        "role": "purchased",
    },
    "cabinet-chain/cabinet_chain_motor_cover": {
        "name": "蛇形链条电机固定罩（可沿下压方向滑动）",
        "color": "#56616d",
        "role": "printed",
    },
    "cabinet-chain/cabinet_chain_motor_tensioner": {
        "name": "蛇形电机张紧调节（导槽 + 弹簧 + M3 螺杆）",
        "color": "#c9a227",
        "role": "printed",
    },
    "cabinet-chain/cabinet_chain_sprockets": {
        "name": "12T 尖齿（右下动力 D 轴 + 其余轴承导向）",
        "color": "#5b9fd6",
        "role": "printed",
    },
    "cabinet-chain/cabinet_chain_idlers": {
        "name": "8T 钝齿轴承平移轮",
        "color": "#7dcc4a",
        "role": "printed",
    },
    "cabinet-chain/cabinet_chain_plates": {"name": "03C 蛇形链板", "color": "#8A919C", "role": "purchased"},
    "cabinet-chain/cabinet_chain_rollers": {"name": "03C 滚子", "color": "#E8EDF2", "role": "purchased"},
    "cabinet-chain/cabinet_chain_pins": {"name": "03C 销轴", "color": "#B08D57", "role": "purchased"},
    "cabinet-chain/cabinet_chain_bearings": {"name": "3×6×2 轴承（装配显示/采购件）", "color": "#b9c2ca", "role": "purchased"},
    "cabinet-chain/cabinet_chain_connector": {"name": "03C 链条连接节（带槽双穿销+圆弧夹片）", "color": "#ff2fd0", "role": "diagnostic"},
    "cabinet-chain/cabinet_chain_clutch_connector": {"name": "03C 链条加长接头（默认隐藏）", "color": "#00d9ff", "role": "diagnostic", "visible": False},
    "cabinet-chain/cabinet_chain_clutch_bearing": {"name": "加长接头 681 轴承（默认隐藏）", "color": "#cfd4da", "role": "purchased", "visible": False},
    "cabinet-chain/cabinet_chain_scheme1_power_wheels": {"name": "旧方案1·常转动力轮（文件保留，默认隐藏）", "visible": False, "role": "diagnostic"},
    "cabinet-chain/cabinet_chain_scheme1_output_wheels": {"name": "旧方案1·抽屉受力轮（文件保留，默认隐藏）", "visible": False, "role": "diagnostic"},
    "cabinet-chain/cabinet_chain_scheme1_clutch_faces": {"name": "旧方案1·狗牙离合面（文件保留，默认隐藏）", "visible": False, "role": "diagnostic"},
    "cabinet-chain/cabinet_chain_scheme1_bearings": {"name": "旧方案1·抽屉输出轴承（文件保留，默认隐藏）", "visible": False, "role": "purchased"},
    "cabinet-chain/cabinet_chain_scheme1_selector": {"name": "旧方案1·链条拨叉/8T 选择轮（文件保留，默认隐藏）", "visible": False, "role": "diagnostic"},
    "motor-library/ch1_03c_power_motor_pololu_100_1_hp_6v": {"name": "Pololu 蛇形驱动电机·独立模型库（默认隐藏）", "visible": False, "role": "purchased"},
    "motor-mount/ch1_03c_power_motor_cover": {"name": "蛇形电机固定罩·独立模型库（默认隐藏）", "visible": False, "role": "printed"},
    "chain-hardware/ch1_03c_connecting_pin": {"name": "03C 连接节穿销·独立模型库（默认隐藏）", "visible": False, "role": "purchased"},
    "chain-hardware/ch1_03c_retaining_clip": {"name": "03C 连接节卡子·独立模型库（默认隐藏）", "visible": False, "role": "purchased"},
    "chain-clutch/ch1_03c_extended_connecting_pin": {"name": "03C 加长接头穿销·独立模型库（默认隐藏）", "visible": False, "role": "purchased"},
    "chain-clutch/ch1_03c_extended_retaining_clips": {"name": "03C 加长接头卡子·独立模型库（默认隐藏）", "visible": False, "role": "purchased"},
    "chain-clutch/ch1_03c_clutch_platform": {"name": "传动离合轴承平台·独立模型库（默认隐藏）", "visible": False, "role": "printed"},
    "chain-clutch/ch1_03c_clutch_bearing": {"name": "681 离合轴承·独立模型库（默认隐藏）", "visible": False, "role": "purchased"},
    "chain-clutch/ch1_03c_clutch_bearing_retainer": {"name": "681 离合轴承承托环·独立模型库（默认隐藏）", "visible": False, "role": "printed"},
}
group_map = {
    "cabinet_clutch_cabinet": "00·柜体与格口",
    "cabinet_clutch_cabinet_context": "00·柜体与格口",
    "00_tensioner_t_solid_reference": "01·动力母线",
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
    "00_tensioner_t_solid_reference": "右侧张紧滑台 · SKP 参数化",
    "06_upper_axis_z_spur_candidate": "中心格新版公轮 · 3mm兼容齿形",
    "07_upper_downward_dog_candidate": "中心格新版公轮 · 圆角三角插销",
    "08_lower_upward_dog_candidate": "中心格新版母轮 · 母槽与2GT",
    "09_rear_takeoff_timing_pulley_candidate": "中心格新版后端2GT母轮",
    "10_clutch_spring_reference": "离合压簧",
    "11_t_countersunk_screw_reference": "T 形沉头螺丝",
    "12_clutch_fork_candidate": "离合拨叉",
    "13_drawer_timing_belt_reference": "中心格新版2GT皮带 · 80T/160mm/6mm",
    "14_front_timing_pulley_candidate": "中心格新版前端2GT同步轮",
    "15_front_pinion_candidate": "中心格新版前端粗齿驱动轮",
    "16_drawer_linear_rack_candidate": "中心格新版抽屉底部直线齿排",
    "cabinet_clutch_power_bus": "动力母线合并检查体（可选）",
    "cabinet_clutch_all_clutches": "离合机构合并检查体（可选）",
    "cabinet_clutch_drawer_drive": "抽屉驱动合并检查体（可选）",
    "cabinet_clutch_detail_open": "离合细节 · 打开状态（可选）",
    "cabinet_clutch_detail_engaged": "离合细节 · 闭合状态（可选）",
    "cabinet_clutch_assembly": "总装配合并检查体（可选）",
}
for part in payload.get("parts", []):
    stem = str(part.get("id", "")).rsplit("/", 1)[-1]
    if stem in group_map:
        part["group"] = group_map[stem]
    if stem in name_map:
        part["name"] = name_map[stem]
    patch = labels.get(part.get("id")) or chain_labels.get(part.get("id"))
    if patch:
        part.update(patch)
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

# Preserve the authored call structure in the root viewer.  A tree node that
# has partId points to a real STL and receives a visibility checkbox; a call
# node is structural information only and does not create another mesh.
parts_by_id = {
    str(part.get("id")): part
    for part in payload.get("parts", [])
    if isinstance(part, dict) and part.get("id")
}
parts_by_group = {}
for part in payload.get("parts", []):
    group_id = str(part.get("group") or "ungrouped")
    parts_by_group.setdefault(group_id, []).append(part)

def part_node(part_id, *, children=None, exclusive_groups=None, display_mode=None):
    part = parts_by_id.get(part_id)
    if not part:
        return None
    node = {
        "id": f"part:{part_id}",
        "kind": "part",
        "partId": part_id,
        "name": part.get("name") or part_id,
    }
    if children:
        node["children"] = [child for child in children if child]
    if exclusive_groups:
        node["exclusiveGroups"] = exclusive_groups
    if display_mode:
        node["displayMode"] = display_mode
    return node

def call_node(node_id, name, description=""):
    node = {"id": f"call:{node_id}", "kind": "call", "name": name}
    if description:
        node["description"] = description
    return node

def folder_node(group_id):
    label = next(
        (group.get("name") for group in payload["groups"] if group.get("id") == group_id),
        group_id,
    )
    return {
        "id": group_id,
        "kind": "folder",
        "groupId": group_id,
        "name": label,
        "children": [],
    }

tree = []
for group_id in ordered_group_ids:
    root = folder_node(group_id)
    if group_id == "01·动力母线":
        root["children"] = [
            part_node(
                "cabinet-clutch/cabinet_clutch_power_bus",
                exclusive_groups=["power-bus"],
                display_mode="assembly",
                children=[
                    call_node(
                        "power_bus/power_motor_vertical",
                        "抽屉开合电机 · 竖直（内含）",
                        "power_motor_vertical()",
                    ),
                    call_node(
                        "power_bus/column_plus_x_max",
                        "+X 末列花键齿轮杆 · 电机直接接驳（内含）",
                        "vertical_gear_column(N_COL - 1)",
                    ),
                    call_node(
                        "power_bus/columns_remaining",
                        "其余 4 列花键齿轮杆（内含）",
                        "vertical_gear_column(0 .. N_COL - 2)",
                    ),
                ],
            ),
            part_node(
                "cabinet-clutch/00_tensioner_t_solid_reference",
                exclusive_groups=["power-bus"],
                display_mode="detail",
            ),
        ]
    elif group_id == "02·离合机构":
        upper_alias = part_node(
            "cabinet-clutch/07_upper_downward_dog_candidate",
            exclusive_groups=["clutch-assembly", "clutch-upper-alias"],
            display_mode="alias",
        )
        lower_alias = part_node(
            "cabinet-clutch/09_rear_takeoff_timing_pulley_candidate",
            exclusive_groups=["clutch-assembly", "clutch-lower-alias"],
            display_mode="alias",
        )
        upper = part_node(
            "cabinet-clutch/06_upper_axis_z_spur_candidate",
            exclusive_groups=["clutch-assembly", "clutch-upper-alias"],
            children=[upper_alias],
        )
        lower = part_node(
            "cabinet-clutch/08_lower_upward_dog_candidate",
            exclusive_groups=["clutch-assembly", "clutch-lower-alias"],
            children=[lower_alias],
        )
        root["children"] = [
            part_node(
                "cabinet-clutch/cabinet_clutch_all_clutches",
                exclusive_groups=["clutch-assembly", "clutch-detail-state"],
                display_mode="assembly",
                children=[upper, lower],
            ),
            part_node(
                "cabinet-clutch/cabinet_clutch_detail_open",
                exclusive_groups=["clutch-detail-state"],
                display_mode="detail",
            ),
            part_node(
                "cabinet-clutch/cabinet_clutch_detail_engaged",
                exclusive_groups=["clutch-detail-state"],
                display_mode="detail",
            ),
        ]
    elif group_id == "03·抽屉驱动":
        root["children"] = [
            part_node(
                "cabinet-clutch/cabinet_clutch_drawer_drive",
                exclusive_groups=["drawer-assembly"],
                display_mode="assembly",
                children=[
                    part_node(
                        "cabinet-clutch/13_drawer_timing_belt_reference",
                        exclusive_groups=["drawer-assembly"],
                    ),
                    part_node(
                        "cabinet-clutch/14_front_timing_pulley_candidate",
                        exclusive_groups=["drawer-assembly"],
                    ),
                    part_node(
                        "cabinet-clutch/15_front_pinion_candidate",
                        exclusive_groups=["drawer-assembly"],
                    ),
                    part_node(
                        "cabinet-clutch/16_drawer_linear_rack_candidate",
                        exclusive_groups=["drawer-assembly"],
                    ),
                ],
            ),
        ]
    else:
        root["children"] = [
            part_node(str(part.get("id")))
            for part in parts_by_group.get(group_id, [])
        ]
    root["children"] = [child for child in root["children"] if child]
    tree.append(root)

# Keep any group introduced by a future exporter visible even if it is not in
# the fixed mechanism order above.
known_groups = {node["id"] for node in tree}
for group_id in sorted(parts_by_group):
    if group_id in known_groups:
        continue
    root = folder_node(group_id)
    root["children"] = [
        part_node(str(part.get("id")))
        for part in parts_by_group[group_id]
    ]
    root["children"] = [child for child in root["children"] if child]
    tree.append(root)
payload["treeVersion"] = 1
payload["tree"] = tree
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

# The default physical-validation scene has no legacy spring/screw/fork. Remove
# any stale derived files from an older full-station export so the viewer cannot
# accidentally present those retired parts as current center-cell hardware.
LEGACY_CLUTCH_OUTPUTS=(
    "10_clutch_spring_reference.stl"
    "11_t_countersunk_screw_reference.stl"
    "12_clutch_fork_candidate.stl"
)
for old_file in "${LEGACY_CLUTCH_OUTPUTS[@]}"; do
    rm -f "${OUT_DIR}/${old_file}" "${REPORT_DIR}/${old_file%.stl}.json"
done

# The root viewer uses the assembled power bus as the single authoritative
# model for this mechanism. These generated child previews used to be loaded
# at the same coordinates and duplicated the motor, D shaft, and column shaft.
# Keep their parametric SCAD entry points, but do not publish duplicate root
# list items.
POWER_BUS_CHILD_OUTPUTS=(
    "00_left_d_axis_candidate.stl"
    "01_motor_vertical_reference.stl"
    "02_drive_column_reference.stl"
    "03_vertical_rack_candidate.stl"
)
for old_file in "${POWER_BUS_CHILD_OUTPUTS[@]}"; do
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
export_part "tensioner_t_solid" "${OUT_DIR}/00_tensioner_t_solid_reference.stl" false 0
export_part "upper_spur" "${OUT_DIR}/06_upper_axis_z_spur_candidate.stl" false 0
export_part "upper_dog" "${OUT_DIR}/07_upper_downward_dog_candidate.stl" false 0
export_part "lower_dog" "${OUT_DIR}/08_lower_upward_dog_candidate.stl" false 0
export_part "rear_pulley" "${OUT_DIR}/09_rear_takeoff_timing_pulley_candidate.stl" false 0
export_part "drawer_belt" "${OUT_DIR}/13_drawer_timing_belt_reference.stl" false 0
export_part "front_pulley" "${OUT_DIR}/14_front_timing_pulley_candidate.stl" false 0
export_part "front_gear" "${OUT_DIR}/15_front_pinion_candidate.stl" false 0
export_part "drawer_rack" "${OUT_DIR}/16_drawer_linear_rack_candidate.stl" false 0

if [[ "${SHOW_LEGACY_STATIONS}" == "true" ]]; then
    export_part "spring" "${OUT_DIR}/10_clutch_spring_reference.stl" false 0
    export_part "screw" "${OUT_DIR}/11_t_countersunk_screw_reference.stl" false 0
    export_part "fork" "${OUT_DIR}/12_clutch_fork_candidate.stl" false 0
fi

# ===== 分区：原生世界坐标预览 =====
# cabinet_clutch.scad is authored in X=width, Y=height, Z=depth directly.
# Regenerate the root manifest so STL mtimes bust the browser cache, then
# install the single world-assembly viewer at the server root.
[[ -f "${MANIFEST_PY}" ]] || die "未找到 STL 预览清单脚本: ${MANIFEST_PY}"
[[ -f "${PREVIEW_SOURCE_DIR}/index.html" ]] || die "未找到离合预览模板: ${PREVIEW_SOURCE_DIR}/index.html"
[[ -f "${PREVIEW_SOURCE_DIR}/app.js" ]] || die "未找到离合预览模板: ${PREVIEW_SOURCE_DIR}/app.js"
python3 "${MANIFEST_PY}" \
    --stl-dir "${OUT_DIR}" \
    --stl-dir "${OUT_CHAIN}" \
    --stl-dir "${OUT_CABINET}" \
    --stl-dir "${OUT_MOTOR}" \
    --stl-dir "${OUT_MOUNT}" \
    --stl-dir "${OUT_CHAIN_HARDWARE}" \
    --stl-dir "${OUT_CHAIN_CLUTCH}" \
    --preview-dir "${PREVIEW_DIR}" \
    --title "SmartPartsDrawer 离合张紧机构" \
    --role printed \
    --no-recursive
patch_native_preview_manifest
cp "${PREVIEW_SOURCE_DIR}/index.html" "${PREVIEW_DIR}/index.html"
cp "${PREVIEW_SOURCE_DIR}/app.js" "${PREVIEW_DIR}/app.js"
mkdir -p "${PREVIEW_DIR}/js"
cp "${PROJECT_ROOT}/web/cabinet-preview/js/cabinet-chain-play.js" "${PREVIEW_DIR}/js/cabinet-chain-play.js"

echo "完成: ${OUT_DIR}"
echo "检查报告: ${REPORT_DIR}"
echo "世界总装配预览: http://127.0.0.1:8765/"
