#!/usr/bin/env python3
"""Step 3 — Append MCU and IMU module body cutouts to Edge.Cuts.

The cutouts are rectangular openings for the ESP32-C6-WROOM-1 and ICM-948
embedded modules.  Each opening is the module outside dimensions plus a
small assembly clearance (0.20 mm per side).

This step APPENDS to Edge.Cuts — it does NOT clear anything, so the PCB
substrate outline from Step 2 remains intact.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import circle, load_board, rect, save_board
from rigid_pcb.tools.mech_geometry import (
    ESP32_CUTOUT,
    IMU_CUTOUT,
    MODULE_CUTOUT_CLEARANCE,
    PCB_CLEARANCE_HOLES,
)

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"


# ===== 分区：公开 API =====
def main() -> None:
    parser = argparse.ArgumentParser(description="Step 3: Append MCU and IMU module cutouts to Edge.Cuts")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)

    # Append only — do not clear Edge.Cuts
    rect(pcbnew, board, pcbnew.Edge_Cuts, *ESP32_CUTOUT, 0.10)
    rect(pcbnew, board, pcbnew.Edge_Cuts, *IMU_CUTOUT, 0.10)
    for hole_x, hole_y, hole_r in PCB_CLEARANCE_HOLES:
        circle(pcbnew, board, pcbnew.Edge_Cuts, hole_x, hole_y, hole_r, 0.10)

    save_board(board, args.board)

    print(f"=== Step 3 完成 ===")
    print(f"模块开孔间隙 (单边): {MODULE_CUTOUT_CLEARANCE:.2f} mm")
    print(f"ESP32 开孔: 中心=({ESP32_CUTOUT[0]:.1f}, {ESP32_CUTOUT[1]:.1f}) "
          f"尺寸=({ESP32_CUTOUT[2]:.2f}×{ESP32_CUTOUT[3]:.2f}) mm")
    print(f"IMU 开孔:  中心=({IMU_CUTOUT[0]:.1f}, {IMU_CUTOUT[1]:.1f}) "
          f"尺寸=({IMU_CUTOUT[2]:.2f}×{IMU_CUTOUT[3]:.2f}) mm")
    print(f"PCB螺丝让位孔: {len(PCB_CLEARANCE_HOLES)} 个")
    print(f"注意: 开孔已附加到 Edge.Cuts，基材轮廓保留不变")


if __name__ == "__main__":
    main()
