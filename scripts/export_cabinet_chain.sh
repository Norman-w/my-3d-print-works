#!/usr/bin/env bash
# Export rear-cavity 03C snake chain STLs into the existing HTTP preview.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAD_DIR="${PROJECT_ROOT}/cad/openscad/enclosure"
SCAD_FILE="cabinet_chain.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
OUT_STL="${PROJECT_ROOT}/output/3d-print/cabinet-chain"
OUT_CLUTCH="${PROJECT_ROOT}/output/3d-print/cabinet-clutch"
OUT_MOTOR="${PROJECT_ROOT}/output/3d-print/motor-library"
OUT_MOUNT="${PROJECT_ROOT}/output/3d-print/motor-mount"
OUT_CHAIN_HARDWARE="${PROJECT_ROOT}/output/3d-print/chain-hardware"
OUT_CHAIN_CLUTCH="${PROJECT_ROOT}/output/3d-print/chain-clutch"
OUT_CABINET="${PROJECT_ROOT}/output/3d-print/cabinet"
OUT_PNG="${PROJECT_ROOT}/output/previews"
PREVIEW_DIR="${PROJECT_ROOT}/output/3d-preview"
INSPECT_PY="${HOME}/.cursor/skills/openscad-stl-print/scripts/inspect_stl.py"
MANIFEST_PY="${HOME}/.cursor/skills/stl-http-preview/scripts/write_preview_manifest.py"
PARTS=(plates rollers pins sprockets idlers bearings motor motor_shaft motor_cover motor_tensioner connector clutch_connector clutch_bearing scheme1_power_wheels scheme1_output_wheels scheme1_clutch_faces scheme1_bearings scheme1_selector)
MOTOR_SCAD_DIR="${PROJECT_ROOT}/cad/openscad"
MOTOR_SCAD_FILE="ch1_03c_power_motor.scad"
MOTOR_COVER_SCAD_FILE="ch1_03c_power_motor_cover.scad"
CHAIN_PIN_SCAD_FILE="ch1_03c_connecting_pin.scad"
CHAIN_CLIP_SCAD_FILE="ch1_03c_retaining_clip.scad"
EXTENDED_PIN_SCAD_FILE="ch1_03c_extended_connecting_pin.scad"
EXTENDED_CLIPS_SCAD_FILE="ch1_03c_extended_retaining_clips.scad"
CLUTCH_PLATFORM_SCAD_FILE="ch1_03c_clutch_platform.scad"
CLUTCH_BEARING_SCAD_FILE="ch1_03c_clutch_bearing.scad"
CLUTCH_RETAINER_SCAD_FILE="ch1_03c_clutch_bearing_retainer.scad"
QUALITY="${QUALITY:-2}"

# ===== 分区：模型/类型 =====
# plates / rollers / pins 是外购链条；sprockets / idlers 是后仓轮。

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

export_stl() {
    local part="$1"
    local dest="${OUT_STL}/cabinet_chain_${part}.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ STL PART=${part} QUALITY=${QUALITY} → ${dest}"
    (
        cd "$SCAD_DIR"
        "$OPENSCAD_BIN" \
            --backend Manifold \
            --export-format binstl \
            -D "PART=\"${part}\"" \
            -D "QUALITY=${QUALITY}" \
            -o "$tmp" \
            "$SCAD_FILE"
    )
    [[ -s "$tmp" ]] || die "空 STL: $dest"
    mv -f "$tmp" "$dest"
}

patch_manifest() {
    python3 - "$PREVIEW_DIR/manifest.json" <<'PY'
from pathlib import Path
import json
import sys

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
payload["title"] = "零件柜 · 后仓横走 03C + 张紧 U"
payload["units"] = "mm"
payload["up"] = "y"
names = {
    "cabinet_shell": {
        "name": "柜体（外框+隔板+格栅）",
        "role": "printed",
        "color": "#6f8f9a",
        "explosion": [0, 0, 0],
        "visible": False,
    },
    "cabinet_back_panel": {
        "name": "可拆背板",
        "role": "printed",
        "color": "#c4a574",
        "explosion": [0, 48, 0],
        "visible": False,
    },
    "cabinet_chain_plates": {
        "name": "03C 蛇形链板",
        "role": "purchased",
        "color": "#8A919C",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_rollers": {
        "name": "03C 滚子",
        "role": "purchased",
        "color": "#E8EDF2",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_pins": {
        "name": "03C 销轴",
        "role": "purchased",
        "color": "#B08D57",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_sprockets": {
        "name": "12T 尖齿唯一主动轮（D 轴）",
        "role": "printed",
        "color": "#5b9fd6",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_idlers": {
        "name": "12T/8T 绿色钝齿轴承导向轮",
        "role": "printed",
        "color": "#7dcc4a",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_bearings": {
        "name": "3×6×2 轴承（装配显示/采购件）",
        "role": "purchased",
        "color": "#b9c2ca",
        "opacity": 1.0,
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_motor": {
        "name": "蛇形链条唯一驱动电机本体（右下张紧位）",
        "role": "purchased",
        "color": "#424a54",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_motor_shaft": {
        "name": "蛇形链条驱动 D 输出轴（右下，随动力轮转动）",
        "role": "purchased",
        "color": "#d6d9dc",
        "opacity": 1.0,
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_motor_cover": {
        "name": "蛇形链条电机固定罩（可沿下压方向滑动）",
        "role": "printed",
        "color": "#56616d",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_motor_tensioner": {
        "name": "蛇形电机张紧调节（导槽 + 弹簧 + M3 螺杆）",
        "role": "printed",
        "color": "#c9a227",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_connector": {
        "name": "03C 链条连接节（带槽双穿销+圆弧夹片，高亮）",
        "role": "diagnostic",
        "color": "#ff2fd0",
        "opacity": 1.0,
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_clutch_connector": {
        "name": "03C 链条加长接头（双夹片+前向离合座，高亮）",
        "role": "diagnostic",
        "color": "#00d9ff",
        "opacity": 1.0,
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_clutch_bearing": {
        "name": "加长接头 681 轴承（银色装配显示）",
        "role": "purchased",
        "color": "#cfd4da",
        "opacity": 1.0,
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_scheme1_power_wheels": {
        "name": "旧方案1·25 个常转动力轮（世界默认隐藏，文件保留）",
        "role": "diagnostic",
        "color": "#e6a23c",
        "opacity": 1.0,
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_scheme1_output_wheels": {
        "name": "旧方案1·25 个抽屉受力轮（世界默认隐藏，文件保留）",
        "role": "diagnostic",
        "color": "#5b9fd6",
        "opacity": 1.0,
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_scheme1_clutch_faces": {
        "name": "旧方案1·25 组狗牙离合面（世界默认隐藏，文件保留）",
        "role": "diagnostic",
        "color": "#f0c36a",
        "opacity": 1.0,
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_scheme1_bearings": {
        "name": "旧方案1·抽屉输出轴承（世界默认隐藏，文件保留）",
        "role": "purchased",
        "color": "#cfd4da",
        "opacity": 1.0,
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_scheme1_selector": {
        "name": "旧方案1·链条拨叉/8T 选择轮（世界默认隐藏，文件保留）",
        "role": "diagnostic",
        "color": "#72e06a",
        "opacity": 1.0,
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "ch1_03c_power_motor_pololu_100_1_hp_6v": {
        "name": "Pololu 100:1 HP 6V D轴电机（独立模型库，默认隐藏）",
        "role": "purchased",
        "color": "#424a54",
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "ch1_03c_power_motor_cover": {
        "name": "动力轮电机固定罩（独立模型库，默认隐藏）",
        "role": "printed",
        "color": "#56616d",
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "ch1_03c_connecting_pin": {
        "name": "03C 连接节双穿销（独立模型库，默认隐藏）",
        "role": "purchased",
        "color": "#b08d57",
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "ch1_03c_retaining_clip": {
        "name": "03C 连接节固定弹片/夹片（独立模型库，默认隐藏）",
        "role": "purchased",
        "color": "#9aa7b6",
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "ch1_03c_extended_connecting_pin": {
        "name": "03C 加长连接节双穿销（独立模型库，默认隐藏）",
        "role": "purchased",
        "color": "#b08d57",
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "ch1_03c_extended_retaining_clips": {
        "name": "03C 加长销双固定弹片/夹片（独立模型库，默认隐藏）",
        "role": "purchased",
        "color": "#9aa7b6",
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "ch1_03c_clutch_platform": {
        "name": "传动离合轴承平台（独立模型库，默认隐藏）",
        "role": "printed",
        "color": "#d17a3d",
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "ch1_03c_clutch_bearing": {
        "name": "681 1×3×1 离合转动基础轴承（独立模型库，默认隐藏）",
        "role": "purchased",
        "color": "#b9c2ca",
        "visible": False,
        "opacity": 1.0,
        "explosion": [0, 0, 0],
    },
    "ch1_03c_clutch_bearing_retainer": {
        "name": "681 离合轴承下承托环（独立模型库，默认隐藏）",
        "role": "printed",
        "color": "#a85c2a",
        "visible": False,
        "explosion": [0, 0, 0],
    },
}
# Keep the single root viewer complete when this chain export is run after
# the drawer/clutch export.  The manifest writer scans all supplied folders;
# these mappings restore the canonical mechanism folders and labels for the
# native-world drawer parts instead of leaving raw filenames in the tree.
names.update({
    "cabinet_clutch_cabinet": {
        "name": "柜体·世界坐标背景", "role": "printed", "color": "#6f8f9a", "opacity": 0.18, "visible": True,
    },
    "cabinet_clutch_cabinet_context": {
        "name": "柜体·格口与抽屉背景", "role": "diagnostic", "color": "#8fa9b8", "opacity": 0.32, "visible": True,
    },
    "cabinet_clutch_assembly": {
        "name": "总装配合并检查体（可选）", "role": "diagnostic", "color": "#7f8ea3", "opacity": 0.28, "visible": False,
    },
    "cabinet_clutch_all_clutches": {"name": "离合器合并检查体（可选）", "role": "diagnostic", "visible": False},
    "cabinet_clutch_detail_open": {"name": "离合细节·打开状态（可选）", "role": "diagnostic", "visible": False},
    "cabinet_clutch_detail_engaged": {"name": "离合细节·闭合状态（可选）", "role": "diagnostic", "visible": False},
    "cabinet_clutch_drawer_drive": {"name": "抽屉驱动合并检查体（可选）", "role": "diagnostic", "visible": False},
    "cabinet_clutch_power_bus": {"name": "动力母线合并检查体（可选）", "role": "diagnostic", "visible": False},
    "00_tensioner_t_solid_reference": {"name": "右侧张紧滑台 · SKP 参数化", "color": "#aebdce"},
    "00_left_d_axis_candidate": {"name": "左侧驱动轴 · D 型"},
    "01_motor_vertical_reference": {"name": "抽屉开合电机 · 竖直"},
    "02_drive_column_reference": {"name": "传动轴 · 代表列"},
    "03_vertical_rack_candidate": {"name": "Y 向长花键齿轮杆 · 两端 D 轴"},
    "06_upper_axis_z_spur_candidate": {"name": "离合上方齿轮 · Z 轴"},
    "07_upper_downward_dog_candidate": {"name": "上方离合齿 · 向下"},
    "08_lower_upward_dog_candidate": {"name": "下方离合齿 · 向上"},
    "09_rear_takeoff_timing_pulley_candidate": {"name": "后方取力同步轮"},
    "10_clutch_spring_reference": {"name": "离合压簧"},
    "11_t_countersunk_screw_reference": {"name": "T 形沉头螺丝"},
    "12_clutch_fork_candidate": {"name": "离合拨叉"},
    "13_drawer_timing_belt_reference": {"name": "抽屉同步皮带"},
    "14_front_timing_pulley_candidate": {"name": "前方同步轮"},
    "15_front_pinion_candidate": {"name": "抽屉底部驱动齿轮"},
    "16_drawer_linear_rack_candidate": {"name": "抽屉底部直线齿排"},
})
clutch_group_map = {
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
for part in payload.get("parts", []):
    extra = names.get(Path(str(part.get("file", ""))).stem)
    if extra is not None:
        part.update(extra)
        part["visible"] = extra.get("visible", True)
    group_id = clutch_group_map.get(Path(str(part.get("file", ""))).stem)
    if group_id is not None:
        part["group"] = group_id
group_order = ["00·柜体与格口", "01·动力母线", "02·离合机构", "03·抽屉驱动", "99·总装配检查体"]
counts = {}
for part in payload.get("parts", []):
    group_id = str(part.get("group") or "未分组")
    counts[group_id] = counts.get(group_id, 0) + 1
ordered = [group_id for group_id in group_order if counts.get(group_id)]
ordered += sorted(group_id for group_id in counts if group_id not in group_order)
payload["groups"] = [{"id": group_id, "name": group_id, "count": counts[group_id]} for group_id in ordered]
payload["groupCount"] = len(payload["groups"])
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
path.write_text(text, encoding="utf-8")
path.with_name("parts.json").write_text(text, encoding="utf-8")
print(f"已标注零件名: {path}")
PY
}

# ===== 分区：公开 API =====
[[ -x "$OPENSCAD_BIN" ]] || die "找不到 OpenSCAD: $OPENSCAD_BIN"
mkdir -p "$OUT_STL" "$OUT_MOTOR" "$OUT_MOUNT" "$OUT_CHAIN_HARDWARE" "$OUT_CHAIN_CLUTCH" "$OUT_PNG"

echo "→ 按真实节距闭合链条 / 张紧轮"
python3 "${PROJECT_ROOT}/scripts/solve_cabinet_chain.py"

for part in "${PARTS[@]}"; do
    export_stl "$part"
done

export_library_motor() {
    local dest="${OUT_MOTOR}/ch1_03c_power_motor_pololu_100_1_hp_6v.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ 独立模型库电机 → ${dest}"
    (
        cd "$MOTOR_SCAD_DIR"
        "$OPENSCAD_BIN" \
            --backend Manifold \
            --export-format binstl \
            -D 'PART="motor"' \
            -o "$tmp" \
            "$MOTOR_SCAD_FILE"
    )
    [[ -s "$tmp" ]] || die "空 STL: $dest"
    mv -f "$tmp" "$dest"
}

export_library_motor

export_library_motor_cover() {
    local dest="${OUT_MOUNT}/ch1_03c_power_motor_cover.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ 独立模型库电机固定罩 → ${dest}"
    (
        cd "$MOTOR_SCAD_DIR"
        "$OPENSCAD_BIN" \
            --backend Manifold \
            --export-format binstl \
            -D 'PART="cover"' \
            -o "$tmp" \
            "$MOTOR_COVER_SCAD_FILE"
    )
    [[ -s "$tmp" ]] || die "空 STL: $dest"
    mv -f "$tmp" "$dest"
}

export_library_motor_cover

export_library_chain_hardware() {
    local source="$1"
    local mode="$2"
    local name="$3"
    local dest="${OUT_CHAIN_HARDWARE}/${name}.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ 独立模型库链条连接件 ${name} → ${dest}"
    (
        cd "$MOTOR_SCAD_DIR"
        "$OPENSCAD_BIN" \
            --backend Manifold \
            --export-format binstl \
            -D "PART=\"${mode}\"" \
            -o "$tmp" \
            "$source"
    )
    [[ -s "$tmp" ]] || die "空 STL: $dest"
    mv -f "$tmp" "$dest"
}

export_library_chain_hardware "$CHAIN_PIN_SCAD_FILE" "pin" "ch1_03c_connecting_pin"
export_library_chain_hardware "$CHAIN_CLIP_SCAD_FILE" "clip" "ch1_03c_retaining_clip"

export_library_chain_clutch() {
    local source="$1"
    local mode="$2"
    local name="$3"
    local dest="${OUT_CHAIN_CLUTCH}/${name}.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ 独立模型库离合连接件 ${name} → ${dest}"
    (
        cd "$MOTOR_SCAD_DIR"
        "$OPENSCAD_BIN" \
            --backend Manifold \
            --export-format binstl \
            -D "PART=\"${mode}\"" \
            -o "$tmp" \
            "$source"
    )
    [[ -s "$tmp" ]] || die "空 STL: $dest"
    mv -f "$tmp" "$dest"
}

export_library_chain_clutch "$EXTENDED_PIN_SCAD_FILE" "pin" "ch1_03c_extended_connecting_pin"
export_library_chain_clutch "$EXTENDED_CLIPS_SCAD_FILE" "clips" "ch1_03c_extended_retaining_clips"
export_library_chain_clutch "$CLUTCH_PLATFORM_SCAD_FILE" "platform" "ch1_03c_clutch_platform"
export_library_chain_clutch "$CLUTCH_BEARING_SCAD_FILE" "bearing" "ch1_03c_clutch_bearing"
export_library_chain_clutch "$CLUTCH_RETAINER_SCAD_FILE" "retainer" "ch1_03c_clutch_bearing_retainer"

if [[ -f "$INSPECT_PY" ]]; then
    for part in sprockets idlers bearings motor motor_shaft motor_cover motor_tensioner scheme1_power_wheels scheme1_output_wheels scheme1_clutch_faces scheme1_bearings scheme1_selector; do
        echo "→ inspect cabinet_chain_${part}.stl"
        python3 "$INSPECT_PY" --require-watertight "${OUT_STL}/cabinet_chain_${part}.stl"
    done
    for part in plates rollers pins; do
        echo "→ inspect cabinet_chain_${part}.stl"
        python3 "$INSPECT_PY" "${OUT_STL}/cabinet_chain_${part}.stl"
    done
    echo "→ inspect cabinet_chain_connector.stl"
    python3 "$INSPECT_PY" --require-watertight "${OUT_STL}/cabinet_chain_connector.stl"
    echo "→ inspect cabinet_chain_clutch_connector.stl"
    python3 "$INSPECT_PY" --require-watertight "${OUT_STL}/cabinet_chain_clutch_connector.stl"
    for part in extended_connecting_pin extended_retaining_clips clutch_platform clutch_bearing clutch_bearing_retainer; do
        echo "→ inspect ch1_03c_${part}.stl"
        python3 "$INSPECT_PY" --require-watertight "${OUT_CHAIN_CLUTCH}/ch1_03c_${part}.stl"
    done
fi

if [[ -f "$MANIFEST_PY" ]]; then
    args=(--preview-dir "$PREVIEW_DIR" --title "零件柜 · 后仓横走 03C + 张紧 U" --no-recursive)
    [[ -d "$OUT_CABINET" ]] && args+=(--stl-dir "$OUT_CABINET")
    [[ -d "$OUT_CLUTCH" ]] && args+=(--stl-dir "$OUT_CLUTCH")
    args+=(--stl-dir "$OUT_MOTOR")
    args+=(--stl-dir "$OUT_MOUNT")
    args+=(--stl-dir "$OUT_CHAIN_HARDWARE")
    args+=(--stl-dir "$OUT_CHAIN_CLUTCH")
    args+=(--stl-dir "$OUT_STL")
    python3 "$MANIFEST_PY" "${args[@]}"
    patch_manifest
    mkdir -p "${PREVIEW_DIR}/js" "${PREVIEW_DIR}/models/cabinet-chain"
    cp "${PROJECT_ROOT}/web/cabinet-preview/index.html" "${PREVIEW_DIR}/index.html"
    cp "${PROJECT_ROOT}/web/cabinet-preview/app.js" "${PREVIEW_DIR}/app.js"
    cp "${PROJECT_ROOT}/web/cabinet-preview/js/cabinet-chain-play.js" "${PREVIEW_DIR}/js/cabinet-chain-play.js"
    MOTION_JSON="${OUT_STL}/cabinet_chain_motion.json"
    if [[ -f "$MOTION_JSON" ]]; then
        ln -sfn "$MOTION_JSON" "${PREVIEW_DIR}/models/cabinet-chain/cabinet_chain_motion.json"
    fi
fi

echo "完成:"
for part in "${PARTS[@]}"; do
    echo "  STL  ${OUT_STL}/cabinet_chain_${part}.stl"
done
echo "  STL  ${OUT_MOTOR}/ch1_03c_power_motor_pololu_100_1_hp_6v.stl"
echo "  STL  ${OUT_MOUNT}/ch1_03c_power_motor_cover.stl"
echo "  STL  ${OUT_CHAIN_HARDWARE}/ch1_03c_connecting_pin.stl"
echo "  STL  ${OUT_CHAIN_HARDWARE}/ch1_03c_retaining_clip.stl"
echo "  STL  ${OUT_CHAIN_CLUTCH}/ch1_03c_extended_connecting_pin.stl"
echo "  STL  ${OUT_CHAIN_CLUTCH}/ch1_03c_extended_retaining_clips.stl"
  echo "  STL  ${OUT_CHAIN_CLUTCH}/ch1_03c_clutch_platform.stl"
  echo "  STL  ${OUT_CHAIN_CLUTCH}/ch1_03c_clutch_bearing.stl"
  echo "  STL  ${OUT_CHAIN_CLUTCH}/ch1_03c_clutch_bearing_retainer.stl"
echo "  方案1视图: 输入轮 / 输出轮 / 狗牙离合 / 银色轴承 / 链条拨叉"
echo "  预览保持现有 HTTP 服务，刷新即可"

# ===== 分区：业务逻辑 =====
# 不 restart 预览端口；链条 STL 只用于观看，不要当 FDM 打印件。

# ===== 分区：方法/工具 =====
# QUALITY 可用环境变量覆盖，默认 2。
