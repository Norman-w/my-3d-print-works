#!/usr/bin/env bash
# Export rear-cavity 03C snake chain STLs into the existing HTTP preview.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/resolve_preview_tools.sh"
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
PARTS=(plates rollers pins sprockets idlers bearings clutch_trigger_magnet motor motor_shaft motor_cover motor_spring_hardware connector clutch_connector clutch_bearing)
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
            -D "CHAIN_PART=\"${part}\"" \
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
        "name": "8T 小尺寸绿色钝齿轴承导向轮（8颗）",
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
    "cabinet_chain_clutch_trigger_magnet": {
        "name": "蛇形链条·链节 Z− 触发磁铁（Ø2×1.8 采购件参考）",
        "role": "purchased",
        "color": "#5b6670",
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
        "name": "蛇形链条电机 Ω 固定套（四孔套 Ø5×12 Boss；M3 下压）",
        "role": "printed",
        "color": "#56616d",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_motor_spring_hardware": {
        "name": "蛇链电机固定座·四组硬弹簧与下压蘑菇头螺丝",
        "role": "purchased",
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
    "ch1_03c_power_motor_pololu_100_1_hp_6v": {
        "name": "Pololu 100:1 HP 6V D轴电机（独立模型库，默认隐藏）",
        "role": "purchased",
        "color": "#424a54",
        "visible": False,
        "explosion": [0, 0, 0],
    },
    "ch1_03c_power_motor_cover": {
        "name": "动力轮电机 Ω 形贴合固定套（独立模型库，默认隐藏）",
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
    "cabinet_clutch_cabinet_frame": {
        "name": "箱体·上下左右外框 + X+立板 + 前部层格/立格 + 前后仓隔板皮带孔 + 后仓贯通 + 前下实体面",
        "role": "printed", "color": "#6f8f9a", "opacity": 0.30, "visible": True,
    },
    "00_tensioner_t_solid_reference": {"name": "右侧张紧滑台 · SKP 参数化", "color": "#aebdce"},
    "13_drawer_timing_belt_reference": {"name": "抽屉同步皮带"},
    "14_front_timing_pulley_candidate": {"name": "前方同步轮"},
    "15_front_pinion_candidate": {"name": "抽屉底部驱动齿轮"},
    "16_drawer_linear_rack_candidate": {"name": "抽屉底部直线齿排"},
})
clutch_group_map = {
    "cabinet_clutch_cabinet_frame": "00·箱体框架",
    "00_tensioner_t_solid_reference": "01·动力母线",
    "13_drawer_timing_belt_reference": "03·抽屉驱动",
    "14_front_timing_pulley_candidate": "03·抽屉驱动",
    "15_front_pinion_candidate": "03·抽屉驱动",
    "16_drawer_linear_rack_candidate": "03·抽屉驱动",
}
for part in payload.get("parts", []):
    extra = names.get(Path(str(part.get("file", ""))).stem)
    if extra is not None:
        part.update(extra)
        part["visible"] = extra.get("visible", True)
    group_id = clutch_group_map.get(Path(str(part.get("file", ""))).stem)
    if group_id is not None:
        part["group"] = group_id
group_order = ["00·箱体框架", "01·动力母线", "02·离合机构", "03·抽屉驱动", "99·总装配检查体"]
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

# Retired chain diagnostics were intentionally hidden before, but their stale
# STLs were still scanned into the tree. Remove the derived files now that the
# current world uses the native center clutch and the single trigger magnet.
OBSOLETE_CHAIN_OUTPUTS=(
    "cabinet_chain_motor_tensioner.stl"
    "cabinet_chain_scheme1_power_wheels.stl"
    "cabinet_chain_scheme1_output_wheels.stl"
    "cabinet_chain_scheme1_clutch_faces.stl"
    "cabinet_chain_scheme1_bearings.stl"
    "cabinet_chain_scheme1_selector.stl"
)
for old_file in "${OBSOLETE_CHAIN_OUTPUTS[@]}"; do
    rm -f "${OUT_STL}/${old_file}"
    rm -f "${PREVIEW_DIR}/models/cabinet-chain/${old_file}"
done

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
    for part in sprockets idlers bearings clutch_trigger_magnet motor motor_shaft motor_cover motor_spring_hardware; do
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

python3 "${PROJECT_ROOT}/scripts/validate_cabinet_chain_sync.py" \
    --motion "${OUT_STL}/cabinet_chain_motion.json" \
    --stl-dir "${OUT_STL}"

if [[ -f "$MANIFEST_PY" ]]; then
    # Rebuild the canonical clutch model folder before scanning.  The manifest
    # writer updates the JSON but intentionally does not remove dangling links
    # left by retired parts from an older export.
    rm -rf "$PREVIEW_DIR/models/cabinet-clutch"
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
echo "  预览保持现有 HTTP 服务，刷新即可"

# ===== 分区：业务逻辑 =====
# 不 restart 预览端口；链条 STL 只用于观看，不要当 FDM 打印件。

# ===== 分区：方法/工具 =====
# QUALITY 可用环境变量覆盖，默认 2。
