"""Fill KiCad zones for the generated SmartPaddle PCB.

KiCad 9's ZONE_FILLER requires a wxApp.  Running this as a separate
post-process keeps generate_kicad.py stable in KiCad's embedded Python.
"""

import sys
from pathlib import Path

import wx

app = wx.App(False)

import pcbnew  # noqa: E402


def main() -> None:
    if len(sys.argv) > 1:
        board_path = Path(sys.argv[1])
    else:
        board_path = Path(__file__).resolve().parent / "layouts" / "default" / "default.kicad_pcb"

    board = pcbnew.LoadBoard(str(board_path))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(str(board_path))
    print(f"Filled zones: {board_path}")


if __name__ == "__main__":
    main()
