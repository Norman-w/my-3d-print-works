#!/usr/bin/env python3
"""Update only KiCad reference geometry layers.

This script is safe to run after manual placement/routing: it clears and
redraws only Dwgs.User and Eco1.User reference drawings.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import circle, load_board, polyline, rect, remove_drawings_on_layers, save_board, scad_to_kicad
from rigid_pcb.tools.mech_geometry import ESP32_CUTOUT, IMU_CUTOUT, MAINLAND_RECT, M2_CLEARANCE_HOLES, PCB_SLOT_POINTS, SCAD_SLOT_POINTS


DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"
PARAMS = ROOT / "shared" / "board_params.yaml"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    removed = remove_drawings_on_layers(board, {pcbnew.Dwgs_User, pcbnew.Eco1_User})

    params = yaml.safe_load(PARAMS.read_text())
    polyline(pcbnew, board, pcbnew.Dwgs_User, [scad_to_kicad(p) for p in SCAD_SLOT_POINTS], 0.15)
    polyline(pcbnew, board, pcbnew.Eco1_User, PCB_SLOT_POINTS, 0.12)
    rect(pcbnew, board, pcbnew.Dwgs_User, *MAINLAND_RECT, 0.08)
    rect(pcbnew, board, pcbnew.Eco1_User, *ESP32_CUTOUT, 0.10)
    rect(pcbnew, board, pcbnew.Eco1_User, *IMU_CUTOUT, 0.10)

    for pzt in params["components"]["piezo"]:
        x, y = pzt["position"]
        circle(pcbnew, board, pcbnew.Dwgs_User, x, -y, pzt["cavity_diameter"] / 2, 0.12)

    for sx, sy in params["keep_out_zones"][0]["positions"]:
        circle(pcbnew, board, pcbnew.Dwgs_User, sx, -sy, params["keep_out_zones"][0]["clearance_radius"], 0.08)

    for x, y, r in M2_CLEARANCE_HOLES:
        circle(pcbnew, board, pcbnew.Eco1_User, x, y, r, 0.08)

    save_board(board, args.board)
    print(f"Updated reference layers in {args.board} (removed {removed} old reference drawings)")


if __name__ == "__main__":
    main()
