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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import circle, load_board, rect, save_board, xy
from pcb.tools.mech_geometry import (
    ESP32_CUTOUT,
    IMU_CUTOUT,
    MODULE_CUTOUT_CLEARANCE_LONG,
    MODULE_CUTOUT_CLEARANCE_SHORT,
    PCB_CLEARANCE_HOLES,
)

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
IMU_RULE_AREA_NAME = "IMU_EMBEDDED_CASTELLATED_EDGE"
IMU_RULE_AREA_MARGIN = 1.0
# 半孔边历史间隙（含手改/旧版），用于清掉叠画的 Edge.Cuts
_LEGACY_LONG_CLEARANCES = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35)
_MCU_BODY = (25.5, 18.0)
_IMU_BODY = (18.5, 13.0)


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


def _all_known_cutout_specs() -> list[tuple[float, float, float, float]]:
    """当前 + 历史开窗尺寸，避免改间隙后旧 Edge.Cuts 叠在板上。"""
    specs: list[tuple[float, float, float, float]] = [ESP32_CUTOUT, IMU_CUTOUT]
    mcu_cx, mcu_cy = ESP32_CUTOUT[0], ESP32_CUTOUT[1]
    imu_cx, imu_cy = IMU_CUTOUT[0], IMU_CUTOUT[1]
    short = MODULE_CUTOUT_CLEARANCE_SHORT
    for long_c in _LEGACY_LONG_CLEARANCES:
        specs.append((
            mcu_cx, mcu_cy,
            _MCU_BODY[0] + short * 2,
            _MCU_BODY[1] + long_c * 2,
        ))
        specs.append((
            imu_cx, imu_cy,
            _IMU_BODY[0] + short * 2,
            _IMU_BODY[1] + long_c * 2,
        ))
    # 旧文档/实验里出现过的非整间隙高度
    for h in (13.0, 13.4, 13.9, 18.4):
        if h < 16:
            specs.append((imu_cx, imu_cy, _IMU_BODY[0] + short * 2, h))
        else:
            specs.append((mcu_cx, mcu_cy, _MCU_BODY[0] + short * 2, h))
    return specs


def _segment_matches_module_cutout(
    start: tuple[float, float],
    end: tuple[float, float],
    cx: float,
    cy: float,
    width: float,
    height_min: float,
    height_max: float,
    tol: float = 0.04,
) -> bool:
    """任一半孔开窗矩形边（高度可在历史范围内变化）都算生成物，应删掉。"""
    x1, x2 = cx - width / 2, cx + width / 2
    xs, xe = (start[0], end[0]) if start[0] <= end[0] else (end[0], start[0])
    ys, ye = (start[1], end[1]) if start[1] <= end[1] else (end[1], start[1])

    if abs(start[1] - end[1]) <= tol:  # 水平边
        y = (start[1] + end[1]) / 2
        if abs(xs - x1) <= tol and abs(xe - x2) <= tol:
            height = abs(y - cy) * 2
            return height_min - tol <= height <= height_max + tol
        return False

    if abs(start[0] - end[0]) <= tol:  # 竖直边
        x = (start[0] + end[0]) / 2
        if abs(x - x1) > tol and abs(x - x2) > tol:
            return False
        height = ye - ys
        mid_y = (ys + ye) / 2
        return (
            height_min - tol <= height <= height_max + tol
            and abs(mid_y - cy) <= tol
        )

    return False


def remove_generated_cutouts(pcbnew, board) -> int:
    """Remove only the module cutouts and screw holes owned by this step."""
    expected_edges: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for spec in _all_known_cutout_specs():
        expected_edges.extend(_rect_edges(spec))

    # 几何兜底：同中心、同短边宽、高度在本体~本体+0.8 之间的边一律清除
    mcu_w = _MCU_BODY[0] + MODULE_CUTOUT_CLEARANCE_SHORT * 2
    imu_w = _IMU_BODY[0] + MODULE_CUTOUT_CLEARANCE_SHORT * 2
    mcu_h_lo, mcu_h_hi = _MCU_BODY[1], _MCU_BODY[1] + 0.80
    imu_h_lo, imu_h_hi = _IMU_BODY[1], _IMU_BODY[1] + 0.80

    removed = 0
    for drawing in list(board.GetDrawings()):
        if drawing.GetLayer() != pcbnew.Edge_Cuts:
            continue

        shape = drawing.GetShape()
        if shape == pcbnew.SHAPE_T_SEGMENT:
            start = (_mm(drawing.GetStart().x), _mm(drawing.GetStart().y))
            end = (_mm(drawing.GetEnd().x), _mm(drawing.GetEnd().y))
            exact = any(
                (_near(start, a) and _near(end, b)) or (_near(start, b) and _near(end, a))
                for a, b in expected_edges
            )
            fuzzy = (
                _segment_matches_module_cutout(
                    start, end, ESP32_CUTOUT[0], ESP32_CUTOUT[1], mcu_w, mcu_h_lo, mcu_h_hi
                )
                or _segment_matches_module_cutout(
                    start, end, IMU_CUTOUT[0], IMU_CUTOUT[1], imu_w, imu_h_lo, imu_h_hi
                )
            )
            if exact or fuzzy:
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


def _strip_named_zone_blocks(board_path: Path, zone_name: str) -> int:
    """Remove generated top-level zone blocks by name before KiCad reloads them."""
    lines = board_path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    removed = 0

    idx = 0
    while idx < len(lines):
        if lines[idx] != "\t(zone\n":
            out.append(lines[idx])
            idx += 1
            continue

        start = idx
        idx += 1
        while idx < len(lines) and lines[idx] != "\t)\n":
            idx += 1
        if idx < len(lines):
            idx += 1

        block = lines[start:idx]
        if any(f'(name "{zone_name}")' in line for line in block):
            removed += 1
            continue
        out.extend(block)

    if removed:
        board_path.write_text("".join(out), encoding="utf-8")
    return removed


def _add_imu_rule_area(pcbnew, board) -> None:
    """放宽板边间隙的规则区：盖住 IMU 开窗 + MCU/IMU 之间 FR4 走廊（含两侧半孔焊盘）。

    否则默认 edge_clearance=0.5mm 会把贴开窗边的半孔焊盘当成「墙」，
    交互布线吸不住、走不过 MCU↔IMU 的 UART。
    """
    margin = IMU_RULE_AREA_MARGIN
    imu_cx, imu_cy, imu_w, imu_h = IMU_CUTOUT
    mcu_cx, mcu_cy, mcu_w, mcu_h = ESP32_CUTOUT

    # 宽度取两开窗外包 + margin；纵向从 IMU 底边扩到 MCU 南沿焊盘外侧
    x1 = min(imu_cx - imu_w / 2, mcu_cx - mcu_w / 2) - margin
    x2 = max(imu_cx + imu_w / 2, mcu_cx + mcu_w / 2) + margin
    y1 = imu_cy - imu_h / 2 - margin
    y2 = mcu_cy - mcu_h / 2 + margin  # 伸进 MCU 开窗南缘，盖住 IO4/IO5 半孔

    zone = pcbnew.ZONE(board)
    zone.SetZoneName(IMU_RULE_AREA_NAME)
    zone.SetIsRuleArea(True)
    zone.SetAssignedPriority(100)
    zone.SetDoNotAllowTracks(False)
    zone.SetDoNotAllowVias(False)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowCopperPour(False)
    zone.SetDoNotAllowFootprints(False)
    zone.SetRuleAreaPlacementEnabled(False)
    layer_set = pcbnew.LSET()
    layer_set.AddLayer(pcbnew.F_Cu)
    layer_set.AddLayer(pcbnew.B_Cu)
    zone.SetLayerSet(layer_set)
    zone.AppendCorner(xy(pcbnew, x1, y1), -1)
    zone.AppendCorner(xy(pcbnew, x2, y1), -1)
    zone.AppendCorner(xy(pcbnew, x2, y2), -1)
    zone.AppendCorner(xy(pcbnew, x1, y2), -1)
    board.Add(zone)
    print(f"  规则区 {IMU_RULE_AREA_NAME}: "
          f"({x1:.2f},{y1:.2f})–({x2:.2f},{y2:.2f})")


# ===== 分区：公开 API =====
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Step 3: Replace MCU/IMU module cutouts on Edge.Cuts (not append)"
    )
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    removed_rule_areas = _strip_named_zone_blocks(args.board, IMU_RULE_AREA_NAME)
    board = load_board(pcbnew, args.board)

    removed = remove_generated_cutouts(pcbnew, board)
    rect(pcbnew, board, pcbnew.Edge_Cuts, *ESP32_CUTOUT, 0.10)
    rect(pcbnew, board, pcbnew.Edge_Cuts, *IMU_CUTOUT, 0.10)
    for hole_x, hole_y, hole_r in PCB_CLEARANCE_HOLES:
        circle(pcbnew, board, pcbnew.Edge_Cuts, hole_x, hole_y, hole_r, 0.10)
    _add_imu_rule_area(pcbnew, board)

    save_board(board, args.board)

    print(f"=== Step 3 完成 ===")
    print(f"模块开孔间隙: 短边={MODULE_CUTOUT_CLEARANCE_SHORT:.2f} mm, "
          f"半孔长边={MODULE_CUTOUT_CLEARANCE_LONG:.2f} mm")
    print(f"ESP32 开孔: 中心=({ESP32_CUTOUT[0]:.1f}, {ESP32_CUTOUT[1]:.1f}) "
          f"尺寸=({ESP32_CUTOUT[2]:.2f}×{ESP32_CUTOUT[3]:.2f}) mm")
    print(f"IMU 开孔:  中心=({IMU_CUTOUT[0]:.1f}, {IMU_CUTOUT[1]:.1f}) "
          f"尺寸=({IMU_CUTOUT[2]:.2f}×{IMU_CUTOUT[3]:.2f}) mm")
    print(f"PCB螺丝让位孔: {len(PCB_CLEARANCE_HOLES)} 个")
    print(f"清除旧开孔图元: {removed} 个（替换，非叠加）")
    print(f"刷新旧规则区域: {removed_rule_areas} 个")
    print(f"IMU规则区域: {IMU_RULE_AREA_NAME}")
    print(f"注意: 模块开孔已替换；基材外轮廓（step2）保留不变")


if __name__ == "__main__":
    main()
