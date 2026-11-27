#!/usr/bin/env python3
# ===== 分区：导入/依赖 =====
"""Step 4.1d — 备份尾插（正反 MX1.25 5P）位置到 JSON。

含 flip / 层信息，供 step4 或 step4.2d 在 ato 重建后恢复。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import load_board

# ===== 分区：常量/配置 =====

DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "tail_snapshot.json"
TAIL_PREFIXES = ("tail.",)


# ===== 分区：私有成员 =====


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
        if not addr or not addr.startswith("tail."):
            continue
        pos = fp.GetPosition()
        entries.append({
            "addr": addr,
            "ref": fp.GetReference(),
            "x": round(pos.x / 1_000_000, 4),
            "y": round(pos.y / 1_000_000, 4),
            "rot": round(fp.GetOrientationDegrees(), 2),
            "flip": bool(fp.IsFlipped()) if hasattr(fp, "IsFlipped") else False,
        })

    entries.sort(key=lambda e: e["addr"])
    SNAPSHOT.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"4.1d — 已备份 {len(entries)} 个尾插位置 → {SNAPSHOT}")


if __name__ == "__main__":
    main()
