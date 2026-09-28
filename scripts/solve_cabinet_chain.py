#!/usr/bin/env python3
"""按真实节距 P 走销，用底端张紧轮闭合 03C 蛇形链。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import math
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# ===== 分区：常量/配置 =====
P = 4.7625
WALL = 3.2
SERVICE_W = 44.0
W = 250.0
GRID_W = W - 2 * WALL - SERVICE_W
N_COL = 5
N_ROW = 3
SERVICE_LAYERS = 1
DESIGN_BAY_H = 55.30
DIV_T = 2.4
SHELF_T = 2.4
SPROCKET_TEETH = 12
BLUNT_TEETH = 8  # 所有绿色导向轮统一使用的小轮
WALL_CLEAR = 0.40
# The two small return wheels are deliberately staggered in opposite X
# directions.  In the rear view this is the pair shown in the user's arrow
# sketch: the lower wheel moves toward world X+ and the upper wheel toward
# world X−.  They are not allowed to share an X coordinate because that was
# the source of the old twisted loop.
DRIVE_RETURN_X_TRIM = -4.00       # upper 8T guide, world X−
SERVICE_PRESS_RETURN_X_TRIM = 16.00  # lower 8T guide, world X+
MOTOR_RETURN_X_OFFSET_MM = -2.00
TEN_TRAVEL = 10.0
TENSIONER_HOME_RISE_MM = 6.0
PITCH_TOL = 0.02
CLOSE_TOL = 0.05
EXPECTED_PIN_COUNT = 260
POWER_SERVICE_MIN_CLEARANCE = 0.40
PATH_TANGENCY_MIN_DOT = 0.999
CHAIN_PATH_ENVELOPE_RADIUS_MM = 3.00
SERVICE_MOTOR_ENVELOPE_MIN_CLEARANCE = 0.40
RETURN_PATH_SELF_CLEARANCE_MIN_MM = (
    2.0 * CHAIN_PATH_ENVELOPE_RADIUS_MM + 0.40
)

# 方案 1 选择离合的网页/SCAD 共用装配参数（单位 mm）。输入轮与输出轮
# 同轴，狗牙面默认开 2.6 mm；输出狗牙向输入侧移动 2.5 mm 后只剩 0.1 mm
# 端面间隙，作为“已啮合”展示状态。
CHAIN_Y = 75.0
CHAIN_VERTICAL_SHIFT = 0.0
CHAIN_HEIGHT_CONTRACT: dict[str, object] = {}
# Segment 182 is on the horizontal service run at the clutch magnet datum,
# near the center column.  The former 143 was on the middle drawer row and
# could never trigger the center clutch at its lower installation height.
CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX = 182
CHAIN_REFERENCE_ROW = 0
CHAIN_LINK_TOP_OFFSET_MM = 2.15
CHAIN_TRIGGER_MAGNET_D_MM = 5.0
CHAIN_TRIGGER_MAGNET_L_MM = 4.00
CHAIN_TRIGGER_MAGNET_NORMAL_OFFSET_MM = 0.00
CHAIN_TRIGGER_MAGNET_TOP_CLEARANCE_MM = 0.0
CHAIN_TRIGGER_MAGNET_AXIAL_START_OFFSET_MM = 2.39
CHAIN_RETURN_GUIDE_CENTER_Y_MM = 41.20
SCHEME1_POWER_Y_OFFSET = -5.20
SCHEME1_OUTPUT_Y_OFFSET = 5.20
SCHEME1_DOG_INPUT_Y_OFFSET = -1.80
SCHEME1_DOG_OUTPUT_Y_OFFSET = 1.80
SCHEME1_DOG_ENGAGED_Y_OFFSET = -0.70
SCHEME1_OPEN_GAP = 2.60
SCHEME1_ENGAGE_STROKE = 2.50
# 与 12T 链轮在 1 Hz 时的理论链速一致；网页再按当前 Hz 比例缩放，
# 让拨叉在运输阶段沿真实销轴路径同步移动。
SCHEME1_SELECTOR_SPEED = SPROCKET_TEETH * P

BAY_W = (GRID_W - (N_COL - 1) * DIV_T) / N_COL
BAY_H = DESIGN_BAY_H
ROW_PITCH = BAY_H + SHELF_T
COL_PITCH = BAY_W + DIV_T
SERVICE_H = SERVICE_LAYERS * ROW_PITCH
GRID_ORIGIN_X = WALL + SERVICE_W
GRID_ORIGIN_Z = WALL + SERVICE_H

assert abs(GRID_W - 199.6) < 1e-6
assert abs(BAY_W - 38.0) < 1e-6
assert abs(COL_PITCH - 40.4) < 1e-6

# ===== 分区：模型/类型 =====
Vec = tuple[float, float]


@dataclass
class Line:
    a: Vec
    b: Vec

    @property
    def length(self) -> float:
        return dist(self.a, self.b)

    def point(self, s: float) -> Vec:
        l = self.length
        if l < 1e-12:
            return self.a
        t = s / l
        return lerp(self.a, self.b, t)

    def forward_intersect(self, pin: Vec, pitch: float, s0: float):
        l = self.length
        if l < 1e-12 or s0 >= l - 1e-9:
            return None
        here = self.point(max(0.0, s0))
        if dist(here, pin) < 1e-6:
            rem = l - s0
            if rem + 1e-9 < pitch:
                return None
            return (s0 + pitch, self.point(s0 + pitch))
        d = sub(self.b, self.a)
        f = sub(self.a, pin)
        qa = dot(d, d)
        qb = 2.0 * dot(f, d)
        qc = dot(f, f) - pitch * pitch
        disc = qb * qb - 4.0 * qa * qc
        if disc < 0.0:
            return None
        root = math.sqrt(disc)
        tmin = max(0.0, s0 / l)
        hits = []
        for t in ((-qb - root) / (2.0 * qa), (-qb + root) / (2.0 * qa)):
            if t + 1e-9 < tmin or t > 1.0 + 1e-9:
                continue
            t = min(1.0, max(tmin, t))
            pt = lerp(self.a, self.b, t)
            if dist(pt, pin) < pitch * 0.5:
                continue
            hits.append((t * l, pt))
        if not hits:
            return None
        hits.sort(key=lambda h: h[0])
        return hits[0]


@dataclass
class Arc:
    c: Vec
    r: float
    a0: float
    a1: float

    def __post_init__(self) -> None:
        self.sign = 1.0 if self.a1 >= self.a0 else -1.0
        self.span = abs(self.a1 - self.a0)
        self.length = self.r * self.span

    def point(self, s: float) -> Vec:
        th = self.a0 + self.sign * (s / self.r)
        return polar(self.c, self.r, th)

    def s_from_angle(self, th: float):
        delta = self.sign * (th - self.a0)
        delta = delta % (2.0 * math.pi)
        if delta > self.span + 1e-5:
            if delta > 2.0 * math.pi - 1e-5:
                delta = 0.0
            else:
                return None
        return delta * self.r

    def forward_intersect(self, pin: Vec, pitch: float, s0: float):
        if s0 >= self.length - 1e-9:
            return None
        here = self.point(max(0.0, s0))
        if dist(here, pin) < 1e-6 and self.r > pitch * 0.5:
            step = 2.0 * math.asin(min(1.0, pitch / (2.0 * self.r)))
            need = step * self.r
            if self.length - s0 + 1e-9 < need:
                return None
            return (s0 + need, self.point(s0 + need))
        hits = []
        for pt in circle_circle(self.c, self.r, pin, pitch):
            th = math.atan2(pt[1] - self.c[1], pt[0] - self.c[0])
            s = self.s_from_angle(th)
            if s is None or s + 1e-9 < s0:
                continue
            if dist(pt, pin) < pitch * 0.5:
                continue
            hits.append((s, pt))
        if not hits:
            return None
        hits.sort(key=lambda h: h[0])
        return hits[0]


# ===== 分区：私有成员 =====
def add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1])


def sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1])


def dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1]


def dist(a: Vec, b: Vec) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def lerp(a: Vec, b: Vec, t: float) -> Vec:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def polar(c: Vec, r: float, a: float) -> Vec:
    return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))


def circle_circle(c1: Vec, r1: float, c2: Vec, r2: float) -> list[Vec]:
    dx, dy = c2[0] - c1[0], c2[1] - c1[1]
    d = math.hypot(dx, dy)
    if d < 1e-12 or d > r1 + r2 + 1e-8 or d < abs(r1 - r2) - 1e-8:
        return []
    aa = (r1 * r1 - r2 * r2 + d * d) / (2.0 * d)
    h2 = r1 * r1 - aa * aa
    if h2 < -1e-8:
        return []
    h = math.sqrt(max(0.0, h2))
    mx = c1[0] + aa * dx / d
    my = c1[1] + aa * dy / d
    if h < 1e-9:
        return [(mx, my)]
    rx, ry = -dy * h / d, dx * h / d
    return [(mx + rx, my + ry), (mx - rx, my - ry)]


def col_center_x(i: int) -> float:
    return GRID_ORIGIN_X + i * COL_PITCH + BAY_W / 2.0


def row_center_z(j: int) -> float:
    return GRID_ORIGIN_Z + j * ROW_PITCH + BAY_H / 2.0


def chain_row_center_z(j: int) -> float:
    """Vertical center of a drawer-serving horizontal chain run."""
    return row_center_z(j) + CHAIN_VERTICAL_SHIFT


def drive_pitch_r() -> float:
    return P / (2.0 * math.sin(math.pi / SPROCKET_TEETH))


def translator_r() -> float:
    return P / (2.0 * math.sin(math.pi / BLUNT_TEETH))


def drive_outer_r() -> float:
    return drive_pitch_r() + 0.38 * P


def guide_outer_r() -> float:
    return translator_r() + 0.12 * P


def wall_inset() -> float:
    return WALL + drive_outer_r() + WALL_CLEAR


def guide_anchor_dx() -> float:
    """Keep the former 8T side anchors while all fixed guides use 8T."""
    return drive_pitch_r() - translator_r()


def blunt_dx() -> float:
    return (W - wall_inset()) - col_center_x(N_COL - 1)


def right_sprocket_c(z_hi: float) -> Vec:
    return (W - wall_inset() + guide_anchor_dx(), z_hi - translator_r())


def right_blunt_c(z_lo: float) -> Vec:
    return (W - wall_inset() + guide_anchor_dx(), z_lo + translator_r())


def left_sprocket_c(z_hi: float) -> Vec:
    return (col_center_x(0) - blunt_dx() - guide_anchor_dx(), z_hi - translator_r())


def left_blunt_c(z_lo: float) -> Vec:
    return (col_center_x(0) - blunt_dx() - guide_anchor_dx(), z_lo + translator_r())


def service_chain_z() -> float:
    return row_center_z(0) - ROW_PITCH + CHAIN_VERTICAL_SHIFT


def drive_c() -> Vec:
    return (
        wall_inset() + 2.0 * drive_pitch_r() + translator_r() + DRIVE_RETURN_X_TRIM,
        CHAIN_RETURN_GUIDE_CENTER_Y_MM,
    )


def service_press_c() -> Vec:
    """Lower 8T press/return guide that creates the horizontal service run."""
    return (
        wall_inset() + 2.0 * drive_pitch_r() + translator_r()
        + SERVICE_PRESS_RETURN_X_TRIM,
        service_chain_z() + translator_r(),
    )


def power_service_envelope_clearance(tz: float) -> float:
    """Return the 2-D radial clearance between the motor drive and press guide."""
    return dist(ten_c(tz), service_press_c()) - drive_outer_r() - guide_outer_r()


def entry_c() -> Vec:
    return (wall_inset() + translator_r(), chain_row_center_z(N_ROW - 1) - translator_r())


def power_c() -> Vec:
    """Former high-X top turn, now a normal rear-view-left guide wheel."""
    return right_sprocket_c(chain_row_center_z(N_ROW - 1))


def ten_home_z() -> float:
    return ten_z_min() + TENSIONER_HOME_RISE_MM


def ten_c(tz: float) -> Vec:
    return (wall_inset() + drive_pitch_r() + MOTOR_RETURN_X_OFFSET_MM, tz)


def north(c: Vec) -> Vec:
    return polar(c, translator_r(), math.pi / 2.0)


def ang(deg: float) -> float:
    return math.radians(deg)


def common_tangent(
    c1: Vec,
    r1: float,
    c2: Vec,
    r2: float,
    side: int,
    branch: int,
) -> dict[str, object]:
    """Return one oriented common tangent between two pulley envelopes.

    ``side=1`` is an external tangent and ``side=-1`` is an internal
    tangent.  ``branch`` selects the two mirror solutions.  The returned
    signs are the only safe way to choose the arc direction: guessing CW/CCW
    from the screen view was what produced the old knot.
    """
    if side not in (-1, 1) or branch not in (-1, 1):
        raise ValueError("common tangent side/branch must be ±1")
    d = dist(c1, c2)
    if d < 1e-9:
        raise RuntimeError("两个回程轮中心重合，没有可用切线")
    gamma = math.atan2(c2[1] - c1[1], c2[0] - c1[0])
    cosine = (r1 - side * r2) / d
    if abs(cosine) > 1.0 + 1e-9:
        raise RuntimeError("回程轮包络没有可用公共切线")
    normal_angle = gamma + branch * math.acos(max(-1.0, min(1.0, cosine)))
    normal = (math.cos(normal_angle), math.sin(normal_angle))
    other_normal = (side * normal[0], side * normal[1])
    p1 = add(c1, (r1 * normal[0], r1 * normal[1]))
    p2 = add(c2, (r2 * other_normal[0], r2 * other_normal[1]))
    tangent = unit(sub(p2, p1))

    def arc_sign(radial: Vec) -> int:
        return 1 if dot((-radial[1], radial[0]), tangent) >= 0.0 else -1

    return {
        "p1": p1,
        "p2": p2,
        "a1": math.atan2(normal[1], normal[0]),
        "a2": math.atan2(other_normal[1], other_normal[0]),
        "sign1": arc_sign(normal),
        "sign2": arc_sign(other_normal),
        "side": side,
        "branch": branch,
    }


def directed_arc(c: Vec, r: float, a0: float, a1: float, sign: int) -> Arc:
    """Create the shortest arc that follows the requested tangent direction."""
    delta = (sign * (a1 - a0)) % (2.0 * math.pi)
    return Arc(c, r, a0, a0 + sign * delta)


def right_s(z_hi: float, z_lo: float) -> list:
    c1 = right_sprocket_c(z_hi)
    c2 = right_blunt_c(z_lo)
    rg = translator_r()
    return [
        Arc(c1, rg, ang(90.0), ang(0.0)),
        Line(polar(c1, rg, 0.0), polar(c2, rg, 0.0)),
        Arc(c2, rg, ang(0.0), ang(-90.0)),
    ]


def left_s(z_hi: float, z_lo: float) -> list:
    c1 = left_sprocket_c(z_hi)
    c2 = left_blunt_c(z_lo)
    rg = translator_r()
    return [
        Arc(c1, rg, ang(90.0), ang(180.0)),
        Line(polar(c1, rg, math.pi), polar(c2, rg, math.pi)),
        Arc(c2, rg, ang(180.0), ang(270.0)),
    ]


def path_segments(tz: float) -> list:
    r12 = drive_pitch_r()
    rb = translator_r()
    z_svc = service_chain_z()
    top_row = N_ROW - 1
    segs: list = [Line(north(entry_c()), north(right_sprocket_c(chain_row_center_z(top_row))))]
    # The chain alternates right/left turns while descending through the
    # drawer rows.  Keeping this loop in lock-step with cabinet_chain_path.scad
    # prevents the old 5-row path from silently surviving the 3-row layout.
    side = "right"
    for upper_row in range(top_row, 0, -1):
        lower_row = upper_row - 1
        if side == "right":
            segs.extend(right_s(chain_row_center_z(upper_row), chain_row_center_z(lower_row)))
            segs.append(
                Line(
                    polar(right_blunt_c(chain_row_center_z(lower_row)), rb, ang(-90.0)),
                    north(left_sprocket_c(chain_row_center_z(lower_row))),
                )
            )
            side = "left"
        else:
            segs.extend(left_s(chain_row_center_z(upper_row), chain_row_center_z(lower_row)))
            segs.append(
                Line(
                    polar(left_blunt_c(chain_row_center_z(lower_row)), rb, ang(270.0)),
                    north(right_sprocket_c(chain_row_center_z(lower_row))),
                )
            )
            side = "right"
    # For an odd row count the bottom row exits on the right.  The chain must
    # first run horizontally through the service/magnet datum and only then
    # enter the corrected three-wheel return.  Traversed from the service
    # run, the non-crossing order is:
    #
    #     lower green -> upper green -> blue 12T drive -> entry return
    #
    # Reversing the same closed chain gives the user's arrow direction from
    # the drive side without making a second, mirrored chain.  The two
    # green wheels use opposite-X datums and the two internal tangents use
    # opposite branches; this is the part the old vertical dogleg got wrong.
    segs.extend(right_s(chain_row_center_z(0), z_svc))
    lower = service_press_c()
    upper = drive_c()
    ten = ten_c(tz)
    entry = entry_c()
    service_exit = polar(right_blunt_c(z_svc), rb, ang(-90.0))
    lower_to_upper = common_tangent(lower, rb, upper, rb, side=-1, branch=1)
    upper_to_motor = common_tangent(upper, rb, ten, r12, side=-1, branch=-1)
    motor_to_entry = common_tangent(ten, r12, entry, rb, side=1, branch=1)

    if lower_to_upper["sign1"] != -1:
        raise RuntimeError("下方绿轮没有从服务水平段连续离开")
    if lower_to_upper["sign2"] != upper_to_motor["sign1"]:
        raise RuntimeError("上下绿轮之间的内切线旋向不连续")
    if upper_to_motor["sign2"] != motor_to_entry["sign1"]:
        raise RuntimeError("上方绿轮到蓝色主动轮的内切线旋向不连续")
    if motor_to_entry["sign2"] != -1:
        raise RuntimeError("蓝色主动轮到左侧回程的切线旋向不连续")

    segs.append(Line(service_exit, polar(lower, rb, ang(-90.0))))
    segs.append(
        directed_arc(
            lower,
            rb,
            ang(-90.0),
            lower_to_upper["a1"],
            -1,
        )
    )
    segs.append(Line(lower_to_upper["p1"], lower_to_upper["p2"]))
    segs.append(
        directed_arc(
            upper,
            rb,
            lower_to_upper["a2"],
            upper_to_motor["a1"],
            int(lower_to_upper["sign2"]),
        )
    )
    segs.append(Line(upper_to_motor["p1"], upper_to_motor["p2"]))
    segs.append(
        directed_arc(
            ten,
            r12,
            upper_to_motor["a2"],
            motor_to_entry["a1"],
            int(upper_to_motor["sign2"]),
        )
    )
    segs.append(Line(motor_to_entry["p1"], motor_to_entry["p2"]))
    segs.append(
        directed_arc(
            entry,
            rb,
            motor_to_entry["a2"],
            ang(90.0),
            -1,
        )
    )
    return segs


def next_pin(pin: Vec, seg_i: int, s_cur: float, segs: list, pitch: float):
    n = len(segs)
    for step in range(n + 1):
        j = (seg_i + step) % n
        s0 = s_cur if step == 0 else 0.0
        hit = segs[j].forward_intersect(pin, pitch, s0)
        if hit is None:
            continue
        s_hit, pt = hit
        if step == 0 and s_hit <= s_cur + 1e-9:
            continue
        return pt, j, s_hit, step > 0 and j < seg_i
    raise RuntimeError("chain walk could not find the next pin")


def walk_pins(tz: float):
    segs = path_segments(tz)
    start = segs[0].point(0.0)
    pins = [start]
    pin = start
    seg_i = 0
    s_cur = 0.0
    for _ in range(800):
        pt, nj, ns, wrapped = next_pin(pin, seg_i, s_cur, segs, P)
        if wrapped and len(pins) > 16:
            return pins
        if len(pins) > 16 and dist(pt, start) < 0.12:
            return pins
        pins.append(pt)
        pin, seg_i, s_cur = pt, nj, ns
    raise RuntimeError("chain walk did not close")


def close_err(pins: list[Vec]) -> float:
    return dist(pins[-1], pins[0]) - P


def unit(v: Vec) -> Vec:
    length = math.hypot(v[0], v[1])
    if length < 1e-12:
        raise RuntimeError("链条路径出现零长度切线")
    return (v[0] / length, v[1] / length)


def segment_tangent(segment, at_end: bool) -> Vec:
    if isinstance(segment, Line):
        return unit(sub(segment.b, segment.a))
    theta = segment.a1 if at_end else segment.a0
    return unit((
        -math.sin(theta) * segment.sign,
        math.cos(theta) * segment.sign,
    ))


def point_segment_distance(point: Vec, a: Vec, b: Vec) -> float:
    ab = sub(b, a)
    denom = dot(ab, ab)
    if denom < 1e-12:
        return dist(point, a)
    t = max(0.0, min(1.0, dot(sub(point, a), ab) / denom))
    return dist(point, add(a, (ab[0] * t, ab[1] * t)))


def cross(a: Vec, b: Vec) -> float:
    return a[0] * b[1] - a[1] * b[0]


def segment_segment_distance(a: Vec, b: Vec, c: Vec, d: Vec) -> float:
    """Minimum distance between two finite 2-D segments."""
    ab = sub(b, a)
    cd = sub(d, c)
    ac = sub(c, a)
    ad = sub(d, a)
    ca = sub(a, c)
    cb = sub(b, c)
    denom = cross(ab, cd)
    if abs(denom) > 1e-12:
        t = cross(ac, cd) / denom
        u = cross(ac, ab) / denom
        if -1e-9 <= t <= 1.0 + 1e-9 and -1e-9 <= u <= 1.0 + 1e-9:
            return 0.0
    return min(
        point_segment_distance(a, c, d),
        point_segment_distance(b, c, d),
        point_segment_distance(c, a, b),
        point_segment_distance(d, a, b),
    )


def polyline_segments(segment, step: float = 0.75) -> list[tuple[Vec, Vec]]:
    """Approximate a line/arc with short chords for self-clearance checks."""
    count = max(1, int(math.ceil(segment.length / step)))
    points = [segment.point(segment.length * i / count) for i in range(count + 1)]
    return list(zip(points, points[1:]))


def path_self_clearance(segments: list) -> tuple[float, tuple[int, int]]:
    """Measure non-adjacent centerline clearance, including line crossings."""
    pieces: list[tuple[int, Vec, Vec]] = []
    for index, segment in enumerate(segments):
        pieces.extend(
            (index, start, end)
            for start, end in polyline_segments(segment)
        )
    minimum = float("inf")
    pair = (-1, -1)
    last = len(segments) - 1
    for first, (owner_a, a0, a1) in enumerate(pieces):
        for owner_b, b0, b1 in pieces[first + 1:]:
            if owner_a == owner_b:
                continue
            if owner_b == owner_a + 1 or (owner_a == 0 and owner_b == last):
                continue
            clearance = segment_segment_distance(a0, a1, b0, b1)
            if clearance < minimum:
                minimum = clearance
                pair = (owner_a, owner_b)
    return minimum, pair


def audit_path_geometry(tz: float) -> dict[str, float]:
    """Reject tangent reversal, knotting, and chain-envelope self-intersection."""
    segments = path_segments(tz)
    joints = [
        dot(
            segment_tangent(segments[index], True),
            segment_tangent(segments[(index + 1) % len(segments)], False),
        )
        for index in range(len(segments))
    ]
    tangent_min = min(joints)
    if tangent_min < PATH_TANGENCY_MIN_DOT:
        raise RuntimeError(
            "蛇链回程路径存在反向/折角切线: "
            f"minDot={tangent_min:.6f} < {PATH_TANGENCY_MIN_DOT:.3f}"
        )

    upper = drive_c()
    lower = service_press_c()
    center_clearance = dist(upper, lower) - 2.0 * guide_outer_r()
    if center_clearance < 0.40:
        raise RuntimeError(
            "上下绿色导向轮实体包络相交: "
            f"clear={center_clearance:.6f} mm < 0.40 mm"
        )
    self_clearance, pair = path_self_clearance(segments)
    if self_clearance < RETURN_PATH_SELF_CLEARANCE_MIN_MM:
        raise RuntimeError(
            "蛇链回程路径形成麻花/自交或包络干涉: "
            f"clear={self_clearance:.6f} mm "
            f"< {RETURN_PATH_SELF_CLEARANCE_MIN_MM:.2f} mm "
            f"segments={pair[0]}-{pair[1]}"
        )
    service_motor_envelope_clearance = power_service_envelope_clearance(tz)
    if service_motor_envelope_clearance < SERVICE_MOTOR_ENVELOPE_MIN_CLEARANCE:
        raise RuntimeError(
            "下方服务轮与蓝色主动轮实体包络发生干涉: "
            f"clear={service_motor_envelope_clearance:.6f} mm "
            f"< {SERVICE_MOTOR_ENVELOPE_MIN_CLEARANCE:.2f} mm"
        )
    return {
        "tangentMinDot": tangent_min,
        "upperMotorTangentAngleDeg": 0.0,
        "upperMotorLineClearanceMm": center_clearance,
        "serviceMotorCenterlineClearanceMm": self_clearance,
        "serviceMotorEnvelopeClearanceMm": service_motor_envelope_clearance,
        "returnPathSelfClearanceMm": self_clearance,
    }


def ten_z_min() -> float:
    return WALL + drive_outer_r()


def search_tensioner():
    home = ten_home_z()
    lo = max(home - TEN_TRAVEL, ten_z_min())
    best = None
    samples = 801
    for i in range(samples + 1):
        tz = lo + (home - lo) * i / samples
        pins = walk_pins(tz)
        n = len(pins)
        if n % 2:
            continue
        err = abs(close_err(pins))
        rec = (err, tz, pins)
        if best is None or rec[0] < best[0]:
            best = rec
    if best is None:
        raise RuntimeError("no even pin count inside the floor-safe tensioner travel")
    err, tz, pins = best
    span = (home - lo) / samples
    for _ in range(20):
        span *= 0.5
        for cand in (tz - span, tz + span):
            if cand < lo or cand > home:
                continue
            cpins = walk_pins(cand)
            if len(cpins) != len(pins) or len(cpins) % 2:
                continue
            cerr = abs(close_err(cpins))
            if cerr < err:
                err, tz, pins = cerr, cand, cpins
    return tz, pins


def apply_seat_phase(wheels: list[dict], pins: list[Vec]) -> None:
    for w in wheels:
        r = P / (2.0 * math.sin(math.pi / w["teeth"]))
        step = 360.0 / w["teeth"]
        offs = []
        for x, z in pins:
            if abs(dist((x, z), (w["x"], w["z"])) - r) > 0.08:
                continue
            ang = math.degrees(math.atan2(z - w["z"], x - w["x"])) % 360.0
            offs.append((ang - round(ang / step) * step + 180.0) % 360.0 - 180.0)
        w["rot"] = sum(offs) / len(offs) if offs else 0.0


def audit_wheel_seating(wheels: list[dict], pins: list[Vec]) -> dict[str, float]:
    """Check that every modeled wheel has real chain pins on its pitch circle."""
    max_error = 0.0
    contact_counts: list[int] = []
    for wheel in wheels:
        radius = P / (2.0 * math.sin(math.pi / wheel["teeth"]))
        errors = [
            abs(dist((x, z), (wheel["x"], wheel["z"])) - radius)
            for x, z in pins
        ]
        contacts = [error for error in errors if error <= 0.08]
        if len(contacts) < 2:
            raise RuntimeError(
                f"{wheel['id']} has fewer than two pins on its {wheel['teeth']}T pitch circle"
            )
        max_error = max(max_error, max(contacts))
        contact_counts.append(len(contacts))
        wheel["contactCount"] = len(contacts)
        wheel["maxContactErrorMm"] = max(contacts)
    return {
        "maxContactErrorMm": max_error,
        "minContactCount": min(contact_counts),
        "maxContactCount": max(contact_counts),
    }


def write_gen(path: Path, tz: float, pins: list[Vec], wheels: list[dict]) -> None:
    lines = [
        "// Generated by scripts/solve_cabinet_chain.py — 每节弦长 = P。",
        f"TEN_Z = {tz:.8f};",
        f"SNAKE_CHAIN_VERTICAL_SHIFT = {CHAIN_VERTICAL_SHIFT:.8f};",
        f"SNAKE_CHAIN_RETURN_GUIDE_CENTER_Y = {CHAIN_RETURN_GUIDE_CENTER_Y_MM:.8f};",
        f"SNAKE_PIN_N = {len(pins)};",
        "SNAKE_PINS = [",
    ]
    for x, y in pins:
        lines.append(f"    [{x:.8f}, {y:.8f}, 0],")
    lines.append("];")
    lines.append("WHEEL_POSES = [")
    for w in wheels:
        lines.append(f"    [{w['x']:.8f}, {w['z']:.8f}, {w['rot']:.8f}],")
    lines.append("];")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def motion_wheels(tz: float) -> list[dict]:
    wheels = [
        # The motor shaft follows the lower return/tensioner sprocket.  It is
        # the only pointed 12T sprocket; every other green position is the
        # smaller 8T blunt, bearing-supported guide.
        {"id": "power", "kind": "sprocket", "teeth": 12, "sign": -1, "x": ten_c(tz)[0], "z": ten_c(tz)[1]},
        {"id": "upper-guide", "kind": "idler", "teeth": BLUNT_TEETH, "sign": -1, "x": power_c()[0], "z": power_c()[1]},
        {"id": "entry", "kind": "idler", "teeth": BLUNT_TEETH, "sign": -1, "x": entry_c()[0], "z": entry_c()[1]},
        # The upper return wheel is face-flipped in the rear assembly.  Its
        # visible model therefore needs the opposite browser yaw sign from
        # the lower service-press wheel; using the same sign for both made the
        # chain appear to wind back over the upper wheel in the preview.
        {"id": "drive", "kind": "idler", "teeth": BLUNT_TEETH, "sign": 1, "x": drive_c()[0], "z": drive_c()[1]},
        {"id": "service-press", "kind": "idler", "teeth": BLUNT_TEETH, "sign": -1, "x": service_press_c()[0], "z": service_press_c()[1]},
    ]
    for row in range(N_ROW - 3, -1, -2):
        z = chain_row_center_z(row)
        c = right_sprocket_c(z)
        wheels.append({"id": f"r8-guide-{row}", "kind": "idler", "teeth": BLUNT_TEETH, "sign": -1, "x": c[0], "z": c[1]})
    for row in range(N_ROW - 2, 0, -2):
        z = chain_row_center_z(row)
        c = left_sprocket_c(z)
        wheels.append({"id": f"l8-guide-{row}", "kind": "idler", "teeth": BLUNT_TEETH, "sign": 1, "x": c[0], "z": c[1]})
    for k in range(N_ROW - 1):
        row = N_ROW - 2 - k
        z = chain_row_center_z(row)
        if k % 2 == 0:
            c = right_blunt_c(z)
            side = "r"
            sign = -1
        else:
            c = left_blunt_c(z)
            side = "l"
            sign = 1
        wheels.append({"id": f"{side}8-guide-{row}", "kind": "idler", "teeth": BLUNT_TEETH, "sign": sign, "x": c[0], "z": c[1]})
    c = right_blunt_c(service_chain_z())
    wheels.append({"id": "r8-guide-svc", "kind": "idler", "teeth": BLUNT_TEETH, "sign": -1, "x": c[0], "z": c[1]})
    return wheels


def scheme1_stations() -> list[dict]:
    """Return drawer stations in the same serpentine order as the selector path."""
    stations = []
    order = 0
    for path_row, row in enumerate(range(N_ROW - 1, -1, -1)):
        columns = range(N_COL) if path_row % 2 == 0 else range(N_COL - 1, -1, -1)
        for col in columns:
            stations.append({
                "id": f"drawer-r{row + 1}c{col + 1}",
                "order": order,
                "row": row,
                "col": col,
                "x": round(col_center_x(col), 6),
                "z": round(chain_row_center_z(row), 6),
                "powerY": round(CHAIN_Y + SCHEME1_POWER_Y_OFFSET, 6),
                "outputY": round(CHAIN_Y + SCHEME1_OUTPUT_Y_OFFSET, 6),
                "dogInputY": round(CHAIN_Y + SCHEME1_DOG_INPUT_Y_OFFSET, 6),
                "dogOutputY": round(CHAIN_Y + SCHEME1_DOG_OUTPUT_Y_OFFSET, 6),
                "dogEngagedY": round(CHAIN_Y + SCHEME1_DOG_ENGAGED_Y_OFFSET, 6),
            })
            order += 1
    return stations


def load_center_clutch_contract(root: Path) -> dict | None:
    """Read the OpenSCAD-generated contract without duplicating its dimensions."""
    contract_path = root / "output/3d-print/cabinet-clutch/center_clutch_contract.json"
    if not contract_path.is_file():
        return None
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    contract = payload.get("centerClutch")
    if not isinstance(contract, dict):
        raise RuntimeError(f"中心离合契约格式无效: {contract_path}")
    return contract


def configure_chain_height(contract: dict | None) -> None:
    """Apply the OpenSCAD magnet-bottom datum before solving the chain."""
    global CHAIN_VERTICAL_SHIFT, CHAIN_HEIGHT_CONTRACT
    global DRIVE_RETURN_X_TRIM, SERVICE_PRESS_RETURN_X_TRIM
    global MOTOR_RETURN_X_OFFSET_MM
    global CHAIN_REFERENCE_ROW, CHAIN_LINK_TOP_OFFSET_MM
    global CHAIN_TRIGGER_MAGNET_D_MM, CHAIN_TRIGGER_MAGNET_L_MM
    global CHAIN_TRIGGER_MAGNET_NORMAL_OFFSET_MM
    global CHAIN_TRIGGER_MAGNET_TOP_CLEARANCE_MM
    global CHAIN_TRIGGER_MAGNET_AXIAL_START_OFFSET_MM
    global CHAIN_RETURN_GUIDE_CENTER_Y_MM
    if contract is None:
        raise RuntimeError(
            "缺少中心离合契约；请先运行 generate_center_clutch_contract.py，"
            "再求解蛇形链条。"
        )
    required = (
        "snakeChainHeightDatum",
        "inputSleeveMagnetOpenBottomYMm",
        "snakeChainLinkTopOffsetMm",
        "snakeChainReferenceRow",
        "snakeChainReferencePathCenterYMm",
        "snakeChainVerticalShiftMm",
        "snakeChainServicePathCenterYMm",
        "snakeChainReturnGuideCenterYMm",
        "snakeChainReturnDriveXTrimMm",
        "snakeChainServicePressXTrimMm",
        "snakeChainMotorXOffsetMm",
        "snakeChainTriggerMagnetSegmentIndex",
        "snakeChainTriggerMagnetDiameterMm",
        "snakeChainTriggerMagnetLengthMm",
        "snakeChainTriggerMagnetNormalOffsetMm",
        "snakeChainTriggerMagnetTopClearanceMm",
        "snakeChainTriggerMagnetAxialStartOffsetMm",
        "snakeChainTriggerMagnetAxis",
        "snakeChainTriggerCarrierPinSpacingMm",
        "snakeChainTriggerCarrierPinDiameterMm",
        "snakeChainTriggerCarrierPinHoleDiameterMm",
        "snakeChainTriggerCarrierPinLengthMm",
        "snakeChainTriggerCarrierPlateThicknessMm",
        "snakeChainTriggerCarrierMagnetPocketDiameterMm",
        "snakeChainTriggerCarrierMagnetLengthMm",
        "snakeChainTriggerCarrierMagnetPocketDepthMm",
        "snakeChainTriggerCarrierMagnetRetentionLipMm",
        "snakeChainTriggerCarrierMagnetBackWallMm",
        "snakeChainTriggerCarrierMagnetCenterAlongLinkMm",
        "snakeChainTriggerCarrierMagnetCenterNormalMm",
        "snakeChainTriggerCarrierMagnetAxis",
        "snakeChainTriggerCarrierMagnetCenterReference",
        "snakeChainTriggerCarrierHardwareMode",
        "snakeChainTriggerCarrierRetainingClipThicknessMm",
        "snakeChainTriggerCarrierPart",
        "snakeChainTriggerCarrierMagnetPart",
        "snakeChainTriggerCarrierConnectingPinsPart",
        "snakeChainTriggerCarrierRetainingClipPart",
    )
    missing = [key for key in required if key not in contract]
    if missing:
        raise RuntimeError("中心离合契约缺少链条高度字段: " + ", ".join(missing))
    if contract["snakeChainHeightDatum"] != "input-sleeve-magnet-bottom":
        raise RuntimeError("蛇链高度基准必须是公轮底部 M5 磁铁下沿")

    CHAIN_HEIGHT_CONTRACT = contract
    DRIVE_RETURN_X_TRIM = float(contract["snakeChainReturnDriveXTrimMm"])
    SERVICE_PRESS_RETURN_X_TRIM = float(
        contract["snakeChainServicePressXTrimMm"]
    )
    MOTOR_RETURN_X_OFFSET_MM = float(contract["snakeChainMotorXOffsetMm"])
    CHAIN_REFERENCE_ROW = int(float(contract["snakeChainReferenceRow"]))
    CHAIN_LINK_TOP_OFFSET_MM = float(contract["snakeChainLinkTopOffsetMm"])
    CHAIN_TRIGGER_MAGNET_D_MM = float(contract["snakeChainTriggerMagnetDiameterMm"])
    CHAIN_TRIGGER_MAGNET_L_MM = float(contract["snakeChainTriggerMagnetLengthMm"])
    CHAIN_TRIGGER_MAGNET_NORMAL_OFFSET_MM = float(
        contract["snakeChainTriggerMagnetNormalOffsetMm"]
    )
    CHAIN_TRIGGER_MAGNET_TOP_CLEARANCE_MM = float(
        contract["snakeChainTriggerMagnetTopClearanceMm"]
    )
    CHAIN_TRIGGER_MAGNET_AXIAL_START_OFFSET_MM = float(
        contract["snakeChainTriggerMagnetAxialStartOffsetMm"]
    )

    reference_path = float(contract["snakeChainReferencePathCenterYMm"])
    magnet_bottom = float(contract["inputSleeveMagnetOpenBottomYMm"])
    expected = magnet_bottom - CHAIN_LINK_TOP_OFFSET_MM - reference_path
    declared = float(contract["snakeChainVerticalShiftMm"])
    if abs(expected - declared) > 0.001:
        raise RuntimeError(
            "蛇链高度偏移推导不一致: "
            f"derived={expected:.6f} declared={declared:.6f}"
        )
    CHAIN_VERTICAL_SHIFT = declared
    if abs(row_center_z(CHAIN_REFERENCE_ROW) - reference_path) > 0.001:
        raise RuntimeError("蛇链参考行与柜体行中心不一致")
    if abs(service_chain_z() - float(contract["snakeChainServicePathCenterYMm"])) > 0.001:
        raise RuntimeError("蛇链服务行高度与中心离合契约不一致")
    CHAIN_RETURN_GUIDE_CENTER_Y_MM = float(
        contract["snakeChainReturnGuideCenterYMm"]
    )
    if CHAIN_RETURN_GUIDE_CENTER_Y_MM < WALL + guide_outer_r() + 0.25:
        raise RuntimeError("蛇链回程导向轮下沿侵入箱底")
    if CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX != int(
        float(contract["snakeChainTriggerMagnetSegmentIndex"])
    ):
        raise RuntimeError("蛇链触发磁铁节号与 OpenSCAD 契约不一致")
    if abs(CHAIN_TRIGGER_MAGNET_D_MM - 5.0) > 0.001 \
            or abs(CHAIN_TRIGGER_MAGNET_L_MM - 4.00) > 0.001 \
            or abs(CHAIN_TRIGGER_MAGNET_NORMAL_OFFSET_MM - 0.00) > 0.001 \
            or abs(CHAIN_TRIGGER_MAGNET_AXIAL_START_OFFSET_MM - 2.39) > 0.001:
        raise RuntimeError("蛇链触发磁铁必须为 M5×4，且按双销载架基准定位")
    carrier_checks = (
        ("snakeChainTriggerCarrierPinSpacingMm", 4.7625),
        ("snakeChainTriggerCarrierPinDiameterMm", 1.62),
        ("snakeChainTriggerCarrierPinHoleDiameterMm", 1.80),
        ("snakeChainTriggerCarrierPinLengthMm", 11.50),
        ("snakeChainTriggerCarrierPlateThicknessMm", 4.00),
        ("snakeChainTriggerCarrierMagnetPocketDiameterMm", 5.25),
        ("snakeChainTriggerCarrierMagnetLengthMm", 4.00),
        ("snakeChainTriggerCarrierMagnetPocketDepthMm", 4.00),
        ("snakeChainTriggerCarrierMagnetRetentionLipMm", 0.00),
        ("snakeChainTriggerCarrierMagnetBackWallMm", 0.00),
        ("snakeChainTriggerCarrierMagnetCenterNormalMm", 0.00),
    )
    for key, expected_value in carrier_checks:
        actual = float(contract[key])
        if abs(actual - expected_value) > 0.001:
            raise RuntimeError(
                f"双销 M5 载架契约字段错误: {key}={actual:.6f}, "
                f"expected={expected_value:.6f}"
            )
    if float(contract["snakeChainTriggerCarrierMagnetCenterAlongLinkMm"]) <= 0:
        raise RuntimeError("蛇链触发磁铁必须位于第二销外侧的圆角拖尾内")
    if contract["snakeChainTriggerCarrierPart"] != (
        "cabinet-chain/cabinet_chain_clutch_trigger_carrier"
    ) or contract["snakeChainTriggerCarrierMagnetPart"] != (
        "cabinet-chain/cabinet_chain_clutch_trigger_magnet"
    ):
        raise RuntimeError("双销 M5 载架 STL ID 与中心离合契约不一致")
    if contract["snakeChainTriggerMagnetAxis"] != "stl-Z" \
            or contract["snakeChainTriggerCarrierMagnetAxis"] != "stl-Z":
        raise RuntimeError("蛇链触发磁铁导出 STL 必须沿 STL Z 轴")
    if contract["snakeChainTriggerCarrierMagnetCenterReference"] != (
        "rear-rounded-tail-hole-center"
    ):
        raise RuntimeError("蛇链触发磁铁 X 基准必须是后侧圆角拖尾的磁铁座中心")
    if contract["snakeChainTriggerCarrierHardwareMode"] != (
            "purchased-03C-extended-pin-pair-plus-two-U-clips"):
        raise RuntimeError("蛇链触发件必须使用现成加长双卡槽穿销与两片 U 形卡")
    if abs(float(contract["snakeChainTriggerCarrierRetainingClipThicknessMm"]) - 0.60) > 0.001:
        raise RuntimeError("蛇链触发 U 形卡厚度必须为 0.60 mm")


def write_motion(
    path: Path,
    tz: float,
    pins: list[Vec],
    wheels: list[dict],
    center_contract: dict | None = None,
    path_audit: dict[str, float] | None = None,
) -> None:
    path_audit = path_audit or {}
    payload = {
        "p": P,
        "driveTeeth": SPROCKET_TEETH,
        "guideTeeth": BLUNT_TEETH,
        "driveReturnXTrimMm": DRIVE_RETURN_X_TRIM,
        "servicePressReturnXTrimMm": SERVICE_PRESS_RETURN_X_TRIM,
        "motorReturnXOffsetMm": MOTOR_RETURN_X_OFFSET_MM,
        "powerServiceEnvelopeClearanceMm": round(
            power_service_envelope_clearance(tz), 6
        ),
        "guidePitchRadiusMm": round(translator_r(), 6),
        "guideOuterRadiusMm": round(guide_outer_r(), 6),
        "guideBendAngleDeg": round(360.0 / BLUNT_TEETH, 6),
        "chainY": CHAIN_Y,
        "chainVerticalShiftMm": round(CHAIN_VERTICAL_SHIFT, 6),
        "chainTopDatum": {
            "mode": CHAIN_HEIGHT_CONTRACT["snakeChainHeightDatum"],
            "inputSleeveMagnetOpenBottomYMm": round(
                float(CHAIN_HEIGHT_CONTRACT["inputSleeveMagnetOpenBottomYMm"]), 6
            ),
            "linkTopOffsetMm": round(CHAIN_LINK_TOP_OFFSET_MM, 6),
            "referenceRow": CHAIN_REFERENCE_ROW,
            "referencePathCenterYMm": round(
                float(CHAIN_HEIGHT_CONTRACT["snakeChainReferencePathCenterYMm"]), 6
            ),
            "referencePathShiftedCenterYMm": round(
                chain_row_center_z(CHAIN_REFERENCE_ROW), 6
            ),
            "servicePathCenterYMm": round(service_chain_z(), 6),
            "returnGuideCenterYMm": round(CHAIN_RETURN_GUIDE_CENTER_Y_MM, 6),
            "servicePathFloorClearanceMm": round(
                service_chain_z() - guide_outer_r() - WALL, 6
            ),
        },
        "chainTriggerMagnet": {
            "segmentIndex": CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX,
            "diameterMm": round(CHAIN_TRIGGER_MAGNET_D_MM, 6),
            "lengthMm": round(CHAIN_TRIGGER_MAGNET_L_MM, 6),
            "normalOffsetMm": round(CHAIN_TRIGGER_MAGNET_NORMAL_OFFSET_MM, 6),
            "topClearanceMm": round(CHAIN_TRIGGER_MAGNET_TOP_CLEARANCE_MM, 6),
            "axialStartOffsetMm": round(CHAIN_TRIGGER_MAGNET_AXIAL_START_OFFSET_MM, 6),
            "axis": center_contract["snakeChainTriggerMagnetAxis"],
        },
        "chainTriggerCarrier": {
            "segmentIndex": CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX,
            "pinSpacingMm": round(float(center_contract["snakeChainTriggerCarrierPinSpacingMm"]), 6),
            "pinDiameterMm": round(float(center_contract["snakeChainTriggerCarrierPinDiameterMm"]), 6),
            "pinHoleDiameterMm": round(float(center_contract["snakeChainTriggerCarrierPinHoleDiameterMm"]), 6),
            "pinLengthMm": round(float(center_contract["snakeChainTriggerCarrierPinLengthMm"]), 6),
            "plateThicknessMm": round(float(center_contract["snakeChainTriggerCarrierPlateThicknessMm"]), 6),
            "magnetDiameterMm": round(float(center_contract["snakeChainTriggerMagnetDiameterMm"]), 6),
            "magnetLengthMm": round(float(center_contract["snakeChainTriggerCarrierMagnetLengthMm"]), 6),
            "magnetPocketDiameterMm": round(float(center_contract["snakeChainTriggerCarrierMagnetPocketDiameterMm"]), 6),
            "magnetPocketDepthMm": round(float(center_contract["snakeChainTriggerCarrierMagnetPocketDepthMm"]), 6),
            "magnetRetentionLipMm": round(float(center_contract["snakeChainTriggerCarrierMagnetRetentionLipMm"]), 6),
            "magnetBackWallMm": round(float(center_contract["snakeChainTriggerCarrierMagnetBackWallMm"]), 6),
            "magnetCenterAlongLinkMm": round(float(center_contract["snakeChainTriggerCarrierMagnetCenterAlongLinkMm"]), 6),
            "magnetCenterNormalMm": round(float(center_contract["snakeChainTriggerCarrierMagnetCenterNormalMm"]), 6),
            "magnetAxis": center_contract["snakeChainTriggerCarrierMagnetAxis"],
            "magnetCenterReference": center_contract["snakeChainTriggerCarrierMagnetCenterReference"],
            "hardwareMode": center_contract["snakeChainTriggerCarrierHardwareMode"],
            "retainingClipThicknessMm": round(float(center_contract["snakeChainTriggerCarrierRetainingClipThicknessMm"]), 6),
            "partId": center_contract["snakeChainTriggerCarrierPart"],
            "magnetPartId": center_contract["snakeChainTriggerCarrierMagnetPart"],
            "connectingPinsPartId": center_contract["snakeChainTriggerCarrierConnectingPinsPart"],
            "retainingClipPartId": center_contract["snakeChainTriggerCarrierRetainingClipPart"],
            "mounting": "two-adjacent-03C-pins-side-hung",
        },
        # The trigger is one rigid installed component even though its
        # printable carrier, purchased pins, retaining clips, and M5 magnet
        # remain four separately inspectable STL/reference parts.  This
        # relation is consumed by the browser so a corner of the snake path
        # cannot make the four parts drift apart.
        "chainTriggerAssembly": {
            "schemaVersion": 1,
            "id": "chain-trigger-assembly",
            "name": "03C 蛇形链条触发组件",
            "componentMode": "rigid-mounted",
            "geometrySpace": "source-adapter",
            "pathMount": {
                "type": "chain-segment",
                "segmentIndex": CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX,
                "pinCenters": [
                    CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX,
                    (CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX + 1) % len(pins),
                ],
                "pinAxis": "stl-Y",
                "follow": "segment-midpoint",
                "phaseOffsetMm": 0.0,
            },
            "relativeFrame": {
                "origin": "mounted-chain-segment-midpoint",
                "longitudinalAxis": "stl-X/tangent",
                "normalAxis": "stl-Z/chain-side",
                "axialAxis": "stl-Y/pin-axis",
                "motion": "one-rigid-pivot",
            },
            "mountRelations": [
                {
                    "parent": "chain-segment",
                    "child": "carrier",
                    "interface": "two-adjacent-03C-pin-bores",
                    "description": "打印件磁台的两个孔套在相邻链节的两根加长穿销上，磁台不单独漂浮。",
                },
                {
                    "parent": "carrier",
                    "child": "connecting-pins",
                    "interface": "paired-pin-bores",
                    "description": "两根现成双卡槽长穿销穿过链条与磁台的两孔，销轴向为 STL Y。",
                },
                {
                    "parent": "connecting-pins",
                    "child": "retaining-clips",
                    "interface": "two-groove-capture",
                    "description": "两片现成 U 形卡扣入长穿销卡槽，负责轴向防脱。",
                },
                {
                    "parent": "carrier",
                    "child": "magnet",
                    "interface": "rear-rounded-tail-through-seat",
                    "description": "M5×4 圆柱磁铁装入后侧圆角拖尾贯通座，螺丝由用户固定，磁铁轴为 STL Z。",
                },
            ],
            "components": [
                {
                    "id": "carrier",
                    "partId": center_contract["snakeChainTriggerCarrierPart"],
                    "role": "printed-carrier",
                    "parent": "chain-segment",
                    "mountRelation": "two-adjacent-03C-pin-bores",
                },
                {
                    "id": "connecting-pins",
                    "partId": center_contract["snakeChainTriggerCarrierConnectingPinsPart"],
                    "role": "purchased-extended-pins",
                    "parent": "carrier+chain-segment",
                    "mountRelation": "paired-pin-bores",
                },
                {
                    "id": "retaining-clips",
                    "partId": center_contract["snakeChainTriggerCarrierRetainingClipPart"],
                    "role": "purchased-retaining-clips",
                    "parent": "connecting-pins",
                    "mountRelation": "two-groove-capture",
                },
                {
                    "id": "magnet",
                    "partId": center_contract["snakeChainTriggerCarrierMagnetPart"],
                    "role": "purchased-magnet",
                    "parent": "carrier",
                    "mountRelation": "rear-rounded-tail-through-seat",
                },
            ],
            "animation": {
                "mode": "rigid-follow-segment",
                "pivot": "segment-midpoint",
                "phaseSource": "chainOffsetMm",
                "allComponentsSharePose": True,
            },
        },
        "returnPathAudit": {
            key: round(value, 6) for key, value in path_audit.items()
        },
        "tenZ": tz,
        "pins": [[round(x, 6), round(z, 6)] for x, z in pins],
        "wheels": [
            {
                "id": w["id"],
                "kind": w["kind"],
                "teeth": w["teeth"],
                "sign": w["sign"],
                "rot": round(w["rot"], 6),
                "x": round(w["x"], 6),
                "z": round(w["z"], 6),
                "contactCount": w["contactCount"],
                "maxContactErrorMm": round(w["maxContactErrorMm"], 6),
            }
            for w in wheels
        ],
        "scheme1": {
            "scheme": "scheme1-clutch-selective-drive",
            "selectorSpeed": SCHEME1_SELECTOR_SPEED,
            "openGap": SCHEME1_OPEN_GAP,
            "engageStroke": SCHEME1_ENGAGE_STROKE,
            "stations": scheme1_stations(),
            "selectorStart": 0,
        },
    }
    if center_contract is not None:
        payload["centerClutch"] = center_contract
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ===== 分区：公开 API =====
def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / "cad/openscad/enclosure/cabinet_chain_pins.gen.scad"
    center_contract = load_center_clutch_contract(root)
    configure_chain_height(center_contract)
    tz, pins = search_tensioner()
    n = len(pins)
    chords = [dist(pins[i], pins[(i + 1) % n]) for i in range(n)]
    path_audit = audit_path_geometry(tz)
    wheels = motion_wheels(tz)
    envelope_clearance = power_service_envelope_clearance(tz)
    if envelope_clearance < POWER_SERVICE_MIN_CLEARANCE:
        raise SystemExit(
            "12T 电机主动轮与下压服务轮实体包络净空不足: "
            f"{envelope_clearance:.6f} mm < {POWER_SERVICE_MIN_CLEARANCE:.2f} mm"
        )
    apply_seat_phase(wheels, pins)
    seating = audit_wheel_seating(wheels, pins)
    write_gen(out, tz, pins, wheels)
    motion = root / "output/3d-print/cabinet-chain/cabinet_chain_motion.json"
    motion.parent.mkdir(parents=True, exist_ok=True)
    write_motion(motion, tz, pins, wheels, center_contract, path_audit)
    print(
        f"pins={n} even={n % 2 == 0} ten_z={tz:.4f} "
        f"home={ten_home_z():.4f} drop={ten_home_z() - tz:.4f} "
        f"chord_min={min(chords):.6f} chord_max={max(chords):.6f} "
        f"close={chords[-1]:.6f} P={P} "
        f"guide={BLUNT_TEETH}T R={translator_r():.6f} "
        f"bend={360.0 / BLUNT_TEETH:.2f}deg "
        f"power_service_clear={envelope_clearance:.6f} "
        f"tangent_dot={path_audit['tangentMinDot']:.6f} "
        f"return_wheel_clear={path_audit['upperMotorLineClearanceMm']:.6f} "
        f"return_self_clear={path_audit['returnPathSelfClearanceMm']:.6f} "
        f"service_motor_clear={path_audit['serviceMotorEnvelopeClearanceMm']:.6f} "
        f"seat_error={seating['maxContactErrorMm']:.6f} "
        f"seat_contacts={seating['minContactCount']}-{seating['maxContactCount']}"
    )
    if n % 2:
        raise SystemExit("pin count must be even")
    if n != EXPECTED_PIN_COUNT:
        raise SystemExit(
            f"250 mm / 44 mm / 错向修正回程方案应有 {EXPECTED_PIN_COUNT} 个销，实际为 {n}"
        )
    if min(chords) < P - PITCH_TOL or max(chords) > P + PITCH_TOL:
        raise SystemExit("pin spacing is not true pitch")
    if abs(chords[-1] - P) > CLOSE_TOL:
        raise SystemExit("loop does not close on a real pitch")
    if not (ten_z_min() - 1e-6 <= tz <= ten_home_z() + 1e-6):
        raise SystemExit("tensioner would put teeth through the floor")
    print(f"wrote {out}")
    print(f"wrote {motion}")
    return 0


# ===== 分区：业务逻辑 =====
# 销轴沿节圆/直线以弦长 P 前进；只移动张紧轮 Z 让最后一节也等于 P。

# ===== 分区：方法/工具 =====
if __name__ == "__main__":
    sys.exit(main())
