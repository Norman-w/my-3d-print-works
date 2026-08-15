#!/usr/bin/env python3
"""Generate the ESP32-S3-WROOM-1 embedded cutout footprint."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pcb"))

from lib.esp32s3wroom1.pinmap import (  # noqa: E402
    BODY_MM,
    ORIENTATION,
    PAD_SIZE_MM,
    PADS,
    PITCH_MM,
    drill_mm,
    pad_xy,
)

_NS = uuid.UUID("e9168082-47cc-4a4d-b099-159828d85dd8")
OUT = (
    ROOT
    / "pcb"
    / "layouts"
    / "lib"
    / "footprints.pretty"
    / "ESP32-S3-WROOM-1_CUTOUT.kicad_mod"
)


def _uid(tag: str) -> str:
    return str(uuid.uuid5(_NS, f"esp32-s3-wroom-1-cutout:{tag}"))


def _fmt(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _user_text(pad: int, x: float, y: float) -> list[str]:
    label = PADS[pad]["silk"]
    font = 0.42 if len(label) >= 4 else 0.50
    if pad <= 14:
        tx, ty, angle, justify = x, y + 0.72, 90, "right"
    elif pad <= 26:
        tx, ty, angle, justify = x + 0.72, y, 0, "left"
    else:
        tx, ty, angle, justify = x, y - 0.72, 270, "left"
    return [
        f'  (fp_text user "{label}" (at {_fmt(tx)} {_fmt(ty)} {angle}) '
        f'(layer "F.Fab") (uuid "{_uid(f"label-{pad}")}")',
        f"    (effects (font (size {_fmt(font)} {_fmt(font)}) (thickness 0.07)) "
        f"(justify {justify}))",
        "  )",
    ]


def build_mod() -> str:
    length, width = BODY_MM
    hx, hy = length / 2, width / 2
    lines = [
        '(footprint "ESP32-S3-WROOM-1_CUTOUT"',
        "  (version 20240108)",
        '  (generator "pcb/scripts/generate_esp32s3wroom1_cutout_mod.py")',
        '  (layer "F.Cu")',
        '  (descr "ESP32-S3-WROOM-1-N16R8 embedded half-hole interface; '
        f'top view; antenna {ORIENTATION["antenna"]}; pitch {PITCH_MM} mm; '
        'underside EP41 is unavailable in the cutout assembly")',
        '  (tags "ESP32-S3-WROOM-1 N16R8 embedded cutout SmartPaddle")',
        "  (attr through_hole)",
        '  (fp_text reference "REF**" (at 0 -11.1) (layer "F.SilkS")',
        "    (effects (font (size 0.8 0.8) (thickness 0.12)))",
        "  )",
        '  (fp_text value "ESP32-S3-WROOM-1-N16R8" (at 0 11.1) '
        '(layer "F.Fab") hide',
        "    (effects (font (size 0.8 0.8) (thickness 0.12)))",
        "  )",
        f'  (fp_rect (start {_fmt(-hx)} {_fmt(-hy)}) '
        f'(end {_fmt(hx)} {_fmt(hy)}) '
        '(stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))',
        f'  (fp_rect (start {_fmt(-(hx + 1.05))} {_fmt(-(hy + 1.05))}) '
        f'(end {_fmt(hx + 1.05)} {_fmt(hy + 1.05)}) '
        '(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
        # The module body coincides with an internal Edge.Cuts opening, so a
        # silk body rectangle would be clipped by fabrication. F.Fab remains
        # the assembly outline; the readable reference stays on F.SilkS.
        '  (fp_rect (start -12.75 -8.2) (end -6.2 8.2) '
        '(stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))',
        f'  (fp_text user "ANT" (at -9.45 0 90) (layer "F.Fab") '
        f'(uuid "{_uid("antenna")}")',
        "    (effects (font (size 0.8 0.8) (thickness 0.10)))",
        "  )",
        f'  (fp_text user "EP41: no host land (embedded)" (at 0 0 90) '
        f'(layer "F.Fab") (uuid "{_uid("ep41-note")}")',
        "    (effects (font (size 0.6 0.6) (thickness 0.08)))",
        "  )",
    ]
    for pad in range(1, 41):
        x, y = pad_xy(pad)
        lines.append(
            f'  (pad "{pad}" thru_hole circle (at {_fmt(x)} {_fmt(y)}) '
            f'(size {_fmt(PAD_SIZE_MM)} {_fmt(PAD_SIZE_MM)}) '
            f'(drill {_fmt(drill_mm())}) (layers "*.Cu" "*.Mask") '
            f'(uuid "{_uid(f"pad-{pad}")}"))'
        )
        lines.extend(_user_text(pad, x, y))
    lines.extend(
        [
            '  (model "${KIPRJMOD}/../lib/3dmodels/ESP32-S3-WROOM-1.step"',
            "    (offset (xyz 0 0 -0.8))",
            "    (scale (xyz 1 1 1))",
            "    (rotate (xyz 0 0 -90))",
            "  )",
            ")",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_mod(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(
        f"pad1={pad_xy(1)} pad14={pad_xy(14)} "
        f"pad15={pad_xy(15)} pad26={pad_xy(26)} "
        f"pad27={pad_xy(27)} pad40={pad_xy(40)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
