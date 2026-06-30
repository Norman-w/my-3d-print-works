#!/usr/bin/env python3
"""Step 4.3 - finish deterministic PZT bridge electrical details.

This step is intentionally narrow and repeatable:
  1. add two layer-change vias for TL/TR PZT signal entries near the MCU pads;
  2. add/refill a solid B.Cu GND zone over the generated substrate outline.

The PZT dock placement and dock-to-mainland routing remain owned by the
step4.1/4.2 snapshot scripts and by the user's manual routing choices.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, mk, save_board, xy
from rigid_pcb.tools.mech_geometry import PCB_SLOT_POINTS

DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"

ZONE_NAME = "B_GND_POUR"
VIA_SIZE = 0.60
VIA_DRILL = 0.30
SIGNAL_TRACK_WIDTH = 0.20

PZT_SIGNAL_ENTRIES = [
    # net, x, MCU pad y, existing B.Cu stub end y, via y
    ("pzt_tr_signal", -2.66, -7.22, -7.301, -8.05),
    ("pzt_tl_signal", -3.93, -7.22, -7.301, -8.05),
]


def _same_point(point, x: float, y: float, tolerance_mm: float = 0.01) -> bool:
    return abs(point.x / 1e6 - x) <= tolerance_mm and abs(point.y / 1e6 - y) <= tolerance_mm


def _track_exists(pcbnew, board, net_name: str, layer: int, a: tuple[float, float], b: tuple[float, float]) -> bool:
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA):
            continue
        if item.GetNetname() != net_name or item.GetLayer() != layer:
            continue
        start = item.GetStart()
        end = item.GetEnd()
        if _same_point(start, *a) and _same_point(end, *b):
            return True
        if _same_point(start, *b) and _same_point(end, *a):
            return True
    return False


def _via_exists(pcbnew, board, net_name: str, x: float, y: float) -> bool:
    for item in board.GetTracks():
        if not isinstance(item, pcbnew.PCB_VIA):
            continue
        if item.GetNetname() == net_name and _same_point(item.GetPosition(), x, y):
            return True
    return False


def _add_track(pcbnew, board, net, layer: int, a: tuple[float, float], b: tuple[float, float], width: float) -> bool:
    if _track_exists(pcbnew, board, net.GetNetname(), layer, a, b):
        return False
    item = pcbnew.PCB_TRACK(board)
    item.SetStart(xy(pcbnew, *a))
    item.SetEnd(xy(pcbnew, *b))
    item.SetWidth(mk(width))
    item.SetLayer(layer)
    item.SetNet(net)
    board.Add(item)
    return True


def _add_via(pcbnew, board, net, x: float, y: float) -> bool:
    if _via_exists(pcbnew, board, net.GetNetname(), x, y):
        return False
    item = pcbnew.PCB_VIA(board)
    item.SetPosition(xy(pcbnew, x, y))
    item.SetWidth(mk(VIA_SIZE))
    item.SetDrill(mk(VIA_DRILL))
    item.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    item.SetNet(net)
    board.Add(item)
    return True


def _finish_pzt_signal_entries(pcbnew, board) -> tuple[int, int]:
    added_tracks = 0
    added_vias = 0
    for net_name, x, pad_y, b_stub_y, via_y in PZT_SIGNAL_ENTRIES:
        net = board.FindNet(net_name)
        if net is None:
            print(f"警告: 找不到网络 {net_name}，跳过")
            continue
        if _add_via(pcbnew, board, net, x, via_y):
            added_vias += 1
        if _add_track(pcbnew, board, net, pcbnew.F_Cu, (x, pad_y), (x, via_y), SIGNAL_TRACK_WIDTH):
            added_tracks += 1
        if _add_track(pcbnew, board, net, pcbnew.B_Cu, (x, b_stub_y), (x, via_y), SIGNAL_TRACK_WIDTH):
            added_tracks += 1
    return added_tracks, added_vias


def _remove_generated_gnd_zone(board) -> int:
    removed = 0
    for zone in list(board.Zones()):
        if zone.GetZoneName() == ZONE_NAME:
            board.Remove(zone)
            removed += 1
    return removed


def _add_bcu_gnd_zone(pcbnew, board) -> None:
    net = board.FindNet("gnd")
    if net is None:
        raise RuntimeError("找不到 gnd 网络，无法创建 B.Cu GND 铺铜")

    zone = pcbnew.ZONE(board)
    zone.SetLayer(pcbnew.B_Cu)
    layer_set = pcbnew.LSET()
    layer_set.AddLayer(pcbnew.B_Cu)
    zone.SetLayerSet(layer_set)
    zone.SetNet(net)
    zone.SetZoneName(ZONE_NAME)
    zone.SetAssignedPriority(1)
    zone.SetLocalClearance(mk(0.25))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)

    for x, y in PCB_SLOT_POINTS[:-1]:
        zone.AppendCorner(xy(pcbnew, x, y), -1)

    board.Add(zone)
    zone.SetFillFlag(pcbnew.B_Cu, True)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 4.3: PZT bridge electrical finish + B.Cu GND pour")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    added_tracks, added_vias = _finish_pzt_signal_entries(pcbnew, board)
    removed_zones = _remove_generated_gnd_zone(board)
    _add_bcu_gnd_zone(pcbnew, board)
    save_board(board, args.board)

    print("=== Step 4.3 完成 ===")
    print(f"PZT TL/TR signal 补线: 新增 {added_tracks} 段走线、{added_vias} 个过孔")
    print(f"B.Cu GND zone: 删除旧 {removed_zones} 个，重新生成 1 个 solid GND 铺铜")


if __name__ == "__main__":
    main()
