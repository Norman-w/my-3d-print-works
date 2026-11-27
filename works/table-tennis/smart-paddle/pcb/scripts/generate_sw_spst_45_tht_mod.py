#!/usr/bin/env python3
# ===== 分区：导入/依赖 =====
"""从 pcb/lib/tactile_45/params.py 生成 SW_SPST_4.5x4.5.kicad_mod（THT；只写库，不碰 PCB）。"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pcb"))

from lib.tactile_45.params import (  # noqa: E402
    BODY_MM,
    CRTYD_HALF_XY_MM,
    DRILL_MM,
    FAB_HALF_MM,
    PAD_SIZE_MM,
    PAD_XY_MM,
    SILK_HALF_MM,
)

# ===== 分区：常量/配置 =====

_NS = uuid.UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901")
OUT = (
    ROOT
    / "pcb"
    / "layouts"
    / "lib"
    / "footprints.pretty"
    / "SW_SPST_4.5x4.5.kicad_mod"
)

# ===== 分区：方法/工具 =====


def _uid(tag: str) -> str:
    return str(uuid.uuid5(_NS, f"sw-spst-45-tht:{tag}"))


def _fmt(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


def build_mod() -> str:
    cx, cy = CRTYD_HALF_XY_MM
    lines = [
        '(footprint "SW_SPST_4.5x4.5"',
        "  (version 20240108)",
        '  (generator "pcb/scripts/generate_sw_spst_45_tht_mod.py")',
        '  (layer "F.Cu")',
        f'  (descr "{BODY_MM}x{BODY_MM}mm SPST tactile THT '
        f'(same body as tail power key; pads from pcb/lib/tactile_45/params.py)")',
        '  (tags "tactile switch 4.5 SPST THT SmartPaddle")',
        "  (attr through_hole)",
        '  (fp_text reference "REF**" (at 0 -3.8) (layer "F.SilkS")',
        "    (effects (font (size 0.8 0.8) (thickness 0.12)))",
        "  )",
        '  (fp_text value "SW_4.5x4.5" (at 0 3.8) (layer "F.Fab") hide',
        "    (effects (font (size 0.7 0.7) (thickness 0.1)))",
        "  )",
        f'  (fp_rect (start -{ _fmt(FAB_HALF_MM) } -{ _fmt(FAB_HALF_MM) }) '
        f'(end { _fmt(FAB_HALF_MM) } { _fmt(FAB_HALF_MM) }) '
        f'(stroke (width 0.12) (type solid)) (fill none) (layer "F.Fab"))',
        f'  (fp_rect (start -{ _fmt(SILK_HALF_MM) } -{ _fmt(SILK_HALF_MM) }) '
        f'(end { _fmt(SILK_HALF_MM) } { _fmt(SILK_HALF_MM) }) '
        f'(stroke (width 0.15) (type solid)) (fill none) (layer "F.SilkS"))',
        f'  (fp_rect (start -{ _fmt(cx) } -{ _fmt(cy) }) '
        f'(end { _fmt(cx) } { _fmt(cy) }) '
        f'(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
        '  (fp_circle (center 0 0) (end 1.0 0) '
        '(stroke (width 0.15) (type solid)) (fill none) (layer "F.SilkS"))',
        '  (fp_circle (center 0 0) (end 0.6 0) '
        '(stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))',
    ]
    for i, (num, x, y) in enumerate(PAD_XY_MM):
        lines.append(
            f'  (pad "{num}" thru_hole circle (at {_fmt(x)} {_fmt(y)}) '
            f"(size {_fmt(PAD_SIZE_MM)} {_fmt(PAD_SIZE_MM)}) "
            f"(drill {_fmt(DRILL_MM)}) "
            f'(layers "*.Cu" "*.Mask") '
            f'(uuid "{_uid(f"pad{i}")}"))'
        )
    lines.append(")")
    lines.append("")
    return "\n".join(lines)


# ===== 分区：公开 API =====


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_mod(), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
