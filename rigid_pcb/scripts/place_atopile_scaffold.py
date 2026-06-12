#!/usr/bin/env python3
"""Place atopile-generated footprints onto the mechanical scaffold.

This does not create footprints. It only moves footprints that already have an
`atopile_address` property. By default it moves only the obvious atopile initial
grid placements so later manual KiCad placement is preserved. Use `--force` to
re-apply the scaffold placement intentionally.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, save_board, slot_basis, xy
from rigid_pcb.tools.mech_geometry import ESP32_CUTOUT, IMU_CUTOUT


DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"
PARAMS = ROOT / "shared" / "board_params.yaml"


def address(fp) -> str | None:
    if not fp.HasFieldByName("atopile_address"):
        return None
    return fp.GetFieldByName("atopile_address").GetText()


def is_initial_grid(fp) -> bool:
    pos = fp.GetPosition()
    x = pos.x / 1_000_000
    y = pos.y / 1_000_000
    return math.isclose(x / 10, round(x / 10), abs_tol=1e-3) and math.isclose(
        y / 10, round(y / 10), abs_tol=1e-3
    )


def move(pcbnew, fp_by_addr, addr: str, x: float, y: float, rot: float, force: bool) -> int:
    fp = fp_by_addr.get(addr)
    if fp is None:
        return 0
    if not force and not is_initial_grid(fp):
        return 0
    fp.SetPosition(xy(pcbnew, x, y))
    fp.SetOrientationDegrees(rot)
    return 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--force", action="store_true", help="move already-placed footprints too")
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    params = yaml.safe_load(PARAMS.read_text())
    fp_by_addr = {addr: fp for fp in board.GetFootprints() if (addr := address(fp))}

    moved = 0

    moved += move(pcbnew, fp_by_addr, "mcu", ESP32_CUTOUT[0], ESP32_CUTOUT[1], 0, args.force)
    moved += move(pcbnew, fp_by_addr, "imu", IMU_CUTOUT[0], IMU_CUTOUT[1], 0, args.force)

    central = {
        "led.c_supply": (18.0, 14.0, 0),
        "led.r_data": (18.8, 8.0, 90),
        "power.q_power": (-17.2, 18.0, 90),
        "power.q_latch": (-17.2, 11.2, 90),
        "power.r_gate": (-12.5, 15.0, 0),
        "power.d_button": (-19.0, 15.0, 0),
        "power.r_button": (18.2, -2.8, 90),
        "power.r_latch_pd": (-18.4, 7.8, 0),
        "power.ldo": (-17.5, -4.8, 90),
        "power.c_in": (-18.7, -12.0, 0),
        "power.c_out": (-18.7, -15.2, 0),
    }
    for addr, (x, y, rot) in central.items():
        moved += move(pcbnew, fp_by_addr, addr, x, y, rot, args.force)

    tail = {
        "tail.bat_plus_pad": (-6.0, 96.5, 0),
        "tail.gnd_pad": (-2.0, 96.5, 0),
        "tail.led_plus_pad": (2.0, 96.5, 0),
        "tail.led_din_pad": (6.0, 96.5, 0),
        "tail.button_pad": (-4.0, 101.2, 0),
        "tail.usb_dp_pad": (0.0, 101.2, 0),
        "tail.usb_dn_pad": (4.0, 101.2, 0),
    }
    for addr, (x, y, rot) in tail.items():
        moved += move(pcbnew, fp_by_addr, addr, x, y, rot, args.force)

    for pzt in params["components"]["piezo"]:
        pid = pzt["id"]
        key = pid.lower()
        x, y0 = pzt["position"]
        y = -y0
        (ux, uy), (nx, ny), slot_rot = slot_basis(x, y)
        part_rot = slot_rot - 90
        lead_base = (x + ux * 13.5, y + uy * 13.5)
        sig = (lead_base[0] - nx * 1.65, lead_base[1] - ny * 1.65)
        gnd = (lead_base[0] + nx * 1.65, lead_base[1] + ny * 1.65)
        rpos = (x + ux * 18.0, y + uy * 18.0)
        dpos = (x + ux * 23.5, y + uy * 23.5)

        moved += move(pcbnew, fp_by_addr, f"{key}.pzt_signal_pad", sig[0], sig[1], slot_rot, args.force)
        moved += move(pcbnew, fp_by_addr, f"{key}.pzt_gnd_pad", gnd[0], gnd[1], slot_rot, args.force)
        moved += move(pcbnew, fp_by_addr, f"{key}.clamp_resistor", rpos[0], rpos[1], slot_rot, args.force)
        moved += move(pcbnew, fp_by_addr, f"{key}.clamp_diode", dpos[0], dpos[1], part_rot, args.force)

    save_board(board, args.board)
    print(f"placed {moved} atopile scaffold footprints in {args.board}")


if __name__ == "__main__":
    main()
