#!/usr/bin/env python3
"""Build a non-manufacturing tail-board packing candidate.

The production board is never opened for writing.  The source is the validated
functional-island workbench; only G2/G3/G4 keep their verified local copper as
rigid islands.  Mechanically anchored groups are decomposed and repacked around
the frozen M7.C5 connector/hole poses, so their old local copper is removed and
must be re-routed inside this candidate.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "pcb-tail/layouts/functional-groups/functional-groups.kicad_pcb"
PRODUCTION = ROOT / "pcb-tail/layouts/default/default.kicad_pcb"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "in-board-candidate.kicad_pcb"

PRESERVED_GROUP_POSES = {
    # group name: (pivot reference, rotation delta deg, new pivot x/y)
    "G2_USB_INPUT_LIMIT": ("U5", 0.0, (7.25, 4.75)),
    "G3_IP5305_POWER_CORE": ("U3", 0.0, (4.80, 3.00)),
    "G4_SYSTEM_5V_LIMIT": ("U4", 90.0, (7.75, -4.00)),
}

# P0/P1 mechanical anchors come from the M7.C5 shell contract.  The remaining
# poses are the first constraint-clean packing result around those anchors.
POSES = {
    # G1: J1 is the hard USB opening anchor.
    "J1": (-6.858008, -0.381000, -90.0),
    "R1": (-2.984000, -0.762000, 0.0),
    "R2": (-9.949000, 0.853000, -90.0),
    "U2": (-2.771016, 4.704503, -90.0),
    # G5: SW1 and LED1 are separate shell-hole anchors.
    "SW1": (-1.651000, -5.461000, -90.0),
    "LED1": (-5.943500, -6.350000, 0.0),
    "D2": (1.250000, -7.500000, 90.0),
    "R4": (-7.500000, -7.700000, 0.0),
    "R5": (-8.000000, 6.500000, 180.0),
    "R6": (-4.500000, 7.000000, 0.0),
    # G6: D1 is the RGB light-pipe anchor.
    "D1": (2.454994, -3.783996, -90.0),
    "C1": (3.500000, -7.250000, 270.0),
    "C2": (1.000000, -1.000000, 0.0),
    "U1": (-2.750000, -1.750000, 90.0),
    "R3": (-5.000000, 4.400000, 90.0),
    # G7/G8: qualified connector and mated-housing poses.
    "J2": (-11.300000, -0.600000, -90.0),
    "J4": (-2.794000, -7.000000, 90.0),
    "J3": (6.300000, -5.800000, 180.0),
}

CLEAR_LOCAL_COPPER_GROUPS = {
    "G1_USB_C_CC_ESD",
    "G5_PMIC_KEY_STATUS",
    "G6_RGB_BUFFER_PIXEL",
    "G7_POWER_BAT_INTERFACES",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vector(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I_MM(x, y)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if output == PRODUCTION.resolve():
        raise SystemExit("refusing to overwrite the production tail board")
    if output.exists() and not args.force:
        raise SystemExit(f"output exists; pass --force intentionally: {output}")

    production_hash_before = sha256(PRODUCTION)
    board = pcbnew.LoadBoard(str(SOURCE))

    groups = {group.GetName(): group for group in board.Groups()}
    group_items = {name: list(group.GetItems()) for name, group in groups.items()}
    expected_groups = set(PRESERVED_GROUP_POSES) | CLEAR_LOCAL_COPPER_GROUPS
    missing = expected_groups - set(groups)
    if missing:
        raise RuntimeError(f"missing expected workbench groups: {sorted(missing)}")

    # Mechanically anchored groups cannot remain rigid.  Remove only their
    # workbench tracks/vias; footprint membership and net assignments stay intact.
    for group_name in CLEAR_LOCAL_COPPER_GROUPS:
        group = groups[group_name]
        for item in group_items[group_name]:
            if isinstance(item, (pcbnew.PCB_TRACK, pcbnew.PCB_VIA)):
                group.RemoveItem(item)
                board.Remove(item)

    # Move the three electrically sensitive islands as rigid bodies so every
    # verified internal route and relative component pose remains byte-semantic.
    for group_name, (pivot_ref, angle_deg, target) in PRESERVED_GROUP_POSES.items():
        group = groups[group_name]
        pivot_fp = board.FindFootprintByReference(pivot_ref)
        pivot = pivot_fp.GetPosition()
        if angle_deg:
            group.Rotate(pivot, pcbnew.EDA_ANGLE(angle_deg, pcbnew.DEGREES_T))
        new_pivot = vector(*target)
        group.Move(new_pivot - pivot)

    # Repack the decomposed groups around their exact shell/connector anchors.
    for ref, (x, y, rot) in POSES.items():
        footprint = board.FindFootprintByReference(ref)
        if footprint is None:
            raise RuntimeError(f"missing footprint {ref}")
        if ref == "C1" and footprint.GetLayer() != pcbnew.F_Cu:
            footprint.Flip(footprint.GetPosition(), False)
        footprint.SetPosition(vector(x, y))
        footprint.SetOrientationDegrees(rot)

    # Workbench labels and island boxes are diagnostic only.  Detach them from
    # their PCB_GROUP before removing them so KiCad never retains a dangling
    # grouped-item pointer.  Preserve exactly the real production Edge.Cuts.
    for group_name, group in groups.items():
        for item in group_items[group_name]:
            if isinstance(item, pcbnew.PCB_SHAPE) and item.GetLayer() != pcbnew.Edge_Cuts:
                group.RemoveItem(item)
                board.Remove(item)
            elif isinstance(item, pcbnew.PCB_TEXT):
                group.RemoveItem(item)
                board.Remove(item)
    for drawing in list(board.GetDrawings()):
        if drawing.GetLayer() != pcbnew.Edge_Cuts:
            board.Remove(drawing)

    board.GetTitleBlock().SetTitle("IN-BOARD PACKING CANDIDATE ONLY - NOT FOR FABRICATION")
    board.GetTitleBlock().SetComment(0, "M7.C5 mechanical anchors; cross-group nets intentionally unrouted")
    board.BuildConnectivity()
    output.parent.mkdir(parents=True, exist_ok=True)
    pcbnew.SaveBoard(str(output), board)

    production_hash_after = sha256(PRODUCTION)
    if production_hash_after != production_hash_before:
        raise RuntimeError("production board hash changed unexpectedly")
    print(f"wrote {output}")
    print(f"production SHA256 unchanged: {production_hash_after}")
    print(f"footprints={len(board.GetFootprints())} tracks+vias={len(board.GetTracks())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
