#!/usr/bin/env python3
"""Step 4.2b — Restore mainland footprints from the step 4.1b snapshot."""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import load_board, save_board, xy

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "mainland_snapshot.json"


# ===== 分区：方法/工具 =====

def _address(fp) -> str | None:
    if not fp.HasFieldByName("atopile_address"):
        return None
    return fp.GetFieldByName("atopile_address").GetText()


# ===== 分区：公开 API =====

def main() -> None:
    import pcbnew

    if not SNAPSHOT.exists():
        raise SystemExit(f"缺少大陆位置快照: {SNAPSHOT}")

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
    print(f"4.2b — 从快照原样恢复了 {restored} 个大陆组件")
    if missing:
        print(f"警告: 当前板缺少 {len(missing)} 个快照组件: {', '.join(missing)}")


if __name__ == "__main__":
    main()
