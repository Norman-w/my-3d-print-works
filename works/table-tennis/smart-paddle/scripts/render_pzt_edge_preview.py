#!/usr/bin/env python3
"""Render four PZT dock close-ups from the live KiCad Edge.Cuts geometry."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path

import pcbnew
from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "pcb/layouts/default/default.kicad_pcb"
CONTRACT = ROOT / "docs/mechanical-handoff/mechanical-contract.scad"
OUTPUT = ROOT / "docs/mechanical-handoff/pzt-pad-reliefs.png"

PZT_PREFIXES = {
    "pzt_tl": "PZT TOP LEFT",
    "pzt_tr": "PZT TOP RIGHT",
    "pzt_bl": "PZT BOTTOM LEFT",
    "pzt_br": "PZT BOTTOM RIGHT",
}

BACKGROUND = (250, 249, 230)
BOARD_GREEN = (24, 91, 57)
EDGE_DARK = (8, 55, 34)
COPPER_GOLD = (229, 161, 25)
RELIEF_ORANGE = (244, 92, 25)
TEXT = (28, 35, 31)


def _font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _field(footprint, name: str) -> str:
    return footprint.GetFieldByName(name).GetText() if footprint.HasFieldByName(name) else ""


def _mm(point) -> tuple[float, float]:
    return point.x / 1e6, point.y / 1e6


def _point_segment_distance(point, start, end) -> float:
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.dist(point, start)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _outer_loop(board) -> list[tuple[float, float]]:
    adjacency: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for drawing in board.GetDrawings():
        if drawing.GetLayer() != pcbnew.Edge_Cuts or drawing.GetShape() != pcbnew.SHAPE_T_SEGMENT:
            continue
        start = (drawing.GetStart().x, drawing.GetStart().y)
        end = (drawing.GetEnd().x, drawing.GetEnd().y)
        adjacency[start].append(end)
        adjacency[end].append(start)

    components: list[set[tuple[int, int]]] = []
    unvisited = set(adjacency)
    while unvisited:
        seed = next(iter(unvisited))
        stack = [seed]
        component = {seed}
        unvisited.remove(seed)
        while stack:
            point = stack.pop()
            for neighbor in adjacency[point]:
                if neighbor in unvisited:
                    unvisited.remove(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
        components.append(component)
    if not components:
        raise RuntimeError("PCB has no segmented Edge.Cuts outline")
    outer = max(components, key=len)
    if any(len(adjacency[point]) != 2 for point in outer):
        raise RuntimeError("outer Edge.Cuts loop is not closed and degree-two")

    start = min(outer)
    loop = [start]
    previous = None
    current = start
    while True:
        candidates = [point for point in adjacency[current] if point != previous]
        following = candidates[0]
        if following == start:
            break
        loop.append(following)
        previous, current = current, following
        if len(loop) > len(outer):
            raise RuntimeError("failed to order outer Edge.Cuts loop")
    if len(loop) != len(outer):
        raise RuntimeError("ordered Edge.Cuts loop is incomplete")
    return [(x / 1e6, y / 1e6) for x, y in loop]


def _scalar(text: str, name: str) -> float:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*([-+0-9.]+)\s*;", text)
    if not match:
        raise RuntimeError(f"missing {name} in mechanical contract")
    return float(match.group(1))


def _dashed_circle(draw, box, color, width: int) -> None:
    for start in range(0, 360, 24):
        draw.arc(box, start=start, end=start + 14, fill=color, width=width)


def main() -> int:
    board = pcbnew.LoadBoard(str(BOARD))
    outer = _outer_loop(board)
    contract = CONTRACT.read_text(encoding="utf-8")
    relief_d = _scalar(contract, "pzt_solder_relief_d")

    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for footprint in board.GetFootprints():
        address = _field(footprint, "atopile_address")
        prefix = address.split(".", 1)[0]
        if prefix not in PZT_PREFIXES or not address.endswith((".pzt_gnd_pad", ".pzt_signal_pad")):
            continue
        pads = [pad for pad in footprint.Pads() if pad.GetNumber() == "1"]
        if len(pads) != 1:
            raise RuntimeError(f"{address} does not have exactly one pad 1")
        pad = pads[0]
        center = _mm(pad.GetPosition())
        edge_offset = min(
            _point_segment_distance(center, outer[index], outer[(index + 1) % len(outer)])
            for index in range(len(outer))
        )
        groups[prefix].append(
            {
                "address": address,
                "center": center,
                "land": pad.GetSize().x / 1e6,
                "drill": pad.GetDrillSize().x / 1e6,
                "edge_offset": edge_offset,
            }
        )
    if set(groups) != set(PZT_PREFIXES) or any(len(pads) != 2 for pads in groups.values()):
        raise RuntimeError("live PCB does not contain four two-pad PZT docks")

    canvas = Image.new("RGB", (1800, 1200), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    title_font = _font(38, bold=True)
    body_font = _font(24)
    small_font = _font(20)
    draw.text((60, 30), "LIVE KICAD PZT EDGE-CUT AUDIT", font=title_font, fill=TEXT)
    draw.text(
        (60, 82),
        "Green = retained PCB   Gold = retained copper   Orange dashed = shell relief Ø3.5 mm",
        font=body_font,
        fill=TEXT,
    )

    panel_w, panel_h = 820, 490
    panel_positions = {
        "pzt_tl": (60, 145),
        "pzt_tr": (920, 145),
        "pzt_bl": (60, 675),
        "pzt_br": (920, 675),
    }
    world_w, world_h = 16.0, 11.5

    for prefix, origin in panel_positions.items():
        ox, oy = origin
        panel = Image.new("RGB", (panel_w, panel_h), BACKGROUND)
        panel_draw = ImageDraw.Draw(panel)
        pads = groups[prefix]
        cx = sum(pad["center"][0] for pad in pads) / 2
        cy = sum(pad["center"][1] for pad in pads) / 2
        scale = min((panel_w - 60) / world_w, (panel_h - 90) / world_h)

        def project(point):
            x, y = point
            return (
                panel_w / 2 + (x - cx) * scale,
                panel_h / 2 + 25 + (y - cy) * scale,
            )

        board_mask = Image.new("L", (panel_w, panel_h), 0)
        mask_draw = ImageDraw.Draw(board_mask)
        mask_draw.polygon([project(point) for point in outer], fill=255)
        panel.paste(BOARD_GREEN, mask=board_mask)

        for pad in pads:
            px, py = project(pad["center"])
            land_r = pad["land"] * scale / 2
            drill_r = pad["drill"] * scale / 2
            relief_r = relief_d * scale / 2
            pad_mask = Image.new("L", (panel_w, panel_h), 0)
            ImageDraw.Draw(pad_mask).ellipse(
                (px - land_r, py - land_r, px + land_r, py + land_r), fill=255
            )
            retained = ImageChops.multiply(board_mask, pad_mask)
            panel.paste(COPPER_GOLD, mask=retained)
            panel_draw.ellipse(
                (px - drill_r, py - drill_r, px + drill_r, py + drill_r), fill=BACKGROUND
            )
            _dashed_circle(
                panel_draw,
                (px - relief_r, py - relief_r, px + relief_r, py + relief_r),
                RELIEF_ORANGE,
                4,
            )
            role = "GND" if "gnd" in pad["address"] else "SIGNAL"
            label = f"{role}  edge↔center {pad['edge_offset']:.3f} mm"
            label_box = panel_draw.textbbox((0, 0), label, font=small_font)
            label_w = label_box[2] - label_box[0]
            label_h = label_box[3] - label_box[1]
            tx = px + 18 if px < panel_w / 2 else px - label_w - 18
            ty = py - label_h / 2
            panel_draw.rounded_rectangle(
                (tx - 7, ty - 5, tx + label_w + 7, ty + label_h + 5),
                radius=7,
                fill=BACKGROUND,
            )
            panel_draw.text((tx, ty), label, font=small_font, fill=TEXT)

        edge_points = [project(point) for point in outer]
        panel_draw.line(edge_points + [edge_points[0]], fill=EDGE_DARK, width=4, joint="curve")
        panel_draw.rounded_rectangle((1, 1, panel_w - 2, panel_h - 2), radius=18, outline=(104, 116, 105), width=3)
        title = PZT_PREFIXES[prefix]
        title_box = panel_draw.textbbox((0, 0), title, font=_font(26, bold=True))
        panel_draw.rounded_rectangle(
            (18, 12, title_box[2] + 34, title_box[3] + 25), radius=9, fill=BACKGROUND
        )
        panel_draw.text((24, 18), title, font=_font(26, bold=True), fill=TEXT)
        canvas.paste(panel, (ox, oy))

    canvas.save(OUTPUT)
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
