#!/usr/bin/env python3
"""Add MCU and IMU module body openings to Edge.Cuts.

The openings use the modules' outside dimensions plus a small assembly
clearance.  This script appends only the two internal cutout contours, so run it
after draw_embedded_substrate.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, rect, save_board
from rigid_pcb.tools.mech_geometry import ESP32_CUTOUT, IMU_CUTOUT, MODULE_CUTOUT_CLEARANCE


DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    rect(pcbnew, board, pcbnew.Edge_Cuts, *ESP32_CUTOUT, 0.10)
    rect(pcbnew, board, pcbnew.Edge_Cuts, *IMU_CUTOUT, 0.10)
    save_board(board, args.board)
    print(f"drew MCU/IMU cutouts in {args.board}")
    print(f"module cutout clearance per side: {MODULE_CUTOUT_CLEARANCE:.2f} mm")
    print(f"ESP32 cutout: center=({ESP32_CUTOUT[0]:.2f}, {ESP32_CUTOUT[1]:.2f}) size=({ESP32_CUTOUT[2]:.2f}, {ESP32_CUTOUT[3]:.2f})")
    print(f"IMU cutout: center=({IMU_CUTOUT[0]:.2f}, {IMU_CUTOUT[1]:.2f}) size=({IMU_CUTOUT[2]:.2f}, {IMU_CUTOUT[3]:.2f})")


if __name__ == "__main__":
    main()
