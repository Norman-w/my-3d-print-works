#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
model_file="$project_root/orthokeratology_lens_cleaning_kit_box.scad"
output_dir="$project_root/output/3d-print"
openscad_bin="${OPENSCAD_BIN:-$(command -v openscad || true)}"
openscad_bin="${openscad_bin:-/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD}"

if [[ ! -x "$openscad_bin" ]]; then
  echo "OpenSCAD executable not found: $openscad_bin" >&2
  echo "Set OPENSCAD_BIN to an installed OpenSCAD CLI and retry." >&2
  exit 1
fi

mkdir -p "$output_dir"

pids=()
for mode in print closed base lid open90 section coupon; do
  case "$mode" in
    print) output_name="orthokeratology_lens_cleaning_kit_box_print_in_place_open.stl" ;;
    closed) output_name="orthokeratology_lens_cleaning_kit_box_closed_preview.stl" ;;
    base) output_name="orthokeratology_lens_cleaning_kit_box_base.stl" ;;
    lid) output_name="orthokeratology_lens_cleaning_kit_box_lid.stl" ;;
    open90) output_name="orthokeratology_lens_cleaning_kit_box_open90.stl" ;;
    section) output_name="orthokeratology_lens_cleaning_kit_box_section.stl" ;;
    coupon) output_name="orthokeratology_lens_cleaning_kit_box_hinge_coupon.stl" ;;
    *) echo "Unknown export mode: $mode" >&2; exit 1 ;;
  esac
  output_file="$output_dir/$output_name"
  echo "Exporting $mode -> $output_file"
  "$openscad_bin" \
    --backend=CGAL \
    -D "model_mode=\"$mode\"" \
    -o "$output_file" \
    "$model_file" &
  pids+=("$!")
done

failed=0
for job in "${pids[@]}"; do wait "$job" || failed=1; done
[[ "$failed" == 0 ]] || exit 1

echo "OpenSCAD export complete: $output_dir"
