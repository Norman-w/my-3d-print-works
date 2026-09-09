#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
output_dir="$project_root/output/previews/views"
openscad_bin="${OPENSCAD_BIN:-$(command -v openscad || true)}"
openscad_bin="${openscad_bin:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"

if [[ ! -x "$openscad_bin" ]]; then
  echo "OpenSCAD executable not found: $openscad_bin" >&2
  exit 1
fi

mkdir -p "$output_dir"

render_view() {
  local name="$1"
  local camera="$2"
  local mode="$3"
  "$openscad_bin" \
    -D "model_mode=\"$mode\"" --render \
    --imgsize=1200,900 \
    --viewall \
    --autocenter \
    --camera="$camera" \
    -o "$output_dir/${mode}_${name}.png" \
    "$project_root/orthokeratology_lens_cleaning_kit_box.scad"
}

render_view top "0,0,0,0,0,0,330" print
render_view bottom "0,0,0,180,0,0,330" print
render_view front "0,0,0,90,0,0,330" print
render_view back "0,0,0,-90,0,0,330" print
render_view left "0,0,0,90,0,90,330" print
render_view right "0,0,0,90,0,-90,330" print
render_view iso "0,0,0,58,0,28,330" print
render_view front "0,0,0,90,0,0,250" closed
render_view back "0,0,0,90,0,180,250" closed
render_view top "0,0,0,0,0,0,250" closed
render_view iso "0,0,0,65,0,150,250" section

echo "All print-state view renders complete: $output_dir"
