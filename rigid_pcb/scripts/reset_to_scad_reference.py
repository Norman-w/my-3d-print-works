#!/usr/bin/env python3
"""Reset the KiCad PCB to a single SCAD-derived reference outline.

This is intentionally destructive to the board layout only: it removes
footprints, drawings, tracks/vias, and zones from the .kicad_pcb, then draws one
reference contour converted from SCAD coordinates plus X/Y direction markers.
The electrical source files are not touched.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, mk, polyline, save_board, shape_line, xy
from rigid_pcb.tools.mech_geometry import SCAD_SLOT_POINTS, SCAD_TO_KICAD_Y_OFFSET, slot_scad_to_kicad


DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"


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

    removed = {
        "footprints": 0,
        "tracks_vias": 0,
        "zones": 0,
        "drawings": 0,
    }

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    removed = clear_board(board)

    contour = [slot_scad_to_kicad(p) for p in SCAD_SLOT_POINTS]
    polyline(pcbnew, board, pcbnew.Dwgs_User, contour, 0.18)

    xs = [p[0] for p in contour]
    ys = [p[1] for p in contour]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2

    arrow = 8.0
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, cy), (cx + arrow, cy), 0.15)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, cy), (cx, cy - arrow), 0.15)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (xmin - 4.0, cy), (xmin + 4.0, cy), 0.12)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (xmax - 4.0, cy), (xmax + 4.0, cy), 0.12)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, ymin - 4.0), (cx, ymin + 4.0), 0.12)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, ymax - 4.0), (cx, ymax + 4.0), 0.12)

    add_text(pcbnew, board, "X+", xmax + 6.0, cy, 3.0)
    add_text(pcbnew, board, "X-", xmin - 14.0, cy, 3.0)
    add_text(pcbnew, board, "Y+", cx + 2.0, ymin - 8.0, 3.0)
    add_text(pcbnew, board, "Y-", cx + 2.0, ymax + 6.0, 3.0)

    save_board(board, args.board)
    print(f"reset {args.board}")
    print("removed", removed)
    print(f"scad_to_kicad_y_offset {SCAD_TO_KICAD_Y_OFFSET:.2f} mm")
    print(f"scad_reference_bbox x=[{xmin:.2f}, {xmax:.2f}] y=[{ymin:.2f}, {ymax:.2f}]")


if __name__ == "__main__":
    main()
