#!/usr/bin/env python3
"""Generate M5 fixed-battery tail PCB bare Edge.Cuts from the real handle loft.

板面不在最尾端：Type-C 超短体立贴身体高度 H_typec=5.8mm，外壳口与母座平齐时
  Y_pcb = Y_butt + H_typec
在该 Y 取外壳 XZ，再按 wall_t+cavity_inset 得到内壁，并加微小装配间隙。

Writes into the atopile layout board:
  pcb-tail/layouts/default/default.kicad_pcb

Board plane = handle XZ (thickness along Y).
  F.Cu / front  → handle butt end (−Y)
  B.Cu / back   → paddle head (+Y)
KiCad X = handle X ; KiCad Y = handle Z

参考：docs/usb-c-vertical-16p-short/
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import math
import re
import sys
import uuid
from pathlib import Path

from shapely.geometry import LinearRing, Polygon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from bezier_to_openscad import (  # noqa: E402
    DEFAULT_JSON,
    DEFAULT_PARAMS,
    DEFAULT_SIDE,
    handle_loft_slices,
    parse_params,
)


# ===== 分区：常量/配置 =====
HERE = Path(__file__).resolve().parent
LAYOUT_DIR = HERE / "layouts" / "default"
LAYOUT_PCB = LAYOUT_DIR / "default.kicad_pcb"
BOARD_CLEARANCE_MM = 0.20  # 内壁外再留的装配间隙（外形≈内壁）
BOARD_THICKNESS_MM = 1.00
# 16P 立贴超短体「身体高度」— docs/usb-c-vertical-16p-short/
USB_BODY_HEIGHT_MM = 5.80
EDGE_WIDTH_MM = 0.10  # match C4 Edge.Cuts visibility
SAMPLE_SLICES = 96  # denser loft sampling near butt for Y_pcb slice
OUTLINE_MAX_POINTS = 96
PREVIEW_SVG = HERE / "m5-tail-outline-preview.svg"
PREVIEW_PNG = HERE / "m5-tail-outline-preview.png"
REPORT_TXT = HERE / "geometry-report.txt"
OUTLINE_JSON = HERE / "outline-facts.json"
LEGACY_OUTLINE_PCB = HERE / "m5-tail-outline.kicad_pcb"

ATO_BARE_SHELL = """(kicad_pcb
    (version 20241229)
    (generator "atopile")
    (generator_version "0.12.5")
    (general
        (thickness 1.0)
        (legacy_teardrops no)
    )
    (paper "A4")
    (title_block
        (title "SmartPaddle M5 Tail")
        (date "")
        (rev "M5-TAIL-BARE")
        (company "SmartPaddle")
    )
    (layers
        (0 "F.Cu" signal)
        (31 "B.Cu" signal)
        (32 "B.Adhes" user "B.Adhesive")
        (33 "F.Adhes" user "F.Adhesive")
        (34 "B.Paste" user)
        (35 "F.Paste" user)
        (36 "B.SilkS" user "B.Silkscreen")
        (37 "F.SilkS" user "F.Silkscreen")
        (38 "B.Mask" user)
        (39 "F.Mask" user)
        (40 "Dwgs.User" user "User.Drawings")
        (41 "Cmts.User" user "User.Comments")
        (42 "Eco1.User" user "User.Eco1")
        (43 "Eco2.User" user "User.Eco2")
        (44 "Edge.Cuts" user)
        (45 "Margin" user)
        (46 "B.CrtYd" user "B.Courtyard")
        (47 "F.CrtYd" user "F.Courtyard")
        (48 "B.Fab" user)
        (49 "F.Fab" user)
        (50 "User.1" user)
        (51 "User.2" user)
        (52 "User.3" user)
        (53 "User.4" user)
        (54 "User.5" user)
        (55 "User.6" user)
        (56 "User.7" user)
        (57 "User.8" user)
        (58 "User.9" user)
    )
    (setup
        (pad_to_mask_clearance 0)
        (allow_soldermask_bridges_in_footprints no)
    )
    (net 0 "")
)
"""


# ===== 分区：私有成员 =====
def _resample_ring(coords: list[tuple[float, float]], n: int) -> list[tuple[float, float]]:
    if len(coords) < 3:
        raise ValueError("ring too short")
    pts = coords[:]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    seg_lens = [
        math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        for i in range(len(pts) - 1)
    ]
    total = sum(seg_lens)
    if total <= 0:
        raise ValueError("zero-length ring")
    out: list[tuple[float, float]] = []
    for i in range(n):
        target = total * i / n
        acc = 0.0
        for j, sl in enumerate(seg_lens):
            if acc + sl >= target or j == len(seg_lens) - 1:
                t = 0.0 if sl <= 1e-12 else (target - acc) / sl
                ax, ay = pts[j]
                bx, by = pts[j + 1]
                out.append((ax + (bx - ax) * t, ay + (by - ay) * t))
                break
            acc += sl
    return out


def _ccw(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    area2 = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        area2 += x0 * y1 - x1 * y0
    return pts if area2 > 0 else list(reversed(pts))


def _kicad_edge_poly(pts: list[tuple[float, float]]) -> str:
    """Single closed Edge.Cuts polygon — more reliable than many gr_line segments."""
    closed = list(pts)
    if closed[0] != closed[-1]:
        closed.append(closed[0])
    xy = "\n".join(f"            (xy {x:.4f} {y:.4f})" for x, y in closed)
    return (
        "    (gr_poly\n"
        "        (pts\n"
        f"{xy}\n"
        "        )\n"
        f"        (stroke (width {EDGE_WIDTH_MM:.2f}) (type default))\n"
        "        (fill none)\n"
        '        (layer "Edge.Cuts")\n'
        f'        (uuid "{uuid.uuid4()}")\n'
        "    )"
    )


def _lerp_poly(
    a: list[tuple[float, float]],
    b: list[tuple[float, float]],
    t: float,
) -> list[tuple[float, float]]:
    if len(a) != len(b):
        raise RuntimeError("loft polygons must share vertex count")
    return [
        (ax + (bx - ax) * t, az + (bz - az) * t)
        for (ax, az), (bx, bz) in zip(a, b)
    ]


def _outer_at_y(
    slices: list[tuple[float, list[tuple[float, float]]]],
    y: float,
) -> list[tuple[float, float]]:
    """Interpolate outer XZ shell polygon at world Y."""
    if y <= slices[0][0]:
        return list(slices[0][1])
    if y >= slices[-1][0]:
        return list(slices[-1][1])
    for (y0, p0), (y1, p1) in zip(slices, slices[1:]):
        if y0 <= y <= y1:
            if y1 <= y0:
                return list(p0)
            t = (y - y0) / (y1 - y0)
            return _lerp_poly(p0, p1, t)
    return list(slices[-1][1])


def _load_pcb_plane_outer() -> tuple[float, float, list[tuple[float, float]], list[tuple[float, float]], dict[str, float]]:
    """Return (butt_y, pcb_y, outer_at_butt, outer_at_pcb, params)."""
    data = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
    params = parse_params(DEFAULT_PARAMS)
    side = data.get("side") or DEFAULT_SIDE
    slices = handle_loft_slices(
        data["handle-front"],
        data["handle-bottom"],
        side,
        params["handle_join_y"],
        params["blade_core_t"] / 2.0,
        SAMPLE_SLICES,
    )
    butt_y = slices[0][0]
    pcb_y = butt_y + USB_BODY_HEIGHT_MM
    outer_butt = slices[0][1]
    outer_pcb = _outer_at_y(slices, pcb_y)
    return butt_y, pcb_y, outer_butt, outer_pcb, params


def _inset_board_outline(
    outer_xz: list[tuple[float, float]],
    inset_mm: float,
) -> list[tuple[float, float]]:
    poly = Polygon(outer_xz)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty or not isinstance(poly, Polygon):
        raise RuntimeError("outer butt polygon is invalid")
    inner = poly.buffer(-inset_mm)
    if inner.is_empty:
        raise RuntimeError(f"inset {inset_mm} mm emptied the butt profile")
    if inner.geom_type == "MultiPolygon":
        inner = max(inner.geoms, key=lambda g: g.area)
    if not isinstance(inner, Polygon):
        raise RuntimeError(f"unexpected inset geometry: {inner.geom_type}")
    coords = list(inner.exterior.coords)[:-1]
    ring = _resample_ring(coords, OUTLINE_MAX_POINTS)
    return _ccw([(x, z) for x, z in ring])


def _extent(pts: list[tuple[float, float]]) -> dict[str, float]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
        "half_x": max(abs(x) for x in xs),
        "half_y": max(abs(y) for y in ys),
    }


def _strip_sexpr_blocks(text: str, head: str) -> str:
    """Remove top-level (...) blocks whose token after '(' starts with head."""
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "(" and text.startswith(head, i + 1):
            depth = 0
            j = i
            while j < n:
                ch = text[j]
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            # drop preceding newline/whitespace belonging to the block
            k = len(out)
            while k > 0 and out[k - 1] in " \t":
                k -= 1
            if k > 0 and out[k - 1] == "\n":
                k -= 1
            out = out[:k]
            i = j
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _strip_graphics(text: str) -> str:
    """Remove board graphics so only footprints/nets remain before re-injecting Edge.Cuts."""
    for head in (
        "gr_line",
        "gr_arc",
        "gr_circle",
        "gr_rect",
        "gr_poly",
        "gr_text",
        "gr_curve",
    ):
        text = _strip_sexpr_blocks(text, head)
    return text



def _set_thickness(text: str, thickness: float) -> str:
    if re.search(r"\(thickness\s+[0-9.]+\)", text):
        return re.sub(r"\(thickness\s+[0-9.]+\)", f"(thickness {thickness:.1f})", text, count=1)
    return text.replace(
        "(general",
        f"(general\n        (thickness {thickness:.1f})",
        1,
    )


def _ensure_title_block(text: str) -> str:
    block = (
        "    (title_block\n"
        '        (title "SmartPaddle M5 Tail")\n'
        '        (date "")\n'
        '        (rev "M5-TAIL-BARE")\n'
        '        (company "SmartPaddle")\n'
        "    )"
    )
    if "(title_block" in text:
        return re.sub(r"\(title_block\b(?:[^()]|\([^()]*\))*\)", block, text, count=1, flags=re.S)
    return text.replace("(paper \"A4\")", f'(paper "A4")\n{block}', 1)


def _apply_bare_outline(edge_pts: list[tuple[float, float]]) -> None:
    LAYOUT_DIR.mkdir(parents=True, exist_ok=True)
    if LAYOUT_PCB.is_file():
        text = LAYOUT_PCB.read_text(encoding="utf-8")
    else:
        text = ATO_BARE_SHELL

    text = _strip_graphics(text)
    text = _set_thickness(text, BOARD_THICKNESS_MM)
    text = _ensure_title_block(text)

    edge_poly = _kicad_edge_poly(edge_pts)
    text = text.rstrip()
    if not text.endswith(")"):
        raise RuntimeError(f"unexpected PCB footer in {LAYOUT_PCB}")
    text = text[:-1].rstrip() + "\n" + edge_poly + "\n)\n"
    LAYOUT_PCB.write_text(text, encoding="utf-8")


def _write_png(
    edge_pts: list[tuple[float, float]],
    outer_pts: list[tuple[float, float]],
) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(6, 5))
    ox, oy = zip(*outer_pts)
    ex, ey = zip(*edge_pts)
    ax.plot([*ox, ox[0]], [*oy, oy[0]], "--", color="#94a3b8", lw=1.2, label="outer shell")
    ax.fill([*ex, ex[0]], [*ey, ey[0]], color="#2d9c5a", alpha=0.85, label="Edge.Cuts")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    ax.set_xlabel("KiCad X = handle X (mm)")
    ax.set_ylabel("KiCad Y = handle Z (mm)")
    ax.set_title("M5 tail bare PCB (front = handle end)")
    fig.tight_layout()
    fig.savefig(PREVIEW_PNG, dpi=140)
    plt.close(fig)


def _write_svg(
    edge_pts: list[tuple[float, float]],
    outer_pts: list[tuple[float, float]],
    facts: dict,
) -> None:
    all_pts = edge_pts + outer_pts
    min_x = min(p[0] for p in all_pts) - 6
    max_x = max(p[0] for p in all_pts) + 6
    min_y = min(p[1] for p in all_pts) - 8
    max_y = max(p[1] for p in all_pts) + 8
    scale = 8.0

    def sx(x: float) -> float:
        return (x - min_x) * scale

    def sy(y: float) -> float:
        return (max_y - y) * scale

    width = (max_x - min_x) * scale
    height = (max_y - min_y) * scale
    outer_poly = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in outer_pts)
    edge_poly = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in edge_pts)
    e = facts["edge"]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.2f} {height:.2f}">
<rect width="100%" height="100%" fill="#f4f6f8"/>
<text x="16" y="22" font-size="16" font-weight="700" fill="#102a43">M5 尾部裸板 Edge.Cuts</text>
<text x="16" y="42" font-size="12" fill="#334e68">正面→拍柄末端  背面→拍头  ·  KiCad X=柄X  Y=柄Z</text>
<polygon points="{outer_poly}" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 3"/>
<polygon points="{edge_poly}" fill="#2d9c5a" fill-opacity="0.85" stroke="#0d5f36" stroke-width="2"/>
<line x1="{sx(0):.2f}" y1="{sy(min_y+1):.2f}" x2="{sx(0):.2f}" y2="{sy(max_y-1):.2f}" stroke="#64748b" stroke-width="0.8"/>
<line x1="{sx(min_x+1):.2f}" y1="{sy(0):.2f}" x2="{sx(max_x-1):.2f}" y2="{sy(0):.2f}" stroke="#64748b" stroke-width="0.8"/>
<text x="16" y="{height-18:.1f}" font-size="12" fill="#334e68">虚线=Y_pcb外壳 · 实心=内壁≈裸板 {e['width']:.2f}×{e['height']:.2f} mm · H_usb={USB_BODY_HEIGHT_MM:.1f} · t={BOARD_THICKNESS_MM:.1f}</text>
</svg>
'''
    PREVIEW_SVG.write_text(svg, encoding="utf-8")


def _write_report(facts: dict) -> None:
    o = facts["outer"]
    e = facts["edge"]
    report = f"""SmartPaddle M5 tail PCB bare-board geometry report
STATUS: BARE OUTLINE / ATO MODULE PRESENT / NOT FOR FABRICATION

Entry: main.ato:SmartPaddleTail
Layout: layouts/default/default.kicad_pcb

Source profile: web/src/data/userBezierProfiles.json (handle loft)
Butt world Y (outer face): {facts['butt_y']:.4f} mm
PCB plane Y (F.Cu):        {facts['pcb_y']:.4f} mm
  = butt_y + USB_BODY_HEIGHT ({facts['usb_body_height']:.2f} mm)
  docs: docs/usb-c-vertical-16p-short/ (H_typec=5.8)

Orientation:
  Board plane = handle XZ at Y_pcb
  F.Cu / front → handle end (−Y)
  B.Cu / back  → paddle head (+Y)
  KiCad X = handle X
  KiCad Y = handle Z

Inset stack (per side, from outer shell at Y_pcb → ≈inner wall):
  wall_t              = {facts['wall_t']:.2f} mm
  handle_cavity_inset = {facts['cavity_inset']:.2f} mm
  board_clearance     = {facts['board_clearance']:.2f} mm
  total_inset         = {facts['total_inset']:.2f} mm

Outer shell at Y_pcb extents (bbox):
  width×height = {o['width']:.3f} × {o['height']:.3f} mm
  |x|_max = {o['half_x']:.3f} mm   |z|_max = {o['half_y']:.3f} mm

PCB Edge.Cuts extents (bbox):
  width×height = {e['width']:.3f} × {e['height']:.3f} mm
  |x|_max = {e['half_x']:.3f} mm   |z|_max = {e['half_y']:.3f} mm
  points = {facts['point_count']}
  thickness = {BOARD_THICKNESS_MM:.2f} mm
"""
    REPORT_TXT.write_text(report, encoding="utf-8")
    OUTLINE_JSON.write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")


# ===== 分区：公开 API =====
def main() -> int:
    butt_y, pcb_y, _outer_butt, outer_pcb, params = _load_pcb_plane_outer()
    # 内壁 = 外壳 − (wall + cavity)；再减微小装配间隙
    total_inset = params["wall_t"] + params["handle_cavity_inset"] + BOARD_CLEARANCE_MM
    outer_kicad = _ccw(_resample_ring([(x, z) for x, z in outer_pcb], OUTLINE_MAX_POINTS))
    edge_pts = _inset_board_outline(outer_pcb, total_inset)

    ring = LinearRing(edge_pts + [edge_pts[0]])
    if not ring.is_simple:
        raise RuntimeError("Edge.Cuts ring is self-intersecting")

    facts = {
        "butt_y": butt_y,
        "pcb_y": pcb_y,
        "usb_body_height": USB_BODY_HEIGHT_MM,
        "wall_t": params["wall_t"],
        "cavity_inset": params["handle_cavity_inset"],
        "board_clearance": BOARD_CLEARANCE_MM,
        "total_inset": total_inset,
        "board_thickness": BOARD_THICKNESS_MM,
        "point_count": len(edge_pts),
        "layout_pcb": str(LAYOUT_PCB.relative_to(ROOT)),
        "ato_entry": "main.ato:SmartPaddleTail",
        "usb_ref": "docs/usb-c-vertical-16p-short/",
        "outer": _extent(outer_kicad),
        "edge": _extent(edge_pts),
        "orientation": {
            "plane": "XZ",
            "front": "handle_end_-Y",
            "back": "paddle_head_+Y",
            "kicad_x": "handle_X",
            "kicad_y": "handle_Z",
        },
    }
    _apply_bare_outline(edge_pts)
    _write_svg(edge_pts, outer_kicad, facts)
    _write_png(edge_pts, outer_kicad)
    _write_report(facts)
    if LEGACY_OUTLINE_PCB.is_file():
        LEGACY_OUTLINE_PCB.unlink()

    print(f"✓ {LAYOUT_PCB.relative_to(ROOT)}  (bare Edge.Cuts)")
    print(f"✓ {PREVIEW_SVG.relative_to(ROOT)}")
    if PREVIEW_PNG.is_file():
        print(f"✓ {PREVIEW_PNG.relative_to(ROOT)}")
    print(f"✓ {REPORT_TXT.relative_to(ROOT)}")
    print(
        f"  Y_pcb=butt+{USB_BODY_HEIGHT_MM:.1f}  "
        f"Edge.Cuts {facts['edge']['width']:.2f}×{facts['edge']['height']:.2f} mm "
        f"(inset {total_inset:.2f} mm from shell at Y_pcb)"
    )
    return 0


# ===== 分区：方法/工具 =====
if __name__ == "__main__":
    raise SystemExit(main())
