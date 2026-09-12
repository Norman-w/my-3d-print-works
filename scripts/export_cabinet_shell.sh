#!/usr/bin/env bash
# Export cabinet shell + back panel STLs, then inspect and preview.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAD_DIR="${PROJECT_ROOT}/cad/openscad/enclosure"
SCAD_FILE="cabinet.scad"
OPENSCAD_BIN="${OPENSCAD_BIN:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"
OUT_STL="${PROJECT_ROOT}/output/3d-print/cabinet"
OUT_PNG="${PROJECT_ROOT}/output/previews"
PREVIEW_DIR="${PROJECT_ROOT}/output/3d-preview"
INSPECT_PY="${HOME}/.cursor/skills/openscad-stl-print/scripts/inspect_stl.py"
MANIFEST_PY="${HOME}/.cursor/skills/stl-http-preview/scripts/write_preview_manifest.py"
PREVIEW_SH="${HOME}/.cursor/skills/stl-http-preview/scripts/preview_http.sh"
PARTS=(shell back_panel)

# ===== 分区：模型/类型 =====
# shell / back_panel 是 FDM 打印件；assembly 只用于预览，不导出 STL。

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

export_stl() {
    local part="$1"
    local dest="${OUT_STL}/cabinet_${part}.stl"
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
payload["title"] = "零件柜外壳 · 240×200×120 mm · 5×6 格"
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
    },
}
for part in payload.get("parts", []):
    extra = names.get(Path(str(part.get("file", ""))).stem)
    if extra is None:
        continue
    part.update(extra)
    part["visible"] = True
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
path.write_text(text, encoding="utf-8")
path.with_name("parts.json").write_text(text, encoding="utf-8")
print(f"已标注零件名: {path}")
PY
}

# ===== 分区：公开 API =====
[[ -x "$OPENSCAD_BIN" ]] || die "找不到 OpenSCAD: $OPENSCAD_BIN"
mkdir -p "$OUT_STL" "$OUT_PNG"

for part in "${PARTS[@]}"; do
    export_stl "$part"
done

export_png cabinet_iso \
    -D "PART=\"assembly\"" --projection=p --camera=0,0,0,55,0,35,520
export_png cabinet_front \
    -D "PART=\"assembly\"" --projection=o --camera=0,0,0,90,0,0,360
export_png cabinet_back \
    -D "PART=\"assembly\"" --projection=o --camera=0,0,0,90,0,180,360
export_png cabinet_top \
    -D "PART=\"assembly\"" --projection=o --camera=0,0,0,0,0,0,360

if [[ -f "$INSPECT_PY" ]]; then
    for part in "${PARTS[@]}"; do
        echo "→ inspect cabinet_${part}.stl"
        python3 "$INSPECT_PY" "${OUT_STL}/cabinet_${part}.stl"
    done
fi

if [[ -f "$MANIFEST_PY" ]]; then
    python3 "$MANIFEST_PY" \
        --stl-dir "$OUT_STL" \
        --preview-dir "$PREVIEW_DIR" \
        --title "零件柜外壳 · 240×200×120 mm · 5×6 格" \
        --role printed \
        --no-recursive
    patch_manifest
fi

if [[ -f "$PREVIEW_SH" ]]; then
    "$PREVIEW_SH" restart "$PREVIEW_DIR" --host 0.0.0.0 --lan-host auto --no-open || \
        "$PREVIEW_SH" start "$PREVIEW_DIR" --host 0.0.0.0 --lan-host auto --no-open
fi

echo "完成:"
for part in "${PARTS[@]}"; do
    echo "  STL  ${OUT_STL}/cabinet_${part}.stl"
done
echo "  预览 ${OUT_PNG}/cabinet_iso.png"

# ===== 分区：业务逻辑 =====
# 只导出两个打印件；装配爆炸和抽屉幽灵体只出现在 PNG / HTTP 预览。

# ===== 分区：方法/工具 =====
# OpenSCAD 路径可用 OPENSCAD_BIN 覆盖。
