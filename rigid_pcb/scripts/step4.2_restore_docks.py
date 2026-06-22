#!/usr/bin/env python3
"""Step 4.2 - restore PZT dock footprints exactly from the step 4.1 snapshot."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, save_board, xy

DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"
SNAPSHOT = ROOT / "rigid_pcb" / "layouts" / "default" / "dock_snapshot.json"


def _address(fp) -> str | None:
    if not fp.HasFieldByName("atopile_address"):
        return None
    return fp.GetFieldByName("atopile_address").GetText()


def main() -> None:
    import pcbnew

    if not SNAPSHOT.exists():
        raise SystemExit(f"缺少码头位置快照: {SNAPSHOT}")

    entries = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    board = load_board(pcbnew, DEFAULT_BOARD)
    footprints = {addr: fp for fp in board.GetFootprints() if (addr := _address(fp))}
    restored = 0
    missing = []

    for entry in entries:
        footprint = footprints.get(entry["addr"])
        if footprint is None:
            missing.append(entry["addr"])
            continue
        footprint.SetPosition(xy(pcbnew, float(entry["x"]), float(entry["y"])))
        footprint.SetOrientationDegrees(float(entry["rot"]))
        restored += 1

    save_board(board, DEFAULT_BOARD)
    print(f"4.2 - 从快照原样恢复了 {restored} 个 PZT 码头组件")
    if missing:
        print(f"警告: 当前板缺少 {len(missing)} 个快照组件: {', '.join(missing)}")


if __name__ == "__main__":
    main()
