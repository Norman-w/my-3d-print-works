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
OUT_MOTOR="${PROJECT_ROOT}/output/3d-print/motor-library"
OUT_MOUNT="${PROJECT_ROOT}/output/3d-print/motor-mount"
OUT_CHAIN_HARDWARE="${PROJECT_ROOT}/output/3d-print/chain-hardware"
OUT_CHAIN_CLUTCH="${PROJECT_ROOT}/output/3d-print/chain-clutch"
OUT_CABINET="${PROJECT_ROOT}/output/3d-print/cabinet"
OUT_PNG="${PROJECT_ROOT}/output/previews"
PREVIEW_DIR="${PROJECT_ROOT}/output/3d-preview"
INSPECT_PY="${HOME}/.cursor/skills/openscad-stl-print/scripts/inspect_stl.py"
MANIFEST_PY="${HOME}/.cursor/skills/stl-http-preview/scripts/write_preview_manifest.py"
PARTS=(plates rollers pins sprockets idlers bearings motor motor_cover)
MOTOR_SCAD_DIR="${PROJECT_ROOT}/cad/openscad"
MOTOR_SCAD_FILE="ch1_03c_power_motor.scad"
MOTOR_COVER_SCAD_FILE="ch1_03c_power_motor_cover.scad"
CHAIN_PIN_SCAD_FILE="ch1_03c_connecting_pin.scad"
CHAIN_CLIP_SCAD_FILE="ch1_03c_retaining_clip.scad"
EXTENDED_PIN_SCAD_FILE="ch1_03c_extended_connecting_pin.scad"
EXTENDED_CLIPS_SCAD_FILE="ch1_03c_extended_retaining_clips.scad"
CLUTCH_PLATFORM_SCAD_FILE="ch1_03c_clutch_platform.scad"
CLUTCH_BEARING_SCAD_FILE="ch1_03c_clutch_bearing.scad"
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
payload["up"] = "z"
names = {
    "cabinet_shell": {
        "name": "柜体（外框+隔板+格栅）",
        "role": "printed",
        "color": "#6f8f9a",
        "explosion": [0, 0, 0],
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
        "name": "12T 尖齿（网页右上动力 D 轴 + 其余轴承）",
        "role": "printed",
        "color": "#5b9fd6",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_idlers": {
        "name": "8T 钝齿轴承平移轮",
        "role": "printed",
        "color": "#7dcc4a",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_bearings": {
        "name": "3×6×2 轴承（装配显示/采购件）",
        "role": "purchased",
        "color": "#b9c2ca",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_motor": {
        "name": "动力轮已安装电机（Pololu 100:1 HP 6V，D轴）",
        "role": "purchased",
        "color": "#424a54",
        "explosion": [0, 0, 0],
    },
    "cabinet_chain_motor_cover": {
        "name": "动力轮电机固定罩（M3 boss 螺钉固定）",
        "role": "printed",
        "color": "#56616d",
        "explosion": [0, 0, 0],
    },
    "ch1_03c_power_motor_pololu_100_1_hp_6v": {
        "name": "Pololu 100:1 HP 6V D轴电机（模型库/采购件）",
        "role": "purchased",
        "color": "#424a54",
        "explosion": [0, 0, 0],
    },
    "ch1_03c_power_motor_cover": {
        "name": "动力轮电机固定罩（模型库/打印件）",
        "role": "printed",
        "color": "#56616d",
        "explosion": [0, 0, 0],
    },
    "ch1_03c_connecting_pin": {
        "name": "03C 连接节双穿销（模型库/外购参考件）",
        "role": "purchased",
        "color": "#b08d57",
        "explosion": [0, 0, 0],
    },
    "ch1_03c_retaining_clip": {
        "name": "03C 连接节固定弹片/夹片（模型库/外购参考件）",
        "role": "purchased",
        "color": "#9aa7b6",
        "explosion": [0, 0, 0],
    },
    "ch1_03c_extended_connecting_pin": {
        "name": "03C 加长连接节双穿销（双夹片定位）",
        "role": "purchased",
        "color": "#b08d57",
        "explosion": [0, 0, 0],
    },
    "ch1_03c_extended_retaining_clips": {
        "name": "03C 加长销双固定弹片/夹片",
        "role": "purchased",
        "color": "#9aa7b6",
        "explosion": [0, 0, 0],
    },
    "ch1_03c_clutch_platform": {
        "name": "传动离合轴承平台（3×6×2 座）",
        "role": "printed",
        "color": "#d17a3d",
        "explosion": [0, 0, 0],
    },
    "ch1_03c_clutch_bearing": {
        "name": "3×6×2 离合转动基础轴承（装配显示/采购件）",
        "role": "purchased",
        "color": "#b9c2ca",
        "explosion": [0, 0, 0],
    },
}
for part in payload.get("parts", []):
    extra = names.get(Path(str(part.get("file", ""))).stem)
    if extra is None:
        continue
    part.update(extra)
    part["visible"] = extra.get("visible", True)
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

if [[ -f "$INSPECT_PY" ]]; then
    for part in sprockets idlers bearings motor motor_cover; do
        echo "→ inspect cabinet_chain_${part}.stl"
        python3 "$INSPECT_PY" --require-watertight "${OUT_STL}/cabinet_chain_${part}.stl"
    done
    for part in plates rollers pins; do
        echo "→ inspect cabinet_chain_${part}.stl"
        python3 "$INSPECT_PY" "${OUT_STL}/cabinet_chain_${part}.stl"
    done
    for part in extended_connecting_pin extended_retaining_clips clutch_platform clutch_bearing; do
        echo "→ inspect ch1_03c_${part}.stl"
        python3 "$INSPECT_PY" --require-watertight "${OUT_CHAIN_CLUTCH}/ch1_03c_${part}.stl"
    done
fi

if [[ -f "$MANIFEST_PY" ]]; then
    args=(--preview-dir "$PREVIEW_DIR" --title "零件柜 · 后仓横走 03C + 张紧 U" --no-recursive)
    [[ -d "$OUT_CABINET" ]] && args+=(--stl-dir "$OUT_CABINET")
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
echo "  预览保持现有 HTTP 服务，刷新即可"

# ===== 分区：业务逻辑 =====
# 不 restart 预览端口；链条 STL 只用于观看，不要当 FDM 打印件。

# ===== 分区：方法/工具 =====
# QUALITY 可用环境变量覆盖，默认 2。
