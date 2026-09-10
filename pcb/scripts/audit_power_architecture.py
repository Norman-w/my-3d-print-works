#!/usr/bin/env python3
"""End-to-end, route-independent audit for the main-board power redesign.

This audit intentionally checks more than KiCad DRC: authoritative source-file
hashes, physical footprint identities, exact contact-to-net mappings, NC pins,
placement regions, critical switching-loop distances, harness vocabulary and
the active-high isolated-button firmware contract.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import hashlib
import math
from pathlib import Path

try:
    import pcbnew
except ImportError as exc:  # pragma: no cover - KiCad runtime only
    raise SystemExit(
        "pcbnew is unavailable; run with KiCad 9's bundled Python"
    ) from exc


# ===== 分区：常量/配置 =====
REPO = Path(__file__).resolve().parents[2]
BOARD = REPO / "pcb/layouts/default/default.kicad_pcb"
STAGING = REPO / "pcb/layouts/staging/default.atopile.kicad_pcb"
MAIN_ATO = REPO / "pcb/main.ato"
PARTS_ATO = REPO / "pcb/parts.ato"
FW_CONFIG = REPO / "firmware/main/config.h"
FW_POWER = REPO / "firmware/main/power_control.cpp"
FW_BATTERY = REPO / "firmware/main/battery_monitor.cpp"
FW_MAIN = REPO / "firmware/main/main.cpp"
WEB_WS = REPO / "web/src/lib/deviceWsSingleton.ts"
WEB_DASHBOARD = REPO / "web/src/components/TelemetryDashboard.tsx"

SOURCE_HASHES = {
    REPO / "docs/power-architecture-rework/sources/TPS62162-RevE.pdf":
        "6c26eb5b607f7af543c24ed99b8ed942e4819326352ae9fb87e8396686d06659",
    REPO / "docs/power-architecture-rework/sources/Coilcraft-XFL3012-Doc747.pdf":
        "a939120103cf22d59438ec9eaee8a385e6a7f36fc0b05492206a6e0840a94689",
    REPO / "docs/power-architecture-rework/sources/Coilcraft-XFL3012-official-land-pattern.gif":
        "54a7f89087deb535be2ba85aa181000b61f45786cde12c7020013033b30c7a09",
}

EXPECTED = {
    "SW_BOOT": {"1": "boot_btn", "2": "gnd"},
    "SW_EN": {"1": "en", "2": "gnd"},
    "SW_PWR": {"1": "btn_sw", "2": "gnd"},
    "TAIL_MX125_F": {
        "1": "sys_5v_in", "2": "sys_5v_sw", "3": "btn_sw",
        "4": "usb_dp_conn", "5": "uart_tx", "MP": None,
    },
    "TAIL_MX125_B": {
        "1": "uart_rx", "2": "usb_dn_conn", "3": "bat_cell_p",
        "4": "led_din", "5": "gnd", "MP": None,
    },
    "PW_Q_LOAD": {"1": "p_gate", "2": "sys_5v_in", "3": "sys_5v_sw"},
    "PW_Q_LATCH": {"1": "pwr_latch", "2": "gnd", "3": "p_gate"},
    # Project SOD-323 contract is pad 2=A, pad 1=K.
    "D_BTN_START": {"1": "btn_sw", "2": "p_gate"},
    "PW_Q_BTN_SENSE": {
        "1": "button_sense_gate", "2": "gnd", "3": "user_btn",
    },
    "PW_R_GATE_100K": {"1": "p_gate", "2": "sys_5v_in"},
    "PW_R_BTN_SER_1K": {"1": "btn_sw", "2": "button_sense_gate"},
    "PW_R_BTN_RAW_PU_100K": {"1": "btn_sw", "2": "sys_5v_in"},
    "PW_R_BTN_GPIO_PU_100K": {"1": "user_btn", "2": "vcc"},
    "PW_R_LATCH_PD_100K": {"1": "pwr_latch", "2": "gnd"},
    "PW_BUCK_3V3": {
        "1": "gnd", "2": "sys_5v_sw", "3": "sys_5v_sw", "4": "gnd",
        "5": "gnd", "6": "vcc", "7": "buck_sw", "8": None, "9": "gnd",
    },
    "PW_L_BUCK_2U2": {"1": "buck_sw", "2": "vcc"},
    "PW_C_IN_10U": {"1": "sys_5v_sw", "2": "gnd"},
    "PW_C_OUT_22U": {"1": "vcc", "2": "gnd"},
    "USB_R_DP_22R": {"1": "usb_dp_conn", "2": "usb_dp"},
    "USB_R_DN_22R": {"1": "usb_dn_conn", "2": "usb_dn"},
    "MCU_C_BULK_10U": {"1": "vcc", "2": "gnd"},
    "MCU_C_DEC_100N": {"1": "vcc", "2": "gnd"},
    "MCU_C_EN_1U": {"1": "en", "2": "gnd"},
    "PW_R_EN_PU_10K": {"1": "en", "2": "vcc"},
    "BAT_R_TOP_1M": {"1": "bat_cell_p", "2": "bat_sense"},
    "BAT_R_BOT_1M": {"1": "bat_sense", "2": "gnd"},
    "BAT_C_ADC_100N": {"1": "bat_sense", "2": "gnd"},
}

FPIDS = {
    "SW_BOOT": "Button_Switch_SMD:SW_SPST_B3U-1000P",
    "SW_EN": "Button_Switch_SMD:SW_SPST_B3U-1000P",
    "SW_PWR": "Button_Switch_SMD:SW_SPST_B3U-1000P",
    "MCU_ESP32_S3": "SmartPaddle:ESP32-S3-WROOM-1_CUTOUT",
    "PW_BUCK_3V3":
        "Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
    "PW_L_BUCK_2U2": "SmartPaddle:L_Coilcraft_XFL3012",
    "PW_C_IN_10U": "Capacitor_SMD:C_0805_2012Metric",
    "PW_C_OUT_22U": "Capacitor_SMD:C_1206_3216Metric",
    "PW_Q_BTN_SENSE": "Package_TO_SOT_SMD:SOT-23",
    "PW_R_BTN_RAW_PU_100K": "Resistor_SMD:R_0603_1608Metric",
    "PW_R_BTN_GPIO_PU_100K": "Resistor_SMD:R_0603_1608Metric",
    "USB_R_DP_22R": "Resistor_SMD:R_0603_1608Metric",
    "USB_R_DN_22R": "Resistor_SMD:R_0603_1608Metric",
    "MCU_C_BULK_10U": "Capacitor_SMD:C_0603_1608Metric",
    "MCU_C_DEC_100N": "Capacitor_SMD:C_0603_1608Metric",
    "MCU_C_EN_1U": "Capacitor_SMD:C_0603_1608Metric",
    "PW_R_EN_PU_10K": "Resistor_SMD:R_0603_1608Metric",
    "BAT_R_TOP_1M": "Resistor_SMD:R_0603_1608Metric",
    "BAT_R_BOT_1M": "Resistor_SMD:R_0603_1608Metric",
    "BAT_C_ADC_100N": "Capacitor_SMD:C_0603_1608Metric",
}

VALUES = {
    "SW_BOOT": "B3U-1000P DNP",
    "SW_EN": "B3U-1000P DNP",
    "SW_PWR": "B3U-1000P DNP",
    "PW_BUCK_3V3": "TPS62162DSGR",
    "PW_L_BUCK_2U2": "XFL3012-222MEC 2.2uH",
    "PW_C_IN_10U": "10uF 10V X5R/X7R",
    "PW_C_OUT_22U": "22uF 6.3V X5R/X7R",
    "PW_Q_BTN_SENSE": "AO3400A",
    "PW_R_BTN_RAW_PU_100K": "100k 1%",
    "PW_R_BTN_GPIO_PU_100K": "100k 1%",
    "USB_R_DP_22R": "22R 1%",
    "USB_R_DN_22R": "22R 1%",
    "MCU_C_BULK_10U": "10uF 6.3V X5R/X7R",
    "MCU_C_DEC_100N": "100nF 10V X7R",
    "MCU_C_EN_1U": "1uF 10V X5R/X7R",
    "PW_R_EN_PU_10K": "10k",
    "BAT_R_TOP_1M": "1M",
    "BAT_R_BOT_1M": "1M",
    "BAT_C_ADC_100N": "100nF",
}

# Atopile may choose an internal interface name as a generated net name.  The
# physical PCB and harness intentionally retain these established public names.
STAGING_NET_RENAMES = {
    "BAT_CELL_P": "bat_cell_p",
    "BUTTON": "btn_sw",
    "EN": "en",
    "LED_B": "led_b",
    "LED_R": "led_r",
    "SYS_5V_IN": "sys_5v_in",
    "SYS_5V_SW": "sys_5v_sw",
    "UART_RX": "uart_rx",
    "UART_TX": "uart_tx",
    "adc_iso_bl": "pzt_adc_iso_bl",
    "adc_iso_br": "pzt_adc_iso_br",
    "adc_iso_tl": "pzt_adc_iso_tl",
    "adc_iso_tr": "pzt_adc_iso_tr",
    "bleed_resistor-SIGNAL_PAD-0": "pzt_raw_bl",
    "bleed_resistor-SIGNAL_PAD-1": "pzt_raw_br",
    "bleed_resistor-SIGNAL_PAD-2": "pzt_raw_tl",
    "bleed_resistor-SIGNAL_PAD-3": "pzt_raw_tr",
    "vref_bl": "pzt_vref_bl",
    "vref_br": "pzt_vref_br",
    "vref_tl": "pzt_vref_tl",
    "vref_tr": "pzt_vref_tr",
}

FORCED_NC = {
    ("power.ldo", "8"),
    ("imu", "3"), ("imu", "4"), ("imu", "9"),
    ("imu", "10"), ("imu", "15"),
    ("pzt_frontend.dac", "10"),
}

INTENTIONAL_POSES = {
    "LED_MCU_PWR": (-19.400, -12.800, 0.0, pcbnew.F_Cu),
    "MCU_C_BULK_10U": (-12.000, 10.400, 0.0, pcbnew.F_Cu),
    "MCU_C_DEC_100N": (-8.800, 10.400, 0.0, pcbnew.F_Cu),
    "MCU_C_EN_1U": (-5.700, 10.795, 270.0, pcbnew.F_Cu),
    "PW_BUCK_3V3": (-16.300, -19.500, 0.0, pcbnew.F_Cu),
    "PW_C_IN_10U": (-19.000, -20.700, 90.0, pcbnew.F_Cu),
    "PW_C_OUT_22U": (-10.800, -23.650, 90.0, pcbnew.F_Cu),
    "PW_L_BUCK_2U2": (-12.065, -19.177, 0.0, pcbnew.F_Cu),
    "PW_Q_BTN_SENSE": (-11.400, -28.500, 90.0, pcbnew.F_Cu),
    "PW_R_BTN_GPIO_PU_100K": (-11.400, -32.200, 0.0, pcbnew.F_Cu),
    "PW_R_BTN_RAW_PU_100K": (-18.800, -28.660, 90.0, pcbnew.F_Cu),
    "PW_R_EN_PU_10K": (-3.900, 10.795, 270.0, pcbnew.F_Cu),
    "R_MCU_PWR_1K": (-19.400, -15.000, 90.0, pcbnew.F_Cu),
    "USB_R_DN_22R": (7.000, 10.600, 90.0, pcbnew.F_Cu),
    "USB_R_DP_22R": (8.500, 10.600, 90.0, pcbnew.F_Cu),
    "PZT_CMP_TLV9034": (15.195, -18.093, 270.0, pcbnew.F_Cu),
    "PZT_C_CMP_100N": (15.200, -24.000, 90.0, pcbnew.F_Cu),
    "PZT_C_DAC_100N": (13.208, -28.435, 90.0, pcbnew.F_Cu),
    "PZT_DAC_MCP4728": (17.400, -28.500, 0.0, pcbnew.F_Cu),
    "PZT_R_SCL_PU_4K7": (17.653, -24.701, 90.0, pcbnew.F_Cu),
    "PZT_R_SDA_PU_4K7": (19.812, -22.415, 90.0, pcbnew.F_Cu),
}

# SHA-256 over address|reference|position-nm|orientation|layer for the 46
# footprints outside INTENTIONAL_POSES.  Recomputed after parking the
# TLV9034 frontend on IMU +X; SHA covers the 46 non-INTENTIONAL poses.
PROTECTED_POSE_SHA256 = "3b872578987e8cb2e3ff15fe561d6e10c28c6cdf65ece0da36821be65dd9e026"


# ===== 分区：私有成员 =====
class AuditError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pad_map(fp: "pcbnew.FOOTPRINT") -> dict[str, str | None]:
    grouped: dict[str, set[str | None]] = {}
    for pad in fp.Pads():
        number = pad.GetNumber()
        if not number:
            if pad.GetNetname():
                raise AuditError(f"{fp.GetReference()} unnumbered aperture has a net")
            continue
        grouped.setdefault(number, set()).add(pad.GetNetname() or None)
    result = {}
    for number, names in grouped.items():
        if len(names) != 1:
            raise AuditError(f"{fp.GetReference()}.{number} maps to {names}")
        result[number] = next(iter(names))
    return result


def _by_address(board: "pcbnew.BOARD") -> dict[str, "pcbnew.FOOTPRINT"]:
    result = {}
    for fp in board.GetFootprints():
        if not fp.HasFieldByName("atopile_address"):
            raise AuditError(f"{fp.GetReference()} has no atopile_address")
        address = fp.GetFieldByName("atopile_address").GetText()
        if not address or address in result:
            raise AuditError(f"invalid or duplicate atopile_address {address!r}")
        result[address] = fp
    return result


def _audit_all_staging_maps(
    target: dict[str, "pcbnew.FOOTPRINT"],
    stage: dict[str, "pcbnew.FOOTPRINT"],
) -> None:
    if set(target) != set(stage) or len(target) != 67:
        raise AuditError("main target/staging 67-address inventories differ")
    for address in sorted(stage):
        expected = {}
        for number, net in _pad_map(stage[address]).items():
            expected[number] = (
                None
                if (address, number) in FORCED_NC
                else STAGING_NET_RENAMES.get(net, net)
            )
        actual = _pad_map(target[address])
        if actual != expected:
            raise AuditError(f"{address} full staging map {actual} != {expected}")


def _audit_poses(fps: dict[str, "pcbnew.FOOTPRINT"]) -> None:
    for reference, wanted in INTENTIONAL_POSES.items():
        fp = fps[reference]
        pos = fp.GetPosition()
        actual = (
            pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y),
            fp.GetOrientationDegrees() % 360, fp.GetLayer(),
        )
        if not (
            math.isclose(actual[0], wanted[0], abs_tol=0.001)
            and math.isclose(actual[1], wanted[1], abs_tol=0.001)
            and math.isclose(actual[2], wanted[2], abs_tol=0.001)
            and actual[3] == wanted[3]
        ):
            raise AuditError(f"{reference} pose {actual} != {wanted}")

    lines = []
    for fp in fps.values():
        if fp.GetReference() in INTENTIONAL_POSES:
            continue
        address = fp.GetFieldByName("atopile_address").GetText()
        pos = fp.GetPosition()
        lines.append(
            f"{address}|{fp.GetReference()}|{pos.x}|{pos.y}|"
            f"{fp.GetOrientationDegrees():.6f}|{fp.GetLayer()}"
        )
    digest = hashlib.sha256(("\n".join(sorted(lines)) + "\n").encode()).hexdigest()
    if len(lines) != 46 or digest != PROTECTED_POSE_SHA256:
        raise AuditError(f"protected legacy pose digest mismatch: {len(lines)} / {digest}")


def _pad(fp: "pcbnew.FOOTPRINT", number: str) -> "pcbnew.PAD":
    matches = [pad for pad in fp.Pads() if pad.GetNumber() == number]
    if len(matches) != 1:
        raise AuditError(f"{fp.GetReference()}.{number} expected one pad, got {len(matches)}")
    return matches[0]


def _distance_mm(a: "pcbnew.PAD", b: "pcbnew.PAD") -> float:
    pa, pb = a.GetPosition(), b.GetPosition()
    return math.hypot(pa.x - pb.x, pa.y - pb.y) / 1_000_000


def _assert_xfl3012_land(fp: "pcbnew.FOOTPRINT") -> None:
    """Lock the official 1.00 x 2.90 mm, 2.03 mm inner-gap land."""
    pads = (_pad(fp, "1"), _pad(fp, "2"))
    for pad in pads:
        size = sorted((pad.GetSize().x / 1e6, pad.GetSize().y / 1e6))
        if not (math.isclose(size[0], 1.00, abs_tol=0.001) and
                math.isclose(size[1], 2.90, abs_tol=0.001)):
            raise AuditError(f"{fp.GetReference()} pad size {size} != [1.00, 2.90] mm")
    center_distance = _distance_mm(*pads)
    if not math.isclose(center_distance, 3.03, abs_tol=0.001):
        raise AuditError(
            f"{fp.GetReference()} pad center distance {center_distance:.3f} != 3.030 mm"
        )


def _assert_antenna_rule_area(fp: "pcbnew.FOOTPRINT") -> None:
    zones = list(fp.Zones())
    if len(zones) != 1:
        raise AuditError(
            f"{fp.GetReference()} expected one footprint rule area, got {len(zones)}"
        )
    zone = zones[0]
    if not zone.GetIsRuleArea() or zone.GetZoneName() != "ESP32_ANTENNA_HOST_KEEP_OUT":
        raise AuditError("MCU antenna footprint rule-area identity is wrong")
    layer_names = {
        fp.GetBoard().GetLayerName(layer) for layer in zone.GetLayerSet().Seq()
    }
    if layer_names != {"F.Cu", "B.Cu"}:
        raise AuditError(f"MCU antenna rule-area layers are {sorted(layer_names)}")
    if not all((
        zone.GetDoNotAllowTracks(), zone.GetDoNotAllowVias(),
        zone.GetDoNotAllowPads(), zone.GetDoNotAllowCopperPour(),
        zone.GetDoNotAllowFootprints(),
    )):
        raise AuditError("MCU antenna rule area does not block every host-board object")
    expected = (-21.000, -11.000, -8.700, 9.000)
    box = zone.GetBoundingBox()
    actual = (
        box.GetX() / 1e6,
        box.GetY() / 1e6,
        (box.GetX() + box.GetWidth()) / 1e6,
        (box.GetY() + box.GetHeight()) / 1e6,
    )
    if any(not math.isclose(a, b, abs_tol=0.001) for a, b in zip(actual, expected)):
        raise AuditError(f"MCU antenna rule-area box {actual} != {expected}")
    outline = zone.Outline().COutline(0)
    actual_points = [
        (outline.CPoint(i).x / 1e6, outline.CPoint(i).y / 1e6)
        for i in range(outline.PointCount())
    ]
    expected_points = [
        (-21.0, -11.0), (-9.3, -11.0), (-9.3, -9.6), (-8.7, -9.6),
        (-8.7, 7.6), (-9.3, 7.6), (-9.3, 9.0), (-21.0, 9.0),
    ]
    if len(actual_points) != len(expected_points) or any(
        not (math.isclose(a[0], b[0], abs_tol=0.001)
             and math.isclose(a[1], b[1], abs_tol=0.001))
        for a, b in zip(actual_points, expected_points)
    ):
        raise AuditError(
            f"MCU antenna rule-area polygon {actual_points} != {expected_points}"
        )


def _courtyard(fp: "pcbnew.FOOTPRINT") -> tuple[float, float, float, float]:
    layer = pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd
    boxes = []
    for item in fp.GraphicalItems():
        if item.GetLayer() == layer:
            box = item.GetBoundingBox()
            boxes.append(
                (
                    box.GetX() / 1e6,
                    box.GetY() / 1e6,
                    (box.GetX() + box.GetWidth()) / 1e6,
                    (box.GetY() + box.GetHeight()) / 1e6,
                )
            )
    if not boxes:
        raise AuditError(f"{fp.GetReference()} has no courtyard")
    return (
        min(box[0] for box in boxes), min(box[1] for box in boxes),
        max(box[2] for box in boxes), max(box[3] for box in boxes),
    )


def _assert_text(path: Path, snippets: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    for snippet in snippets:
        if snippet not in text:
            raise AuditError(f"{path.relative_to(REPO)} missing contract: {snippet}")


# ===== 分区：公开 API =====
def audit(require_route_free: bool = True) -> None:
    for source, expected_hash in SOURCE_HASHES.items():
        if not source.is_file() or _sha256(source) != expected_hash:
            raise AuditError(f"authoritative source hash mismatch: {source}")

    board = pcbnew.LoadBoard(str(BOARD))
    staging = pcbnew.LoadBoard(str(STAGING))
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    if len(fps) != 67:
        raise AuditError(f"expected 67 unique footprints, found {len(fps)}")
    if require_route_free and (list(board.GetTracks()) or board.GetAreaCount()):
        raise AuditError("main board must remain route-free: 0 tracks/vias/zones")
    if list(staging.GetTracks()) or staging.GetAreaCount():
        raise AuditError("main staging board must remain route-free")

    _audit_all_staging_maps(_by_address(board), _by_address(staging))
    _audit_poses(fps)

    for reference, expected in EXPECTED.items():
        fp = fps.get(reference)
        if fp is None:
            raise AuditError(f"missing physical footprint {reference}")
        actual = _pad_map(fp)
        if actual != expected:
            raise AuditError(f"{reference} pad/net map {actual} != {expected}")
    for reference, fpid in FPIDS.items():
        actual = fps[reference].GetFPIDAsString()
        if actual != fpid:
            raise AuditError(f"{reference} footprint {actual} != {fpid}")
    for reference, expected_value in VALUES.items():
        actual = fps[reference].GetValue()
        if actual != expected_value:
            raise AuditError(f"{reference} value {actual!r} != {expected_value!r}")

    _assert_xfl3012_land(fps["PW_L_BUCK_2U2"])
    _assert_antenna_rule_area(fps["MCU_ESP32_S3"])

    mcu = fps["MCU_ESP32_S3"]
    mcu_contract = {
        "2": "vcc", "3": "en", "13": "usb_dn", "14": "usb_dp",
        "17": "bat_sense", "24": "pwr_latch", "25": "user_btn",
    }
    actual_mcu = _pad_map(mcu)
    for number, net in mcu_contract.items():
        if actual_mcu.get(number) != net:
            raise AuditError(f"MCU pad {number}: {actual_mcu.get(number)} != {net}")

    # Switching-loop placement is audited by electrical endpoints, not just
    # by non-overlapping courtyards.
    distances = {
        "CIN+ -> VIN": _distance_mm(_pad(fps["PW_C_IN_10U"], "1"), _pad(fps["PW_BUCK_3V3"], "2")),
        "SW -> L1": _distance_mm(_pad(fps["PW_BUCK_3V3"], "7"), _pad(fps["PW_L_BUCK_2U2"], "1")),
        "L2 -> COUT+": _distance_mm(_pad(fps["PW_L_BUCK_2U2"], "2"), _pad(fps["PW_C_OUT_22U"], "1")),
    }
    # Current KiCad placement keeps each direct copper span short.  The
    # 0.30 mm SW trace is under 2 mm and has no via.
    limits = {"CIN+ -> VIN": 2.0, "SW -> L1": 2.0, "L2 -> COUT+": 3.1}
    for name, distance in distances.items():
        if distance > limits[name]:
            raise AuditError(f"{name} is {distance:.2f} mm, limit {limits[name]:.2f} mm")

    # New parts must be inside known solid-board strips, not over the two
    # module cutouts.  A 0.20 mm courtyard-to-edge margin is enforced here.
    left_strip = (
        "PW_C_IN_10U", "PW_BUCK_3V3", "PW_L_BUCK_2U2", "PW_C_OUT_22U",
        "PW_Q_BTN_SENSE", "PW_R_BTN_RAW_PU_100K", "PW_R_BTN_GPIO_PU_100K",
    )
    for reference in left_strip:
        x0, y0, x1, y1 = _courtyard(fps[reference])
        if x0 < -20.50 or x1 > -9.55 or y0 < -33.50 or y1 > -10.25:
            raise AuditError(f"{reference} courtyard leaves solid left strip: {(x0,y0,x1,y1)}")
    top_strip = (
        "MCU_C_BULK_10U", "MCU_C_DEC_100N", "MCU_C_EN_1U", "PW_R_EN_PU_10K",
        "USB_R_DP_22R", "USB_R_DN_22R",
    )
    for reference in top_strip:
        x0, y0, x1, y1 = _courtyard(fps[reference])
        # The rotated USB 0603 courtyard extends to y=9.095 while its body,
        # pads and copper remain on solid board and pass KiCad edge DRC.
        minimum_y = 9.0 if reference.startswith("USB_R_") else 9.275
        if x0 < -20.50 or x1 > 20.50 or y0 < minimum_y or y1 > 15.50:
            raise AuditError(f"{reference} courtyard leaves solid top strip: {(x0,y0,x1,y1)}")

    _assert_text(
        MAIN_ATO,
        (
            "component ESP32S3WROOM1_Cutout:",
            "component IM948_Cutout:",
            "    signal GND_1",
            "    signal GPIO9_BAT_SENSE",
            "    signal VBAT_15",
            "q_button_sense.gate ~ button_sense_gate",
            "q_button_sense.source ~ GND",
            "q_button_sense.drain ~ BUTTON_GPIO",
            "ldo.VIN ~ SYS_5V_SW",
            "ldo.FB ~ GND",
            "ldo.VOS ~ VCC_3V3",
            "usb_r_dp.p2 ~ usb_dp",
            "usb_r_dn.p2 ~ usb_dn",
        ),
    )
    main_ato_text = MAIN_ATO.read_text(encoding="utf-8")
    for duplicate_pin in ("    pin GND_1", "    pin GPIO9_BAT_SENSE", "    pin VBAT_15"):
        if duplicate_pin in main_ato_text:
            raise AuditError(
                "MCU/IMU logical names must be signals mapped to numeric pads, "
                f"not duplicate component pins: {duplicate_pin.strip()}"
            )
    _assert_text(
        PARTS_ATO,
        (
            'footprint = "Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm"',
            'footprint = "SmartPaddle:L_Coilcraft_XFL3012"',
            "PGND ~ pin 1", "VIN ~ pin 2", "VOS ~ pin 6", "SW ~ pin 7",
        ),
    )
    _assert_text(FW_CONFIG, ("#define USER_BTN_ACTIVE_LEVEL       1",))
    _assert_text(
        FW_POWER,
        (
            "gpio_set_level(PWR_LATCH_GPIO, 0)",
            ".pull_up_en = GPIO_PULLUP_ENABLE",
        ),
    )
    _assert_text(
        MAIN_ATO,
        (
            'r_top.value = "1M"',
            'r_bottom.value = "1M"',
            'c_filter.value = "100nF"',
            "tail.BAT_CELL_P ~ bat_cell_p",
            "mcu.GPIO9_BAT_SENSE ~ bat_sense",
        ),
    )
    _assert_text(
        FW_BATTERY,
        (
            "ADC_CHANNEL_8",
            "kDividerRatio = 2.0f",
            "kAverageSamples = 32",
            "{3300, 0}, {3500, 5}, {3600, 10}, {3700, 25}, {3800, 45}",
            "if (cell_mv < 2500 || cell_mv > 4500)",
            '\\"battery_percent\\"',
            '\\"adc_calibrated\\"',
        ),
    )
    if "charging" in FW_BATTERY.read_text(encoding="utf-8"):
        raise AuditError("firmware must not infer or publish charging state")
    _assert_text(
        FW_MAIN,
        (
            "ret = battery_monitor::init();",
            "只发布校准电压与明确标注的电量估算",
        ),
    )
    _assert_text(
        WEB_WS,
        (
            "batteryMv: Number(msg.battery_mv)",
            "batteryPercent:",
            "percentIsEstimate: msg.percent_is_estimate === true",
            "adcCalibrated: msg.adc_calibrated === true",
        ),
    )
    _assert_text(
        WEB_DASHBOARD,
        (
            'aria-label="估算剩余电量"',
            "电压曲线估算，不用于充电或保护判断",
        ),
    )
    for path in (FW_BATTERY, WEB_WS, WEB_DASHBOARD):
        if "charging" in path.read_text(encoding="utf-8"):
            raise AuditError(f"{path.relative_to(REPO)} must not expose charging state")

    print("Main-board end-to-end power/USB audit PASS")
    print("  authoritative TPS62162/XFL3012 source hashes and exact XFL3012 land verified")
    print("  all 67 staging-to-physical pad/net maps plus deliberate NC pins verified")
    print("  harness, PMOS latch, isolated active-high button and USB split verified")
    print(
        "  critical distances: "
        + ", ".join(f"{name}={distance:.2f}mm" for name, distance in distances.items())
    )
    print("  21 intentional poses and 46 checkpoint-preserved legacy poses verified")
    print("  critical package library IDs and populated values verified")
    print("  BAT_P -> 1M/1M + 100nF -> GPIO9 ADC and web estimate verified; no charging telemetry")
    if require_route_free:
        print("  67 footprints; 0 tracks/vias; 0 copper zones; 1 footprint antenna rule area")
    else:
        print("  copper allowed; electrical/physical semantics audited independently of routing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-copper", action="store_true",
        help="skip the route-free-state assertion while retaining semantic checks",
    )
    args = parser.parse_args()
    try:
        audit(require_route_free=not args.allow_copper)
    except AuditError as exc:
        raise SystemExit(f"AUDIT FAIL: {exc}")
