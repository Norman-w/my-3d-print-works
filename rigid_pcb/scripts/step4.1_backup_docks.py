#!/usr/bin/env python3
"""Step 4.1 — Backup PZT dock component positions to a JSON snapshot.

Run after manually arranging dock components so their positions are archived.
The snapshot can be restored later via step4.2 even after a full ato rebuild.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board

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

    board = load_board(pcbnew, DEFAULT_BOARD)

    entries = []
    for fp in board.GetFootprints():
        addr = _address(fp)
        if not addr or not addr.startswith("pzt_"):
            continue
        pos = fp.GetPosition()
        entries.append({
            "addr": addr,
            "x": round(pos.x / 1_000_000, 4),
            "y": round(pos.y / 1_000_000, 4),
            "rot": round(fp.GetOrientationDegrees(), 2),
        })

    entries.sort(key=lambda e: e["addr"])
    SNAPSHOT.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"4.1 — 已备份 {len(entries)} 个 PZT 码头组件位置 → {SNAPSHOT}")


if __name__ == "__main__":
    main()
