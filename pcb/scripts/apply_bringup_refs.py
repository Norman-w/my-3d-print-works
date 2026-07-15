#!/usr/bin/env python3
"""Apply SW_/TP_ readable refs + snapshot positions only (no net/track edits).

- 宽栈道：SW_BOOT / SW_EN ← corridor_snapshot
- 大陆：TP_3V3 / TP_SYS_5V_SW ← mainland_snapshot
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[2]
CORRIDOR_SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "corridor_snapshot.json"
MAINLAND_SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "mainland_snapshot.json"
READABLE = {
    "debug_sw.sw_boot": ("SW_BOOT", "4.5x4.5"),
    "debug_sw.sw_en": ("SW_EN", "4.5x4.5"),
    "bringup.vcc_pad": ("TP_3V3", "3V3"),
    "bringup.sys5_pad": ("TP_SYS_5V_SW", "SYS_5V_SW"),
}


# ===== 分区：私有成员 =====
def _load_snap(path: Path) -> dict:
    if not path.is_file():
        return {}
    return {e["addr"]: e for e in json.loads(path.read_text(encoding="utf-8"))}


# ===== 分区：公开 API =====
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", type=Path, required=True)
    args = ap.parse_args()
    board_path = args.board.resolve()
    import pcbnew

    board = pcbnew.LoadBoard(str(board_path))
    if board is None:
        print("LoadBoard failed", board_path)
        return 2
    snap = {}
    snap.update(_load_snap(MAINLAND_SNAPSHOT))
    snap.update(_load_snap(CORRIDOR_SNAPSHOT))  # SW 覆盖同名时以栈道为准
    for fp in list(board.GetFootprints()):
        addr = None
        try:
            if fp.HasFieldByName("atopile_address"):
                addr = fp.GetFieldByName("atopile_address").GetText()
        except Exception:
            continue
        if not addr:
            continue
        if addr in snap:
            e = snap[addr]
            fp.SetPosition(
                pcbnew.VECTOR2I(pcbnew.FromMM(float(e["x"])), pcbnew.FromMM(float(e["y"])))
            )
            fp.SetOrientation(pcbnew.EDA_ANGLE(float(e.get("rot", 0)), pcbnew.DEGREES_T))
        if addr in READABLE:
            fp.SetReference(READABLE[addr][0])
            fp.SetValue(READABLE[addr][1])
    bad = [fp.GetReference() for fp in board.GetFootprints() if fp.GetReference() in ("REF**", "")]
    board.Save(str(board_path))
    print(f"applied bringup refs/pos → {board_path}; REF**= {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
