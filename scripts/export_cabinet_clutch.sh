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
MERGE_STL_PY="${PROJECT_ROOT}/scripts/merge_binary_stl.py"
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
            -D "SELECTED_COLUMN=${selected_column}" \
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

verify_empty_tensioner_collision_selector() {
    local tmp="${TMPDIR:-/tmp}/smartpartsdrawer-tensioner-collision.$$.stl"
    local log="${tmp%.stl}.log"
    local status=0
    echo "→ 检查上下张紧支撑与对应皮带实体交集必须为空"
    (
        cd "${SCAD_DIR}"
        "${OPENSCAD_BIN}" \
            --backend Manifold \
            --export-format binstl \
            -D "QUALITY=${QUALITY}" \
            -D 'CLUTCH_PART="column_sync_tensioner_belt_collision"' \
            -o "${tmp}" \
            "${SCAD_FILE}"
    ) >"${log}" 2>&1 || status=$?
    if [[ -s "${tmp}" ]]; then
        local triangles
        triangles="$(python3 -c 'import struct,sys; data=open(sys.argv[1], "rb").read(); print(struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else 0)' "${tmp}")"
        rm -f "${tmp}" "${log}"
        [[ "${triangles}" == "0" ]] || die "上下张紧支撑与对应皮带发生实体干涉: ${triangles} triangles"
    else
        rm -f "${tmp}" "${log}"
    fi
    # OpenSCAD returns non-zero for an intentionally empty top-level object;
    # that is the expected success state for this diagnostic selector.
    [[ "${status}" == "0" || "${status}" == "1" ]] \
        || die "上下张紧支撑干涉检查执行失败: exit ${status}"
    return 0
}

verify_empty_tensioner_capture_selector() {
    local tmp="${TMPDIR:-/tmp}/smartpartsdrawer-tensioner-capture.$$.stl"
    local log="${tmp%.stl}.log"
    local rc=0
    echo "→ 检查张紧机构固定 C 与移动 T/滑台在全行程实体交集必须为空"
    (
        cd "${SCAD_DIR}"
        "${OPENSCAD_BIN}" \
            --backend Manifold \
            --export-format binstl \
            -D "QUALITY=${QUALITY}" \
            -D 'CLUTCH_PART="column_sync_tensioner_capture_collision"' \
            -o "${tmp}" \
            "${SCAD_FILE}"
    ) >"${log}" 2>&1 || rc=$?
    if [[ -s "${tmp}" ]]; then
        local triangles
        triangles="$(python3 -c 'import struct,sys; data=open(sys.argv[1], "rb").read(); print(struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else 0)' "${tmp}")"
        rm -f "${tmp}" "${log}"
        [[ "${triangles}" == "0" ]] || die "张紧机构固定 C 与移动 T/滑台发生实体干涉: ${triangles} triangles"
    else
        rm -f "${tmp}" "${log}"
    fi
    [[ "${rc}" == "0" || "${rc}" == "1" ]] \
        || die "张紧机构固定 C/T 全行程干涉检查执行失败: exit ${rc}"
    return 0
}

patch_native_preview_manifest() {
    python3 - "${PREVIEW_DIR}/manifest.json" "${CENTER_CONTRACT_JSON}" <<'PY'
from pathlib import Path
import json
import math
import sys

path = Path(sys.argv[1])
contract_path = Path(sys.argv[2])
payload = json.loads(path.read_text(encoding="utf-8"))
contract = json.loads(contract_path.read_text(encoding="utf-8"))["centerClutch"]
payload["up"] = "y"
# The browser manifest is the installed-world assembly, not a catch-all CAD
# library. Fit coupons, retired T-shaped tensioners, highlighted chain
# connectors, and every other diagnostic-only artifact stay out of it. The
# Each animated station component is still one shared STL source. The browser
# instantiates that source fourteen times around the native R3C3 first article;
# no merged kit is published because one merged mesh cannot move a drawer,
# belt, clutch rotor, and fixed guide independently.
retired_ids = {
    "cabinet-clutch/00_tensioner_t_solid_reference",
    "cabinet-clutch/center_linear_bearing_fit_coupon",
    # Diagnostic-only cheek/bar preview.  The production cheek and the new
    # green-idler Bosses are already fused into center_mechanism_plate; keeping
    # this old world-space STL visible creates a coplanar duplicate in Three.js.
    "cabinet-clutch/center_chain_emboss_detail",
    "cabinet-chain/cabinet_chain_connector",
    "cabinet-chain/cabinet_chain_clutch_connector",
    "cabinet-chain/cabinet_chain_clutch_bearing",
    "cabinet-clutch/17_drawer_rack_guide_rollers_reference",
    "cabinet-clutch/24_center_station_kit_template",
}
all_parts = payload.get("parts", [])
kept_parts = []
for part in all_parts:
    part_id = str(part.get("id", ""))
    retired = (
        part_id in retired_ids
        or part.get("role") == "diagnostic"
        or part_id.startswith("cabinet/")
        or part_id.startswith("ch1_03c_")
    )
    if retired:
        stale_path = path.parent / str(part.get("file", ""))
        if stale_path.is_file() or stale_path.is_symlink():
            stale_path.unlink()
        continue
    kept_parts.append(part)
payload["parts"] = kept_parts
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
        "name": "箱体框架·上下左右外框 + x+/x-/y+/y-四边各两套前后仓隔板D泪滴耳接收件 + 屋顶8个花键轴承Boss + 左侧服务回程立板 + X+立板 + 前部层格/立格 + 后仓贯通 + 前下实体面 + 蛇链电机四点Boss（隔板另列）",
        "color": "#6f8f9a",
        "opacity": 0.30,
        "visible": True,
    },
    "cabinet-clutch/cabinet_clutch_partition": {
        "name": "前后仓隔板·内净尺寸 + 四边各两套D泪滴耳接收/开放D环全外轮廓承压外套 + x-/y-紧凑贯通服务口 + 宽承力网格 + 5×3皮带通孔 + 每格四角离合板Boss（独立安装件）",
        "group": "00·箱体框架",
        "color": "#91a7b2",
        "opacity": 1.0,
        "visible": False,
        "role": "printed",
    },
    "cabinet-clutch/17_drawer_tail_guide_rollers_reference": {
        "name": "中心格·抽屉尾部随动 681 导向轴承×2（1×3×1；X轴向）",
        "color": "#cfd4da",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/19_drawer_front_lower_guide_bearings_reference": {
        "name": "中心格·C形槽前端下托 681 固定轴承×2（1×3×1；X轴向）",
        "color": "#cfd4da",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/18_drawer_rack_guide_rails_candidate": {
        "name": "中心格·立板一体内向 C 槽唇边×2（Z向；尾部滚轮+前端下托）",
        "color": "#657f8c",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/20_drawer_body_candidate": {
        "name": "中心格·真实抽屉壳体（共享源件；底部齿排让位 + 两侧 C 槽/681 让位；随 +Z 运动）",
        "color": "#d3b184",
        "opacity": 0.22,
        "visible": True,
        "role": "printed",
        "animationRole": "drawer-moving",
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
    "cabinet-clutch/21_front_timing_bearing_support_candidate": {
        "name": "中心格·前端主动轮层板一体 MR63 轴承座（打印件）",
        "color": "#657f8c",
        "visible": True,
        "role": "printed",
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
    "cabinet-clutch/cabinet_clutch_vertical_spline_bearing_support": {
        "name": "抽屉电机花键轴·下方3 mm可拆承载板 + 8个Ø5底板Boss/Ø5.2通孔 + C1-C4圆柱座/C5圆角梯形双侧座",
        "color": "#657f8c",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/cabinet_clutch_vertical_spline_bearing_upper_support": {
        "name": "抽屉电机花键轴·上方2.2 mm可拆承载板 + 8个Ø5屋顶Boss/Ø5.2通孔 + 下方蘑菇头M3自攻固定",
        "color": "#718b99",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/cabinet_clutch_vertical_spline_bearings_reference": {
        "name": "抽屉电机花键轴·上下各5枚3×6×2固定轴承×10（与花键轴同轴；采购件）",
        "color": "#cfd4da",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/cabinet_clutch_column_sync_belt_bottom": {
        "name": "列同步2GT皮带 · 下端 · 220T/440mm/6mm",
        "color": "#ce5c31",
        "opacity": 1.0,
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/cabinet_clutch_column_sync_belt_top": {
        "name": "列同步2GT皮带 · 上端 · 220T/440mm/6mm",
        "color": "#ce5c31",
        "opacity": 1.0,
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/cabinet_clutch_column_sync_tensioner_rotor": {
        "name": "列同步张紧轮转子组 · 上下2GT轮 + 共轴圆轴（只旋转；沿−X调节）",
        "color": "#f0a23b",
        "visible": True,
        "role": "printed",
    },
    "cabinet-clutch/cabinet_clutch_column_sync_tensioner_integral": {
        "name": "列同步张紧机构总成 · 原总成+C包T+大C箱壁安装套（上/下实例×2）",
        "color": "#657f8c",
        "visible": True,
        "role": "printed",
        "assemblyRole": "integral-fixed-housing-capture",
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
    "cabinet-clutch/center_linear_bearings_reference": {
        "name": "中心 R3C3 · 固定 LM3UU×1 · Ø3×Ø7×10（与公轮同轴；采购件）",
        "color": "#b7c0c8",
        "visible": True,
        "role": "purchased",
    },
    "cabinet-clutch/center_mechanism_plate": {
        "name": "后仓离合共用承载板×3（每层一条、跨 5 站；四角孔/Boss + 一体 LM3UU + 输出双轴承长方条）",
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
    "cabinet-clutch/center_output_bearings_reference": {
        "name": "中心 R3C3 · 输出双枚 3×6×2 径向轴承（同一体长方条上下固定；采购件）",
        "color": "#cfd4da",
        "visible": True,
        "role": "purchased",
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
        "name": "蛇形链条电机 Ω 固定套（四孔套 Ø5×12 Boss；M3 下压）",
        "color": "#56616d",
        "role": "printed",
    },
    "cabinet-chain/cabinet_chain_motor_spring_hardware": {
        "name": "蛇链电机固定座·四组硬弹簧与下压蘑菇头螺丝",
        "color": "#c9a227",
        "role": "purchased",
    },
    "cabinet-chain/cabinet_chain_sprockets": {
        "name": "12T 尖齿唯一主动轮（D 轴）",
        "color": "#5b9fd6",
        "role": "printed",
    },
    "cabinet-chain/cabinet_chain_idlers": {
        "name": "8T 小尺寸绿色钝齿轴承导向轮（9颗）",
        "color": "#7dcc4a",
        "role": "printed",
    },
    "cabinet-chain/cabinet_chain_idler_axles": {
        "name": "绿色导向轮固定轴·M3 肩螺钉/Ø3 光杆×9（采购件参考）",
        "color": "#aeb6bf",
        "role": "purchased",
    },
    "cabinet-chain/cabinet_chain_plates": {"name": "03C 蛇形链板", "color": "#8A919C", "role": "purchased"},
    "cabinet-chain/cabinet_chain_rollers": {"name": "03C 滚子", "color": "#E8EDF2", "role": "purchased"},
    "cabinet-chain/cabinet_chain_pins": {"name": "03C 销轴", "color": "#B08D57", "role": "purchased"},
    "cabinet-chain/cabinet_chain_bearings": {"name": "3×6×2 轴承（装配显示/采购件）", "color": "#b9c2ca", "role": "purchased"},
    "cabinet-chain/cabinet_chain_clutch_trigger_carrier": {
        "name": "03C 蛇形链条·后侧圆角矩形 M5 磁铁一体拖尾（PETG）",
        "color": "#d9933d",
        "role": "printed",
    },
    "cabinet-chain/cabinet_chain_clutch_trigger_magnet": {
        "name": "蛇形链条·M5×4 触发磁铁（采购件参考）",
        "color": "#5b6670",
        "role": "purchased",
    },
    "cabinet-chain/cabinet_chain_clutch_trigger_connecting_pins": {
        "name": "03C 蛇形链条·17.50 mm 双卡槽穿销×2（现成采购件）",
        "color": "#b08d57",
        "role": "purchased",
    },
    "cabinet-chain/cabinet_chain_clutch_trigger_retaining_clip": {
        "name": "03C 蛇形链条·双卡槽 U 形固定卡×2（现成采购件）",
        "color": "#9aa7b6",
        "role": "purchased",
    },
}
group_map = {
    "cabinet_clutch_cabinet_frame": "00·箱体框架",
    "cabinet_clutch_partition": "00·箱体框架",
    "cabinet_clutch_power_motor_body": "01·动力母线",
    "cabinet_clutch_power_motor_shaft": "01·动力母线",
    "cabinet_clutch_power_column_0": "01·动力母线",
    "cabinet_clutch_power_column_1": "01·动力母线",
    "cabinet_clutch_power_column_2": "01·动力母线",
    "cabinet_clutch_power_column_3": "01·动力母线",
    "cabinet_clutch_power_column_4": "01·动力母线",
    "cabinet_clutch_vertical_spline_bearing_support": "01·动力母线",
    "cabinet_clutch_vertical_spline_bearing_upper_support": "01·动力母线",
    "cabinet_clutch_vertical_spline_bearings_reference": "01·动力母线",
    "cabinet_clutch_column_sync_belt_bottom": "01·动力母线",
    "cabinet_clutch_column_sync_belt_top": "01·动力母线",
    "cabinet_clutch_column_sync_tensioner_rotor": "01·动力母线",
    "cabinet_clutch_column_sync_tensioner_integral": "01·动力母线",
    "center_input_rotor": "02·离合机构",
    "center_output_rotor": "02·离合机构",
    "center_input_sleeve": "02·离合机构",
    "center_input_sleeve_magnet_reference": "02·离合机构",
    "center_linear_bearings_reference": "02·离合机构",
    "center_mechanism_plate": "02·离合机构",
    "center_input_shaft_reference": "02·离合机构",
    "center_output_shaft_reference": "02·离合机构",
    "center_output_bearings_reference": "02·离合机构",
    "13_drawer_timing_belt_reference": "03·抽屉驱动",
    "14_front_timing_pulley_candidate": "03·抽屉驱动",
    "15_front_pinion_candidate": "03·抽屉驱动",
    "16_drawer_linear_rack_candidate": "03·抽屉驱动",
    "17_drawer_tail_guide_rollers_reference": "03·抽屉驱动",
    "19_drawer_front_lower_guide_bearings_reference": "03·抽屉驱动",
    "18_drawer_rack_guide_rails_candidate": "03·抽屉驱动",
    "20_drawer_body_candidate": "03·抽屉驱动",
    "21_front_timing_bearing_support_candidate": "03·抽屉驱动",
    "22_front_timing_bearing_reference": "03·抽屉驱动",
    "23_front_d_axis_reference": "03·抽屉驱动",
}
name_map = {
    "cabinet_clutch_cabinet_frame": "箱体框架（上下左右外框 + 左侧服务回程立板 + X+立板 + 前部层格/立格 + 后仓贯通 + 前下实体面；前后仓隔板另列）",
    "cabinet_clutch_partition": "前后仓隔板·内净尺寸 + 四边各两套D泪滴耳接收/开放D环全外轮廓承压外套 + x-/y-紧凑贯通服务口 + 宽承力网格 + 5×3皮带通孔 + 每格四角 Boss（独立安装件）",
    "center_input_rotor": "中心 R3C3 输入公轮 · 12T/3mm + 圆角公牙",
    "center_output_rotor": "中心 R3C3 输出母轮 · 母槽 + 12T/2GT",
    "center_input_sleeve": "中心 R3C3 公轮底部 D 型圆套 · 下端 Ø8 + Ø5×5 磁铁盲槽",
    "center_input_sleeve_magnet_reference": "中心 R3C3 圆套内 Ø5×5 圆柱磁铁 · 采购件",
    "center_linear_bearings_reference": "中心 R3C3 固定 LM3UU×1 · Ø3×Ø7×10（与公轮同轴；采购件）",
    "center_mechanism_plate": "后仓离合共用承载板×3 · 每层连续跨 5 站 · 四角孔/Boss 自攻固定 · 一体 LM3UU + 输出双轴承长方条",
    "center_input_shaft_reference": "中心 R3C3 输入独立 3mm D 轴 · 采购件",
    "center_output_shaft_reference": "中心 R3C3 输出 D-round 短轴 · 母轮D段 + 双轴承圆轴 · 采购件",
    "center_output_bearings_reference": "中心 R3C3 输出双枚 3×6×2轴承 · 长方条上下固定 · 采购件",
    "13_drawer_timing_belt_reference": "中心格新版2GT皮带 · 80T/160mm/6mm",
    "14_front_timing_pulley_candidate": "中心格新版前端2GT同步轮",
    "15_front_pinion_candidate": "中心格新版前端粗齿驱动轮",
    "16_drawer_linear_rack_candidate": "中心格新版抽屉底部直线齿排",
    "17_drawer_tail_guide_rollers_reference": "中心格抽屉尾部随动 681 导向轴承×2（1×3×1；X轴向）",
    "19_drawer_front_lower_guide_bearings_reference": "中心格 C 形槽前端下托 681 固定轴承×2（1×3×1；X轴向）",
    "18_drawer_rack_guide_rails_candidate": "中心格立板一体内向 C 槽唇边×2（Z向；尾部滚轮+前端下托）",
    "20_drawer_body_candidate": "中心格真实抽屉壳体·底部齿排让位 + 两侧 C 槽/681 让位·随 +Z 运动",
    "22_front_timing_bearing_reference": "中心格前端主动轮层板内 MR63/3×6×2 轴承（采购件）",
    "23_front_d_axis_reference": "中心格前端主动轮到下层同步轮 3mm 短 D 轴",
    "21_front_timing_bearing_support_candidate": "中心格前端主动轮层板一体 MR63 轴承座（打印件）",
    "cabinet_clutch_power_motor_body": "抽屉开合动力电机 · 竖直本体（+X末列）",
    "cabinet_clutch_power_motor_shaft": "抽屉开合动力电机 · 竖直D输出轴",
    "cabinet_clutch_power_column_0": "列同步轴 C1 · Y向长花键 + 上下2GT",
    "cabinet_clutch_power_column_1": "列同步轴 C2 · Y向长花键 + 上下2GT",
    "cabinet_clutch_power_column_2": "列同步轴 C3 · Y向长花键 + 上下2GT",
    "cabinet_clutch_power_column_3": "列同步轴 C4 · Y向长花键 + 上下2GT",
    "cabinet_clutch_power_column_4": "列同步轴 C5 · Y向长花键 + 上下2GT · 电机直连",
    "cabinet_clutch_vertical_spline_bearing_support": "抽屉电机花键轴 下方3 mm可拆承载板 + 8个Ø5底板Boss/Ø5.2通孔 · C1-C4圆柱座/C5圆角梯形双侧座",
    "cabinet_clutch_vertical_spline_bearing_upper_support": "抽屉电机花键轴 上方2.2 mm可拆承载板 + 8个Ø5屋顶Boss/Ø5.2通孔 · 下方蘑菇头M3自攻固定",
    "cabinet_clutch_vertical_spline_bearings_reference": "抽屉电机花键轴 上下各5枚3×6×2固定轴承×10 · 采购件",
    "cabinet_clutch_column_sync_belt_bottom": "列同步2GT皮带 · 下端 · 220T/440mm/6mm",
    "cabinet_clutch_column_sync_belt_top": "列同步2GT皮带 · 上端 · 220T/440mm/6mm",
    "cabinet_clutch_column_sync_tensioner_rotor": "列同步张紧轮转子组 · 上下2GT轮 + 共轴圆轴（只旋转；沿−X调节）",
    "cabinet_clutch_column_sync_tensioner_integral": "列同步张紧机构总成 · 原总成+C形扣架一体固定件（上/下实例×2）",
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

# The SCAD file owns one canonical R3C3 component set. The browser reuses those
# existing STL paths as fourteen lightweight station instances. Each entry is
# a separate component role so Three.js can move every drawer station without
# duplicating the underlying STL geometry.
template_specs = [
    ("cabinet-clutch/template_station_input_rotor",
     "cabinet-clutch/center_input_rotor", "02·离合机构", "clutch-input-rotor",
     "其他14站·输入公轮（共享R3C3 STL）"),
    ("cabinet-clutch/template_station_input_shaft",
     "cabinet-clutch/center_input_shaft_reference", "02·离合机构", "clutch-input-shaft",
     "其他14站·输入D-round-D轴（共享R3C3 STL）"),
    ("cabinet-clutch/template_station_input_sleeve",
     "cabinet-clutch/center_input_sleeve", "02·离合机构", "clutch-input-sleeve",
     "其他14站·公轮底部圆套（共享R3C3 STL）"),
    ("cabinet-clutch/template_station_input_magnet",
     "cabinet-clutch/center_input_sleeve_magnet_reference", "02·离合机构", "clutch-input-magnet",
     "其他14站·公轮底部M5磁铁参考（共享R3C3 STL）"),
    ("cabinet-clutch/template_station_output_rotor",
     "cabinet-clutch/center_output_rotor", "02·离合机构", "clutch-output-rotor",
     "其他14站·输出母轮（共享R3C3 STL）"),
    ("cabinet-clutch/template_station_output_shaft",
     "cabinet-clutch/center_output_shaft_reference", "02·离合机构", "clutch-output-shaft",
     "其他14站·输出D-round轴（共享R3C3 STL）"),
    ("cabinet-clutch/template_station_linear_bearings",
     "cabinet-clutch/center_linear_bearings_reference", "02·离合机构", None,
     "其他14站·固定LM3UU参考（共享R3C3 STL）"),
    ("cabinet-clutch/template_station_output_bearings",
     "cabinet-clutch/center_output_bearings_reference", "02·离合机构", None,
     "其他14站·输出双轴承参考（共享R3C3 STL）"),
    ("cabinet-clutch/template_station_drawer_belt",
     "cabinet-clutch/13_drawer_timing_belt_reference", "03·抽屉驱动", "drawer-belt",
     "其他14站·2GT抽屉皮带（共享中心格STL）"),
    ("cabinet-clutch/template_station_front_pulley",
     "cabinet-clutch/14_front_timing_pulley_candidate", "03·抽屉驱动", "drawer-rotary",
     "其他14站·前端2GT同步轮（共享中心格STL）"),
    ("cabinet-clutch/template_station_front_pinion",
     "cabinet-clutch/15_front_pinion_candidate", "03·抽屉驱动", "drawer-rotary",
     "其他14站·前端直齿驱动轮（共享中心格STL）"),
    ("cabinet-clutch/template_station_front_d_axis",
     "cabinet-clutch/23_front_d_axis_reference", "03·抽屉驱动", "drawer-rotary",
     "其他14站·前端短D轴（共享中心格STL）"),
    ("cabinet-clutch/template_station_drawer_rack",
     "cabinet-clutch/16_drawer_linear_rack_candidate", "03·抽屉驱动", "drawer-moving",
     "其他14站·抽屉底部直齿排/导向翼（共享中心格STL）"),
    ("cabinet-clutch/template_station_drawer_body",
     "cabinet-clutch/20_drawer_body_candidate", "03·抽屉驱动", "drawer-moving",
     "其他14站·真实抽屉壳体（共享中心格 STL）"),
    ("cabinet-clutch/template_station_drawer_tail_bearings",
     "cabinet-clutch/17_drawer_tail_guide_rollers_reference", "03·抽屉驱动", "drawer-moving",
     "其他14站·抽屉尾部随动681轴承（共享中心格STL）"),
    ("cabinet-clutch/template_station_drawer_guide_rails",
     "cabinet-clutch/18_drawer_rack_guide_rails_candidate", "03·抽屉驱动", None,
     "其他14站·立板一体C形导轨（共享中心格STL）"),
    ("cabinet-clutch/template_station_front_lower_bearings",
     "cabinet-clutch/19_drawer_front_lower_guide_bearings_reference", "03·抽屉驱动", None,
     "其他14站·C形槽前端下托轴承（共享中心格STL）"),
    ("cabinet-clutch/template_station_front_bearing_support",
     "cabinet-clutch/21_front_timing_bearing_support_candidate", "03·抽屉驱动", None,
     "其他14站·层板一体MR63轴承座（共享中心格STL）"),
    ("cabinet-clutch/template_station_front_bearing",
     "cabinet-clutch/22_front_timing_bearing_reference", "03·抽屉驱动", None,
     "其他14站·前端MR63轴承参考（共享中心格STL）"),
]
source_by_id = {
    str(part.get("id")): part
    for part in payload.get("parts", [])
    if isinstance(part, dict) and part.get("id")
}
template_clutch_ids = {spec[0] for spec in template_specs if spec[2] == "02·离合机构"}
template_drawer_ids = {spec[0] for spec in template_specs if spec[2] == "03·抽屉驱动"}
template_ids = template_clutch_ids | template_drawer_ids
for template_id, source_id, group_id, animation_role, display_name in template_specs:
    source = source_by_id.get(source_id)
    if source is None:
        raise RuntimeError(f"共享模板来源不存在: {source_id}")
    template = dict(source)
    template.update({
        "id": template_id,
        "name": display_name,
        "group": group_id,
        "visible": True,
        "templateSourceId": source_id,
    })
    if animation_role:
        template["animationRole"] = animation_role
    for key in ("instances", "instanceCount", "instanceMode", "placement", "motion"):
        template.pop(key, None)
    payload["parts"].append(template)
origin_x = float(contract["drawerStationTemplateOriginXMm"])
origin_y = float(contract["drawerStationTemplateOriginYMm"])
column_pitch = float(contract["drawerStationColumnPitchMm"])
row_pitch = float(contract["drawerStationRowPitchMm"])
center_col = int(contract["centerCol"])
center_row = int(contract["centerRow"])
center_x = origin_x + center_col * column_pitch
center_y = origin_y + center_row * row_pitch
instances = [
    {
        "id": f"R{row + 1}C{col + 1}",
        "position": [
            origin_x + col * column_pitch,
            origin_y + row * row_pitch,
            0,
        ],
        "parentFrameId": "world",
        "localTransform": {
            "position": [
                origin_x + col * column_pitch - center_x,
                origin_y + row * row_pitch - center_y,
                0,
            ],
            "rotation": [0, 0, 0],
        },
    }
    for row in range(int(contract["drawerLayerCount"]))
    for col in range(int(contract["drawerColumnCount"]))
    if (col, row) != (center_col, center_row)
]
if len(instances) != int(contract["drawerStationInstanceCount"]):
    raise RuntimeError(
        f"抽屉模板实例数不匹配: {len(instances)} != "
        f"{contract['drawerStationInstanceCount']}"
    )
for part in payload.get("parts", []):
    if part.get("id") in template_ids:
        part["instanceMode"] = "world-offset-from-center-native"
        part["instanceCount"] = len(instances)
        part["instances"] = [dict(instance) for instance in instances]

# The tensioner support is authored once and mounted at two world-space
# instances. The purchased 3×6×2 bearing is an existing shared reference; its
# two relative datums stay in the contract and are not emitted as a new STL.
tensioner_integral_part_id = (
    "cabinet-clutch/cabinet_clutch_column_sync_tensioner_integral"
)
tensioner_support_instances = [
    {
        "id": "lower",
        "position": [
            float(contract["columnSyncTensionerSupportCenterXMm"]),
            float(contract["columnSyncTensionerLowerSupportCenterYMm"]),
            float(contract["columnSyncTensionerSupportCenterZMm"]),
        ],
    },
    {
        "id": "upper",
        "position": [
            float(contract["columnSyncTensionerSupportCenterXMm"]),
            float(contract["columnSyncTensionerUpperSupportCenterYMm"]),
            float(contract["columnSyncTensionerSupportCenterZMm"]),
        ],
    },
]
for part in payload.get("parts", []):
    if part.get("id") == tensioner_integral_part_id:
        part["instanceMode"] = "world-xyz-translation"
        part["instanceCount"] = len(tensioner_support_instances)
        part["instances"] = tensioner_support_instances
        # One canonical STL intentionally contains the fixed small-c + outer-C
        # island and the moving original-T + integral shoe island.  The viewer
        # splits connected islands once and mounts them on the correct frames;
        # this is still one source model instantiated twice, not two duplicate
        # tensioner files.
        part["componentMode"] = "connected-islands"
        part["componentCount"] = 2
        part["componentBindings"] = [
            {
                "id": "fixed-capture",
                "selection": "largest-bounds-y",
                "parentFrameId": "power-bus-fixed",
                "transform": "instance-world-position",
            },
            {
                "id": "moving-housing",
                "selection": "remaining",
                "parentFrameId": "instance-parent",
                "transform": "instance-local-transform",
            },
        ]

# The STL scanner only knows files.  Keep the assembly semantics beside it so
# the browser can reconstruct a real world -> fixed assembly -> motion-frame
# tree instead of guessing parents from part names or bounding boxes.
center_station_y = origin_y + center_row * row_pitch
center_station_id = f"station:R{center_row + 1}C{center_col + 1}"
frames = [
    {
        "id": "world",
        "parentFrameId": None,
        "kind": "fixed",
        "localTransform": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
    },
    {
        "id": "cabinet-fixed",
        "parentFrameId": "world",
        "kind": "fixed",
        "localTransform": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
    },
    {
        "id": "power-bus-fixed",
        "parentFrameId": "cabinet-fixed",
        "kind": "fixed",
        "localTransform": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
    },
    {
        "id": "drawer-drive-fixed",
        "parentFrameId": "cabinet-fixed",
        "kind": "fixed",
        "localTransform": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
    },
    {
        "id": "chain-source",
        "parentFrameId": "world",
        "kind": "coordinate-adapter",
        "localTransform": {
            "position": [0, 0, 0],
            "rotation": [-math.pi / 2, 0, 0],
        },
    },
]
for row in range(int(contract["drawerLayerCount"])):
    for col in range(int(contract["drawerColumnCount"])):
        station_id = f"station:R{row + 1}C{col + 1}"
        frames.append({
            "id": station_id,
            "parentFrameId": "cabinet-fixed",
            "kind": "fixed",
            "localTransform": {
                "position": [
                    origin_x + col * column_pitch,
                    origin_y + row * row_pitch,
                    0,
                ],
                "rotation": [0, 0, 0],
            },
        })
frames.extend([
    {
        "id": "center-input-carriage",
        "parentFrameId": center_station_id,
        "kind": "prismatic",
        "axis": [0, 1, 0],
        "contract": "centerClutch",
        "localTransform": {
            "position": [
                0,
                float(contract["inputBaseYMm"]) - center_station_y,
                float(contract["axisZMm"]),
            ],
            "rotation": [0, 0, 0],
        },
    },
    {
        "id": "center-output-rotor",
        "parentFrameId": center_station_id,
        "kind": "revolute",
        "axis": [0, 1, 0],
        "contract": "centerClutch",
        "localTransform": {
            "position": [
                0,
                float(contract["outputBaseYMm"]) - center_station_y,
                float(contract["axisZMm"]),
            ],
            "rotation": [0, 0, 0],
        },
    },
    {
        "id": "center-front-drive",
        "parentFrameId": center_station_id,
        "kind": "revolute",
        "axis": [0, 1, 0],
        "contract": "centerClutch",
        "localTransform": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
    },
])
frames.append({
    "id": "tensioner-shaft-adjustment",
    "parentFrameId": "power-bus-fixed",
    "kind": "prismatic",
    "axis": [1, 0, 0],
    "contract": "centerClutch",
    "localTransform": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
})
for support_id, position in (
    ("tensioner-lower", tensioner_support_instances[0]["position"]),
    ("tensioner-upper", tensioner_support_instances[1]["position"]),
):
    frames.append({
        "id": support_id,
        "parentFrameId": "tensioner-shaft-adjustment",
        "kind": "fixed",
        "localTransform": {"position": position, "rotation": [0, 0, 0]},
    })

payload["assembly"] = {
    "schemaVersion": 1,
    "rootFrameId": "world",
    "source": "cad/openscad/enclosure/cabinet_clutch.scad",
    "coordinateSystem": {
        "units": "mm",
        "up": "y",
        "world": "openscad-native-world",
    },
    "frames": frames,
}

world_ids = {
    "cabinet-clutch/cabinet_clutch_cabinet_frame",
    "cabinet-clutch/cabinet_clutch_partition",
}
power_ids = {
    "cabinet-clutch/cabinet_clutch_power_motor_body",
    "cabinet-clutch/cabinet_clutch_power_motor_shaft",
    "cabinet-clutch/cabinet_clutch_column_sync_belt_bottom",
    "cabinet-clutch/cabinet_clutch_column_sync_belt_top",
    "cabinet-clutch/cabinet_clutch_column_sync_tensioner_rotor",
    "cabinet-clutch/cabinet_clutch_column_sync_tensioner_integral",
    "cabinet-clutch/cabinet_clutch_vertical_spline_bearing_support",
    "cabinet-clutch/cabinet_clutch_vertical_spline_bearing_upper_support",
    "cabinet-clutch/cabinet_clutch_vertical_spline_bearings_reference",
}
drawer_ids = {
    "cabinet-clutch/13_drawer_timing_belt_reference",
    "cabinet-clutch/14_front_timing_pulley_candidate",
    "cabinet-clutch/15_front_pinion_candidate",
    "cabinet-clutch/16_drawer_linear_rack_candidate",
    "cabinet-clutch/20_drawer_body_candidate",
    "cabinet-clutch/17_drawer_tail_guide_rollers_reference",
    "cabinet-clutch/19_drawer_front_lower_guide_bearings_reference",
    "cabinet-clutch/18_drawer_rack_guide_rails_candidate",
    "cabinet-clutch/21_front_timing_bearing_support_candidate",
    "cabinet-clutch/22_front_timing_bearing_reference",
    "cabinet-clutch/23_front_d_axis_reference",
}
center_input_ids = {
    "cabinet-clutch/center_input_rotor",
    "cabinet-clutch/center_input_shaft_reference",
    "cabinet-clutch/center_input_sleeve",
    "cabinet-clutch/center_input_sleeve_magnet_reference",
}
center_output_ids = {
    "cabinet-clutch/center_output_rotor",
    "cabinet-clutch/center_output_shaft_reference",
}
center_fixed_ids = {
    "cabinet-clutch/center_linear_bearings_reference",
    "cabinet-clutch/center_output_bearings_reference",
    "cabinet-clutch/center_mechanism_plate",
}
chain_trigger_component_specs = {
    "cabinet-chain/cabinet_chain_clutch_trigger_carrier": {
        "id": "carrier",
        "role": "printed-carrier",
        "parent": "chain-segment",
        "mountRelation": "two-adjacent-03C-pin-bores",
    },
    "cabinet-chain/cabinet_chain_clutch_trigger_connecting_pins": {
        "id": "connecting-pins",
        "role": "purchased-extended-pins",
        "parent": "carrier+chain-segment",
        "mountRelation": "paired-pin-bores",
    },
    "cabinet-chain/cabinet_chain_clutch_trigger_retaining_clip": {
        "id": "retaining-clips",
        "role": "purchased-retaining-clips",
        "parent": "connecting-pins",
        "mountRelation": "two-groove-capture",
    },
    "cabinet-chain/cabinet_chain_clutch_trigger_magnet": {
        "id": "magnet",
        "role": "purchased-magnet",
        "parent": "carrier",
        "mountRelation": "rear-rounded-tail-through-seat",
    },
}
front_rotary_ids = {
    "cabinet-clutch/14_front_timing_pulley_candidate",
    "cabinet-clutch/15_front_pinion_candidate",
    "cabinet-clutch/23_front_d_axis_reference",
}
for part in payload.get("parts", []):
    part_id = str(part.get("id", ""))
    parent_frame = "world"
    if part_id in world_ids:
        parent_frame = "cabinet-fixed"
    elif part_id in power_ids:
        parent_frame = "power-bus-fixed"
    elif part_id in drawer_ids:
        parent_frame = "drawer-drive-fixed"
    elif part_id.startswith("cabinet-chain/"):
        parent_frame = "chain-source"
    part["placement"] = {
        "geometrySpace": "world",
        "parentFrameId": parent_frame,
        "mode": "instances" if part.get("instances") else "single",
    }
    if part_id in center_input_ids:
        part["placement"].update({
            "parentFrameId": "world",
            "motionFrameId": "center-input-carriage",
            "motionGeometrySpace": "world-at-motion-datum",
        })
        part["motion"] = {
            "frameId": "center-input-carriage",
            "kind": "prismatic+revolute",
            "axis": [0, 1, 0],
            "role": "input",
        }
    elif part_id in center_output_ids:
        part["placement"].update({
            "parentFrameId": "world",
            "motionFrameId": "center-output-rotor",
            "motionGeometrySpace": "world-at-motion-datum",
        })
        part["motion"] = {
            "frameId": "center-output-rotor",
            "kind": "revolute",
            "axis": [0, 1, 0],
            "role": "output",
        }
    elif part_id in center_fixed_ids:
        part["placement"]["parentFrameId"] = "cabinet-fixed"
        part["placement"]["assemblyFrameId"] = center_station_id
    elif part_id.startswith("cabinet-chain/"):
        part["placement"]["geometrySpace"] = "source-adapter"
    if part_id in front_rotary_ids:
        part["placement"].update({
            "motionFrameId": "center-front-drive",
            "motionGeometrySpace": "world-at-motion-datum",
        })
        part["motion"] = {
            "frameId": "center-front-drive",
            "kind": "revolute",
            "axis": [0, 1, 0],
            "role": "drawer-drive",
        }
    elif part_id == "cabinet-clutch/cabinet_clutch_column_sync_tensioner_rotor":
        part["placement"].update({
            "motionFrameId": "tensioner-shaft-adjustment",
            "motionGeometrySpace": "world-at-motion-datum",
        })
        part["motion"] = {
            "frameId": "tensioner-shaft-adjustment",
            "kind": "prismatic+revolute",
            "axis": [1, 0, 0],
            "rotationAxis": [0, 1, 0],
            "role": "tensioner-shaft",
        }
    trigger_spec = chain_trigger_component_specs.get(part_id)
    if trigger_spec:
        part["assemblyId"] = "chain-trigger-assembly"
        part["assemblyRole"] = trigger_spec["role"]
        part["componentMode"] = "rigid-mounted-component"
        part["componentId"] = trigger_spec["id"]
        part["mountRelation"] = {
            "parent": trigger_spec["parent"],
            "interface": trigger_spec["mountRelation"],
            "motion": "shared-rigid-chain-segment-pose",
        }
        part["placement"].update({
            "assemblyId": "chain-trigger-assembly",
            "assemblyFrameId": "chain-source",
            "mountRelationRef": "chainTriggerAssembly.mountRelations",
        })

# Template instances retain the authored center-native STL coordinates and use
# an explicit world-space delta from R3C3. Keep the absolute `position` as an
# audit datum, while the current app consumes `parentFrameId` + `localTransform`
# and never recomputes the column/row pitch itself.
for part in payload.get("parts", []):
    if part.get("id") in template_ids:
        part["placement"].update({
            "geometrySpace": "world",
            "instanceFrameMode": "world-offset-from-center-native",
        })
    elif part.get("id") == tensioner_integral_part_id:
        for instance in part.get("instances", []):
            instance["parentFrameId"] = f"tensioner-{instance['id']}"
            instance["localTransform"] = {
                "position": [0, 0, 0],
                "rotation": [0, 0, 0],
            }
        part["placement"].update({
            "geometrySpace": "local-template",
            "instanceFrameMode": "tensioner-component-frames",
        })
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
            part_node(
                "cabinet-clutch/cabinet_clutch_vertical_spline_bearing_support",
            ),
            part_node(
                "cabinet-clutch/cabinet_clutch_vertical_spline_bearing_upper_support",
            ),
            part_node(
                "cabinet-clutch/cabinet_clutch_vertical_spline_bearings_reference",
            ),
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
            call_node(
                "power_bus/tensioner-assembly",
                "列同步张紧机构总成 · 一体原壳+C包T滑台 + X向张紧轮轴",
                "固定件只有一个 STL：原张紧机构外壳、C包T扣架、滑台鞋和加固件已在源端 union 成一个实体并以两处实例挂载；箱体一体导轨通过共享 X 向运动坐标承接两处实例，轮轴/轮系只保留一个旋转模板。",
                children=[
                    part_node(
                        "cabinet-clutch/cabinet_clutch_column_sync_tensioner_integral",
                    ),
                    part_node(
                        "cabinet-clutch/cabinet_clutch_column_sync_tensioner_rotor",
                    ),
                ],
            ),
        ]
        root["children"] = [
            call_node(
                "power_bus/active",
                "列同步动力母线 · 电机 + 5列2GT + 上下同步带 + 完整张紧机构",
                "power_motor_vertical() + vertical_gear_column(0 .. N_COL - 1) + power_column_sync_belts() + column_sync_tensioner()",
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
        active_center = [
            part_node("cabinet-clutch/center_input_rotor"),
            part_node("cabinet-clutch/center_output_rotor"),
            part_node("cabinet-clutch/center_mechanism_plate"),
            input_axis,
            rotary_support,
            call_node(
                "center_clutch/station-templates",
                "其他14站·共享离合活动零件实例",
                "输入公轮/轴/圆套、输出母轮/轴和采购轴承均引用同一组R3C3 STL，并按站点世界偏移实例化；选择指只决定链条当前触发目标，15站离合和抽屉驱动共享同一动力相位并同时接合/运动。",
                children=[part_node(template_id) for template_id in sorted(template_clutch_ids)],
            ),
        ]
        root["children"] = [
            call_node(
                "center_clutch/active",
                "中心 R3C3 · 单站纯永磁离合",
                "输入公轮 + 输出母轮 + D-round-D 阶梯轴 + 机构板一体实心 LM3UU 轴承座 + D 型/Ø5×5 磁铁圆套 + 输出双轴承一体长方条 + 可拆机构板",
                children=active_center,
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
                "cabinet-clutch/20_drawer_body_candidate",
            ),
            part_node(
                "cabinet-clutch/17_drawer_tail_guide_rollers_reference",
            ),
            part_node(
                "cabinet-clutch/19_drawer_front_lower_guide_bearings_reference",
            ),
            part_node(
                "cabinet-clutch/18_drawer_rack_guide_rails_candidate",
            ),
            part_node(
                "cabinet-clutch/21_front_timing_bearing_support_candidate",
            ),
            part_node(
                "cabinet-clutch/22_front_timing_bearing_reference",
            ),
            part_node(
                "cabinet-clutch/23_front_d_axis_reference",
            ),
            call_node(
                "drawer-drive/station-templates",
                "其他14站·共享抽屉驱动零件实例",
                "皮带、前端同步轮/直齿轮/D轴、直齿排、尾部随动轴承和固定导向件均复用中心格 STL；动画按同一动力相位驱动全部15个站点，选择指只负责触发站定位。",
                children=[part_node(template_id) for template_id in sorted(template_drawer_ids)],
            ),
        ]
    elif group_id == "cabinet-chain":
        trigger_part_ids = set(chain_trigger_component_specs)
        trigger_nodes = [
            part_node(part_id)
            for part_id in (
                "cabinet-chain/cabinet_chain_clutch_trigger_carrier",
                "cabinet-chain/cabinet_chain_clutch_trigger_connecting_pins",
                "cabinet-chain/cabinet_chain_clutch_trigger_retaining_clip",
                "cabinet-chain/cabinet_chain_clutch_trigger_magnet",
            )
        ]
        ordinary_nodes = [
            part_node(str(part.get("id")))
            for part in parts_by_group.get(group_id, [])
            if str(part.get("id")) not in trigger_part_ids
        ]
        root["children"] = [
            call_node(
                "chain/trigger-assembly",
                "03C 蛇形链条·触发组件（双长穿销 + 两卡簧 + 一体磁台 + M5磁铁）",
                "一个刚性运动组件：载架的两孔套在相邻链节两根 STL-Y 加长穿销上；U 形卡扣入穿销卡槽防脱；M5×4 磁铁沿 STL-Z 装入后侧圆角矩形拖尾贯通座，由用户螺丝固定。四个 STL 仍独立可检验，但网页动画共享同一个链节中点姿态，弯道不拆散、不扭结。",
                children=trigger_nodes,
            ),
            *ordinary_nodes,
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
verify_empty_tensioner_collision_selector
verify_empty_tensioner_capture_selector

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
    "00_tensioner_t_solid_reference.stl"
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
    "cabinet_clutch_column_sync_tensioner_bearing_template.stl"
    "cabinet_clutch_column_sync_tensioner_support_template.stl"
    "cabinet_clutch_column_sync_tensioner.stl"
    "cabinet_clutch_column_sync_tensioner_slider_bridge.stl"
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
    "center_chain_emboss_detail.stl"
    "center_input_carriage.stl"
    "center_guide_rails.stl"
    "center_linear_bearing_retainers.stl"
    "center_linear_bearing_fit_coupon.stl"
    "center_stops.stl"
    "center_input_bearings_reference.stl"
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
    "17_drawer_rack_guide_rollers_reference.stl"
    "19_front_pinion_bearing_support_candidate.stl"
    "20_front_pinion_bearings_reference.stl"
    "21_front_timing_bearing_support_candidate.stl"
    "24_drawer_station_timing_belt_template.stl"
    "25_drawer_station_front_pulley_template.stl"
    "26_drawer_station_front_gear_template.stl"
    "27_drawer_station_front_axis_template.stl"
    "28_drawer_station_rack_template.stl"
    "29_drawer_station_guide_rollers_template.stl"
    "30_drawer_station_guide_rails_template.stl"
    "31_drawer_station_front_bearing_support_template.stl"
    "32_drawer_station_front_bearings_template.stl"
    "33_drawer_station_takeoff_template.stl"
    "24_center_station_kit_template.stl"
)
for old_file in "${OBSOLETE_DRAWER_DRIVE_OUTPUTS[@]}"; do
    rm -f "${OUT_DIR}/${old_file}" \
        "${REPORT_DIR}/${old_file%.stl}.json" \
        "${REPORT_DIR}/${old_file%.stl}.watertight.json"
done

# The selector-shoe mechanism has been deleted. Remove stale outputs so a
# refresh can never show the retired actuator at a different coordinate origin.
LEGACY_CHAIN_SELECTOR_OUTPUTS=(
    "cabinet_chain_selector_magnetic_shoe.stl"
    "center_selector_shoe.stl"
)
for old_file in "${LEGACY_CHAIN_SELECTOR_OUTPUTS[@]}"; do
    rm -f "${OUT_CHAIN}/${old_file}" \
        "${OUT_DIR}/${old_file}" \
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
export_part "vertical_spline_bearing_support" "${OUT_DIR}/cabinet_clutch_vertical_spline_bearing_support.stl" false 0
export_part "vertical_spline_bearing_upper_support" "${OUT_DIR}/cabinet_clutch_vertical_spline_bearing_upper_support.stl" false 0
export_part "vertical_spline_bearings" "${OUT_DIR}/cabinet_clutch_vertical_spline_bearings_reference.stl" false 0
export_part "column_sync_belt_bottom" "${OUT_DIR}/cabinet_clutch_column_sync_belt_bottom.stl" false 0
export_part "column_sync_belt_top" "${OUT_DIR}/cabinet_clutch_column_sync_belt_top.stl" false 0
export_part "column_sync_tensioner_rotor" "${OUT_DIR}/cabinet_clutch_column_sync_tensioner_rotor.stl" false 0
export_part "column_sync_tensioner_integral" "${OUT_DIR}/cabinet_clutch_column_sync_tensioner_integral.stl" false 0

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

export_center_mechanism_plate() (
    # Each row is generated from the same center_clutch_mechanism_row_plate()
    # module.  The row shells are deliberately kept separate until the final
    # binary STL container is written: a direct OpenSCAD merge of the three
    # disjoint rows can create a two-edge seam even when every row is closed.
    # This still publishes exactly one physical center_mechanism_plate.stl;
    # the temporary row files never enter output/ or the browser manifest.
    set -euo pipefail
    local target="$1"
    local temp_rows
    temp_rows="$(mktemp -d "${TMPDIR:-/tmp}/smartparts-center-rows.XXXXXX")"
    trap 'rm -rf -- "${temp_rows}"' EXIT

    local row
    local row_stl
    local -a row_stls=()
    for row in 0 1 2; do
        row_stl="${temp_rows}/center_mechanism_row_${row}.stl"
        echo "→ CLUTCH_PART=center_mechanism_row_plate_debug SELECTED_ROW=${row} → ${row_stl}"
        (
            cd "${SCAD_DIR}"
            "${OPENSCAD_BIN}" \
                --backend Manifold \
                --export-format binstl \
                -D "QUALITY=${QUALITY}" \
                -D 'CLUTCH_PART="center_mechanism_row_plate_debug"' \
                -D "ENGAGED=false" \
                -D "SELECTED_COLUMN=${SELECTED_COLUMN}" \
                -D "SELECTED_ROW=${row}" \
                -o "${row_stl}" \
                "${SCAD_FILE}"
        )
        [[ -s "${row_stl}" ]] || die "空中心离合行板 STL: row=${row}"
        python3 "${INSPECT_PY}" "${row_stl}" --require-watertight --json \
            --output "${temp_rows}/center_mechanism_row_${row}.watertight.json"
        row_stls+=("${row_stl}")
    done

    local merged="${temp_rows}/center_mechanism_plate.stl"
    python3 "${MERGE_STL_PY}" "${merged}" "${row_stls[@]}"
    python3 "${INSPECT_PY}" "${merged}" --require-watertight --json \
        --output "${REPORT_DIR}/center_mechanism_plate.json"
    mv -f "${merged}" "${target}"
    echo "→ 单一正式中心离合主板 → ${target}"
)

# ===== 分区：逐件输出 =====
# These are intentionally emitted in mechanism order so a failed fit can be
# corrected without hiding it inside a full assembly export.
export_part "center_input_rotor" "${OUT_DIR}/center_input_rotor.stl" false 0
export_part "center_output_rotor" "${OUT_DIR}/center_output_rotor.stl" false 0
export_part "center_linear_bearings" "${OUT_DIR}/center_linear_bearings_reference.stl" false 0
export_center_mechanism_plate "${OUT_DIR}/center_mechanism_plate.stl"
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
    "${OUT_DIR}/center_mechanism_plate.stl" \
    "${OUT_DIR}/center_input_sleeve.stl" \
    "${OUT_DIR}/cabinet_clutch_vertical_spline_bearing_support.stl" \
    "${OUT_DIR}/cabinet_clutch_vertical_spline_bearing_upper_support.stl" \
    "${OUT_DIR}/cabinet_clutch_column_sync_tensioner_rotor.stl" \
    "${OUT_DIR}/cabinet_clutch_column_sync_tensioner_integral.stl"; do
    require_watertight_print_part "${printable_part}"
done

export_part "drawer_belt" "${OUT_DIR}/13_drawer_timing_belt_reference.stl" false 0
export_part "front_pulley" "${OUT_DIR}/14_front_timing_pulley_candidate.stl" false 0
export_part "front_gear" "${OUT_DIR}/15_front_pinion_candidate.stl" false 0
export_part "drawer_rack" "${OUT_DIR}/16_drawer_linear_rack_candidate.stl" false 0
export_part "drawer_body" "${OUT_DIR}/20_drawer_body_candidate.stl" false 0
export_part "drawer_tail_guide_rollers" "${OUT_DIR}/17_drawer_tail_guide_rollers_reference.stl" false 0
export_part "drawer_front_lower_guide_bearings" "${OUT_DIR}/19_drawer_front_lower_guide_bearings_reference.stl" false 0
export_part "drawer_rack_guide_rails" "${OUT_DIR}/18_drawer_rack_guide_rails_candidate.stl" false 0
export_part "front_timing_bearing_support" "${OUT_DIR}/21_front_timing_bearing_support_candidate.stl" false 0
export_part "front_timing_bearing" "${OUT_DIR}/22_front_timing_bearing_reference.stl" false 0
export_part "front_d_axis" "${OUT_DIR}/23_front_d_axis_reference.stl" false 0

for printable_part in \
    "${OUT_DIR}/16_drawer_linear_rack_candidate.stl" \
    "${OUT_DIR}/18_drawer_rack_guide_rails_candidate.stl" \
    "${OUT_DIR}/21_front_timing_bearing_support_candidate.stl" \
    "${OUT_DIR}/20_drawer_body_candidate.stl"; do
    require_watertight_print_part "${printable_part}"
done

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
python3 "${PROJECT_ROOT}/scripts/validate_assembly_manifest.py" \
    --manifest "${PREVIEW_DIR}/manifest.json"
cp "${PREVIEW_SOURCE_DIR}/index.html" "${PREVIEW_DIR}/index.html"
cp "${PREVIEW_SOURCE_DIR}/app.js" "${PREVIEW_DIR}/app.js"
mkdir -p "${PREVIEW_DIR}/js"
cp "${PROJECT_ROOT}/web/cabinet-preview/js/cabinet-chain-play.js" "${PREVIEW_DIR}/js/cabinet-chain-play.js"
mkdir -p "${PREVIEW_DIR}/models/cabinet-chain"
ln -sfn "${MOTION_JSON}" "${PREVIEW_DIR}/models/cabinet-chain/cabinet_chain_motion.json"

echo "完成: ${OUT_DIR}"
echo "检查报告: ${REPORT_DIR}"
echo "世界总装配预览: http://127.0.0.1:${PREVIEW_PORT}/"
