#!/usr/bin/env python3
"""Draw the embedded rigid PCB substrate outline.

This script is intentionally narrow: it removes only existing Edge.Cuts and
draws the PCB substrate that should sit in the SCAD slot.  It does not place
components, create module cutouts, or touch reference drawings.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, polyline, remove_drawings_on_layers, save_board
from rigid_pcb.tools.mech_geometry import PCB_SLOT_POINTS


DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    removed = remove_drawings_on_layers(board, {pcbnew.Edge_Cuts})
    polyline(pcbnew, board, pcbnew.Edge_Cuts, PCB_SLOT_POINTS, 0.10)
    save_board(board, args.board)
    print(f"drew embedded substrate in {args.board} (removed {removed} Edge.Cuts drawings)")


if __name__ == "__main__":
    main()
