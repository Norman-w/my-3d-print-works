#!/usr/bin/env python3
"""Update only Edge.Cuts board outline and module cutouts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, polyline, rect, remove_drawings_on_layers, save_board
from rigid_pcb.tools.mech_geometry import ESP32_CUTOUT, IMU_CUTOUT, PCB_SLOT_POINTS


DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    removed = remove_drawings_on_layers(board, {pcbnew.Edge_Cuts})

    polyline(pcbnew, board, pcbnew.Edge_Cuts, PCB_SLOT_POINTS, 0.10)
    rect(pcbnew, board, pcbnew.Edge_Cuts, *ESP32_CUTOUT, 0.10)
    rect(pcbnew, board, pcbnew.Edge_Cuts, *IMU_CUTOUT, 0.10)

    save_board(board, args.board)
    print(f"Updated Edge.Cuts in {args.board} (removed {removed} old edge drawings)")


if __name__ == "__main__":
    main()
