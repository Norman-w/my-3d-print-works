#!/usr/bin/env python3
"""Step 4.2a - restore the exact PZT bridge copper saved by step 4.1a."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import load_board, save_board, xy

DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "dock_routes_snapshot.json"


def main() -> None:
    import pcbnew

    if not SNAPSHOT.exists():
        raise SystemExit(f"缺少码头走线快照: {SNAPSHOT}")
    entries = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    board = load_board(pcbnew, DEFAULT_BOARD)
    restored_tracks = restored_vias = 0
    existing_tracks = {
        (
            item.GetNetname(), item.GetLayerName(),
            item.GetStart().x, item.GetStart().y, item.GetEnd().x, item.GetEnd().y,
            item.GetWidth(),
        )
        for item in board.GetTracks()
        if not isinstance(item, pcbnew.PCB_VIA)
    }
    existing_vias = {
        (item.GetNetname(), item.GetPosition().x, item.GetPosition().y,
         item.GetWidth(), item.GetDrillValue())
        for item in board.GetTracks()
        if isinstance(item, pcbnew.PCB_VIA)
    }

    for entry in entries:
        net = board.FindNet(entry["net"])
        if net is None:
            print(f"警告: 跳过不存在的网络 {entry['net']}")
            continue
        if entry["kind"] == "via":
            signature = (
                entry["net"], int(round(entry["x"] * 1e6)), int(round(entry["y"] * 1e6)),
                int(round(entry["size"] * 1e6)), int(round(entry["drill"] * 1e6)),
            )
            if signature in existing_vias:
                continue
            item = pcbnew.PCB_VIA(board)
            item.SetPosition(xy(pcbnew, entry["x"], entry["y"]))
            item.SetWidth(int(round(entry["size"] * 1e6)))
            item.SetDrill(int(round(entry["drill"] * 1e6)))
            item.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            restored_vias += 1
        else:
            x1, y1 = int(round(entry["x1"] * 1e6)), int(round(entry["y1"] * 1e6))
            x2, y2 = int(round(entry["x2"] * 1e6)), int(round(entry["y2"] * 1e6))
            signature = (
                entry["net"], entry["layer"], x1, y1, x2, y2,
                int(round(entry["width"] * 1e6)),
            )
            reverse = (signature[0], signature[1], x2, y2, x1, y1, signature[6])
            if signature in existing_tracks or reverse in existing_tracks:
                continue
            item = pcbnew.PCB_TRACK(board)
            item.SetStart(xy(pcbnew, entry["x1"], entry["y1"]))
            item.SetEnd(xy(pcbnew, entry["x2"], entry["y2"]))
            item.SetWidth(int(round(entry["width"] * 1e6)))
            item.SetLayer(board.GetLayerID(entry["layer"]))
            restored_tracks += 1
        item.SetNet(net)
        board.Add(item)

    save_board(board, DEFAULT_BOARD)
    print(f"4.2a - 已恢复码头至大陆走线 {restored_tracks} 段、过孔 {restored_vias} 个")


if __name__ == "__main__":
    main()
