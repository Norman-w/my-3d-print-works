#!/usr/bin/env python3
"""Place the route-free main-board power, USB and PZT-frontend support parts.

This is deliberately a placement-only step.  It refuses any board containing
tracks, vias or zones, moves only the named footprints below, and verifies that
all other footprint poses are byte-for-byte unchanged.  The coordinates keep
the TPS62162 input capacitor, converter, XFL3012 inductor and output capacitor
in power-flow order; move the ESP32 supply/EN capacitors next to their module
pins; park USB 22 ohm resistors east of the module so they do not plug the
MCU-to-analog corridor; and keep the DAC / I2C pullups / bypass caps off the
TLV9034 pin-escape channels.
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
# DAC shifts east so VREF/digital can use the CMP–DAC corridor;
# I2C pullups leave that corridor and sit on the DAC I2C/VDD side.
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
    # ESP32 bulk/decap stay above pins 2/3.  EN RC parks on the far +X
    # edge of the solid top strip so the TLV9034 south row can fan out.
    "MCU_C_BULK_10U": Pose(-12.00, 10.40, 0.0),
    "MCU_C_DEC_100N": Pose(-8.80, 10.40, 0.0),
    # East of the module, still in the solid top strip.  Leaving the
    # MCU-to-TLV9034 alley empty so the comparator south row can fan out.
    "MCU_C_EN_1U": Pose(19.00, 10.80, 90.0),
    "PW_R_EN_PU_10K": Pose(19.00, 13.97, 90.0),
    # Power indicator is non-critical; park it in the clear left column.
    "LED_MCU_PWR": Pose(-19.40, -12.80, 0.0),
    "R_MCU_PWR_1K": Pose(-19.40, -15.00, 90.0),
    # USB 22R east of the module but west of the right-wing inner cut.
    # 90° puts pad 2 (PHY) toward the MCU and pad 1 (connector) toward the tail.
    "USB_R_DN_22R": Pose(11.80, 11.00, 90.0),
    "USB_R_DP_22R": Pose(13.50, 11.00, 90.0),
    # TLV9034 stays at its C4 body pose; bypass sits west of the body so the
    # MCU-facing analog pin row can still arrive from -X.
    "PZT_C_CMP_100N": Pose(-7.70, 14.80, 180.0),
    # DAC VOUT stays facing the comparator; body shifts +X to open a ~3 mm
    # courtyard corridor.  Bypass and I2C pullups cluster on the VDD/I2C side.
    "PZT_DAC_MCP4728": Pose(5.80, 17.465, 0.0),
    "PZT_C_DAC_100N": Pose(10.70, 16.97, 0.0),
    "PZT_R_SCL_PU_4K7": Pose(10.70, 14.90, 180.0),
    "PZT_R_SDA_PU_4K7": Pose(10.70, 18.70, 180.0),
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
    print("  PZT DAC, I2C pullups and 100 nF caps placed for pin escape")
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
