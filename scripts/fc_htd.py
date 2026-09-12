#!/usr/bin/env python3
"""HTD3M 带轮/带齿：节圆啮合，不是方块齿轮。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import math

from fc_config import HTD_BELT_WIDTH_MM, HTD_PITCH_MM

# ===== 分区：常量/配置 =====
HTD_TOOTH_DEPTH_MM = 1.17
TOOTH_POOL = 36

# ===== 分区：模型/类型 =====
# 带轮轮廓在节圆内侧开槽；带齿从节线指向包角圆心。

# ===== 分区：私有成员 =====
def _polar(App, radius: float, angle: float, z: float = 0.0):
    return App.Vector(radius * math.cos(angle), radius * math.sin(angle), z)

# ===== 分区：公开 API =====
def pitch_radius_mm(teeth: int, pitch_mm: float = HTD_PITCH_MM) -> float:
    return teeth * pitch_mm / (2.0 * math.pi)

def htd_pulley_shape(Part, App, teeth: int, pitch_mm: float, width: float):
    teeth = max(10, int(teeth))
    pitch_r = pitch_radius_mm(teeth, pitch_mm)
    tip_r = max(2.2, pitch_r - 0.12)
    root_r = max(1.6, tip_r - HTD_TOOTH_DEPTH_MM)
    shoulder = tip_r - (tip_r - root_r) * 0.38
    pitch = 2.0 * math.pi / teeth
    points = []
    for index in range(teeth):
        center = index * pitch
        for radius, frac in (
            (root_r, -0.50),
            (root_r, -0.34),
            (shoulder, -0.24),
            (tip_r, -0.12),
            (tip_r, 0.12),
            (shoulder, 0.24),
            (root_r, 0.34),
            (root_r, 0.48),
        ):
            points.append(_polar(App, radius, center + frac * pitch))
    points.append(points[0])
    face = Part.Face(Part.makePolygon(points))
    rim = face.extrude(App.Vector(0, 0, width * 0.72))
    rim.translate(App.Vector(0, 0, width * 0.14))
    core = Part.makeCylinder(root_r * 0.62, width)
    flange_h = max(1.1, width * 0.12)
    flange_r = pitch_r + 0.9
    flange_a = Part.makeCylinder(flange_r, flange_h)
    flange_b = Part.makeCylinder(flange_r, flange_h, App.Vector(0, 0, width - flange_h))
    return core.fuse(rim).fuse(flange_a).fuse(flange_b)

def htd_belt_tooth_shape(Part, App, width: float = HTD_BELT_WIDTH_MM):
    depth = HTD_TOOTH_DEPTH_MM
    half = HTD_PITCH_MM * 0.26
    thick = max(6.0, width * 0.82)
    pts = [
        App.Vector(0.0, -half, 0.0),
        App.Vector(depth * 0.26, -half * 0.94, 0.0),
        App.Vector(depth * 0.68, -half * 0.70, 0.0),
        App.Vector(depth, -half * 0.48, 0.0),
        App.Vector(depth, half * 0.48, 0.0),
        App.Vector(depth * 0.68, half * 0.70, 0.0),
        App.Vector(depth * 0.26, half * 0.94, 0.0),
        App.Vector(0.0, half, 0.0),
        App.Vector(0.0, -half, 0.0),
    ]
    face = Part.Face(Part.makePolygon(pts))
    solid = face.extrude(App.Vector(0, 0, thick))
    solid.translate(App.Vector(0, 0, -thick * 0.5))
    return solid

def tooth_placement(App, sample: dict):
    inward_x = sample["ty"]
    inward_y = -sample["tx"]
    yaw = math.degrees(math.atan2(inward_y, inward_x))
    origin = App.Vector(sample["x"], sample["y"], sample["z"])
    return App.Placement(origin, App.Rotation(App.Vector(0, 0, 1), yaw))

# ===== 分区：业务逻辑 =====
def no_slip_deg(distance_mm: float, pitch_radius: float, sign: float = 1.0) -> float:
    if pitch_radius <= 1e-6:
        return 0.0
    return math.degrees(distance_mm / pitch_radius) * sign

# ===== 分区：方法/工具 =====
def integer_tooth_count(loop_length: float, pitch_mm: float = HTD_PITCH_MM) -> int:
    return max(20, int(round(loop_length / pitch_mm)))
