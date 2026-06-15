#!/usr/bin/env python3
"""Step 4.2 — Restore PZT dock component positions from the snapshot file.

Reads dock_snapshot.json (created by step4.1) and places every listed
footprint at its recorded position.  If no snapshot exists the script
prints a warning and exits without modifying the board.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rigid_pcb.tools.kicad_update_utils import load_board, save_board, xy

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"
SNAPSHOT = ROOT / "rigid_pcb" / "layouts" / "default" / "dock_snapshot.json"


# ===== 分区：方法/工具 =====

def _address(fp) -> str | None:
    if not fp.HasFieldByName("atopile_address"):
        return None
    return fp.GetFieldByName("atopile_address").GetText()


# ===== 分区：公开 API =====

def main() -> None:
    import pcbnew

    if not SNAPSHOT.exists():
        print(f"4.2 — 未找到 {SNAPSHOT.name}，请先运行 step4.1 备份码头位置")
        sys.exit(1)

    board = load_board(pcbnew, DEFAULT_BOARD)
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    lookup = {e["addr"]: e for e in data}
    fp_by_addr = {addr: fp for fp in board.GetFootprints() if (addr := _address(fp))}

    moved = 0
    for addr, entry in lookup.items():
        fp = fp_by_addr.get(addr)
        if fp is None:
            continue
        fp.SetPosition(xy(pcbnew, entry["x"], entry["y"]))
        fp.SetOrientationDegrees(entry["rot"])
        moved += 1

    save_board(board, DEFAULT_BOARD)
    print(f"4.2 — 从 {SNAPSHOT.name} 恢复了 {moved} 个 PZT 码头组件位置")

    # 注入螺丝孔 keepout zone（PCB_CLEARANCE_HOLES 从 SCAD 解析，无需手动维护）
    _inject_keepout_from_mech(DEFAULT_BOARD)


def _inject_keepout_from_mech(board_path: Path):
    """在 pcbnew 保存后，文本注入螺丝孔 keepout zone（KiCadRoutingTools 自动识别）。"""
    from rigid_pcb.tools.mech_geometry import PCB_CLEARANCE_HOLES

    holes = PCB_CLEARANCE_HOLES
    if not holes:
        return

    import math, re

    content = board_path.read_text()
    max_zid = max((int(m.group(1)) for m in re.finditer(r'\(zone_id (\d+)\)', content)), default=0)
    keepout_blocks = []

    for hx, hy, hr in holes:
        n_seg = 48
        pts = " ".join(
            f"(xy {hx + hr * math.cos(2 * math.pi * i / n_seg):.6f} "
            f"{hy + hr * math.sin(2 * math.pi * i / n_seg):.6f})"
            for i in range(n_seg)
        )
        for layer in ("F.Cu", "B.Cu"):
            max_zid += 1
            keepout_blocks.append(
                f"  (zone\n"
                f"    (zone_id {max_zid})\n"
                f"    (keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))\n"
                f'    (layers "{layer}")\n'
                f"    (hatch edge 0.508)\n"
                f"    (priority 100)\n"
                f"    (connect_pads no)\n"
                f"    (min_thickness 0.15)\n"
                f"    (filled_areas_thickness no)\n"
                f"    (fill yes (mode solid) (thermal_gap 0.508) (thermal_bridge_width 0.508))\n"
                f"    (polygon\n"
                f"      (pts\n"
                f"        {pts}\n"
                f"      )\n"
                f"    )\n"
                f"  )"
            )

    insert_at = content.rfind(')\n')
    if insert_at < 0:
        insert_at = len(content)
    board_path.write_text(content[:insert_at + 1] + "\n" + "\n".join(keepout_blocks) + "\n" + content[insert_at + 1:])
    print(f"     螺丝孔 keepout: 注入了 {len(keepout_blocks)} 个 zone (F.Cu + B.Cu)")


if __name__ == "__main__":
    main()
