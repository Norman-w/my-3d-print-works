#!/usr/bin/env python3
"""Validate the main-to-tail-board harness against both actual KiCad boards."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "pcb-tail/harness/adapter.json"
TAIL_INTERFERENCE = ROOT / "enclosure/stl/interference/tail_interference.json"
SCREW_SAFETY = ROOT / "enclosure/generated/m6_screw_safety.json"
MAIN_FIT_REPORT = ROOT / "pcb/output/tail_mx125_fit/fit_report.txt"


def footprint_block(text: str, reference: str) -> str:
    marker = f'(property "Reference" "{reference}"'
    at = text.find(marker)
    if at < 0:
        raise ValueError(f"missing footprint {reference}")
    start = text.rfind("(footprint", 0, at)
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise ValueError(f"unterminated footprint {reference}")


def pad_nets(board: Path, reference: str) -> dict[str, str]:
    block = footprint_block(board.read_text(encoding="utf-8"), reference)
    result: dict[str, str] = {}
    for match in re.finditer(r'\(pad\s+"?([^"\s]+)"?[\s\S]*?\(net\s+\d+\s+"([^"]+)"\)', block):
        pin, net = match.groups()
        if pin.isdigit():
            result[pin] = net
    return result


def footprint_id(board: Path, reference: str) -> str:
    block = footprint_block(board.read_text(encoding="utf-8"), reference)
    match = re.match(r'\(footprint\s+"([^"]+)"', block)
    if not match:
        raise ValueError(f"cannot parse footprint id for {reference}")
    return match.group(1)


def main() -> int:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    main_board = ROOT / spec["mainBoard"]
    tail_board = ROOT / spec["tailBoard"]
    boards = {
        "main": main_board,
        "tail": tail_board,
    }
    caches: dict[tuple[str, str], dict[str, str]] = {}
    errors: list[str] = []
    seen_main: set[tuple[str, str]] = set()
    seen_tail: set[tuple[str, str]] = set()
    connector_contract = spec.get("tailBoardConnectors", {})
    if set(connector_contract) != {"J2", "J3"}:
        errors.append("tail connector metadata must cover exactly J2/J3")
    for reference, contract in connector_contract.items():
        actual_fpid = footprint_id(tail_board, reference)
        if actual_fpid != contract.get("footprint"):
            errors.append(
                f"tail {reference} footprint: {actual_fpid!r} != "
                f"{contract.get('footprint')!r}"
            )
        if (
            contract.get("manufacturerPartNumber") != "53261-0471"
            or contract.get("mount") != "right-angle SMT"
            or contract.get("matingHousing") != "51021-0400"
        ):
            errors.append(f"tail {reference} is not the approved 53261/51021 system")
        else:
            print(f"✓ {reference}=Molex 53261-0471 right-angle SMT -> 51021-0400")
    for wire in spec["conductors"]:
        for side, ref_key, pin_key, net_key in (
            ("tail", "tailRef", "tailPin", "tailNet"),
            ("main", "mainRef", "mainPin", "mainNet"),
        ):
            ref, pin, expected = wire[ref_key], wire[pin_key], wire[net_key]
            cache_key = (side, ref)
            actuals = caches.setdefault(cache_key, pad_nets(boards[side], ref))
            actual = actuals.get(pin)
            if actual != expected:
                errors.append(f"{side} {ref}.{pin}: {actual!r} != {expected!r}")
        seen_tail.add((wire["tailRef"], wire["tailPin"]))
        seen_main.add((wire["mainRef"], wire["mainPin"]))
        print(
            f"✓ {wire['tailRef']}.{wire['tailPin']} {wire['tailNet']} -> "
            f"{wire['mainRef']}.{wire['mainPin']} {wire['mainNet']}"
        )

    for item in spec["intentionallyUnconnectedMainPins"]:
        ref, pin, expected = item["mainRef"], item["mainPin"], item["mainNet"]
        actual = caches.setdefault(("main", ref), pad_nets(main_board, ref)).get(pin)
        if actual != expected or (ref, pin) in seen_main:
            errors.append(f"reserved {ref}.{pin}: actual={actual!r}, expected={expected!r}")

    tail_signal_pins = {
        (ref, pin)
        for (side, ref), nets in caches.items() if side == "tail"
        for pin in nets if pin.isdigit()
    }
    if tail_signal_pins != seen_tail:
        errors.append(f"tail connector coverage mismatch: {sorted(tail_signal_pins ^ seen_tail)}")

    mech = spec["mechanical"]
    wire = spec.get("wireConstruction", {})
    if (
        wire.get("marking") != "UL1571 28AWG"
        or wire.get("conductor") != "7 x 0.12 mm tinned copper"
        or abs(float(wire.get("outerDiameterMm", 0)) - 0.9) > 1e-6
        or abs(float(wire.get("tinnedFreeEndMm", 0)) - 3.0) > 1e-6
        or {int(item["wireAwg"]) for item in spec["conductors"]} != {28}
    ):
        errors.append("finished-wire construction differs from purchased UL1571 28AWG leads")
    else:
        print("✓ wire construction=UL1571 28AWG, 7x0.12mm, OD0.9mm, tinned 3mm")
    allowed = mech["allowedHarnessLengthMm"]
    if not (allowed[0] <= mech["finishedHarnessLengthMm"] <= allowed[1]):
        errors.append("finished harness length outside allowed range")
    if mech["finishedHarnessLengthMm"] - mech["nominalSpanMm"] < mech["serviceLoopMinMm"]:
        errors.append("insufficient service-loop allowance")

    # Mechanical values are checked against generated geometry reports rather
    # than trusted as prose. The main-board connector Y range comes from the shell-fit
    # calculation; the tail-board plane comes from the actual KiCad interference export.
    fit_text = MAIN_FIT_REPORT.read_text(encoding="utf-8")
    match = re.search(r"Fab SCAD X\[[^]]+\] Y\[([-.0-9]+),([-.0-9]+)\]", fit_text)
    if not match:
        errors.append("cannot parse main-board connector world-Y range")
    else:
        main_center_y = sum(map(float, match.groups())) / 2
        tail = json.loads(TAIL_INTERFERENCE.read_text(encoding="utf-8"))
        actual_span = abs(float(tail["pcb_y"]) - main_center_y)
        if abs(actual_span - float(mech["nominalSpanMm"])) > 0.25:
            errors.append(
                f"harness span stale: spec={mech['nominalSpanMm']:.3f}, actual={actual_span:.3f}"
            )
        print(f"✓ mechanical span={actual_span:.3f}mm service allowance={mech['finishedHarnessLengthMm'] - actual_span:.3f}mm")

        mechanical_connectors = {
            item.get("ref"): item for item in tail.get("harness_connectors", [])
        }
        if set(mechanical_connectors) != {"J2", "J3"}:
            errors.append("tail mechanical facts do not cover J2/J3 harness connectors")
        for reference, contract in connector_contract.items():
            item = mechanical_connectors.get(reference, {})
            pose = contract.get("pose", {})
            actual_pose = (
                float(item.get("x", 999)),
                float(item.get("y", 999)),
                float(item.get("rot_deg", 999)),
                item.get("layer"),
            )
            expected_pose = (
                float(pose.get("xMm", 999)),
                float(pose.get("yMm", 999)),
                float(pose.get("rotationDeg", 999)),
                pose.get("layer"),
            )
            if actual_pose != expected_pose or float(item.get("mated_height", 0)) != 3.4:
                errors.append(
                    f"tail {reference} mechanical pose/envelope is stale: "
                    f"{actual_pose!r} != {expected_pose!r}"
                )

    screw = json.loads(SCREW_SAFETY.read_text(encoding="utf-8"))
    boss_radius = float(screw["bossDiameterMm"]) / 2
    route = mech["routing"]
    bundle_radius = float(route["bundleEnvelopeRadiusMm"])
    required_clearance = float(route["minimumScrewEnvelopeClearanceMm"])
    for label, center_x in (
        ("power", float(route["powerBundleCenterXmm"])),
        ("signal", float(route["signalBundleCenterXmm"])),
    ):
        clearance = min(
            abs(float(move["final"][0]) - center_x) - boss_radius - bundle_radius
            for move in screw["moves"]
        )
        if clearance < required_clearance:
            errors.append(f"{label} bundle-to-screw clearance {clearance:.3f}mm")
        else:
            print(f"✓ {label} bundle-to-screw envelope clearance={clearance:.3f}mm")

    bypass_size = float(route["batteryBypassCorridorSizeMm"])
    bypass_center = float(route["batteryBypassCenterXmm"])
    if bypass_size + 1e-6 < 2 * float(wire.get("outerDiameterMm", 0)):
        errors.append("battery-bypass passage is too small for a 2x2 wire branch")
    if not (
        abs(bypass_center - 8.2) < 1e-6
        and route["batteryBypassYRangeMm"] == [-159.25, -106.75]
    ):
        errors.append("battery-bypass route differs from the enclosure mechanical contract")
    else:
        print(f"✓ battery bypass=two {bypass_size:.1f}mm square corridors at X=±{bypass_center:.1f}mm")

    if errors:
        print("\nTail harness validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 2
    print("\nTail harness validation passed: 8 mapped conductors + 2 reserved UART pins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
