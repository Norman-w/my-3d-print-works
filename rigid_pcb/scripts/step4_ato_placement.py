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
COL_SPACING_Y = 3.5   # mm between component centres along a column
COL_MARGIN = 1.0       # extra margin inside keepout before first component


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
    if not args.place_docks:
        save_board(board, args.board)
        print(f"4b. 放置: 移动了 {moved} 个 atopile 封装到机械定位点")
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

    save_board(board, args.board)
    print(f"4b. 放置: 移动了 {moved} 个 atopile 封装到机械定位点 (含 PZT 码头)")


if __name__ == "__main__":
    main()
