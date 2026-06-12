#!/usr/bin/env python3
"""Normalize generated KiCad footprints so atopile can decode the PCB.

Older scripts created board-only footprints with an empty library ID and without
a footprint attr. KiCad can open those, but atopile's KiCad decoder expects the
attr field. This keeps placement and pads unchanged while filling metadata.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, save_board


DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"


def safe_id(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_+.-]+", "_", text.strip())
    return text or "Generated"


def infer_attr(pcbnew, fp) -> int:
    for pad in fp.Pads():
        if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            return pcbnew.FP_THROUGH_HOLE
    return pcbnew.FP_SMD


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    changed = 0

    for fp in board.GetFootprints():
        ref = fp.GetReference() or "Generated"

        if not fp.GetFPIDAsString():
            fp.SetFPIDAsString(f"SmartPaddle:{safe_id(ref)}")
            changed += 1

        if fp.GetAttributes() == 0:
            fp.SetAttributes(infer_attr(pcbnew, fp))
            changed += 1

    save_board(board, args.board)
    print(f"normalized {changed} footprint metadata fields")


if __name__ == "__main__":
    main()
