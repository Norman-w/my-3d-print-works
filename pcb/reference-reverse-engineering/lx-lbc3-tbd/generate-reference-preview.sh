#!/bin/sh
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
KICAD_APP=${KICAD_APP:-/Applications/KiCad/KiCad.app}
KPY="$KICAD_APP/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9"
KCLI="$KICAD_APP/Contents/MacOS/kicad-cli"

if [ ! -x "$KPY" ] || [ ! -x "$KCLI" ]; then
    echo "KiCad 9 command-line tools were not found under: $KICAD_APP" >&2
    exit 2
fi

"$KPY" "$HERE/generate_reference_preview.py"

mkdir -p "$HERE/output"
sips -s format png "$HERE/output/photo_calibrated_layout.svg" \
    --out "$HERE/output/photo_calibrated_layout.png" >/dev/null
"$KCLI" pcb export svg \
    --output "$HERE/output/reference_top.svg" \
    --layers F.SilkS,F.Mask,Edge.Cuts \
    --page-size-mode 2 --exclude-drawing-sheet --mode-single \
    "$HERE/lx-lbc3-reference-tbd.kicad_pcb"
"$KCLI" pcb export svg \
    --output "$HERE/output/reference_bottom.svg" \
    --layers B.SilkS,B.Mask,Edge.Cuts \
    --mirror --page-size-mode 2 --exclude-drawing-sheet --mode-single \
    "$HERE/lx-lbc3-reference-tbd.kicad_pcb"
# KiCad's SVG exporter leaves trailing spaces; normalize generated text so
# committed previews remain reviewable and pass git diff --check.
perl -pi -e 's/[ \t]+$//' "$HERE/output/reference_top.svg" "$HERE/output/reference_bottom.svg"
"$KCLI" pcb render --side top --width 1600 --height 1200 \
    --background opaque --quality high --floor \
    -o "$HERE/output/reference_3d_top.png" \
    "$HERE/lx-lbc3-reference-tbd.kicad_pcb"
"$KCLI" pcb render --side top --width 1600 --height 1200 \
    --background opaque --quality high --floor --perspective \
    --rotate 35,0,35 --zoom 1.15 \
    -o "$HERE/output/reference_3d_iso.png" \
    "$HERE/lx-lbc3-reference-tbd.kicad_pcb"
"$KPY" "$HERE/validate_reference_preview.py"

echo "Generated reference-only KiCad previews in $HERE/output"
