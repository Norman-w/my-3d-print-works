#!/usr/bin/env python3
"""Step 3 — Refresh MCU and IMU module body cutouts on Edge.Cuts.

The cutouts are rectangular openings for the ESP32-C6-WROOM-1 and ICM-948
embedded modules.  Each opening is the module outside dimensions plus a
small assembly clearance except on castellated solder edges.

This step removes only the Edge.Cuts geometry it owns, then redraws it. The
PCB substrate outline from Step 2 remains intact.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import circle, load_board, rect, save_board
from pcb.tools.mech_geometry import (
    ESP32_CUTOUT,
    IMU_CUTOUT,
    MODULE_CUTOUT_CLEARANCE,
    PCB_CLEARANCE_HOLES,
)

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
IMU_RULE_AREA_NAME = "IMU_EMBEDDED_CASTELLATED_EDGE"
IMU_RULE_AREA_MARGIN = 1.0


def _mm(value: int) -> float:
    return value / 1_000_000


def _near(a: tuple[float, float], b: tuple[float, float], tol: float = 0.02) -> bool:
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def _rect_edges(spec: tuple[float, float, float, float]):
    cx, cy, width, height = spec
    x1, x2 = cx - width / 2, cx + width / 2
    y1, y2 = cy - height / 2, cy + height / 2
    return [
        ((x1, y1), (x2, y1)),
        ((x2, y1), (x2, y2)),
        ((x2, y2), (x1, y2)),
        ((x1, y2), (x1, y1)),
    ]


def remove_generated_cutouts(pcbnew, board) -> int:
    """Remove only the module cutouts and screw holes owned by this step."""
    expected_edges = _rect_edges(ESP32_CUTOUT) + _rect_edges(IMU_CUTOUT)
    removed = 0

    for drawing in list(board.GetDrawings()):
        if drawing.GetLayer() != pcbnew.Edge_Cuts:
            continue

        shape = drawing.GetShape()
        if shape == pcbnew.SHAPE_T_SEGMENT:
            start = (_mm(drawing.GetStart().x), _mm(drawing.GetStart().y))
            end = (_mm(drawing.GetEnd().x), _mm(drawing.GetEnd().y))
            if any((_near(start, a) and _near(end, b)) or (_near(start, b) and _near(end, a))
                   for a, b in expected_edges):
                board.Remove(drawing)
                removed += 1
                continue

        if shape == pcbnew.SHAPE_T_CIRCLE:
            center = (_mm(drawing.GetCenter().x), _mm(drawing.GetCenter().y))
            end = (_mm(drawing.GetEnd().x), _mm(drawing.GetEnd().y))
            radius = ((end[0] - center[0]) ** 2 + (end[1] - center[1]) ** 2) ** 0.5
            if any(_near(center, (x, y)) and abs(radius - r) <= 0.02
                   for x, y, r in PCB_CLEARANCE_HOLES):
                board.Remove(drawing)
                removed += 1

    return removed


def _zone_id_after(content: str) -> int:
    ids = [int(match.group(1)) for match in re.finditer(r'\(zone_id (\d+)\)', content)]
    return (max(ids) if ids else 0) + 1


def _inject_imu_rule_area(board_path: Path) -> None:
    """Keep the IMU custom-rule area aligned with the generated cutout."""
    content = board_path.read_text()
    content = re.sub(
        rf'\n\t\(zone\n\t\t\(zone_id \d+\)\n\t\t\(name "{re.escape(IMU_RULE_AREA_NAME)}"\).*?\n\t\)',
        '',
        content,
        flags=re.S,
    )

    cx, cy, width, height = IMU_CUTOUT
    margin = IMU_RULE_AREA_MARGIN
    x1, x2 = cx - width / 2 - margin, cx + width / 2 + margin
    y1, y2 = cy - height / 2 - margin, cy + height / 2 + margin
    zone_id = _zone_id_after(content)
    block = f"""
\t(zone
\t\t(zone_id {zone_id})
\t\t(name "{IMU_RULE_AREA_NAME}")
\t\t(keepout)
\t\t(layers "F.Cu" "B.Cu")
\t\t(hatch edge 0.508)
\t\t(priority 100)
\t\t(connect_pads no)
\t\t(min_thickness 0.15)
\t\t(filled_areas_thickness no)
\t\t(fill yes (mode solid) (thermal_gap 0.508) (thermal_bridge_width 0.508))
\t\t(polygon
\t\t\t(pts
\t\t\t\t(xy {x1:.6f} {y1:.6f}) (xy {x2:.6f} {y1:.6f}) (xy {x2:.6f} {y2:.6f}) (xy {x1:.6f} {y2:.6f})
\t\t\t)
\t\t)
\t)"""
    insert_at = content.rfind(")\n")
    if insert_at < 0:
        raise RuntimeError(f"Unable to find PCB closing parenthesis in {board_path}")
    board_path.write_text(content[:insert_at + 1] + block + "\n" + content[insert_at + 1:])


# ===== 分区：公开 API =====
def main() -> None:
    parser = argparse.ArgumentParser(description="Step 3: Append MCU and IMU module cutouts to Edge.Cuts")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)

    removed = remove_generated_cutouts(pcbnew, board)
    rect(pcbnew, board, pcbnew.Edge_Cuts, *ESP32_CUTOUT, 0.10)
    rect(pcbnew, board, pcbnew.Edge_Cuts, *IMU_CUTOUT, 0.10)
    for hole_x, hole_y, hole_r in PCB_CLEARANCE_HOLES:
        circle(pcbnew, board, pcbnew.Edge_Cuts, hole_x, hole_y, hole_r, 0.10)

    save_board(board, args.board)
    _inject_imu_rule_area(args.board)

    print(f"=== Step 3 完成 ===")
    print(f"模块开孔间隙 (单边): {MODULE_CUTOUT_CLEARANCE:.2f} mm")
    print(f"ESP32 开孔: 中心=({ESP32_CUTOUT[0]:.1f}, {ESP32_CUTOUT[1]:.1f}) "
          f"尺寸=({ESP32_CUTOUT[2]:.2f}×{ESP32_CUTOUT[3]:.2f}) mm")
    print(f"IMU 开孔:  中心=({IMU_CUTOUT[0]:.1f}, {IMU_CUTOUT[1]:.1f}) "
          f"尺寸=({IMU_CUTOUT[2]:.2f}×{IMU_CUTOUT[3]:.2f}) mm")
    print(f"PCB螺丝让位孔: {len(PCB_CLEARANCE_HOLES)} 个")
    print(f"刷新旧开孔图元: {removed} 个")
    print(f"IMU规则区域: {IMU_RULE_AREA_NAME}")
    print(f"注意: 开孔已附加到 Edge.Cuts，基材轮廓保留不变")


if __name__ == "__main__":
    main()
