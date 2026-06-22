#!/usr/bin/env python3
"""Step 4.1a - back up manually routed copper in the four PZT bridge corridors."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board
from rigid_pcb.tools.mech_geometry import MAINLAND_RECT, PZT_CAVITIES_SCAD, slot_scad_to_kicad

DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"
SNAPSHOT = ROOT / "rigid_pcb" / "layouts" / "default" / "dock_routes_snapshot.json"
CORRIDOR_HALF_WIDTH = 4.0
PZT_NET_PREFIX = "pzt_"


def _distance_to_segment(point, start, end) -> float:
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _in_bridge_corridor(x: float, y: float) -> bool:
    mainland = (MAINLAND_RECT[0], MAINLAND_RECT[1])
    for sx, sy, _radius in PZT_CAVITIES_SCAD:
        cavity = slot_scad_to_kicad((sx, sy))
        if _distance_to_segment((x, y), mainland, cavity) <= CORRIDOR_HALF_WIDTH:
            return True
    return False


def main() -> None:
    import pcbnew

    board = load_board(pcbnew, DEFAULT_BOARD)
    entries = []
    for item in board.GetTracks():
        net_name = item.GetNetname()
        if not (net_name.startswith(PZT_NET_PREFIX) or net_name in {"gnd", "vcc"}):
            continue
        if isinstance(item, pcbnew.PCB_VIA):
            pos = item.GetPosition()
            x, y = pos.x / 1e6, pos.y / 1e6
            if _in_bridge_corridor(x, y):
                entries.append({
                    "kind": "via", "x": x, "y": y,
                    "size": item.GetWidth() / 1e6, "drill": item.GetDrillValue() / 1e6,
                    "net": net_name,
                })
            continue

        start, end = item.GetStart(), item.GetEnd()
        midpoint = ((start.x + end.x) / 2e6, (start.y + end.y) / 2e6)
        if not _in_bridge_corridor(*midpoint):
            continue
        entries.append({
            "kind": "track",
            "x1": start.x / 1e6, "y1": start.y / 1e6,
            "x2": end.x / 1e6, "y2": end.y / 1e6,
            "width": item.GetWidth() / 1e6,
            "layer": item.GetLayerName(), "net": net_name,
        })

    SNAPSHOT.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tracks = sum(entry["kind"] == "track" for entry in entries)
    vias = len(entries) - tracks
    print(f"4.1a - 已备份码头至大陆走线 {tracks} 段、过孔 {vias} 个 -> {SNAPSHOT}")


if __name__ == "__main__":
    main()
