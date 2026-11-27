#!/usr/bin/env python3
"""Refill all copper zones on a KiCad PCB file."""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_BOARD = Path(__file__).resolve().parents[1] / "layouts" / "default" / "default.kicad_pcb"


def main() -> None:
    parser = argparse.ArgumentParser(description="Refill all KiCad copper zones")
    parser.add_argument("board", nargs="?", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = pcbnew.LoadBoard(str(args.board))
    if board is None:
        raise RuntimeError(f"Unable to load KiCad board: {args.board}")

    zones = board.Zones()
    pcbnew.ZONE_FILLER(board).Fill(zones)
    board.Save(str(args.board))
    print(f"refilled {len(list(zones))} zone(s): {args.board}")


if __name__ == "__main__":
    main()
