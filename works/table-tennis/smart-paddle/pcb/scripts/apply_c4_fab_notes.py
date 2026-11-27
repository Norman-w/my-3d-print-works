#!/usr/bin/env python3
"""Apply or verify the C4 fabrication notes on ``Cmts.User``.

The notes sit outside the board outline and are intended for the fabrication
drawing, not for copper or silkscreen.  The update is idempotent and removes
only text owned by this script.  It never changes tracks, vias, zones,
footprints, pads, nets, or Edge.Cuts.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
OWNED_PREFIX = "C4 FAB"

HEADER = "C4 FABRICATION NOTES"
BODY = """C4 FAB NOTE 1: 0.8 mm / 2-layer / ENIG / single board.
C4 FAB NOTE 2: MCU and IMU INTERNAL ROUTED CUTOUTS intentionally cross PTH centers.
C4 FAB NOTE 3: Do not straighten or alter the outline; contact before any process change/upcharge.
C4 FAB NOTE 4: Prototype may use ordinary routing at internal PTH edges if castellations are unavailable.
C4 FAB NOTE 5: ESP32-S3 EP41 has no host land; assembly must ground perimeter pads 1 and 40.
C4 FAB NOTE 6: JP_ADC_TL/TR/BL/BR are DNP; tail connector map is the C4 MX1.25 map."""


def _owned_texts(board, pcbnew):
    return [
        drawing
        for drawing in board.GetDrawings()
        if drawing.GetLayer() == pcbnew.Cmts_User
        and drawing.GetClass() == "PCB_TEXT"
        and drawing.GetText().startswith(OWNED_PREFIX)
    ]


def _add_text(pcbnew, board, text: str, x: float, y: float, size: float) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetLayer(pcbnew.Cmts_User)
    item.SetText(text)
    item.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    item.SetTextHeight(pcbnew.FromMM(size))
    item.SetTextWidth(pcbnew.FromMM(size))
    item.SetTextThickness(pcbnew.FromMM(max(0.18, size * 0.12)))
    item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    item.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_TOP)
    board.Add(item)


def _validate(board, pcbnew) -> list[str]:
    errors: list[str] = []
    owned = _owned_texts(board, pcbnew)
    texts = {item.GetText() for item in owned}
    if texts != {HEADER, BODY}:
        errors.append(
            f"fab-note text set mismatch: expected 2 owned blocks, found {len(owned)}"
        )
    if list(board.GetTracks()):
        # Applying notes after routing is safe, but the C4 baseline verifier is
        # deliberately explicit about the current handoff state.
        print("warning: board already contains tracks/vias; notes remain non-copper")
    return errors


def apply(board_path: Path, *, check_only: bool) -> None:
    import pcbnew

    before_bytes = board_path.read_bytes()
    before_hash = hashlib.sha256(before_bytes).hexdigest()
    board = pcbnew.LoadBoard(str(board_path))
    if board is None:
        raise RuntimeError(f"cannot load board: {board_path}")

    if check_only:
        errors = _validate(board, pcbnew)
        after_hash = hashlib.sha256(board_path.read_bytes()).hexdigest()
        if after_hash != before_hash:
            raise RuntimeError("check-only unexpectedly changed the board file")
        if errors:
            raise RuntimeError("; ".join(errors))
        print(f"C4 fab notes OK: 2 Cmts.User blocks; board unchanged {before_hash}")
        return

    for item in _owned_texts(board, pcbnew):
        board.Remove(item)
    _add_text(pcbnew, board, HEADER, 46.0, -55.0, 1.8)
    _add_text(pcbnew, board, BODY, 46.0, -50.5, 1.15)
    board.Save(str(board_path))

    reloaded = pcbnew.LoadBoard(str(board_path))
    errors = _validate(reloaded, pcbnew)
    if errors:
        raise RuntimeError("; ".join(errors))
    print(f"C4 fab notes applied: {board_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        apply(args.board.resolve(), check_only=args.check_only)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
