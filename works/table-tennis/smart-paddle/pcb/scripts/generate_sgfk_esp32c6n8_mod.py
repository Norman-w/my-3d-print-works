#!/usr/bin/env python3
# ===== 分区：导入/依赖 =====
"""从校本 pinmap 生成 SGFK_ESP32-C6-N8_CUTOUT.kicad_mod（只写库封装，不碰 .kicad_pcb）。"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pcb"))

from lib.esp32c6n8.pinmap import (  # noqa: E402
    BODY_MM,
    ORIENTATION,
    PAD_SIZE_MM,
    PADS,
    PITCH_MM,
    drill_mm,
    pad_xy,
)

# ===== 分区：常量/配置 =====

_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
OUT = (
    ROOT
    / "pcb"
    / "layouts"
    / "lib"
    / "footprints.pretty"
    / "SGFK_ESP32-C6-N8_CUTOUT.kicad_mod"
)

# ===== 分区：方法/工具 =====


def _uid(tag: str) -> str:
    return str(uuid.uuid5(_NS, f"sgfk-c6-n8:{tag}"))


def _fmt(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


def build_mod() -> str:
    length, width = BODY_MM
    hx, hy = length / 2, width / 2
    drill = drill_mm()
    pad_sz = PAD_SIZE_MM
    lines = [
        '(footprint "SGFK_ESP32-C6-N8_CUTOUT"',
        "  (version 20240108)",
        '  (generator "pcb/scripts/generate_sgfk_esp32c6n8_mod.py")',
        '  (layer "F.Cu")',
        '  (descr "SGFK ESP32-C6-N8 castellated: from pcb/lib/esp32c6n8/pinmap.py; '
        f'top/component view; ANT {ORIENTATION["antenna"]}; '
        f'pin1-14 at {ORIENTATION["pin1_to_14_edge"]} (handle); '
        f'pin15-28 at {ORIENTATION["pin15_to_28_edge"]} (tip/IMU); '
        f'pitch {PITCH_MM}; drill Ø{drill}")',
        '  (tags "SGFK ESP32-C6-N8 castellated thru_hole SmartPaddle")',
        "  (attr through_hole)",
        '  (fp_text reference "REF**" (at 0 -11.5) (layer "F.SilkS")',
        "    (effects (font (size 1 1) (thickness 0.15)))",
        "  )",
        '  (fp_text value "SGFK_ESP32-C6-N8_CUTOUT" (at 0 11.5) (layer "F.Fab") hide',
        "    (effects (font (size 1 1) (thickness 0.15)))",
        "  )",
        f'  (fp_rect (start {_fmt(-hx)} {_fmt(-hy)}) (end {_fmt(hx)} {_fmt(hy)}) '
        f'(stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))',
        f'  (fp_rect (start {_fmt(-(hx + 0.5))} {_fmt(-(hy + 1.2))}) '
        f'(end {_fmt(hx + 0.5)} {_fmt(hy + 1.2)}) '
        f'(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
        f'  (fp_line (start {_fmt(-hx)} {_fmt(-hy)}) (end {_fmt(-hx)} {_fmt(hy)}) '
        f'(stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
        f'  (fp_line (start {_fmt(hx)} {_fmt(-hy)}) (end {_fmt(hx)} {_fmt(hy)}) '
        f'(stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
        f'  (fp_line (start {_fmt(-hx)} {_fmt(-hy)}) (end {_fmt(hx)} {_fmt(-hy)}) '
        f'(stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
        f'  (fp_line (start {_fmt(-hx)} {_fmt(hy)}) (end -6.95 {_fmt(hy)}) '
        f'(stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
        f'  (fp_line (start -4.75 {_fmt(hy)}) (end {_fmt(hx)} {_fmt(hy)}) '
        f'(stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
        f'  (fp_rect (start -12.10 -8.20) (end -6.15 8.20) '
        f'(stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))',
        f'  (fp_text user "ANT" (at -9.15 0 90) (layer "F.Fab") '
        f'(uuid "{_uid("txt-ant")}")',
        "    (effects (font (size 0.8 0.8) (thickness 0.10)))",
        "  )",
        '  (fp_circle (center -12.05 8.20) (end -11.70 8.20) '
        '(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))',
    ]
    for pad in range(1, 29):
        x, y = pad_xy(pad)
        silk = PADS[pad]["silk"]
        outward = 0.70
        fs = 0.45 if len(silk) >= 4 else 0.55
        th = 0.07 if len(silk) >= 4 else 0.08
        # 与 −Y 正确排对称：锚点在焊盘外侧，字向体外发散（勿压邮票孔）
        # −Y：270° + left → 读向 −Y；+Y：90° + right → 读向 +Y（left 会往里盖焊盘）
        if y > 0:
            tx, ty, angle, just = x, y + outward, 90, "right"
        else:
            tx, ty, angle, just = x, y - outward, 270, "left"
        lines.append(
            f'  (pad "{pad}" thru_hole circle (at {_fmt(x)} {_fmt(y)}) '
            f"(size {_fmt(pad_sz)} {_fmt(pad_sz)}) (drill {_fmt(drill)}) "
            f'(layers "*.Cu" "*.Mask") (uuid "{_uid(f"pad-{pad}")}"))'
        )
        lines.append(
            f'  (fp_text user "{silk}" (at {_fmt(tx)} {_fmt(ty)} {angle}) '
            f'(layer "F.Fab") (uuid "{_uid(f"silk-pad-{pad}")}")'
        )
        lines.append(
            f"    (effects (font (size {_fmt(fs)} {_fmt(fs)}) "
            f"(thickness {_fmt(th)})) (justify {just}))"
        )
        lines.append("  )")
    lines.extend(
        [
            '  (model "${KIPRJMOD}/../lib/3dmodels/SGFK_ESP32-C6-N8_CUTOUT.wrl"',
            "    (offset (xyz 0 0 -0.8))",
            "    (scale (xyz 0.3937008 0.3937008 0.3937008))",
            "    (rotate (xyz 0 0 0))",
            "  )",
            ")",
            "",
        ]
    )
    return "\n".join(lines)


# ===== 分区：公开 API =====


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_mod(), encoding="utf-8")
    print(f"✓ wrote {OUT.relative_to(ROOT)}")
    print(f"  pad1={pad_xy(1)} pad14={pad_xy(14)} pad15={pad_xy(15)} pad28={pad_xy(28)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
