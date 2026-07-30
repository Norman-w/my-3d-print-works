#!/usr/bin/env python3
"""Restore C4 assembly metadata after ``ato build`` without placing parts.

Atopile 0.12.5 preserves the footprint positions in the checked-in board, but
its KiCad update pass can reset human-readable values and a few custom
references.  This post-netlist step restores only metadata needed for manual
placement and assembly.  Footprint position, rotation, side, routing, and zones
must remain unchanged.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "pcb" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from migrate_c3_to_c4_unrouted import DNP_ADDRESSES, EXPECTED_C4_COMPONENTS
from step4_ato_placement import (
    BOARD_FILE,
    _address,
    _apply_model_scales,
    _apply_readable_text,
    _move_embedded_body_silk_to_fab,
    _readable_ref,
)

LOCAL_PRETTY = ROOT / "pcb" / "layouts" / "lib" / "footprints.pretty"
TAIL_FOOTPRINT = "Molex_PicoBlade_53261-0571_1x05-1MP_P1.25mm_Horizontal"
C4_TITLE = "SmartPaddle Rigid PCB"
C4_REVISION = "C4"
C4_COMPANY = "SmartPaddle"
C4_DATE = "2026-07-29"


def _placement_state(footprint) -> tuple[int, int, float, int]:
    position = footprint.GetPosition()
    return (
        position.x,
        position.y,
        footprint.GetOrientationDegrees(),
        footprint.GetLayer(),
    )


def _set_address(footprint, address: str) -> None:
    if footprint.HasFieldByName("atopile_address"):
        footprint.GetFieldByName("atopile_address").SetText(address)
    else:
        footprint.SetField("atopile_address", address)


def _repair_back_tail_footprint(board, pcbnew, old):
    """Undo atopile 0.12.5's inverted internal geometry on the back connector.

    The footprint origin, board side, and final orientation are preserved.  A
    fresh project-library instance is flipped only after being attached to the
    board, which is the KiCad 9-safe sequence also used by apply_tail_mx125.py.
    """
    position = old.GetPosition()
    desired_orientation = old.GetOrientationDegrees()
    pad_nets = {}
    for pad in old.Pads():
        pad_nets.setdefault(pad.GetNumber(), pad.GetNet())

    io = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    fresh = io.FootprintLoad(str(LOCAL_PRETTY), TAIL_FOOTPRINT)
    if fresh is None:
        raise RuntimeError(
            f"cannot load {LOCAL_PRETTY}:{TAIL_FOOTPRINT}"
        )
    fresh.SetParent(board)
    fresh.SetPosition(position)
    # FLIP_DIRECTION_LEFT_RIGHT maps a front-side angle A to 180-A.
    fresh.SetOrientationDegrees((180.0 - desired_orientation) % 360.0)
    fresh.SetReference("TAIL_MX125_B")
    fresh.SetValue("MX1.25-5P")
    fresh.SetFPIDAsString(f"SmartPaddle:{TAIL_FOOTPRINT}")
    _set_address(fresh, "tail.conn_b")
    board.Add(fresh)
    fresh.Flip(position, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    for pad in fresh.Pads():
        if (net := pad_nets.get(pad.GetNumber())) is not None:
            pad.SetNet(net)
    board.Remove(old)
    return fresh


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Step 3.2 metadata finalizer (never places components)"
    )
    parser.add_argument("--board", type=Path, default=BOARD_FILE)
    parser.add_argument("--metadata-pass", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--expected-tail-state", nargs=4, metavar=("X", "Y", "ROT", "LAYER"),
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    import pcbnew

    board_path = args.board.resolve()
    board = pcbnew.LoadBoard(str(board_path))
    if board is None:
        raise RuntimeError(f"cannot load board: {board_path}")

    addressed = {
        address: footprint
        for footprint in board.GetFootprints()
        if (address := _address(footprint))
    }
    missing_metadata = sorted(
        address for address in addressed if _readable_ref(address) is None
    )
    if len(addressed) != EXPECTED_C4_COMPONENTS or missing_metadata:
        raise RuntimeError(
            "refusing partial C4 metadata update: "
            f"addresses={len(addressed)}, missing={missing_metadata}"
        )

    before = {
        address: _placement_state(footprint)
        for address, footprint in addressed.items()
    }

    if not args.metadata_pass:
        expected_tail = before["tail.conn_b"]
        addressed["tail.conn_b"] = _repair_back_tail_footprint(
            board, pcbnew, addressed["tail.conn_b"]
        )
        board.Save(str(board_path))
        return subprocess.call(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--board",
                str(board_path),
                "--metadata-pass",
                "--expected-tail-state",
                *(str(value) for value in expected_tail),
            ]
        )

    if args.expected_tail_state is None:
        raise RuntimeError("internal metadata pass is missing expected tail state")
    expected_tail_state = (
        int(args.expected_tail_state[0]),
        int(args.expected_tail_state[1]),
        float(args.expected_tail_state[2]),
        int(args.expected_tail_state[3]),
    )
    actual_tail_state = _placement_state(addressed["tail.conn_b"])
    if actual_tail_state != expected_tail_state:
        raise RuntimeError(
            "back-tail repair changed component placement: "
            f"expected={expected_tail_state}, actual={actual_tail_state}"
        )

    labelled, visible = _apply_readable_text(board, addressed.values())
    moved_silk = _move_embedded_body_silk_to_fab(addressed)
    scaled_models = _apply_model_scales(board, addressed.values())
    for address in DNP_ADDRESSES:
        addressed[address].SetDNP(True)

    title_block = board.GetTitleBlock()
    title_block.SetTitle(C4_TITLE)
    title_block.SetRevision(C4_REVISION)
    title_block.SetCompany(C4_COMPANY)
    title_block.SetDate(C4_DATE)

    after = {
        address: _placement_state(footprint)
        for address, footprint in addressed.items()
    }
    changed_placements = sorted(
        address for address in before if before[address] != after[address]
    )
    if changed_placements:
        raise RuntimeError(
            "metadata pass changed component placement: "
            f"{changed_placements}"
        )

    board.Save(str(board_path))
    print(
        "Step 3.2 metadata OK: "
        f"{len(addressed)} components, {labelled} readable fields, "
        f"{visible} visible refs, {len(DNP_ADDRESSES)} DNP, "
        f"back-tail geometry repaired, {moved_silk} silk items moved to Fab, "
        f"{scaled_models} model scales; "
        f"title={C4_TITLE!r} rev={C4_REVISION}; 0 component placements changed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
