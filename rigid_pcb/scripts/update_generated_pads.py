#!/usr/bin/env python3
"""Create generated pads/placeholder footprints without moving existing ones.

This script is intentionally conservative.  If a footprint reference already
exists, it is left in place so manual placement survives repeated updates.

Electrical intent belongs in ../main.ato. Net names used here must mirror that
logic source; this script only materializes special pads/placeholders for KiCad.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, mk, save_board, slot_basis, xy


DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"
PARAMS = ROOT / "shared" / "board_params.yaml"


def ensure_net(pcbnew, board, nets: dict[str, object], name: str):
    if name in nets:
        return nets[name]
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    nets[name] = net
    return net


def hide_texts(fp) -> None:
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)


def make_fp(pcbnew, board, ref: str, value: str, x: float, y: float, rot: float = 0.0):
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetFPIDAsString(f"SmartPaddle:{ref}")
    fp.SetAttributes(pcbnew.FP_SMD)
    hide_texts(fp)
    fp.SetLayer(pcbnew.F_Cu)
    fp.SetPosition(xy(pcbnew, x, y))
    fp.SetOrientationDegrees(rot)
    board.Add(fp)
    return fp


def add_pad(pcbnew, fp, num: int, rel: tuple[float, float], size: tuple[float, float], net):
    pad = pcbnew.PAD(fp)
    pad.SetNumber(str(num))
    pad.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetFPRelativePosition(xy(pcbnew, *rel))
    pad.SetSize(pcbnew.VECTOR2I(mk(size[0]), mk(size[1])))
    pad.SetOrientationDegrees(fp.GetOrientationDegrees())
    if net is not None:
        pad.SetNet(net)
    layers = pcbnew.LSET()
    for layer in [pcbnew.F_Cu, pcbnew.F_Paste, pcbnew.F_Mask]:
        layers.addLayer(layer)
    pad.SetLayerSet(layers)
    fp.Add(pad)


def ref_exists(board, ref: str) -> bool:
    return board.FindFootprintByReference(ref) is not None


def add_wire_pad(pcbnew, board, ref: str, value: str, x: float, y: float, net, rot: float, size=(2.4, 1.4)):
    if ref_exists(board, ref):
        return False
    fp = make_fp(pcbnew, board, ref, value, x, y, rot)
    add_pad(pcbnew, fp, 1, (0, 0), size, net)
    return True


def add_two_pad(pcbnew, board, ref: str, value: str, x: float, y: float, n1, n2, rot: float):
    if ref_exists(board, ref):
        return False
    fp = make_fp(pcbnew, board, ref, value, x, y, rot)
    add_pad(pcbnew, fp, 1, (0, -0.8), (1.0, 0.7), n1)
    add_pad(pcbnew, fp, 2, (0, 0.8), (1.0, 0.7), n2)
    return True


def add_sot23(pcbnew, board, ref: str, value: str, x: float, y: float, mapping: dict[int, object], rot: float):
    if ref_exists(board, ref):
        return False
    fp = make_fp(pcbnew, board, ref, value, x, y, rot)
    for num, rel in {1: (-0.95, -0.65), 2: (0.95, -0.65), 3: (0, 0.95)}.items():
        add_pad(pcbnew, fp, num, rel, (0.32, 0.24), mapping.get(num))
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument(
        "--legacy-create",
        action="store_true",
        help="create pre-atopile placeholder PZT footprints; normally leave disabled",
    )
    args = parser.parse_args()

    if not args.legacy_create:
        print("update_generated_pads.py is legacy; use atopile + place_atopile_scaffold.py")
        return

    import pcbnew

    board = load_board(pcbnew, args.board)
    nets = {net.GetNetname(): net for net in board.GetNetInfo().NetsByName().values()}
    params = yaml.safe_load(PARAMS.read_text())

    created = 0
    gnd = ensure_net(pcbnew, board, nets, "GND")
    vcc = ensure_net(pcbnew, board, nets, "VCC")

    for pzt in params["components"]["piezo"]:
        pid = pzt["id"]
        x, y0 = pzt["position"]
        y = -y0
        sn = ensure_net(pcbnew, board, nets, f"{pid}_SIGNAL")
        (ux, uy), (nx, ny), slot_rot = slot_basis(x, y)
        part_rot = slot_rot - 90

        lead_base = (x + ux * 12.8, y + uy * 12.8)
        sig = (lead_base[0] - nx * 2.0, lead_base[1] - ny * 2.0)
        g = (lead_base[0] + nx * 2.0, lead_base[1] + ny * 2.0)
        rpos = (x + ux * 16.6, y + uy * 16.6)
        dpos = (x + ux * 19.2, y + uy * 19.2)

        created += add_wire_pad(pcbnew, board, pid, pid, sig[0], sig[1], sn, slot_rot)
        created += add_wire_pad(pcbnew, board, f"{pid}_G", "PZT_G", g[0], g[1], gnd, slot_rot)
        created += add_two_pad(pcbnew, board, f"R_{pid}", "1M", rpos[0], rpos[1], sn, gnd, slot_rot)
        created += add_sot23(pcbnew, board, f"D_{pid}", "BAT54S", dpos[0], dpos[1], {1: sn, 2: gnd, 3: vcc}, part_rot)

    save_board(board, args.board)
    print(f"Generated missing pads/parts in {args.board} (created {created}; existing references preserved)")


if __name__ == "__main__":
    main()
