#!/usr/bin/env python3
"""Step 1 — 清空 PCB 并绘制 SCAD 腔体参考线和 X±/Y± 坐标标记。

破坏性操作：清除所有封装、走线/过孔、覆铜区和图形。
然后根据 SCAD 中定义的腔体形状（pcb_main_cavity、rigid_pcb_cavity、
piezo_pockets）逐项绘制到 Dwgs.User，附以 M2 参照孔和方向标记。
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import (
    circle,
    load_board,
    mk,
    polyline,
    rect,
    save_board,
    shape_line,
    xy,
)
from pcb.tools.mech_geometry import (
    M2_CLEARANCE_HOLES,
    SCAD_CAVITY_SHAPES,
    SCAD_SLOT_POINTS,
    SCAD_TO_KICAD_Y_OFFSET,
    slot_scad_to_kicad,
)

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"

# ===== 分区：方法/工具 =====


def add_text(pcbnew, board, text: str, x: float, y: float, size: float = 3.0) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetLayer(pcbnew.Dwgs_User)
    item.SetText(text)
    item.SetPosition(xy(pcbnew, x, y))
    item.SetTextHeight(mk(size))
    item.SetTextWidth(mk(size))
    item.SetTextThickness(mk(0.25))
    board.Add(item)


def clear_board(board, *, keep_parts: bool = False) -> dict[str, int]:
    """清空板。keep_parts=True 时只清 Dwgs.User 参考线，保留封装/走线/区。"""
    import pcbnew

    footprints = list(board.GetFootprints())
    tracks = list(board.GetTracks())
    zones = [board.GetArea(i) for i in range(board.GetAreaCount())]
    drawings = list(board.GetDrawings())

    removed = {"footprints": 0, "tracks_vias": 0, "zones": 0, "drawings": 0}

    if keep_parts:
        for drawing in drawings:
            if drawing.GetLayer() == pcbnew.Dwgs_User:
                board.Remove(drawing)
                removed["drawings"] += 1
        return removed

    for track in tracks:
        board.Remove(track)
        removed["tracks_vias"] += 1

    for zone in zones:
        board.Remove(zone)
        removed["zones"] += 1

    for drawing in drawings:
        board.Remove(drawing)
        removed["drawings"] += 1

    for fp in footprints:
        board.Remove(fp)
        removed["footprints"] += 1

    return removed


# ===== 分区：公开 API =====


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 1: 清空 PCB 并绘制 SCAD 腔体参考线 + X±/Y± 标记")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument(
        "--keep-parts",
        action="store_true",
        help="只重绘 Dwgs.User 参考线，保留封装/走线/覆铜（不全盘清空）",
    )
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    removed = clear_board(board, keep_parts=args.keep_parts)

    # ---- SCAD 腔体形状 — 逐项从 SCAD 数据绘制到 Dwgs.User ----
    # 所有腔体形状直接从 SCAD 解析（paddle_shell.scad 中的 _cutouts 模块），
    # 不做人工计算。每个 SCAD 坐标通过 slot_scad_to_kicad 转换为 KiCad 坐标。
    pzt_count = 0
    for shape in SCAD_CAVITY_SHAPES:
        stype = shape["type"]
        label = shape["label"]
        if stype == "rect":
            sc, ss = shape["scad_center"], shape["scad_size"]
            kx, ky = slot_scad_to_kicad(sc)
            rect(pcbnew, board, pcbnew.Dwgs_User, kx, ky, ss[0], ss[1], 0.25)
        elif stype == "polygon":
            contour = [slot_scad_to_kicad(p) for p in shape["scad_points"]]
            polyline(pcbnew, board, pcbnew.Dwgs_User, contour, 0.18)
        elif stype == "circle":
            kx, ky = slot_scad_to_kicad(shape["scad_center"])
            circle(pcbnew, board, pcbnew.Dwgs_User, kx, ky, shape["scad_radius"], 0.12)
            pzt_count += 1
        print(f"  SCAD腔体: {label}")

    # ---- M2 螺丝参照孔 ----
    for hole_x, hole_y, hole_r in M2_CLEARANCE_HOLES:
        circle(pcbnew, board, pcbnew.Dwgs_User, hole_x, hole_y, hole_r, 0.12)

    # ---- 方向标记：基于 SCAD 槽轮廓的 BBox ----
    contour = [slot_scad_to_kicad(p) for p in SCAD_SLOT_POINTS]
    xs = [p[0] for p in contour]
    ys = [p[1] for p in contour]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2

    # 中心十字 + 方向箭头
    arrow = 8.0
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, cy), (cx + arrow, cy), 0.15)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, cy), (cx, cy - arrow), 0.15)

    # BBox 边缘刻度线
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (xmin - 4.0, cy), (xmin + 4.0, cy), 0.12)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (xmax - 4.0, cy), (xmax + 4.0, cy), 0.12)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, ymin - 4.0), (cx, ymin + 4.0), 0.12)
    shape_line(pcbnew, board, pcbnew.Dwgs_User, (cx, ymax - 4.0), (cx, ymax + 4.0), 0.12)

    # X± / Y± 文本标记
    add_text(pcbnew, board, "X+", xmax + 6.0, cy, 3.0)
    add_text(pcbnew, board, "X-", xmin - 14.0, cy, 3.0)
    add_text(pcbnew, board, "Y+", cx + 2.0, ymin - 8.0, 3.0)
    add_text(pcbnew, board, "Y-", cx + 2.0, ymax + 6.0, 3.0)

    save_board(board, args.board)

    print(f"=== Step 1 完成 ===")
    print(f"清除了: {removed}")
    print(f"SCAD→KiCad Y偏移: {SCAD_TO_KICAD_Y_OFFSET:.2f} mm")
    print(f"SCAD腔体形状数: {len(SCAD_CAVITY_SHAPES)}")
    print(f"  其中 rect: {sum(1 for s in SCAD_CAVITY_SHAPES if s['type']=='rect')}")
    print(f"  其中 polygon: {sum(1 for s in SCAD_CAVITY_SHAPES if s['type']=='polygon')}")
    print(f"  其中 circle: {pzt_count}")
    print(f"参考轮廓 BBox: X=[{xmin:.2f}, {xmax:.2f}] Y=[{ymin:.2f}, {ymax:.2f}]")
    print(f"中心: ({cx:.2f}, {cy:.2f})")
    print(f"M2参考孔: {len(M2_CLEARANCE_HOLES)} 个圆")
    print(f"方向标记: X± Y± 已标注")


if __name__ == "__main__":
    main()
