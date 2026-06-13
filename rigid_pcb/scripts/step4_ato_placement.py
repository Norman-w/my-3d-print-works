#!/usr/bin/env python3
"""Step 4 — Normalize atopile footprints and place them at scaffold positions.

Layout zones (all positions derived from cutout edges + keepout offsets):

  MCU X+  — power-latch circuit + LED interface (2 columns)
  MCU X-  — bring-up test pads ONLY (1 column)
  IMU X-  — LDO filter capacitors (1 column)
  IMU X+  — remaining bring-up test pads (2 columns)
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

KEEPOUT = 1.5
COL_SPACING_Y = 5.0   # mm between component centres along a column
COL_MARGIN = 1.0       # extra margin inside keepout before first component
TEXT_THICKNESS = 0.10

READABLE_REFS = {
    "mcu": ("MCU_SGFK_C6", "SGFK ESP32-C6-N8"),
    "imu": ("IMU_IM948", "IM948"),
    "power.q_power": ("PW_Q_LOAD", "P-MOS load switch"),
    "power.q_latch": ("PW_Q_LATCH", "N-MOS latch"),
    "power.r_gate": ("PW_R_GATE_100K", "100k"),
    "power.r_button": ("PW_R_BTN_100K", "100k"),
    "power.r_latch_pd": ("PW_R_LATCH_PD_100K", "100k"),
    "power.d_button": ("PW_D_BTN", "Schottky"),
    "power.ldo": ("PW_LDO_3V3", "AP2112K-3.3"),
    "power.c_in": ("PW_C_IN_10U", "10uF"),
    "power.c_out": ("PW_C_OUT_10U", "10uF"),
    "led.r_data": ("LED_R_DATA_330R", "330R"),
    "led.c_supply": ("LED_C_SUP_100N", "100nF"),
    "led_r_data": ("LED_R_DATA_330R", "330R"),
    "led_c_supply": ("LED_C_SUP_100N", "100nF"),
    "tail.bat_plus_pad": ("TAIL_BAT_PLUS", "BAT+ wire"),
    "tail.gnd_pad": ("TAIL_GND", "GND wire"),
    "tail.led_plus_pad": ("TAIL_LED_PLUS", "LED+ wire"),
    "tail.led_din_pad": ("TAIL_LED_DIN", "LED DIN wire"),
    "tail.button_pad": ("TAIL_BTN", "button wire"),
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
}

PZT_READABLE_PREFIXES = {
    "pzt_tr": "PZT_TR",
    "pzt_tl": "PZT_TL",
    "pzt_br": "PZT_BR",
    "pzt_bl": "PZT_BL",
}

PZT_READABLE_PARTS = {
    "clamp_resistor": ("R_DIS_1M", "1M"),
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


def col_y(t: float, step: int) -> float:
    """Return Y for the nth position in a vertical column starting at *t* (north edge)."""
    return t + COL_MARGIN + step * COL_SPACING_Y


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

    # ── MCU X+ zone: power-latch + LED  (2 columns) ──
    # Col spacing inside zone: 3mm between columns
    rx_A = mcu["right"] + 2.0
    rx_B = mcu["right"] + 5.0
    ry   = mcu["top"]           # column start Y

    mcu_right = {
        # Col A (X=rx_A)
        "power.q_power":       (rx_A, col_y(ry, 0), 90),
        "power.q_latch":       (rx_A, col_y(ry, 1), 90),
        "power.ldo":           (rx_A, col_y(ry, 2), 90),
        "led.c_supply":        (rx_A, col_y(ry, 3), 0),
        "led.r_data":          (rx_A, col_y(ry, 4), 90),
        "led_c_supply":        (rx_A, col_y(ry, 3), 0),
        "led_r_data":          (rx_A, col_y(ry, 4), 90),
        # Col B (X=rx_B)
        "power.d_button":      (rx_B, col_y(ry, 0), 0),
        "power.r_gate":        (rx_B, col_y(ry, 1), 0),
        "power.r_latch_pd":    (rx_B, col_y(ry, 2), 0),
        "power.r_button":      (rx_B, col_y(ry, 3), 90),
    }
    for addr, (x, y, rot) in mcu_right.items():
        moved += move_one(pcbnew, fp_by_addr, addr, x, y, rot, args.force)

    # ── MCU X- zone: bring-up test pads ONLY (1 column) ──
    lx = mcu["left"] - 2.0
    ly = mcu["top"]
    mcu_left = {
        "bringup.gnd_pad":      (lx, col_y(ly, 0), 0),
        "bringup.vcc_pad":      (lx, col_y(ly, 1), 0),
        "bringup.vbat_pad":     (lx, col_y(ly, 2), 0),
        "bringup.uart_tx_pad":  (lx, col_y(ly, 3), 0),
        "bringup.uart_rx_pad":  (lx, col_y(ly, 4), 0),
    }
    for addr, (x, y, rot) in mcu_left.items():
        moved += move_one(pcbnew, fp_by_addr, addr, x, y, rot, args.force)

    # ── IMU X- zone: LDO filter capacitors (1 column) ──
    ilx = imu["left"] - 2.0
    ily = imu["top"]
    imu_left = {
        "power.c_in":   (ilx, col_y(ily, 0), 0),
        "power.c_out":  (ilx, col_y(ily, 1), 0),
    }
    for addr, (x, y, rot) in imu_left.items():
        moved += move_one(pcbnew, fp_by_addr, addr, x, y, rot, args.force)

    # ── IMU X+ zone: remaining bring-up test pads (2 columns) ──
    irx_A = imu["right"] + 2.0
    irx_B = imu["right"] + 5.0
    iry   = imu["top"]
    imu_right = {
        # Col A
        "bringup.en_pad":           (irx_A, col_y(iry, 0), 0),
        "bringup.pwr_latch_pad":    (irx_A, col_y(iry, 1), 0),
        "bringup.imu_gpio_pad":     (irx_A, col_y(iry, 2), 0),
        "bringup.led_data_pad":     (irx_A, col_y(iry, 3), 0),
        # Col B
        "bringup.boot_pad":         (irx_B, col_y(iry, 0), 0),
        "bringup.imu_key_pad":      (irx_B, col_y(iry, 1), 0),
        "bringup.vbus_pad":         (irx_B, col_y(iry, 2), 0),
    }
    for addr, (x, y, rot) in imu_right.items():
        moved += move_one(pcbnew, fp_by_addr, addr, x, y, rot, args.force)

    # ---- Handle tail pads ----
    tail = {
        "tail.bat_plus_pad": (-6.0, 74.5, 0),
        "tail.gnd_pad":      (-2.0, 74.5, 0),
        "tail.led_plus_pad": ( 2.0, 74.5, 0),
        "tail.led_din_pad":  ( 6.0, 74.5, 0),
        "tail.button_pad":   (-4.0, 77.4, 0),
        "tail.usb_dp_pad":   ( 0.0, 77.4, 0),
        "tail.usb_dn_pad":   ( 4.0, 77.4, 0),
    }
    for addr, (x, y, rot) in tail.items():
        moved += move_one(pcbnew, fp_by_addr, addr, x, y, rot, args.force)

    # ---- Summary ----
    labelled, visible_labels = apply_readable_text(pcbnew, board)
    scaled = apply_model_scales(board)
    if not args.place_docks:
        save_board(board, args.board)
        print(f"4b. 放置: 移动了 {moved} 个 atopile 封装到机械定位点")
        print(f"4c. 文本: 应用了 {labelled} 个可读Reference, 显示 {visible_labels} 个关键标签, 隐藏Value")
        print(f"4d. 3D: 应用了 {scaled} 个模块模型缩放修正")
        print(f"    总共 {len(fp_by_addr)} 个带 atopile_address 的封装")
        print(f"    MCU 相对: right({rx_A:.1f}/{rx_B:.1f}) left({lx:.1f})")
        print(f"    IMU 相对: right({irx_A:.1f}/{irx_B:.1f}) left({ilx:.1f})")
        print(f"    PZT 码头封装保持在当前位置 (使用 --place-docks 可同时放置)")
        return

    # PZT dock footprints (only with --place-docks)
    for pzt in params["components"]["piezo"]:
        pid = pzt["id"]
        key = pid.lower()
        x, y0 = pzt["position"]
        y = -y0
        (ux, uy), (nx, ny), slot_rot = slot_basis(x, y)
        part_rot = slot_rot - 90
        lead_base = (x + ux * 13.5, y + uy * 13.5)
        sig = (lead_base[0] - nx * 1.65, lead_base[1] - ny * 1.65)
        gnd = (lead_base[0] + nx * 1.65, lead_base[1] + ny * 1.65)
        rpos = (x + ux * 18.0, y + uy * 18.0)
        dpos = (x + ux * 23.5, y + uy * 23.5)

        moved += move_one(pcbnew, fp_by_addr, f"{key}.pzt_signal_pad", sig[0], sig[1], slot_rot, args.force)
        moved += move_one(pcbnew, fp_by_addr, f"{key}.pzt_gnd_pad", gnd[0], gnd[1], slot_rot, args.force)
        moved += move_one(pcbnew, fp_by_addr, f"{key}.clamp_resistor", rpos[0], rpos[1], slot_rot, args.force)
        moved += move_one(pcbnew, fp_by_addr, f"{key}.clamp_diode", dpos[0], dpos[1], part_rot, args.force)

    labelled, visible_labels = apply_readable_text(pcbnew, board)
    scaled = apply_model_scales(board)
    save_board(board, args.board)
    print(f"4b. 放置: 移动了 {moved} 个 atopile 封装到机械定位点 (含 PZT 码头)")
    print(f"4c. 文本: 应用了 {labelled} 个可读Reference, 显示 {visible_labels} 个关键标签, 隐藏Value")
    print(f"4d. 3D: 应用了 {scaled} 个模块模型缩放修正")


if __name__ == "__main__":
    main()
