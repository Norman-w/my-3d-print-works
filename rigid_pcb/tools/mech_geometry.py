"""Mechanical geometry shared by incremental KiCad update scripts.

Coordinates in this file are KiCad board coordinates in millimeters unless the
name explicitly says SCAD.  KiCad's Y axis is positive downward in the board
editor; the PZT centers from board_params.yaml are converted at their callsite.
"""

from __future__ import annotations

import math


SCAD_TO_KICAD_Y_OFFSET = -10.0
SUBSTRATE_EDGE_CLEARANCE = 0.30
SUBSTRATE_TAIL_MAX_Y = 78.0
PZT_CAVITY_CLEARANCE = 0.32
PZT_DOCK_RETREAT_BAND = 4.0
PZT_DOCK_RETREAT_STEP = 3.0
SUBSTRATE_EDGE_SAMPLE = 1.0
MAINLAND_RECT = (0.0, -14.0, 42.0, 60.0)

PZT_CAVITIES_SCAD = [
    (38.0, 52.0, 20.5 / 2),
    (-38.0, 52.0, 20.5 / 2),
    (44.0, -52.0, 20.5 / 2),
    (-44.0, -52.0, 20.5 / 2),
]

SCREW_CLEARANCE_RADIUS = 3.5
SCREW_HOLES_SCAD = [
    (0.0, 65.0),
    (52.0, 45.0),
    (-52.0, 45.0),
    (55.0, 0.0),
    (-55.0, 0.0),
    (36.0, -65.0),
    (-36.0, -65.0),
    (0.0, 34.0),
    (0.0, -33.0),
]


def slot_scad_to_kicad(point: tuple[float, float]) -> tuple[float, float]:
    """Convert SCAD slot coordinates into the KiCad mechanical reference frame."""
    x, y = point
    return (x, -y + SCAD_TO_KICAD_Y_OFFSET)


SCAD_SLOT_POINTS = [
    (9.00, -108.00),
    (-9.00, -108.00),
    (-9.00, -26.00),
    (-16.75, -26.00),
    (-29.99, -40.11),
    (-28.24, -41.75),
    (-35.08, -49.05),
    (-41.65, -42.90),
    (-34.81, -35.60),
    (-33.06, -37.24),
    (-21.00, -24.39),
    (-21.00, 16.00),
    (-19.48, 16.00),
    (-29.66, 35.62),
    (-31.62, 34.32),
    (-37.17, 42.64),
    (-29.68, 47.63),
    (-24.13, 39.31),
    (-26.15, 37.97),
    (-14.75, 16.00),
    (14.75, 16.00),
    (26.15, 37.97),
    (24.13, 39.31),
    (29.68, 47.63),
    (37.17, 42.64),
    (31.62, 34.32),
    (29.66, 35.62),
    (19.48, 16.00),
    (21.00, 16.00),
    (21.00, -24.39),
    (33.06, -37.24),
    (34.81, -35.60),
    (41.65, -42.90),
    (35.08, -49.05),
    (28.24, -41.75),
    (29.99, -40.11),
    (16.75, -26.00),
    (9.00, -26.00),
]


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


def _edge_inset_polygon(points: list[tuple[float, float]], distance: float) -> list[tuple[float, float]]:
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
        offset_edges.append(((ax + nx * distance, ay + ny * distance), (bx + nx * distance, by + ny * distance)))

    inset = []
    count = len(offset_edges)
    for i in range(count):
        prev_edge = offset_edges[i - 1]
        edge = offset_edges[i]
        intersection = _line_intersection(prev_edge[0], prev_edge[1], edge[0], edge[1])
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
        steps = max(1, math.ceil(math.hypot(bx - ax, by - ay) / SUBSTRATE_EDGE_SAMPLE))
        for step in range(steps):
            t = step / steps
            point = (ax + (bx - ax) * t, ay + (by - ay) * t)
            point = (point[0], min(point[1], SUBSTRATE_TAIL_MAX_Y))
            for pzt in pzt_keepouts:
                point = _retreat_from_pzt(point, pzt, hub)
            if not points or math.hypot(point[0] - points[-1][0], point[1] - points[-1][1]) > 0.05:
                points.append(point)

    return _polygon_points(points)


PCB_SLOT_POINTS = _embedded_substrate_points()


# Module body cutouts.  The actual modules mount with their long side along X.
# The opening dimensions are the module outside dimensions plus 0.20 mm
# clearance on each side.
MODULE_CUTOUT_CLEARANCE = 0.20
ESP32_CUTOUT = (
    0.0,
    2.5,
    25.5 + MODULE_CUTOUT_CLEARANCE * 2,
    18.0 + MODULE_CUTOUT_CLEARANCE * 2,
)
IMU_CUTOUT = (
    0.0,
    -34.5,
    18.5 + MODULE_CUTOUT_CLEARANCE * 2,
    13.0 + MODULE_CUTOUT_CLEARANCE * 2,
)
M2_CLEARANCE_HOLES = [
    (*slot_scad_to_kicad((x, y)), SCREW_CLEARANCE_RADIUS)
    for x, y in SCREW_HOLES_SCAD
]

# Actual PCB cutouts.  Keep this narrower than the full mechanical reference
# list so board-external screw references do not become isolated Edge.Cuts.
# These two enclosure screws pass through the central substrate; use the same
# boss clearance as the SCAD keepout so the rigid PCB does not collide with
# the printed screw towers.
PCB_CLEARANCE_HOLES = [
    (*slot_scad_to_kicad((0.0, -33.0)), SCREW_CLEARANCE_RADIUS),
]
