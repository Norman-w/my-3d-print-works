#!/usr/bin/env python3
"""Independent end-to-end audit of the unrouted tail-board power redesign.

This deliberately checks design intent that KiCad DRC cannot infer: the
source-PDF identities, every physical pad-to-net assignment, true NC pads,
critical package geometry, unchanged legacy poses, and the explicit
non-manufacturing (zero-copper/new-parts-parked) state.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import hashlib
import json
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
MECHANICAL_JSON = REPO / "enclosure/stl/interference/tail_interference.json"
MOLEX_53261_SNAPSHOT = (
    REPO
    / "docs/molex-picoblade-53261-4p-horizontal/kicad/"
    "Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal.kicad_mod"
)
MOLEX_53261_SNAPSHOT_SHA256 = (
    "b177546df583a5dd26f4014428716db6733ab55483712201ca3afc315c415253"
)
MOLEX_53261_STEP_SNAPSHOT = (
    REPO
    / "docs/molex-picoblade-53261-4p-horizontal/kicad/"
    "Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal.step"
)
MOLEX_53261_STEP_SNAPSHOT_SHA256 = (
    "9c491a4fe35352e64f0576351c8f9e371e406bd158a0c6610bedb3421f8972d2"
)
EXPECTED_MATED_CONNECTOR_BOXES = {
    "J2": {
        "header_pcb_box_xy": (-13.900, -5.675, -8.700, 4.475),
        "housing_pcb_box_xy": (-8.850, -3.975, -4.900, 2.775),
        "housing_keepout_pcb_box_xy": (-9.100, -4.225, -4.650, 3.025),
    },
    "J3": {
        "header_pcb_box_xy": (1.225, -8.400, 11.375, -3.200),
        "housing_pcb_box_xy": (2.925, -3.350, 9.675, 0.600),
        "housing_keepout_pcb_box_xy": (2.675, -3.600, 9.925, 0.850),
    },
}

EXPECTED_SHELL_KEEPOUT_REFS = {
    "C6", "J2", "J3", "D2", "C9", "U2",
    "U4", "U5", "R9", "R5", "L1", "C7",
}

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

# Approved placement contract after the routed in-board candidate was promoted
# to the production tail board.  These coordinates lock the mechanically
# anchored connectors/user interfaces and the compact, DRC-clean functional
# islands that were manually completed before release validation.
ORIGINAL_POSES = {
	"c_ahct": (3.500000, -7.250000, -90.0, "F.Cu"),
	"c_led": (1.000000, -1.000000, 0.0, "F.Cu"),
	"c_bat": (-0.950000, 6.650000, 0.0, "B.Cu"),
	"c_vin": (6.600000, -1.049999, 180.0, "B.Cu"),
	"c_vin_damp": (3.000000, 7.050000, 180.0, "B.Cu"),
	"c_vout": (2.250000, -1.200000, 0.0, "B.Cu"),
	"c_vout2": (7.750000, -0.630000, 0.0, "F.Cu"),
    "led_rgb": (2.454994, -3.783996, -90.0, "F.Cu"),
    "usb": (-6.858008, -0.381000, -90.0, "F.Cu"),
    "j_pwr": (-11.300000, -0.600000, -90.0, "B.Cu"),
    "j_sig": (6.300000, -5.800000, 180.0, "B.Cu"),
    "j_bat": (-2.794000, -7.000000, 90.0, "B.Cu"),
	"l_boost": (-1.500000, 3.050000, -90.0, "B.Cu"),
    "led_stat": (-5.943500, -6.350000, 0.0, "F.Cu"),
	"r_cc1": (-2.984000, -0.762000, 0.0, "F.Cu"),
	"r_cc2": (-9.949000, 0.853000, -90.0, "F.Cu"),
	"r_led": (-5.000000, 4.400000, 90.0, "B.Cu"),
	"r_key": (-7.500000, -7.700000, 0.0, "B.Cu"),
	"r_led1": (-8.000000, 6.500000, 180.0, "B.Cu"),
	"r_led23": (-4.500000, 7.000000, 0.0, "B.Cu"),
	"r_vin_damp": (6.550000, 6.800000, 180.0, "B.Cu"),
    "sw_user": (-1.651000, -5.461000, -90.0, "F.Cu"),
	"u_ahct": (-2.750000, -1.750000, 90.0, "B.Cu"),
    "u_esd": (-2.771016, 4.704503, -90.0, "F.Cu"),
	"u_pmic": (4.800000, 3.000000, 180.0, "B.Cu"),
}

NEW_POSES = {
	"u_vbus_limit": (7.250000, 4.750000, 0.0, "F.Cu"),
	"c_vbus_limit": (4.130000, 4.750000, -90.0, "F.Cu"),
	"r_vbus_ilim": (10.370000, 4.750000, 90.0, "F.Cu"),
	"u_system_limit": (7.750000, -4.000000, 90.0, "F.Cu"),
	"c_system_limit_in": (4.980000, -2.200000, 90.0, "F.Cu"),
	"c_system_limit_out": (4.980000, -5.500000, 90.0, "F.Cu"),
	"r_system_ilim": (7.750000, -7.120000, 180.0, "F.Cu"),
	"d_key_isolate": (1.250000, -7.500000, 90.0, "F.Cu"),
}

CRITICAL_FPIDS = {
    "c_led": "SmartPaddleTail:C_0603_1608Metric",
    "j_pwr": "Connector_Molex:Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal",
    "j_sig": "Connector_Molex:Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal",
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
    "c_led": "100nF",
    "j_pwr": "Molex 53261-0471",
    "j_sig": "Molex 53261-0471",
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


def _close(actual: float, expected: float, tolerance: float = 5e-6) -> bool:
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


def _box_gap(a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]) -> float:
    dx = max(float(a[0]) - float(b[2]), float(b[0]) - float(a[2]), 0.0)
    dy = max(float(a[1]) - float(b[3]), float(b[1]) - float(a[3]), 0.0)
    return math.hypot(dx, dy)


def _audit_critical_geometry(parts: dict[str, "pcbnew.FOOTPRINT"]) -> None:
    for address, expected in CRITICAL_FPIDS.items():
        _expect(
            parts[address].GetFPIDAsString() == expected,
            f"{address} footprint ID mismatch",
        )
    for address, expected in CRITICAL_VALUES.items():
        _expect(parts[address].GetValue() == expected, f"{address} value mismatch")

    for address in ("j_pwr", "j_sig"):
        fp = parts[address]
        pads: dict[str, list["pcbnew.PAD"]] = {}
        for pad in fp.Pads():
            pads.setdefault(pad.GetNumber(), []).append(pad)
        _expect(set(pads) == {"1", "2", "3", "4", "MP"}, f"{address} pad inventory")
        _expect(len(pads["MP"]) == 2, f"{address} must have two SMT hold-downs")
        signal_pads = [pads[str(number)][0] for number in range(1, 5)]
        _expect(
            all(pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD for pad in signal_pads + pads["MP"]),
            f"{address} 53261 must be fully SMT",
        )
        _expect(
            all(
                sorted((pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y)))
                == [0.8, 1.6]
                for pad in signal_pads
            ),
            f"{address} signal lands must be 0.8 x 1.6 mm",
        )
        signal_centers = [pad.GetPosition() for pad in signal_pads]
        pitches = [
            math.hypot(a.x - b.x, a.y - b.y) / 1_000_000
            for a, b in zip(signal_centers, signal_centers[1:])
        ]
        _expect(all(_close(pitch, 1.25) for pitch in pitches), f"{address} pitch changed")
        _expect(
            all(
                sorted((pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y)))
                == [2.1, 3.0]
                for pad in pads["MP"]
            ),
            f"{address} hold-down lands must be 2.1 x 3.0 mm",
        )
        mount_centers = [pad.GetPosition() for pad in pads["MP"]]
        mount_spacing = math.hypot(
            mount_centers[0].x - mount_centers[1].x,
            mount_centers[0].y - mount_centers[1].y,
        ) / 1_000_000
        _expect(_close(mount_spacing, 8.85), f"{address} hold-down spacing changed")

    def anchor_distance(a: str, b: str) -> float:
        pa = parts[a].GetPosition()
        pb = parts[b].GetPosition()
        return math.hypot(pa.x - pb.x, pa.y - pb.y) / 1_000_000

    _expect(parts["c_led"].GetLayer() == pcbnew.F_Cu, "C2 must remain on F.Cu")
    # C1/C2 are electrically identical 100 nF V5_SW_RETURN decouplers.  The
    # routed compact placement may exchange their physical roles, so validate
    # the best distinct assignment instead of hard-coding one reference per IC.
    assignment_a = max(
        anchor_distance("c_ahct", "u_ahct"),
        anchor_distance("c_led", "led_rgb"),
    )
    assignment_b = max(
        anchor_distance("c_led", "u_ahct"),
        anchor_distance("c_ahct", "led_rgb"),
    )
    _expect(
        min(assignment_a, assignment_b) <= 4.00,
        "C1/C2 no longer provide distinct local decoupling for U1 and D1",
    )

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
        "component MolexPicoBlade_53261_4P_Horizontal:",
        "Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal",
    )
    for fragment in required_main:
        _expect(fragment in main, f"main.ato missing {fragment}")
    for fragment in required_parts:
        _expect(fragment in parts, f"parts.ato missing {fragment}")


def _audit_mechanical_contract(parts: dict[str, "pcbnew.FOOTPRINT"]) -> None:
    _expect(MECHANICAL_JSON.is_file(), "tail mechanical interference JSON is missing")
    facts = json.loads(MECHANICAL_JSON.read_text(encoding="utf-8"))
    _expect(
        facts.get("source_pcb") == "pcb-tail/layouts/default/default.kicad_pcb",
        "tail mechanical facts point at the wrong PCB",
    )

    button = facts.get("button", {})
    _expect(
        button.get("access_mode") == "pinhole_with_optional_retained_plunger",
        "SW1 access must use the verified pinhole baseline",
    )
    _expect(button.get("pinhole_ready") is True, "SW1 pinhole is not release-ready")
    _expect(_close(float(button.get("hole_d", 0)), 2.0), "SW1 pinhole must be 2.0 mm")
    _expect(button.get("plunger_optional") is True, "SW1 plunger must remain optional")
    _expect(
        float(button.get("plunger_flange_d", 0))
        > float(button.get("hole_d", 0)),
        "SW1 plunger flange cannot retain against the pinhole",
    )
    _expect(
        float(button.get("plunger_flange_pocket_d", 0))
        > float(button.get("plunger_flange_d", 0)),
        "SW1 flange recess has no diametral clearance",
    )

    keepouts = facts.get("component_keepouts", [])
    _expect(len(keepouts) == 12, "tail shell must carry exactly 12 local component keepouts")
    _expect(
        {item.get("ref") for item in keepouts} == EXPECTED_SHELL_KEEPOUT_REFS,
        "tail shell component-keepout reference set changed",
    )
    by_ref = {fp.GetReference(): fp for fp in parts.values()}
    for item in keepouts:
        ref = item["ref"]
        _expect(ref in by_ref, f"mechanical keepout {ref} is absent from current PCB")
        expected_pose = (
            float(item["x"]),
            float(item["y"]),
            float(item["rot_deg"]),
            str(item["layer"]),
        )
        _expect_pose(_pose_mm(by_ref[ref]), expected_pose, f"mechanical keepout {ref}")
        box = item.get("handle_box_xyz", [])
        _expect(
            len(box) == 6 and all(float(box[i + 3]) > float(box[i]) for i in range(3)),
            f"mechanical keepout {ref} has an invalid 3D box",
        )

    connectors = facts.get("harness_connectors", [])
    _expect(len(connectors) == 2, "mechanical facts must contain J2/J3 mated assemblies")
    by_connector_ref = {item.get("ref"): item for item in connectors}
    _expect(set(by_connector_ref) == {"J2", "J3"}, "mated connector reference set changed")
    for ref, expected_boxes in EXPECTED_MATED_CONNECTOR_BOXES.items():
        item = by_connector_ref[ref]
        _expect(item.get("part") == "Molex 53261-0471", f"{ref} header identity changed")
        _expect(item.get("mating_housing") == "Molex 51021-0400", f"{ref} mate changed")
        _expect(_close(float(item.get("mated_height", 0)), 3.40), f"{ref} mated height")
        _expect(_close(float(item.get("housing_height", 0)), 3.20), f"{ref} housing height")
        _expect(
            tuple(float(value) for value in item.get("header_local_box_xy", []))
            == (-5.075, -2.600, 5.075, 2.600),
            f"{ref} header local envelope changed",
        )
        _expect(
            tuple(float(value) for value in item.get("housing_local_box_xy", []))
            == (-3.375, -6.400, 3.375, -2.450),
            f"{ref} 51021 local envelope changed",
        )
        for key, expected in expected_boxes.items():
            actual = item.get(key, [])
            _expect(
                len(actual) == 4 and all(_close(float(a), e) for a, e in zip(actual, expected)),
                f"{ref} {key} changed: {actual} != {expected}",
            )
        handle_box = item.get("housing_keepout_handle_box_xyz", [])
        _expect(
            len(handle_box) == 6
            and all(float(handle_box[index + 3]) > float(handle_box[index]) for index in range(3)),
            f"{ref} inserted-housing keepout is invalid",
        )

    j4_box = facts.get("battery_connector", {}).get("body_pcb_box_xy", [])
    _expect(len(j4_box) == 4, "J4 body box is missing")
    _expect(
        _box_gap(by_connector_ref["J2"]["housing_pcb_box_xy"], j4_box) >= 0.50,
        "inserted J2 housing lacks 0.5 mm physical clearance from J4",
    )

    # J2's cable housing passes beside the two plated shell slots of J1.  DRC
    # cannot see this plastic-to-through-hole relationship, so bind the 0.3 mm
    # physical clearance directly to the actual KiCad pad geometry.
    usb_shell_pads = [pad for pad in parts["usb"].Pads() if pad.GetNumber() == "S1"]
    _expect(len(usb_shell_pads) == 2, "J1 shell-slot inventory changed")
    shell_boxes = []
    for pad in usb_shell_pads:
        box = pad.GetBoundingBox()
        shell_boxes.append(
            (
                pcbnew.ToMM(box.GetX()),
                pcbnew.ToMM(box.GetY()),
                pcbnew.ToMM(box.GetX() + box.GetWidth()),
                pcbnew.ToMM(box.GetY() + box.GetHeight()),
            )
        )
    _expect(
        min(
            _box_gap(by_connector_ref["J2"]["housing_pcb_box_xy"], shell_box)
            for shell_box in shell_boxes
        )
        >= 0.30,
        "inserted J2 housing is too close to a J1 plated shell slot",
    )


# ===== 分区：公开 API =====
def audit(require_route_free: bool = True) -> None:
    for path, expected in SOURCE_HASHES.items():
        _expect(path.is_file(), f"missing source PDF {path}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        _expect(actual == expected, f"source PDF checksum mismatch: {path}")
    _expect(MOLEX_53261_SNAPSHOT.is_file(), "missing archived Molex 53261 footprint")
    _expect(
        hashlib.sha256(MOLEX_53261_SNAPSHOT.read_bytes()).hexdigest()
        == MOLEX_53261_SNAPSHOT_SHA256,
        "archived Molex 53261 footprint checksum mismatch",
    )
    _expect(MOLEX_53261_STEP_SNAPSHOT.is_file(), "missing archived Molex 53261 STEP")
    _expect(
        hashlib.sha256(MOLEX_53261_STEP_SNAPSHOT.read_bytes()).hexdigest()
        == MOLEX_53261_STEP_SNAPSHOT_SHA256,
        "archived Molex 53261 STEP checksum mismatch",
    )

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
    _audit_mechanical_contract(parts)

    print("Tail power architecture end-to-end audit PASS")
    print("  6 archived primary PDFs plus Molex 53261 footprint/STEP snapshots match locked hashes")
    print("  Atopile topology fragments and all 33 physical footprint maps agree")
    print("  routed production poses and complete J2/J3/J4 connector reliefs are locked")
    print("  J2/J3 53261 land geometry, 1.25 mm pitch, hold-downs and pad nets verified")
    print("  C1/C2 provide distinct local decoupling; the compact U3/L1 power island is locked")
    print("  8 new low-profile parts match their in-board F.Cu placement contract")
    print("  U3 no-via EP, XFL4020 exact land, power values, ILIM and deliberate NC pads verified")
    print("  IP5305T Figure-6 one-LED status path and populated LED/resistor values verified")
    print("  SW1 pinhole, 12 component keepouts and both inserted 51021 envelopes match")
    print("  inserted J2 housing clears J4 and both J1 plated shell slots")
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
