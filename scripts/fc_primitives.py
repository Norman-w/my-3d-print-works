#!/usr/bin/env python3
"""FreeCAD 几何原语与 ISO 4762 螺钉包络。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import math

from fc_config import ISO_M3, ISO_M4

# ===== 分区：常量/配置 =====
ISO_SPECS = {"M3": ISO_M3, "M4": ISO_M4}

# ===== 分区：模型/类型 =====
# 零件以 Part::Box / Cylinder / Feature 加入文档，颜色仅 GUI 有效。

# ===== 分区：私有成员 =====
def _vec(App, x: float, y: float, z: float):
    return App.Vector(x, y, z)

def _axis_rotation(App, axis: str):
    axis = (axis or "z").lower()
    if axis == "x":
        return App.Rotation(App.Vector(0, 1, 0), 90)
    if axis == "y":
        return App.Rotation(App.Vector(1, 0, 0), -90)
    return App.Rotation()

# ===== 分区：公开 API =====
def set_placement(obj, App, x, y, z, axis: str = "z"):
    obj.Placement = App.Placement(_vec(App, x, y, z), _axis_rotation(App, axis))
    return obj

def set_color(obj, rgb, alpha=0.0):
    # CLI / headless 没有 ViewObject，忽略显示属性即可。
    try:
        r, g, b = rgb
        obj.ViewObject.ShapeColor = (r / 255.0, g / 255.0, b / 255.0)
        obj.ViewObject.Transparency = float(alpha) * 100.0
    except Exception:
        pass

def add_box(doc, App, name: str, x: float, y: float, z: float, dx: float, dy: float, dz: float, color, alpha=0.0):
    obj = doc.addObject("Part::Box", name)
    obj.Length = dx
    obj.Width = dy
    obj.Height = dz
    set_placement(obj, App, x, y, z)
    set_color(obj, color, alpha)
    return obj

def add_cylinder(doc, App, name: str, x: float, y: float, z: float, radius: float, height: float, color, alpha=0.0, axis: str = "z"):
    obj = doc.addObject("Part::Cylinder", name)
    obj.Radius = radius
    obj.Height = height
    obj.Angle = 360
    set_placement(obj, App, x, y, z, axis)
    set_color(obj, color, alpha)
    return obj

def add_feature(doc, shape, name: str, color, alpha=0.0):
    feature = doc.addObject("Part::Feature", name)
    feature.Shape = shape
    set_color(feature, color, alpha)
    return feature

def add_gear_disc(doc, Part, App, name: str, x: float, y: float, z: float, radius: float, thickness: float, teeth: int, color=(220, 190, 120)):
    origin = _vec(App, x, y, z)
    shape = Part.makeCylinder(radius * 0.88, thickness, origin)
    ring = Part.makeCylinder(radius, thickness * 0.7, origin)
    shape = shape.fuse(ring)
    tooth_count = max(8, int(teeth))
    for i in range(tooth_count):
        a = (360.0 / tooth_count) * i
        tooth = Part.makeBox(
            3.6,
            radius * 0.32,
            thickness * 0.38,
            _vec(App, x + radius * 0.65, y - radius * 0.16, z + thickness * 0.3),
        )
        tooth.rotate(origin, _vec(App, 0, 0, 1), a)
        shape = shape.fuse(tooth)
    return add_feature(doc, shape, name, color, 0.1)

def make_htd_pulley_shape(Part, App, teeth: int, pitch_mm: float, width: float, toothed: bool = True):
    from fc_htd import htd_pulley_shape
    return htd_pulley_shape(Part, App, teeth, pitch_mm, width)

def add_placed_shape(doc, App, name: str, shape, x: float, y: float, z: float, color, alpha=0.0, yaw_deg: float = 0.0):
    feature = add_feature(doc, shape, name, color, alpha)
    feature.Placement = App.Placement(_vec(App, x, y, z), App.Rotation(App.Vector(0, 0, 1), yaw_deg))
    return feature

def make_iso_shcs_shape(Part, App, size: str, length: float):
    spec = ISO_SPECS[size]
    shaft = Part.makeCylinder(spec["d"] * 0.5, length)
    head = Part.makeCylinder(spec["dk"] * 0.5, spec["k"], _vec(App, 0, 0, length))
    drive = Part.makeCylinder(spec["d"] * 0.42, spec["k"] * 0.45, _vec(App, 0, 0, length + spec["k"] * 0.55))
    return shaft.fuse(head).cut(drive)

def add_iso_shcs(doc, Part, App, name: str, x: float, y: float, z: float, size: str, length: float, axis: str = "z", color=(90, 96, 104)):
    shape = make_iso_shcs_shape(Part, App, size, length)
    feature = add_feature(doc, shape, name, color, 0.0)
    feature.Placement = App.Placement(_vec(App, x, y, z), _axis_rotation(App, axis))
    return feature

# ===== 分区：业务逻辑 =====
def _resample(samples: list[dict], limit: int) -> list[dict]:
    if len(samples) <= limit:
        return list(samples)
    step = max(1, int(round((len(samples) - 1) / (limit - 1))))
    picked = [samples[index] for index in range(0, len(samples), step)]
    if picked[-1] is not samples[-1]:
        picked.append(samples[-1])
    return picked

def _resample_by_spacing(samples: list[dict], max_step: float = 6.0) -> list[dict]:
    if len(samples) < 2:
        return list(samples)
    picked = [samples[0]]
    acc = 0.0
    for prev, cur in zip(samples, samples[1:]):
        acc += math.hypot(cur["x"] - prev["x"], cur["y"] - prev["y"])
        if acc >= max_step:
            picked.append(cur)
            acc = 0.0
    if picked[-1] is not samples[-1]:
        picked.append(samples[-1])
    return picked

def _polyline_wire(Part, App, samples: list[dict], closed: bool = False, max_step: float = 2.2):
    picked = _resample_by_spacing(samples, max_step)
    vectors = [_vec(App, p["x"], p["y"], p["z"]) for p in picked]
    cleaned = [vectors[0]]
    for vec in vectors[1:]:
        if cleaned[-1].distanceToPoint(vec) >= 0.35:
            cleaned.append(vec)
    if len(cleaned) < 2:
        return None, picked
    if closed:
        if cleaned[0].distanceToPoint(cleaned[-1]) > 0.35:
            cleaned.append(cleaned[0])
        else:
            cleaned[-1] = cleaned[0]
    return Part.Wire(Part.makePolygon(cleaned).Edges), picked

def make_pipe_along(Part, App, samples: list[dict], radius: float, closed: bool = False):
    if len(samples) < 2:
        return Part.makeSphere(radius)
    wire, picked = _polyline_wire(Part, App, samples, closed)
    if wire is None:
        return Part.makeSphere(radius)
    start = picked[0]
    origin = _vec(App, start["x"], start["y"], start["z"])
    tangent = App.Vector(start.get("tx") or 1.0, start.get("ty") or 0.0, 0.0)
    if tangent.Length < 1e-6:
        tangent = App.Vector(1, 0, 0)
    try:
        circle = Part.makeCircle(radius, origin, tangent)
        return wire.makePipe(Part.Wire([circle]))
    except Exception:
        try:
            if hasattr(Part, "makeTube"):
                return Part.makeTube(wire, radius)
        except Exception:
            pass
        return Part.makeCylinder(radius, 12.0, origin, tangent)

def _outward_xy(start: dict, samples: list[dict]) -> tuple[float, float]:
    tx, ty = start.get("tx") or 1.0, start.get("ty") or 0.0
    mag_t = math.hypot(tx, ty) or 1.0
    tx, ty = tx / mag_t, ty / mag_t
    cx = sum(p["x"] for p in samples) / max(1, len(samples))
    cy = sum(p["y"] for p in samples) / max(1, len(samples))
    ox, oy = start["x"] - cx, start["y"] - cy
    along = ox * tx + oy * ty
    ox -= along * tx
    oy -= along * ty
    mag = math.hypot(ox, oy)
    if mag < 1e-6:
        ox, oy = ty, -tx
        mag = math.hypot(ox, oy) or 1.0
    return ox / mag, oy / mag

def make_rect_belt(Part, App, samples: list[dict], width: float, thickness: float):
    wire, picked = _polyline_wire(Part, App, samples, closed=True, max_step=1.6)
    if wire is None:
        return make_pipe_along(Part, App, samples, max(width, thickness) * 0.28, closed=True)
    start = picked[0]
    tx, ty = start.get("tx") or 1.0, start.get("ty") or 0.0
    mag_t = math.hypot(tx, ty) or 1.0
    nx, ny = ty / mag_t, -tx / mag_t
    hx, hy = thickness * 0.5, width * 0.5
    origin = _vec(App, start["x"], start["y"], start["z"])
    corners = [
        origin + _vec(App, nx * hx, ny * hx, -hy),
        origin + _vec(App, -nx * hx, -ny * hx, -hy),
        origin + _vec(App, -nx * hx, -ny * hx, hy),
        origin + _vec(App, nx * hx, ny * hx, hy),
        origin + _vec(App, nx * hx, ny * hx, -hy),
    ]
    try:
        profile = Part.Wire(Part.makePolygon(corners).Edges)
        return wire.makePipe(profile)
    except Exception:
        return make_pipe_along(Part, App, samples, max(width, thickness) * 0.28, closed=True)

# ===== 分区：方法/工具 =====
def local_offset_placement(App, origin: dict, lx: float, ly: float, lz: float, extra_yaw: float = 0.0):
    yaw = math.degrees(math.atan2(origin["ty"], origin["tx"])) + extra_yaw
    base = App.Placement(_vec(App, origin["x"], origin["y"], origin["z"]), App.Rotation(App.Vector(0, 0, 1), yaw))
    local = App.Placement(_vec(App, lx, ly, lz), App.Rotation())
    return base.multiply(local)
