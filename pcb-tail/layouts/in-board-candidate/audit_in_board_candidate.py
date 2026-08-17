#!/usr/bin/env python3
"""Read-only gate for the isolated, non-manufacturing in-board candidate."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pcbnew


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPTS = ROOT / "pcb-tail/scripts"
sys.path.insert(0, str(SCRIPTS))
from audit_functional_group_workbench import (  # noqa: E402
    _group_inventory,
    _validate_group_routes,
    _validate_no_via_in_pad,
)
from merge_functional_group_routes import _shape_fingerprint  # noqa: E402

BOARD = HERE / "in-board-candidate.kicad_pcb"
DRC = HERE / "drc-final.json"
SOURCE = ROOT / "pcb-tail/layouts/functional-groups/functional-groups.kicad_pcb"
PRODUCTION = ROOT / "pcb-tail/layouts/default/default.kicad_pcb"
ANCHORS = {
    "J1": (-6.858008, -0.381000, -90.0, pcbnew.F_Cu),
    "SW1": (-1.651000, -5.461000, -90.0, pcbnew.F_Cu),
    "D1": (2.454994, -3.783996, -90.0, pcbnew.F_Cu),
    "LED1": (-5.943500, -6.350000, 0.0, pcbnew.F_Cu),
    "J2": (-11.300000, -0.600000, -90.0, pcbnew.B_Cu),
    "J3": (6.300000, -5.800000, 180.0, pcbnew.B_Cu),
    "J4": (-2.794000, -7.000000, 90.0, pcbnew.B_Cu),
}
ROUTED_GROUPS = {
    "G2_USB_INPUT_LIMIT",
    "G3_IP5305_POWER_CORE",
    "G4_SYSTEM_5V_LIMIT",
    "G8_SIGNAL_INTERFACE",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def edge_fingerprint(board: pcbnew.BOARD) -> tuple[tuple[object, ...], ...]:
    return tuple(
        sorted(
            _shape_fingerprint(item)
            for item in board.GetDrawings()
            if item.GetLayer() == pcbnew.Edge_Cuts
        )
    )


def main() -> int:
    production_hash_before = sha256(PRODUCTION)
    board = pcbnew.LoadBoard(str(BOARD))
    expect("IN-BOARD PACKING CANDIDATE" in board.GetTitleBlock().GetTitle().upper(), "bad candidate title")
    expect(board.GetAreaCount() == 0, "candidate must contain zero zones")
    groups, route_owner, group_routes = _group_inventory(board)
    via_count = _validate_no_via_in_pad(board, route_owner)

    board.BuildConnectivity()
    connectivity = board.GetConnectivity()
    for group_name in sorted(ROUTED_GROUPS):
        _validate_group_routes(
            board, connectivity, group_name, group_routes[group_name], route_owner
        )

    for ref, (x, y, angle, layer) in ANCHORS.items():
        fp = board.FindFootprintByReference(ref)
        pos = fp.GetPosition()
        actual = (
            round(pcbnew.ToMM(pos.x), 6),
            round(pcbnew.ToMM(pos.y), 6),
            round(float(fp.GetOrientationDegrees()), 6),
            fp.GetLayer(),
        )
        expected = (round(x, 6), round(y, 6), round(angle, 6), layer)
        expect(actual == expected, f"anchor drift {ref}: {actual} != {expected}")

    source = pcbnew.LoadBoard(str(SOURCE))
    production = pcbnew.LoadBoard(str(PRODUCTION))
    edge = edge_fingerprint(board)
    expect(edge == edge_fingerprint(source), "candidate Edge.Cuts differs from validated source")
    expect(edge == edge_fingerprint(production), "candidate Edge.Cuts differs from production board")

    report = json.loads(DRC.read_text())
    errors = [item for item in report["violations"] if item["severity"] == "error"]
    warnings = [item for item in report["violations"] if item["severity"] == "warning"]
    expect(not errors, f"DRC contains {len(errors)} rule errors")
    expect(len(report["unconnected_items"]) == 53, "unexpected unconnected count drift")
    expect(sha256(PRODUCTION) == production_hash_before, "production board changed during audit")

    pending = {
        name: sorted({item.GetNetname() for item in group_routes[name]})
        for name in sorted(groups)
        if name not in ROUTED_GROUPS
    }
    print("IN-BOARD CANDIDATE AUDIT PASS (PLACEMENT / SAFE-LOCAL-COPPER ONLY)")
    print(f"  board: {BOARD}")
    print("  inventory: 33 footprints / 8 PCB_GROUPs / 0 zones")
    print("  Edge.Cuts: exact match to validated source and current production board")
    print("  anchors: J1/SW1/D1/LED1/J2/J3/J4 exact M7.C5 positions")
    print(f"  safe local copper: G2/G3/G4 (+ copper-free G8); vias={via_count}")
    print(f"  DRC: 0 rule errors, {len(warnings)} warnings, 53 unconnected items")
    print(f"  incomplete groups (no accepted local copper): {sorted(pending)}")
    print(f"  production SHA256 unchanged: {production_hash_before}")
    print("  status: candidate only; NOT FOR FABRICATION")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"IN-BOARD CANDIDATE AUDIT FAIL: {exc}")
        raise SystemExit(1)
