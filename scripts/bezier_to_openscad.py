#!/usr/bin/env python3
"""
Export web Bezier profiles → OpenSCAD geometry matching paddleFromBezier.ts:
  - Blade: closed XY polygon + linear_extrude (not Y-sliced circles)
  - Handle: butt ring lofted with front/side scaling per slice
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "web/src/data/userBezierProfiles.json"
DEFAULT_PARAMS = ROOT / "enclosure/parameters.scad"
OUT_DIR = ROOT / "enclosure/generated"
OUT_SCAD = OUT_DIR / "bezier_geometry.scad"

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

HANDLE_SLICES = 56
RING_SEGMENTS = 40
JOIN_GAP_MM = 0.0  # shell meets blade at join (Live preview uses 0.6 mm gap)


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
    pts = sample_profile(profile, 40)
    x = abs(pts[0][0])
    for px, py in pts:
        if abs(py - y_mm) < abs(pts[0][1] - y_mm):
            x = abs(px)
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        if (ay <= y_mm <= by) or (by <= y_mm <= ay):
            t = 0.5 if abs(by - ay) < 1e-6 else (y_mm - ay) / (by - ay)
            x = max(x, abs(ax + t * (bx - ax)))
    return max(x, 0.5)


def close_symmetric_right(right: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = list(right)
    lx, ly = right[-1]
    if abs(lx) > 0.01:
        out.append((-lx, ly))
    for i in range(len(right) - 2, -1, -1):
        out.append((-right[i][0], right[i][1]))
    return out


def blade_closed_polygon(blade: dict[str, Any], join_y: float = -78.5) -> list[tuple[float, float]]:
    pts = clip_open_polyline_at_min_y(sample_profile(blade, 48), join_y)
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
    slices: int,
) -> list[tuple[float, list[tuple[float, float]]]]:
    """List of (y_center, polygon in XZ as (x,z) pairs)."""
    ring = butt_cross_section_ring(bottom, RING_SEGMENTS)
    base_hw = max(max(p[0] for p in ring), 1.0)
    base_ht = max(max(abs(p[1]) for p in ring), 1.0)
    hpts = sample_profile(handle, 48)
    bottom_y = min(p[1] for p in hpts)
    top_y = min(max(p[1] for p in hpts), join_y - JOIN_GAP_MM)
    out: list[tuple[float, list[tuple[float, float]]]] = []
    for s in range(slices):
        t = s / max(slices - 1, 1)
        y = bottom_y + t * (top_y - bottom_y)
        hw = half_width_at_y(handle, y)
        ht = half_width_at_y(side, y) if side else base_ht * (hw / base_hw)
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
    lines = [
        "// AUTO-GENERATED by scripts/bezier_to_openscad.py — do not edit",
        f"// Source: {json_path.relative_to(ROOT)}",
        "// Geometry matches web/src/lib/paddleFromBezier.ts (blade extrude + handle loft)",
        "",
        f"BEZIER_BLADE_CORE_T = {fmt_num(blade_core_t)};",
        f"BEZIER_JOIN_Y = {fmt_num(join_y)};",
        f"BEZIER_BLADE_POLY = {fmt_poly(blade_poly)};",
        "",
        "module bezier_blade_solid() {",
        "    linear_extrude(height = BEZIER_BLADE_CORE_T, center = true)",
        "        polygon(points = BEZIER_BLADE_POLY);",
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
    for i in range(len(handle_slices) - 1):
        y0, poly0 = handle_slices[i]
        y1, _ = handle_slices[i + 1]
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
        hw.append(paddle_hx_at_y(y, blade, handle, p))
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

    blade_poly = blade_closed_polygon(blade, join_y)
    handle_slices = handle_loft_slices(handle, bottom, side, join_y, HANDLE_SLICES)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cavity_margin = p["wall_t"] + p["handle_cavity_inset"]
    write_scad(blade_poly, handle_slices, blade_core_t, join_y, cavity_margin, json_path)

    profiles_path = OUT_DIR / "profiles.scad"
    n = 128
    y0 = min(s[0] for s in handle_slices)
    y1 = max(p[1] for p in blade_poly)
    dh = (y1 - y0) / n
    hzs = []
    for i in range(n + 1):
        y = y0 + i * dh
        if y >= join_y - 5:
            hzs.append(blade_core_t / 2)
        else:
            hzs.append(half_width_at_y(side, y))
    profiles_path.write_text(
        "\n".join(
            [
                "// AUTO-GENERATED — half_z lookup for bosses (from side profile)",
                f"BEZIER_Y0 = {fmt_num(y0)};",
                f"BEZIER_Y1 = {fmt_num(y1)};",
                f"BEZIER_N = {n};",
                f"BEZIER_DH = {fmt_num(dh)};",
                f"BEZIER_HZ = [{', '.join(fmt_num(z) for z in hzs)}];",
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
