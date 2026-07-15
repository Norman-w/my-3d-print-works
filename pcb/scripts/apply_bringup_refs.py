#!/usr/bin/env python3
"""Apply SW_/TP_ readable refs + corridor_snapshot positions only (no net/track edits)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "corridor_snapshot.json"
READABLE = {
    "debug_sw.sw_boot": ("SW_BOOT", "4.5x4.5"),
    "debug_sw.sw_en": ("SW_EN", "4.5x4.5"),
    "bringup.gnd_pad": ("TP_GND", "GND"),
    "bringup.vcc_pad": ("TP_3V3", "3V3"),
    "bringup.vbat_pad": ("TP_VBAT", "VBAT_SW"),
    "bringup.tp_mcu_boot": ("TP_MCU_BOOT", "BOOT"),
    "bringup.tp_mcu_en": ("TP_MCU_EN", "EN"),
}


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
    snap = {e["addr"]: e for e in json.loads(SNAPSHOT.read_text())}
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
