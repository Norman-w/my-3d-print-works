#!/usr/bin/env python3
"""Step 4.2 — Restore PZT dock component positions from the snapshot file.

Reads dock_snapshot.json (created by step4.1) and places every listed
footprint at its recorded position.  If no snapshot exists the script
prints a warning and exits without modifying the board.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, save_board, xy

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"
SNAPSHOT = ROOT / "rigid_pcb" / "layouts" / "default" / "dock_snapshot.json"


# ===== 分区：方法/工具 =====

def _address(fp) -> str | None:
    if not fp.HasFieldByName("atopile_address"):
        return None
    return fp.GetFieldByName("atopile_address").GetText()


# ===== 分区：公开 API =====

def main() -> None:
    import pcbnew

    if not SNAPSHOT.exists():
        print(f"4.2 — 未找到 {SNAPSHOT.name}，请先运行 step4.1 备份码头位置")
        sys.exit(1)

    board = load_board(pcbnew, DEFAULT_BOARD)
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    lookup = {e["addr"]: e for e in data}
    fp_by_addr = {addr: fp for fp in board.GetFootprints() if (addr := _address(fp))}

    moved = 0
    for addr, entry in lookup.items():
        fp = fp_by_addr.get(addr)
        if fp is None:
            continue
        fp.SetPosition(xy(pcbnew, entry["x"], entry["y"]))
        fp.SetOrientationDegrees(entry["rot"])
        moved += 1

    save_board(board, DEFAULT_BOARD)
    print(f"4.2 — 从 {SNAPSHOT.name} 恢复了 {moved} 个 PZT 码头组件位置")


if __name__ == "__main__":
    main()
