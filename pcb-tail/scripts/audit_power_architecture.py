#!/usr/bin/env python3
"""Independent end-to-end audit of the unrouted M5 tail power redesign.

This deliberately checks design intent that KiCad DRC cannot infer: the
source-PDF identities, every physical pad-to-net assignment, true NC pads,
critical package geometry, unchanged legacy poses, and the explicit
non-manufacturing (zero-copper/new-parts-parked) state.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import hashlib
import math
import sys
from pathlib import Path

try:
    import pcbnew
except ImportError as exc:  # pragma: no cover - depends on KiCad runtime
    raise SystemExit(
        "pcbnew is unavailable; run with KiCad 9's bundled Python"
    ) from exc


# ===== 分区：常量/配置 =====
REPO = Path(__file__).resolve().parents[2]
PCB = REPO / "pcb-tail/layouts/default/default.kicad_pcb"
STAGING = REPO / "pcb-tail/layouts/staging/default.atopile.kicad_pcb"
MAIN_ATO = REPO / "pcb-tail/main.ato"
PARTS_ATO = REPO / "pcb-tail/parts.ato"

SOURCE_HASHES = {
    REPO / "docs/power-architecture-rework/sources/IP5305T-V1.4.pdf":
        "210568ac364ef2588792d879ffa6266ad7f70b84940bece5123ec86553d785b0",
    REPO / "docs/power-architecture-rework/sources/TPS2553-RevF.pdf":
        "56c62cd42a9b37ef3b680ab08b4921c3ec8cc997760ee403287dc4c1971852db",
    REPO / "docs/power-architecture-rework/sources/Coilcraft-XFL4020-Doc745.pdf":
        "6dca915ac1daa47210f7708a7540221ffef4f34a88a8621c94bd50cdf48647e6",
    REPO / "docs/usb-c-vertical-16p-short/Type-C-16PIN-vertical-H5.8-short-datasheet.pdf":
        "8d8f9afa88a8fc6049e041b519745d119b16f8eccdcf78de7f4090ee294dff23",
    REPO / "docs/battery-connector-jst-ach-2p/JST-ACH-official.pdf":
        "d1f9e9375b1c0dfc4814d5f633997484d84da6c0b03f712104df3bbdf462131b",
    REPO / "docs/tail-user-switch-b3u-1000p/Omron-B3U-A162-E1-07-official.pdf":
        "271b3d35eb58fac7449cb36bbe6a78b36439baa29281e74da83bede2b7ba8b01",
}

EXPECTED_PAD_NETS: dict[str, dict[str, str | None]] = {
    "c_ahct": {"1": "v5_sw_return", "2": "GND"},
    "c_bat": {"1": "bat_p", "2": "GND"},
    "c_led": {"1": "v5_sw_return", "2": "GND"},
    "c_system_limit_in": {"1": "vout_5v_raw", "2": "GND"},
    "c_system_limit_out": {"1": "vout_5v", "2": "GND"},
    "c_vbus_limit": {"1": "vbus", "2": "GND"},
    "c_vin": {"1": "vbus_limited", "2": "GND"},
    "c_vin_damp": {"1": "vin_damp_mid", "2": "GND"},
    "c_vout": {"1": "vout_5v_raw", "2": "GND"},
    "c_vout2": {"1": "vout_5v_raw", "2": "GND"},
    "d_key_isolate": {"1": "user_btn", "2": "pmic_key_isolated"},
    "j_bat": {"1": "bat_p", "2": "GND", "MP": None},
    "j_pwr": {
        "1": "vout_5v",
        "2": "GND",
        "3": "bat_p",
        "4": "v5_sw_return",
        "MP": None,
    },
    "j_sig": {
        "1": "usb_dn",
        "2": "usb_dp",
        "3": "user_btn",
        "4": "led_data",
        "MP": None,
    },
    "l_boost": {"1": "sw_node", "2": "bat_p"},
    "led_rgb": {
        "1": "led_dout",
        "2": "GND",
        "3": "led_din",
        "4": "v5_sw_return",
    },
    "led_stat": {"1": "GND", "2": "led_stat_a"},
    "r_cc1": {"1": "cc1", "2": "GND"},
    "r_cc2": {"1": "cc2", "2": "GND"},
    "r_key": {"1": "pmic_key", "2": "pmic_key_isolated"},
    "r_led": {"1": "led_ahct_y", "2": "led_din"},
    "r_led1": {"1": "pmic_led1", "2": "led_stat_a"},
    "r_led23": {"1": "pmic_led23", "2": "bat_p"},
    "r_system_ilim": {"1": "system_ilim", "2": "GND"},
    "r_vbus_ilim": {"1": "vbus_ilim", "2": "GND"},
    "r_vin_damp": {"1": "vbus_limited", "2": "vin_damp_mid"},
    "sw_user": {"1": "user_btn", "2": "GND"},
    "u_ahct": {
        "1": "GND",
        "2": "led_data",
        "3": "GND",
        "4": "led_ahct_y",
        "5": "v5_sw_return",
    },
    "u_esd": {
        "1": "usb_dp_conn",
        "2": "GND",
        "3": "usb_dn_conn",
        "4": "usb_dn",
        "5": "vbus",
        "6": "usb_dp",
    },
    "u_pmic": {
        "1": "vbus_limited",
        "2": "pmic_led1",
        "3": "pmic_led23",
        "4": "pmic_led23",
        "5": "pmic_key",
        "6": "bat_p",
        "7": "sw_node",
        "8": "vout_5v_raw",
        "9": "GND",
    },
    "u_system_limit": {
        "1": "vout_5v_raw",
        "2": "GND",
        "3": "vout_5v_raw",
        "4": None,
        "5": "system_ilim",
        "6": "vout_5v",
    },
    "u_vbus_limit": {
        "1": "vbus",
        "2": "GND",
        "3": "vbus",
        "4": None,
        "5": "vbus_ilim",
        "6": "vbus_limited",
    },
    "usb": {
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
        "S1": "GND",
    },
}

# Approved placement contract after the routed-board checkpoint.  Twenty-four
# legacy poses are unchanged; C6 alone moved +0.20/+0.25 mm to clear the larger
# corrected U3 and 1206 courtyards.  New parts are listed separately below.
ORIGINAL_POSES = {
    "c_ahct": (2.552997, -6.477002, 180.0, "F.Cu"),
    "c_led": (2.413000, -8.001000, 180.0, "B.Cu"),
    "c_bat": (8.001000, -1.397002, 0.0, "B.Cu"),
    "c_vin": (-2.325000, 5.675000, 90.0, "B.Cu"),
    "c_vin_damp": (-2.606002, 1.270002, 0.0, "B.Cu"),
    "c_vout": (9.277998, 5.457000, 0.0, "B.Cu"),
    "c_vout2": (12.318998, -0.066007, 90.0, "B.Cu"),
    "led_rgb": (2.454994, -3.783996, -90.0, "F.Cu"),
    "usb": (-6.858008, -0.381000, -90.0, "F.Cu"),
    "j_pwr": (-11.049000, -0.635000, -90.0, "B.Cu"),
    "j_sig": (6.858000, -5.503004, 180.0, "B.Cu"),
    "j_bat": (-2.794000, -5.969000, 90.0, "B.Cu"),
    "l_boost": (9.077998, 1.905000, 90.0, "B.Cu"),
    "led_stat": (-5.943500, -6.350000, 0.0, "F.Cu"),
    "r_cc1": (-2.984011, -0.762000, 0.0, "F.Cu"),
    "r_cc2": (-9.949009, 0.853001, -90.0, "F.Cu"),
    "r_led": (-1.206000, -2.413000, 0.0, "B.Cu"),
    "r_key": (5.270000, 0.889000, 0.0, "B.Cu"),
    "r_led1": (-7.303000, 6.222999, 180.0, "B.Cu"),
    "r_led23": (-5.325000, 1.675000, 90.0, "B.Cu"),
    "r_vin_damp": (-2.325000, 3.175000, 0.0, "B.Cu"),
    "sw_user": (-1.651000, -5.461000, -90.0, "F.Cu"),
    "u_ahct": (1.391500, -0.127000, 0.0, "B.Cu"),
    "u_esd": (-2.771016, 4.704503, -90.0, "F.Cu"),
    "u_pmic": (3.110000, 4.317997, 0.0, "B.Cu"),
}

NEW_POSES = {
    "u_vbus_limit": (7.000000, 4.800000, 0.0, "F.Cu"),
    "c_vbus_limit": (3.800000, 4.800000, 90.0, "F.Cu"),
    "r_vbus_ilim": (10.000000, 4.800000, 90.0, "F.Cu"),
    "u_system_limit": (8.500000, -4.500000, 0.0, "F.Cu"),
    "c_system_limit_in": (5.300000, -4.500000, 90.0, "F.Cu"),
    "c_system_limit_out": (11.700000, -5.200000, 90.0, "F.Cu"),
    "r_system_ilim": (11.700000, -1.500000, 0.0, "F.Cu"),
    "d_key_isolate": (7.500000, -8.300000, 0.0, "F.Cu"),
}

CRITICAL_FPIDS = {
    "u_pmic": "SmartPaddleTail:IP5305T_HSOP-8-1EP",
    "l_boost": "SmartPaddleTail:L_Coilcraft_XxL4020",
    "c_bat": "SmartPaddleTail:C_0805_2012Metric",
    "c_vin": "SmartPaddleTail:C_0805_2012Metric",
    "c_vin_damp": "SmartPaddleTail:C_0805_2012Metric",
    "c_vout": "Capacitor_SMD:C_1206_3216Metric",
    "c_vout2": "SmartPaddleTail:C_0805_2012Metric",
    "u_vbus_limit": "Package_TO_SOT_SMD:SOT-23-6",
    "u_system_limit": "Package_TO_SOT_SMD:SOT-23-6",
    "c_vbus_limit": "Capacitor_SMD:C_0603_1608Metric",
    "c_system_limit_in": "Capacitor_SMD:C_0603_1608Metric",
    "c_system_limit_out": "Capacitor_SMD:C_0603_1608Metric",
    "d_key_isolate": "Diode_SMD:D_SOD-323",
    "led_stat": "SmartPaddleTail:LED_0603_1608Metric",
    "r_led1": "SmartPaddleTail:R_0603_1608Metric",
    "r_led23": "SmartPaddleTail:R_0603_1608Metric",
}

CRITICAL_VALUES = {
    "u_pmic": "IP5305T",
    "l_boost": "XFL4020-222MEC 2.2uH",
    "c_bat": "10uF 10V X5R/X7R",
    "c_vin": "10uF 10V X5R/X7R",
    "c_vin_damp": "10uF 10V X5R/X7R",
    "c_vout": "22uF 10V X5R/X7R",
    "c_vout2": "10uF 10V X5R/X7R",
    "u_vbus_limit": "TPS2553DBVR",
    "u_system_limit": "TPS2553DBVR",
    "c_vbus_limit": "100nF 10V X7R",
    "c_system_limit_in": "100nF 10V X7R",
    "c_system_limit_out": "100nF 10V X7R",
    "r_vbus_ilim": "59k 1%",
    "r_system_ilim": "43.2k 1%",
    "d_key_isolate": "1N4148W",
    "led_stat": "LTST-C190KGKT",
    "r_led1": "200R",
    "r_led23": "1k",
}


# ===== 分区：私有成员 =====
class AuditError(RuntimeError):
    pass


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def _field(fp: "pcbnew.FOOTPRINT", name: str) -> str:
    return fp.GetFieldByName(name).GetText() if fp.HasFieldByName(name) else ""


def _by_address(board: "pcbnew.BOARD") -> dict[str, "pcbnew.FOOTPRINT"]:
    result = {}
    for fp in board.GetFootprints():
        address = _field(fp, "atopile_address")
        _expect(bool(address), f"{fp.GetReference()} lacks atopile_address")
        _expect(address not in result, f"duplicate atopile_address {address}")
        result[address] = fp
    return result


def _net_sets(fp: "pcbnew.FOOTPRINT") -> dict[str, set[str | None]]:
    result: dict[str, set[str | None]] = {}
    for pad in fp.Pads():
        number = pad.GetNumber()
        if not number:  # unnumbered paste aperture, not an electrical pad
            _expect(not pad.GetNetname(), f"{fp.GetReference()} paste aperture has a net")
            continue
        result.setdefault(number, set()).add(pad.GetNetname() or None)
    return result


def _close(actual: float, expected: float, tolerance: float = 1e-6) -> bool:
    return math.isclose(actual, expected, abs_tol=tolerance)


def _pose_mm(fp: "pcbnew.FOOTPRINT") -> tuple[float, float, float, str]:
    position = fp.GetPosition()
    return (
        pcbnew.ToMM(position.x),
        pcbnew.ToMM(position.y),
        fp.GetOrientationDegrees(),
        pcbnew.LayerName(fp.GetLayer()),
    )


def _expect_pose(actual: tuple[float, float, float, str], expected, address: str) -> None:
    _expect(
        actual[3] == expected[3]
        and all(_close(a, e) for a, e in zip(actual[:3], expected[:3])),
        f"{address} pose changed: {actual} != {expected}",
    )


def _audit_critical_geometry(parts: dict[str, "pcbnew.FOOTPRINT"]) -> None:
    for address, expected in CRITICAL_FPIDS.items():
        _expect(
            parts[address].GetFPIDAsString() == expected,
            f"{address} footprint ID mismatch",
        )
    for address, expected in CRITICAL_VALUES.items():
        _expect(parts[address].GetValue() == expected, f"{address} value mismatch")

    u3 = parts["u_pmic"]
    _expect(
        u3.GetFPIDAsString() == "SmartPaddleTail:IP5305T_HSOP-8-1EP",
        "U3 footprint ID mismatch",
    )
    u3_pads = [pad for pad in u3.Pads() if pad.GetNumber()]
    _expect(len([pad for pad in u3_pads if pad.GetNumber() == "9"]) == 1, "U3 EP duplicated")
    _expect(
        all(pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD for pad in u3_pads),
        "U3 must have no via-in-pad or through-hole pad",
    )
    ep = next(pad for pad in u3_pads if pad.GetNumber() == "9")
    _expect(
        (pcbnew.ToMM(ep.GetSize().x), pcbnew.ToMM(ep.GetSize().y)) == (2.41, 3.1),
        "U3 EP land must be 2.41 x 3.10 mm",
    )
    for number in map(str, range(1, 9)):
        pad = next(pad for pad in u3_pads if pad.GetNumber() == number)
        size = (pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y))
        _expect(size == (1.6, 0.6), f"U3.{number} land size {size} is wrong")

    inductor = parts["l_boost"]
    inductor_pads = [pad for pad in inductor.Pads() if pad.GetNumber()]
    _expect(len(inductor_pads) == 2, "L1 must have two lands")
    for pad in inductor_pads:
        _expect(
            (pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y))
            == (0.98, 3.4),
            "L1 land must be 0.98 x 3.40 mm",
        )
    p1, p2 = (pad.GetPosition() for pad in inductor_pads)
    center_distance = math.hypot(p1.x - p2.x, p1.y - p2.y) / 1_000_000
    _expect(_close(center_distance, 2.37), "L1 land centers must be 2.37 mm apart")

    c6 = parts["c_vout"]
    _expect(
        c6.GetFPIDAsString() == "Capacitor_SMD:C_1206_3216Metric",
        "C6 must use the 1206 footprint",
    )
    _expect(c6.GetValue() == "22uF 10V X5R/X7R", "C6 value/voltage/dielectric mismatch")

    for address in ("u_system_limit", "u_vbus_limit"):
        fp = parts[address]
        _expect(fp.GetValue() == "TPS2553DBVR", f"{address} MPN mismatch")
        _expect(_net_sets(fp)["4"] == {None}, f"{address} /FAULT must be true NC")
    _expect(parts["r_vbus_ilim"].GetValue() == "59k 1%", "USB ILIM resistor mismatch")
    _expect(parts["r_system_ilim"].GetValue() == "43.2k 1%", "system ILIM resistor mismatch")


def _audit_source_fragments() -> None:
    main = MAIN_ATO.read_text(encoding="utf-8")
    parts = PARTS_ATO.read_text(encoding="utf-8")
    required_main = (
        "u_vbus_limit.OUT ~ vbus_limited",
        "u_pmic.VIN ~ vbus_limited",
        "u_pmic.VOUT ~ vout_5v_raw",
        "u_system_limit.OUT ~ vout_5v",
        "d_key_isolate.anode ~ pmic_key_isolated",
        "d_key_isolate.cathode ~ user_btn",
        "u_pmic.LED1 ~ pmic_led1",
        "u_pmic.LED2 ~ pmic_led23",
        "u_pmic.LED3 ~ pmic_led23",
        "r_led1.p1 ~ pmic_led1",
        "led_stat.a ~ led_stat_a",
        "led_stat.c ~ gnd",
        "r_led23.p2 ~ bat_p",
        "j_pwr.p1 ~ vout_5v",
        "j_pwr.p3 ~ bat_p",
        "j_bat.BAT_P ~ bat_p",
        "j_bat.GND ~ gnd",
    )
    required_parts = (
        "component TPS2553DBV:",
        "LIMIT_SET ~ pin 5",
        "component Diode_1N4148W:",
        "anode ~ pin 2",
        "cathode ~ pin 1",
    )
    for fragment in required_main:
        _expect(fragment in main, f"main.ato missing {fragment}")
    for fragment in required_parts:
        _expect(fragment in parts, f"parts.ato missing {fragment}")


# ===== 分区：公开 API =====
def audit(require_route_free: bool = True) -> None:
    for path, expected in SOURCE_HASHES.items():
        _expect(path.is_file(), f"missing source PDF {path}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        _expect(actual == expected, f"source PDF checksum mismatch: {path}")

    _audit_source_fragments()
    _expect(PCB.is_file() and STAGING.is_file(), "PCB or staging board is missing")
    board = pcbnew.LoadBoard(str(PCB))
    parts = _by_address(board)
    _expect(set(parts) == set(EXPECTED_PAD_NETS), "33-part address inventory mismatch")
    _expect(len(list(board.GetFootprints())) == 33, "tail board must have 33 footprints")
    if require_route_free:
        _expect(not list(board.GetTracks()), "tail board must have 0 tracks and 0 vias")
        _expect(board.GetAreaCount() == 0, "tail board must have 0 zones")

    for address, expected in EXPECTED_PAD_NETS.items():
        actual = _net_sets(parts[address])
        expected_sets = {number: {net} for number, net in expected.items()}
        _expect(actual == expected_sets, f"{address} physical pad/net map mismatch: {actual}")

    for address, expected in ORIGINAL_POSES.items():
        _expect_pose(_pose_mm(parts[address]), expected, address)

    _expect(set(parts) - set(ORIGINAL_POSES) == set(NEW_POSES), "new-part set mismatch")
    for address, expected in NEW_POSES.items():
        _expect_pose(_pose_mm(parts[address]), expected, address)

    _audit_critical_geometry(parts)

    print("Tail power architecture end-to-end audit PASS")
    print("  6 archived primary PDFs match their locked SHA-256 hashes")
    print("  Atopile topology fragments and all 33 physical footprint maps agree")
    print("  24 legacy poses unchanged; approved C6 clearance shift verified")
    print("  8 new low-profile parts match their in-board F.Cu placement contract")
    print("  U3 no-via EP, XFL4020 exact land, power values, ILIM and deliberate NC pads verified")
    print("  IP5305T Figure-6 one-LED status path and populated LED/resistor values verified")
    if require_route_free:
        print("  0 tracks/vias; 0 zones: this board is intentionally NOT manufacturable")
    else:
        print("  copper allowed; electrical/physical semantics audited independently of routing")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-copper", action="store_true",
        help="skip the route-free-state assertion while retaining semantic checks",
    )
    args = parser.parse_args()
    try:
        audit(require_route_free=not args.allow_copper)
    except AuditError as exc:
        print(f"AUDIT FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
