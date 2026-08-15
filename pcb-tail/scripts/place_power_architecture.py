#!/usr/bin/env python3
"""Place the tail-board power rework without creating copper.

The eight added low-profile parts stay on F.Cu, where the board had an unused
region and the enclosure provides 3.8 mm nominal component space between F.Cu
and the inside of the 2 mm tail wall.  C6 moves only 0.20/0.25 mm to clear the
corrected U3 and 1206 courtyards.  Every other footprint pose is immutable.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

try:
    import pcbnew
except ImportError as exc:  # pragma: no cover - KiCad runtime only
    raise SystemExit("run with KiCad 9's bundled Python") from exc


REPO = Path(__file__).resolve().parents[2]
PCB = REPO / "pcb-tail/layouts/default/default.kicad_pcb"

# x mm, y mm, orientation deg, target copper layer
PLACEMENTS = {
    "c_vout": (9.277998, 5.457000, 0.0, pcbnew.B_Cu),
    "u_vbus_limit": (7.000000, 4.800000, 0.0, pcbnew.F_Cu),
    "c_vbus_limit": (3.800000, 4.800000, 90.0, pcbnew.F_Cu),
    "r_vbus_ilim": (10.000000, 4.800000, 90.0, pcbnew.F_Cu),
    "u_system_limit": (8.500000, -4.500000, 0.0, pcbnew.F_Cu),
    "c_system_limit_in": (5.300000, -4.500000, 90.0, pcbnew.F_Cu),
    "c_system_limit_out": (11.700000, -5.200000, 90.0, pcbnew.F_Cu),
    "r_system_ilim": (11.700000, -1.500000, 0.0, pcbnew.F_Cu),
    "d_key_isolate": (7.500000, -8.300000, 0.0, pcbnew.F_Cu),
}


class PlacementError(RuntimeError):
    pass


def _address(fp: "pcbnew.FOOTPRINT") -> str:
    if not fp.HasFieldByName("atopile_address"):
        return ""
    return fp.GetFieldByName("atopile_address").GetText()


def place(pcb_path: Path) -> None:
    board = pcbnew.LoadBoard(str(pcb_path))
    if list(board.GetTracks()) or board.GetAreaCount():
        raise PlacementError("board must have no tracks/vias/zones")
    parts = {_address(fp): fp for fp in board.GetFootprints()}
    if "" in parts or not set(PLACEMENTS).issubset(parts):
        raise PlacementError("footprint address inventory mismatch")

    protected = {
        address: (
            fp.GetPosition().x,
            fp.GetPosition().y,
            fp.GetOrientationDegrees(),
            fp.GetLayer(),
        )
        for address, fp in parts.items()
        if address not in PLACEMENTS
    }

    for address, (x, y, angle, layer) in PLACEMENTS.items():
        fp = parts[address]
        position = pcbnew.VECTOR2I_MM(x, y)
        if fp.GetLayer() != layer:
            if {fp.GetLayer(), layer} != {pcbnew.F_Cu, pcbnew.B_Cu}:
                raise PlacementError(f"unsupported layer change for {address}")
            fp.Flip(position, pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        fp.SetPosition(position)
        fp.SetOrientationDegrees(angle)
        if address != "c_vout":
            fp.Reference().SetVisible(False)
            fp.Value().SetVisible(False)

    for address, expected in protected.items():
        fp = parts[address]
        position = fp.GetPosition()
        actual = (
            position.x,
            position.y,
            fp.GetOrientationDegrees(),
            fp.GetLayer(),
        )
        if actual != expected:
            raise PlacementError(f"protected footprint moved: {address}")

    temporary = pcb_path.with_name(
        f".{pcb_path.stem}.{uuid.uuid4().hex}.placement.tmp.kicad_pcb"
    )
    pcbnew.SaveBoard(str(temporary), board)
    verify = pcbnew.LoadBoard(str(temporary))
    if verify is None or list(verify.GetTracks()) or verify.GetAreaCount():
        temporary.unlink(missing_ok=True)
        raise PlacementError("saved-board verification failed")
    for suffix in (".kicad_pro", ".kicad_prl"):
        temporary.with_suffix(suffix).unlink(missing_ok=True)
    os.replace(temporary, pcb_path)
    print("Tail power placement PASS")
    print("  8 new low-profile parts placed on F.Cu; no copper created")
    print("  C6 shifted +0.20 mm X / +0.25 mm Y for courtyard clearance")
    print("  all other footprint poses preserved")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcb", type=Path, default=PCB)
    args = parser.parse_args()
    place(args.pcb.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PlacementError as exc:
        print(f"PLACEMENT FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
