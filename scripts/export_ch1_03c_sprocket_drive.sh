#!/usr/bin/env bash
# Export 1x/2x sprocket + 03C wrap-chain STLs, then serve HTTP preview.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAD_DIR="${PROJECT_ROOT}/cad/openscad"
SCAD_FILE="ch1_03c_sprocket_drive.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
OUT_STL="${PROJECT_ROOT}/output/3d-print/sprocket-drive"
OUT_PNG="${PROJECT_ROOT}/output/previews"
PREVIEW_DIR="${PROJECT_ROOT}/output/3d-preview"
INSPECT_PY="${HOME}/.cursor/skills/openscad-stl-print/scripts/inspect_stl.py"
MANIFEST_PY="${HOME}/.cursor/skills/stl-http-preview/scripts/write_preview_manifest.py"
PREVIEW_SH="${HOME}/.cursor/skills/stl-http-preview/scripts/preview_http.sh"
PARTS=(sprocket_1x sprocket_2x plates rollers pins)

# ===== 分区：模型/类型 =====
# sprocket_* 是打印件；plates/rollers/pins 是外购链条包络，不能标成打印件。

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

export_stl() {
    local part="$1"
    local dest="${OUT_STL}/ch1_03c_drive_${part}.stl"
    local tmp="${dest}.tmp.$$.$RANDOM.stl"
    echo "→ STL PART=${part} → ${dest}"
    (
        cd "$SCAD_DIR"
        "$OPENSCAD_BIN" \
            --backend Manifold \
            --export-format binstl \
            -D "PART=\"${part}\"" \
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
            --backend Manifold \
            --preview \
            --imgsize=1600,1000 \
            --colorscheme="Tomorrow Night" \
            --viewall --autocenter \
            "$@" \
            -o "$dest" \
            "$SCAD_FILE"
    )
    [[ -s "$dest" ]] || die "空 PNG: $dest"
}

patch_manifest() {
    python3 - "$PREVIEW_DIR/manifest.json" <<'PY'
from pathlib import Path
import json
import sys

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
payload["title"] = "CH1 03C 链传动 · 左 1x / 右 2x / 中心距 200 mm"
payload["units"] = "mm"
payload["up"] = "z"
names = {
    "ch1_03c_drive_sprocket_1x": {
        "name": "1x 链轮（左）",
        "role": "printed",
        "color": "#5b9fd6",
        "explosion": [0, -42, 24],
    },
    "ch1_03c_drive_sprocket_2x": {
        "name": "2x 链轮（右）",
        "role": "printed",
        "color": "#e0c07a",
        "explosion": [0, 42, 24],
    },
    "ch1_03c_drive_plates": {
        "name": "链条链板",
        "role": "purchased",
        "color": "#8A919C",
        "explosion": [0, 0, 22],
    },
    "ch1_03c_drive_rollers": {
        "name": "链条套筒",
        "role": "purchased",
        "color": "#E8EDF2",
        "explosion": [0, 0, 40],
    },
    "ch1_03c_drive_pins": {
        "name": "链条销轴",
        "role": "purchased",
        "color": "#B08D57",
        "explosion": [0, 0, 58],
    },
}
for part in payload.get("parts", []):
    extra = names.get(Path(str(part.get("file", ""))).stem)
    if extra is None:
        continue
    part.update(extra)
    part["visible"] = True
    if part["role"] == "purchased":
        part["opacity"] = 0.92
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
path.write_text(text, encoding="utf-8")
path.with_name("parts.json").write_text(text, encoding="utf-8")
print(f"已标注零件名: {path}")
PY
}

# ===== 分区：公开 API =====
[[ -x "$OPENSCAD_BIN" ]] || die "找不到 OpenSCAD: $OPENSCAD_BIN"
[[ -f "$MANIFEST_PY" ]] || die "找不到 $MANIFEST_PY"
mkdir -p "$OUT_STL" "$OUT_PNG"

for part in "${PARTS[@]}"; do
    export_stl "$part"
done

export_png ch1_03c_drive_iso --projection=p --camera=0,0,0,55,0,25,420
export_png ch1_03c_drive_top --projection=o --camera=0,0,0,0,0,0,280
export_png ch1_03c_drive_front --projection=o --camera=0,0,0,90,0,0,280

if [[ -f "$INSPECT_PY" ]]; then
    for part in "${PARTS[@]}"; do
        echo "→ inspect ch1_03c_drive_${part}.stl"
        python3 "$INSPECT_PY" "${OUT_STL}/ch1_03c_drive_${part}.stl"
    done
fi

python3 "$MANIFEST_PY" \
    --stl-dir "$OUT_STL" \
    --preview-dir "$PREVIEW_DIR" \
    --title "CH1 03C 链传动 · 左 1x / 右 2x / 中心距 200 mm" \
    --role printed \
    --no-recursive

patch_manifest

mkdir -p "${PREVIEW_DIR}/js"
cp -f "${PROJECT_ROOT}/web/sprocket-drive-viewer.html" "${PREVIEW_DIR}/drive.html"
cp -f "${PROJECT_ROOT}/web/js/sprocket-drive-anim.js" "${PREVIEW_DIR}/js/sprocket-drive-anim.js"

if [[ -f "$PREVIEW_SH" ]]; then
    "$PREVIEW_SH" restart "$PREVIEW_DIR" --host 0.0.0.0 --lan-host auto --no-open || \
        "$PREVIEW_SH" start "$PREVIEW_DIR" --host 0.0.0.0 --lan-host auto --no-open
fi

echo "完成:"
for part in "${PARTS[@]}"; do
    echo "  STL  ${OUT_STL}/ch1_03c_drive_${part}.stl"
done
echo "  预览 ${OUT_PNG}/ch1_03c_drive_iso.png"
echo "  HTTP http://127.0.0.1:8765/"
echo "  运动 http://127.0.0.1:8765/drive.html"

# ===== 分区：业务逻辑 =====
# 链条是外购件包络；102 节绕 200 mm 中心距，不在这里张紧或润滑。

# ===== 分区：方法/工具 =====
# OpenSCAD 路径可用 OPENSCAD_BIN 覆盖。
