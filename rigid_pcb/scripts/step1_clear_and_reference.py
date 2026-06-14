#!/usr/bin/env python3
"""Step 1 — Clear PCB and draw SCAD reference with X±/Y± coordinate markers.

Destructive: removes all footprints, tracks/vias, zones, and drawings.
Then draws the SCAD slot contour on Dwgs.User plus direction arrows, axis
tick marks, PZT cavity circles, and X±/Y± text labels for coordinate
orientation.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import (
    circle,
    load_board,
    mk,
    polyline,
    save_board,
    shape_line,
    xy,
)
from rigid_pcb.tools.mech_geometry import (
    M2_CLEARANCE_HOLES,
    PZT_CAVITIES_SCAD,
    SCAD_SLOT_POINTS,
    SCAD_TO_KICAD_Y_OFFSET,
    slot_scad_to_kicad,
)

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"

# ===== 分区：方法/工具 =====


def add_text(pcbnew, board, text: str, x: float, y: float, size: float = 3.0) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetLayer(pcbnew.Dwgs_User)
    item.SetText(text)
    item.SetPosition(xy(pcbnew, x, y))
    item.SetTextHeight(mk(size))
    item.SetTextWidth(mk(size))
    item.SetTextThickness(mk(0.25))
    board.Add(item)


def clear_board(board) -> dict[str, int]:
    footprints = list(board.GetFootprints())
    tracks = list(board.GetTracks())
    zones = [board.GetArea(i) for i in range(board.GetAreaCount())]
    drawings = list(board.GetDrawings())

    removed = {"footprints": 0, "tracks_vias": 0, "zones": 0, "drawings": 0}

    for track in tracks:
        board.Remove(track)
        removed["tracks_vias"] += 1

    for zone in zones:
        board.Remove(zone)
        removed["zones"] += 1

    for drawing in drawings:
        board.Remove(drawing)
        removed["drawings"] += 1

    for fp in footprints:
        board.Remove(fp)
        removed["footprints"] += 1

    return removed


# ===== 分区：公开 API =====


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 1: Clear PCB and draw SCAD reference with X±/Y± markers")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    removed = clear_board(board)

    # ---- SCAD slot contour on Dwgs.User ----
    contour = [slot_scad_to_kicad(p) for p in SCAD_SLOT_POINTS]
    polyline(pcbnew, board, pcbnew.Dwgs_User, contour, 0.18)

    xs = [p[0] for p in contour]
    ys = [p[1] for p in contour]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2

    # ---- Centre cross with direction arrows ----
    arrow = 8.0
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, cy), (cx + arrow, cy), 0.15)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, cy), (cx, cy - arrow), 0.15)

    # ---- Axis tick marks at bounding-box edges ----
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (xmin - 4.0, cy), (xmin + 4.0, cy), 0.12)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (xmax - 4.0, cy), (xmax + 4.0, cy), 0.12)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, ymin - 4.0), (cx, ymin + 4.0), 0.12)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, ymax - 4.0), (cx, ymax + 4.0), 0.12)

    # ---- PZT cavity circles ----
    for pzt_x, pzt_y, pzt_r in PZT_CAVITIES_SCAD:
        kicad_x, kicad_y = slot_scad_to_kicad((pzt_x, pzt_y))
        circle(pcbnew, board, pcbnew.Dwgs_User, kicad_x, kicad_y, pzt_r, 0.12)

    # ---- M2 screw/reference holes ----
    for hole_x, hole_y, hole_r in M2_CLEARANCE_HOLES:
        circle(pcbnew, board, pcbnew.Dwgs_User, hole_x, hole_y, hole_r, 0.12)

    # ---- X± / Y± text markers ----
    add_text(pcbnew, board, "X+", xmax + 6.0, cy, 3.0)
    add_text(pcbnew, board, "X-", xmin - 14.0, cy, 3.0)
    add_text(pcbnew, board, "Y+", cx + 2.0, ymin - 8.0, 3.0)
    add_text(pcbnew, board, "Y-", cx + 2.0, ymax + 6.0, 3.0)

    save_board(board, args.board)

    print(f"=== Step 1 完成 ===")
    print(f"清除了: {removed}")
    print(f"SCAD→KiCad Y偏移: {SCAD_TO_KICAD_Y_OFFSET:.2f} mm")
    print(f"参考轮廓 BBox: X=[{xmin:.2f}, {xmax:.2f}] Y=[{ymin:.2f}, {ymax:.2f}]")
    print(f"中心: ({cx:.2f}, {cy:.2f})")
    print(f"PZT腔体: {len(PZT_CAVITIES_SCAD)} 个圆")
    print(f"M2参考孔: {len(M2_CLEARANCE_HOLES)} 个圆")
    print(f"方向标记: X± Y± 已标注")


if __name__ == "__main__":
    main()
