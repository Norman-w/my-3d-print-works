#!/usr/bin/env bash
# Export the OpenSCAD drawer clutch mechanism and run topology/size triage.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/resolve_preview_tools.sh"
SCAD_DIR="${PROJECT_ROOT}/cad/openscad/enclosure"
SCAD_FILE="cabinet_clutch.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
OUT_DIR="${PROJECT_ROOT}/output/3d-print/cabinet-clutch"
OUT_CHAIN="${PROJECT_ROOT}/output/3d-print/cabinet-chain"
REPORT_DIR="${PROJECT_ROOT}/output/inspection/cabinet-clutch"
MOTION_JSON="${OUT_CHAIN}/cabinet_chain_motion.json"
CENTER_CONTRACT_JSON="${OUT_DIR}/center_clutch_contract.json"
# The single canonical viewer is the preview server root. All view presets
# switch content/camera/opacity in this page instead of opening sub-pages.
PREVIEW_DIR="${PROJECT_ROOT}/output/3d-preview"
LEGACY_PREVIEW_DIR="${PREVIEW_DIR}/cabinet-clutch"
PREVIEW_SOURCE_DIR="${PROJECT_ROOT}/web/cabinet-preview"
# These are retained as standalone library/fit-check outputs, but are not
# published as root-page parts.  The active cabinet-chain assembly calls the
# same parametric modules in-place, so exposing both paths creates duplicate
# library entries rather than additional installed hardware.
RETIRED_ROOT_PREVIEW_GROUPS=(
    "chain-clutch"
    "chain-hardware"
    "motor-library"
    "motor-mount"
)
QUALITY="${QUALITY:-2}"
SELECTED_COLUMN="${SELECTED_COLUMN:-2}"
SELECTED_ROW="${SELECTED_ROW:-2}"
SHOW_LEGACY_STATIONS="${SHOW_LEGACY_STATIONS:-false}"
PREVIEW_PORT="${PREVIEW_PORT:-8876}"

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
    local selected_column="${5:-${SELECTED_COLUMN}}"
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
            -D "SELECTED_COLUMN=${selected_column}" \
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
    "cabinet-clutch/00_tensioner_t_solid_reference": {
        "name": "列同步张紧滑台 · SKP 参数重建",
        "color": "#aebdce",
        "visible": True,
        "role": "diagnostic",
    },
    "cabinet-clutch/cabinet_clutch_power_motor_body": {
        "name": "抽屉开合动力电机 · 竖直本体（+X末列）",
        "color": "#343a40",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/cabinet_clutch_power_motor_shaft": {
        "name": "抽屉开合动力电机 · 竖直D输出轴",
        "color": "#d6d9dc",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/cabinet_clutch_power_column_0": {
        "name": "列同步轴 C1 · Y向长花键 + 上下2GT · 6mm带宽",
        "color": "#9a77c7",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/cabinet_clutch_power_column_1": {
        "name": "列同步轴 C2 · Y向长花键 + 上下2GT · 6mm带宽",
        "color": "#9a77c7",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/cabinet_clutch_power_column_2": {
        "name": "列同步轴 C3 · Y向长花键 + 上下2GT · 6mm带宽",
        "color": "#9a77c7",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/cabinet_clutch_power_column_3": {
        "name": "列同步轴 C4 · Y向长花键 + 上下2GT · 6mm带宽",
        "color": "#9a77c7",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/cabinet_clutch_power_column_4": {
        "name": "列同步轴 C5 · Y向长花键 + 上下2GT · 6mm带宽 · 电机直连",
        "color": "#9a77c7",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/cabinet_clutch_column_sync_belt_bottom": {
        "name": "列同步2GT皮带 · 下端 · 226T/452mm/6mm",
        "color": "#ce5c31",
        "opacity": 1.0,
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/cabinet_clutch_column_sync_belt_top": {
        "name": "列同步2GT皮带 · 上端 · 226T/452mm/6mm",
        "color": "#ce5c31",
        "opacity": 1.0,
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/cabinet_clutch_column_sync_tensioner": {
        "name": "列同步张紧轮 · 上下2GT轮 + 轴（沿−X调节）",
        "color": "#f0a23b",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/center_input_rotor": {
        "name": "中心 R3C3 · 输入公轮（随滑架 +Y 接合）",
        "color": "#e2a84b",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/center_output_rotor": {
        "name": "中心 R3C3 · 输出母轮（固定位置、保持旋转）",
        "color": "#5d7885",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/center_input_carriage": {
        "name": "中心 R3C3 · 输入滑架（双转子轴承座 + 直线轴承套）",
        "color": "#748c99",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/center_linear_bearings_reference": {
        "name": "中心 R3C3 · 2×3×7×10 直线轴承（采购件参考）",
        "color": "#b7c0c8",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/center_linear_bearing_retainers": {
        "name": "中心 R3C3 · 直线轴承套前端压盖/防脱固定件",
        "color": "#8aa1ad",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/center_output_cage": {
        "name": "中心 R3C3 · 输出轴承笼（双轴承座）",
        "color": "#4c6470",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/center_guide_rails": {
        "name": "中心 R3C3 · 双侧 Ø3 金属导向杆（采购件参考）",
        "color": "#657f8c",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/center_stops": {
        "name": "中心 R3C3 · 开位/合位实体止挡",
        "color": "#d26b38",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/center_mechanism_plate": {
        "name": "中心 R3C3 · 可拆后仓机构板（4×M3）",
        "color": "#536d78",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/center_input_shaft_reference": {
        "name": "中心 R3C3 · 采购件输入 3mm D 轴（独立短轴）",
        "color": "#5c6876",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/center_output_shaft_reference": {
        "name": "中心 R3C3 · 采购件输出 3mm D 轴（独立短轴）",
        "color": "#5c6876",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/center_input_bearings_reference": {
        "name": "中心 R3C3 · 输入 2×3×6×2 轴承（采购件参考）",
        "color": "#cfd4da",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/center_output_bearings_reference": {
        "name": "中心 R3C3 · 输出 2×3×6×2 轴承（采购件参考）",
        "color": "#cfd4da",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/center_selector_shoe": {
        "name": "中心 R3C3 · 选择指磁力靴（M_engage/M_release，原生坐标）",
        "color": "#c8d3dc",
        "visible": True,
        "role": "printed",
    },
    "cabinet/cabinet_back_panel": {
        "name": "可拆背板",
        "color": "#c4a574",
        "visible": False,
        "role": "printed",
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
        "name": "蛇形链条电机 Ω 形贴合固定套（下向安装）",
        "color": "#56616d",
        "role": "printed",
    },
    "cabinet-chain/cabinet_chain_motor_spring_hardware": {
        "name": "蛇链电机固定座·四组硬弹簧与下压蘑菇头螺丝",
        "color": "#c9a227",
        "role": "purchased",
    },
    "cabinet-chain/cabinet_chain_motor_tensioner": {
        "name": "旧蛇形电机张紧螺杆（源文件保留，默认隐藏）",
        "color": "#c9a227",
        "role": "printed",
        "visible": False,
    },
    "cabinet-chain/cabinet_chain_sprockets": {
        "name": "12T 尖齿唯一主动轮（D 轴）",
        "color": "#5b9fd6",
        "role": "printed",
    },
    "cabinet-chain/cabinet_chain_idlers": {
        "name": "12T/8T 绿色钝齿轴承导向轮",
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
    "cabinet-chain/cabinet_chain_selector_magnetic_shoe": {
        "name": "旧方案1·链条坐标磁力靴（文件保留，默认隐藏）",
        "color": "#c8d3dc",
        "role": "diagnostic",
        "visible": False,
    },
    "cabinet-chain/cabinet_chain_scheme1_power_wheels": {"name": "旧方案1·常转动力轮（文件保留，默认隐藏）", "visible": False, "role": "diagnostic"},
    "cabinet-chain/cabinet_chain_scheme1_output_wheels": {"name": "旧方案1·抽屉受力轮（文件保留，默认隐藏）", "visible": False, "role": "diagnostic"},
    "cabinet-chain/cabinet_chain_scheme1_clutch_faces": {"name": "旧方案1·狗牙离合面（文件保留，默认隐藏）", "visible": False, "role": "diagnostic"},
    "cabinet-chain/cabinet_chain_scheme1_bearings": {"name": "旧方案1·抽屉输出轴承（文件保留，默认隐藏）", "visible": False, "role": "purchased"},
    "cabinet-chain/cabinet_chain_scheme1_selector": {"name": "旧方案1·链条拨叉/8T 选择轮（文件保留，默认隐藏）", "visible": False, "role": "diagnostic"},
}
group_map = {
    "cabinet_clutch_cabinet": "00·柜体与格口",
    "cabinet_clutch_cabinet_context": "00·柜体与格口",
    "00_tensioner_t_solid_reference": "01·动力母线",
    "cabinet_clutch_power_motor_body": "01·动力母线",
    "cabinet_clutch_power_motor_shaft": "01·动力母线",
    "cabinet_clutch_power_column_0": "01·动力母线",
    "cabinet_clutch_power_column_1": "01·动力母线",
    "cabinet_clutch_power_column_2": "01·动力母线",
    "cabinet_clutch_power_column_3": "01·动力母线",
    "cabinet_clutch_power_column_4": "01·动力母线",
    "cabinet_clutch_column_sync_belt_bottom": "01·动力母线",
    "cabinet_clutch_column_sync_belt_top": "01·动力母线",
    "cabinet_clutch_column_sync_tensioner": "01·动力母线",
    "center_input_rotor": "02·离合机构",
    "center_output_rotor": "02·离合机构",
    "center_input_carriage": "02·离合机构",
    "center_linear_bearings_reference": "02·离合机构",
    "center_linear_bearing_retainers": "02·离合机构",
    "center_output_cage": "02·离合机构",
    "center_guide_rails": "02·离合机构",
    "center_stops": "02·离合机构",
    "center_mechanism_plate": "02·离合机构",
    "center_input_shaft_reference": "02·离合机构",
    "center_output_shaft_reference": "02·离合机构",
    "center_input_bearings_reference": "02·离合机构",
    "center_output_bearings_reference": "02·离合机构",
    "center_selector_shoe": "02·离合机构",
    "10_clutch_spring_reference": "02·离合机构",
    "11_t_countersunk_screw_reference": "02·离合机构",
    "12_clutch_fork_candidate": "02·离合机构",
    "13_drawer_timing_belt_reference": "03·抽屉驱动",
    "14_front_timing_pulley_candidate": "03·抽屉驱动",
    "15_front_pinion_candidate": "03·抽屉驱动",
    "16_drawer_linear_rack_candidate": "03·抽屉驱动",
}
name_map = {
    "cabinet_clutch_cabinet": "柜体外壳（可见背景）",
    "cabinet_clutch_cabinet_context": "柜体格口与抽屉背景",
    "00_tensioner_t_solid_reference": "右侧张紧滑台 · SKP 参数化",
    "center_input_rotor": "中心 R3C3 输入公轮 · 12T/3mm + 圆角公牙",
    "center_output_rotor": "中心 R3C3 输出母轮 · 母槽 + 12T/2GT",
    "center_input_carriage": "中心 R3C3 输入滑架 · 随 +Y 行程移动 · 直线轴承套",
    "center_linear_bearings_reference": "中心 R3C3 2×3×7×10 直线轴承 · 采购件",
    "center_linear_bearing_retainers": "中心 R3C3 直线轴承套压盖 · 打印防脱固定件",
    "center_output_cage": "中心 R3C3 输出轴承笼 · 固定旋转支撑",
    "center_guide_rails": "中心 R3C3 双侧 Ø3 金属导向杆 · 采购件参考",
    "center_stops": "中心 R3C3 实体止挡 · 开位 + 合位",
    "center_mechanism_plate": "中心 R3C3 可拆后仓机构板 · 4×M3",
    "center_input_shaft_reference": "中心 R3C3 输入独立 3mm D 轴 · 采购件",
    "center_output_shaft_reference": "中心 R3C3 输出独立 3mm D 轴 · 采购件",
    "center_input_bearings_reference": "中心 R3C3 输入 2×3×6×2 轴承 · 采购件",
    "center_output_bearings_reference": "中心 R3C3 输出 2×3×6×2 轴承 · 采购件",
    "10_clutch_spring_reference": "旧离合压簧 · legacy 默认隐藏",
    "11_t_countersunk_screw_reference": "旧 T 形沉头螺丝 · legacy 默认隐藏",
    "12_clutch_fork_candidate": "旧离合拨叉 · legacy 默认隐藏",
    "13_drawer_timing_belt_reference": "中心格新版2GT皮带 · 80T/160mm/6mm",
    "14_front_timing_pulley_candidate": "中心格新版前端2GT同步轮",
    "15_front_pinion_candidate": "中心格新版前端粗齿驱动轮",
    "16_drawer_linear_rack_candidate": "中心格新版抽屉底部直线齿排",
    "cabinet_clutch_power_motor_body": "抽屉开合动力电机 · 竖直本体（+X末列）",
    "cabinet_clutch_power_motor_shaft": "抽屉开合动力电机 · 竖直D输出轴",
    "cabinet_clutch_power_column_0": "列同步轴 C1 · Y向长花键 + 上下2GT",
    "cabinet_clutch_power_column_1": "列同步轴 C2 · Y向长花键 + 上下2GT",
    "cabinet_clutch_power_column_2": "列同步轴 C3 · Y向长花键 + 上下2GT",
    "cabinet_clutch_power_column_3": "列同步轴 C4 · Y向长花键 + 上下2GT",
    "cabinet_clutch_power_column_4": "列同步轴 C5 · Y向长花键 + 上下2GT · 电机直连",
    "cabinet_clutch_column_sync_belt_bottom": "列同步2GT皮带 · 下端 · 226T/452mm/6mm",
    "cabinet_clutch_column_sync_belt_top": "列同步2GT皮带 · 上端 · 226T/452mm/6mm",
    "cabinet_clutch_column_sync_tensioner": "列同步张紧轮 · 上下2GT轮 + 轴（沿−X调节）",
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

def call_node(node_id, name, description="", children=None):
    node = {"id": f"call:{node_id}", "kind": "call", "name": name}
    if description:
        node["description"] = description
    if children:
        node["children"] = [child for child in children if child]
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
        motor_shaft = part_node(
            "cabinet-clutch/cabinet_clutch_power_motor_shaft",
        )
        motor_body = part_node(
            "cabinet-clutch/cabinet_clutch_power_motor_body",
            children=[motor_shaft],
        )
        active_power_parts = [
            motor_body,
            *[
                part_node(
                    f"cabinet-clutch/cabinet_clutch_power_column_{column}"
                )
                for column in range(5)
            ],
            part_node(
                "cabinet-clutch/cabinet_clutch_column_sync_belt_bottom",
            ),
            part_node(
                "cabinet-clutch/cabinet_clutch_column_sync_belt_top",
            ),
            part_node(
                "cabinet-clutch/00_tensioner_t_solid_reference",
            ),
            part_node(
                "cabinet-clutch/cabinet_clutch_column_sync_tensioner",
            ),
        ]
        root["children"] = [
            call_node(
                "power_bus/active",
                "列同步动力母线 · 电机 + 5列2GT + 上下同步带 + 张紧轮",
                "power_motor_vertical() + vertical_gear_column(0 .. N_COL - 1) + power_column_sync_belts()",
                children=active_power_parts,
            ),
        ]
    elif group_id == "02·离合机构":
        active_center = [
            part_node("cabinet-clutch/center_input_rotor"),
            part_node("cabinet-clutch/center_output_rotor"),
            part_node("cabinet-clutch/center_input_carriage"),
            part_node("cabinet-clutch/center_linear_bearings_reference"),
            part_node("cabinet-clutch/center_linear_bearing_retainers"),
            part_node("cabinet-clutch/center_output_cage"),
            part_node("cabinet-clutch/center_guide_rails"),
            part_node("cabinet-clutch/center_stops"),
            part_node("cabinet-clutch/center_mechanism_plate"),
            part_node("cabinet-clutch/center_input_shaft_reference"),
            part_node("cabinet-clutch/center_output_shaft_reference"),
            part_node("cabinet-clutch/center_input_bearings_reference"),
            part_node("cabinet-clutch/center_output_bearings_reference"),
            part_node("cabinet-clutch/center_selector_shoe"),
        ]
        legacy_center = [
            part_node("cabinet-clutch/06_upper_axis_y_spur_candidate"),
            part_node("cabinet-clutch/06_upper_axis_z_spur_candidate"),
            part_node("cabinet-clutch/07_upper_downward_dog_candidate"),
            part_node("cabinet-clutch/08_lower_upward_dog_candidate"),
            part_node("cabinet-clutch/09_rear_takeoff_timing_pulley_candidate"),
            part_node("cabinet-clutch/10_clutch_spring_reference"),
            part_node("cabinet-clutch/11_t_countersunk_screw_reference"),
            part_node("cabinet-clutch/12_clutch_fork_candidate"),
        ]
        root["children"] = [
            call_node(
                "center_clutch/active",
                "中心 R3C3 · 单站纯永磁离合",
                "输入公轮 + 输出母轮 + 滑架 + 2×3×7×10直线轴承 + 轴承套/压盖 + 双轴承笼 + 双Ø3金属导杆 + 实体止挡 + 可拆机构板 + 磁力靴",
                children=active_center,
            ),
            call_node(
                "center_clutch/legacy",
                "legacy 诊断项（默认隐藏）",
                "旧 upper/lower、弹簧、螺丝、拨叉仅保留源与显式诊断清单，不参与默认总装",
                children=legacy_center,
            ),
        ]
    elif group_id == "03·抽屉驱动":
        root["children"] = [
            part_node(
                "cabinet-clutch/13_drawer_timing_belt_reference",
            ),
            part_node(
                "cabinet-clutch/14_front_timing_pulley_candidate",
            ),
            part_node(
                "cabinet-clutch/15_front_pinion_candidate",
            ),
            part_node(
                "cabinet-clutch/16_drawer_linear_rack_candidate",
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
mkdir -p "${OUT_DIR}" "${OUT_CHAIN}" "${REPORT_DIR}"

# Generate the motion contract from the OpenSCAD parameter echo before the
# chain solver writes its JSON. The solver then copies this exact object into
# the motion file; JavaScript never owns a second set of clutch dimensions.
python3 "${PROJECT_ROOT}/scripts/generate_center_clutch_contract.py" \
    --openscad "${OPENSCAD_BIN}" \
    --scad "${SCAD_DIR}/${SCAD_FILE}" \
    --output "${CENTER_CONTRACT_JSON}"

# The canonical page owns the chain animation as well as the meshes.  Refresh
# the solver output here so the motion path uses the same generated pin loop
# that cabinet_chain.scad and cabinet_motor_mount_params.scad consume.
python3 "${PROJECT_ROOT}/scripts/solve_cabinet_chain.py"
[[ -s "${MOTION_JSON}" ]] || die "未生成蛇链运动路径: ${MOTION_JSON}"

# Remove the old child-page output and the unrelated legacy root page/assets.
# These are generated preview artifacts, not source models; the root viewer
# below is the only supported browser entry for this assembly.
if [[ -d "${LEGACY_PREVIEW_DIR}" ]]; then
    rm -rf "${LEGACY_PREVIEW_DIR}"
fi
rm -f "${PREVIEW_DIR}/drive.html"
rm -rf "${PREVIEW_DIR}/js"

# Remove retired standalone library links from the root preview.  Their STL
# files remain under output/3d-print for independent fit checks and exports;
# only the duplicate root-page model-library folders are removed.
for retired_group in "${RETIRED_ROOT_PREVIEW_GROUPS[@]}"; do
    if [[ -d "${PREVIEW_DIR}/models/${retired_group}" ]]; then
        rm -rf "${PREVIEW_DIR}/models/${retired_group}"
    fi
done
# The old local-frame cabinet export is also retained for standalone checks,
# but the canonical world scene already publishes its own cabinet shell and
# context.  Keeping both produces a coincident second cabinet (and its old
# mount envelope) in the browser.
if [[ -d "${PREVIEW_DIR}/models/cabinet" ]]; then
    rm -rf "${PREVIEW_DIR}/models/cabinet"
fi

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

# The root viewer is assembled from the individual parts below. Remove every
# old merged/check body before regenerating the manifest; retaining one of them
# would make the tree show a second copy of the mechanism and would mask which
# real part is being animated.
MERGED_CHECK_OUTPUTS=(
    "cabinet_clutch_power_bus.stl"
    "cabinet_clutch_drawer_drive.stl"
    "cabinet_clutch_all_clutches.stl"
    "cabinet_clutch_detail_open.stl"
    "cabinet_clutch_detail_engaged.stl"
    "cabinet_clutch_assembly.stl"
)
for old_file in "${MERGED_CHECK_OUTPUTS[@]}"; do
    rm -f "${OUT_DIR}/${old_file}" "${REPORT_DIR}/${old_file%.stl}.json"
done

# 07/09 were generated aliases of the real 06/08 center-clutch meshes. Remove
# stale copies from older exports; the parameterized source entry points stay
# in cabinet_clutch.scad for single-part inspection and future reuse.
DUPLICATE_CLUTCH_OUTPUTS=(
    "06_upper_axis_y_spur_candidate.stl"
    "06_upper_axis_z_spur_candidate.stl"
    "08_lower_upward_dog_candidate.stl"
    "07_upper_downward_dog_candidate.stl"
    "09_rear_takeoff_timing_pulley_candidate.stl"
)
for old_file in "${DUPLICATE_CLUTCH_OUTPUTS[@]}"; do
    rm -f "${OUT_DIR}/${old_file}" "${REPORT_DIR}/${old_file%.stl}.json"
done

# The selector shoe moved from the old scheme1 chain frame into the native
# cabinet-clutch export. Remove its stale chain-frame preview so a refresh can
# never show two magnetic actuators at different coordinate origins.
LEGACY_CHAIN_SELECTOR_OUTPUTS=(
    "cabinet_chain_selector_magnetic_shoe.stl"
)
for old_file in "${LEGACY_CHAIN_SELECTOR_OUTPUTS[@]}"; do
    rm -f "${OUT_CHAIN}/${old_file}" \
        "${REPORT_DIR}/${old_file%.stl}.json" \
        "${REPORT_DIR}/${old_file%.stl}.watertight.json"
done

# These generated child previews used to be loaded at the same coordinates and
# duplicated the motor, D shaft, and column shaft. Keep their parametric SCAD
# entry points, but do not publish duplicate root list items.
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
export_part "motor_body" "${OUT_DIR}/cabinet_clutch_power_motor_body.stl" false 0
export_part "motor_shaft" "${OUT_DIR}/cabinet_clutch_power_motor_shaft.stl" false 0
for column in 0 1 2 3 4; do
    export_part "column" "${OUT_DIR}/cabinet_clutch_power_column_${column}.stl" false 0 "${column}"
done
export_part "column_sync_belt_bottom" "${OUT_DIR}/cabinet_clutch_column_sync_belt_bottom.stl" false 0
export_part "column_sync_belt_top" "${OUT_DIR}/cabinet_clutch_column_sync_belt_top.stl" false 0
export_part "column_sync_tensioner" "${OUT_DIR}/cabinet_clutch_column_sync_tensioner.stl" false 0

# The root page also owns the snake drive.  Export its motor sleeve here so a
# canonical refresh can never leave an older motor-cover STL beside the new
# native drawer-drive parts.  CHAIN_PART is namespaced because cabinet_chain.scad
# includes libraries that also define PART.
export_chain_motor_cover() {
    local target="${OUT_CHAIN}/cabinet_chain_motor_cover.stl"
    local tmp="${target}.tmp.$$"
    echo "→ CHAIN_PART=motor_cover → ${target}"
    (
        cd "${PROJECT_ROOT}/cad/openscad/enclosure"
        "${OPENSCAD_BIN}" \
            --backend Manifold \
            --export-format binstl \
            -D "QUALITY=${QUALITY}" \
            -D 'CHAIN_PART="motor_cover"' \
            -o "${tmp}" \
            "cabinet_chain.scad"
    )
    [[ -s "${tmp}" ]] || die "空 STL: ${target}"
    mv -f "${tmp}" "${target}"
    if [[ -x "${INSPECT_PY}" || -f "${INSPECT_PY}" ]]; then
        python3 "${INSPECT_PY}" "${target}" --json --output "${REPORT_DIR}/cabinet_chain_motor_cover.json"
    fi
}

export_chain_motor_cover

export_chain_part() {
    local chain_part="$1"
    local target="$2"
    local tmp="${target}.tmp.$$"
    echo "→ CHAIN_PART=${chain_part} → ${target}"
    (
        cd "${PROJECT_ROOT}/cad/openscad/enclosure"
        "${OPENSCAD_BIN}" \
            --backend Manifold \
            --export-format binstl \
            -D "QUALITY=${QUALITY}" \
            -D "CHAIN_PART=\"${chain_part}\"" \
            -o "${tmp}" \
            "cabinet_chain.scad"
    )
    [[ -s "${tmp}" ]] || die "空 STL: ${target}"
    mv -f "${tmp}" "${target}"
    if [[ -x "${INSPECT_PY}" || -f "${INSPECT_PY}" ]]; then
        python3 "${INSPECT_PY}" "${target}" --json \
            --output "${REPORT_DIR}/$(basename "${target}" .stl).json"
    fi
}

require_watertight_print_part() {
    local target="$1"
    local report_name
    report_name="$(basename "${target}" .stl).watertight.json"
    [[ -f "${INSPECT_PY}" ]] || die "未找到可打印件闭合检查所需的 inspect_stl.py: ${INSPECT_PY}"
    echo "→ require-watertight → ${target}"
    python3 "${INSPECT_PY}" "${target}" --require-watertight --json \
        --output "${REPORT_DIR}/${report_name}"
}

# ===== 分区：逐件输出 =====
# These are intentionally emitted in mechanism order so a failed fit can be
# corrected without hiding it inside a full assembly export.
export_part "tensioner_t_solid" "${OUT_DIR}/00_tensioner_t_solid_reference.stl" false 0
export_part "center_input_rotor" "${OUT_DIR}/center_input_rotor.stl" false 0
export_part "center_output_rotor" "${OUT_DIR}/center_output_rotor.stl" false 0
export_part "center_input_carriage" "${OUT_DIR}/center_input_carriage.stl" false 0
export_part "center_output_cage" "${OUT_DIR}/center_output_cage.stl" false 0
export_part "center_guide_rails" "${OUT_DIR}/center_guide_rails.stl" false 0
export_part "center_linear_bearings" "${OUT_DIR}/center_linear_bearings_reference.stl" false 0
export_part "center_linear_bearing_retainers" "${OUT_DIR}/center_linear_bearing_retainers.stl" false 0
export_part "center_stops" "${OUT_DIR}/center_stops.stl" false 0
export_part "center_mechanism_plate" "${OUT_DIR}/center_mechanism_plate.stl" false 0
export_part "center_input_shaft" "${OUT_DIR}/center_input_shaft_reference.stl" false 0
export_part "center_output_shaft" "${OUT_DIR}/center_output_shaft_reference.stl" false 0
export_part "center_input_bearings" "${OUT_DIR}/center_input_bearings_reference.stl" false 0
export_part "center_output_bearings" "${OUT_DIR}/center_output_bearings_reference.stl" false 0
export_part "center_selector_shoe" "${OUT_DIR}/center_selector_shoe.stl" false 0

# The center printed pieces and the selector shoe are the current first-article
# outputs. Keep purchased shaft/bearing/guide-rod references in the ordinary
# inspection report, but require closed topology for every printable center
# component.
for printable_part in \
    "${OUT_DIR}/center_input_rotor.stl" \
    "${OUT_DIR}/center_output_rotor.stl" \
    "${OUT_DIR}/center_input_carriage.stl" \
    "${OUT_DIR}/center_linear_bearing_retainers.stl" \
    "${OUT_DIR}/center_output_cage.stl" \
    "${OUT_DIR}/center_stops.stl" \
    "${OUT_DIR}/center_mechanism_plate.stl" \
    "${OUT_DIR}/center_selector_shoe.stl"; do
    require_watertight_print_part "${printable_part}"
done

export_part "drawer_belt" "${OUT_DIR}/13_drawer_timing_belt_reference.stl" false 0
export_part "front_pulley" "${OUT_DIR}/14_front_timing_pulley_candidate.stl" false 0
export_part "front_gear" "${OUT_DIR}/15_front_pinion_candidate.stl" false 0
export_part "drawer_rack" "${OUT_DIR}/16_drawer_linear_rack_candidate.stl" false 0

if [[ "${SHOW_LEGACY_STATIONS}" == "true" ]]; then
    export_part "spring" "${OUT_DIR}/10_clutch_spring_reference.stl" false 0
    export_part "screw" "${OUT_DIR}/11_t_countersunk_screw_reference.stl" false 0
    export_part "fork" "${OUT_DIR}/12_clutch_fork_candidate.stl" false 0
fi

# Run the center-only open/engaged sweep in a temporary directory. This checks
# the actual OpenSCAD positions and keeps analytic motion/clearance regressions
# out of the browser manifest; it is still not a substitute for the printed
# bearing, magnet and 20-cycle physical gate.
[[ -f "${INSPECT_PY}" ]] || die "未找到中心离合几何检查所需的 inspect_stl.py: ${INSPECT_PY}"
python3 "${PROJECT_ROOT}/scripts/validate_center_clutch_geometry.py" \
    --openscad "${OPENSCAD_BIN}" \
    --scad "${SCAD_DIR}/${SCAD_FILE}" \
    --contract "${CENTER_CONTRACT_JSON}" \
    --inspect "${INSPECT_PY}"

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
    --preview-dir "${PREVIEW_DIR}" \
    --title "SmartPartsDrawer 离合张紧机构" \
    --role printed \
    --no-recursive
patch_native_preview_manifest
cp "${PREVIEW_SOURCE_DIR}/index.html" "${PREVIEW_DIR}/index.html"
cp "${PREVIEW_SOURCE_DIR}/app.js" "${PREVIEW_DIR}/app.js"
mkdir -p "${PREVIEW_DIR}/js"
cp "${PROJECT_ROOT}/web/cabinet-preview/js/cabinet-chain-play.js" "${PREVIEW_DIR}/js/cabinet-chain-play.js"
mkdir -p "${PREVIEW_DIR}/models/cabinet-chain"
ln -sfn "${MOTION_JSON}" "${PREVIEW_DIR}/models/cabinet-chain/cabinet_chain_motion.json"

echo "完成: ${OUT_DIR}"
echo "检查报告: ${REPORT_DIR}"
echo "世界总装配预览: http://127.0.0.1:${PREVIEW_PORT}/"
