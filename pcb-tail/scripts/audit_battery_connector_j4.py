#!/usr/bin/env python3
"""Read-only audit for routed JST ACH J4 and the B3U-1000P SW1 replacement."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DEFAULT_PCB = REPO / "pcb-tail/layouts/default/default.kicad_pcb"
MAIN_ATO = REPO / "pcb-tail/main.ato"
PARTS_ATO = REPO / "pcb-tail/parts.ato"
FP_LIB_TABLE = REPO / "pcb-tail/layouts/default/fp-lib-table"
ACH_PDF = REPO / "docs/battery-connector-jst-ach-2p/JST-ACH-official.pdf"
ACH_STOCK_FOOTPRINT = REPO / (
    "docs/battery-connector-jst-ach-2p/kicad/"
    "JST_ACH_BM02B-ACHSS-GAN-ETF_1x02-1MP_P1.20mm_Vertical.kicad_mod"
)
B3U_PDF = REPO / "docs/tail-user-switch-b3u-1000p/Omron-B3U-A162-E1-07-official.pdf"
B3U_STOCK_FOOTPRINT = REPO / (
    "docs/tail-user-switch-b3u-1000p/kicad/SW_SPST_B3U-1000P.kicad_mod"
)
B3U_STOCK_MODEL = REPO / "docs/tail-user-switch-b3u-1000p/kicad/SW_SPST_B3U-1000P.step"
ACH_PREVIEW_SOURCE = REPO / (
    "docs/battery-connector-jst-ach-2p/kicad/"
    "JST_ACH_BM02B-ACHSS-GAN-ETF_simplified-preview.scad"
)
ACH_PREVIEW_MODEL = REPO / (
    "docs/battery-connector-jst-ach-2p/kicad/"
    "JST_ACH_BM02B-ACHSS-GAN-ETF_simplified-preview.wrl"
)

ACH_PDF_SHA256 = "d1f9e9375b1c0dfc4814d5f633997484d84da6c0b03f712104df3bbdf462131b"
ACH_STOCK_SHA256 = "dad2081506a292c544881eed161e70d1094ac79ea579526652e5616722d0942c"
B3U_STOCK_SHA256 = "cde2d6cafc390e73f300ce36157ec6d8933f1bd4d2aa4758a9aa98beee6aff1e"
B3U_PDF_SHA256 = "271b3d35eb58fac7449cb36bbe6a78b36439baa29281e74da83bede2b7ba8b01"
B3U_MODEL_SHA256 = "4b5ee4da023d76030db22a90f5835f3691d5e4e9fc41b3f37b2c5922c65d307b"
ACH_PREVIEW_SOURCE_SHA256 = "f203e87aa2c600fee3342089080623d4d68f6709496d9b5ed645d898a872d2d6"
ACH_PREVIEW_MODEL_SHA256 = "52ba2757e40cbaf3699a208c9adee2ff5a7624a1b3871bc1b1b0fd41a0180a6c"
J4_MODEL_PATH = (
    "${KIPRJMOD}/../../../docs/battery-connector-jst-ach-2p/kicad/"
    "JST_ACH_BM02B-ACHSS-GAN-ETF_simplified-preview.wrl"
)
SW1_MODEL_PATH = (
    "${KIPRJMOD}/../../../docs/tail-user-switch-b3u-1000p/kicad/"
    "SW_SPST_B3U-1000P.step"
)
J4_FOOTPRINT_ID = (
    "Connector_JST:"
    "JST_ACH_BM02B-ACHSS-GAN-ETF_1x02-1MP_P1.20mm_Vertical"
)
SW1_FOOTPRINT_ID = "Button_Switch_SMD:SW_SPST_B3U-1000P"


class AuditError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child_forms(text: str) -> list[tuple[str, int, int, str]]:
    """Return direct child S-expressions of the outermost expression."""

    root = text.find("(")
    if root < 0:
        raise AuditError("S-expression has no root")

    depth = 0
    child_start: int | None = None
    in_string = False
    escaped = False
    forms: list[tuple[str, int, int, str]] = []

    for index in range(root, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
            if depth == 2:
                child_start = index
        elif char == ")":
            if depth == 2 and child_start is not None:
                end = index + 1
                form = text[child_start:end]
                match = re.match(r"\(([^\s()]+)", form)
                if not match:
                    raise AuditError("could not parse child form name")
                forms.append((match.group(1), child_start, end, form))
                child_start = None
            depth -= 1
            if depth == 0:
                break

    if depth != 0:
        raise AuditError("unbalanced S-expression")
    return forms


def property_value(block: str, name: str) -> str | None:
    match = re.search(rf'\(property\s+"{re.escape(name)}"\s+"([^"]*)"', block)
    return match.group(1) if match else None


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def pad_forms(block: str, number: str) -> list[str]:
    return [
        form
        for name, _, _, form in child_forms(block)
        if name == "pad" and re.match(r'\(pad\s+"([^"]+)"', form.lstrip()).group(1) == number
    ]


def footprint_by_ref(forms: list[tuple[str, int, int, str]], ref: str):
    matches = [item for item in forms if item[0] == "footprint" and property_value(item[3], "Reference") == ref]
    expect(len(matches) == 1, f"expected one {ref} footprint, found {len(matches)}")
    return matches[0]


def audit(pcb_path: Path) -> None:
    text = pcb_path.read_text()
    forms = child_forms(text)
    footprints = [item for item in forms if item[0] == "footprint"]
    j4 = footprint_by_ref(forms, "J4")[3]
    sw1 = footprint_by_ref(forms, "SW1")[3]

    expect(j4.startswith(f'(footprint "{J4_FOOTPRINT_ID}"'), "J4 footprint library ID mismatch")
    expect(property_value(j4, "Value") == "BM02B-ACHSS-GAN-ETF", "J4 value mismatch")
    expect(property_value(j4, "atopile_address") == "j_bat", "J4 atopile_address mismatch")
    expect(re.search(r'^\s*\(layer "B\.Cu"\)$', j4, re.MULTILINE) is not None, "J4 must be on B.Cu")
    expect(
        re.search(r'^\s*\(at -2\.794 -5\.969 90\)$', j4, re.MULTILINE) is not None,
        "J4 routed pose mismatch",
    )
    expect(len(pad_forms(j4, "1")) == 1 and len(pad_forms(j4, "2")) == 1, "J4 signal pad set mismatch")
    expect(len(pad_forms(j4, "MP")) == 2, "J4 must have two unnumbered mechanical tabs")
    expect(f'(model "{J4_MODEL_PATH}"' in j4, "J4 docs-local preview model path mismatch")
    expect("(xyz 0.393701 0.393701 0.393701)" in j4, "J4 OpenSCAD VRML scale mismatch")
    j4_checks = {
        "1": ("-0.6 1.875 90", '12 "bat_p"'),
        "2": ("0.6 1.875 90", '10 "GND"'),
    }
    for number, (at, net) in j4_checks.items():
        pad = pad_forms(j4, number)[0]
        expect(re.match(rf'\(pad\s+"{number}"\s+smd\s+roundrect', pad.lstrip()) is not None, f"J4.{number} pad type mismatch")
        expect(f"(at {at})" in pad, f"J4.{number} local coordinate mismatch")
        expect("(size 0.6 0.85)" in pad, f"J4.{number} land mismatch")
        expect('(layers "B.Cu" "B.Mask" "B.Paste")' in pad, f"J4.{number} layer mismatch")
        expect(f"(net {net})" in pad, f"J4.{number} net mismatch")
    for pad in pad_forms(j4, "MP"):
        expect("(net " not in pad, "J4 MP must be NC")

    expect(sw1.startswith(f'(footprint "{SW1_FOOTPRINT_ID}"'), "SW1 footprint library ID mismatch")
    expect(property_value(sw1, "Value") == "B3U-1000P", "SW1 value mismatch")
    expect(property_value(sw1, "atopile_address") == "sw_user", "SW1 atopile_address mismatch")
    expect(re.search(r'^\s*\(layer "F\.Cu"\)$', sw1, re.MULTILINE) is not None, "SW1 must remain on F.Cu")
    expect(re.search(r'^\s*\(at -1\.651 -5\.461 -90\)$', sw1, re.MULTILINE) is not None, "SW1 pose changed")
    expect(f'(model "{SW1_MODEL_PATH}"' in sw1, "SW1 docs-local model path mismatch")
    sw1_checks = {
        "1": ("-1.7 0 270", '1 "user_btn"'),
        "2": ("1.7 0 270", '10 "GND"'),
    }
    for number, (at, net) in sw1_checks.items():
        pads = pad_forms(sw1, number)
        expect(len(pads) == 1, f"SW1.{number} missing or duplicated")
        pad = pads[0]
        expect(re.match(rf'\(pad\s+"{number}"\s+smd\s+rect', pad.lstrip()) is not None, f"SW1.{number} pad type mismatch")
        expect(f"(at {at})" in pad, f"SW1.{number} local coordinate mismatch")
        expect("(size 0.9 1.7)" in pad, f"SW1.{number} land mismatch")
        expect(f"(net {net})" in pad, f"SW1.{number} net mismatch")

    expect(len(footprints) == 25, f"expected 25 footprints, found {len(footprints)}")
    expect(sum(item[0] == "segment" for item in forms) == 367, "routed track count changed")
    expect(sum(item[0] == "via" for item in forms) == 58, "routed via count changed")
    expect(sum(item[0] == "zone" for item in forms) == 2, "zone count changed")

    main = MAIN_ATO.read_text()
    parts = PARTS_ATO.read_text()
    fp_lib = FP_LIB_TABLE.read_text()
    for fragment in (
        "j_bat = new JST_ACH_BM02B_ACHSS_GAN_ETF_2P_Battery",
        "sw_user = new Omron_B3U_1000P",
        "j_bat.BAT_P ~ bat_p",
        "j_bat.GND ~ gnd",
        "sw_user.a ~ user_btn",
        "sw_user.b ~ gnd",
    ):
        expect(fragment in main, f"main.ato missing: {fragment}")
    for fragment in (
        "component JST_ACH_BM02B_ACHSS_GAN_ETF_2P_Battery:",
        "component Omron_B3U_1000P:",
        "BAT_P ~ pin 1",
        "GND ~ pin 2",
        f'footprint = "{J4_FOOTPRINT_ID}"',
        f'footprint = "{SW1_FOOTPRINT_ID}"',
    ):
        expect(fragment in parts, f"parts.ato missing: {fragment}")
    expect('(lib (name "Connector_JST")' in fp_lib, "Connector_JST library is not registered")
    expect('(lib (name "Button_Switch_SMD")' in fp_lib, "Button_Switch_SMD library is not registered")

    expect(sha256(ACH_PDF) == ACH_PDF_SHA256, "archived JST ACH PDF checksum mismatch")
    expect(sha256(ACH_STOCK_FOOTPRINT) == ACH_STOCK_SHA256, "JST ACH stock footprint checksum mismatch")
    expect(sha256(ACH_PREVIEW_SOURCE) == ACH_PREVIEW_SOURCE_SHA256, "ACH preview source checksum mismatch")
    expect(sha256(ACH_PREVIEW_MODEL) == ACH_PREVIEW_MODEL_SHA256, "ACH preview model checksum mismatch")
    expect(sha256(B3U_PDF) == B3U_PDF_SHA256, "archived Omron B3U PDF checksum mismatch")
    expect(sha256(B3U_STOCK_FOOTPRINT) == B3U_STOCK_SHA256, "B3U stock footprint checksum mismatch")
    expect(sha256(B3U_STOCK_MODEL) == B3U_MODEL_SHA256, "B3U stock model checksum mismatch")

    print("J4 battery connector + SW1 switch audit")
    print(f"  PCB: {pcb_path}")
    print(f"  J4: {J4_FOOTPRINT_ID}, B.Cu, routed at (-2.794, -5.969, 90 deg)")
    print("  J4.1 = bat_p / BAT_P / red; J4.2 = GND / black; MP x2 = NC")
    print(f"  SW1: {SW1_FOOTPRINT_ID}, F.Cu, original pose (-1.651, -5.461, -90 deg)")
    print("  SW1.1 = user_btn; SW1.2 = GND")
    print("  J4/SW1 footprints, PDFs and 3D preview assets resolve from docs/")
    print("  routed PCB baseline: 25 footprints, 367 segments, 58 vias, 2 zones")
    print("AUDIT PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcb", type=Path, default=DEFAULT_PCB)
    args = parser.parse_args()
    try:
        audit(args.pcb.resolve())
    except (AuditError, FileNotFoundError, ValueError, AttributeError) as error:
        print(f"AUDIT FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
