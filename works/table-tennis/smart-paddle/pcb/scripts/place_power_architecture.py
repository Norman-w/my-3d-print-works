#!/usr/bin/env python3
"""Place the route-free main-board power, USB and PZT-frontend support parts.

This is deliberately a placement-only step.  It refuses any board containing
tracks, vias or zones, moves only the named footprints below, and verifies that
all other footprint poses are byte-for-byte unchanged.  The coordinates keep
the TPS62162 input capacitor, converter, XFL3012 inductor and output capacitor
in power-flow order; move the ESP32 supply/EN capacitors next to their module
pins; park USB 22 ohm resistors next to the USB pads; and park the DAC,
I2C pullups and bypass caps on IMU +X because this board does not use
Bluetooth, so both IMU X sides are legal placement area.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

try:
    import pcbnew
except ImportError as exc:  # pragma: no cover - KiCad runtime only
    raise SystemExit(
        "pcbnew is unavailable; run with KiCad 9's bundled Python"
    ) from exc


# ===== 分区：常量/配置 =====
REPO = Path(__file__).resolve().parents[2]
DEFAULT_BOARD = REPO / "pcb/layouts/default/default.kicad_pcb"


@dataclass(frozen=True)
class Pose:
    x_mm: float
    y_mm: float
    rotation_deg: float


# Only these references are intentionally moved.  Existing connectors,
# sensors, the comparator body, PZT docks and switches remain untouched.
# PZT frontend lives on IMU +X.  DAC sits toward the blade head so
# TR/TL VREF match the TLV9034 south row without wrapping the TSSOP.
PLACEMENTS = {
    # PMIC block: CIN -> TPS62162 -> L -> COUT, all on F.Cu.
    "PW_C_IN_10U": Pose(-19.00, -20.70, 90.0),
    "PW_BUCK_3V3": Pose(-16.30, -19.50, 0.0),
    "PW_L_BUCK_2U2": Pose(-12.55, -19.50, 0.0),
    "PW_C_OUT_22U": Pose(-10.80, -23.65, 90.0),
    # Isolated button reader at the bottom of the existing latch cluster.
    "PW_R_BTN_RAW_PU_100K": Pose(-18.80, -28.66, 90.0),
    "PW_Q_BTN_SENSE": Pose(-11.40, -28.50, 90.0),
    "PW_R_BTN_GPIO_PU_100K": Pose(-11.40, -32.20, 0.0),
    # ESP32 bulk/decap stay above pins 2/3.  EN RC sits on the EN pad row.
    "MCU_C_BULK_10U": Pose(-12.00, 10.40, 0.0),
    "MCU_C_DEC_100N": Pose(-8.80, 10.40, 0.0),
    "MCU_C_EN_1U": Pose(-5.70, 10.50, -90.0),
    "PW_R_EN_PU_10K": Pose(-3.90, 10.50, -90.0),
    # Power indicator is non-critical; park it in the clear left column.
    "LED_MCU_PWR": Pose(-19.40, -12.80, 0.0),
    "R_MCU_PWR_1K": Pose(-19.40, -15.00, 90.0),
    # USB 22R beside the MCU USB pads.  90° puts pad 2 (PHY) toward the MCU.
    "USB_R_DN_22R": Pose(7.00, 10.60, 90.0),
    "USB_R_DP_22R": Pose(8.50, 10.60, 90.0),
    # No Bluetooth: IMU ±X are both legal.  PZT frontend sits on IMU +X.
    # TLV9034 keeps -90° so TL/TR stay on the head-side row.  Bypass is
    # south of pin 3.  DAC sits further south with VOUT west toward the
    # comparator so TR/TL VREF do not wrap around the TSSOP.
    "PZT_CMP_TLV9034": Pose(14.00, -18.80, -90.0),
    "PZT_C_CMP_100N": Pose(15.20, -24.00, 90.0),
    "PZT_DAC_MCP4728": Pose(17.40, -28.50, 0.0),
    "PZT_C_DAC_100N": Pose(19.50, -29.00, 90.0),
    "PZT_R_SCL_PU_4K7": Pose(19.50, -26.80, 90.0),
    "PZT_R_SDA_PU_4K7": Pose(19.50, -25.50, 90.0),
}

PLACEMENT_VALUES = {
    "MCU_C_BULK_10U": "10uF 6.3V X5R/X7R",
    "MCU_C_DEC_100N": "100nF 10V X7R",
    "MCU_C_EN_1U": "1uF 10V X5R/X7R",
}


# ===== 分区：私有成员 =====
class PlacementError(RuntimeError):
    pass


def _pose(fp: "pcbnew.FOOTPRINT") -> tuple[int, int, float, int]:
    pos = fp.GetPosition()
    return pos.x, pos.y, fp.GetOrientationDegrees(), fp.GetLayer()


def _hide_nonassembly_fields(fp: "pcbnew.FOOTPRINT") -> None:
    for name in ("Reference", "Value", "atopile_address"):
        if fp.HasFieldByName(name):
            field = fp.GetFieldByName(name)
            field.SetVisible(False)
            if name == "atopile_address":
                field.SetLayer(pcbnew.User_9)


def _save_detached(board: "pcbnew.BOARD", destination: Path) -> None:
    """Save away from the live .kicad_pro, then atomically replace the PCB."""
    scratch = Path(tempfile.mkdtemp(prefix="smartpaddle-main-place-"))
    try:
        detached = scratch / f"main-{uuid.uuid4().hex}.kicad_pcb"
        pcbnew.SaveBoard(str(detached), board)
        verify = pcbnew.LoadBoard(str(detached))
        if verify is None or len(list(verify.GetFootprints())) != 67:
            raise PlacementError("detached saved-board verification failed")
        if list(verify.GetTracks()) or verify.GetAreaCount():
            raise PlacementError("placement unexpectedly created copper")
        temporary = destination.with_name(
            f".{destination.stem}.{uuid.uuid4().hex}.placement.tmp.kicad_pcb"
        )
        shutil.copy2(detached, temporary)
        os.replace(temporary, destination)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ===== 分区：公开 API =====
def place(board_path: Path) -> None:
    if not board_path.is_file():
        raise PlacementError(f"board not found: {board_path}")
    board = pcbnew.LoadBoard(str(board_path))
    footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
    if len(footprints) != 67:
        raise PlacementError(f"expected 67 unique footprints, got {len(footprints)}")
    missing = set(PLACEMENTS) - set(footprints)
    if missing:
        raise PlacementError(f"missing placement targets: {sorted(missing)}")
    if list(board.GetTracks()) or board.GetAreaCount():
        raise PlacementError("board must contain 0 tracks/vias and 0 zones")

    untouched = {
        reference: _pose(fp)
        for reference, fp in footprints.items()
        if reference not in PLACEMENTS
    }
    for reference, wanted in PLACEMENTS.items():
        fp = footprints[reference]
        if fp.GetLayer() != pcbnew.F_Cu:
            raise PlacementError(f"{reference} must remain on F.Cu")
        fp.SetPosition(pcbnew.VECTOR2I_MM(wanted.x_mm, wanted.y_mm))
        fp.SetOrientationDegrees(wanted.rotation_deg)
        if reference in PLACEMENT_VALUES:
            fp.SetValue(PLACEMENT_VALUES[reference])
        _hide_nonassembly_fields(fp)

    for reference, before in untouched.items():
        after = _pose(footprints[reference])
        if after != before:
            raise PlacementError(f"unapproved pose change: {reference}: {before} -> {after}")

    _save_detached(board, board_path)
    print("Main-board placement PASS")
    print("  buck power loop placed in physical current-flow order")
    print("  ESP32 supply/EN support moved next to module pins")
    print("  isolated button reader and USB 22R resistors placed")
    print("  PZT frontend parked on IMU +X with DAC toward the blade head")
    print("  every other footprint pose preserved")
    print("  67 footprints; 0 tracks/vias; 0 zones")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()
    try:
        place(args.board.resolve())
    except PlacementError as exc:
        print(f"PLACEMENT FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
