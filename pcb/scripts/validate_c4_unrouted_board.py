#!/usr/bin/env python3
"""Validate the checked-in C4 board before manual routing starts.

This checks the explicit C4 migration table against the KiCad board.  It is
not a substitute for compiling ``main.ato`` with the repository-locked
atopile version; that separate gate remains visible in C4_PLAN.md.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "pcb" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from migrate_c3_to_c4_unrouted import (
    BOARD,
    C4_PARTS,
    DNP_ADDRESSES,
    PAD_NETS,
    _addr,
    _source_guard,
)
from apply_tail_mx125 import CONN_B, CONN_F
from step4_ato_placement import TAIL_NET_MAP

DEFAULT_DRC = ROOT / "pcb" / "layouts" / "default" / "output" / "c4_unrouted_drc.json"
TAIL_HTML = ROOT / "output" / "assembly" / "smartpaddle_tail_wiring.html"
TAIL_PNG = ROOT / "output" / "assembly" / "smartpaddle_tail_mx125_pinout.png"
PLACEMENT_SNAPSHOT = (
    ROOT / "pcb" / "layouts" / "default" / "c4_placement_snapshot.json"
)
ALLOWED_BASELINE_WARNING_TYPES = {
    "silk_edge_clearance",
    "silk_over_copper",
    "silk_overlap",
}

EXPECTED_TAIL_MAP = {
    "tail.conn_f": {
        "1": "sys_5v_in", "2": "sys_5v_sw", "3": "btn_sw",
        "4": "usb_dp", "5": "uart_tx",
    },
    "tail.conn_b": {
        "1": "uart_rx", "2": "usb_dn", "3": "bat_cell_p",
        "4": "led_din", "5": "gnd",
    },
}
EXPECTED_ATO_TAIL_PINS = {
    "tail.conn_f": {
        "1": "SYS_5V_IN", "2": "LED_PLUS", "3": "BUTTON",
        "4": "USB_DP", "5": "UART_TX",
    },
    "tail.conn_b": {
        "1": "UART_RX", "2": "USB_DN", "3": "BAT_CELL_P",
        "4": "LED_DIN", "5": "GND",
    },
}
EXPECTED_ATO_TAIL_BINDINGS = {
    "SYS_5V_IN": "sys_5v_in",
    "LED_PLUS": "sys_5v_sw",
    "BUTTON": "btn_sw",
    "USB_DP": "usb_dp",
    "UART_TX": "uart_tx",
    "UART_RX": "uart_rx",
    "USB_DN": "usb_dn",
    "BAT_CELL_P": "bat_cell_p",
    "LED_DIN": "led_din",
    "GND": "gnd",
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def _tail_source_errors() -> list[str]:
    errors: list[str] = []

    code_maps = {
        "step4_ato_placement.py": TAIL_NET_MAP,
        "apply_tail_mx125.py": {
            "tail.conn_f": CONN_F["nets"],
            "tail.conn_b": CONN_B["nets"],
        },
        "migrate/step3 PAD_NETS": {
            address: {
                pin: net for pin, net in PAD_NETS[address].items() if pin != "MP"
            }
            for address in EXPECTED_TAIL_MAP
        },
    }
    for source, mapping in code_maps.items():
        if mapping != EXPECTED_TAIL_MAP:
            errors.append(f"{source}: C4 tail map differs: {mapping}")

    ato_text = (ROOT / "pcb" / "main.ato").read_text(encoding="utf-8")
    block_match = re.search(
        r"module\s+TailHarness5P2S:(.*?)(?=\nmodule\s+)", ato_text, re.S
    )
    if block_match is None:
        errors.append("main.ato: TailHarness5P2S block missing")
    else:
        ato_pin_map = {"tail.conn_f": {}, "tail.conn_b": {}}
        for side, pin, signal in re.findall(
            r"conn_([fb])\.p([1-5])\s*~\s*(\w+)", block_match.group(1)
        ):
            ato_pin_map[f"tail.conn_{side}"][pin] = signal
        if ato_pin_map != EXPECTED_ATO_TAIL_PINS:
            errors.append(f"main.ato: TailHarness5P2S pins differ: {ato_pin_map}")

    ato_bindings = {
        signal: net
        for signal, net in re.findall(r"tail\.(\w+)\s*~\s*(\w+)", ato_text)
        if signal in EXPECTED_ATO_TAIL_BINDINGS
    }
    if ato_bindings != EXPECTED_ATO_TAIL_BINDINGS:
        errors.append(f"main.ato: top-level tail bindings differ: {ato_bindings}")

    doc_text = (ROOT / "docs" / "1.25x10p" / "README.md").read_text(
        encoding="utf-8"
    )
    section_match = re.search(
        r"## C4 现行线序.*?(?=\n## )", doc_text, re.S
    )
    doc_map = {"tail.conn_f": {}, "tail.conn_b": {}}
    if section_match is not None:
        for side, pin, net in re.findall(
            r"\|\s*([FB])(?:\s+`[^`]+`)?\s*\|\s*([1-5])\s*\|\s*`([^`]+)`",
            section_match.group(0),
        ):
            doc_map[f"tail.conn_{side.lower()}"][pin] = net
    if doc_map != EXPECTED_TAIL_MAP:
        errors.append(f"docs/1.25x10p/README.md: C4 tail table differs: {doc_map}")

    if not TAIL_HTML.is_file():
        errors.append(f"missing generated tail wiring HTML: {TAIL_HTML}")
    else:
        html_text = TAIL_HTML.read_text(encoding="utf-8")
        html_map = {"tail.conn_f": {}, "tail.conn_b": {}}
        for side, pin, net in re.findall(
            r'<g transform="translate\([^"]+\)">.*?'
            r'<text[^>]*>([FB])\.p([1-5])[^<]*</text>'
            r'<text[^>]*>([a-z0-9_]+)</text></g>',
            html_text,
            re.S,
        ):
            html_map[f"tail.conn_{side.lower()}"][pin] = net
        if html_map != EXPECTED_TAIL_MAP:
            errors.append(f"generated tail wiring HTML differs: {html_map}")

    if not TAIL_PNG.is_file():
        errors.append(f"missing generated tail pinout PNG: {TAIL_PNG}")
    else:
        header = TAIL_PNG.read_bytes()[:24]
        if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            errors.append("generated tail pinout is not a valid PNG")
        else:
            width, height = struct.unpack(">II", header[16:24])
            if width < 1200 or height < 450:
                errors.append(
                    f"generated tail pinout is too small for print: {width}x{height}"
                )

    step3_text = (SCRIPTS / "step3_import_netlist.py").read_text(encoding="utf-8")
    if "PAD_NETS" not in step3_text:
        errors.append("step3_import_netlist.py: reviewed PAD_NETS gate missing")
    return errors


def validate_board(board_path: Path, drc_path: Path | None) -> int:
    import pcbnew

    _source_guard()
    board = pcbnew.LoadBoard(str(board_path))
    errors: list[str] = _tail_source_errors()

    footprints = list(board.GetFootprints())
    addressed = [(_addr(fp), fp) for fp in footprints if _addr(fp)]
    by_addr = {addr: fp for addr, fp in addressed}
    if len(by_addr) != len(addressed):
        duplicates = sorted(
            addr for addr, _ in addressed
            if sum(candidate == addr for candidate, _ in addressed) > 1
        )
        fail(errors, f"duplicate atopile_address values: {sorted(set(duplicates))}")

    missing_addresses = sorted(set(PAD_NETS) - set(by_addr))
    unexpected_addresses = sorted(set(by_addr) - set(PAD_NETS))
    if missing_addresses:
        fail(errors, f"missing footprint addresses: {missing_addresses}")
    if unexpected_addresses:
        fail(errors, f"unexpected footprint addresses: {unexpected_addresses}")

    placement_snapshot_state = "pending"
    if PLACEMENT_SNAPSHOT.is_file():
        try:
            snapshot = json.loads(PLACEMENT_SNAPSHOT.read_text(encoding="utf-8"))
            entries = snapshot.get("placements", [])
            snapshot_by_addr = {
                str(entry.get("addr", "")): entry
                for entry in entries
                if isinstance(entry, dict) and entry.get("addr")
            }
            if (
                snapshot.get("schema_version") != 1
                or snapshot.get("component_count") != 64
                or len(entries) != 64
                or len(snapshot_by_addr) != 64
            ):
                fail(errors, "C4 placement snapshot schema/count is invalid")
            elif set(snapshot_by_addr) != set(by_addr):
                fail(errors, "C4 placement snapshot address set differs from board")
            else:
                for addr, entry in snapshot_by_addr.items():
                    fp = by_addr[addr]
                    pos = fp.GetPosition()
                    actual = {
                        "x": round(pcbnew.ToMM(pos.x), 6),
                        "y": round(pcbnew.ToMM(pos.y), 6),
                        "rot": round(fp.GetOrientationDegrees(), 4),
                        "flip": bool(fp.IsFlipped())
                        if hasattr(fp, "IsFlipped") else False,
                    }
                    for key in ("x", "y", "rot", "flip"):
                        if actual[key] != entry.get(key):
                            fail(
                                errors,
                                f"placement snapshot mismatch {addr}.{key}: "
                                f"board={actual[key]!r} snapshot={entry.get(key)!r}",
                            )
                placement_snapshot_state = "matched"
        except (AttributeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            fail(errors, f"cannot read C4 placement snapshot: {exc}")

    if len(footprints) != 64:
        fail(errors, f"expected 64 footprints, found {len(footprints)}")

    title_block = board.GetTitleBlock()
    if title_block.GetTitle() != "SmartPaddle Rigid PCB":
        fail(errors, f"expected C4 title, found {title_block.GetTitle()!r}")
    if title_block.GetRevision() != "C4":
        fail(errors, f"expected board revision C4, found {title_block.GetRevision()!r}")

    tracks_and_vias = list(board.GetTracks())
    if tracks_and_vias:
        fail(errors, f"manual-routing handoff must have 0 tracks/vias, found {len(tracks_and_vias)}")

    copper_zones = [
        board.GetArea(i) for i in range(board.GetAreaCount())
        if not board.GetArea(i).GetIsRuleArea()
    ]
    if copper_zones:
        fail(errors, f"manual-routing handoff must have 0 copper zones, found {len(copper_zones)}")

    for addr, pin_nets in PAD_NETS.items():
        fp = by_addr.get(addr)
        if fp is None:
            fail(errors, f"missing footprint address: {addr}")
            continue
        pads = list(fp.Pads())
        actual_pin_numbers = {pad.GetNumber() for pad in pads}
        expected_pin_numbers = set(pin_nets)
        if actual_pin_numbers != expected_pin_numbers:
            fail(
                errors,
                f"{addr}: pad set differs; expected {sorted(expected_pin_numbers)}, "
                f"found {sorted(actual_pin_numbers)}",
            )
        for pad in pads:
            pin = pad.GetNumber()
            if pin not in pin_nets:
                continue
            expected_net = pin_nets[pin]
            actual_net = pad.GetNetname()
            if actual_net != expected_net:
                fail(errors, f"{addr}.pad{pin}: expected {expected_net}, found {actual_net or '<none>'}")

    for addr in sorted(DNP_ADDRESSES):
        fp = by_addr.get(addr)
        if fp is None:
            continue
        if not fp.IsDNP():
            fail(errors, f"{addr}: expected KiCad DNP flag")
        if "DNP" not in fp.GetValue().upper():
            fail(errors, f"{addr}: value must identify DNP, found {fp.GetValue()!r}")

    for part in C4_PARTS:
        fp = by_addr.get(part.addr)
        if fp is None:
            continue
        if fp.GetReference() != part.ref:
            fail(errors, f"{part.addr}: expected ref {part.ref}, found {fp.GetReference()}")
        if fp.GetValue() != part.value:
            fail(errors, f"{part.addr}: expected value {part.value}, found {fp.GetValue()}")

    refs = {fp.GetReference() for fp in footprints}
    if "MCU_SGFK_C6" in refs:
        fail(errors, "C3 MCU_SGFK_C6 is still present")

    mcu = by_addr.get("mcu")
    if mcu is not None:
        mcu_pads = {pad.GetNumber(): pad.GetNetname() for pad in mcu.Pads()}
        occupied_psram_pads = {pin: mcu_pads.get(pin, "") for pin in ("28", "29", "30")}
        occupied_psram_pads = {pin: net for pin, net in occupied_psram_pads.items() if net}
        if occupied_psram_pads:
            fail(errors, f"N16R8-reserved GPIO35..37 pads are connected: {occupied_psram_pads}")

    for corner in ("tl", "tr", "bl", "br"):
        addr = f"pzt_frontend.jp_adc_{corner}"
        fp = by_addr.get(addr)
        if fp is not None and fp.GetValue() != "0R DNP":
            fail(errors, f"{addr} must remain 0R DNP, found {fp.GetValue()}")

    warning_count = 0
    unconnected_count = 0
    if drc_path is not None:
        report = json.loads(drc_path.read_text(encoding="utf-8"))
        violations = report.get("violations", [])
        drc_errors = [item for item in violations if item.get("severity") == "error"]
        warning_count = sum(item.get("severity") == "warning" for item in violations)
        unconnected_count = len(report.get("unconnected_items", []))
        if drc_errors:
            fail(errors, f"DRC has {len(drc_errors)} non-routing error violations")
        unexpected_warning_types = sorted({
            item.get("type", "<missing>")
            for item in violations
            if item.get("severity") == "warning"
            and item.get("type") not in ALLOWED_BASELINE_WARNING_TYPES
        })
        if unexpected_warning_types:
            fail(errors, f"DRC has unexpected warning types: {unexpected_warning_types}")

    if errors:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        return 1

    drc_summary = (
        f"DRC {warning_count} warnings + {unconnected_count} expected unrouted items"
        if drc_path is not None else "DRC skipped"
    )
    print(
        "C4 unrouted board OK: "
        f"{len(footprints)} footprints, {len(PAD_NETS)} checked addresses, "
        f"tail sources/assets matched, placement snapshot {placement_snapshot_state}, "
        f"0 tracks/vias, 0 copper zones, {drc_summary}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=BOARD)
    parser.add_argument("--drc", type=Path, default=DEFAULT_DRC)
    parser.add_argument("--skip-drc", action="store_true")
    args = parser.parse_args()
    return validate_board(args.board.resolve(), None if args.skip_drc else args.drc.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
