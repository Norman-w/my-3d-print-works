"""Mechanical geometry shared by incremental KiCad update scripts.

Coordinates in this file are KiCad board coordinates in millimeters unless the
name explicitly says SCAD.  KiCad's Y axis is positive downward in the board
editor.

SCAD-derived values (screw positions, PZT cavities, mainland rectangle) are
parsed from enclosure/parameters.scad at import time so changing the SCAD
parameters automatically updates the KiCad toolchain.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

# ===== 分区：SCAD 参数解析 =====

_ROOT = Path(__file__).resolve().parents[2]


def _eval_scad_term(text: str, ctx: dict[str, object]) -> object:
    """Evaluate a single SCAD value (number, vector, or nested list)."""
    text = text.strip()

    # Nested list of vectors: [[...], [...], ...]
    if text.startswith("["):
        # Find matching closing bracket
        depth = 0
        end = 0
        for i, ch in enumerate(text):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        inner = text[1 : end - 1].strip()
        if inner.startswith("["):
            # List of vectors
            items = _split_top_level_commas(inner)
            return tuple(_eval_scad_term(it, ctx) for it in items)
        elif "," in inner:
            # Single vector: [x, y] or [x, y, z]
            parts = [p.strip() for p in inner.split(",")]
            return tuple(_safe_eval(p, ctx) for p in parts if p)

    # Scalar expression (number, possibly with arithmetic)
    return _safe_eval(text, ctx)


def _safe_eval(expr: str, ctx: dict[str, object]) -> float:
    """Evaluate a numeric expression, returning 0.0 on failure."""
    try:
        return eval(expr, {}, ctx)
    except Exception:
        return 0.0


def _split_top_level_commas(text: str) -> list[str]:
    """Split text at top-level commas, respecting bracket nesting."""
    items = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        items.append("".join(current).strip())
    return items


def _parse_scad_file(path: Path) -> dict[str, object]:
    """Extract top-level variable assignments from a SCAD file.

    Supports numbers, vectors ([x, y]), and nested lists of vectors
    ([[x0,y0], [x1,y1], ...]).  Line comments (//) are stripped before
    parsing.  Multi-line arrays are collapsed to single-line form.
    """
    text = path.read_text(encoding="utf-8")
    # Remove line comments
    clean = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
    # Collapse whitespace so multi-line arrays become single-line
    collapsed = re.sub(r"\s+", " ", clean).strip()

    result: dict[str, object] = {}
    # Match: name = value;  (non-greedy, stops at first ;)
    for m in re.finditer(r"(\w+)\s*=\s*(.+?);", collapsed):
        name = m.group(1)
        expr = m.group(2).strip()
        try:
            value = _eval_scad_term(expr, result)
            if value is not None:
                result[name] = value
        except Exception:
            pass

    return result


# Parse parameters.scad first (primary source for dimensions and geometry).
# Then parse paddle_shell.scad (for the PCB slot outline polygon).
# Merged in that order so parameters.scad values take precedence on overlap.
_PARAMS = _parse_scad_file(_ROOT / "enclosure" / "parameters.scad")
_SHELL_PARAMS = _parse_scad_file(_ROOT / "enclosure" / "paddle_shell.scad")
_PARAMS = {**_SHELL_PARAMS, **_PARAMS}  # parameters.scad wins on conflict

# ===== 分区：常量/配置 =====

# KiCad/SCAD Y 轴握手锚点: SCAD blade_ellipse_cy 映射到 KiCad 原点 (0,0)
SCAD_TO_KICAD_Y_OFFSET = float(_PARAMS.get("blade_ellipse_cy", -10.0))  # type: ignore[arg-type]
SUBSTRATE_EDGE_CLEARANCE = 0.30
SUBSTRATE_TAIL_MAX_Y = 78.0
PZT_CAVITY_CLEARANCE = 0.32
PZT_DOCK_RETREAT_BAND = 4.0
PZT_DOCK_RETREAT_STEP = 3.0
SUBSTRATE_EDGE_SAMPLE = 1.0

# PZT 腔体 — 圆心和半径均来自 SCAD
_pzt_radius = float(_PARAMS.get("piezo_disc_d", 20.5)) / 2  # type: ignore[arg-type]
PZT_CAVITIES_SCAD = [
    (float(p[0]), float(p[1]), _pzt_radius)  # type: ignore[index]
    for p in _PARAMS.get("piezo_positions", [])  # type: ignore[union-attr]
]

# 螺丝孔 — 直径来自 SCAD screw_d_boss，坐标来自 screw_positions
_screw_boss_d = float(_PARAMS.get("screw_d_boss", 5.5))  # type: ignore[arg-type]
SCREW_CLEARANCE_RADIUS = _screw_boss_d / 2.0 + 0.75  # boss 柱外 + 0.75mm 余量
SCREW_HOLES_SCAD = [
    (float(p[0]), float(p[1]))  # type: ignore[index]
    for p in _PARAMS.get("screw_positions", [])  # type: ignore[union-attr]
]

# 大陆区矩形 — 从 SCAD pcb_cavity_center + pcb_cavity_size 推算 KiCad 坐标
_cav_center = _PARAMS.get("pcb_cavity_center", (0, -1))  # type: ignore
_cav_size = _PARAMS.get("pcb_cavity_size", (42, 50))  # type: ignore
_ki_y = -float(_cav_center[1]) + SCAD_TO_KICAD_Y_OFFSET  # type: ignore[index]  # SCAD +Y=拍头, KiCad -Y=拍头
MAINLAND_RECT = (
    float(_cav_center[0]),  # type: ignore[index]
    _ki_y,
    float(_cav_size[0]),  # type: ignore[index]
    float(_cav_size[1]),  # type: ignore[index]
)


def slot_scad_to_kicad(point: tuple[float, float]) -> tuple[float, float]:
    """Convert SCAD slot coordinates into the KiCad mechanical reference frame."""
    x, y = point
    return (x, -y + SCAD_TO_KICAD_Y_OFFSET)


# 拍形外轮廓槽点 — 从 paddle_shell.scad 的 rigid_pcb_slot_points 解析。
# 该多边形定义了 PCB 在球拍壳体中的最大投影轮廓（37 个顶点）。
# SCAD 中用 polygon(points=rigid_pcb_slot_points) 驱动腔体切割，
# KiCad 中用同一组点（经 slot_scad_to_kicad 转换）绘制参考线和 Edge.Cuts。
# 两边共享同一个数据源，修改 paddle_shell.scad 即可同步。
_shell_pts = _PARAMS.get("rigid_pcb_slot_points")
if _shell_pts is not None and len(_shell_pts) > 0:  # type: ignore[arg-type]
    SCAD_SLOT_POINTS = [
        (float(p[0]), float(p[1]))  # type: ignore[index]
        for p in _shell_pts  # type: ignore[union-attr]
    ]
else:
    # 回退：与 paddle_shell.scad 中当前值一致（2026-06-15）
    SCAD_SLOT_POINTS = [
        (9.00, -108.00), (-9.00, -108.00), (-9.00, -26.00),
        (-16.75, -26.00), (-29.99, -40.11), (-28.24, -41.75),
        (-35.08, -49.05), (-41.65, -42.90), (-34.81, -35.60),
        (-33.06, -37.24), (-21.00, -24.39), (-21.00, 16.00),
        (-19.48, 16.00), (-29.66, 35.62), (-31.62, 34.32),
        (-37.17, 42.64), (-29.68, 47.63), (-24.13, 39.31),
        (-26.15, 37.97), (-14.75, 16.00), (14.75, 16.00),
        (26.15, 37.97), (24.13, 39.31), (29.68, 47.63),
        (37.17, 42.64), (31.62, 34.32), (29.66, 35.62),
        (19.48, 16.00), (21.00, 16.00), (21.00, -24.39),
        (33.06, -37.24), (34.81, -35.60), (41.65, -42.90),
        (35.08, -49.05), (28.24, -41.75), (29.99, -40.11),
        (16.75, -26.00), (9.00, -26.00),
    ]

# ===== 分区：几何工具函数 =====


def _embedded_substrate_scad_points() -> list[tuple[float, float]]:
    """PCB substrate outline derived from the SCAD slot reference.

    Keep the dock/gangway/mainland points aligned to the SCAD slot so the PCB
    cannot drift outside the black reference frame.  Only shorten the handle
    tail, because the rigid PCB should stop inside the handle cavity.
    """
    points = list(SCAD_SLOT_POINTS)
    points[0] = (points[0][0], -88.00)
    points[1] = (points[1][0], -88.00)
    return points


def _polygon_points(poly) -> list[tuple[float, float]]:
    return [(round(x, 3), round(y, 3)) for x, y in poly]


def _signed_area(points: list[tuple[float, float]]) -> float:
    area = 0.0
    for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
        area += ax * by - bx * ay
    return area / 2.0


def _line_intersection(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> tuple[float, float] | None:
    ax, ay = a1
    bx, by = a2
    cx, cy = b1
    dx, dy = b2
    adx, ady = bx - ax, by - ay
    bdx, bdy = dx - cx, dy - cy
    denom = adx * bdy - ady * bdx
    if abs(denom) < 1e-9:
        return None
    t = ((cx - ax) * bdy - (cy - ay) * bdx) / denom
    return (ax + adx * t, ay + ady * t)


def _edge_inset_polygon(
    points: list[tuple[float, float]],
    distance: float,
) -> list[tuple[float, float]]:
    """Inset polygon by moving each edge along its inward normal.

    This preserves gangway/dock length much better than moving every vertex
    toward the mainland center.
    """
    if len(points) < 3:
        return points

    area = _signed_area(points)
    inward_sign = 1.0 if area > 0 else -1.0
    offset_edges = []
    for a, b in zip(points, points[1:] + points[:1]):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy) or 1.0
        nx, ny = (-dy / length * inward_sign, dx / length * inward_sign)
        offset_edges.append(
            (
                (ax + nx * distance, ay + ny * distance),
                (bx + nx * distance, by + ny * distance),
            )
        )

    inset = []
    count = len(offset_edges)
    for i in range(count):
        prev_edge = offset_edges[i - 1]
        edge = offset_edges[i]
        intersection = _line_intersection(
            prev_edge[0], prev_edge[1], edge[0], edge[1]
        )
        if intersection is None:
            px = (prev_edge[1][0] + edge[0][0]) / 2
            py = (prev_edge[1][1] + edge[0][1]) / 2
            intersection = (px, py)
        inset.append(intersection)
    return inset


def _retreat_from_pzt(
    point: tuple[float, float],
    pzt: tuple[float, float, float],
    hub: tuple[float, float],
) -> tuple[float, float]:
    px, py = point
    cx, cy, radius = pzt
    keepout = radius + PZT_CAVITY_CLEARANCE
    distance = math.hypot(px - cx, py - cy)
    if distance >= keepout + PZT_DOCK_RETREAT_BAND:
        return point

    # Move the dock point back toward the mainland hub until it clears the
    # circular PZT cavity.  This shortens the dock instead of expanding it.
    hx, hy = hub
    dx, dy = hx - px, hy - py
    step_len = math.hypot(dx, dy) or 1.0
    ux, uy = dx / step_len, dy / step_len
    initial_retreat = PZT_DOCK_RETREAT_STEP if distance >= keepout else 0.0
    px += ux * initial_retreat
    py += uy * initial_retreat

    for i in range(1, 100):
        candidate = (px + ux * i * 0.10, py + uy * i * 0.10)
        if math.hypot(candidate[0] - cx, candidate[1] - cy) >= keepout:
            return candidate
    return point


def _embedded_substrate_points() -> list[tuple[float, float]]:
    hub = (MAINLAND_RECT[0], MAINLAND_RECT[1])
    pzt_keepouts = [
        (*slot_scad_to_kicad((cx, cy)), radius)
        for cx, cy, radius in PZT_CAVITIES_SCAD
    ]

    base_points = _edge_inset_polygon(
        [slot_scad_to_kicad(raw) for raw in _embedded_substrate_scad_points()],
        SUBSTRATE_EDGE_CLEARANCE,
    )

    points = []
    for point_a, point_b in zip(base_points, base_points[1:] + base_points[:1]):
        ax, ay = point_a
        bx, by = point_b
        steps = max(
            1, math.ceil(math.hypot(bx - ax, by - ay) / SUBSTRATE_EDGE_SAMPLE)
        )
        for step in range(steps):
            t = step / steps
            point = (ax + (bx - ax) * t, ay + (by - ay) * t)
            point = (point[0], min(point[1], SUBSTRATE_TAIL_MAX_Y))
            for pzt in pzt_keepouts:
                point = _retreat_from_pzt(point, pzt, hub)
            if (
                not points
                or math.hypot(
                    point[0] - points[-1][0], point[1] - points[-1][1]
                )
                > 0.05
            ):
                points.append(point)

    return _polygon_points(points)


PCB_SLOT_POINTS = _embedded_substrate_points()

# ===== 分区：模块开孔与螺丝让位 =====

MODULE_CUTOUT_CLEARANCE = 0.20
ESP32_CUTOUT = (
    0.0,
    2.5,
    25.5 + MODULE_CUTOUT_CLEARANCE * 2,
    18.0 + MODULE_CUTOUT_CLEARANCE * 2,
)
IMU_CUTOUT = (
    0.0,
    -24.5,
    18.5 + MODULE_CUTOUT_CLEARANCE * 2,
    13.0 + MODULE_CUTOUT_CLEARANCE * 2,
)

# 参考线用的全部螺丝孔（含板外螺丝）
M2_CLEARANCE_HOLES = [
    (*slot_scad_to_kicad((x, y)), SCREW_CLEARANCE_RADIUS)
    for x, y in SCREW_HOLES_SCAD
]

# 实际 PCB Edge.Cuts 上只保留穿过大陆区的那两个
PCB_CLEARANCE_HOLES = [
    (*slot_scad_to_kicad((0.0, -33.0)), SCREW_CLEARANCE_RADIUS),
]
