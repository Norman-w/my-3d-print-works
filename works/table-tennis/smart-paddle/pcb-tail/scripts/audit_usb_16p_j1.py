#!/usr/bin/env python3
"""Audit tail-board J1 against the archived H=5.8 short-pin PDF.

KiCad DRC cannot know a supplier connector's physical contact semantics.  This
gate therefore checks all 16 contacts by name, local position, land size and
net, plus the two shell slots, in both the library footprint and the PCB.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import hashlib
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path


# ===== 分区：常量/配置 =====
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PCB = ROOT / "pcb-tail" / "layouts" / "default" / "default.kicad_pcb"
FOOTPRINT = (
    ROOT
    / "pcb-tail"
    / "lib"
    / "footprints.pretty"
    / "USB_C_Receptacle_16P_Vertical_SMT_Short.kicad_mod"
)
PARTS = ROOT / "pcb-tail" / "parts.ato"
MAIN = ROOT / "pcb-tail" / "main.ato"
DATASHEET = (
    ROOT
    / "docs"
    / "usb-c-vertical-16p-short"
    / "Type-C-16PIN-vertical-H5.8-short-datasheet.pdf"
)
DATASHEET_SHA256 = "8d8f9afa88a8fc6049e041b519745d119b16f8eccdcf78de7f4090ee294dff23"

PAD_W = 0.43
PAD_H = 1.40
YA = -1.15
YB = 1.15
XS = (-2.73, -1.95, -1.17, -0.39, 0.39, 1.17, 1.95, 2.73)
J1_AT = (-6.858008, -0.381, -90.0)
TOL = 1e-6

A_ORDER = ("A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12")
B_ORDER = ("B12", "B9", "B8", "B7", "B6", "B5", "B4", "B1")
if len(A_ORDER) != len(XS) or len(B_ORDER) != len(XS):
    raise RuntimeError("USB contact-order tables must match the eight X positions")
CONTACT_NETS = {
    "A1": "GND",
    "A4": "vbus",
    "A5": "cc1",
    "A6": "usb_dp_conn",
    "A7": "usb_dn_conn",
    "A8": None,
    "A9": "vbus",
    "A12": "GND",
    "B12": "GND",
    "B9": "vbus",
    "B8": None,
    "B7": "usb_dn_conn",
    "B6": "usb_dp_conn",
    "B5": "cc2",
    "B4": "vbus",
    "B1": "GND",
}
SOURCE_NETS = {
    "A1": "gnd",
    "A4": "vbus",
    "A5": "cc1",
    "A6": "usb_dp_conn",
    "A7": "usb_dn_conn",
    "A9": "vbus",
    "A12": "gnd",
    "B1": "gnd",
    "B4": "vbus",
    "B5": "cc2",
    "B6": "usb_dp_conn",
    "B7": "usb_dn_conn",
    "B9": "vbus",
    "B12": "gnd",
    "S1": "gnd",
}


# ===== 分区：数据结构 =====
@dataclass(frozen=True)
class Pad:
    name: str
    at: tuple[float, float]
    size: tuple[float, float]
    drill: tuple[float, float] | None
    net: str | None


# ===== 分区：私有成员 =====
def _sexpr_blocks(text: str, head: str) -> list[str]:
    """Return balanced S-expression blocks beginning with ``(head``."""
    blocks: list[str] = []
    needle = f"({head}"
    cursor = 0
    while True:
        start = text.find(needle, cursor)
        if start < 0:
            return blocks
        depth = 0
        quoted = False
        escaped = False
        for end in range(start, len(text)):
            char = text[end]
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
                continue
            if char == '"':
                quoted = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    blocks.append(text[start : end + 1])
                    cursor = end + 1
                    break
        else:
            raise ValueError(f"unbalanced ({head} block at byte {start}")


def _number_pair(block: str, keyword: str) -> tuple[float, float]:
    match = re.search(
        rf"\({re.escape(keyword)}\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)",
        block,
    )
    if not match:
        raise ValueError(f"missing {keyword} in {block[:80]!r}")
    return float(match.group(1)), float(match.group(2))


def _parse_pad(block: str) -> Pad:
    name_match = re.match(r'\(pad\s+"([^"]+)"', block)
    if not name_match:
        raise ValueError(f"unnamed pad: {block[:80]!r}")
    drill_match = re.search(
        r"\(drill(?:\s+oval)?\s+(-?\d+(?:\.\d+)?)"
        r"(?:\s+(-?\d+(?:\.\d+)?))?",
        block,
    )
    drill = None
    if drill_match:
        first = float(drill_match.group(1))
        drill = (first, float(drill_match.group(2) or first))
    net_match = re.search(r'\(net\s+\d+\s+"([^"]+)"\)', block)
    return Pad(
        name=name_match.group(1),
        at=_number_pair(block, "at"),
        size=_number_pair(block, "size"),
        drill=drill,
        net=net_match.group(1) if net_match else None,
    )


def _close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, abs_tol=TOL)


def _pair_close(actual: tuple[float, float], expected: tuple[float, float]) -> bool:
    return _close(actual[0], expected[0]) and _close(actual[1], expected[1])


def _find_j1(board_text: str) -> str:
    matches = [
        block
        for block in _sexpr_blocks(board_text, "footprint")
        if re.search(r'\(property\s+"Reference"\s+"J1"', block)
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one J1 footprint, found {len(matches)}")
    return matches[0]


def _component_body(parts_text: str) -> str:
    match = re.search(
        r"(?ms)^component USB4120_03_C_Vertical:\s*(.*?)(?=^component |\Z)",
        parts_text,
    )
    if not match:
        raise ValueError("USB4120_03_C_Vertical component not found")
    return match.group(1)


def _global_xy(local: tuple[float, float]) -> tuple[float, float]:
    ox, oy, degrees = J1_AT
    radians = math.radians(degrees)
    x, y = local
    return (
        ox + x * math.cos(radians) - y * math.sin(radians),
        oy + x * math.sin(radians) + y * math.cos(radians),
    )


# ===== 分区：公开 API =====
def main() -> int:
    failures: list[str] = []
    for path in (PCB, FOOTPRINT, PARTS, MAIN, DATASHEET):
        if not path.is_file():
            failures.append(f"missing required file: {path}")
    if failures:
        print("\n".join(f"FAIL: {item}" for item in failures), file=sys.stderr)
        return 1

    actual_sha = hashlib.sha256(DATASHEET.read_bytes()).hexdigest()
    if actual_sha != DATASHEET_SHA256:
        failures.append(f"datasheet SHA-256 {actual_sha} != {DATASHEET_SHA256}")

    footprint_text = FOOTPRINT.read_text(encoding="utf-8")
    board_text = PCB.read_text(encoding="utf-8")
    parts_text = PARTS.read_text(encoding="utf-8")
    main_text = MAIN.read_text(encoding="utf-8")
    j1 = _find_j1(board_text)

    at_match = re.search(
        r"\(at\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)"
        r"(?:\s+(-?\d+(?:\.\d+)?))?\)",
        j1,
    )
    if not at_match:
        failures.append("J1 has no footprint position")
    else:
        actual_at = tuple(float(at_match.group(i) or 0) for i in range(1, 4))
        if len(actual_at) != len(J1_AT) or any(
            not _close(a, e) for a, e in zip(actual_at, J1_AT)
        ):
            failures.append(f"J1 moved/rotated: {actual_at} != {J1_AT}")

    expected_positions = {
        **{name: (x, YA) for name, x in zip(A_ORDER, XS)},
        **{name: (x, YB) for name, x in zip(B_ORDER, XS)},
    }

    for label, text, require_nets in (
        ("library footprint", footprint_text, False),
        ("PCB J1", j1, True),
    ):
        pads = [_parse_pad(block) for block in _sexpr_blocks(text, "pad")]
        by_name: dict[str, list[Pad]] = {}
        for pad in pads:
            by_name.setdefault(pad.name, []).append(pad)
        if len(pads) != 18:
            failures.append(f"{label}: expected 18 pad objects, found {len(pads)}")
        expected_names = set(CONTACT_NETS) | {"S1"}
        if set(by_name) != expected_names:
            failures.append(
                f"{label}: pad names {sorted(by_name)} != {sorted(expected_names)}"
            )
        for name, expected_at in expected_positions.items():
            candidates = by_name.get(name, [])
            if len(candidates) != 1:
                failures.append(f"{label}: {name} count={len(candidates)}, expected 1")
                continue
            pad = candidates[0]
            if not _pair_close(pad.at, expected_at):
                failures.append(f"{label}: {name} at={pad.at}, expected={expected_at}")
            if not _pair_close(pad.size, (PAD_W, PAD_H)):
                failures.append(f"{label}: {name} size={pad.size}, expected={(PAD_W, PAD_H)}")
            if pad.drill is not None:
                failures.append(f"{label}: contact {name} unexpectedly has a drill")
            expected_net = CONTACT_NETS[name] if require_nets else None
            if pad.net != expected_net:
                failures.append(f"{label}: {name} net={pad.net!r}, expected={expected_net!r}")
        shell = by_name.get("S1", [])
        if len(shell) != 2:
            failures.append(f"{label}: S1 count={len(shell)}, expected 2")
        else:
            shell.sort(key=lambda pad: pad.at[0])
            for pad, expected_x in zip(shell, (-4.34, 4.34)):
                if not _pair_close(pad.at, (expected_x, 0.0)):
                    failures.append(f"{label}: S1 at={pad.at}, expected={(expected_x, 0.0)}")
                if not _pair_close(pad.size, (0.80, 1.55)):
                    failures.append(f"{label}: S1 size={pad.size}, expected={(0.80, 1.55)}")
                if pad.drill is None or not _pair_close(pad.drill, (0.50, 1.25)):
                    failures.append(f"{label}: S1 drill={pad.drill}, expected={(0.50, 1.25)}")
                expected_net = "GND" if require_nets else None
                if pad.net != expected_net:
                    failures.append(f"{label}: S1 net={pad.net!r}, expected={expected_net!r}")

    component = _component_body(parts_text)
    declared_pins = re.findall(r'^\s*pin\s+"([^"]+)"\s*$', component, re.MULTILINE)
    expected_pins = list(A_ORDER) + ["B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12", "S1"]
    if declared_pins != expected_pins:
        failures.append(f"parts.ato named pins {declared_pins} != {expected_pins}")
    if re.search(r"(?m)^\s*signal\s+(?:A|B)\d+\s*$", component):
        failures.append("parts.ato reintroduces signal/pin name shadowing")

    for contact, net in SOURCE_NETS.items():
        if not re.search(
            rf"(?m)^\s*usb\.{re.escape(contact)}\s*~\s*{re.escape(net)}\s*$",
            main_text,
        ):
            failures.append(f"main.ato missing usb.{contact} ~ {net}")
    for contact in ("A8", "B8"):
        if re.search(rf"(?m)^\s*usb\.{contact}\s*~", main_text):
            failures.append(f"main.ato {contact} must remain NC")

    source_path = "docs/usb-c-vertical-16p-short/Type-C-16PIN-vertical-H5.8-short-datasheet.pdf"
    if source_path not in footprint_text or source_path not in j1:
        failures.append("library footprint or PCB J1 does not identify the primary PDF")

    print("J1 physical-contact audit (PCB view; local coordinates in mm)")
    print("contact  local-x  local-y  global-x    global-y    net")
    for name in A_ORDER + B_ORDER:
        local = expected_positions[name]
        global_xy = _global_xy(local)
        print(
            f"{name:>4}  {local[0]:+7.2f}  {local[1]:+7.2f}  "
            f"{global_xy[0]:+10.6f}  {global_xy[1]:+10.6f}  "
            f"{CONTACT_NETS[name] or 'NC'}"
        )

    if failures:
        print("\nAUDIT FAILED", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"\nAUDIT PASS: 16 contacts + 2 shell slots; PDF SHA-256 {actual_sha}")
    return 0


# ===== 分区：方法/工具 =====
if __name__ == "__main__":
    raise SystemExit(main())
