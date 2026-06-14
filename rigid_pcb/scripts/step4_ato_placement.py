#!/usr/bin/env python3
"""Step 4 — Normalize atopile footprints and place them at scaffold positions.

Layout zones:

  mainland right/top    — power latch, EN, button logic, regulator
  mainland lower/core   — LED interface and battery sense
  handle root           — bring-up and UART test pads
  gangway entrances     — PZT series/bleed/clamp parts

PZT signal/GND wire pads stay on the docks and are only re-snapped when
--place-docks is passed.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, save_board, slot_basis, xy
from rigid_pcb.tools.mech_geometry import ESP32_CUTOUT, IMU_CUTOUT

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"
PARAMS = ROOT / "shared" / "board_params.yaml"
ATO_BACKUP_DIR = ROOT / "rigid_pcb" / "build" / "builds" / "default"

KEEPOUT = 1.5
COL_SPACING_Y = 3.5           # 默认列间距 (元件中心到中心) — 大部分区域用
GRID_SPACING_X = 4.2
GRID_SPACING_Y = 4.4
COL_MARGIN = 1.0               # 距区域北边缘的额外余量
TEXT_THICKNESS = 0.10

READABLE_REFS = {
    "mcu": ("MCU_SGFK_C6", "SGFK ESP32-C6-N8"),
    "imu": ("IMU_IM948", "IM948"),
    "power.q_power": ("PW_Q_LOAD", "P-MOS load switch"),
    "power.q_latch": ("PW_Q_LATCH", "N-MOS latch"),
    "power.r_gate": ("PW_R_GATE_100K", "100k"),
    "power.r_button_series": ("PW_R_BTN_SER_1K", "1k"),
    "power.r_button_pullup": ("PW_R_BTN_PU_10K", "10k"),
    "power.r_latch_pd": ("PW_R_LATCH_PD_100K", "100k"),
    "power.r_en_pullup": ("PW_R_EN_PU_10K", "10k"),
    "power.d_button": ("PW_D_BTN", "Schottky"),
    "power.ldo": ("PW_LDO_3V3", "AP2112K-3.3"),
    "power.c_in": ("PW_C_IN_10U", "10uF"),
    "power.c_out": ("PW_C_OUT_10U", "10uF"),
    "battery.r_top": ("BAT_R_TOP_1M", "1M"),
    "battery.r_bottom": ("BAT_R_BOT_1M", "1M"),
    "battery.c_filter": ("BAT_C_ADC_100N", "100nF"),
    "led.r_data": ("LED_R_DATA_330R", "330R"),
    "led.c_supply": ("LED_C_SUP_100N", "100nF"),
    "led_r_data": ("LED_R_DATA_330R", "330R"),
    "led_c_supply": ("LED_C_SUP_100N", "100nF"),
    "tail.bat_plus_pad": ("TAIL_BAT_PLUS", "BAT+ wire"),
    "tail.gnd_pad": ("TAIL_GND", "GND wire"),
    "tail.led_plus_pad": ("TAIL_LED_PLUS", "LED+ wire"),
    "tail.led_din_pad": ("TAIL_LED_DIN", "LED DIN wire"),
    "tail.button_pad": ("TAIL_BTN", "button wire"),
    "tail.usb_vbus_pad": ("TAIL_USB_VBUS", "USB VBUS wire"),
    "tail.usb_dp_pad": ("TAIL_USB_DP", "USB D+ wire"),
    "tail.usb_dn_pad": ("TAIL_USB_DN", "USB D- wire"),
    "bringup.vbat_pad": ("TP_VBAT_SW", "VBAT_SW test"),
    "bringup.vcc_pad": ("TP_3V3", "3V3 test"),
    "bringup.gnd_pad": ("TP_GND", "GND test"),
    "bringup.en_pad": ("TP_EN", "EN test"),
    "bringup.boot_pad": ("TP_BOOT", "BOOT test"),
    "bringup.uart_tx_pad": ("TP_UART_TX", "UART TX test"),
    "bringup.uart_rx_pad": ("TP_UART_RX", "UART RX test"),
    "bringup.imu_key_pad": ("TP_IMU_KEY", "IMU KEY test"),
    "bringup.imu_gpio_pad": ("TP_IMU_GPIO", "IMU GPIO test"),
    "bringup.pwr_latch_pad": ("TP_PWR_LATCH", "PWR_LATCH test"),
    "bringup.led_data_pad": ("TP_LED_DATA", "LED DATA test"),
    "bringup.vbus_pad": ("TP_VBUS", "VBUS test"),
    "bringup.imu_vddio_pad": ("TP_IMU_VDDIO", "IMU VDDIO test"),
    "bringup.vbat_sense_pad": ("TP_VBAT_SENSE", "battery sense test"),
}

PZT_READABLE_PREFIXES = {
    "pzt_tr": "PZT_TR",
    "pzt_tl": "PZT_TL",
    "pzt_br": "PZT_BR",
    "pzt_bl": "PZT_BL",
}

PZT_READABLE_PARTS = {
    "series_resistor": ("R_SER_4K7", "4.7k"),
    "bleed_resistor": ("R_DIS_1M", "1M"),
    "clamp_diode": ("D_CLAMP", "BAT54S"),
    "pzt_signal_pad": ("SIG", "PZT signal wire"),
    "pzt_gnd_pad": ("GND", "PZT GND wire"),
}

MODEL_SCALES = {
    "mcu": 0.3937008,
    "imu": 0.3937008,
}


# ===== 分区：方法/工具 =====


def safe_id(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_+.-]+", "_", text.strip())
    return text or "Generated"


def infer_attr(pcbnew, fp) -> int:
    for pad in fp.Pads():
        if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            return pcbnew.FP_THROUGH_HOLE
    return pcbnew.FP_SMD


def address(fp) -> str | None:
    if not fp.HasFieldByName("atopile_address"):
        return None
    return fp.GetFieldByName("atopile_address").GetText()


def readable_ref(addr: str) -> tuple[str, str] | None:
    if addr in READABLE_REFS:
        return READABLE_REFS[addr]
    for pzt_addr, prefix in PZT_READABLE_PREFIXES.items():
        stem = pzt_addr + "."
        if addr.startswith(stem):
            part = addr[len(stem):]
            if part in PZT_READABLE_PARTS:
                suffix, value = PZT_READABLE_PARTS[part]
                return f"{prefix}_{suffix}", value
    return None


def set_text_size(pcbnew, field, size_mm: float) -> None:
    field.SetTextHeight(pcbnew.FromMM(size_mm))
    field.SetTextWidth(pcbnew.FromMM(size_mm))
    field.SetTextThickness(pcbnew.FromMM(TEXT_THICKNESS))


def set_text_at(pcbnew, field, x: float, y: float, angle_deg: float = 0) -> None:
    field.SetPosition(xy(pcbnew, x, y))
    field.SetTextAngleDegrees(angle_deg)


def label_spec(addr: str, fp) -> tuple[float, tuple[float, float], float]:
    """Return reference text size, absolute position, and angle."""
    pos = fp.GetPosition()
    x = pos.x / 1_000_000
    y = pos.y / 1_000_000

    if addr == "mcu":
        return 0.60, (x, y - ESP32_CUTOUT[3] / 2 - 1.4), 0
    if addr == "imu":
        return 0.60, (x, y - IMU_CUTOUT[3] / 2 - 1.2), 0
    if addr.startswith("tail."):
        return 0.38, (x, y + 1.4), 0
    if addr.startswith("pzt_"):
        return 0.38, (x, y + 1.2), fp.GetOrientationDegrees()
    return 0.38, (x, y), 0


def should_show_reference(addr: str) -> bool:
    if addr in {"mcu", "imu"}:
        return True
    if addr.startswith("tail."):
        return True
    if addr.endswith(".pzt_signal_pad") or addr.endswith(".pzt_gnd_pad"):
        return True
    return False


def apply_readable_text(pcbnew, board) -> int:
    used = set()
    changed = 0
    visible = 0
    for fp in board.GetFootprints():
        addr = address(fp)
        if not addr:
            continue
        alias = readable_ref(addr)
        if not alias:
            continue

        ref, value = alias
        if ref in used:
            raise RuntimeError(f"duplicate generated reference: {ref}")
        used.add(ref)

        fp.SetReference(ref)
        fp.SetValue(value)
        size, (tx, ty), angle = label_spec(addr, fp)

        ref_field = fp.Reference()
        value_field = fp.Value()
        show_ref = should_show_reference(addr)
        ref_field.SetVisible(show_ref)
        value_field.SetVisible(False)
        ref_field.SetLayer(pcbnew.F_SilkS)
        value_field.SetLayer(pcbnew.F_Fab)
        set_text_size(pcbnew, ref_field, size)
        set_text_size(pcbnew, value_field, 0.45)
        set_text_at(pcbnew, ref_field, tx, ty, angle)
        changed += 1
        visible += 1 if show_ref else 0
    return changed, visible


def apply_model_scales(board) -> int:
    changed = 0
    for fp in board.GetFootprints():
        addr = address(fp)
        if addr not in MODEL_SCALES:
            continue
        models = fp.Models()
        fixed = []
        for model in models:
            scale = MODEL_SCALES[addr]
            model.m_Scale.Set(scale, scale, scale)
            fixed.append(model)
        models.clear()
        for model in fixed:
            models.append(model)
            changed += 1
    return changed


def _net_source_candidates() -> list[Path]:
    if not ATO_BACKUP_DIR.exists():
        return []
    return sorted(ATO_BACKUP_DIR.glob("default.pcbnew-*.kicad_pcb"), key=lambda p: p.stat().st_mtime, reverse=True)


def _board_has_named_nets(board) -> bool:
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname():
                return True
    return False


def _address_pad_nets(board) -> dict[tuple[str, str], str]:
    mapping = {}
    for fp in board.GetFootprints():
        addr = address(fp)
        if not addr:
            continue
        for pad in fp.Pads():
            netname = pad.GetNetname()
            if netname:
                mapping[(addr, pad.GetNumber())] = netname
    return mapping


def sync_nets_from_recent_ato_backup(pcbnew, board) -> tuple[int, Path | None]:
    """Restore pad net assignments after a Step 1 clear + ATO rebuild.

    ATO 0.12.5 currently re-adds footprints after a completely cleared PCB, but
    the generated KiCad netlist can be empty.  The latest pre-build PCB backup
    still carries the intended pad nets, so copy them by atopile_address + pad
    number.  This does not create or change any logical connections in ATO.
    """

    if _board_has_named_nets(board):
        return 0, None

    for candidate in _net_source_candidates():
        source_board = load_board(pcbnew, candidate)
        source_nets = _address_pad_nets(source_board)
        if not source_nets:
            continue

        net_cache = {}

        def ensure_net(netname: str):
            net = net_cache.get(netname)
            if net is not None:
                return net
            net = board.FindNet(netname)
            if net is None:
                net = pcbnew.NETINFO_ITEM(board, netname)
                board.Add(net)
            net_cache[netname] = net
            return net

        assigned = 0
        for fp in board.GetFootprints():
            addr = address(fp)
            if not addr:
                continue
            for pad in fp.Pads():
                netname = source_nets.get((addr, pad.GetNumber()))
                if not netname:
                    continue
                pad.SetNet(ensure_net(netname))
                assigned += 1

        board.BuildListOfNets()
        board.SanitizeNetcodes()
        return assigned, candidate

    return 0, None


def is_initial_grid(fp) -> bool:
    pos = fp.GetPosition()
    x = pos.x / 1_000_000
    y = pos.y / 1_000_000
    return math.isclose(x / 10, round(x / 10), abs_tol=1e-3) and math.isclose(
        y / 10, round(y / 10), abs_tol=1e-3
    )


def move_one(pcbnew, fp_by_addr: dict, addr: str, x: float, y: float, rot: float, force: bool) -> int:
    fp = fp_by_addr.get(addr)
    if fp is None:
        return 0
    if not force and not is_initial_grid(fp):
        return 0
    fp.SetPosition(xy(pcbnew, x, y))
    fp.SetOrientationDegrees(rot)
    return 1


def _cutout_edges(cutout: tuple[float, float, float, float]) -> dict[str, float]:
    """Compute edge positions for a cutout (cx, cy, w, h) including keepout."""
    cx, cy, w, h = cutout
    hw, hh = w / 2, h / 2
    return {
        "left":  cx - hw - KEEPOUT,
        "right": cx + hw + KEEPOUT,
        "top":   cy - hh - KEEPOUT,
        "bot":   cy + hh + KEEPOUT,
        "cx":    cx,
        "cy":    cy,
    }


def col_y(t: float, step: int, spacing: float | None = None) -> float:
    """Return Y for the nth position in a vertical column starting at *t* (north edge)."""
    return t + COL_MARGIN + step * (spacing if spacing is not None else COL_SPACING_Y)


def place_map(pcbnew, fp_by_addr: dict, placements: dict[str, tuple[float, float, float]], force: bool) -> int:
    moved = 0
    for addr, (x, y, rot) in placements.items():
        moved += move_one(pcbnew, fp_by_addr, addr, x, y, rot, force)
    return moved


# ===== 分区：公开 API =====


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 4: Normalize and place atopile footprints")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--force", action="store_true", help="re-snap already-placed footprints")
    parser.add_argument("--place-docks", action="store_true", help="also place PZT dock footprints")
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)

    # ---- 4a: Normalize footprint metadata ----
    changed = 0
    for fp in board.GetFootprints():
        ref = fp.GetReference() or "Generated"
        if not fp.GetFPIDAsString():
            fp.SetFPIDAsString(f"SmartPaddle:{safe_id(ref)}")
            changed += 1
        if fp.GetAttributes() == 0:
            fp.SetAttributes(infer_attr(pcbnew, fp))
            changed += 1

    print(f"4a. 规范化: 修正了 {changed} 个封装的元数据字段")

    # ---- 4b: Place footprints at relative scaffold positions ----
    params = yaml.safe_load(PARAMS.read_text())
    fp_by_addr = {addr: fp for fp in board.GetFootprints() if (addr := address(fp))}

    if not fp_by_addr:
        print("4b. 警告: 未找到带 atopile_address 属性的封装")
        print("    请先运行 atopile build 生成封装，然后重新执行本步骤")
        save_board(board, args.board)
        return

    moved = 0

    mcu = _cutout_edges(ESP32_CUTOUT)
    imu = _cutout_edges(IMU_CUTOUT)

    # ---- Core modules (centre of their cutouts) ----
    moved += move_one(pcbnew, fp_by_addr, "mcu", ESP32_CUTOUT[0], ESP32_CUTOUT[1], 0, args.force)
    moved += move_one(pcbnew, fp_by_addr, "imu", IMU_CUTOUT[0], IMU_CUTOUT[1], 0, args.force)

    # ---- Mainland functional zones ----
    # The cutouts consume the centre.  These zones keep parts inside the
    # 42x42 mainland / handle-root substrate while leaving routing corridors
    # beside the IMU and MCU pads.
    power_x_a = 15.0
    power_x_b = 19.2
    power_y = [-7.2, -2.8, 1.6, 6.0]
    power_zone = {
        # Load switch / latch cluster, close to MCU control pins.
        "power.q_power":          (power_x_a, power_y[0], 90),
        "power.d_button":         (power_x_b, power_y[0], 0),
        "power.q_latch":          (power_x_a, power_y[1], 90),
        "power.r_gate":           (power_x_b, power_y[1], 0),
        "power.r_latch_pd":       (power_x_a, power_y[2], 0),
        "power.r_button_series":  (power_x_b, power_y[2], 90),
        "power.r_button_pullup":  (power_x_a, power_y[3], 90),
        "power.r_en_pullup":      (power_x_b, power_y[3], 90),
    }
    moved += place_map(pcbnew, fp_by_addr, power_zone, args.force)

    regulator_zone = {
        # Regulator parts use the right-top mainland pocket beside the IMU.
        # This keeps the crowded MCU X+ corridor mostly for switch/latch nets.
        "power.ldo":              (14.0, -20.6, 90),
        "power.c_in":             (18.3, -20.6, 0),
        "power.c_out":            (18.3, -16.5, 0),
    }
    moved += place_map(pcbnew, fp_by_addr, regulator_zone, args.force)

    sense_led_zone = {
        # Battery sense and LED input passives live in the left-top mainland
        # pocket.  Avoid putting extra component height in the handle-root
        # strip and leave MCU antenna-side routing space below.
        "battery.r_top":          (-18.0, -20.6, 0),
        "battery.r_bottom":       (-13.8, -20.6, 0),
        "battery.c_filter":       (-18.0, -16.5, 0),
        "led_c_supply":           (-13.8, -16.5, 0),
        "led_r_data":             (-16.0, -12.4, 90),
    }
    moved += place_map(pcbnew, fp_by_addr, sense_led_zone, args.force)

    bringup_handle_root = {
        # Test pads live above the handle so the shell does not need extra
        # pockets for small passives.  Keep below the centre screw clearance.
        "bringup.gnd_pad":        (-6.0, 33.0, 0),
        "bringup.vcc_pad":        (-2.0, 33.0, 0),
        "bringup.vbat_pad":       (2.0, 33.0, 0),
        "bringup.uart_tx_pad":    (6.0, 33.0, 0),
        "bringup.uart_rx_pad":    (-6.0, 38.0, 0),
        "bringup.en_pad":         (-2.0, 38.0, 0),
        "bringup.boot_pad":       (2.0, 38.0, 0),
        "bringup.pwr_latch_pad":  (6.0, 38.0, 0),
        "bringup.imu_key_pad":    (-6.0, 43.0, 0),
        "bringup.imu_gpio_pad":   (-2.0, 43.0, 0),
        "bringup.imu_vddio_pad":  (2.0, 43.0, 0),
        "bringup.vbus_pad":       (6.0, 43.0, 0),
        "bringup.vbat_sense_pad": (-2.0, 48.0, 0),
        "bringup.led_data_pad":   (2.0, 48.0, 0),
    }
    moved += place_map(pcbnew, fp_by_addr, bringup_handle_root, args.force)

    pzt_mainland = {
        # PZT support parts start in remote staging groups outside the board.
        # They are deliberately easy to box-select and drag onto docks/manually.
        "pzt_tl.series_resistor": (-58.0, -78.0, 0),
        "pzt_tl.bleed_resistor":  (-54.0, -78.0, 0),
        "pzt_tl.clamp_diode":     (-50.0, -78.0, 0),
        "pzt_tr.series_resistor": (50.0, -78.0, 0),
        "pzt_tr.bleed_resistor":  (54.0, -78.0, 0),
        "pzt_tr.clamp_diode":     (58.0, -78.0, 0),
        "pzt_bl.series_resistor": (-64.0, 58.0, 0),
        "pzt_bl.bleed_resistor":  (-60.0, 58.0, 0),
        "pzt_bl.clamp_diode":     (-56.0, 58.0, 0),
        "pzt_br.series_resistor": (56.0, 58.0, 0),
        "pzt_br.bleed_resistor":  (60.0, 58.0, 0),
        "pzt_br.clamp_diode":     (64.0, 58.0, 0),
    }
    moved += place_map(pcbnew, fp_by_addr, pzt_mainland, args.force)

    # ---- Handle tail pads ----
    tail = {
        "tail.bat_plus_pad": (-6.0, 66.0, 0),
        "tail.gnd_pad":      (-2.0, 66.0, 0),
        "tail.led_plus_pad": ( 2.0, 66.0, 0),
        "tail.led_din_pad":  ( 6.0, 66.0, 0),
        "tail.button_pad":   (-6.0, 72.0, 0),
        "tail.usb_vbus_pad": (-2.0, 72.0, 0),
        "tail.usb_dp_pad":   ( 2.0, 72.0, 0),
        "tail.usb_dn_pad":   ( 6.0, 72.0, 0),
    }
    for addr, (x, y, rot) in tail.items():
        moved += move_one(pcbnew, fp_by_addr, addr, x, y, rot, args.force)

    # ---- Summary ----
    labelled, visible_labels = apply_readable_text(pcbnew, board)
    scaled = apply_model_scales(board)
    net_assigned, net_source = sync_nets_from_recent_ato_backup(pcbnew, board)
    if not args.place_docks:
        save_board(board, args.board)
        print(f"4b. 放置: 移动了 {moved} 个 atopile 封装到机械定位点")
        print(f"4c. 文本: 应用了 {labelled} 个可读Reference, 显示 {visible_labels} 个关键标签, 隐藏Value")
        print(f"4d. 3D: 应用了 {scaled} 个模块模型缩放修正")
        if net_source:
            print(f"4e. 网络: 从 {net_source.name} 同步了 {net_assigned} 个焊盘网络")
        print(f"    总共 {len(fp_by_addr)} 个带 atopile_address 的封装")
        print(f"    功能区: 开关锁存在MCU X+侧, LDO在右上大陆, LED/电池检测在左上大陆, 测试点在拍柄上方")
        print(f"    PZT小器件: 已放到四个栈道入口附近; PZT信号/GND焊盘保持当前位置")
        print(f"    PZT码头焊盘: 使用 --place-docks 可按机械点重新放置")
        return

    # PZT wire pads only (with --place-docks).  The small support parts are
    # already placed on mainland gangway entrances above.
    for pzt in params["components"]["piezo"]:
        pid = pzt["id"]
        key = pid.lower()
        x, y0 = pzt["position"]
        y = -y0
        (ux, uy), (nx, ny), slot_rot = slot_basis(x, y)
        lead_base = (x + ux * 13.5, y + uy * 13.5)
        sig = (lead_base[0] - nx * 2.35, lead_base[1] - ny * 2.35)
        gnd = (lead_base[0] + nx * 2.35, lead_base[1] + ny * 2.35)

        moved += move_one(pcbnew, fp_by_addr, f"{key}.pzt_signal_pad", sig[0], sig[1], slot_rot, args.force)
        moved += move_one(pcbnew, fp_by_addr, f"{key}.pzt_gnd_pad", gnd[0], gnd[1], slot_rot, args.force)

    labelled, visible_labels = apply_readable_text(pcbnew, board)
    scaled = apply_model_scales(board)
    net_assigned, net_source = sync_nets_from_recent_ato_backup(pcbnew, board)
    save_board(board, args.board)
    print(f"4b. 放置: 移动了 {moved} 个 atopile 封装到机械定位点 (含 PZT 信号/GND码头焊盘)")
    print(f"4c. 文本: 应用了 {labelled} 个可读Reference, 显示 {visible_labels} 个关键标签, 隐藏Value")
    print(f"4d. 3D: 应用了 {scaled} 个模块模型缩放修正")
    if net_source:
        print(f"4e. 网络: 从 {net_source.name} 同步了 {net_assigned} 个焊盘网络")


if __name__ == "__main__":
    main()
