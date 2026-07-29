#!/usr/bin/env python3
"""Migrate the checked-in C3 board to an unrouted C4 component board.

This bridge is intentionally explicit and project-specific.  It never runs
atopile and does not claim to replace the locked 0.12.5 compiler check.  It
swaps the MCU, adds the C4-only front-end/bypass footprints, assigns the
reviewed pad-to-net table, and removes C3 copper so routing can start cleanly.

Destructive copper removal requires --yes-clear-copper.  Run before Norman
starts manual routing, never after.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
LOCAL_PRETTY = ROOT / "pcb" / "layouts" / "lib" / "footprints.pretty"
KICAD_PRETTY = Path(
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
)
ATO_SOURCE = ROOT / "pcb" / "main.ato"


@dataclass(frozen=True)
class Part:
    addr: str
    ref: str
    value: str
    library: Path
    footprint: str


C4_PARTS = (
    Part("mcu", "MCU_ESP32_S3", "ESP32-S3-WROOM-1-N16R8", LOCAL_PRETTY,
         "ESP32-S3-WROOM-1_CUTOUT"),
    Part("mcu_c_bulk", "MCU_C_BULK_10U", "10uF", KICAD_PRETTY / "Capacitor_SMD.pretty",
         "C_0603_1608Metric"),
    Part("mcu_c_dec", "MCU_C_DEC_100N", "100nF", KICAD_PRETTY / "Capacitor_SMD.pretty",
         "C_0603_1608Metric"),
    Part("en_c_delay", "MCU_C_EN_1U", "1uF", KICAD_PRETTY / "Capacitor_SMD.pretty",
         "C_0603_1608Metric"),
    Part("pzt_frontend.dac", "PZT_DAC_MCP4728", "MCP4728-E/UN",
         KICAD_PRETTY / "Package_SO.pretty", "MSOP-10_3x3mm_P0.5mm"),
    Part("pzt_frontend.comparator", "PZT_CMP_TLV1814", "TLV1814PWR",
         KICAD_PRETTY / "Package_SO.pretty", "TSSOP-14_4.4x5mm_P0.65mm"),
    Part("pzt_frontend.r_sda_pullup", "PZT_R_SDA_PU_4K7", "4.7k",
         KICAD_PRETTY / "Resistor_SMD.pretty", "R_0603_1608Metric"),
    Part("pzt_frontend.r_scl_pullup", "PZT_R_SCL_PU_4K7", "4.7k",
         KICAD_PRETTY / "Resistor_SMD.pretty", "R_0603_1608Metric"),
    Part("pzt_frontend.c_dac", "PZT_C_DAC_100N", "100nF",
         KICAD_PRETTY / "Capacitor_SMD.pretty", "C_0603_1608Metric"),
    Part("pzt_frontend.c_comparator", "PZT_C_CMP_100N", "100nF",
         KICAD_PRETTY / "Capacitor_SMD.pretty", "C_0603_1608Metric"),
    Part("pzt_frontend.r_adc_tl", "PZT_R_ADC_TL_1M", "1M",
         KICAD_PRETTY / "Resistor_SMD.pretty", "R_0603_1608Metric"),
    Part("pzt_frontend.r_adc_tr", "PZT_R_ADC_TR_1M", "1M",
         KICAD_PRETTY / "Resistor_SMD.pretty", "R_0603_1608Metric"),
    Part("pzt_frontend.r_adc_bl", "PZT_R_ADC_BL_1M", "1M",
         KICAD_PRETTY / "Resistor_SMD.pretty", "R_0603_1608Metric"),
    Part("pzt_frontend.r_adc_br", "PZT_R_ADC_BR_1M", "1M",
         KICAD_PRETTY / "Resistor_SMD.pretty", "R_0603_1608Metric"),
    Part("pzt_frontend.jp_adc_tl", "JP_ADC_TL", "0R DNP",
         KICAD_PRETTY / "Resistor_SMD.pretty", "R_0603_1608Metric"),
    Part("pzt_frontend.jp_adc_tr", "JP_ADC_TR", "0R DNP",
         KICAD_PRETTY / "Resistor_SMD.pretty", "R_0603_1608Metric"),
    Part("pzt_frontend.jp_adc_bl", "JP_ADC_BL", "0R DNP",
         KICAD_PRETTY / "Resistor_SMD.pretty", "R_0603_1608Metric"),
    Part("pzt_frontend.jp_adc_br", "JP_ADC_BR", "0R DNP",
         KICAD_PRETTY / "Resistor_SMD.pretty", "R_0603_1608Metric"),
)

REFRESH_PARTS = (
    C4_PARTS[0],
    Part("imu", "IMU_IM948", "IM948", LOCAL_PRETTY, "IM948_CUTOUT"),
    Part("power.c_in", "PW_C_IN_10U", "10uF",
         KICAD_PRETTY / "Capacitor_SMD.pretty", "C_0603_1608Metric"),
    Part("pzt_tl.clamp_diode", "PZT_TL_D_CLAMP", "BAT54S",
         KICAD_PRETTY / "Package_TO_SOT_SMD.pretty", "SOT-23"),
    Part("pzt_tr.clamp_diode", "PZT_TR_D_CLAMP", "BAT54S",
         KICAD_PRETTY / "Package_TO_SOT_SMD.pretty", "SOT-23"),
    Part("pzt_bl.clamp_diode", "PZT_BL_D_CLAMP", "BAT54S",
         KICAD_PRETTY / "Package_TO_SOT_SMD.pretty", "SOT-23"),
    Part("pzt_br.clamp_diode", "PZT_BR_D_CLAMP", "BAT54S",
         KICAD_PRETTY / "Package_TO_SOT_SMD.pretty", "SOT-23"),
)


PAD_NETS: dict[str, dict[str, str]] = {
    "mcu": {
        "1": "gnd", "2": "vcc", "3": "en",
        "4": "pzt_adc_bl", "5": "pzt_adc_br",
        "6": "pzt_edge_bl", "7": "pzt_edge_br",
        "8": "pzt_edge_tl", "9": "pzt_edge_tr",
        "10": "i2c_sda", "11": "i2c_scl",
        "13": "usb_dn", "14": "usb_dp", "17": "bat_sense",
        "23": "led_data", "24": "pwr_latch", "25": "user_btn",
        "27": "boot_btn", "33": "imu_uart_tx", "34": "imu_uart_rx",
        "36": "uart_rx", "37": "uart_tx",
        "38": "pzt_adc_tr", "39": "pzt_adc_tl", "40": "gnd",
    },
    "mcu_c_bulk": {"1": "vcc", "2": "gnd"},
    "mcu_c_dec": {"1": "vcc", "2": "gnd"},
    "en_c_delay": {"1": "en", "2": "gnd"},
    "pzt_frontend.dac": {
        "1": "pzt_vref_tl", "2": "pzt_vref_tr",
        "3": "pzt_vref_bl", "4": "pzt_vref_br", "5": "gnd",
        "6": "gnd", "7": "i2c_scl", "8": "i2c_sda", "9": "vcc",
        "10": "",
    },
    "pzt_frontend.comparator": {
        "1": "pzt_edge_tr", "2": "pzt_edge_tl", "3": "vcc",
        "4": "pzt_vref_tl", "5": "pzt_cmp_in_tl",
        "6": "pzt_vref_tr", "7": "pzt_cmp_in_tr",
        "8": "pzt_vref_bl", "9": "pzt_cmp_in_bl",
        "10": "pzt_vref_br", "11": "pzt_cmp_in_br", "12": "gnd",
        "13": "pzt_edge_br", "14": "pzt_edge_bl",
    },
    "pzt_frontend.r_sda_pullup": {"1": "vcc", "2": "i2c_sda"},
    "pzt_frontend.r_scl_pullup": {"1": "vcc", "2": "i2c_scl"},
    "pzt_frontend.c_dac": {"1": "vcc", "2": "gnd"},
    "pzt_frontend.c_comparator": {"1": "vcc", "2": "gnd"},
    "tail.conn_f": {
        "1": "sys_5v_in", "2": "sys_5v_sw", "3": "btn_sw",
        "4": "usb_dp", "5": "uart_tx", "MP": "",
    },
    "tail.conn_b": {
        "1": "uart_rx", "2": "usb_dn", "3": "bat_cell_p",
        "4": "led_din", "5": "gnd", "MP": "",
    },
    "imu": {
        "1": "gnd", "2": "sys_5v_sw", "3": "", "4": "", "5": "",
        "6": "", "7": "bat_sense", "8": "gnd", "9": "led_b",
        "10": "led_r", "11": "imu_gpio", "12": "imu_key",
        "13": "imu_uart_tx", "14": "imu_uart_rx", "15": "", "16": "gnd",
    },
    "battery.r_top": {"1": "bat_cell_p", "2": "bat_sense"},
    "battery.r_bottom": {"1": "bat_sense", "2": "gnd"},
    "battery.c_filter": {"1": "bat_sense", "2": "gnd"},
    "bringup.vcc_pad": {"1": "vcc"},
    "bringup.sys5_pad": {"1": "sys_5v_sw"},
    "bringup.gnd_pad": {"1": "gnd"},
    "debug_sw.sw_boot": {"1": "boot_btn", "2": "gnd"},
    "debug_sw.sw_en": {"1": "en", "2": "gnd"},
    "debug_sw.sw_pwr": {"1": "btn_sw", "2": "gnd"},
    "led_c_supply": {"1": "sys_5v_sw", "2": "gnd"},
    "led_r_data": {"1": "led_data", "2": "led_din"},
    "power.c_in": {"1": "sys_5v_sw", "2": "gnd"},
    "power.c_out": {"1": "vcc", "2": "gnd"},
    "power.d_btn_start": {"1": "btn_sw", "2": "p_gate"},
    "power.ldo": {
        "1": "sys_5v_sw", "2": "gnd", "3": "sys_5v_sw",
        "4": "nc", "5": "vcc",
    },
    "power.q_latch": {"1": "pwr_latch", "2": "gnd", "3": "p_gate"},
    "power.q_power": {"1": "p_gate", "2": "sys_5v_in", "3": "sys_5v_sw"},
    "power.r_button_series": {"1": "btn_sw", "2": "user_btn"},
    "power.r_en_pullup": {"1": "en", "2": "vcc"},
    "power.r_gate": {"1": "p_gate", "2": "sys_5v_in"},
    "power.r_latch_pd": {"1": "pwr_latch", "2": "gnd"},
    "pwr_led.led": {"1": "vcc", "2": "c"},
    "pwr_led.r_lim": {"1": "c", "2": "gnd"},
}

# Explicitly clear every unused S3 perimeter pad.  In particular, pads
# 28..30 are GPIO35..37 and belong to the N16R8 octal-PSRAM interface.
for unused_mcu_pad in (12, 15, 16, 18, 19, 20, 21, 22, 26, 28, 29, 30, 31, 32, 35):
    PAD_NETS["mcu"][str(unused_mcu_pad)] = ""


for corner in ("tl", "tr", "bl", "br"):
    PAD_NETS[f"pzt_{corner}.pzt_signal_pad"] = {"1": f"pzt_raw_{corner}"}
    PAD_NETS[f"pzt_{corner}.pzt_gnd_pad"] = {"1": "gnd"}
    PAD_NETS[f"pzt_{corner}.series_resistor"] = {
        "1": f"pzt_raw_{corner}", "2": f"pzt_cmp_in_{corner}"
    }
    PAD_NETS[f"pzt_{corner}.bleed_resistor"] = {
        "1": f"pzt_raw_{corner}", "2": "gnd"
    }
    PAD_NETS[f"pzt_{corner}.clamp_diode"] = {
        "1": "gnd", "2": "vcc", "3": f"pzt_cmp_in_{corner}"
    }
    PAD_NETS[f"pzt_frontend.r_adc_{corner}"] = {
        "1": f"pzt_cmp_in_{corner}", "2": f"pzt_adc_iso_{corner}"
    }
    PAD_NETS[f"pzt_frontend.jp_adc_{corner}"] = {
        "1": f"pzt_adc_iso_{corner}", "2": f"pzt_adc_{corner}"
    }


DNP_ADDRESSES = frozenset(
    f"pzt_frontend.jp_adc_{corner}" for corner in ("tl", "tr", "bl", "br")
)


def _addr(fp) -> str:
    if fp.HasFieldByName("atopile_address"):
        return fp.GetFieldByName("atopile_address").GetText()
    try:
        return fp.GetProperty("atopile_address")
    except Exception:
        return ""


def _set_addr(fp, addr: str) -> None:
    if fp.HasFieldByName("atopile_address"):
        fp.GetFieldByName("atopile_address").SetText(addr)
    else:
        fp.SetField("atopile_address", addr)


def _load_footprint(pcbnew, part: Part):
    io = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    fp = io.FootprintLoad(str(part.library), part.footprint)
    if fp is None:
        raise RuntimeError(f"cannot load {part.library}:{part.footprint}")
    fp.SetReference(part.ref)
    fp.SetValue(part.value)
    _set_addr(fp, part.addr)
    return fp


def _ensure_net(board, pcbnew, name: str):
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def _source_guard() -> None:
    text = ATO_SOURCE.read_text(encoding="utf-8")
    required = {
        "ESP32S3WROOM1_Cutout", "PztThresholdFrontend", "MCP4728_MSOP10",
        "TLV1814_TSSOP14", "GPIO35..37", "F.p1(5V) 对 B.p5(GND)",
    }
    missing = sorted(token for token in required if token not in text)
    if missing:
        raise RuntimeError(f"main.ato C4 source guard failed: {missing}")
    if not re.search(r"conn_b\.p1\s*~\s*UART_RX", text):
        raise RuntimeError("main.ato tail C4 map missing conn_b.p1 -> UART_RX")
    if not re.search(r"conn_b\.p5\s*~\s*GND", text):
        raise RuntimeError("main.ato tail C4 map missing conn_b.p5 -> GND")


def migrate(board_path: Path, clear_copper: bool) -> None:
    import pcbnew

    _source_guard()
    board = pcbnew.LoadBoard(str(board_path))
    if board is None:
        raise RuntimeError(f"cannot load {board_path}")

    tracks = list(board.GetTracks())
    copper_zones = [
        board.GetArea(i) for i in range(board.GetAreaCount())
        if not board.GetArea(i).GetIsRuleArea()
    ]
    if (tracks or copper_zones) and not clear_copper:
        raise RuntimeError(
            f"board has {len(tracks)} tracks/vias and {len(copper_zones)} copper zones; "
            "rerun with --yes-clear-copper before manual routing"
        )
    for item in tracks:
        board.Remove(item)
    for zone in copper_zones:
        board.Remove(zone)

    by_addr = {_addr(fp): fp for fp in board.GetFootprints() if _addr(fp)}
    # Refresh the embedded interfaces and the five stale C3 library copies.
    # Embedded body silk belongs on F.Fab because it coincides with an internal
    # cutout. Copper has already been proven empty above, so replacing these
    # footprints cannot destroy manual routing.
    refresh_queue = [
        (part, by_addr[part.addr], _load_footprint(pcbnew, part))
        for part in REFRESH_PARTS
        if part.addr in by_addr
    ]
    add_queue = [
        (part, _load_footprint(pcbnew, part))
        for part in C4_PARTS
        if part.addr not in by_addr
    ]
    refreshed = 0
    for part, old, fresh in refresh_queue:
        position = old.GetPosition()
        rotation = old.GetOrientationDegrees()
        flipped = bool(old.IsFlipped()) if hasattr(old, "IsFlipped") else False
        board.Remove(old)
        fresh.SetPosition(position)
        fresh.SetParent(board)
        board.Add(fresh)
        if flipped and hasattr(fresh, "IsFlipped") and not fresh.IsFlipped():
            fresh.Flip(position, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fresh.SetOrientationDegrees(rotation)
        by_addr[part.addr] = fresh
        refreshed += 1

    added = 0
    for part, fp in add_queue:
        fp.SetPosition(pcbnew.VECTOR2I(0, 0))
        fp.SetParent(board)
        board.Add(fp)
        by_addr[part.addr] = fp
        added += 1

    assigned = 0
    missing_addr: list[str] = []
    for addr, pin_nets in PAD_NETS.items():
        fp = by_addr.get(addr)
        if fp is None:
            missing_addr.append(addr)
            continue
        for pad in fp.Pads():
            pad_number = pad.GetNumber()
            if pad_number not in pin_nets:
                continue
            net_name = pin_nets[pad_number]
            if net_name:
                pad.SetNet(_ensure_net(board, pcbnew, net_name))
                assigned += 1
            else:
                pad.SetNetCode(0)

    if missing_addr:
        raise RuntimeError(f"board missing C4 addresses: {missing_addr}")

    for addr in DNP_ADDRESSES:
        by_addr[addr].SetDNP(True)

    board.Save(str(board_path))
    print(
        f"C4 migration: removed {len(tracks)} tracks/vias + "
        f"{len(copper_zones)} copper zones; refreshed {refreshed} footprints + "
        f"added {added} footprints; "
        f"assigned {assigned} pads"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=BOARD)
    parser.add_argument("--yes-clear-copper", action="store_true")
    args = parser.parse_args()
    migrate(args.board.resolve(), args.yes_clear_copper)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
