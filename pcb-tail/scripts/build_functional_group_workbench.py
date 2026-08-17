#!/usr/bin/env python3
"""Build a non-fabrication tail-board functional-island workbench.

The workbench deliberately parks every footprint outside the production
Edge.Cuts, arranged in mutually exclusive functional groups.  It starts with
no copper or zones so each island can be optimized and routed independently.
The production board is never modified by this script.
"""

from __future__ import annotations

import argparse
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

try:
    import pcbnew
except ImportError as exc:  # pragma: no cover - KiCad runtime only
    raise SystemExit("run with KiCad 9's bundled Python") from exc


REPO = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO / "pcb-tail/layouts/default/default.kicad_pcb"
DEFAULT_OUTPUT = (
    REPO / "pcb-tail/layouts/functional-groups/functional-groups.kicad_pcb"
)


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    angle: float


@dataclass(frozen=True)
class Island:
    label: str
    refs: tuple[str, ...]
    bounds: tuple[float, float, float, float]


# These poses preserve the production-side assignment of every part.  Only the
# temporary X/Y/rotation changes.  The power island is pin-aware: U3/L1 BAT and
# SW pins face one another; C3/C4/C6 hot pads face their function node and their
# ground pads face U3's exposed ground pad.
POSES: dict[str, Pose] = {
    # G1 — USB-C / CC / ESD front end.
    "J1": Pose(-32.0, -27.0, -90.0),
    "U2": Pose(-27.45, -27.0, 0.0),
    "R1": Pose(-27.45, -29.90, 0.0),
    "R2": Pose(-36.0, -25.83, 180.0),
    # G2 — USB input limiter.
    "U5": Pose(22.0, -23.0, 0.0),
    "C10": Pose(18.88, -23.0, -90.0),
    "R9": Pose(25.12, -23.0, 90.0),
    # G3 — IP5305 high-current core.
    "U3": Pose(0.0, -28.0, 180.0),
    "L1": Pose(-6.30, -27.95, -90.0),
    "C3": Pose(-5.75, -24.35, 0.0),
    "C4": Pose(1.80, -32.05, 180.0),
    "C6": Pose(-2.55, -32.20, 0.0),
    "R7": Pose(1.75, -24.20, 180.0),
    "C5": Pose(-1.80, -23.95, 180.0),
    # G4 — system 5 V limiter.  C7 is the input-side secondary bulk cap.
    "U4": Pose(22.0, -39.0, 0.0),
    "C7": Pose(18.63, -39.0, -90.0),
    "C8": Pose(20.20, -41.77, 0.0),
    "C9": Pose(23.50, -41.77, 0.0),
    "R8": Pose(25.12, -39.0, 90.0),
    # G5 — PMIC key and status indication.
    "SW1": Pose(-28.0, 19.0, 0.0),
    "LED1": Pose(-26.23, 16.28, 0.0),
    "D2": Pose(-29.65, 16.06, 180.0),
    "R4": Pose(-29.65, 16.06, 180.0),
    "R5": Pose(-26.23, 16.28, 0.0),
    "R6": Pose(-28.0, 19.0, 0.0),
    # G6 — RGB level shifter and first pixel.
    "U1": Pose(-7.0, 19.0, 0.0),
    "R3": Pose(-3.88, 19.0, -90.0),
    "D1": Pose(-4.795, 19.275, 0.0),
    "C1": Pose(-7.0, 21.775, 180.0),
    "C2": Pose(-4.795, 21.595, 180.0),
    # G7/G8 — interface anchors; their nets intentionally remain cross-island.
    "J2": Pose(25.0, 20.0, -90.0),
    "J4": Pose(18.16, 20.0, 90.0),
    "J3": Pose(30.0, 0.0, 0.0),
}

# These decouplers deliberately change side so each one shares copper with the
# IC it serves.  Every other footprint keeps its production-side assignment.
LAYER_OVERRIDES = {
    "C7": pcbnew.F_Cu,
    "C1": pcbnew.B_Cu,
}


ISLANDS: dict[str, Island] = {
    "G1_USB_C_CC_ESD": Island(
        "G1  USB-C / CC / ESD", ("J1", "R1", "R2", "U2"), (-38.005, -23.700, -32.900, -21.100)
    ),
    "G2_USB_INPUT_LIMIT": Island(
        "G2  USB input limiter", ("U5", "R9", "C10"), (17.075, 26.375, -25.375, -20.450)
    ),
    "G3_IP5305_POWER_CORE": Island(
        "G3  IP5305 power core", ("U3", "L1", "C3", "C4", "C5", "C6", "R7"), (-9.085, 4.775, -33.875, -22.445)
    ),
    "G4_SYSTEM_5V_LIMIT": Island(
        "G4  system 5V limiter", ("U4", "R8", "C7", "C8", "C9"), (16.575, 26.375, -43.375, -36.225)
    ),
    "G5_PMIC_KEY_STATUS": Island(
        "G5  PMIC key / status", ("SW1", "D2", "R4", "R5", "R6", "LED1"), (-31.775, -24.225, 14.585, 21.175)
    ),
    "G6_RGB_BUFFER_PIXEL": Island(
        "G6  RGB buffer / pixel", ("U1", "D1", "R3", "C1", "C2"), (-10.000, -2.350, 16.775, 23.030)
    ),
    "G7_POWER_BAT_INTERFACES": Island(
        "G7  power / battery interfaces", ("J2", "J4"), (14.835, 28.625, 13.495, 26.505)
    ),
    "G8_SIGNAL_INTERFACE": Island(
        "G8  signal interface", ("J3",), (23.495, 36.505, -3.625, 4.225)
    ),
}


class WorkbenchError(RuntimeError):
    pass


def _remove_copper_and_groups(board: "pcbnew.BOARD") -> None:
    for item in list(board.GetTracks()):
        board.RemoveNative(item)
    for idx in reversed(range(board.GetAreaCount())):
        board.RemoveNative(board.GetArea(idx))
    for group in list(board.Groups()):
        board.RemoveNative(group)


def _add_rect(board: "pcbnew.BOARD", bounds: tuple[float, float, float, float]) -> "pcbnew.PCB_SHAPE":
    x0, x1, y0, y1 = bounds
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_RECT)
    shape.SetStart(pcbnew.VECTOR2I_MM(x0, y0))
    shape.SetEnd(pcbnew.VECTOR2I_MM(x1, y1))
    shape.SetLayer(pcbnew.Dwgs_User)
    shape.SetWidth(pcbnew.FromMM(0.20))
    board.Add(shape)
    return shape


def _add_text(board: "pcbnew.BOARD", text: str, x: float, y: float, size: float = 1.25) -> "pcbnew.PCB_TEXT":
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    item.SetLayer(pcbnew.Dwgs_User)
    item.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
    item.SetTextThickness(pcbnew.FromMM(0.20))
    board.Add(item)
    return item


def build(input_path: Path, output_path: Path, *, force: bool = False) -> None:
    if input_path.resolve() == output_path.resolve():
        raise WorkbenchError("input and output must be different; production board is read-only")
    if output_path.exists() and not force:
        raise WorkbenchError(
            f"refusing to overwrite existing workbench {output_path}; "
            "it may contain validated group routing (pass --force only to rebuild from zero)"
        )
    board = pcbnew.LoadBoard(str(input_path))
    if board is None:
        raise WorkbenchError(f"unable to load {input_path}")

    refs = {fp.GetReference(): fp for fp in board.GetFootprints()}
    expected = set(POSES)
    if set(refs) != expected:
        missing = sorted(expected - set(refs))
        extra = sorted(set(refs) - expected)
        raise WorkbenchError(f"footprint inventory mismatch: missing={missing}, extra={extra}")
    grouped = [ref for island in ISLANDS.values() for ref in island.refs]
    if len(grouped) != len(set(grouped)) or set(grouped) != expected:
        raise WorkbenchError("island membership must cover 33 refs exactly once")

    _remove_copper_and_groups(board)
    for ref, pose in POSES.items():
        fp = refs[ref]
        target_layer = LAYER_OVERRIDES.get(ref, fp.GetLayer())
        if fp.GetLayer() != target_layer:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        fp.SetPosition(pcbnew.VECTOR2I_MM(pose.x, pose.y))
        fp.SetOrientationDegrees(pose.angle)

    for name, island in ISLANDS.items():
        group = pcbnew.PCB_GROUP(board)
        group.SetName(name)
        board.Add(group)
        for ref in island.refs:
            group.AddItem(refs[ref])
        rect = _add_rect(board, island.bounds)
        group.AddItem(rect)
        x0, _x1, y0, _y1 = island.bounds
        label = _add_text(board, island.label, x0 + 0.5, y0 - 0.8)
        group.AddItem(label)

    _add_text(
        board,
        "FUNCTIONAL-ISLAND WORKBENCH ONLY — NOT FOR FABRICATION",
        -12.5,
        -3.0,
        0.65,
    )
    _add_text(
        board,
        "Original M7.C5 Edge.Cuts retained; all island-to-island nets intentionally unrouted",
        -12.5,
        -1.5,
        0.45,
    )
    title = board.GetTitleBlock()
    title.SetTitle("SmartPaddle M7.C5 tail functional-island workbench — NOT FOR FAB")
    board.SetTitleBlock(title)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.stem}.{uuid.uuid4().hex}.tmp.kicad_pcb")
    pcbnew.SaveBoard(str(temporary), board)
    verify = pcbnew.LoadBoard(str(temporary))
    if verify is None or len(list(verify.GetFootprints())) != 33:
        temporary.unlink(missing_ok=True)
        raise WorkbenchError("saved-board verification failed")
    os.replace(temporary, output_path)
    print(f"Functional-island workbench PASS: {output_path}")
    print("  33/33 footprints grouped exactly once; 0 tracks, 0 vias, 0 zones")
    print("  production Edge.Cuts retained; all islands deliberately outside board")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing placement/routing workbench with a zero-copper baseline",
    )
    args = parser.parse_args()
    build(args.input.resolve(), args.output.resolve(), force=args.force)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WorkbenchError as exc:
        print(f"WORKBENCH FAIL: {exc}")
        raise SystemExit(1)
