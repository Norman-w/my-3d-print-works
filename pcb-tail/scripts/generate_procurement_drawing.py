#!/usr/bin/env python3
"""Generate the current SmartPaddle M5 tail-board procurement drawing.

The drawing is intentionally based on the checked-in KiCad land patterns and
the current pcb-tail/main.ato values.  It is a procurement/fit reference, not
a substitute for the connector vendor's final datasheet approval.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "output" / "pdf"
OUT_PDF = OUT_DIR / "smartpaddle_m5_tail_procurement_drawing.pdf"
BOARD_IMAGE = ROOT / "pcb-tail" / "layouts" / "default" / "export-preview" / "board-3d-top.png"

PAGE_W, PAGE_H = landscape(A4)
MARGIN = 30

NAVY = colors.HexColor("#15324b")
BLUE = colors.HexColor("#1f6f8b")
TEAL = colors.HexColor("#2f9c95")
ORANGE = colors.HexColor("#d27c2c")
RED = colors.HexColor("#b7463b")
INK = colors.HexColor("#202a33")
MUTED = colors.HexColor("#60717e")
GRID = colors.HexColor("#c8d2d9")
PALE = colors.HexColor("#f3f7f9")
PALE_BLUE = colors.HexColor("#eaf4f7")
PALE_ORANGE = colors.HexColor("#fff4e6")
COPPER = colors.HexColor("#c88635")
MASK = colors.HexColor("#315b49")
BODY = colors.HexColor("#4c5360")


def register_fonts() -> tuple[str, str]:
    candidates = [
        ("/Library/Fonts/Arial Unicode.ttf", "ArialUnicode"),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "ArialUnicode"),
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", "HiraginoSansGB"),
    ]
    for path, name in candidates:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name, name
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


def txt(c: canvas.Canvas, x: float, y: float, value: str, size: float = 8.5,
        color=INK, bold: bool = False, align: str = "left") -> None:
    c.setFont(FONT_BOLD if bold else FONT, size)
    c.setFillColor(color)
    if align == "right":
        c.drawRightString(x, y, value)
    elif align == "center":
        c.drawCentredString(x, y, value)
    else:
        c.drawString(x, y, value)


def text_width(value: str, size: float, bold: bool = False) -> float:
    return pdfmetrics.stringWidth(value, FONT_BOLD if bold else FONT, size)


def wrap(value: str, width: float, size: float = 8.2, bold: bool = False) -> list[str]:
    lines: list[str] = []
    for paragraph in value.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        tokens = re.findall(r"[A-Za-z0-9_.+/-]+|[\u4e00-\u9fff]|[^\s]|\s+", paragraph)
        for token in tokens:
            candidate = current + token
            if current and text_width(candidate, size, bold) > width:
                lines.append(current.rstrip())
                current = token.lstrip()
            else:
                current = candidate
        if current:
            lines.append(current.rstrip())
    return lines


def text_block(c: canvas.Canvas, x: float, y: float, value: str, width: float,
               size: float = 8.2, leading: float | None = None,
               color=INK, bold: bool = False, max_lines: int | None = None) -> float:
    leading = leading or size * 1.35
    lines = wrap(value, width, size, bold)
    if max_lines is not None:
        lines = lines[:max_lines]
    for index, line in enumerate(lines):
        txt(c, x, y - index * leading, line, size, color, bold)
    return y - len(lines) * leading


def round_rect(c: canvas.Canvas, x: float, y: float, w: float, h: float,
               fill=colors.white, stroke=GRID, radius: float = 8, width: float = 0.8) -> None:
    c.setLineWidth(width)
    c.setStrokeColor(stroke)
    c.setFillColor(fill)
    c.roundRect(x, y, w, h, radius, stroke=1, fill=1)


def header(c: canvas.Canvas, title: str, subtitle: str, page: int) -> None:
    c.setFillColor(NAVY)
    c.rect(0, PAGE_H - 54, PAGE_W, 54, stroke=0, fill=1)
    txt(c, MARGIN, PAGE_H - 25, title, 16, colors.white, True)
    txt(c, MARGIN, PAGE_H - 42, subtitle, 8.2, colors.HexColor("#d9edf4"))
    txt(c, PAGE_W - MARGIN, PAGE_H - 25, "M5-TAIL-BARE", 8.5, colors.white, True, "right")
    txt(c, PAGE_W - MARGIN, PAGE_H - 42, f"采购参考图 / 第 {page} 页", 8.0, colors.HexColor("#d9edf4"), align="right")


def footer(c: canvas.Canvas, page: int) -> None:
    c.setStrokeColor(GRID)
    c.setLineWidth(0.5)
    c.line(MARGIN, 24, PAGE_W - MARGIN, 24)
    txt(c, MARGIN, 12, "SmartPaddle pcb-tail | units: mm | top-view land pattern unless noted", 7.2, MUTED)
    txt(c, PAGE_W - MARGIN, 12, f"Page {page}", 7.2, MUTED, align="right")


def section_label(c: canvas.Canvas, x: float, y: float, label: str, color=BLUE) -> None:
    c.setFillColor(color)
    c.roundRect(x, y - 2, 5, 12, 2, stroke=0, fill=1)
    txt(c, x + 12, y, label, 10, NAVY, True)


def pill(c: canvas.Canvas, x: float, y: float, label: str, fill=PALE_BLUE, color=BLUE) -> None:
    w = text_width(label, 7.5, True) + 14
    c.setFillColor(fill)
    c.setStrokeColor(fill)
    c.roundRect(x, y, w, 16, 8, stroke=0, fill=1)
    txt(c, x + w / 2, y + 4.3, label, 7.5, color, True, "center")


def dim_h(c: canvas.Canvas, x1: float, x2: float, y: float, label: str,
          color=ORANGE, ext_y1: float | None = None, ext_y2: float | None = None) -> None:
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(0.65)
    c.line(x1, y, x2, y)
    c.line(x1, y - 3, x1, y + 3)
    c.line(x2, y - 3, x2, y + 3)
    c.line(x1, y, x1 + 4, y + 2)
    c.line(x1, y, x1 + 4, y - 2)
    c.line(x2, y, x2 - 4, y + 2)
    c.line(x2, y, x2 - 4, y - 2)
    if ext_y1 is not None:
        c.line(x1, ext_y1, x1, y)
    if ext_y2 is not None:
        c.line(x2, ext_y2, x2, y)
    txt(c, (x1 + x2) / 2, y + 4, label, 7.2, color, True, "center")


def dim_v(c: canvas.Canvas, x: float, y1: float, y2: float, label: str,
          color=ORANGE, ext_x1: float | None = None, ext_x2: float | None = None) -> None:
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(0.65)
    c.line(x, y1, x, y2)
    c.line(x - 3, y1, x + 3, y1)
    c.line(x - 3, y2, x + 3, y2)
    c.line(x, y1, x + 2, y1 + 4)
    c.line(x, y1, x - 2, y1 + 4)
    c.line(x, y2, x + 2, y2 - 4)
    c.line(x, y2, x - 2, y2 - 4)
    if ext_x1 is not None:
        c.line(ext_x1, y1, x, y1)
    if ext_x2 is not None:
        c.line(ext_x2, y2, x, y2)
    c.saveState()
    c.translate(x - 4, (y1 + y2) / 2)
    c.rotate(90)
    txt(c, 0, 0, label, 7.2, color, True, "center")
    c.restoreState()


def pad(c: canvas.Canvas, x: float, y: float, w: float, h: float,
        fill=COPPER, stroke=colors.white, radius: float = 1.5) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.45)
    c.roundRect(x - w / 2, y - h / 2, w, h, min(radius, w / 2), stroke=1, fill=1)


def draw_typec(c: canvas.Canvas, cx: float, cy: float, scale: float = 22) -> None:
    def xy(x: float, y: float) -> tuple[float, float]:
        return cx + x * scale, cy + y * scale

    # courtyard / body guide
    c.setStrokeColor(GRID)
    c.setDash(2, 2)
    c.rect(cx - 5.125 * scale, cy - 2.31 * scale, 10.25 * scale, 4.62 * scale, stroke=1, fill=0)
    c.setDash()
    c.setStrokeColor(BODY)
    c.setLineWidth(1)
    c.rect(cx - 4.875 * scale, cy - 2.06 * scale, 9.75 * scale, 4.12 * scale, stroke=1, fill=0)
    for y in (-1.1, 1.1):
        for i, x in enumerate([-2.73, -1.95, -1.17, -0.39, 0.39, 1.17, 1.95, 2.73]):
            px, py = xy(x, y)
            pad(c, px, py, 0.32 * scale, 1.72 * scale, fill=COPPER, radius=1.3)
            if i in (0, 7):
                c.setFillColor(colors.white)
                c.circle(px, py + (0.53 if y < 0 else -0.53) * scale, 0.07 * scale, stroke=0, fill=1)
    for x in (-4.325, 4.325):
        px, py = xy(x, 0)
        c.setFillColor(COPPER)
        c.setStrokeColor(MASK)
        c.ellipse(px - 0.45 * scale, py - 0.8 * scale, px + 0.45 * scale, py + 0.8 * scale, stroke=1, fill=1)
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.white)
        c.ellipse(px - 0.25 * scale, py - 0.6 * scale, px + 0.25 * scale, py + 0.6 * scale, stroke=1, fill=0)
    dim_h(c, cx - 2.73 * scale, cx - 1.95 * scale, cy - 2.95 * scale, "P0.78", ext_y1=cy - 1.96 * scale, ext_y2=cy - 1.96 * scale)
    dim_v(c, cx + 3.7 * scale, cy - 1.96 * scale, cy + 1.96 * scale, "2 x 1.72 pad", ext_x1=cx + 2.73 * scale, ext_x2=cx + 2.73 * scale)
    dim_h(c, cx - 4.325 * scale, cx + 4.325 * scale, cy + 3.0 * scale, "slot C-C 8.65", ext_y1=cy + 0.8 * scale, ext_y2=cy + 0.8 * scale)
    txt(c, cx, cy - 3.55 * scale, "16P vertical SMT / 5.8 mm body height", 7.7, NAVY, True, "center")


def draw_molex(c: canvas.Canvas, cx: float, cy: float, scale: float = 15) -> None:
    # footprint top view; pads at y=-1.25, MP pads at y=1.5
    c.setStrokeColor(GRID)
    c.setDash(2, 2)
    c.rect(cx - 5.98 * scale, cy - 1.6 * scale, 11.96 * scale, 5.1 * scale, stroke=1, fill=0)
    c.setDash()
    c.setStrokeColor(BODY)
    c.setLineWidth(1)
    c.rect(cx - 2.78 * scale, cy - 2.4 * scale, 5.56 * scale, 5.0 * scale, stroke=1, fill=0)
    for i, x in enumerate((-1.875, -0.625, 0.625, 1.875), 1):
        pad(c, cx + x * scale, cy - 1.25 * scale, 0.8 * scale, 1.3 * scale, fill=COPPER, radius=1.4)
        txt(c, cx + x * scale, cy - 1.25 * scale - 2.8, str(i), 5.8, colors.white, True, "center")
    for x in (-4.425, 4.425):
        pad(c, cx + x * scale, cy + 1.5 * scale, 2.1 * scale, 3 * scale, fill=COPPER, radius=2)
    dim_h(c, cx - 1.875 * scale, cx - 0.625 * scale, cy - 3.25 * scale, "P1.25", ext_y1=cy - 1.9 * scale, ext_y2=cy - 1.9 * scale)
    dim_h(c, cx - 4.425 * scale, cx + 4.425 * scale, cy + 3.75 * scale, "MP C-C 8.85", ext_y1=cy + 3.0 * scale, ext_y2=cy + 3.0 * scale)
    txt(c, cx, cy - 3.9 * scale, "53398-0471 / 1x04 vertical SMT", 7.7, NAVY, True, "center")


def draw_switch(c: canvas.Canvas, cx: float, cy: float, scale: float = 17) -> None:
    c.setStrokeColor(GRID)
    c.setDash(2, 2)
    c.rect(cx - 3.4 * scale, cy - 2.7 * scale, 6.8 * scale, 5.4 * scale, stroke=1, fill=0)
    c.setDash()
    c.setStrokeColor(BODY)
    c.rect(cx - 2.25 * scale, cy - 2.25 * scale, 4.5 * scale, 4.5 * scale, stroke=1, fill=0)
    c.setStrokeColor(MUTED)
    c.circle(cx, cy, 0.6 * scale, stroke=1, fill=0)
    for x, y in ((-2.75, -1.7), (2.75, -1.7), (-2.75, 1.7), (2.75, 1.7)):
        c.setFillColor(COPPER)
        c.setStrokeColor(MASK)
        c.circle(cx + x * scale, cy + y * scale, 0.8 * scale, stroke=1, fill=1)
        c.setFillColor(colors.white)
        c.circle(cx + x * scale, cy + y * scale, 0.45 * scale, stroke=0, fill=1)
    dim_h(c, cx - 2.75 * scale, cx + 2.75 * scale, cy - 3.35 * scale, "5.50 hole C-C", ext_y1=cy - 1.7 * scale, ext_y2=cy - 1.7 * scale)
    dim_v(c, cx + 3.8 * scale, cy - 1.7 * scale, cy + 1.7 * scale, "3.40", ext_x1=cx + 2.75 * scale, ext_x2=cx + 2.75 * scale)
    txt(c, cx, cy - 4.0 * scale, "4.5 x 4.5 mm THT SPST", 7.7, NAVY, True, "center")


def draw_sot23(c: canvas.Canvas, cx: float, cy: float, pins: int, scale: float = 18) -> None:
    c.setStrokeColor(GRID)
    c.setDash(2, 2)
    c.rect(cx - 2.05 * scale, cy - 1.7 * scale, 4.1 * scale, 3.4 * scale, stroke=1, fill=0)
    c.setDash()
    c.setStrokeColor(BODY)
    c.setLineWidth(1)
    c.rect(cx - 0.8 * scale, cy - 1.45 * scale, 1.6 * scale, 2.9 * scale, stroke=1, fill=0)
    c.setFillColor(BODY)
    c.circle(cx - 0.45 * scale, cy - 1.2 * scale, 0.13 * scale, stroke=0, fill=1)
    ys = (-0.95, 0, 0.95)
    for i, y in enumerate(ys, 1):
        pad(c, cx - 1.1375 * scale, cy + y * scale, 1.325 * scale, 0.6 * scale, fill=COPPER, radius=2)
        if pins == 6:
            pad(c, cx + 1.1375 * scale, cy + y * scale, 1.325 * scale, 0.6 * scale, fill=COPPER, radius=2)
    if pins == 5:
        # SOT-23-5 has two pads on the right side at y +/- 0.95 and no center pad.
        for y in (-0.95, 0.95):
            pad(c, cx + 1.1375 * scale, cy + y * scale, 1.325 * scale, 0.6 * scale, fill=COPPER, radius=2)
    dim_v(c, cx + 2.45 * scale, cy - 0.95 * scale, cy, "P0.95", ext_x1=cx + 1.14 * scale, ext_x2=cx + 1.14 * scale)
    txt(c, cx, cy - 2.15 * scale, f"SOT-23-{pins} / 0.95 pitch", 7.7, NAVY, True, "center")


def draw_ip5305(c: canvas.Canvas, cx: float, cy: float, scale: float = 15) -> None:
    c.setStrokeColor(GRID)
    c.setDash(2, 2)
    c.rect(cx - 3.7 * scale, cy - 2.7 * scale, 7.4 * scale, 5.4 * scale, stroke=1, fill=0)
    c.setDash()
    c.setStrokeColor(BODY)
    c.rect(cx - 1.95 * scale, cy - 2.45 * scale, 3.9 * scale, 4.9 * scale, stroke=1, fill=0)
    c.setFillColor(BODY)
    c.circle(cx - 0.9 * scale, cy - 1.7 * scale, 0.16 * scale, stroke=0, fill=1)
    for i, y in enumerate((-1.905, -0.635, 0.635, 1.905), 1):
        pad(c, cx - 2.475 * scale, cy + y * scale, 1.95 * scale, 0.6 * scale, fill=COPPER, radius=2)
        pad(c, cx + 2.475 * scale, cy - y * scale, 1.95 * scale, 0.6 * scale, fill=COPPER, radius=2)
    c.setFillColor(MASK)
    c.setStrokeColor(MASK)
    c.rect(cx - 1.15 * scale, cy - 1.15 * scale, 2.3 * scale, 2.3 * scale, stroke=1, fill=1)
    for x in (-0.9, 0.9):
        for y in (-0.9, 0.9):
            c.setFillColor(COPPER)
            c.circle(cx + x * scale, cy + y * scale, 0.18 * scale, stroke=0, fill=1)
    dim_h(c, cx - 2.475 * scale, cx - 1.205 * scale, cy - 3.15 * scale, "P1.27", ext_y1=cy - 2.2 * scale, ext_y2=cy - 2.2 * scale)
    dim_h(c, cx - 1.15 * scale, cx + 1.15 * scale, cy + 3.25 * scale, "EP 2.3", ext_y1=cy + 1.15 * scale, ext_y2=cy + 1.15 * scale)
    txt(c, cx, cy - 3.65 * scale, "IP5305T / HSOP-8 + EP", 7.7, NAVY, True, "center")


def draw_inductor(c: canvas.Canvas, cx: float, cy: float, scale: float = 18) -> None:
    c.setStrokeColor(GRID)
    c.setDash(2, 2)
    c.rect(cx - 2.26 * scale, cy - 2.26 * scale, 4.52 * scale, 4.52 * scale, stroke=1, fill=0)
    c.setDash()
    c.setStrokeColor(BODY)
    c.rect(cx - 2 * scale, cy - 2 * scale, 4 * scale, 4 * scale, stroke=1, fill=0)
    pad(c, cx - 1.185 * scale, cy, 0.98 * scale, 3.4 * scale, fill=COPPER, radius=2)
    pad(c, cx + 1.185 * scale, cy, 0.98 * scale, 3.4 * scale, fill=COPPER, radius=2)
    txt(c, cx, cy - 2.9 * scale, "XFL4020 / 4 x 4 x 2 mm", 7.7, NAVY, True, "center")


def draw_0603(c: canvas.Canvas, cx: float, cy: float, scale: float = 30, led: bool = False) -> None:
    c.setStrokeColor(GRID)
    c.setDash(2, 2)
    c.rect(cx - 1.48 * scale, cy - 0.73 * scale, 2.96 * scale, 1.46 * scale, stroke=1, fill=0)
    c.setDash()
    c.setStrokeColor(BODY)
    c.rect(cx - 0.8 * scale, cy - 0.4125 * scale, 1.6 * scale, 0.825 * scale, stroke=1, fill=0)
    pad(c, cx - 0.825 * scale, cy, 0.8 * scale, 0.95 * scale, fill=COPPER, radius=2)
    pad(c, cx + 0.825 * scale, cy, 0.8 * scale, 0.95 * scale, fill=COPPER, radius=2)
    if led:
        c.setStrokeColor(ORANGE)
        c.line(cx - 0.5 * scale, cy - 0.35 * scale, cx - 0.5 * scale, cy + 0.35 * scale)
    txt(c, cx, cy - 1.2 * scale, "0603 metric / 1.6 x 0.8", 7.7, NAVY, True, "center")


def draw_0805(c: canvas.Canvas, cx: float, cy: float, scale: float = 25) -> None:
    c.setStrokeColor(GRID)
    c.setDash(2, 2)
    c.rect(cx - 1.7 * scale, cy - 0.98 * scale, 3.4 * scale, 1.96 * scale, stroke=1, fill=0)
    c.setDash()
    c.setStrokeColor(BODY)
    c.rect(cx - 1 * scale, cy - 0.625 * scale, 2 * scale, 1.25 * scale, stroke=1, fill=0)
    pad(c, cx - 0.95 * scale, cy, 1 * scale, 1.45 * scale, fill=COPPER, radius=2)
    pad(c, cx + 0.95 * scale, cy, 1 * scale, 1.45 * scale, fill=COPPER, radius=2)
    txt(c, cx, cy - 1.45 * scale, "0805 metric / 2.0 x 1.25", 7.7, NAVY, True, "center")


def draw_ws2812(c: canvas.Canvas, cx: float, cy: float, scale: float = 28) -> None:
    c.setStrokeColor(GRID)
    c.setDash(2, 2)
    c.rect(cx - 1.52 * scale, cy - 1.25 * scale, 3.04 * scale, 2.5 * scale, stroke=1, fill=0)
    c.setDash()
    c.setStrokeColor(BODY)
    c.rect(cx - 1.1 * scale, cy - 1.0 * scale, 2.2 * scale, 2.0 * scale, stroke=1, fill=0)
    c.setFillColor(TEAL)
    c.circle(cx, cy, 0.45 * scale, stroke=0, fill=1)
    c.setStrokeColor(colors.white)
    c.line(cx - 0.55 * scale, cy - 1 * scale, cx + 0.55 * scale, cy - 1 * scale)
    for x, y in ((-0.7, -0.7), (-0.7, 0.7), (0.7, 0.7), (0.7, -0.7)):
        pad(c, cx + x * scale, cy + y * scale, 0.75 * scale, 0.65 * scale, fill=COPPER, radius=2)
    txt(c, cx, cy - 1.75 * scale, "WS2812B-2020 / 2.0 x 2.0", 7.7, NAVY, True, "center")


def table(c: canvas.Canvas, x: float, y_top: float, widths: list[float], rows: list[list[str]],
          row_h: float = 22, header_fill=NAVY, font_size: float = 7.8) -> float:
    total_w = sum(widths)
    y = y_top
    for r_index, row in enumerate(rows):
        h = row_h if r_index == 0 else row_h
        fill = header_fill if r_index == 0 else (colors.white if r_index % 2 else PALE)
        c.setFillColor(fill)
        c.setStrokeColor(colors.white if r_index == 0 else GRID)
        c.rect(x, y - h, total_w, h, stroke=1, fill=1)
        cursor = x
        for col, value in enumerate(row):
            c.setStrokeColor(colors.white if r_index == 0 else GRID)
            c.line(cursor, y, cursor, y - h)
            if r_index == 0:
                txt(c, cursor + 6, y - h / 2 - 2.6, value, font_size, colors.white, True)
            else:
                lines = wrap(value, widths[col] - 12, font_size)
                line_y = y - 9
                for line in lines[:2]:
                    txt(c, cursor + 6, line_y, line, font_size, INK)
                    line_y -= font_size * 1.25
            cursor += widths[col]
        c.line(x + total_w, y, x + total_w, y - h)
        y -= h
    return y


def page_one(c: canvas.Canvas) -> None:
    header(c, "SmartPaddle M5 尾板器件采购图纸", "按当前 pcb-tail KiCad 封装与 main.ato BOM 生成", 1)
    section_label(c, MARGIN, PAGE_H - 83, "采购概览")
    txt(c, MARGIN, PAGE_H - 105, "这份图纸用于采购和贴片厂封装核对。器件外形示意均为顶视图，尺寸以标注为准。", 8.5, MUTED)

    # board overview image
    image_x, image_y, image_w, image_h = PAGE_W - 290, 286, 250, 220
    round_rect(c, image_x - 12, image_y - 12, image_w + 24, image_h + 36, fill=PALE, stroke=GRID, radius=8)
    if BOARD_IMAGE.exists():
        c.drawImage(ImageReader(str(BOARD_IMAGE)), image_x, image_y, width=image_w, height=image_h,
                    preserveAspectRatio=True, anchor="c", mask="auto")
    txt(c, image_x, image_y - 3, "当前尾板 3D 顶视预览", 8, MUTED, True)

    rows = [
        ["类别", "采购件", "数量", "封装 / 采购关键词"],
        ["连接器", "USB-C 母座", "1", "16P 立式 SMT，短体，H=5.8"],
        ["连接器", "Molex PicoBlade 53398-0471", "2", "MX1.25，1x04，立插 SMT"],
        ["按键", "4.5 x 4.5 轻触开关", "1", "THT SPST，四孔"],
        ["电源 IC", "IP5305T", "1", "HSOP-8 + EP，必须带散热焊盘"],
        ["USB 保护", "USBLC6-2SC6", "1", "SOT-23-6"],
        ["逻辑 IC", "SN74AHCT1G125DBVR", "1", "SOT-23-5"],
        ["功率件", "Coilcraft XFL4020-222MEC", "1", "2.2 uH，4 x 4 x 2 mm"],
        ["指示灯", "WS2812B-2020", "1", "2.0 x 2.0，四焊盘"],
        ["指示灯", "LTST-C190KGKT 或同规格绿灯", "1", "0603 metric"],
        ["电阻", "5.1k x2, 2R, 10k, 200R, 1k, 330R", "7", "全部 R_0603_1608Metric"],
        ["电容", "10 uF x4, 22 uF x1", "5", "全部 C_0805_2012Metric，10V+"],
        ["电容", "100 nF x2", "2", "C_0603_1608Metric，16V+"],
    ]
    table(c, MARGIN, PAGE_H - 130, [62, 205, 42, 205], rows, row_h=21, font_size=7.5)

    # Critical notes
    box_x, box_y, box_w, box_h = PAGE_W - 290, 170, 250, 92
    round_rect(c, box_x - 12, box_y - 12, box_w + 24, box_h + 24, fill=PALE_ORANGE, stroke=colors.HexColor("#edc58f"), radius=8)
    txt(c, box_x, box_y + box_h - 6, "采购重点", 9.5, ORANGE, True)
    notes = [
        "1. Type-C 信号焊盘同排间距是 P0.78，不是普通 P0.50 通用座。",
        "2. Type-C 是 16P 立式短体，外壳固定槽 C-C 为 8.65。",
        "3. 轻触开关是 4.5 x 4.5 THT，不是旧计划里的贴片 KMR221。",
        "4. 当前尾板为实验样板，替代料必须先核对焊盘和机械高度。",
    ]
    line_y = box_y + box_h - 22
    for note in notes:
        line_y = text_block(c, box_x, line_y, note, box_w, 7.4, leading=10.5, color=INK) - 1

    pill(c, MARGIN, 66, "每块板 24 个器件位", fill=PALE_BLUE, color=BLUE)
    pill(c, MARGIN + 124, 66, "板厚 1.0 mm", fill=PALE_BLUE, color=BLUE)
    pill(c, MARGIN + 220, 66, "2 x 4P 尾板线束", fill=PALE_BLUE, color=BLUE)
    footer(c, 1)
    c.showPage()


def page_two(c: canvas.Canvas) -> None:
    header(c, "连接器与机电件封装", "Type-C、MX1.25 线束座、用户按键", 2)
    section_label(c, MARGIN, PAGE_H - 83, "关键机械封装")
    txt(c, MARGIN, PAGE_H - 105, "所有图为 PCB 顶视图。铜色为焊盘，灰色为器件/丝印参考框，虚线为 courtyard。", 8.5, MUTED)

    # Type-C card
    x, y, w, h = MARGIN, 250, 390, 230
    round_rect(c, x, y, w, h, fill=colors.white, stroke=GRID)
    pill(c, x + 16, y + h - 31, "J1 / USB-C", fill=PALE_BLUE, color=BLUE)
    txt(c, x + 16, y + h - 55, "16P 立式 SMT 短体母座", 10, NAVY, True)
    draw_typec(c, x + 145, y + 106, scale=20)
    text_block(c, x + 285, y + 142, "采购型号关键词\nGCT USB4120-03-C 同系列\n16P vertical SMT short body\n身体高度 H=5.8 mm", 92, 7.5, leading=10.5, color=INK)
    text_block(c, x + 285, y + 82, "焊盘关键尺寸\n同排 P0.78\n单焊盘 0.32 x 1.72\n两排中心距 2.20\n外壳槽 C-C 8.65", 92, 7.5, leading=10.5, color=MUTED)

    # Molex card
    x2, y2, w2, h2 = 450, 250, PAGE_W - 450 - MARGIN, 230
    round_rect(c, x2, y2, w2, h2, fill=colors.white, stroke=GRID)
    pill(c, x2 + 16, y2 + h2 - 31, "J2 / J3", fill=PALE_BLUE, color=BLUE)
    txt(c, x2 + 16, y2 + h2 - 55, "MX1.25 4P 立插线束座", 10, NAVY, True)
    draw_molex(c, x2 + 146, y2 + 107, scale=13)
    text_block(c, x2 + 292, y2 + 142, "采购型号\nMolex PicoBlade\n53398-0471\n1x04, P1.25 mm\nvertical SMT + MP", 100, 7.5, leading=10.5, color=INK)
    text_block(c, x2 + 292, y2 + 80, "板上有两只\nJ2: 电源/电池采样\nJ3: USB/按键/RGB\n板端座不等于线端壳", 100, 7.5, leading=10.5, color=MUTED)

    # Switch card
    x3, y3, w3, h3 = MARGIN, 65, 390, 175
    round_rect(c, x3, y3, w3, h3, fill=colors.white, stroke=GRID)
    pill(c, x3 + 16, y3 + h3 - 31, "SW1", fill=PALE_ORANGE, color=ORANGE)
    txt(c, x3 + 16, y3 + h3 - 55, "4.5 x 4.5 mm THT 轻触开关", 10, NAVY, True)
    draw_switch(c, x3 + 120, y3 + 83, scale=18)
    text_block(c, x3 + 220, y3 + 116, "采购形态\n4.5 x 4.5 mm body\nSPST tactile, THT\n4 个通孔，drill 0.9 mm", 145, 7.8, leading=11, color=INK)
    text_block(c, x3 + 220, y3 + 65, "焊盘孔中心距\nX=5.50, Y=3.40", 145, 7.8, leading=11, color=MUTED)

    # warning card
    x4, y4, w4, h4 = 450, 65, PAGE_W - 450 - MARGIN, 175
    round_rect(c, x4, y4, w4, h4, fill=PALE_ORANGE, stroke=colors.HexColor("#edc58f"))
    txt(c, x4 + 16, y4 + h4 - 32, "不要这样买", 10, ORANGE, True)
    text_block(c, x4 + 16, y4 + h4 - 57,
               "Type-C 不要按普通 0.50 mm 16P 通用座采购。\n"
               "不要把旧的 USB4115 四圆孔封装装到本板。\n"
               "采购链接必须同时确认：16P、立式、短体、H=5.8、焊盘族与图纸一致。\n"
               "MX1.25 线束需要另外采购线端壳体和压接端子。",
               w4 - 32, 8.2, leading=13, color=INK)
    footer(c, 2)
    c.showPage()


def page_three(c: canvas.Canvas) -> None:
    header(c, "IC 与功率件封装", "电源管理、USB ESD、RGB 电平转换、升压电感", 3)
    section_label(c, MARGIN, PAGE_H - 83, "半导体与功率封装")
    txt(c, MARGIN, PAGE_H - 105, "采购时优先按封装名和型号一起核对。IP5305T 的 EP 和散热过孔不能省略。", 8.5, MUTED)

    cards = [
        (MARGIN, 285, 245, 195, "U3 / IP5305T", "HSOP-8 + exposed pad", "1S 充放电 + 5V 升压\n8 个侧焊盘，P1.27\nEP 2.3 x 2.3\n四颗 0.3 mm 散热过孔", "ip"),
        (MARGIN + 260, 285, 245, 195, "U2 / USBLC6-2SC6", "SOT-23-6", "USB D+/D- ESD\n左 3 + 右 3 焊盘\n引脚间距 P0.95\n按 Pin 1 方向采购", "sot6"),
        (MARGIN + 520, 285, 245, 195, "U1 / SN74AHCT1G125", "SOT-23-5", "3.3V 到 5V RGB 数据缓冲\n左 3 + 右 2 焊盘\n引脚间距 P0.95\n采购 DBVR 封装", "sot5"),
        (MARGIN, 75, 245, 195, "L1 / XFL4020-222MEC", "2.2 uH, 4 x 4 x 2 mm", "IP5305T 升压电感\n两侧大焊盘\n焊盘中心距约 2.37\n不要用 3 x 3 小电感替代", "ind"),
    ]
    for cx, cy, cw, ch, title, subtitle, body, kind in cards:
        round_rect(c, cx, cy, cw, ch, fill=colors.white, stroke=GRID)
        pill(c, cx + 14, cy + ch - 29, title, fill=PALE_BLUE if kind != "ind" else PALE_ORANGE,
             color=BLUE if kind != "ind" else ORANGE)
        txt(c, cx + 14, cy + ch - 53, subtitle, 9, NAVY, True)
        if kind == "ip":
            draw_ip5305(c, cx + 75, cy + 83, scale=11)
        elif kind == "sot6":
            draw_sot23(c, cx + 73, cy + 83, 6, scale=14)
        elif kind == "sot5":
            draw_sot23(c, cx + 73, cy + 83, 5, scale=14)
        else:
            draw_inductor(c, cx + 75, cy + 83, scale=14)
        text_block(c, cx + 140, cy + 132, body, cw - 154, 7.8, leading=11, color=INK)

    # procurement note strip
    round_rect(c, MARGIN + 260, 75, PAGE_W - MARGIN - (MARGIN + 260), 195, fill=PALE, stroke=GRID)
    txt(c, MARGIN + 276, 238, "封装核对表", 10, NAVY, True)
    rows = [
        ["型号", "板上封装", "关键核对"],
        ["IP5305T", "HSOP-8-1EP", "P1.27 / EP / thermal vias"],
        ["USBLC6-2SC6", "SOT-23-6", "6-pin, P0.95"],
        ["SN74AHCT1G125DBVR", "SOT-23-5", "5-pin, P0.95"],
        ["XFL4020-222MEC", "XFL4020", "4 x 4 mm, 2.2 uH"],
    ]
    table(c, MARGIN + 276, 222, [120, 90, 135], rows, row_h=23, font_size=7.5)
    text_block(c, MARGIN + 276, 103,
               "IP5305T 采购要拿到正式封装图和顶标信息。兼容料、翻新料或只有 SOIC-8 外形的料不能直接替代。",
               345, 8, leading=11, color=RED, bold=True)
    footer(c, 3)
    c.showPage()


def page_four(c: canvas.Canvas) -> None:
    header(c, "阻容与 LED 封装", "0603 / 0805 / WS2812B-2020", 4)
    section_label(c, MARGIN, PAGE_H - 83, "无源器件与指示灯")
    txt(c, MARGIN, PAGE_H - 105, "阻容尺寸均为 metric 标法；采购时同时写出公制尺寸，避免英制标法混淆。", 8.5, MUTED)

    # footprint visual cards
    cards = [
        (MARGIN, 285, 190, 190, "R1-R7 / 0603", "1.6 x 0.8 mm", "5.1k x2, 2R, 10k, 200R, 1k, 330R", "r"),
        (MARGIN + 205, 285, 190, 190, "C1-C2 / C0603", "1.6 x 0.8 mm", "100 nF x2, X7R, 16V+", "c0603"),
        (MARGIN + 410, 285, 190, 190, "C3-C7 / C0805", "2.0 x 1.25 mm", "10 uF x4 + 22 uF x1, 10V+", "c0805"),
        (MARGIN + 615, 285, 196, 190, "D1 / WS2812B-2020", "2.0 x 2.0 mm", "VDD / GND / DIN / DOUT\n注意 Pin 1 方向", "ws"),
        (MARGIN, 75, 395, 190, "LED1 / 0603 green", "0603 metric, 1.6 x 0.8 mm", "LTST-C190KGKT 或同规格绿灯\n板上为独立电源状态灯，注意极性", "led"),
    ]
    for cx, cy, cw, ch, title, subtitle, body, kind in cards:
        round_rect(c, cx, cy, cw, ch, fill=colors.white, stroke=GRID)
        pill(c, cx + 14, cy + ch - 29, title, fill=PALE_BLUE if kind not in ("led",) else PALE_ORANGE,
             color=BLUE if kind not in ("led",) else ORANGE)
        txt(c, cx + 14, cy + ch - 53, subtitle, 9, NAVY, True)
        if kind == "r":
            draw_0603(c, cx + 65, cy + 92, scale=25)
        elif kind == "c0603":
            draw_0603(c, cx + 65, cy + 92, scale=25)
        elif kind == "c0805":
            draw_0805(c, cx + 65, cy + 92, scale=23)
        elif kind == "ws":
            draw_ws2812(c, cx + 66, cy + 92, scale=24)
        else:
            draw_0603(c, cx + 70, cy + 92, scale=25, led=True)
        text_block(c, cx + 116, cy + 128, body, cw - 130, 7.8, leading=11, color=INK)

    # bottom checklist
    x, y, w, h = MARGIN + 410, 75, PAGE_W - MARGIN - (MARGIN + 410), 190
    round_rect(c, x, y, w, h, fill=PALE_ORANGE, stroke=colors.HexColor("#edc58f"))
    txt(c, x + 16, y + h - 32, "采购写法建议", 10, ORANGE, True)
    notes = [
        "0603 电阻: R_0603_1608Metric",
        "0603 电容: C_0603_1608Metric",
        "0805 电容: C_0805_2012Metric",
        "WS2812B: 2020, 4-pin, 5V addressable RGB",
        "绿色 LED: 0603, 极性按板上丝印/封装缺口核对",
        "电容电压: 0805 选 10V 或更高，0603 去耦选 16V 或更高",
    ]
    line_y = y + h - 57
    for note in notes:
        txt(c, x + 18, line_y, "- " + note, 8, INK)
        line_y -= 17
    footer(c, 4)
    c.showPage()


def build() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT_PDF), pagesize=landscape(A4), pageCompression=1)
    c.setTitle("SmartPaddle M5 Tail Board Procurement Drawing")
    c.setAuthor("SmartPaddle project")
    page_one(c)
    page_two(c)
    page_three(c)
    page_four(c)
    c.save()
    print(OUT_PDF)


if __name__ == "__main__":
    build()
