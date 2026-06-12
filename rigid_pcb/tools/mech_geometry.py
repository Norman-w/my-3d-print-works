"""Mechanical geometry shared by incremental KiCad update scripts.

Coordinates in this file are KiCad board coordinates in millimeters unless the
name explicitly says SCAD.  KiCad's Y axis is positive downward in the board
editor; the PZT centers from board_params.yaml are converted at their callsite.
"""

from __future__ import annotations


SCAD_TO_KICAD_Y_OFFSET = -10.0


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

PCB_SLOT_POINTS = [slot_scad_to_kicad(p) for p in _embedded_substrate_scad_points()]


MAINLAND_RECT = (0.0, -5.0, 42.0, 42.0)

# Module body cutouts.  The actual modules mount with their long side along X.
# The opening dimensions are the module outside dimensions plus 0.20 mm
# clearance on each side.
MODULE_CUTOUT_CLEARANCE = 0.20
ESP32_CUTOUT = (
    0.0,
    5.0,
    25.5 + MODULE_CUTOUT_CLEARANCE * 2,
    18.0 + MODULE_CUTOUT_CLEARANCE * 2,
)
IMU_CUTOUT = (
    0.0,
    -16.5,
    18.5 + MODULE_CUTOUT_CLEARANCE * 2,
    13.0 + MODULE_CUTOUT_CLEARANCE * 2,
)
M2_CLEARANCE_HOLES = [(0.0, -21.0, 1.35), (0.0, 21.0, 1.35), (0.0, -42.0, 1.35)]
