#!/usr/bin/env python3
"""Step 4 — Normalize atopile footprints and place them at scaffold positions.

This step expects atopile has already produced footprints on the PCB (via
`atopile build`).  It does two things:

  4a. Normalize — fix empty library IDs and missing footprint attributes
      so KiCad and atopile can both decode the PCB correctly.
  4b. Place — move footprints tagged with `atopile_address` properties to
      their mechanical scaffold positions (MCU/IMU cutout centres, PZT
      signal-conditioning parts, tail pads, bring-up test pads).

By default only footprints still sitting at atopile's initial 10mm-grid
position are moved, so any manual KiCad placement survives.  Use --force
to re-snap everything.
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

    # ---- 4b: Place footprints at scaffold positions ----
    params = yaml.safe_load(PARAMS.read_text())
    fp_by_addr = {addr: fp for fp in board.GetFootprints() if (addr := address(fp))}

    if not fp_by_addr:
        print("4b. 警告: 未找到带 atopile_address 属性的封装")
        print("    请先运行 atopile build 生成封装，然后重新执行本步骤")
        save_board(board, args.board)
        return

    moved = 0

    # Core modules
    moved += move_one(pcbnew, fp_by_addr, "mcu", ESP32_CUTOUT[0], ESP32_CUTOUT[1], 0, args.force)
    moved += move_one(pcbnew, fp_by_addr, "imu", IMU_CUTOUT[0], IMU_CUTOUT[1], 0, args.force)

    # Central mainland components
    central = {
        "led.c_supply": (18.0, 14.0, 0),
        "led.r_data": (18.8, 8.0, 90),
        "power.q_power": (-17.2, 18.0, 90),
        "power.q_latch": (-17.2, 11.2, 90),
        "power.r_gate": (-12.5, 15.0, 0),
        "power.d_button": (-19.0, 15.0, 0),
        "power.r_button": (18.2, -2.8, 90),
        "power.r_latch_pd": (-18.4, 7.8, 0),
        "power.ldo": (-17.5, -4.8, 90),
        "power.c_in": (-18.7, -12.0, 0),
        "power.c_out": (-18.7, -15.2, 0),
    }
    for addr, (x, y, rot) in central.items():
        moved += move_one(pcbnew, fp_by_addr, addr, x, y, rot, args.force)

    # Handle tail pads
    tail = {
        "tail.bat_plus_pad": (-6.0, 74.5, 0),
        "tail.gnd_pad": (-2.0, 74.5, 0),
        "tail.led_plus_pad": (2.0, 74.5, 0),
        "tail.led_din_pad": (6.0, 74.5, 0),
        "tail.button_pad": (-4.0, 77.4, 0),
        "tail.usb_dp_pad": (0.0, 77.4, 0),
        "tail.usb_dn_pad": (4.0, 77.4, 0),
    }
    for addr, (x, y, rot) in tail.items():
        moved += move_one(pcbnew, fp_by_addr, addr, x, y, rot, args.force)

    # Bring-up test pads
    test_pads = {
        "bringup.vbat_pad": (-19.0, -2.0, 0),
        "bringup.vcc_pad": (-19.0, -5.0, 0),
        "bringup.gnd_pad": (-19.0, -8.0, 0),
        "bringup.uart_tx_pad": (-19.0, -11.0, 0),
        "bringup.uart_rx_pad": (-19.0, -14.0, 0),
        "bringup.en_pad": (19.0, -2.0, 0),
        "bringup.boot_pad": (19.0, -5.0, 0),
        "bringup.pwr_latch_pad": (19.0, -8.0, 0),
        "bringup.imu_key_pad": (19.0, -11.0, 0),
        "bringup.imu_gpio_pad": (19.0, -14.0, 0),
        "bringup.led_data_pad": (15.5, -17.0, 0),
        "bringup.vbus_pad": (19.0, -17.0, 0),
    }
    for addr, (x, y, rot) in test_pads.items():
        moved += move_one(pcbnew, fp_by_addr, addr, x, y, rot, args.force)

    if not args.place_docks:
        save_board(board, args.board)
        print(f"4b. 放置: 移动了 {moved} 个 atopile 封装到机械定位点")
        print(f"    总共 {len(fp_by_addr)} 个带 atopile_address 的封装")
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
