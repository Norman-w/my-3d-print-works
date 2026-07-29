#!/usr/bin/env python3
"""Validate only the safety and mechanical contract of the reference board."""

from __future__ import annotations

from pathlib import Path

import wx

WX_APP = wx.App(False)

import pcbnew  # noqa: E402
from layout_spec import (  # noqa: E402
    MIN_BODY_CLEARANCE_MM,
    PLACEMENTS,
    body_bounds,
    top_side_collisions,
)


HERE = Path(__file__).resolve().parent
BOARD_PATH = HERE / "lx-lbc3-reference-tbd.kicad_pcb"
EXPECTED_REFS = {
    "J1",
    "J2",
    "J3",
    "J4",
    "J5",
    "R1",
    "R2",
    "R3",
    "C1",
    "R4",
    "C3",
    "L1",
    "U1",
    "D1",
    "D2",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> int:
    require(BOARD_PATH.is_file(), f"missing board: {BOARD_PATH}")
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    footprints = {str(fp.GetReference()): fp for fp in board.GetFootprints()}
    require(set(footprints) == EXPECTED_REFS, "unexpected component inventory")

    named_nets = [str(name) for name in board.GetNetInfo().NetsByName().keys() if str(name)]
    require(not named_nets, f"reference board contains named nets: {named_nets}")
    require(len(list(board.GetTracks())) == 0, "reference board contains tracks/vias")
    require(board.GetAreaCount() == 0, "reference board contains copper zones")

    box = board.GetBoardEdgesBoundingBox()
    width = pcbnew.ToMM(box.GetWidth())
    height = pcbnew.ToMM(box.GetHeight())
    # KiCad's edge bounding box includes half the 0.05 mm Edge.Cuts stroke on
    # both sides, so the measured box is 0.05 mm larger than the centerline.
    require(abs(width - 16.0) < 0.06, f"board width is {width:.3f} mm, expected 16 mm")
    require(abs(height - 12.0) < 0.06, f"board height is {height:.3f} mm, expected 12 mm")

    j1_numbered = [pad for pad in footprints["J1"].Pads() if str(pad.GetNumber()).isdigit()]
    require(len(j1_numbered) == 6, "J1 must expose exactly six TBD electrical pads")
    require(len(list(footprints["U1"].Pads())) == 6, "U1 placeholder must remain six-pad SOT-23-6")
    require(footprints["J2"].IsFlipped() and footprints["J3"].IsFlipped(), "5V pads must remain on bottom")
    require(not footprints["J4"].IsFlipped() and not footprints["J5"].IsFlipped(), "B pads must remain on top")

    collisions = top_side_collisions()
    require(
        not collisions,
        f"visible component envelopes overlap at {MIN_BODY_CLEARANCE_MM:.2f} mm clearance: {collisions}",
    )
    for ref, placement in PLACEMENTS.items():
        fp = footprints[ref]
        x_mm = pcbnew.ToMM(fp.GetPosition().x) - 100.0
        y_mm = pcbnew.ToMM(fp.GetPosition().y) - 100.0
        require(
            abs(x_mm - placement.x) < 0.01 and abs(y_mm - placement.y) < 0.01,
            f"{ref} no longer matches the photo-calibrated placement",
        )
        if not placement.bottom:
            actual_rotation = float(fp.GetOrientationDegrees()) % 360.0
            expected_rotation = placement.rotation % 360.0
            rotation_delta = abs(actual_rotation - expected_rotation)
            rotation_delta = min(rotation_delta, 360.0 - rotation_delta)
            require(
                rotation_delta < 0.01,
                f"{ref} rotation is {actual_rotation:.2f} degrees, expected {expected_rotation:.2f}",
            )
        left, right, top, bottom = body_bounds(ref)
        if ref != "J1":
            require(
                right > 0 and left < 16 and bottom > 0 and top < 12,
                f"{ref} visible body is outside the 16x12 mm reference envelope",
            )

    for output in (
        HERE / "output" / "reference_top.svg",
        HERE / "output" / "reference_bottom.svg",
        HERE / "output" / "reference_3d_top.png",
        HERE / "output" / "reference_3d_iso.png",
        HERE / "output" / "photo_calibrated_layout.svg",
        HERE / "output" / "photo_calibrated_layout.png",
    ):
        require(output.is_file() and output.stat().st_size > 1024, f"missing/empty preview: {output}")

    print(
        "PASS: 16x12 mm photo-calibrated board; 15 footprints; J1=6P; "
        f"body_clearance>={MIN_BODY_CLEARANCE_MM:.2f}mm; named_nets=0 tracks=0 vias=0 zones=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
