#!/usr/bin/env bash
# Place existing 1x/2x sprocket STLs at ~200 mm centers, then serve HTTP preview.

# ===== 分区：导入/依赖 =====
set -euo pipefail

# ===== 分区：常量/配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/resolve_preview_tools.sh"
PLACE_PY="${SCRIPT_DIR}/place_ch1_03c_sprocket_layout.py"
LAYOUT_DIR="${PROJECT_ROOT}/output/3d-print/sprocket-layout"
PREVIEW_DIR="${PROJECT_ROOT}/output/3d-preview"
CENTER_DISTANCE_MM="${1:-200}"

# ===== 分区：模型/类型 =====
# 预览零件角色：printed。这是已导出链轮的装配位姿，不是新的打印件。

# ===== 分区：私有成员 =====
die() {
    echo "错误: $*" >&2
    exit 1
}

patch_manifest() {
    python3 - "$PREVIEW_DIR/manifest.json" <<'PY'
from pathlib import Path
import json
import sys

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
payload["title"] = "CH1 03C 链轮布局 · 左 1x / 右 2x · 中心距 200 mm"
payload["units"] = "mm"
payload["up"] = "z"
names = {
    "ch1_03c_sprocket_1x_left": {
        "name": "1x 链轮（左）",
        "color": "#5b9fd6",
        "explosion": [-36, 0, 28],
    },
    "ch1_03c_sprocket_2x_right": {
        "name": "2x 链轮（右）",
        "color": "#e0c07a",
        "explosion": [36, 0, 28],
    },
}
for part in payload.get("parts", []):
    stem = Path(str(part.get("file", ""))).stem
    extra = names.get(stem)
    if extra is None:
        continue
    part.update(extra)
    part["role"] = "printed"
    part["visible"] = True
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
path.write_text(text, encoding="utf-8")
path.with_name("parts.json").write_text(text, encoding="utf-8")
print(f"已标注零件名: {path}")
PY
}

# ===== 分区：公开 API =====
[[ -f "$PLACE_PY" ]] || die "找不到 $PLACE_PY"
[[ -f "$MANIFEST_PY" ]] || die "找不到 $MANIFEST_PY"
[[ -f "$PREVIEW_SH" ]] || die "找不到 $PREVIEW_SH"

python3 "$PLACE_PY" --center-distance "$CENTER_DISTANCE_MM" --out-dir "$LAYOUT_DIR"

if [[ -f "$INSPECT_PY" ]]; then
    python3 "$INSPECT_PY" "${LAYOUT_DIR}/ch1_03c_sprocket_1x_left.stl"
    python3 "$INSPECT_PY" "${LAYOUT_DIR}/ch1_03c_sprocket_2x_right.stl"
fi

python3 "$MANIFEST_PY" \
    --stl-dir "$LAYOUT_DIR" \
    --preview-dir "$PREVIEW_DIR" \
    --title "CH1 03C 链轮布局 · 左 1x / 右 2x · 中心距 200 mm" \
    --role printed \
    --no-recursive

patch_manifest

"$PREVIEW_SH" start "$PREVIEW_DIR" --no-open

# ===== 分区：业务逻辑 =====
# 不调用 OpenSCAD：OpenSCAD MCP 当前不可用，且 1x/2x 网格已经导出过。
# 预览目录只链入 sprocket-layout，避免把链条零件一起灌进页面。

# ===== 分区：方法/工具 =====
# 中心距可用第一个参数覆盖，例如: scripts/preview_ch1_03c_sprocket_layout.sh 200
