#!/usr/bin/env python3
"""Cross-layer validation and manufacturing gate for the power redesign.

The default mode validates the deliberately route-free handoff.  The
``--release-gate`` mode is called by manufacturing exporters and refuses any
board with missing copper, DRC errors/unconnected items, or an open mechanical
tolerance decision.
"""

# ===== Imports =====
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


# ===== Configuration =====
ROOT = Path(__file__).resolve().parents[1]
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
KICAD_PYTHON = Path(
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3"
)
BOARDS = {
    "main": ROOT / "pcb/layouts/default/default.kicad_pcb",
    "tail": ROOT / "pcb-tail/layouts/default/default.kicad_pcb",
}
EXPECTED_UNROUTED = {
    "main": {"footprints": 69, "unconnected": 149},
    "tail": {"footprints": 33, "unconnected": 79},
}
MECHANICAL_REPORT = ROOT / "enclosure/stl/interference/tail_interference.json"


# ===== Helpers =====
class ValidationError(RuntimeError):
    pass


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def board_counts(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8")
    return {
        "footprints": len(re.findall(r"(?m)^\t\(footprint ", text)),
        "segments": len(re.findall(r"(?m)^\t\(segment\b", text)),
        "vias": len(re.findall(r"(?m)^\t\(via\b", text)),
        "zones": len(re.findall(r"(?m)^\t\(zone\b", text)),
    }


def drc(path: Path, output: Path) -> tuple[int, int]:
    run([
        str(KICAD_CLI), "pcb", "drc", "--format", "json", "--units", "mm",
        "--severity-all", "--output", str(output), str(path),
    ])
    data = json.loads(output.read_text(encoding="utf-8"))
    return len(data.get("violations", [])), len(data.get("unconnected_items", []))


def run_semantic_audits(release_gate: bool) -> None:
    python = str(KICAD_PYTHON)
    for script in (
        "pcb/scripts/audit_power_architecture.py",
        "pcb-tail/scripts/audit_power_architecture.py",
        "pcb-tail/scripts/audit_usb_16p_j1.py",
        "pcb-tail/scripts/audit_battery_connector_j4.py",
    ):
        command = [python, str(ROOT / script)]
        if release_gate and (
            script.endswith("audit_power_architecture.py")
            or script.endswith("audit_battery_connector_j4.py")
        ):
            command.append("--allow-copper")
        run(command)
    run([sys.executable, str(ROOT / "scripts/validate_tail_board_harness.py")])


# ===== Public validation =====
def validate(release_gate: bool) -> None:
    for required in (KICAD_CLI, KICAD_PYTHON, MECHANICAL_REPORT, *BOARDS.values()):
        if not required.exists():
            raise ValidationError(f"missing required input: {required}")

    run_semantic_audits(release_gate)
    mechanical = json.loads(MECHANICAL_REPORT.read_text(encoding="utf-8"))
    button = mechanical.get("button", {})
    release_failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="smartpaddle-power-audit-") as temp:
        temp_dir = Path(temp)
        for name, board in BOARDS.items():
            counts = board_counts(board)
            violations, unconnected = drc(board, temp_dir / f"{name}-drc.json")
            if violations:
                if release_gate:
                    release_failures.append(f"{name}: DRC has {violations} violation(s)")
                else:
                    raise ValidationError(f"{name}: DRC has {violations} violation(s)")

            if release_gate:
                if counts["segments"] == 0:
                    release_failures.append(f"{name}: no routed segments")
                if counts["zones"] == 0:
                    release_failures.append(f"{name}: no copper zones")
                if unconnected:
                    release_failures.append(f"{name}: {unconnected} unconnected item(s)")
            else:
                expected = EXPECTED_UNROUTED[name]
                if counts != {
                    "footprints": expected["footprints"],
                    "segments": 0,
                    "vias": 0,
                    "zones": 0,
                }:
                    raise ValidationError(f"{name}: unexpected route-free counts {counts}")
                if unconnected != expected["unconnected"]:
                    raise ValidationError(
                        f"{name}: unconnected={unconnected}, expected {expected['unconnected']}"
                    )
            print(
                f"{name}: footprints={counts['footprints']} segments={counts['segments']} "
                f"vias={counts['vias']} zones={counts['zones']} "
                f"DRC violations={violations} unconnected={unconnected}"
            )

    if release_gate and button.get("tolerance_closed") is not True:
        release_failures.append(
            "tail button tolerance is not closed: "
            + str(button.get("manufacturing_blocker", "missing measured coupon"))
        )

    if release_failures:
        raise ValidationError("; ".join(release_failures))

    if release_gate:
        print("POWER REWORK MANUFACTURING GATE PASS")
    else:
        if button.get("tolerance_closed") is not False:
            raise ValidationError("route-free handoff expects an explicit open button tolerance gate")
        print("POWER REWORK ROUTE-FREE HANDOFF PASS")
        print("MANUFACTURING BLOCKED: both boards are unrouted and B3U plunger tolerance is open")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release-gate", action="store_true",
        help="require routed, connected boards and closed mechanical tolerance",
    )
    args = parser.parse_args()
    try:
        validate(args.release_gate)
    except (ValidationError, subprocess.CalledProcessError) as exc:
        print(f"VALIDATION FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
