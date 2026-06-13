#!/usr/bin/env python3
"""Step 2 — Draw PCB substrate outline on Edge.Cuts.

Derived from the SCAD slot reference with three mechanical adjustments:
  1. Edge inset — every edge shifted inward by SUBSTRATE_EDGE_CLEARANCE (0.30 mm)
     so the PCB fits inside the enclosure slot with manufacturing tolerance.
  2. PZT dock retreat — the portions near PZT cavities are shortened toward the
     mainland hub so the PCB does not collide with the 20.5 mm cavities.
  3. Handle tail shorten — the handle-end PCB stops at Y=-88 (SCAD) instead of
     Y=-108 so the rigid PCB ends inside the handle cavity.

This step ONLY clears and redraws Edge.Cuts.  It does not touch Dwgs.User
(where Step 1 placed the SCAD reference contour and X±/Y± markers), so the
coordinate frame remains visible for verification.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import (
    load_board,
    polyline,
    remove_drawings_on_layers,
    save_board,
)
from rigid_pcb.tools.mech_geometry import (
    PCB_SLOT_POINTS,
    SCAD_SLOT_POINTS,
    SUBSTRATE_EDGE_CLEARANCE,
    SUBSTRATE_TAIL_MAX_Y,
)

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"


# ===== 分区：公开 API =====
def main() -> None:
    parser = argparse.ArgumentParser(description="Step 2: Draw PCB substrate outline on Edge.Cuts")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)

    # Clear only Edge.Cuts — preserve Dwgs.User (SCAD ref + X±/Y± markers)
    removed = remove_drawings_on_layers(board, {pcbnew.Edge_Cuts})

    # Draw the processed PCB substrate polygon
    polyline(pcbnew, board, pcbnew.Edge_Cuts, PCB_SLOT_POINTS, 0.10)

    save_board(board, args.board)

    xs = [p[0] for p in PCB_SLOT_POINTS]
    ys = [p[1] for p in PCB_SLOT_POINTS]
    scad_ys = [slot_scad_to_kicad_y(p[1]) for p in SCAD_SLOT_POINTS]

    print(f"=== Step 2 完成 ===")
    print(f"清除了 Edge.Cuts 上 {removed} 个旧图形")
    print(f"PCB 基材 BBox: X=[{min(xs):.2f}, {max(xs):.2f}] Y=[{min(ys):.2f}, {max(ys):.2f}]")
    print(f"PCB 轮廓采样点数: {len(PCB_SLOT_POINTS)}")
    print(f"语义: 每条边平行内缩 {SUBSTRATE_EDGE_CLEARANCE:.2f}mm + PZT码头缩回 + 拍柄截断 Ymax≤{SUBSTRATE_TAIL_MAX_Y:.2f}")


def slot_scad_to_kicad_y(y: float) -> float:
    """Quick Y-only conversion for info display."""
    from rigid_pcb.tools.mech_geometry import SCAD_TO_KICAD_Y_OFFSET

    return -y + SCAD_TO_KICAD_Y_OFFSET


if __name__ == "__main__":
    main()
