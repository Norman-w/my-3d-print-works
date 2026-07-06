#!/usr/bin/env python3
"""Step 2 — Draw PCB substrate outline on Edge.Cuts + inject screw-hole keepout zones.

Derived from the SCAD slot reference with three mechanical adjustments:
  1. Edge inset — every edge shifted inward by SUBSTRATE_EDGE_CLEARANCE (0.30 mm)
     so the PCB fits inside the enclosure slot with manufacturing tolerance.
  2. PZT dock retreat — the portions near PZT cavities are shortened toward the
     mainland hub so the PCB does not collide with the 20.5 mm cavities.
  3. Handle tail shorten — the handle-end PCB stops at Y=-88 (SCAD) instead of
     Y=-108 so the rigid PCB ends inside the handle cavity.

This step clears and redraws Edge.Cuts, then injects KiCad native keepout zones
around screw holes that pass through the PCB. Keepout zones are injected as
text S-expressions after pcbnew save (to avoid pcbnew stripping them).
"""

import argparse
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import (
    load_board,
    polyline,
    remove_drawings_on_layers,
    save_board,
)
from pcb.tools.mech_geometry import (
    PCB_CLEARANCE_HOLES,
    PCB_SLOT_POINTS,
    SCAD_SLOT_POINTS,
    SUBSTRATE_EDGE_CLEARANCE,
    SUBSTRATE_TAIL_MAX_Y,
)

DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
SCREW_KEEP_OUT_PREFIX = "SCREW_CLEARANCE_KEEP_OUT"


def _make_keepout_zone(zone_id, x, y, radius, layer):
    n_seg = 48
    pts = [f"(xy {x + radius * math.cos(2 * math.pi * i / n_seg):.6f} "
           f"{y + radius * math.sin(2 * math.pi * i / n_seg):.6f})"
           for i in range(n_seg)]
    name = f"{SCREW_KEEP_OUT_PREFIX}_{layer}_{x:.3f}_{y:.3f}"
    return f"""\t(zone
\t\t(zone_id {zone_id})
\t\t(name "{name}")
\t\t(keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
\t\t(layers "{layer}")
\t\t(hatch edge 0.508)
\t\t(priority 100)
\t\t(connect_pads no)
\t\t(min_thickness 0.15)
\t\t(filled_areas_thickness no)
\t\t(fill yes (mode solid) (thermal_gap 0.508) (thermal_bridge_width 0.508))
\t\t(polygon
\t\t\t(pts
\t\t\t\t{" ".join(pts)}
\t\t\t)
\t\t)
\t)"""


def _remove_generated_keepouts(content: str) -> str:
    return re.sub(
        rf'\n\t\(zone\n\t\t\(zone_id \d+\)\n\t\t\(name "{re.escape(SCREW_KEEP_OUT_PREFIX)}[^"]+"\).*?\n\t\)',
        '',
        content,
        flags=re.S,
    )


def _inject_keepout_zones(board_path):
    holes = PCB_CLEARANCE_HOLES
    if not holes:
        print("  (无螺丝孔穿过 PCB，跳过 keepout zone)")
        return 0

    content = _remove_generated_keepouts(board_path.read_text())
    max_zid = 0
    for m in re.finditer(r'\(zone_id (\d+)\)', content):
        max_zid = max(max_zid, int(m.group(1)))

    keepout_blocks = []
    for hx, hy, hr in holes:
        max_zid += 1
        keepout_blocks.append(_make_keepout_zone(max_zid, hx, hy, hr, 'F.Cu'))
        max_zid += 1
        keepout_blocks.append(_make_keepout_zone(max_zid, hx, hy, hr, 'B.Cu'))

    insert_at = content.rfind('\n\t(embedded_fonts')
    if insert_at < 0:
        insert_at = content.rfind(')\n')
    if insert_at < 0:
        raise RuntimeError(f"Unable to find PCB insertion point in {board_path}")
    new_content = content[:insert_at] + "\n" + "\n".join(keepout_blocks) + "\n" + content[insert_at:]
    board_path.write_text(new_content)
    return len(keepout_blocks)


def main():
    parser = argparse.ArgumentParser(description="Step 2: Draw PCB substrate outline + keepout zones")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    removed = remove_drawings_on_layers(board, {pcbnew.Edge_Cuts})
    polyline(pcbnew, board, pcbnew.Edge_Cuts, PCB_SLOT_POINTS, 0.10)
    save_board(board, args.board)

    n_keepout = _inject_keepout_zones(args.board)

    xs = [p[0] for p in PCB_SLOT_POINTS]
    ys = [p[1] for p in PCB_SLOT_POINTS]

    print(f"=== Step 2 完成 ===")
    print(f"清除了 Edge.Cuts 上 {removed} 个旧图形")
    print(f"PCB 基材 BBox: X=[{min(xs):.2f}, {max(xs):.2f}] Y=[{min(ys):.2f}, {max(ys):.2f}]")
    print(f"PCB 轮廓采样点数: {len(PCB_SLOT_POINTS)}")
    print(f"语义: 每条边平行内缩 {SUBSTRATE_EDGE_CLEARANCE:.2f}mm + PZT码头缩回 + 拍柄截断 Ymax≤{SUBSTRATE_TAIL_MAX_Y:.2f}")
    if n_keepout:
        print(f"螺丝孔 keepout: 注入了 {n_keepout} 个 zone (F.Cu + B.Cu)")


def slot_scad_to_kicad_y(y):
    from pcb.tools.mech_geometry import SCAD_TO_KICAD_Y_OFFSET
    return -y + SCAD_TO_KICAD_Y_OFFSET


if __name__ == "__main__":
    main()
