#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
output_dir="$project_root/output/previews"
openscad_bin="${OPENSCAD_BIN:-$(command -v openscad || true)}"
openscad_bin="${openscad_bin:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"

if [[ ! -x "$openscad_bin" ]]; then
  echo "OpenSCAD executable not found: $openscad_bin" >&2
  exit 1
fi

mkdir -p "$output_dir"

"$openscad_bin" \
  -D 'model_mode="print"' --render \
  --imgsize=1500,1100 \
  --viewall \
  --autocenter \
  --camera=0,0,0,58,0,28,330 \
  -o "$output_dir/print_in_place_open.png" \
  "$project_root/orthokeratology_lens_cleaning_kit_box.scad"

"$openscad_bin" \
  -D 'model_mode="closed"' --render \
  --imgsize=1200,900 \
  --viewall \
  --autocenter \
  --camera=0,0,0,62,0,24,230 \
  -o "$output_dir/closed_preview.png" \
  "$project_root/orthokeratology_lens_cleaning_kit_box.scad"

echo "Preview renders complete: $output_dir"
