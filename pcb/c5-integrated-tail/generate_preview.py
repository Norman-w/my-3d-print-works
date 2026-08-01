#!/usr/bin/env python3
"""Generate the isolated C5 integrated-tail mechanical preview.

This script deliberately does not read or modify the active C4 KiCad board.  It
uses the generated handle-cavity slices only to derive the available width.
The output is a mechanical discussion aid, not a production PCB.
"""

from __future__ import annotations

import math
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CAVITY_SCAD = REPO / "enclosure/generated/bezier_geometry.scad"

ROOT_Y = 90.0
BOARD_END_Y = 167.1
WINDOW_X_HALF = 7.4
WINDOW_HEAD_Y = 94.5
WINDOW_TAIL_Y = 145.5
WINDOW_RADIUS = 1.5
WALL_CLEARANCE = 0.5
ROOT_HALF_WIDTH = 8.75
TAIL_HALF_WIDTH = 13.0


def _cavity_slices() -> list[tuple[float, float]]:
    text = CAVITY_SCAD.read_text(encoding="utf-8")
    section = text[text.index("module bezier_handle_cavity()") :]
    pattern = re.compile(
        r"translate\(\[0,\s*(-?[0-9.]+),\s*0\]\).*?"
        r"polygon\(points = \[(.*?)\]\);",
        re.S,
    )
    result: list[tuple[float, float]] = []
    for match in pattern.finditer(section):
        scad_y = float(match.group(1))
        points = [
            (float(x), float(z))
            for x, z in re.findall(
                r"\[(-?[0-9.]+),\s*(-?[0-9.]+)\]", match.group(2)
            )
        ]
        if points:
            kicad_y = -scad_y - 10.0
            cavity_half_width = max(abs(x) for x, _ in points)
            result.append((kicad_y, cavity_half_width))
    if not result:
        raise RuntimeError(f"No cavity slices parsed from {CAVITY_SCAD}")
    return sorted(result)


def _interp(rows: list[tuple[float, float]], y: float) -> float:
    if y <= rows[0][0]:
        return rows[0][1]
    if y >= rows[-1][0]:
        return rows[-1][1]
    for (y0, x0), (y1, x1) in zip(rows, rows[1:]):
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            return x0 + (x1 - x0) * t
    raise AssertionError(y)


def board_half_width(rows: list[tuple[float, float]], y: float) -> float:
    # Preserve the existing C4 neck at the join, then blend into the measured
    # cavity.  The final 3.5 mm requires a new shell pocket and tapers to the
    # deliberately conservative tail width.
    measured_end = rows[-1][0]
    if y <= ROOT_Y + 4.5:
        target = _interp(rows, min(y, measured_end)) - WALL_CLEARANCE
        t = max(0.0, min(1.0, (y - ROOT_Y) / 4.5))
        return ROOT_HALF_WIDTH * (1.0 - t) + target * t
    if y <= measured_end:
        return _interp(rows, y) - WALL_CLEARANCE
    t = min(1.0, (y - measured_end) / (BOARD_END_Y - measured_end))
    return (_interp(rows, measured_end) - WALL_CLEARANCE) * (1.0 - t) + TAIL_HALF_WIDTH * t


def outer_points(rows: list[tuple[float, float]]) -> list[tuple[float, float]]:
    ys = [ROOT_Y]
    y = ROOT_Y + 2.5
    while y < BOARD_END_Y:
        ys.append(round(y, 4))
        y += 2.5
    ys.append(BOARD_END_Y)
    right = [(board_half_width(rows, y), y) for y in ys]
    left = [(-board_half_width(rows, y), y) for y in reversed(ys)]
    return right + left


def _kicad_line(a: tuple[float, float], b: tuple[float, float], layer: str = "Edge.Cuts") -> str:
    return (
        f'  (gr_line (start {a[0]:.4f} {a[1]:.4f}) '
        f'(end {b[0]:.4f} {b[1]:.4f}) (stroke (width 0.05) (type default)) '
        f'(layer "{layer}"))'
    )


def _kicad_rect(x0: float, y0: float, x1: float, y1: float, layer: str = "F.SilkS") -> str:
    return (
        f'  (gr_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) '
        f'(stroke (width 0.25) (type default)) (fill none) (layer "{layer}"))'
    )


def _kicad_text(text: str, x: float, y: float, size: float = 1.0, layer: str = "F.SilkS") -> str:
    return (
        f'  (gr_text "{text}" (at {x:.3f} {y:.3f}) (layer "{layer}") '
        f'(effects (font (size {size:.2f} {size:.2f}) (thickness 0.15))))'
    )


def write_kicad(rows: list[tuple[float, float]]) -> None:
    points = outer_points(rows)
    edge_lines = [_kicad_line(a, b) for a, b in zip(points, points[1:] + points[:1])]

    r = WINDOW_RADIUS
    x = WINDOW_X_HALF
    yh = WINDOW_HEAD_Y
    yt = WINDOW_TAIL_Y
    mid = r / math.sqrt(2.0)
    cutout = [
        _kicad_line((-x + r, yh), (x - r, yh)),
        (
            f'  (gr_arc (start {x-r:.4f} {yh:.4f}) '
            f'(mid {x-mid:.4f} {yh+r-mid:.4f}) (end {x:.4f} {yh+r:.4f}) '
            '(stroke (width 0.05) (type default)) (layer "Edge.Cuts"))'
        ),
        _kicad_line((x, yh + r), (x, yt - r)),
        (
            f'  (gr_arc (start {x:.4f} {yt-r:.4f}) '
            f'(mid {x-mid:.4f} {yt-r+mid:.4f}) (end {x-r:.4f} {yt:.4f}) '
            '(stroke (width 0.05) (type default)) (layer "Edge.Cuts"))'
        ),
        _kicad_line((x - r, yt), (-x + r, yt)),
        (
            f'  (gr_arc (start {-x+r:.4f} {yt:.4f}) '
            f'(mid {-x+mid:.4f} {yt-r+mid:.4f}) (end {-x:.4f} {yt-r:.4f}) '
            '(stroke (width 0.05) (type default)) (layer "Edge.Cuts"))'
        ),
        _kicad_line((-x, yt - r), (-x, yh + r)),
        (
            f'  (gr_arc (start {-x:.4f} {yh+r:.4f}) '
            f'(mid {-x+mid:.4f} {yh+r-mid:.4f}) (end {-x+r:.4f} {yh:.4f}) '
            '(stroke (width 0.05) (type default)) (layer "Edge.Cuts"))'
        ),
    ]

    placeholders = [
        _kicad_rect(-5.0, 158.2, 5.0, 166.8),
        _kicad_text("J1 USB-C 16P", 0.0, 163.0, 0.85),
        _kicad_rect(-9.6, 149.0, -4.2, 156.0),
        _kicad_text("U1 IP5305T TBD", -6.9, 152.5, 0.65),
        _kicad_rect(3.2, 150.0, 7.8, 154.6),
        _kicad_text("L1 2R2", 5.5, 152.3, 0.7),
        _kicad_rect(7.0, 158.5, 11.8, 163.3),
        _kicad_text("SW1", 9.4, 160.9, 0.75),
        _kicad_text("BAT- TAB", 0.0, 92.4, 0.75),
        _kicad_text("BAT+ TAB", 0.0, 147.2, 0.75),
        _kicad_text("14500 WINDOW 14.8 x 51.0 / TBD BY CELL", 0.0, 120.0, 0.75, "Cmts.User"),
        _kicad_text("C5 MECHANICAL PREVIEW - NOT FOR FAB", 0.0, 89.0, 0.9, "Cmts.User"),
    ]

    content = "\n".join(
        [
            "(kicad_pcb",
            "  (version 20241229)",
            '  (generator "smartpaddle-c5-mechanical-preview")',
            "  (general (thickness 0.8))",
            '  (paper "A4")',
            '  (title_block (title "SmartPaddle C5 Integrated Tail - Mechanical Preview") (rev "C5-MECH-TBD") (company "SmartPaddle"))',
            "  (layers",
            '    (0 "F.Cu" signal)',
            '    (2 "B.Cu" signal)',
            '    (5 "F.SilkS" user "F.Silkscreen")',
            '    (7 "B.SilkS" user "B.Silkscreen")',
            '    (1 "F.Mask" user)',
            '    (3 "B.Mask" user)',
            '    (21 "Eco1.User" user "Eco1.User")',
            '    (25 "Edge.Cuts" user)',
            '    (19 "Cmts.User" user "User.Comments")',
            "  )",
            "  (setup (pad_to_mask_clearance 0))",
            *edge_lines,
            *cutout,
            *placeholders,
            ")",
            "",
        ]
    )
    (HERE / "c5-integrated-tail-mechanical.kicad_pcb").write_text(content, encoding="utf-8")


def write_svg(rows: list[tuple[float, float]]) -> None:
    points = outer_points(rows)
    min_x = min(x for x, _ in points) - 22
    max_x = max(x for x, _ in points) + 54
    min_y = ROOT_Y - 9
    max_y = BOARD_END_Y + 7
    scale = 7.0

    def sx(x: float) -> float:
        return (x - min_x) * scale

    def sy(y: float) -> float:
        return (y - min_y) * scale

    width = (max_x - min_x) * scale
    height = (max_y - min_y) * scale
    polygon = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in points)
    wx = sx(-WINDOW_X_HALF)
    wy = sy(WINDOW_HEAD_Y)
    ww = WINDOW_X_HALF * 2 * scale
    wh = (WINDOW_TAIL_Y - WINDOW_HEAD_Y) * scale

    def rect(x0: float, y0: float, x1: float, y1: float, fill: str, label: str) -> str:
        return (
            f'<rect x="{sx(x0):.2f}" y="{sy(y0):.2f}" width="{(x1-x0)*scale:.2f}" '
            f'height="{(y1-y0)*scale:.2f}" rx="3" fill="{fill}" stroke="#102a43" stroke-width="1.5"/>'
            f'<text x="{sx((x0+x1)/2):.2f}" y="{sy((y0+y1)/2):.2f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="11" fill="#102a43">{label}</text>'
        )

    min_rail = min(
        board_half_width(rows, y) - WINDOW_X_HALF
        for y in [WINDOW_HEAD_Y + i * 0.25 for i in range(int((WINDOW_TAIL_Y-WINDOW_HEAD_Y)/0.25)+1)]
    )
    min_rail_y = min(
        [WINDOW_HEAD_Y + i * 0.25 for i in range(int((WINDOW_TAIL_Y-WINDOW_HEAD_Y)/0.25)+1)],
        key=lambda y: board_half_width(rows, y) - WINDOW_X_HALF,
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.2f} {height:.2f}">
<rect x="0" y="0" width="{width:.2f}" height="{height:.2f}" fill="#f5f7fa"/>
<text x="18" y="24" font-size="17" font-weight="700" fill="#102a43">SmartPaddle C5 一体长尾板机械预览（非生产文件）</text>
<polygon points="{polygon}" fill="#2d9c5a" stroke="#0d5f36" stroke-width="2"/>
<rect x="{wx:.2f}" y="{wy:.2f}" width="{ww:.2f}" height="{wh:.2f}" rx="{WINDOW_RADIUS*scale:.2f}" fill="#dfe7ef" stroke="#9b1c1c" stroke-width="2"/>
<rect x="{sx(-7.15):.2f}" y="{sy(WINDOW_HEAD_Y+0.7):.2f}" width="{14.3*scale:.2f}" height="{49.4*scale:.2f}" rx="{7.15*scale:.2f}" fill="#d6a448" stroke="#7a4d0b" stroke-width="2" opacity="0.90"/>
<text x="{sx(0):.2f}" y="{sy(120):.2f}" text-anchor="middle" dominant-baseline="middle" transform="rotate(90 {sx(0):.2f} {sy(120):.2f})" font-size="13" fill="#3d2b08">14500 目标包络 Ø14.3 × 49.4</text>
{rect(-5.0, 158.2, 5.0, 166.8, '#b7d7f0', 'J1 USB-C')}
{rect(-9.6, 149.0, -4.2, 156.0, '#f7c59f', 'U1')}
{rect(3.2, 150.0, 7.8, 154.6, '#b8b8b8', 'L1 2R2')}
{rect(7.0, 158.5, 11.8, 163.3, '#f0d264', 'SW1')}
<line x1="{sx(-WINDOW_X_HALF):.2f}" y1="{sy(WINDOW_HEAD_Y-1.8):.2f}" x2="{sx(WINDOW_X_HALF):.2f}" y2="{sy(WINDOW_HEAD_Y-1.8):.2f}" stroke="#9b1c1c" stroke-width="1.5"/>
<text x="{sx(0):.2f}" y="{sy(WINDOW_HEAD_Y-2.6):.2f}" text-anchor="middle" font-size="12" fill="#9b1c1c">开窗 14.8 mm</text>
<line x1="{sx(board_half_width(rows, 108)+0.6):.2f}" y1="{sy(108):.2f}" x2="{sx(18):.2f}" y2="{sy(108):.2f}" stroke="#334e68" stroke-width="1.2"/>
<text x="{sx(19):.2f}" y="{sy(107.5):.2f}" text-anchor="start" font-size="12" fill="#334e68">D+/D− 同走一侧板桥</text>
<text x="{sx(19):.2f}" y="{sy(111):.2f}" text-anchor="start" font-size="12" fill="#334e68">最窄板桥 {min_rail:.2f} mm @ Y={min_rail_y:.1f}</text>
<text x="{sx(min_x+1):.2f}" y="{sy(89):.2f}" font-size="12" fill="#334e68">C4 接续线 Y=90.0</text>
<text x="{sx(min_x+1):.2f}" y="{sy(166):.2f}" font-size="12" fill="#334e68">PCB 尾端 Y=167.1</text>
</svg>
'''
    (HERE / "c5-integrated-tail-preview.svg").write_text(svg, encoding="utf-8")

    report = f"""SmartPaddle C5 integrated-tail geometry report
STATUS: MECHANICAL DRAFT / NOT FOR FABRICATION / NOT ASSEMBLY TESTED

Existing C4 tail join Y: {ROOT_Y:.2f} mm
Proposed PCB tail Y:      {BOARD_END_Y:.2f} mm
Added board length:       {BOARD_END_Y-ROOT_Y:.2f} mm
Battery window:           {WINDOW_X_HALF*2:.2f} x {WINDOW_TAIL_Y-WINDOW_HEAD_Y:.2f} mm, R{WINDOW_RADIUS:.2f}
Window Y range:           {WINDOW_HEAD_Y:.2f} .. {WINDOW_TAIL_Y:.2f} mm
Minimum calculated rail:  {min_rail:.2f} mm at Y={min_rail_y:.2f} mm
Tail component platform:  {BOARD_END_Y-WINDOW_TAIL_Y:.2f} mm long

The last portion of the PCB requires a new shell pocket. The current shell
cavity stops before the butt wall. Final dimensions require the purchased cell
and USB-C connector samples.
"""
    (HERE / "geometry-report.txt").write_text(report, encoding="utf-8")


def main() -> None:
    rows = _cavity_slices()
    write_kicad(rows)
    write_svg(rows)
    print(f"Generated C5 preview in {HERE}")


if __name__ == "__main__":
    main()
