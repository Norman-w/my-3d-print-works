#!/usr/bin/env python3
"""Recommended-relative cluster parking for pcb-tail (sexpr; no pcbnew).

Not random: each pile uses pin-aware relative offsets; front piles sit south of
Edge.Cuts, back piles north. KiCad groups: side_front / side_back + functional piles.

After open: drag a side group or a pile → nudge spacing → route.

  python3 pcb-tail/scripts/cluster_place.py
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import math
import re
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ===== 分区：常量/配置 =====
HERE = Path(__file__).resolve().parent
PCB = HERE.parent / "layouts" / "default" / "default.kicad_pcb"
PREVIEW = HERE.parent / "cluster-exploded-preview.png"

# Local (dx, dy, rot) relative to pile origin — recommended topology, ~2–3 mm air gap.
# World = pile_origin + local. Front zone Y<0 (south of board); back zone Y>0 (north).
_PILE_LOCAL: dict[str, dict[str, tuple[float, float, float]]] = {
    # USB: U2 on A-row (−Y) rot=-90; R1@cc1 left; R2@cc2 +Y
    "usb_front": {
        "J1": (0.0, 0.0, 0),
        "U2": (0.0, -8.5, -90),
        "R1": (-9.5, -1.5, 90),
        "R2": (3.5, 7.5, 90),
    },
    # UI: SW primary; WS2812+C beside; status LED left of SW (front-visible)
    "ui_front": {
        "SW1": (0.0, 0.0, 0),
        "D1": (0.0, -7.0, 0),
        "C1": (4.0, -7.0, 0),
        "LED1": (-6.0, 0.0, 90),
    },
    # PMIC: VIN island −X; L1/SW/BAT +X; VOUT caps around L1
    "power_back": {
        "U3": (0.0, 0.0, 0),
        "L1": (6.5, 0.0, 90),
        "C4": (-5.5, 2.5, 90),
        "C5": (-5.5, -2.5, 90),
        "R7": (-5.5, 0.0, 0),
        "C6": (6.5, 3.5, 0),
        "C3": (6.5, -3.5, 0),
        "C7": (10.0, 0.0, 0),
        "R4": (2.5, -4.0, 0),
        "R5": (-8.5, 1.5, 90),
        "R6": (-8.5, -1.5, 90),
    },
    # MX power: pins face +X (toward board/power)
    "jpwr_back": {
        "J2": (0.0, 0.0, 90),
    },
    # MX signal: pins face −X; AHCT+RC on pin side
    "jsig_back": {
        "J3": (0.0, 0.0, -90),
        "U1": (-6.5, 0.0, 90),
        "R3": (-6.5, -3.5, 0),
        "C2": (-6.5, 3.5, 0),
    },
}

# Pile origin on the canvas (outside Edge.Cuts)
_PILE_ORIGIN: dict[str, tuple[float, float, str]] = {
    "usb_front": (-18.0, -38.0, "F"),
    "ui_front": (18.0, -38.0, "F"),
    "jpwr_back": (-40.0, 40.0, "B"),
    "power_back": (0.0, 45.0, "B"),
    "jsig_back": (40.0, 40.0, "B"),
}

PLACEMENT: dict[str, tuple[float, float, float, str]] = {}
for _pile, _locals in _PILE_LOCAL.items():
    _ox, _oy, _side = _PILE_ORIGIN[_pile]
    for _ref, (_dx, _dy, _rot) in _locals.items():
        PLACEMENT[_ref] = (_ox + _dx, _oy + _dy, _rot, _side)

# Functional piles + whole-side groups (drag all front / all back)
GROUPS: dict[str, list[str]] = {
    "side_front": ["J1", "U2", "R1", "R2", "SW1", "D1", "C1", "LED1"],
    "side_back": [
        "U3",
        "L1",
        "C4",
        "R7",
        "C5",
        "C6",
        "C7",
        "C3",
        "R5",
        "R6",
        "R4",
        "J2",
        "J3",
        "U1",
        "R3",
        "C2",
    ],
    "usb_front": ["J1", "U2", "R1", "R2"],
    "ui_front": ["SW1", "D1", "C1", "LED1"],
    "power_back": ["U3", "L1", "C4", "R7", "C5", "C6", "C7", "C3", "R5", "R6", "R4"],
    "jpwr_back": ["J2"],
    "jsig_back": ["J3", "U1", "R3", "C2"],
}


# ===== 分区：私有成员 =====
def _strip_top_level(text: str, heads: list[str]) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "(":
            j = i + 1
            while j < n and text[j] not in " \n\t()":
                j += 1
            tok = text[i + 1 : j]
            if tok in heads:
                depth = 0
                k = i
                while k < n:
                    if text[k] == "(":
                        depth += 1
                    elif text[k] == ")":
                        depth -= 1
                        if depth == 0:
                            k += 1
                            break
                    k += 1
                p = len(out)
                while p > 0 and out[p - 1] in " \t":
                    p -= 1
                if p > 0 and out[p - 1] == "\n":
                    p -= 1
                out = out[:p]
                i = k
                continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _apply_placement(text: str) -> tuple[str, dict[str, str]]:
    text = text.replace('(property "Reference" "REF**"', '(property "Reference" "SW1"', 1)
    parts = re.split(r"(?=\n\s*\(footprint )", text)
    out: list[str] = []
    uuid_by_ref: dict[str, str] = {}
    for part in parts:
        if not part.lstrip().startswith("(footprint"):
            out.append(part)
            continue
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', part)
        if not ref_m or ref_m.group(1) not in PLACEMENT:
            out.append(part)
            continue
        ref = ref_m.group(1)
        x, y, rot, side = PLACEMENT[ref]

        def repl_at(_m, x=x, y=y, rot=rot):
            if abs(rot) % 360 == 0:
                return f"(at {x:.4f} {y:.4f}"
            return f"(at {x:.4f} {y:.4f} {rot:g}"

        part, _ = re.subn(
            r"\(at [-\d.]+ [-\d.]+(?: [-\d.]+)?",
            repl_at,
            part,
            count=1,
        )
        part = re.sub(
            r'(\(footprint "[^"]+"\s*\n\t\t\(layer ")(F|B)(\.Cu"\))',
            rf"\g<1>{side}\3",
            part,
            count=1,
        )
        um = re.search(r'\(uuid "([^"]+)"\)', part)
        if um:
            uuid_by_ref[ref] = um.group(1)
        out.append(part)
    return "".join(out), uuid_by_ref


def _write_groups(body: str, uuid_by_ref: dict[str, str]) -> str:
    body = body.rstrip()
    if not body.endswith(")"):
        raise RuntimeError("bad pcb footer")
    body = body[:-1].rstrip() + "\n"
    for gname, refs in GROUPS.items():
        mems = " ".join(f'"{uuid_by_ref[r]}"' for r in refs if r in uuid_by_ref)
        body += (
            f'\t(group "{gname}"\n'
            f'\t\t(uuid "{uuid.uuid4()}")\n'
            f"\t\t(members {mems}\n"
            f"\t\t)\n"
            f"\t)\n"
        )
    return body + ")\n"


def _render(text: str) -> list[tuple[str, float]]:
    em = re.search(
        r'\(gr_poly\s*\(pts([\s\S]*?)\)\s*\(stroke[\s\S]*?\(layer "Edge\.Cuts"\)',
        text,
    )
    edge = [
        (float(a), float(b))
        for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", em.group(1))
    ]
    fps = []
    for ref, (x, y, _r, side) in PLACEMENT.items():
        fps.append({"ref": ref, "x": x, "y": y, "side": side})
    net = [
        ("J1", "U2"),
        ("J1", "R1"),
        ("J1", "R2"),
        ("D1", "C1"),
        ("D1", "LED1"),
        ("SW1", "D1"),
        ("U3", "L1"),
        ("U3", "C4"),
        ("U3", "C6"),
        ("U3", "C3"),
        ("U3", "R5"),
        ("U3", "R6"),
        ("U3", "R4"),
        ("C4", "R7"),
        ("R7", "C5"),
        ("C6", "C7"),
        ("L1", "C3"),
        ("J3", "U1"),
        ("U1", "R3"),
        ("U1", "C2"),
    ]
    by = {f["ref"]: f for f in fps}
    wires = [
        (f"{a}-{b}", (by[a]["x"], by[a]["y"]), (by[b]["x"], by[b]["y"]))
        for a, b in net
    ]
    allx = [p[0] for p in edge] + [f["x"] for f in fps]
    ally = [p[1] for p in edge] + [f["y"] for f in fps]
    pad = 10
    minx, maxx = min(allx) - pad, max(allx) + pad
    miny, maxy = min(ally) - pad, max(ally) + pad
    w, h = 1600, 1200
    sx = lambda x: (x - minx) / (maxx - minx) * (w - 40) + 20
    sy = lambda y: (maxy - y) / (maxy - miny) * (h - 90) + 55
    img = Image.new("RGB", (w, h), (248, 250, 252))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 18
        )
        font_s = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 13
        )
        font_t = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 24
        )
    except Exception:
        font = font_s = font_t = ImageFont.load_default()
    d.text(
        (20, 12),
        "pcb-tail: front=south / back=north — recommended relative piles",
        fill=(15, 23, 42),
        font=font_t,
    )
    d.polygon([(sx(x), sy(y)) for x, y in edge], outline=(100, 116, 139), fill=(226, 232, 240))
    for _n, p, q in wires:
        d.line([sx(p[0]), sy(p[1]), sx(q[0]), sy(q[1])], fill=(148, 163, 184), width=1)
    colors = {
        "side_front": (59, 130, 246),
        "side_back": (239, 68, 68),
        "usb_front": (37, 99, 235),
        "ui_front": (5, 150, 105),
        "power_back": (220, 38, 38),
        "jpwr_back": (217, 119, 6),
        "jsig_back": (147, 51, 234),
    }
    # Draw side envelopes first (wide), then functional piles
    for gname, refs in GROUPS.items():
        if gname.startswith("side_"):
            continue
        col = colors[gname]
        xs = [PLACEMENT[r][0] for r in refs]
        ys = [PLACEMENT[r][1] for r in refs]
        rect = [sx(min(xs) - 4), sy(max(ys) + 4), sx(max(xs) + 4), sy(min(ys) - 4)]
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.rectangle(rect, outline=col + (255,), width=2, fill=col + (35,))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        d = ImageDraw.Draw(img)
        d.text((rect[0] + 4, rect[1] + 2), gname, fill=col, font=font_s)
    for gname in ("side_front", "side_back"):
        refs = GROUPS[gname]
        col = colors[gname]
        xs = [PLACEMENT[r][0] for r in refs]
        ys = [PLACEMENT[r][1] for r in refs]
        rect = [sx(min(xs) - 8), sy(max(ys) + 8), sx(max(xs) + 8), sy(min(ys) - 8)]
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.rectangle(rect, outline=col + (255,), width=3)
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        d = ImageDraw.Draw(img)
        d.text((rect[0] + 6, rect[1] + 4), gname, fill=col, font=font)
    for f in fps:
        col = (30, 64, 175) if f["side"] == "F" else (153, 27, 27)
        d.rectangle(
            [sx(f["x"] - 1.2), sy(f["y"] + 1.2), sx(f["x"] + 1.2), sy(f["y"] - 1.2)],
            outline=col,
            width=2,
            fill=(255, 255, 255),
        )
        d.text((sx(f["x"]) - 12, sy(f["y"]) - 7), f["ref"], fill=col, font=font_s)
    lens = sorted(
        ((n, math.hypot(p[0] - q[0], p[1] - q[1])) for n, p, q in wires),
        key=lambda x: -x[1],
    )
    d.text(
        (20, h - 58),
        "intra: " + ", ".join(f"{n}={d2:.1f}" for n, d2 in lens[:8]),
        fill=(51, 65, 85),
        font=font_s,
    )
    d.text(
        (20, h - 34),
        "Drag side_front / side_back or a pile → nudge spacing → route",
        fill=(71, 85, 105),
        font=font_s,
    )
    img.save(PREVIEW, "PNG", optimize=True)
    return lens


# ===== 分区：业务逻辑 =====
def _check_usb_front_clearance() -> None:
    """Fail fast if usb_front satellites sit inside J1 courtyard."""
    jx, jy, _, _ = PLACEMENT["J1"]
    # Land-pattern courtyard ~ pads+slots (+clearance), centered on J1
    half_w, half_d, gap = 5.1, 2.6, 1.0
    for ref in ("U2", "R1", "R2"):
        x, y, _, _ = PLACEMENT[ref]
        if abs(x - jx) <= half_w + gap and abs(y - jy) <= half_d + gap:
            raise RuntimeError(
                f"{ref} at ({x},{y}) overlaps J1 courtyard — "
                "cluster means nearby, not stacked pads"
            )
    print("usb_front clearance OK")


def _check_usblc6_facing() -> None:
    """Fail fast if U2 conn-side pins are not a row facing J1."""
    _jx, jy, _, _ = PLACEMENT["J1"]
    ux, uy, rot, _ = PLACEMENT["U2"]
    # SOT-23-6 local pads 1/2/3
    local = {1: (-1.137, -0.950), 2: (-1.137, 0.0), 3: (-1.137, 0.950)}
    a = math.radians(rot)
    c, s = math.cos(a), math.sin(a)

    def world(px: float, py: float) -> tuple[float, float]:
        return ux + c * px - s * py, uy + s * px + c * py

    pts = {n: world(*xy) for n, xy in local.items()}
    ys = [pts[n][1] for n in (1, 2, 3)]
    xs = [pts[n][0] for n in (1, 2, 3)]
    row_span_x = max(xs) - min(xs)
    row_span_y = max(ys) - min(ys)
    toward_j1 = (jy - uy)  # >0 means J1 is +Y of U2
    edge_y = sum(ys) / 3.0
    facing_plus_y = edge_y > uy
    if row_span_x < 1.5 or row_span_y > 0.4:
        raise RuntimeError(
            f"U2 rot={rot}: pins 1/2/3 not a horizontal row "
            f"(span_x={row_span_x:.2f}, span_y={row_span_y:.2f})"
        )
    if toward_j1 > 0 and not facing_plus_y:
        raise RuntimeError(f"U2 rot={rot}: pins 1/2/3 face away from J1 (+Y)")
    if toward_j1 < 0 and facing_plus_y:
        raise RuntimeError(f"U2 rot={rot}: pins 1/2/3 face away from J1 (−Y)")
    order = sorted((1, 2, 3), key=lambda n: pts[n][0])
    print(f"U2 facing OK: rot={rot} pins L→R {order} toward J1")


# ===== 分区：公开 API =====
def main() -> int:
    _check_usb_front_clearance()
    _check_usblc6_facing()
    raw = PCB.read_text(encoding="utf-8")
    raw = _strip_top_level(raw, ["segment", "via", "arc", "group"])
    body, uuid_by_ref = _apply_placement(raw)
    body = _write_groups(body, uuid_by_ref)
    PCB.write_text(body, encoding="utf-8")
    lens = _render(body)
    print(f"saved {PCB}")
    print(f"preview {PREVIEW}")
    for g, refs in GROUPS.items():
        print(f"  {g}: {refs}")
    print("longest intra-group links:", ", ".join(f"{n}={d:.1f}" for n, d in lens[:5]))
    return 0


# ===== 分区：方法/工具 =====
if __name__ == "__main__":
    raise SystemExit(main())
