"""Mechanical geometry shared by incremental KiCad update scripts.

Coordinates in this file are KiCad board coordinates in millimeters unless the
name explicitly says SCAD.  KiCad's Y axis is positive downward in the board
editor; the PZT centers from board_params.yaml are converted at their callsite.
"""

from __future__ import annotations


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


_PCB_SLOT_SCAD_POINTS = [
    (9.00, -88.00),
    (-9.00, -88.00),
    (-9.00, -26.00),
    (-17.44, -26.00),
    (-29.81, -39.19),
    (-27.70, -41.17),
    (-33.16, -47.01),
    (-39.73, -40.86),
    (-34.27, -35.02),
    (-32.15, -37.00),
    (-21.00, -25.12),
    (-21.00, 16.00),
    (-18.89, 16.00),
    (-28.80, 35.24),
    (-31.18, 33.65),
    (-35.61, 40.31),
    (-28.13, 45.30),
    (-23.69, 38.65),
    (-26.12, 37.02),
    (-15.29, 16.00),
    (15.29, 16.00),
    (26.12, 37.02),
    (23.69, 38.65),
    (28.13, 45.30),
    (35.61, 40.31),
    (31.18, 33.65),
    (28.80, 35.24),
    (18.89, 16.00),
    (21.00, 16.00),
    (21.00, -25.12),
    (32.15, -37.00),
    (34.27, -35.02),
    (39.73, -40.86),
    (33.16, -47.01),
    (27.70, -41.17),
    (29.81, -39.19),
    (17.44, -26.00),
    (9.00, -26.00),
]

# This keeps the known non-self-intersecting slot outline, but shifts it into
# the same KiCad frame as the 42 x 42 mainland reference: x [-21, 21],
# y [-26, 16].  The handle tail stops at y ~= 78 mm.
PCB_SLOT_POINTS = [(x, -y - 10.0) for x, y in _PCB_SLOT_SCAD_POINTS]


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
