#!/usr/bin/env python3
"""Deliverable exploded clusters for pcb-tail (sexpr; no pcbnew required).

After open in KiCad: select each group → shrink spacing / drag into Edge.Cuts → route.

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

# ref -> (x, y, rot_deg, side)  — board-outside parking, pin-aware
PLACEMENT: dict[str, tuple[float, float, float, str]] = {
    # usb_front
    "J1": (-40.0, -40.0, 0, "F"),
    "U2": (-40.0, -45.0, 180, "F"),
    "R1": (-45.5, -40.8, 90, "F"),
    "R2": (-34.5, -39.2, 90, "F"),
    # ui_front
    "SW1": (40.0, -35.0, 0, "F"),
    "D1": (40.0, -42.0, 0, "F"),
    "C1": (44.0, -42.0, 0, "F"),
    "LED1": (35.5, -42.0, 90, "F"),
    # power_back (U3-centric)
    "U3": (0.0, 48.0, 0, "B"),
    "L1": (7.0, 48.0, 90, "B"),
    "C4": (-5.8, 50.2, 90, "B"),
    "R7": (-5.8, 47.5, 0, "B"),
    "C5": (-5.8, 44.8, 90, "B"),
    "C6": (7.0, 51.5, 0, "B"),
    "C7": (10.2, 48.0, 0, "B"),
    "C3": (7.0, 44.5, 0, "B"),
    "R5": (-8.8, 49.2, 90, "B"),
    "R6": (-8.8, 46.6, 90, "B"),
    "R4": (3.0, 44.5, 0, "B"),
    # harness
    "J2": (-50.0, 30.0, 90, "B"),
    "J3": (50.0, 30.0, -90, "B"),
    "U1": (43.5, 30.0, 90, "B"),
    "R3": (43.5, 26.5, 0, "B"),
    "C2": (43.5, 33.5, 0, "B"),
}

GROUPS: dict[str, list[str]] = {
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
        "pcb-tail deliverable clusters — shrink / drag / route",
        fill=(15, 23, 42),
        font=font_t,
    )
    d.polygon([(sx(x), sy(y)) for x, y in edge], outline=(100, 116, 139), fill=(226, 232, 240))
    for _n, p, q in wires:
        d.line([sx(p[0]), sy(p[1]), sx(q[0]), sy(q[1])], fill=(148, 163, 184), width=1)
    colors = {
        "usb_front": (37, 99, 235),
        "ui_front": (5, 150, 105),
        "power_back": (220, 38, 38),
        "jpwr_back": (217, 119, 6),
        "jsig_back": (147, 51, 234),
    }
    for gname, refs in GROUPS.items():
        col = colors[gname]
        xs = [PLACEMENT[r][0] for r in refs]
        ys = [PLACEMENT[r][1] for r in refs]
        rect = [sx(min(xs) - 6), sy(max(ys) + 6), sx(max(xs) + 6), sy(min(ys) - 6)]
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.rectangle(rect, outline=col + (255,), width=3, fill=col + (40,))
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
        "Ready: shrink groups -> drag into Edge.Cuts -> nudge -> route",
        fill=(71, 85, 105),
        font=font_s,
    )
    img.save(PREVIEW, "PNG", optimize=True)
    return lens


# ===== 分区：公开 API =====
def main() -> int:
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
