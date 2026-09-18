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
# R3C3 is zero-based (col=2,row=1).  The assembly itself already defaults to
# row 1; keeping the one-by-one drawer-drive exports on row 2 silently mixed
# the center clutch with the third drawer layer and produced a legacy 20T
# timing belt under the "center 2GT" labels.
SELECTED_ROW="${SELECTED_ROW:-1}"
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
# The root preview owns one cabinet frame.  The old closed shell and the old
# wire/grid context were coincident alternatives, not additional hardware.
# Drop both IDs from the manifest and remove their generated links so stale
# output cannot reappear after a refresh.
obsolete_cabinet_ids = {
    "cabinet-clutch/cabinet_clutch_cabinet",
    "cabinet-clutch/cabinet_clutch_cabinet_context",
}
payload["parts"] = [
    part for part in payload.get("parts", [])
    if part.get("id") not in obsolete_cabinet_ids
]
models_dir = path.parent / "models" / "cabinet-clutch"
for stale_name in (
    "cabinet_clutch_cabinet.stl",
    "cabinet_clutch_cabinet_context.stl",
):
    stale_path = models_dir / stale_name
    if stale_path.exists() or stale_path.is_symlink():
        stale_path.unlink()
labels = {
    "cabinet-clutch/cabinet_clutch_cabinet_frame": {
        "name": "箱体框架·上下左右外框 + 左侧服务回程立板 + X+立板 + 前部层格/立格 + 后仓贯通 + 前下实体面（前后仓隔板另列）",
        "color": "#6f8f9a",
        "opacity": 0.30,
        "visible": True,
    },
    "cabinet-clutch/cabinet_clutch_partition": {
        "name": "前后仓隔板·5×3抽屉格统一2GT皮带通孔 + 每格四角 Boss（独立安装件）",
        "group": "00·箱体框架",
        "color": "#91a7b2",
        "opacity": 1.0,
        "visible": False,
        "role": "printed",
    },
    "cabinet-clutch/17_drawer_rack_guide_rollers_reference": {
        "name": "中心格·抽屉 C 形槽 681 导向轴承×4（1×3×1；X轴向）",
        "color": "#cfd4da",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/18_drawer_rack_guide_rails_candidate": {
        "name": "中心格·左右内开口 C 形导向槽×2（Z向；尾部滚轮+前端下托）",
        "color": "#657f8c",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/22_front_timing_bearing_reference": {
        "name": "中心格·前端主动轮层板内 MR63/3×6×2 轴承（采购件）",
        "color": "#cfd4da",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/23_front_d_axis_reference": {
        "name": "中心格·前端主动轮到同步轮短 D 轴",
        "color": "#5c6876",
        "visible": True,
        "role": "purchased",
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
        "name": "中心 R3C3 · 输入公轮（随 D-round-D 轴 +Y 接合）",
        "color": "#718b99",
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
        "name": "legacy · 中心 R3C3 输入滑架（已移除）",
        "color": "#748c99",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/center_linear_bearings_reference": {
        "name": "中心 R3C3 · 固定 LM3UU×1 · Ø3×Ø7×10（与公轮同轴；采购件）",
        "color": "#b7c0c8",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/center_linear_bearing_retainers": {
        "name": "中心 R3C3 · 直线轴承套压盖×1（单个；打印防脱件）",
        "color": "#8aa1ad",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/center_linear_bearing_fit_coupon": {
        "name": "中心 R3C3 · LM3UU 长方条轴承孔配合测试片（默认隐藏）",
        "color": "#788a95",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/center_guide_rails": {
        "name": "legacy · 中心 R3C3 独立导轨（已移除）",
        "color": "#657f8c",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/center_stops": {
        "name": "legacy · 中心 R3C3 开合止挡（已移除）",
        "color": "#536d78",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/center_mechanism_plate": {
        "name": "中心 R3C3 · 可拆后仓机构板（四角孔 + 每格四角 Boss 自攻固定；一体 LM3UU + 输出双轴承长方条）",
        "color": "#536d78",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/center_input_shaft_reference": {
        "name": "中心 R3C3 · 采购件输入 D-round-D 阶梯轴（上D/圆滑动段/下D）",
        "color": "#5c6876",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/center_output_shaft_reference": {
        "name": "中心 R3C3 · 采购件输出 D-round 短轴（母轮D段 + 双轴承圆轴）",
        "color": "#5c6876",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/center_input_bearings_reference": {
        "name": "legacy · 中心 R3C3 输入旋转轴承组（已移除）",
        "color": "#cfd4da",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/center_output_bearings_reference": {
        "name": "中心 R3C3 · 输出双枚 3×6×2 径向轴承（同一体长方条上下固定；采购件）",
        "color": "#cfd4da",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/center_selector_shoe": {
        "name": "legacy · 中心 R3C3 选择指磁力靴（待按 M5 圆套重定位）",
        "color": "#c8d3dc",
        "visible": False,
        "role": "diagnostic",
    },
    "cabinet-clutch/center_input_sleeve": {
        "name": "中心 R3C3 · 公轮底部 D 型圆套（下端 Ø8 圆形；Ø5×5 磁铁盲槽）",
        "color": "#7c909d",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/center_input_sleeve_magnet_reference": {
        "name": "中心 R3C3 · 圆套内 Ø5×5 圆柱磁铁（采购件）",
        "color": "#5b6670",
        "visible": True,
        "role": "purchased",
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
        "name": "8T 小尺寸绿色钝齿轴承导向轮（8颗）",
        "color": "#7dcc4a",
        "role": "printed",
    },
    "cabinet-chain/cabinet_chain_plates": {"name": "03C 蛇形链板", "color": "#8A919C", "role": "purchased"},
    "cabinet-chain/cabinet_chain_rollers": {"name": "03C 滚子", "color": "#E8EDF2", "role": "purchased"},
    "cabinet-chain/cabinet_chain_pins": {"name": "03C 销轴", "color": "#B08D57", "role": "purchased"},
    "cabinet-chain/cabinet_chain_bearings": {"name": "3×6×2 轴承（装配显示/采购件）", "color": "#b9c2ca", "role": "purchased"},
    "cabinet-chain/cabinet_chain_clutch_trigger_magnet": {
        "name": "蛇形链条·链节 Z− 触发磁铁（Ø2×1.8 采购件参考）",
        "color": "#5b6670",
        "role": "purchased",
    },
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
    "cabinet_clutch_cabinet_frame": "00·箱体框架",
    "cabinet_clutch_partition": "00·箱体框架",
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
    "center_input_sleeve": "02·离合机构",
    "center_input_sleeve_magnet_reference": "02·离合机构",
    "center_input_carriage": "02·离合机构",
    "center_linear_bearings_reference": "02·离合机构",
    "center_linear_bearing_retainers": "02·离合机构",
    "center_linear_bearing_fit_coupon": "02·离合机构",
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
    "17_drawer_rack_guide_rollers_reference": "03·抽屉驱动",
    "18_drawer_rack_guide_rails_candidate": "03·抽屉驱动",
    "22_front_timing_bearing_reference": "03·抽屉驱动",
    "23_front_d_axis_reference": "03·抽屉驱动",
}
name_map = {
    "cabinet_clutch_cabinet_frame": "箱体框架（上下左右外框 + 左侧服务回程立板 + X+立板 + 前部层格/立格 + 后仓贯通 + 前下实体面；前后仓隔板另列）",
    "cabinet_clutch_partition": "前后仓隔板·5×3抽屉格统一2GT皮带通孔 + 每格四角 Boss（独立安装件）",
    "00_tensioner_t_solid_reference": "右侧张紧滑台 · SKP 参数化",
    "center_input_rotor": "中心 R3C3 输入公轮 · 12T/3mm + 圆角公牙",
    "center_output_rotor": "中心 R3C3 输出母轮 · 母槽 + 12T/2GT",
    "center_input_sleeve": "中心 R3C3 公轮底部 D 型圆套 · 下端 Ø8 + Ø5×5 磁铁盲槽",
    "center_input_sleeve_magnet_reference": "中心 R3C3 圆套内 Ø5×5 圆柱磁铁 · 采购件",
    "center_input_carriage": "legacy · 中心 R3C3 输入滑架（已移除）",
    "center_linear_bearings_reference": "中心 R3C3 固定 LM3UU×1 · Ø3×Ø7×10（与公轮同轴；采购件）",
    "center_linear_bearing_retainers": "legacy · 中心 R3C3 轴承压盖（已移除）",
    "center_linear_bearing_fit_coupon": "中心 R3C3 LM3UU 长方条轴承孔配合测试片 · Ø7.20/7.30/7.40",
    "center_guide_rails": "legacy · 中心 R3C3 独立导轨（已移除）",
    "center_stops": "legacy · 中心 R3C3 实体止挡（已移除）",
    "center_mechanism_plate": "中心 R3C3 可拆后仓机构板 · 四角孔 + 每格四角 Boss 自攻固定 · 一体 LM3UU + 输出双轴承长方条",
    "center_input_shaft_reference": "中心 R3C3 输入独立 3mm D 轴 · 采购件",
    "center_output_shaft_reference": "中心 R3C3 输出 D-round 短轴 · 母轮D段 + 双轴承圆轴 · 采购件",
    "center_input_bearings_reference": "legacy · 中心 R3C3 输入旋转轴承组（已移除）",
    "center_output_bearings_reference": "中心 R3C3 输出双枚 3×6×2轴承 · 长方条上下固定 · 采购件",
    "10_clutch_spring_reference": "旧离合压簧 · legacy 默认隐藏",
    "11_t_countersunk_screw_reference": "旧 T 形沉头螺丝 · legacy 默认隐藏",
    "12_clutch_fork_candidate": "旧离合拨叉 · legacy 默认隐藏",
    "13_drawer_timing_belt_reference": "中心格新版2GT皮带 · 80T/160mm/6mm",
    "14_front_timing_pulley_candidate": "中心格新版前端2GT同步轮",
    "15_front_pinion_candidate": "中心格新版前端粗齿驱动轮",
    "16_drawer_linear_rack_candidate": "中心格新版抽屉底部直线齿排",
    "17_drawer_rack_guide_rollers_reference": "中心格抽屉 C 形槽 681 导向轴承×4（1×3×1；X轴向）",
    "18_drawer_rack_guide_rails_candidate": "中心格左右内开口 C 形导向槽×2（Z向；尾部滚轮+前端下托）",
    "22_front_timing_bearing_reference": "中心格前端主动轮层板内 MR63/3×6×2 轴承（采购件）",
    "23_front_d_axis_reference": "中心格前端主动轮到下层同步轮 3mm 短 D 轴",
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
    "00·箱体框架",
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
        input_axis = call_node(
            "center_clutch/input-axis",
            "公轮轴竖直滑动 · D-round-D + 固定 LM3UU",
            "公轮 D 轴固定后只保留 0.40 mm 外露 D 段，立即变为 Ø3 圆滑动段，直接在与离合机构板一体的 LM3UU 座（Ø3×Ø7×10）中上下滑动；最低端再变为 D 型插入圆套上方 D 孔，圆套下端为 Ø8 圆形并嵌入 Ø5×5 圆柱磁铁。轴承从一体座的贯通孔上下压入，座体除轴承孔外为实心；公轮端没有其他机构。",
            children=[
                part_node("cabinet-clutch/center_input_shaft_reference"),
                part_node("cabinet-clutch/center_input_sleeve"),
                part_node("cabinet-clutch/center_input_sleeve_magnet_reference"),
                part_node("cabinet-clutch/center_linear_bearings_reference"),
            ],
        )
        rotary_support = call_node(
            "center_clutch/rotary-support",
            "输出母轮旋转支撑 · 一体长方条上下2枚 3×6×2",
            "公轮端没有额外旋转轴承组；输出母轮保持固定位置，短 D-round 轴穿过机构板一体长方条上下两枚 3×6×2 轴承旋转支撑。长方条只有两个轴承孔，中间保留实心隔墙。",
            children=[
                part_node("cabinet-clutch/center_output_shaft_reference"),
                part_node("cabinet-clutch/center_output_bearings_reference"),
            ],
        )
        fit_coupon = call_node(
            "center_clutch/fit-coupon",
            "LM3UU 长方条轴承座配合测试片（默认隐藏）",
            "打印后实装一枚真实 Ø3×Ø7×10 LM3UU，先比较 Ø7.20/7.30/7.40 三档长方条座孔；该测试片不承担装机载荷。",
            children=[
                part_node("cabinet-clutch/center_linear_bearing_fit_coupon"),
            ],
        )
        active_center = [
            part_node("cabinet-clutch/center_input_rotor"),
            part_node("cabinet-clutch/center_output_rotor"),
            part_node("cabinet-clutch/center_mechanism_plate"),
            input_axis,
            rotary_support,
            fit_coupon,
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
                "输入公轮 + 输出母轮 + D-round-D 阶梯轴 + 机构板一体实心 LM3UU 轴承座 + D 型/Ø5×5 磁铁圆套 + 输出双轴承一体长方条 + 可拆机构板",
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
            part_node(
                "cabinet-clutch/17_drawer_rack_guide_rollers_reference",
            ),
            part_node(
                "cabinet-clutch/18_drawer_rack_guide_rails_candidate",
            ),
            part_node(
                "cabinet-clutch/22_front_timing_bearing_reference",
            ),
            part_node(
                "cabinet-clutch/23_front_d_axis_reference",
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

# The canonical page owns the chain animation as well as the meshes.  Always
# rebuild the chain meshes from the same solver invocation; otherwise a new
# motion JSON can be paired with older STL geometry and make the browser show
# chains/gears flying out of their authored layers.
CHAIN_EXPORT_SCRIPT="${PROJECT_ROOT}/scripts/export_cabinet_chain.sh"
[[ -x "${CHAIN_EXPORT_SCRIPT}" ]] || die "找不到链条同步导出脚本: ${CHAIN_EXPORT_SCRIPT}"
QUALITY="${QUALITY}" bash "${CHAIN_EXPORT_SCRIPT}"
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
# The manifest writer does not remove dangling links from an older scan.  The
# canonical cabinet-clutch folder is rebuilt below, so clear that generated
# folder first to prevent retired duplicate parts from lingering in the UI's
# model directory.
rm -rf "${PREVIEW_DIR}/models/cabinet-clutch"

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
    "center_input_carriage.stl"
    "center_guide_rails.stl"
    "center_linear_bearing_retainers.stl"
    "center_stops.stl"
    "center_input_bearings_reference.stl"
    "center_selector_shoe.stl"
    "center_linear_bearing_block.stl"
    "center_output_cage.stl"
)
for old_file in "${LEGACY_CLUTCH_OUTPUTS[@]}"; do
    rm -f "${OUT_DIR}/${old_file}" \
        "${REPORT_DIR}/${old_file%.stl}.json" \
        "${REPORT_DIR}/${old_file%.stl}.watertight.json"
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

# The front pinion bearing is now captured directly by the shelf.  Remove the
# three old standalone support/reference meshes so a refresh cannot reintroduce
# the obsolete upper-MR63 stack into the manifest.
OBSOLETE_DRAWER_DRIVE_OUTPUTS=(
    "19_front_pinion_bearing_support_candidate.stl"
    "20_front_pinion_bearings_reference.stl"
    "21_front_timing_bearing_support_candidate.stl"
)
for old_file in "${OBSOLETE_DRAWER_DRIVE_OUTPUTS[@]}"; do
    rm -f "${OUT_DIR}/${old_file}" \
        "${REPORT_DIR}/${old_file%.stl}.json" \
        "${REPORT_DIR}/${old_file%.stl}.watertight.json"
done

# The current male-end assembly uses the Ø5×5 magnet in its printed sleeve;
# neither the old chain-frame shoe nor the retired native shoe is canonical.
# Remove both stale outputs so a refresh can never show a second actuator at a
# different coordinate origin.
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

# The printable closed shell remains available from cabinet.scad.  This root
# preview exports only the one canonical open structural frame; remove older
# shell/context outputs so they cannot be scanned as duplicate root parts.
OLD_DUPLICATE_CABINET_OUTPUTS=(
    "cabinet_clutch_cabinet.stl"
    "cabinet_clutch_cabinet_context.stl"
    "cabinet_clutch_backplate.stl"
)
for old_file in "${OLD_DUPLICATE_CABINET_OUTPUTS[@]}"; do
    rm -f "${OUT_DIR}/${old_file}" \
        "${REPORT_DIR}/${old_file%.stl}.json" \
        "${REPORT_DIR}/${old_file%.stl}.watertight.json"
done
export_part "cabinet_frame" "${OUT_DIR}/cabinet_clutch_cabinet_frame.stl" false 0
export_part "cabinet_partition" "${OUT_DIR}/cabinet_clutch_partition.stl" false 0
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
export_part "center_linear_bearings" "${OUT_DIR}/center_linear_bearings_reference.stl" false 0
export_part "center_linear_bearing_fit_coupon" "${OUT_DIR}/center_linear_bearing_fit_coupon.stl" false 0
export_part "center_mechanism_plate" "${OUT_DIR}/center_mechanism_plate.stl" false 0
export_part "center_input_shaft" "${OUT_DIR}/center_input_shaft_reference.stl" false 0
export_part "center_input_sleeve" "${OUT_DIR}/center_input_sleeve.stl" false 0
export_part "center_input_sleeve_magnet" "${OUT_DIR}/center_input_sleeve_magnet_reference.stl" false 0
export_part "center_output_shaft" "${OUT_DIR}/center_output_shaft_reference.stl" false 0
export_part "center_output_bearings" "${OUT_DIR}/center_output_bearings_reference.stl" false 0

# The center printed pieces are the current first-article outputs. Purchased
# shaft/bearing/magnet references remain ordinary inspection artifacts, while
# every printable center component must be closed.
for printable_part in \
    "${OUT_DIR}/cabinet_clutch_partition.stl" \
    "${OUT_DIR}/center_input_rotor.stl" \
    "${OUT_DIR}/center_output_rotor.stl" \
    "${OUT_DIR}/center_linear_bearing_fit_coupon.stl" \
    "${OUT_DIR}/center_mechanism_plate.stl" \
    "${OUT_DIR}/center_input_sleeve.stl"; do
    require_watertight_print_part "${printable_part}"
done

export_part "drawer_belt" "${OUT_DIR}/13_drawer_timing_belt_reference.stl" false 0
export_part "front_pulley" "${OUT_DIR}/14_front_timing_pulley_candidate.stl" false 0
export_part "front_gear" "${OUT_DIR}/15_front_pinion_candidate.stl" false 0
export_part "drawer_rack" "${OUT_DIR}/16_drawer_linear_rack_candidate.stl" false 0
export_part "drawer_rack_guide_rollers" "${OUT_DIR}/17_drawer_rack_guide_rollers_reference.stl" false 0
export_part "drawer_rack_guide_rails" "${OUT_DIR}/18_drawer_rack_guide_rails_candidate.stl" false 0
export_part "front_timing_bearing" "${OUT_DIR}/22_front_timing_bearing_reference.stl" false 0
export_part "front_d_axis" "${OUT_DIR}/23_front_d_axis_reference.stl" false 0

for printable_part in \
    "${OUT_DIR}/18_drawer_rack_guide_rails_candidate.stl"; do
    require_watertight_print_part "${printable_part}"
done

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
