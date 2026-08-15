#!/usr/bin/env python3
"""Safely synchronize the main-board power/USB redesign from Atopile staging.

The routed board is never an Atopile build target.  This script moves logical
pad nets from the route-free staging PCB to the user PCB by
``atopile_address`` + pad number, keeps all 63 legacy footprint poses,
normalizes verified footprint geometry, and parks a missing new part outside
the outline only on its first synchronization.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

try:
    import pcbnew
except ImportError as exc:  # pragma: no cover - KiCad runtime only
    raise SystemExit(
        "pcbnew is unavailable; run this script with KiCad 9's bundled Python"
    ) from exc


# ===== 分区：常量/配置 =====
REPO = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = REPO / "pcb/layouts/default/default.kicad_pcb"
DEFAULT_STAGING = REPO / "pcb/layouts/staging/default.atopile.kicad_pcb"


@dataclass(frozen=True)
class Part:
    reference: str
    value: str
    datasheet: str = ""


CHANGED_PARTS = {
    "power.ldo": Part(
        "PW_BUCK_3V3",
        "TPS62162DSGR",
        "${KIPRJMOD}/../../../docs/power-architecture-rework/sources/"
        "TPS62162-RevE.pdf",
    ),
    "power.l_buck": Part(
        "PW_L_BUCK_2U2",
        "XFL3012-222MEC 2.2uH",
        "${KIPRJMOD}/../../../docs/power-architecture-rework/sources/"
        "Coilcraft-XFL3012-Doc747.pdf",
    ),
    "power.c_in": Part("PW_C_IN_10U", "10uF 10V X5R/X7R"),
    "power.c_out": Part("PW_C_OUT_22U", "22uF 6.3V X5R/X7R"),
    "power.q_button_sense": Part("PW_Q_BTN_SENSE", "AO3400A"),
    "power.r_button_pullup": Part("PW_R_BTN_RAW_PU_100K", "100k 1%"),
    "power.r_button_gpio_pullup": Part("PW_R_BTN_GPIO_PU_100K", "100k 1%"),
    "usb_r_dp": Part("USB_R_DP_22R", "22R 1%"),
    "usb_r_dn": Part("USB_R_DN_22R", "22R 1%"),
}

NEW_PARTS = frozenset(
    {
        "power.l_buck",
        "power.q_button_sense",
        "power.r_button_pullup",
        "power.r_button_gpio_pullup",
        "usb_r_dp",
        "usb_r_dn",
    }
)

# Main-board outline ends near X=40.42 mm.  This is an outside-board parking
# tray only, not an electrical or mechanical placement decision.
PARK_MM = {
    "power.l_buck": (48.0, -34.0),
    "power.q_button_sense": (48.0, -27.0),
    "power.r_button_pullup": (52.0, -28.5),
    "power.r_button_gpio_pullup": (52.0, -25.5),
    "usb_r_dp": (48.0, -18.0),
    "usb_r_dn": (48.0, -15.0),
}

# Preserve the established physical-board/harness net vocabulary.  Atopile's
# canonical name selection otherwise changes several public nets to interface
# labels even though their electrical identity did not change.
NET_NAME_NORMALIZATION = {
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

# Explicitly unused physical pins.  Atopile can synthesize a one-pad net for
# them after the second build, but the manufacturing PCB must show true NC.
FORCED_NC = {
    ("power.ldo", "8"),  # TPS62162 PG
    ("imu", "3"),       # VBAT_3
    ("imu", "4"),       # VDDIO
    ("imu", "9"),       # LED_B
    ("imu", "10"),      # LED_R
    ("imu", "15"),      # VBAT_15
    ("pzt_frontend.dac", "10"),  # MCP4728 RDY/BSY
}

# These project-local geometries deliberately changed without changing their
# pad numbers.  Refreshing them from the route-free stage is safe because the
# synchronizer restores side, position, orientation, public fields and nets.
ALWAYS_REFRESH_FROM_LIBRARY = {
    "debug_sw.sw_boot",
    "debug_sw.sw_en",
    "debug_sw.sw_pwr",
    "pwr_led.led",
    "tail.conn_f",
    "tail.conn_b",
    # Remove stale local overrides inherited from the old routed board.  These
    # are exact stock/project footprints; only pose, fields and nets are local.
    "pzt_frontend.jp_adc_tl",
    "pzt_frontend.r_adc_tr",
    "power.q_power",
    "power.r_gate",
    "power.r_button_series",
    "pzt_frontend.comparator",
    "power.r_latch_pd",
    "mcu_c_bulk",
    "pzt_frontend.jp_adc_tr",
    "mcu_c_dec",
    "pzt_bl.bleed_resistor",
    "pzt_tl.bleed_resistor",
    "pzt_frontend.r_adc_br",
    "pzt_br.bleed_resistor",
    "pzt_frontend.r_adc_bl",
    "power.r_en_pullup",
    "pzt_frontend.jp_adc_br",
    "power.d_btn_start",
    "led_c_supply",
    "battery.r_bottom",
    "battery.r_top",
    "battery.c_filter",
    "power.q_latch",
    "pzt_frontend.c_dac",
    "pzt_frontend.c_comparator",
    "en_c_delay",
    "pzt_frontend.dac",
    "pzt_frontend.r_sda_pullup",
    "led_r_data",
    "pzt_frontend.r_scl_pullup",
    "pwr_led.r_lim",
}

HIDE_REFERENCE = ALWAYS_REFRESH_FROM_LIBRARY | {
    "pzt_tl.pzt_signal_pad", "pzt_tl.pzt_gnd_pad",
    "pzt_tr.pzt_signal_pad", "pzt_tr.pzt_gnd_pad",
    "pzt_bl.pzt_signal_pad", "pzt_bl.pzt_gnd_pad",
    "pzt_br.pzt_signal_pad", "pzt_br.pzt_gnd_pad",
}


# ===== 分区：私有成员 =====
class SyncError(RuntimeError):
    pass


def _field(fp: "pcbnew.FOOTPRINT", name: str) -> str:
    return fp.GetFieldByName(name).GetText() if fp.HasFieldByName(name) else ""


def _by_address(board: "pcbnew.BOARD") -> dict[str, "pcbnew.FOOTPRINT"]:
    result = {}
    for fp in board.GetFootprints():
        address = _field(fp, "atopile_address")
        if not address:
            raise SyncError(f"{fp.GetReference()} has no atopile_address")
        if address in result:
            raise SyncError(f"duplicate atopile_address {address}")
        result[address] = fp
    return result


def _pose(fp: "pcbnew.FOOTPRINT") -> tuple[int, int, float, int]:
    pos = fp.GetPosition()
    return pos.x, pos.y, fp.GetOrientationDegrees(), fp.GetLayer()


def _pad_net_map(fp: "pcbnew.FOOTPRINT") -> dict[str, str | None]:
    by_number: dict[str, set[str | None]] = {}
    for pad in fp.Pads():
        if not pad.GetNumber():
            if pad.GetNetname():
                raise SyncError(f"{fp.GetReference()} unnumbered aperture has a net")
            continue
        by_number.setdefault(pad.GetNumber(), set()).add(pad.GetNetname() or None)
    result = {}
    for number, names in by_number.items():
        if len(names) != 1:
            raise SyncError(f"{_field(fp, 'atopile_address')}.{number} has {names}")
        result[number] = next(iter(names))
    return result


def _ensure_net(board: "pcbnew.BOARD", name: str) -> "pcbnew.NETINFO_ITEM":
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def _stock_library(name: str, item: str) -> Path:
    if name == "SmartPaddle":
        local = REPO / "pcb/layouts/lib/footprints.pretty"
        if (local / f"{item}.kicad_mod").is_file():
            return local
        raise SyncError(f"project footprint SmartPaddle:{item} was not found")
    candidates = []
    if root := os.environ.get("KICAD9_FOOTPRINT_DIR"):
        candidates.append(Path(root) / f"{name}.pretty")
    candidates.extend(
        [
            Path(
                "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
            )
            / f"{name}.pretty",
            Path("/usr/share/kicad/footprints") / f"{name}.pretty",
        ]
    )
    for candidate in candidates:
        if (candidate / f"{item}.kicad_mod").is_file():
            return candidate
    raise SyncError(f"KiCad 9 library item {name}:{item} was not found")


def _replace_from_library(
    board: "pcbnew.BOARD",
    old: "pcbnew.FOOTPRINT",
    nickname: str,
    item: str,
) -> "pcbnew.FOOTPRINT":
    position = old.GetPosition()
    orientation = old.GetOrientationDegrees()
    layer = old.GetLayer()
    # Do not copy Atopile's private footprint hash: it belongs to the replaced
    # geometry.  Reading the full SWIG field tuple after another replacement is
    # also unreliable in KiCad 9, so copy only the public contract explicitly.
    fields = {
        "Reference": old.GetReference(),
        "Value": old.GetValue(),
        "Datasheet": _field(old, "Datasheet"),
        "Description": _field(old, "Description"),
        "atopile_address": _field(old, "atopile_address"),
    }
    library = _stock_library(nickname, item)
    replacement = pcbnew.FootprintLoad(str(library), item)
    if replacement is None:
        raise SyncError(f"could not load {nickname}:{item}")
    board.Remove(old)
    board.Add(replacement)
    replacement.SetPosition(position)
    if layer == pcbnew.B_Cu:
        replacement.Flip(position, pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    elif layer != pcbnew.F_Cu:
        raise SyncError(f"unsupported layer for {fields['Reference']}")
    replacement.SetOrientationDegrees(orientation)
    replacement.SetFPID(pcbnew.LIB_ID(nickname, item))
    replacement.SetFields(fields)
    return replacement


def _geometry_is(
    fp: "pcbnew.FOOTPRINT", fpid: str, expected_numbers: set[str]
) -> bool:
    return (
        fp.GetFPIDAsString() == fpid
        and {pad.GetNumber() for pad in fp.Pads() if pad.GetNumber()} == expected_numbers
    )


def _normalize_net(name: str | None) -> str | None:
    return NET_NAME_NORMALIZATION.get(name, name) if name else None


def _set_changed_fields(fp: "pcbnew.FOOTPRINT", address: str) -> None:
    if address in CHANGED_PARTS:
        part = CHANGED_PARTS[address]
        fp.SetReference(part.reference)
        fp.SetValue(part.value)
        if fp.HasFieldByName("Datasheet"):
            fp.GetFieldByName("Datasheet").SetText(part.datasheet)
    # Atopile's private address is synchronization metadata, not assembly
    # silkscreen.  Legacy boards had several of these fields visible/mirrored.
    if fp.HasFieldByName("atopile_address"):
        field = fp.GetFieldByName("atopile_address")
        field.SetLayer(pcbnew.User_9)
        field.SetVisible(False)
    if address in HIDE_REFERENCE:
        fp.Reference().SetVisible(False)


# ===== 分区：公开 API =====
def synchronize(target_path: Path, staging_path: Path) -> None:
    if not target_path.is_file() or not staging_path.is_file():
        raise SyncError("target or staging PCB is missing")
    # KiCad 9's SWIG layer can crash when a board loaded beside its live
    # .kicad_pro is saved under another name.  Work from a detached copy and
    # swap only after an independent reload succeeds.
    input_handle = tempfile.NamedTemporaryFile(
        prefix="smartpaddle-main-input-", suffix=".kicad_pcb", delete=False
    )
    detached_input = Path(input_handle.name)
    input_handle.close()
    shutil.copy2(target_path, detached_input)
    target = pcbnew.LoadBoard(str(detached_input))
    stage = pcbnew.LoadBoard(str(staging_path))
    target_parts = _by_address(target)
    stage_parts = _by_address(stage)
    if len(target_parts) not in (63, 69) or len(stage_parts) != 69:
        raise SyncError(
            f"unexpected inventories: target={len(target_parts)}, staging={len(stage_parts)}"
        )
    if not set(target_parts).issubset(stage_parts):
        raise SyncError("target contains an address absent from the logical staging board")
    if list(target.GetTracks()) or target.GetAreaCount():
        raise SyncError("target must have 0 tracks/vias and 0 zones")
    if list(stage.GetTracks()) or stage.GetAreaCount():
        raise SyncError("staging must have 0 tracks/vias and 0 zones")

    logical_nets = {address: _pad_net_map(fp) for address, fp in stage_parts.items()}
    required = {
        ("power.ldo", "7"): "buck_sw",
        ("power.l_buck", "1"): "buck_sw",
        ("power.l_buck", "2"): "vcc",
        ("power.q_button_sense", "1"): "button_sense_gate",
        ("power.q_button_sense", "3"): "user_btn",
        ("tail.conn_f", "4"): "usb_dp_conn",
        ("tail.conn_b", "2"): "usb_dn_conn",
    }
    for (address, pad), net in required.items():
        if logical_nets[address].get(pad) != net:
            raise SyncError(f"staging map mismatch: {address}.{pad}")

    legacy_addresses = set(target_parts) - NEW_PARTS
    legacy_poses = {address: _pose(target_parts[address]) for address in legacy_addresses}

    replacements = {
        "power.ldo": (
            "Package_SON",
            "Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
        ),
        "power.c_in": ("Capacitor_SMD", "C_0805_2012Metric"),
        "power.c_out": ("Capacitor_SMD", "C_1206_3216Metric"),
        "pzt_tl.pzt_signal_pad": ("SmartPaddle", "PZT_WirePad_THT_D2.5mm_Drill1.2mm"),
        "pzt_tl.pzt_gnd_pad": ("SmartPaddle", "PZT_WirePad_THT_D2.5mm_Drill1.2mm"),
        "pzt_tr.pzt_signal_pad": ("SmartPaddle", "PZT_WirePad_THT_D2.5mm_Drill1.2mm"),
        "pzt_tr.pzt_gnd_pad": ("SmartPaddle", "PZT_WirePad_THT_D2.5mm_Drill1.2mm"),
        "pzt_bl.pzt_signal_pad": ("SmartPaddle", "PZT_WirePad_THT_D2.5mm_Drill1.2mm"),
        "pzt_bl.pzt_gnd_pad": ("SmartPaddle", "PZT_WirePad_THT_D2.5mm_Drill1.2mm"),
        "pzt_br.pzt_signal_pad": ("SmartPaddle", "PZT_WirePad_THT_D2.5mm_Drill1.2mm"),
        "pzt_br.pzt_gnd_pad": ("SmartPaddle", "PZT_WirePad_THT_D2.5mm_Drill1.2mm"),
        "debug_sw.sw_boot": ("SmartPaddle", "SW_SPST_4.5x4.5"),
        "debug_sw.sw_en": ("SmartPaddle", "SW_SPST_4.5x4.5"),
        "debug_sw.sw_pwr": ("SmartPaddle", "SW_SPST_4.5x4.5"),
        "pwr_led.led": ("SmartPaddle", "LED_0603"),
        "tail.conn_f": (
            "SmartPaddle",
            "Molex_PicoBlade_53261-0571_1x05-1MP_P1.25mm_Horizontal",
        ),
        "tail.conn_b": (
            "SmartPaddle",
            "Molex_PicoBlade_53261-0571_1x05-1MP_P1.25mm_Horizontal",
        ),
        "pzt_frontend.jp_adc_tl": ("Resistor_SMD", "R_0603_1608Metric"),
        "pzt_frontend.r_adc_tr": ("Resistor_SMD", "R_0603_1608Metric"),
        "power.q_power": ("Package_TO_SOT_SMD", "SOT-23"),
        "power.r_gate": ("Resistor_SMD", "R_0603_1608Metric"),
        "power.r_button_series": ("Resistor_SMD", "R_0603_1608Metric"),
        "pzt_frontend.comparator": ("Package_SO", "TSSOP-14_4.4x5mm_P0.65mm"),
        "power.r_latch_pd": ("Resistor_SMD", "R_0603_1608Metric"),
        "mcu_c_bulk": ("Capacitor_SMD", "C_0603_1608Metric"),
        "pzt_frontend.jp_adc_tr": ("Resistor_SMD", "R_0603_1608Metric"),
        "mcu_c_dec": ("Capacitor_SMD", "C_0603_1608Metric"),
        "pzt_bl.bleed_resistor": ("Resistor_SMD", "R_0603_1608Metric"),
        "pzt_tl.bleed_resistor": ("Resistor_SMD", "R_0603_1608Metric"),
        "pzt_frontend.r_adc_br": ("Resistor_SMD", "R_0603_1608Metric"),
        "pzt_br.bleed_resistor": ("Resistor_SMD", "R_0603_1608Metric"),
        "pzt_frontend.r_adc_bl": ("Resistor_SMD", "R_0603_1608Metric"),
        "power.r_en_pullup": ("Resistor_SMD", "R_0603_1608Metric"),
        "pzt_frontend.jp_adc_br": ("Resistor_SMD", "R_0603_1608Metric"),
        "power.d_btn_start": ("SmartPaddle", "D_SOD-323_HandSoldering"),
        "led_c_supply": ("Capacitor_SMD", "C_0603_1608Metric"),
        "battery.r_bottom": ("Resistor_SMD", "R_0603_1608Metric"),
        "battery.r_top": ("Resistor_SMD", "R_0603_1608Metric"),
        "battery.c_filter": ("Capacitor_SMD", "C_0603_1608Metric"),
        "power.q_latch": ("Package_TO_SOT_SMD", "SOT-23"),
        "pzt_frontend.c_dac": ("Capacitor_SMD", "C_0603_1608Metric"),
        "pzt_frontend.c_comparator": ("Capacitor_SMD", "C_0603_1608Metric"),
        "en_c_delay": ("Capacitor_SMD", "C_0603_1608Metric"),
        "pzt_frontend.dac": ("Package_SO", "MSOP-10_3x3mm_P0.5mm"),
        "pzt_frontend.r_sda_pullup": ("Resistor_SMD", "R_0603_1608Metric"),
        "led_r_data": ("Resistor_SMD", "R_0603_1608Metric"),
        "pzt_frontend.r_scl_pullup": ("Resistor_SMD", "R_0603_1608Metric"),
        "pwr_led.r_lim": ("Resistor_SMD", "R_0603_1608Metric"),
    }
    prepared_replacements = []
    for address, (nickname, item) in replacements.items():
        fpid = f"{nickname}:{item}"
        expected_numbers = set(logical_nets[address])
        current = target_parts[address]
        if address in ALWAYS_REFRESH_FROM_LIBRARY or not _geometry_is(
            current, fpid, expected_numbers
        ):
            # Capture all SWIG-backed data before removing anything; KiCad 9
            # may invalidate field proxies for unrelated footprints after the
            # first BOARD.Remove().  The staging clone already uses the exact
            # verified stock footprint.
            position = current.GetPosition()
            captured = (
                position.x,
                position.y,
                current.GetOrientationDegrees(),
                current.GetLayer(),
                current.GetReference(),
                current.GetValue(),
                _field(current, "Datasheet"),
                _field(current, "Description"),
                _field(current, "atopile_address"),
            )
            prepared_replacements.append(
                (
                    address,
                    current,
                    pcbnew.FootprintLoad(
                        str(_stock_library(nickname, item)), item
                    ),
                    nickname,
                    item,
                    captured,
                )
            )

    for address, old, replacement, nickname, item, captured in prepared_replacements:
        x, y, orientation, layer, reference, value, datasheet, description, ato_address = captured
        position = pcbnew.VECTOR2I(x, y)
        if replacement is None:
            raise SyncError(f"could not load replacement library for {address}")
        target.Remove(old)
        target.Add(replacement)
        replacement.SetFPID(pcbnew.LIB_ID(nickname, item))
        replacement.SetPosition(position)
        if layer == pcbnew.B_Cu:
            replacement.Flip(position, pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        elif layer not in (pcbnew.F_Cu, pcbnew.B_Cu):
            raise SyncError(f"unsupported layer for {reference}")
        replacement.SetOrientationDegrees(orientation)
        replacement.SetFields(
            {
                "Reference": reference,
                "Value": value,
                "Datasheet": datasheet,
                "Description": description,
                "atopile_address": ato_address,
            }
        )
        target_parts[address] = replacement

    target_parts = _by_address(target)

    for address in sorted(NEW_PARTS - set(target_parts)):
        clone = stage_parts[address].Duplicate()
        target.Add(clone)
        clone.SetPosition(pcbnew.VECTOR2I_MM(*PARK_MM[address]))
        clone.SetOrientationDegrees(0)
        target_parts[address] = clone

    if set(target_parts) != set(stage_parts):
        raise SyncError("target/staging address sets differ after synchronization")

    for address, fp in target_parts.items():
        _set_changed_fields(fp, address)
        target_numbers = {pad.GetNumber() for pad in fp.Pads() if pad.GetNumber()}
        if target_numbers != set(logical_nets[address]):
            raise SyncError(
                f"pad-number mismatch for {address}: {sorted(target_numbers)} != "
                f"{sorted(logical_nets[address])}"
            )
        for pad in fp.Pads():
            number = pad.GetNumber()
            if not number:
                pad.SetNetCode(0)
                continue
            net_name = (
                None
                if (address, number) in FORCED_NC
                else _normalize_net(logical_nets[address][number])
            )
            if net_name:
                pad.SetNet(_ensure_net(target, net_name))
            else:
                pad.SetNetCode(0)

    target.SanitizeNetcodes()
    for address, before in legacy_poses.items():
        after = _pose(target_parts[address])
        if after != before:
            raise SyncError(f"legacy pose changed: {address}: {before} -> {after}")
    if len(list(target.GetFootprints())) != 69:
        raise SyncError("main board must contain 69 footprints")
    references = [fp.GetReference() for fp in target.GetFootprints()]
    if len(references) != len(set(references)):
        raise SyncError("duplicate references after synchronization")

    handle = tempfile.NamedTemporaryFile(
        prefix="smartpaddle-main-sync-", suffix=".kicad_pcb", delete=False
    )
    temporary = Path(handle.name)
    handle.close()
    temporary.unlink()
    pcbnew.SaveBoard(str(temporary), target)
    verify = pcbnew.LoadBoard(str(temporary))
    if verify is None or len(list(verify.GetFootprints())) != 69:
        temporary.unlink(missing_ok=True)
        raise SyncError("saved-board verification failed")
    if list(verify.GetTracks()) or verify.GetAreaCount():
        temporary.unlink(missing_ok=True)
        raise SyncError("saved board unexpectedly contains copper")
    swap = target_path.with_name(
        f".{target_path.stem}.{uuid.uuid4().hex}.sync.swap.kicad_pcb"
    )
    shutil.copy2(temporary, swap)
    temporary.unlink()
    os.replace(swap, target_path)
    detached_input.unlink(missing_ok=True)
    for path in (temporary, detached_input):
        for suffix in (".kicad_pro", ".kicad_prl"):
            path.with_suffix(suffix).unlink(missing_ok=True)

    print("Main-board power/USB synchronization PASS")
    print("  63 legacy footprint poses preserved")
    print("  TPS62162 + 0805 input + 1206 output footprints applied")
    print("  6 added parts retained at existing poses (parked only on first add)")
    print("  stable public net names and deliberate NC pads preserved")
    print("  69 footprints; 0 tracks/vias; 0 zones")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    args = parser.parse_args()
    try:
        synchronize(args.target.resolve(), args.staging.resolve())
    except SyncError as exc:
        print(f"SYNC FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
