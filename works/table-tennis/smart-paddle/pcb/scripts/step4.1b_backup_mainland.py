#!/usr/bin/env python3
"""Step 4.1b — Backup mainland (大陆) component positions to a JSON snapshot.

Run after manually arranging mainland parts (MCU/IMU/power/battery/LED…).
Restore later via step4.2b even after a full ato rebuild.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import load_board

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "mainland_snapshot.json"

MAINLAND_EXACT = frozenset({"mcu", "imu", "led_r_data", "led_c_supply"})
# bringup.* 测试点已从主板删除；历史 mainland_snapshot 仍可能含其坐标。
MAINLAND_PREFIXES = ("power.", "battery.", "pwr_led.")


# ===== 分区：方法/工具 =====

def _address(fp) -> str | None:
    if not fp.HasFieldByName("atopile_address"):
        return None
    return fp.GetFieldByName("atopile_address").GetText()


def _is_mainland(addr: str) -> bool:
    if addr in MAINLAND_EXACT:
        return True
    return addr.startswith(MAINLAND_PREFIXES)


# ===== 分区：公开 API =====

def main() -> None:
    import pcbnew

    board = load_board(pcbnew, DEFAULT_BOARD)

    entries = []
    for fp in board.GetFootprints():
        addr = _address(fp)
        if not addr or not _is_mainland(addr):
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
    print(f"4.1b — 已备份 {len(entries)} 个大陆组件位置 → {SNAPSHOT}")


if __name__ == "__main__":
    main()
