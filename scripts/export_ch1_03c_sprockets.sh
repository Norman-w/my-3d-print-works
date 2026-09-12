#!/usr/bin/env bash
# Export CH1 03C sprocket family (1x / 1.5x / 2x / 3x / 4x) to STL and PNG.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAD_DIR="${PROJECT_ROOT}/cad/openscad/parts"
SCAD_FILE="ch1_03c_sprocket.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
OUT_STL="${PROJECT_ROOT}/output/3d-print"
OUT_PNG="${PROJECT_ROOT}/output/previews"
INSPECT_PY="${HOME}/.cursor/skills/openscad-stl-print/scripts/inspect_stl.py"
SIZES=(1x 1.5x 2x 3x 4x)

# ===== 分区：模型/类型 =====
# SIZE 覆盖 sprocket.scad；PART=family / wrap_check 只用于预览。

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

need_bin() {
    [[ -x "$OPENSCAD_BIN" ]] || die "找不到 OpenSCAD: $OPENSCAD_BIN"
}

export_stl() {
    local size="$1"
    local dest="${OUT_STL}/ch1_03c_sprocket_${size}.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ STL SIZE=${size} → ${dest}"
    (
        cd "$SCAD_DIR"
        "$OPENSCAD_BIN" \
            -D "SIZE=\"${size}\"" \
            -D "PART=\"sprocket\"" \
            -o "$tmp" \
            "$SCAD_FILE"
    )
    [[ -s "$tmp" ]] || die "空 STL: $dest"
    mv -f "$tmp" "$dest"
}

export_png() {
    local name="$1"
    shift
    local dest="${OUT_PNG}/${name}.png"
    echo "→ PNG ${name}"
    (
        cd "$SCAD_DIR"
        "$OPENSCAD_BIN" \
            --preview \
            --imgsize=1600,1000 \
            --colorscheme="Tomorrow Night" \
            "$@" \
            -o "$dest" \
            "$SCAD_FILE"
    )
    [[ -s "$dest" ]] || die "空 PNG: $dest"
}

# ===== 分区：公开 API =====
need_bin
mkdir -p "$OUT_STL" "$OUT_PNG"

for size in "${SIZES[@]}"; do
    export_stl "$size"
done

export_png ch1_03c_sprocket_family_iso \
    -D "PART=\"family\"" \
    --viewall --autocenter --projection=p --camera=0,0,0,55,0,25,220

export_png ch1_03c_sprocket_family_top \
    -D "PART=\"family\"" \
    --viewall --autocenter --projection=o --camera=0,0,0,0,0,0,180

export_png ch1_03c_sprocket_1x_iso \
    -D "SIZE=\"1x\"" -D "PART=\"sprocket\"" \
    --viewall --autocenter --projection=p --camera=0,0,0,55,0,35,40

export_png ch1_03c_sprocket_1x_top \
    -D "SIZE=\"1x\"" -D "PART=\"sprocket\"" \
    --viewall --autocenter --projection=o --camera=0,0,0,0,0,0,32

export_png ch1_03c_sprocket_1x_front \
    -D "SIZE=\"1x\"" -D "PART=\"sprocket\"" \
    --viewall --autocenter --projection=o --camera=0,0,0,90,0,0,32

export_png ch1_03c_sprocket_1x_wrap \
    -D "SIZE=\"1x\"" -D "PART=\"wrap_check\"" \
    --viewall --autocenter --projection=p --camera=0,0,0,70,0,25,38

# ===== 分区：业务逻辑 =====
if [[ -f "$INSPECT_PY" ]]; then
    for size in "${SIZES[@]}"; do
        echo "→ inspect ch1_03c_sprocket_${size}.stl"
        python3 "$INSPECT_PY" "${OUT_STL}/ch1_03c_sprocket_${size}.stl"
    done
else
    echo "跳过 STL 检查：找不到 $INSPECT_PY"
fi

echo "完成:"
for size in "${SIZES[@]}"; do
    echo "  STL  ${OUT_STL}/ch1_03c_sprocket_${size}.stl"
done
echo "  预览 ${OUT_PNG}/ch1_03c_sprocket_family_iso.png"

# ===== 分区：方法/工具 =====
# OpenSCAD 路径可用 OPENSCAD_BIN 覆盖。
