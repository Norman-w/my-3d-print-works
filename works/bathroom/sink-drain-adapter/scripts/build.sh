#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
SCAD_FILE="$ROOT_DIR/src/sink_drain_adapter.scad"
STL_FILE="$ROOT_DIR/output/3d-print/sink_drain_adapter_v0.1.stl"
PREVIEW_FILE="$ROOT_DIR/output/previews/sink_drain_adapter_v0.1_isometric_axes.png"
CUTAWAY_FILE="$ROOT_DIR/output/previews/sink_drain_adapter_v0.1_cutaway_isometric_axes.png"
REPORT_FILE="$ROOT_DIR/output/validation/sink_drain_adapter_v0.1.stl.json"
INSPECT="/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py"

OPENSCAD_BIN="${OPENSCAD_BIN:-$(command -v openscad || true)}"
if [[ -z "$OPENSCAD_BIN" || ! -x "$OPENSCAD_BIN" ]]; then
  echo "错误：找不到可执行的 OpenSCAD CLI；请设置 OPENSCAD_BIN。" >&2
  exit 1
fi

mkdir -p "$(dirname "$STL_FILE")" "$(dirname "$PREVIEW_FILE")" "$(dirname "$REPORT_FILE")"

(
  cd "$ROOT_DIR"
  "$OPENSCAD_BIN" -o "$STL_FILE" "$SCAD_FILE"
  "$OPENSCAD_BIN" --render --projection=o --view=axes --imgsize=1200,1200 \
    -o "$PREVIEW_FILE" "$SCAD_FILE"
  "$OPENSCAD_BIN" --render --projection=o --view=axes --imgsize=1200,1200 \
    -D preview_cutaway=true -o "$CUTAWAY_FILE" "$SCAD_FILE"
)

python3 "$INSPECT" "$STL_FILE" --require-watertight --output "$REPORT_FILE"
echo "完成：$STL_FILE"
echo "完成：$PREVIEW_FILE"
echo "完成：$CUTAWAY_FILE"
echo "完成：$REPORT_FILE"
