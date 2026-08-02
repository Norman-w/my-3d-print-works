#!/usr/bin/env python3
"""
Export web Bezier profiles → OpenSCAD geometry matching paddleFromBezier.ts:
  - Blade: closed XY polygon + linear_extrude (not Y-sliced circles)
  - Handle: butt ring lofted with front/side scaling per slice
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "web/src/data/userBezierProfiles.json"
DEFAULT_PARAMS = ROOT / "enclosure/parameters.scad"
OUT_DIR = ROOT / "enclosure/generated"
OUT_SCAD = OUT_DIR / "bezier_geometry.scad"
TAIL_INTERFERENCE = ROOT / "enclosure/stl/interference/tail_interference.json"
SCREW_SAFETY_REPORT = OUT_DIR / "m6_screw_safety.json"

DEFAULT_SIDE = {
    "target": "side",
    "start": {"x": 9.4, "y": 78.5},
    "segments": [
        {"cp1": {"x": 9.4, "y": 40}, "cp2": {"x": 9.4, "y": -20}, "end": {"x": 9.4, "y": -78.5}},
        {
            "cp1": {"x": 9.4, "y": -103.5},
            "cp2": {"x": 12.5, "y": -138.5},
            "end": {"x": 12.5, "y": -178.5},
        },
    ],
}

HANDLE_SLICES = int(
    os.environ.get("HANDLE_SLICES", "48" if os.environ.get("QUALITY_MODE") == "quick" else "256")
)
RING_SEGMENTS = 80
JOIN_GAP_MM = 0.0  # M6: handle must meet the blade neck without a structural gap
HANDLE_BUTT_SOLID_MM = 4.0  # minimal tail wall — just enough for USB-C opening & structural integrity
# 真实球拍尾端是齐平切面；贝塞尔封口收到中线时，从尖点起 loft 会出针尖。
HANDLE_BUTT_FLAT_BAND_MM = 3.0


def flat_butt_start_y(handle: dict[str, Any], tip_y: float, band_mm: float = HANDLE_BUTT_FLAT_BAND_MM) -> float:
    """在尾端 band 内取半宽接近最大值的 Y，作为平底起点（与 paddleFromBezier.ts 一致）。"""
    steps = 24
    max_hw = 0.0
    for i in range(steps + 1):
        y = tip_y + band_mm * i / steps
        max_hw = max(max_hw, half_width_at_y(handle, y))
    target = max_hw * 0.92
    for i in range(steps + 1):
        y = tip_y + band_mm * i / steps
        if half_width_at_y(handle, y) >= target:
            return y
    return tip_y + min(band_mm, 0.5)


def _smooth_series(values: list[float], passes: int = 2) -> list[float]:
    """Simple edge-preserving smoothing to reduce visible loft stepping."""
    if len(values) < 5 or passes <= 0:
        return values[:]
    out = values[:]
    for _ in range(passes):
        nxt = out[:]
        for i in range(2, len(out) - 2):
            nxt[i] = (
                out[i - 2] * 0.1
                + out[i - 1] * 0.2
                + out[i] * 0.4
                + out[i + 1] * 0.2
                + out[i + 2] * 0.1
            )
        out = nxt
    return out


def clip_open_polyline_at_min_y(
    pts: list[tuple[float, float]], y_min: float
) -> list[tuple[float, float]]:
    """Match paddleFromBezier.ts — keep y >= y_min for blade shell outline."""
    if len(pts) < 2:
        return pts
    out: list[tuple[float, float]] = []
    if pts[0][1] >= y_min:
        out.append(pts[0])
    for i in range(1, len(pts)):
        ax, ay = pts[i - 1]
        bx, by = pts[i]
        if ay >= y_min and by >= y_min:
            out.append((bx, by))
        elif ay >= y_min and by < y_min:
            t = (y_min - ay) / (by - ay)
            out.append((ax + t * (bx - ax), y_min))
        elif ay < y_min and by >= y_min:
            t = (y_min - ay) / (by - ay)
            out.append((ax + t * (bx - ax), y_min))
            out.append((bx, by))
    return out if len(out) >= 2 else pts


def _xy(p: dict[str, float]) -> tuple[float, float]:
    return p["x"], p["y"]


def _pt(p) -> tuple[float, float]:
    if isinstance(p, dict):
        return p["x"], p["y"]
    return float(p[0]), float(p[1])


def cubic_at(p0, p1, p2, p3, t: float) -> tuple[float, float]:
    a, b, c, d = _pt(p0), _pt(p1), _pt(p2), _pt(p3)
    u = 1.0 - t
    x = u**3 * a[0] + 3 * u**2 * t * b[0] + 3 * u * t**2 * c[0] + t**3 * d[0]
    y = u**3 * a[1] + 3 * u**2 * t * b[1] + 3 * u * t**2 * c[1] + t**3 * d[1]
    return x, y


def sample_profile(profile: dict[str, Any], steps_per_seg: int = 40) -> list[tuple[float, float]]:
    pts = [(profile["start"]["x"], profile["start"]["y"])]
    p0 = profile["start"]
    for seg in profile["segments"]:
        p1, p2, p3 = seg["cp1"], seg["cp2"], seg["end"]
        for j in range(1, steps_per_seg + 1):
            pts.append(cubic_at(p0, p1, p2, p3, j / steps_per_seg))
        p0 = p3
    return pts


def half_width_at_y(profile: dict[str, Any], y_mm: float) -> float:
    """Right-half width at y (mm); matches paddleFromBezier.ts halfWidthAtY."""
    pts = sample_profile(profile, 40)
    best_d = abs(pts[0][1] - y_mm)
    x = abs(pts[0][0])
    for px, py in pts:
        d = abs(py - y_mm)
        if d < best_d:
            best_d = d
            x = abs(px)
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        if (ay <= y_mm <= by) or (by <= y_mm <= ay):
            t = 0.5 if abs(by - ay) < 1e-6 else (y_mm - ay) / (by - ay)
            x = max(x, abs(ax + t * (bx - ax)))
    return max(x, 0.5)


def envelope_half_width_at_y(
    y_mm: float,
    blade: dict[str, Any],
    handle: dict[str, Any],
    join_y: float,
) -> float:
    """Silhouette half-width for screw / boss placement (blade + handle)."""
    hw = 0.0
    if y_mm >= join_y - 20:
        hw = max(hw, half_width_at_y(blade, y_mm))
    if y_mm <= join_y + 5:
        hw = max(hw, half_width_at_y(handle, y_mm))
    return max(hw, 0.5)


def close_symmetric_right(right: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = list(right)
    lx, ly = right[-1]
    if abs(lx) > 0.01:
        out.append((-lx, ly))
    for i in range(len(right) - 2, -1, -1):
        out.append((-right[i][0], right[i][1]))
    return out


def blade_closed_polygon(blade: dict[str, Any]) -> list[tuple[float, float]]:
    """Full blade-front outline including neck / 鬓角 (same as web wood extrude)."""
    pts = sample_profile(blade, 48)
    right = [(max(x, 0.0), y) for x, y in pts]
    return close_symmetric_right(right)


def resample_closed_ring(points: list[tuple[float, float]], count: int) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points
    dists = [0.0]
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        dists.append(dists[-1] + math.hypot(dx, dy))
    dx, dy = points[0][0] - points[-1][0], points[0][1] - points[-1][1]
    total = dists[-1] + math.hypot(dx, dy)
    out: list[tuple[float, float]] = []
    for i in range(count):
        target = (i / count) * total
        j = 0
        while j < len(dists) - 1 and dists[j + 1] < target:
            j += 1
        a = points[j]
        b = points[(j + 1) % len(points)]
        seg_start = dists[j]
        seg_end = dists[j + 1] if j < len(dists) - 1 else total
        t = (target - seg_start) / (seg_end - seg_start) if seg_end > seg_start else 0.0
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def butt_cross_section_ring(bottom: dict[str, Any], ring_segments: int) -> list[tuple[float, float]]:
    pts = sample_profile(bottom, 36)
    loop: list[tuple[float, float]] = [(max(p[0], 0.0), p[1]) for p in pts]
    lx, lz = loop[-1]
    if lx > 0.01:
        loop.append((-lx, lz))
    for i in range(len(pts) - 2, -1, -1):
        loop.append((-max(pts[i][0], 0.0), pts[i][1]))
    return resample_closed_ring(loop, ring_segments)


def handle_loft_slices(
    handle: dict[str, Any],
    bottom: dict[str, Any],
    side: dict[str, Any] | None,
    join_y: float,
    blade_half_t: float,
    slices: int,
) -> list[tuple[float, list[tuple[float, float]]]]:
    """List of (y_center, polygon in XZ as (x,z) pairs)."""
    ring = butt_cross_section_ring(bottom, RING_SEGMENTS)
    base_hw = max(max(p[0] for p in ring), 1.0)
    base_ht = max(max(abs(p[1]) for p in ring), 1.0)
    hpts = sample_profile(handle, 48)
    tip_y = min(p[1] for p in hpts)
    bottom_y = flat_butt_start_y(handle, tip_y)
    # M6 extends the final handle section to the declared join datum.  Sampling
    # above the final handle control point intentionally reuses its terminal
    # width, producing a short, solid overlap with the blade tang.
    top_y = join_y - JOIN_GAP_MM
    ys: list[float] = []
    hws: list[float] = []
    hts: list[float] = []
    for s in range(slices):
        t = s / max(slices - 1, 1)
        y = bottom_y + t * (top_y - bottom_y)
        ys.append(y)
        hw = half_width_at_y(handle, y)
        hws.append(hw)
        if side:
            # 与 paddleFromBezier.ts 一致：直接用侧视轮廓厚度，不做颈部混厚。
            ht = half_width_at_y(side, y)
        else:
            ht = base_ht * (hw / base_hw)
        hts.append(ht)

    # 轻量平滑台阶感；不做强平滑，避免肩部外形偏离 Three.js。
    hws = _smooth_series(hws, passes=1)
    hts = _smooth_series(hts, passes=1)

    out: list[tuple[float, list[tuple[float, float]]]] = []
    for y, hw, ht in zip(ys, hws, hts):
        sx = max(hw / base_hw, 0.05)
        sz = max(max(ht, 0.5) / base_ht, 0.05)
        poly = [(p[0] * sx, p[1] * sz) for p in ring]
        out.append((y, poly))
    return out


def parse_params(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    keys = [
        "blade_core_t",
        "handle_join_y",
        "handle_butt_y",
        "blade_tip_y",
        "wall_t",
        "handle_cavity_inset",
        "m6_handle_screw_station_count",
        "m6_handle_screw_top_clearance",
        "m6_handle_screw_bottom_clearance",
        "m6_handle_screw_tail_edge_clearance",
        "m6_handle_screw_tail_inset",
        "m6_pcb_slot_min_ligament",
        "m6_tail_slot_min_ligament",
        "m6_core_edge_min_ligament",
    ]
    out: dict[str, float] = {}
    for k in keys:
        m = re.search(rf"^{k}\s*=\s*([-\d.]+)\s*;", text, re.M)
        if not m:
            raise ValueError(f"missing {k}")
        out[k] = float(m.group(1))
    return out


def fmt_pt(x: float, y: float) -> str:
    return f"[{fmt_num(x)}, {fmt_num(y)}]"


def fmt_num(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".")


def fmt_poly(poly: list[tuple[float, float]]) -> str:
    return "[" + ", ".join(fmt_pt(x, y) for x, y in poly) + "]"


def m6_screw_positions_on_midcurve(
    handle: dict[str, Any],
    y0: float,
    join_y: float,
    cavity_margin: float,
    count: int,
    top_clearance: float,
    bottom_clearance: float,
    tail_edge_clearance: float,
    tail_inset: float,
    pcb_avoidance: dict[str, float] | None = None,
) -> list[tuple[float, float]]:
    """等弧长排布常规站，并在尾边增加一个由同一中线推导的加强站。"""
    bottom_y = y0 + bottom_clearance
    top_y = join_y - top_clearance
    if count < 1 or top_y <= bottom_y:
        return []
    samples: list[tuple[float, float]] = []
    for i in range(241):
        y = bottom_y + (top_y - bottom_y) * i / 240
        outer_x = half_width_at_y(handle, y)
        inner_x = max(outer_x - cavity_margin, 0.5)
        samples.append(((outer_x + inner_x) / 2, y))
    cumulative = [0.0]
    for a, b in zip(samples, samples[1:]):
        cumulative.append(cumulative[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = cumulative[-1]
    right: list[tuple[float, float]] = []
    for station in range(count):
        target = total * (station / (count - 1) if count > 1 else 0.5)
        j = next((i for i, value in enumerate(cumulative) if value >= target), len(samples) - 1)
        if j == 0:
            right.append(samples[0])
            continue
        span = cumulative[j] - cumulative[j - 1]
        t = 0.0 if span <= 1e-9 else (target - cumulative[j - 1]) / span
        ax, ay = samples[j - 1]
        bx, by = samples[j]
        right.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    tail_y = y0 + tail_edge_clearance
    tail_outer_x = half_width_at_y(handle, tail_y)
    tail_inner_x = max(tail_outer_x - cavity_margin, 0.5)
    tail_x = max((tail_outer_x + tail_inner_x) / 2 - tail_inset, 0.5)
    stations = [(tail_x, tail_y), *right]
    if pcb_avoidance:
        x_limit = pcb_avoidance["x_limit"]
        y_min = pcb_avoidance["y_min"]
        y_max = pcb_avoidance["y_max"]
        required = pcb_avoidance["required_center_clearance"]
        min_pitch = pcb_avoidance["min_station_pitch"]

        def clearance(point: tuple[float, float]) -> float:
            x, y = point
            dx = max(abs(x) - x_limit, 0.0)
            dy = y_min - y if y < y_min else y - y_max if y > y_max else 0.0
            return math.hypot(dx, dy)

        safe: list[tuple[float, float]] = []
        moves: list[dict[str, object]] = []
        for station_index, original in enumerate(stations):
            candidate = original
            required_here = (
                pcb_avoidance["tail_required_center_clearance"]
                if station_index == 0
                else required
            )
            # Follow the actual midcurve toward the paddle head (+Y), never a
            # fixed world-coordinate offset. Also retain boss-to-boss pitch.
            for step in range(4001):
                y = original[1] + step * 0.05
                if step == 0:
                    candidate = original
                else:
                    outer_x = half_width_at_y(handle, y)
                    inner_x = max(outer_x - cavity_margin, 0.5)
                    candidate = ((outer_x + inner_x) / 2, y)
                pitch_ok = not safe or y - safe[-1][1] >= min_pitch
                # The first station is the user-confirmed tail pair: preserve
                # its exact original location when it satisfies the dedicated
                # two-perimeter tail ligament. Only PCB-region stations move.
                if clearance(candidate) >= required_here and pitch_ok:
                    break
            else:
                raise ValueError(f"cannot place M6 screw safely toward head from {original}")
            safe.append(candidate)
            moves.append({
                "original": [original[0], original[1]],
                "final": [candidate[0], candidate[1]],
                "pcbSlotCenterClearanceMm": clearance(candidate),
                "requiredCenterClearanceMm": required_here,
                "classification": "preserved_tail_pair" if station_index == 0 else "pcb_region",
                "moved": math.dist(original, candidate) > 1e-6,
            })
        stations = safe
        pcb_avoidance["moves"] = moves
    return [point for x, y in stations for point in ((-x, y), (x, y))]


def inset_xz_poly(
    poly: list[tuple[float, float]], margin: float
) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for x, z in poly:
        ax, az = abs(x), abs(z)
        nx = math.copysign(max(ax - margin, 0.5), x) if ax > 1e-6 else 0.0
        nz = math.copysign(max(az - margin, 0.5), z) if az > 1e-6 else 0.0
        out.append((nx, nz))
    return out


def write_scad(
    blade_poly: list[tuple[float, float]],
    handle_slices: list[tuple[float, list[tuple[float, float]]]],
    blade_core_t: float,
    join_y: float,
    cavity_margin: float,
    json_path: Path,
) -> None:
    handle_right = [
        (max(abs(x) for x, _ in ring), y)
        for y, ring in handle_slices
    ]
    handle_planform = handle_right + [
        (-x, y) for x, y in reversed(handle_right)
    ]
    lines = [
        "// AUTO-GENERATED by scripts/bezier_to_openscad.py — do not edit",
        f"// Source: {json_path.relative_to(ROOT)}",
        "// Geometry matches web/src/lib/paddleFromBezier.ts (blade extrude + handle loft)",
        "",
        f"BEZIER_BLADE_CORE_T = {fmt_num(blade_core_t)};",
        f"BEZIER_JOIN_Y = {fmt_num(join_y)};",
        f"BEZIER_BLADE_POLY = {fmt_poly(blade_poly)};",
        f"BEZIER_HANDLE_PLANFORM = {fmt_poly(handle_planform)};",
        "",
        "module bezier_blade_solid() {",
        "    linear_extrude(height = BEZIER_BLADE_CORE_T, center = true)",
        "        polygon(points = BEZIER_BLADE_POLY);",
        "}",
        "",
        "module bezier_handle_planform_2d() {",
        "    polygon(points = BEZIER_HANDLE_PLANFORM);",
        "}",
        "",
        "module bezier_handle_solid() {",
        "    union() {",
    ]
    for i in range(len(handle_slices) - 1):
        y0, poly0 = handle_slices[i]
        y1, _ = handle_slices[i + 1]
        dh = y1 - y0
        ym = (y0 + y1) / 2
        lines.append(f"        // slice {i}")
        lines.append(f"        translate([0, {fmt_num(ym)}, 0])")
        lines.append('            rotate([90, 0, 0])')
        lines.append(f"                linear_extrude(height = {fmt_num(dh)} + 0.02, center = true)")
        lines.append(f"                    polygon(points = {fmt_poly(poly0)});")
    lines.extend(["    }", "}", "", "module bezier_handle_cavity() {", "    union() {"])
    butt_cap_end_y = handle_slices[0][0] + HANDLE_BUTT_SOLID_MM
    for i in range(len(handle_slices) - 1):
        y0, poly0 = handle_slices[i]
        y1, _ = handle_slices[i + 1]
        if y0 < butt_cap_end_y:
            continue
        if y0 > join_y - 2:
            continue
        dh = y1 - y0
        ym = (y0 + y1) / 2
        inner = inset_xz_poly(poly0, cavity_margin)
        lines.append(f"        translate([0, {fmt_num(ym)}, 0])")
        lines.append('            rotate([90, 0, 0])')
        lines.append(f"                linear_extrude(height = {fmt_num(dh)} + 0.02, center = true)")
        lines.append(f"                    polygon(points = {fmt_poly(inner)});")
    lines.extend(
        [
            "    }",
            "}",
            "",
            "module bezier_paddle_outer() {",
            "    union() {",
            "        bezier_blade_solid();",
            "        bezier_handle_solid();",
            "    }",
            "}",
            "",
        ]
    )
    OUT_SCAD.write_text("\n".join(lines), encoding="utf-8")


def design_silhouette_profile(
    json_path: Path,
    params_path: Path = DEFAULT_PARAMS,
    n: int = 200,
) -> dict[str, float | list[float]]:
    """沿 Y 的设计半宽轮廓（与 OpenSCAD bezier 外形同源，非 STL 顶点采样）。"""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    blade = data["blade-front"]
    handle = data["handle-front"]
    p = parse_params(params_path)
    hpts = sample_profile(handle, 48)
    y0 = min(p["handle_butt_y"], min(pt[1] for pt in hpts))
    y1 = p["blade_tip_y"]
    ys: list[float] = []
    hw: list[float] = []
    for i in range(n + 1):
        y = y0 + (y1 - y0) * i / n
        ys.append(y)
        hw.append(envelope_half_width_at_y(y, blade, handle, p["handle_join_y"]))
    return {
        "y_centers": ys,
        "half_width_pos_x": hw,
        "half_width_neg_x": hw,
        "max_asymmetry_mm": 0.0,
        "mean_asymmetry_mm": 0.0,
        "source": "bezier_design",
    }


def main() -> int:
    json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSON
    if not json_path.is_file():
        print(f"Missing {json_path}", file=sys.stderr)
        return 1

    data = json.loads(json_path.read_text(encoding="utf-8"))
    blade = data["blade-front"]
    handle = data["handle-front"]
    bottom = data.get("handle-bottom") or {
        "target": "handle-bottom",
        "start": {"x": 0, "y": 12.5},
        "segments": [
            {"cp1": {"x": 10, "y": 12.8}, "cp2": {"x": 17, "y": 10.5}, "end": {"x": 17, "y": 4}},
            {"cp1": {"x": 17, "y": -2}, "cp2": {"x": 17, "y": -9}, "end": {"x": 10, "y": -12.5}},
            {"cp1": {"x": 4, "y": -12.5}, "cp2": {"x": 0, "y": -12.2}, "end": {"x": 0, "y": -12.5}},
        ],
    }
    side = data.get("side") or DEFAULT_SIDE

    p = parse_params(DEFAULT_PARAMS)
    join_y = p["handle_join_y"]
    blade_core_t = p["blade_core_t"]

    blade_poly = blade_closed_polygon(blade)
    handle_slices = handle_loft_slices(handle, bottom, side, join_y, blade_core_t / 2, HANDLE_SLICES)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cavity_margin = p["wall_t"] + p["handle_cavity_inset"]
    tail_info = json.loads(TAIL_INTERFERENCE.read_text(encoding="utf-8"))
    available_wall = min(blade_core_t / 2, cavity_margin)
    screw_d = 1.0 if available_wall < 2.0 else 1.2 if available_wall < 3.5 else 1.4 if available_wall < 4.5 else 1.6
    boss_d = screw_d + 2 * min(1.40, cavity_margin - 0.5)
    head_d = screw_d * 1.90
    board_x_limit = max(abs(float(point[0])) for point in tail_info["edge_cuts_xy"])
    board_y_min = float(tail_info["pcb_y"]) - float(tail_info["board_axial_clear"])
    board_y_max = (
        float(tail_info["pcb_y"])
        + float(tail_info["board_thickness"])
        + float(tail_info["board_axial_clear"])
    )
    pcb_avoidance: dict[str, Any] = {
        "x_limit": board_x_limit,
        "y_min": board_y_min,
        "y_max": board_y_max,
        "bossDiameterMm": boss_d,
        "petgLigamentMm": p["m6_pcb_slot_min_ligament"],
        "required_center_clearance": boss_d / 2 + p["m6_pcb_slot_min_ligament"],
        "tail_required_center_clearance": boss_d / 2 + p["m6_tail_slot_min_ligament"],
        "min_station_pitch": boss_d + p["m6_core_edge_min_ligament"],
    }
    screw_positions = m6_screw_positions_on_midcurve(
        handle,
        min(s[0] for s in handle_slices),
        join_y,
        cavity_margin,
        int(p["m6_handle_screw_station_count"]),
        p["m6_handle_screw_top_clearance"],
        p["m6_handle_screw_bottom_clearance"],
        p["m6_handle_screw_tail_edge_clearance"],
        p["m6_handle_screw_tail_inset"],
        pcb_avoidance,
    )
    edge_checks = []
    direction_checks = []
    moved_y = [float(item["final"][1]) for item in pcb_avoidance["moves"] if item["moved"]]
    for position_index, (x, y) in enumerate(screw_positions):
        outer_margin = half_width_at_y(handle, y) - abs(x) - head_d / 2
        edge_checks.append({"position": [x, y], "outerEdgeLigamentMm": outer_margin})
        if outer_margin + 1e-6 < p["m6_core_edge_min_ligament"]:
            raise ValueError(
                f"M6 screw at {(x, y)} leaves {outer_margin:.3f}mm to core edge; "
                f"requires {p['m6_core_edge_min_ligament']:.3f}mm"
            )
        dx = max(abs(x) - board_x_limit, 0.0)
        dy = board_y_min - y if y < board_y_min else y - board_y_max if y > board_y_max else 0.0
        pcb_clearance = math.hypot(dx, dy)
        relocated = any(abs(y - value) < 1e-5 for value in moved_y)
        station_number = position_index // 2 + 1
        required_here = (
            pcb_avoidance["tail_required_center_clearance"]
            if station_number == 1
            else pcb_avoidance["required_center_clearance"]
        )
        for direction, z_side in (("layer2_to_layer1", "positive_z"), ("layer3_to_layer4", "negative_z")):
            direction_checks.append({
                "station": station_number,
                "visualCallout": (
                    "left_small_circles_tail_edge"
                    if position_index // 2 + 1 == 1
                    else "center_large_circle_pcb_slot_pair"
                    if position_index // 2 + 1 == 2
                    else None
                ),
                "side": "left" if x < 0 else "right",
                "direction": direction,
                "zSide": z_side,
                "position": [x, y],
                "relocatedForPcbSlot": relocated,
                "pcbSlotCenterClearanceMm": pcb_clearance,
                "requiredPcbSlotCenterClearanceMm": required_here,
                "outerEdgeLigamentMm": outer_margin,
                "passed": (
                    pcb_clearance + 1e-6 >= required_here
                    and outer_margin + 1e-6 >= p["m6_core_edge_min_ligament"]
                ),
            })
    SCREW_SAFETY_REPORT.write_text(
        json.dumps({
            "screwDiameterMm": screw_d,
            "headDiameterMm": head_d,
            "bossDiameterMm": boss_d,
            "pcbSlot": {"xLimitMm": board_x_limit, "yRangeMm": [board_y_min, board_y_max]},
            "requiredPcbSlotCenterClearanceMm": pcb_avoidance["required_center_clearance"],
            "requiredTailSlotCenterClearanceMm": pcb_avoidance["tail_required_center_clearance"],
            "requiredCoreEdgeLigamentMm": p["m6_core_edge_min_ligament"],
            "finalPositions": [[x, y] for x, y in screw_positions],
            "moves": pcb_avoidance["moves"],
            "edgeChecks": edge_checks,
            "directionChecks": direction_checks,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_scad(blade_poly, handle_slices, blade_core_t, join_y, cavity_margin, json_path)

    profiles_path = OUT_DIR / "profiles.scad"
    n = 128
    y0 = min(s[0] for s in handle_slices)
    y1 = max(p[1] for p in blade_poly)
    dh = (y1 - y0) / n
    hzs: list[float] = []
    hxs: list[float] = []
    for i in range(n + 1):
        y = y0 + i * dh
        hxs.append(envelope_half_width_at_y(y, blade, handle, join_y))
        if y >= join_y:
            hzs.append(blade_core_t / 2)
        elif side:
            hzs.append(max(half_width_at_y(side, y), 0.5))
        else:
            hzs.append(blade_core_t / 2)
    profiles_path.write_text(
        "\n".join(
            [
                "// AUTO-GENERATED — half_z lookup for bosses (from side profile)",
                f"BEZIER_Y0 = {fmt_num(y0)};",
                f"BEZIER_Y1 = {fmt_num(y1)};",
                f"BEZIER_N = {n};",
                f"BEZIER_DH = {fmt_num(dh)};",
                f"BEZIER_HZ = [{', '.join(fmt_num(z) for z in hzs)}];",
                f"BEZIER_HX = [{', '.join(fmt_num(x) for x in hxs)}];",
                "// AUTO-GENERATED — M6 screw centers on the midcurve between outer and cavity profiles",
                f"BEZIER_M6_SCREW_POSITIONS = {fmt_poly(screw_positions)};",
                "",
            ]
        ),
        encoding="utf-8",
    )

    xs = [abs(x) for x, _ in blade_poly]
    print(f"✓ {OUT_SCAD}")
    print(f"✓ {profiles_path}")
    print(f"  Blade polygon: {len(blade_poly)} pts, max |x|={max(xs):.1f} mm")
    print(f"  Handle slices: {len(handle_slices)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
