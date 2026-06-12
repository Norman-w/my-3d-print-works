"""Small helpers for incremental KiCad PCB updates.

These helpers deliberately update only the objects owned by one script at a
time.  The intent is to keep manual component placement and routing intact
while regenerating mechanical references, cutouts, or generated pads.
"""

from __future__ import annotations

import math
from pathlib import Path


MM = 1_000_000


def mk(value_mm: float) -> int:
    return int(round(value_mm * MM))


def xy(pcbnew, x: float, y: float):
    return pcbnew.VECTOR2I(mk(x), mk(y))


def load_board(pcbnew, path: Path):
    board = pcbnew.LoadBoard(str(path))
    if board is None:
        raise RuntimeError(f"Unable to load KiCad board: {path}")
    return board


def save_board(board, path: Path) -> None:
    board.Save(str(path))


def remove_drawings_on_layers(board, layers: set[int]) -> int:
    removed = 0
    for drawing in list(board.GetDrawings()):
        if drawing.GetLayer() in layers:
            board.Remove(drawing)
            removed += 1
    return removed


def shape_line(pcbnew, board, layer: int, a: tuple[float, float], b: tuple[float, float], width: float = 0.1):
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
    shape.SetLayer(layer)
    shape.SetStart(xy(pcbnew, *a))
    shape.SetEnd(xy(pcbnew, *b))
    shape.SetWidth(mk(width))
    board.Add(shape)
    return shape


def polyline(pcbnew, board, layer: int, points: list[tuple[float, float]], width: float = 0.1, closed: bool = True):
    if len(points) < 2:
        return
    pairs = zip(points, points[1:] + points[:1] if closed else points[1:])
    for a, b in pairs:
        shape_line(pcbnew, board, layer, a, b, width)


def rect(pcbnew, board, layer: int, cx: float, cy: float, w: float, h: float, width: float = 0.1):
    hw, hh = w / 2, h / 2
    polyline(
        pcbnew,
        board,
        layer,
        [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)],
        width,
        True,
    )


def circle(pcbnew, board, layer: int, cx: float, cy: float, r: float, width: float = 0.1):
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_CIRCLE)
    shape.SetLayer(layer)
    shape.SetCenter(xy(pcbnew, cx, cy))
    shape.SetEnd(xy(pcbnew, cx + r, cy))
    shape.SetWidth(mk(width))
    board.Add(shape)
    return shape


def scad_to_kicad(point: tuple[float, float]) -> tuple[float, float]:
    x, y = point
    return (x, -y)


def slot_basis(x: float, y: float, target: tuple[float, float] = (0.0, 5.0)):
    dx, dy = target[0] - x, target[1] - y
    mag = math.hypot(dx, dy) or 1.0
    ux, uy = dx / mag, dy / mag
    nx, ny = -uy, ux
    rot = math.degrees(math.atan2(uy, ux))
    return (ux, uy), (nx, ny), rot

