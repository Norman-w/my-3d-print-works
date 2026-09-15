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
SERVICE_W = 20.0
W = 240.0 + SERVICE_W
GRID_W = 233.6
REF_GRID_H = 193.6
N_COL = 5
N_ROW = 5
REF_ROWS = 6
DIV_T = 2.4
SHELF_T = 2.4
SPROCKET_TEETH = 12
BLUNT_TEETH = 8
WALL_CLEAR = 0.40
TEN_TRAVEL = 10.0
PITCH_TOL = 0.02
CLOSE_TOL = 0.05

# 方案 1 选择离合的网页/SCAD 共用装配参数（单位 mm）。输入轮与输出轮
# 同轴，狗牙面默认开 2.6 mm；输出狗牙向输入侧移动 2.5 mm 后只剩 0.1 mm
# 端面间隙，作为“已啮合”展示状态。
CHAIN_Y = 75.0
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
BAY_H = (REF_GRID_H - (REF_ROWS - 1) * SHELF_T) / REF_ROWS
ROW_PITCH = BAY_H + SHELF_T
COL_PITCH = BAY_W + DIV_T
SERVICE_H = 2 * ROW_PITCH
GRID_ORIGIN_X = WALL + SERVICE_W
GRID_ORIGIN_Z = WALL + SERVICE_H

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


def drive_pitch_r() -> float:
    return P / (2.0 * math.sin(math.pi / SPROCKET_TEETH))


def translator_r() -> float:
    return P / (2.0 * math.sin(math.pi / BLUNT_TEETH))


def drive_outer_r() -> float:
    return drive_pitch_r() + 0.38 * P


def wall_inset() -> float:
    return WALL + drive_outer_r() + WALL_CLEAR


def pair_align_dx() -> float:
    return drive_pitch_r() - translator_r()


def blunt_dx() -> float:
    return (W - wall_inset()) - col_center_x(N_COL - 1)


def right_sprocket_c(z_hi: float) -> Vec:
    return (W - wall_inset(), z_hi - drive_pitch_r())


def right_blunt_c(z_lo: float) -> Vec:
    return (W - wall_inset() + pair_align_dx(), z_lo + translator_r())


def left_sprocket_c(z_hi: float) -> Vec:
    return (col_center_x(0) - blunt_dx(), z_hi - drive_pitch_r())


def left_blunt_c(z_lo: float) -> Vec:
    return (col_center_x(0) - blunt_dx() - pair_align_dx(), z_lo + translator_r())


def service_chain_z() -> float:
    return row_center_z(0) - ROW_PITCH


def drive_c() -> Vec:
    return (wall_inset() + 3.0 * drive_pitch_r(), service_chain_z() - drive_pitch_r())


def entry_c() -> Vec:
    return (wall_inset() + drive_pitch_r(), row_center_z(N_ROW - 1) - drive_pitch_r())


def power_c() -> Vec:
    """High-X top turn: rear-view-left D-shaft power wheel."""
    return right_sprocket_c(row_center_z(N_ROW - 1))


def ten_home_z() -> float:
    return WALL + drive_outer_r() + 1.2


def ten_c(tz: float) -> Vec:
    return (wall_inset() + drive_pitch_r(), tz)


def north(c: Vec) -> Vec:
    return polar(c, drive_pitch_r(), math.pi / 2.0)


def ang(deg: float) -> float:
    return math.radians(deg)


def right_s(z_hi: float, z_lo: float) -> list:
    c1 = right_sprocket_c(z_hi)
    c2 = right_blunt_c(z_lo)
    r12 = drive_pitch_r()
    rb = translator_r()
    return [
        Arc(c1, r12, ang(90.0), ang(0.0)),
        Line(polar(c1, r12, 0.0), polar(c2, rb, 0.0)),
        Arc(c2, rb, ang(0.0), ang(-90.0)),
    ]


def left_s(z_hi: float, z_lo: float) -> list:
    c1 = left_sprocket_c(z_hi)
    c2 = left_blunt_c(z_lo)
    r12 = drive_pitch_r()
    rb = translator_r()
    return [
        Arc(c1, r12, ang(90.0), ang(180.0)),
        Line(polar(c1, r12, math.pi), polar(c2, rb, math.pi)),
        Arc(c2, rb, ang(180.0), ang(270.0)),
    ]


def path_segments(tz: float) -> list:
    r12 = drive_pitch_r()
    rb = translator_r()
    z_svc = service_chain_z()
    segs: list = [Line(north(entry_c()), north(right_sprocket_c(row_center_z(4))))]
    segs.extend(right_s(row_center_z(4), row_center_z(3)))
    segs.append(Line(polar(right_blunt_c(row_center_z(3)), rb, ang(-90.0)), north(left_sprocket_c(row_center_z(3)))))
    segs.extend(left_s(row_center_z(3), row_center_z(2)))
    segs.append(Line(polar(left_blunt_c(row_center_z(2)), rb, ang(270.0)), north(right_sprocket_c(row_center_z(2)))))
    segs.extend(right_s(row_center_z(2), row_center_z(1)))
    segs.append(Line(polar(right_blunt_c(row_center_z(1)), rb, ang(-90.0)), north(left_sprocket_c(row_center_z(1)))))
    segs.extend(left_s(row_center_z(1), row_center_z(0)))
    segs.append(Line(polar(left_blunt_c(row_center_z(0)), rb, ang(270.0)), north(right_sprocket_c(row_center_z(0)))))
    segs.extend(right_s(row_center_z(0), z_svc))
    segs.append(Line(polar(right_blunt_c(z_svc), rb, ang(-90.0)), north(drive_c())))
    segs.append(Arc(drive_c(), r12, ang(90.0), ang(180.0)))
    ten = ten_c(tz)
    segs.append(Line(polar(drive_c(), r12, math.pi), polar(ten, r12, 0.0)))
    segs.append(Arc(ten, r12, ang(0.0), ang(-180.0)))
    segs.append(Line(polar(ten, r12, math.pi), polar(entry_c(), r12, math.pi)))
    segs.append(Arc(entry_c(), r12, ang(180.0), ang(90.0)))
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


def write_gen(path: Path, tz: float, pins: list[Vec], wheels: list[dict]) -> None:
    lines = [
        "// Generated by scripts/solve_cabinet_chain.py — 每节弦长 = P。",
        f"TEN_Z = {tz:.8f};",
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
        {"id": "power", "kind": "sprocket", "teeth": 12, "sign": -1, "x": power_c()[0], "z": power_c()[1]},
        {"id": "entry", "kind": "sprocket", "teeth": 12, "sign": -1, "x": entry_c()[0], "z": entry_c()[1]},
        {"id": "drive", "kind": "sprocket", "teeth": 12, "sign": 1, "x": drive_c()[0], "z": drive_c()[1]},
        {"id": "tensioner", "kind": "sprocket", "teeth": 12, "sign": -1, "x": ten_c(tz)[0], "z": ten_c(tz)[1]},
    ]
    for row, z in (("2", row_center_z(2)), ("0", row_center_z(0))):
        c = right_sprocket_c(z)
        wheels.append({"id": f"r12-{row}", "kind": "sprocket", "teeth": 12, "sign": -1, "x": c[0], "z": c[1]})
    for row, z in (("3", row_center_z(3)), ("1", row_center_z(1))):
        c = left_sprocket_c(z)
        wheels.append({"id": f"l12-{row}", "kind": "sprocket", "teeth": 12, "sign": 1, "x": c[0], "z": c[1]})
    for row, z in (("3", row_center_z(3)), ("1", row_center_z(1)), ("svc", service_chain_z())):
        c = right_blunt_c(z)
        wheels.append({"id": f"r8-{row}", "kind": "idler", "teeth": 8, "sign": -1, "x": c[0], "z": c[1]})
    for row, z in (("2", row_center_z(2)), ("0", row_center_z(0))):
        c = left_blunt_c(z)
        wheels.append({"id": f"l8-{row}", "kind": "idler", "teeth": 8, "sign": 1, "x": c[0], "z": c[1]})
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
                "z": round(row_center_z(row), 6),
                "powerY": round(CHAIN_Y + SCHEME1_POWER_Y_OFFSET, 6),
                "outputY": round(CHAIN_Y + SCHEME1_OUTPUT_Y_OFFSET, 6),
                "dogInputY": round(CHAIN_Y + SCHEME1_DOG_INPUT_Y_OFFSET, 6),
                "dogOutputY": round(CHAIN_Y + SCHEME1_DOG_OUTPUT_Y_OFFSET, 6),
                "dogEngagedY": round(CHAIN_Y + SCHEME1_DOG_ENGAGED_Y_OFFSET, 6),
            })
            order += 1
    return stations


def write_motion(path: Path, tz: float, pins: list[Vec], wheels: list[dict]) -> None:
    payload = {
        "p": P,
        "driveTeeth": SPROCKET_TEETH,
        "chainY": CHAIN_Y,
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
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ===== 分区：公开 API =====
def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / "cad/openscad/enclosure/cabinet_chain_pins.gen.scad"
    tz, pins = search_tensioner()
    n = len(pins)
    chords = [dist(pins[i], pins[(i + 1) % n]) for i in range(n)]
    wheels = motion_wheels(tz)
    apply_seat_phase(wheels, pins)
    write_gen(out, tz, pins, wheels)
    motion = root / "output/3d-print/cabinet-chain/cabinet_chain_motion.json"
    motion.parent.mkdir(parents=True, exist_ok=True)
    write_motion(motion, tz, pins, wheels)
    print(
        f"pins={n} even={n % 2 == 0} ten_z={tz:.4f} "
        f"home={ten_home_z():.4f} drop={ten_home_z() - tz:.4f} "
        f"chord_min={min(chords):.6f} chord_max={max(chords):.6f} "
        f"close={chords[-1]:.6f} P={P}"
    )
    if n % 2:
        raise SystemExit("pin count must be even")
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
