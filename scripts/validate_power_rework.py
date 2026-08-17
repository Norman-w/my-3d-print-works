#!/usr/bin/env python3
"""Cross-layer validation and manufacturing gate for the power redesign.

The default mode validates the deliberately route-free handoff.  The
``--release-gate`` mode is called by manufacturing exporters and refuses any
board with missing copper, DRC errors/unconnected items, or an incomplete
baseline button-access definition.  The retained plunger is an optional
accessory; its coupon tolerance does not block the verified pinhole baseline.
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
    "main": {"footprints": 69, "unconnected": 143},
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


def drc(path: Path, output: Path) -> tuple[int, int, int]:
    run([
        str(KICAD_CLI), "pcb", "drc", "--format", "json", "--units", "mm",
        "--severity-all", "--output", str(output), str(path),
    ])
    data = json.loads(output.read_text(encoding="utf-8"))
    violations = data.get("violations", [])
    errors = sum(item.get("severity") == "error" for item in violations)
    warnings = sum(item.get("severity") == "warning" for item in violations)
    return errors, warnings, len(data.get("unconnected_items", []))


def run_semantic_audits(release_gate: bool, target: str) -> None:
    python = str(KICAD_PYTHON)
    scripts: list[str] = []
    if target in ("all", "main"):
        scripts.append("pcb/scripts/audit_power_architecture.py")
    if target in ("all", "tail"):
        scripts.extend((
            "pcb-tail/scripts/audit_power_architecture.py",
            "pcb-tail/scripts/audit_usb_16p_j1.py",
            "pcb-tail/scripts/audit_battery_connector_j4.py",
            "scripts/validate_mechanical_handoff.py",
        ))
    for script in scripts:
        command = [python, str(ROOT / script)]
        if release_gate and (
            script.endswith("audit_power_architecture.py")
            or script.endswith("audit_battery_connector_j4.py")
        ):
            command.append("--allow-copper")
        run(command)
    if target in ("all", "main", "tail"):
        run([sys.executable, str(ROOT / "scripts/validate_tail_board_harness.py")])


# ===== Public validation =====
def validate(release_gate: bool, target: str = "all") -> None:
    selected_boards = BOARDS if target == "all" else {target: BOARDS[target]}
    required_inputs = [KICAD_CLI, KICAD_PYTHON, *selected_boards.values()]
    if target in ("all", "tail"):
        required_inputs.append(MECHANICAL_REPORT)
    for required in required_inputs:
        if not required.exists():
            raise ValidationError(f"missing required input: {required}")

    run_semantic_audits(release_gate, target)
    button: dict[str, object] = {}
    if target in ("all", "tail"):
        mechanical = json.loads(MECHANICAL_REPORT.read_text(encoding="utf-8"))
        button = mechanical.get("button", {})
    release_failures: list[str] = []

    if target in ("all", "tail"):
        if button.get("access_mode") != "pinhole_with_optional_retained_plunger":
            raise ValidationError("tail button access mode is missing or unexpected")
        if button.get("pinhole_ready") is not True or float(button.get("hole_d", 0)) < 1.8:
            raise ValidationError("tail button pinhole is not a usable verified baseline")
        if button.get("plunger_optional") is not True:
            raise ValidationError("tail button plunger must remain explicitly optional")

    with tempfile.TemporaryDirectory(prefix="smartpaddle-power-audit-") as temp:
        temp_dir = Path(temp)
        for name, board in selected_boards.items():
            counts = board_counts(board)
            errors, warnings, unconnected = drc(board, temp_dir / f"{name}-drc.json")
            if errors:
                if release_gate:
                    release_failures.append(f"{name}: DRC has {errors} error(s)")
                else:
                    raise ValidationError(f"{name}: DRC has {errors} error(s)")

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
                f"vias={counts['vias']} copper_zones={counts['zones']} "
                f"DRC errors={errors} warnings={warnings} unconnected={unconnected}"
            )

    if release_failures:
        raise ValidationError("; ".join(release_failures))

    if release_gate:
        print("POWER REWORK MANUFACTURING GATE PASS")
    else:
        if target in ("all", "tail") and button.get("tolerance_closed") is not False:
            raise ValidationError("optional plunger must retain its explicit open coupon status")
        print("POWER REWORK ROUTE-FREE HANDOFF PASS")
        print("MANUFACTURING BLOCKED: both boards are unrouted")
        print("B3U: Ø2.0 mm pinhole is baseline; retained plunger remains an optional coupon item")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release-gate", action="store_true",
        help="require routed, connected boards and closed mechanical tolerance",
    )
    parser.add_argument(
        "--target", choices=("all", "main", "tail"), default="all",
        help="validate both boards (default) or one independently fabricated board",
    )
    args = parser.parse_args()
    try:
        validate(args.release_gate, args.target)
    except (ValidationError, subprocess.CalledProcessError) as exc:
        print(f"VALIDATION FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
