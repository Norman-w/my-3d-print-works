#!/usr/bin/env python3
"""Generate a conservative, printable SmartPaddle solder assembly package.

The PCB is read-only input. Placement facts come from an exact byte snapshot of
the .kicad_pcb file. Any orientation claim that the board cannot prove is marked
TO_CONFIRM instead of being guessed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PCB = PROJECT_ROOT / "pcb/layouts/default/default.kicad_pcb"
DEFAULT_OUT = PROJECT_ROOT / "output/pdf/assembly-package"
EVIDENCE_PATH = Path(__file__).with_name("orientation_evidence.json")
PDF_NAME = "smartpaddle_printable_assembly_package.pdf"
CSV_NAME = "smartpaddle_assembly_components.csv"
MANIFEST_NAME = "assembly_package_manifest.json"
QA_NAME = "assembly_package_qa.json"
CONTACT_NAME = "smartpaddle_assembly_package_contact_sheet.png"
PAGE_SIZE = landscape(A4)

VERIFIED = "VERIFIED"
TO_CONFIRM = "TO_CONFIRM"

COLORS = {
    "R": colors.HexColor("#C45C26"),
    "C": colors.HexColor("#2A6FDB"),
    "D": colors.HexColor("#8B1FA8"),
    "Q": colors.HexColor("#B58B16"),
    "U": colors.HexColor("#1A7A4C"),
    "MOD": colors.HexColor("#0B3D5C"),
    "SW": colors.HexColor("#B45309"),
    "LED": colors.HexColor("#DB2777"),
    "PAD": colors.HexColor("#444444"),
    "TP": colors.HexColor("#666666"),
}

STAGE_NAMES = {
    0: "0 DNP / inspect only",
    1: "1 Low-profile R/C",
    2: "2 Diodes / LED / IC / MOS",
    3: "3 Modules / switches / connectors",
    4: "4 PZT wires",
}


@dataclass
class Pad:
    number: str
    x: float
    y: float
    net: str = ""


@dataclass
class Part:
    ref: str
    value: str
    package: str
    side: str
    x: float
    y: float
    rotation: float
    description: str = ""
    pads: list[Pad] = field(default_factory=list)
    kind: str = "U"
    install: str = "PLACE"
    stage: int = 2
    location_status: str = VERIFIED
    orientation_status: str = TO_CONFIRM
    orientation_instruction: str = ""
    orientation_evidence: str = ""

    @property
    def pad1(self) -> Pad | None:
        return next((p for p in self.pads if p.number == "1"), None)


@dataclass
class PackageContext:
    source_path: str
    source_sha256: str
    generated_at: str
    git_commit: str
    git_dirty: bool
    board_title: str
    board_revision: str
    legacy_count: int | None
    warnings: list[str]
    current_at_finish: bool = False


def _unquote(token: str) -> str:
    if not token.startswith('"'):
        return token
    return token[1:-1].replace(r"\"", '"').replace(r"\\", "\\")


def parse_sexpr(text: str) -> list[Any]:
    """Small, lossless-enough S-expression parser for KiCad board metadata."""
    token_re = re.compile(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()]+')
    roots: list[Any] = []
    stack: list[list[Any]] = []
    for match in token_re.finditer(text):
        token = match.group(0)
        if token == "(":
            node: list[Any] = []
            if stack:
                stack[-1].append(node)
            else:
                roots.append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("Unexpected ')' while parsing KiCad board")
            stack.pop()
        else:
            if not stack:
                raise ValueError("Atom outside S-expression")
            stack[-1].append(_unquote(token))
    if stack:
        raise ValueError("Unclosed S-expression in KiCad board")
    if len(roots) != 1 or not roots[0] or roots[0][0] != "kicad_pcb":
        raise ValueError("Input is not a KiCad PCB document")
    return roots[0]


def _children(node: Sequence[Any], name: str) -> list[list[Any]]:
    return [x for x in node[1:] if isinstance(x, list) and x and x[0] == name]


def _child(node: Sequence[Any], name: str) -> list[Any] | None:
    return next(iter(_children(node, name)), None)


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _property(node: Sequence[Any], name: str) -> str:
    for prop in _children(node, "property"):
        if len(prop) >= 3 and prop[1] == name:
            return str(prop[2])
    return ""


def _transform_local(fx: float, fy: float, rotation: float, lx: float, ly: float) -> tuple[float, float]:
    angle = math.radians(rotation)
    return (
        fx + lx * math.cos(angle) - ly * math.sin(angle),
        fy + lx * math.sin(angle) + ly * math.cos(angle),
    )


def extract_parts(board: Sequence[Any]) -> list[Part]:
    parts: list[Part] = []
    for fp in _children(board, "footprint"):
        at = _child(fp, "at") or ["at", 0, 0, 0]
        layer = _child(fp, "layer") or ["layer", "F.Cu"]
        fx, fy = _num(at[1]), _num(at[2])
        rotation = _num(at[3] if len(at) > 3 else 0)
        side = "bottom" if len(layer) > 1 and str(layer[1]).startswith("B.") else "top"
        ref = _property(fp, "Reference")
        if not ref:
            continue
        pads: list[Pad] = []
        for pad_node in _children(fp, "pad"):
            if len(pad_node) < 2:
                continue
            pad_at = _child(pad_node, "at") or ["at", 0, 0]
            px, py = _transform_local(fx, fy, rotation, _num(pad_at[1]), _num(pad_at[2]))
            net_node = _child(pad_node, "net")
            net = str(net_node[2]) if net_node and len(net_node) > 2 else ""
            pads.append(Pad(str(pad_node[1]), px, py, net))
        descr = _child(fp, "descr")
        part = Part(
            ref=ref,
            value=_property(fp, "Value") or "[value missing]",
            package=str(fp[1]) if len(fp) > 1 else "[package missing]",
            side=side,
            x=fx,
            y=fy,
            rotation=rotation % 360,
            description=str(descr[1]) if descr and len(descr) > 1 else "",
            pads=pads,
        )
        classify_part(part)
        parts.append(part)
    refs = [p.ref for p in parts]
    if len(refs) != len(set(refs)):
        duplicates = sorted({r for r in refs if refs.count(r) > 1})
        raise ValueError(f"Duplicate footprint references: {duplicates}")
    if not parts:
        raise ValueError("No footprints found in PCB")
    return sorted(parts, key=lambda p: p.ref)


def classify_part(part: Part) -> None:
    ref = part.ref.upper()
    value = part.value.upper()
    package = part.package.upper()
    if ref.startswith("TP_"):
        part.kind = "TP"
        part.install = "INSPECT"
        part.stage = 0
        part.orientation_status = VERIFIED
        part.orientation_instruction = "Existing test point: inspect only; do not add a component."
        part.orientation_evidence = "Reference and footprint in PCB snapshot"
        return
    if "DNP" in value:
        part.kind = "R" if ref.startswith("JP_") else "U"
        part.install = "DNP"
        part.stage = 0
        part.orientation_status = VERIFIED
        part.orientation_instruction = "DNP: leave unpopulated unless an approved rework instruction says otherwise."
        part.orientation_evidence = "Value contains DNP in PCB snapshot"
        return
    if ref.startswith("PZT_") and ref.endswith(("_SIG", "_GND")):
        part.kind = "PAD"
        part.stage = 4
        part.orientation_status = TO_CONFIRM
        part.orientation_instruction = "Board pad/net is shown; confirm which physical PZT lead is signal/GND before soldering."
        part.orientation_evidence = "PCB proves pad/net, not the loose sensor lead identity"
        return
    if ref.startswith("R_") or ref.startswith("BAT_R") or "_R_" in ref or ref.startswith("JP_"):
        part.kind = "R"
        part.stage = 1
        part.orientation_status = VERIFIED
        part.orientation_instruction = "Non-polar resistor: either direction; match value and footprint."
        part.orientation_evidence = "Resistor reference/footprint in PCB snapshot"
        return
    if ref.startswith("C_") or ref.startswith("BAT_C") or "_C_" in ref or package.split(":")[-1].startswith("C_"):
        part.kind = "C"
        part.stage = 1
        if any(word in package for word in ("CP_", "TANTAL", "POLAR")):
            part.orientation_status = TO_CONFIRM
            part.orientation_instruction = "Polar capacitor footprint: confirm + / - against the exact part datasheet and board mark."
            part.orientation_evidence = "Polarity not fully proven by placement data"
        else:
            part.orientation_status = VERIFIED
            part.orientation_instruction = "Non-polar chip capacitor: either direction; match value and footprint."
            part.orientation_evidence = "Non-polar C footprint in PCB snapshot"
        return
    if ref.startswith("LED_"):
        part.kind = "LED"
        part.stage = 2
    elif ref.startswith("D_") or "_D_" in ref or "DIODE" in package:
        part.kind = "D"
        part.stage = 2
    elif ref.startswith("Q_") or "_Q_" in ref or "MOS" in value:
        part.kind = "Q"
        part.stage = 2
    elif ref.startswith("SW_"):
        part.kind = "SW"
        part.stage = 3
        part.orientation_status = VERIFIED
        part.orientation_instruction = "Non-polar switch: match body outline and all plated holes."
        part.orientation_evidence = "Switch footprint geometry in PCB snapshot"
        return
    elif ref.startswith(("MCU_", "IMU_")):
        part.kind = "MOD"
        part.stage = 3
    elif ref.startswith("TAIL_") or "CONNECTOR" in package or "MOLEX" in package:
        part.kind = "PAD"
        part.stage = 3
    else:
        part.kind = "U"
        part.stage = 2

    part.orientation_status = TO_CONFIRM
    part.orientation_instruction = "Align the exact part's physical Pin 1 / polarity mark with the red Pad 1 marker; verify its datasheet first."
    part.orientation_evidence = "Pad 1 position is in PCB; physical package marking is not proven by PCB alone"


def apply_evidence(parts: list[Part], path: Path) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    overrides = data.get("overrides", {})
    by_ref = {p.ref: p for p in parts}
    for ref, rule in overrides.items():
        part = by_ref.get(ref)
        if part is None:
            continue
        required = str(rule.get("evidence_contains", ""))
        if not required or required.lower() not in part.description.lower():
            continue
        part.orientation_status = str(rule.get("status", TO_CONFIRM))
        part.orientation_instruction = str(rule.get("instruction", part.orientation_instruction))
        part.orientation_evidence = str(rule.get("evidence", "Configured evidence"))


def _xy(node: Sequence[Any], name: str) -> tuple[float, float] | None:
    item = _child(node, name)
    if not item or len(item) < 3:
        return None
    return _num(item[1]), _num(item[2])


def _on_edge_cuts(node: Sequence[Any]) -> bool:
    layer = _child(node, "layer")
    return bool(layer and len(layer) > 1 and layer[1] == "Edge.Cuts")


def _arc_points(start: tuple[float, float], mid: tuple[float, float], end: tuple[float, float]) -> list[tuple[float, float]]:
    x1, y1 = start
    x2, y2 = mid
    x3, y3 = end
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-9:
        return [start, mid, end]
    ux = ((x1 * x1 + y1 * y1) * (y2 - y3) + (x2 * x2 + y2 * y2) * (y3 - y1) + (x3 * x3 + y3 * y3) * (y1 - y2)) / d
    uy = ((x1 * x1 + y1 * y1) * (x3 - x2) + (x2 * x2 + y2 * y2) * (x1 - x3) + (x3 * x3 + y3 * y3) * (x2 - x1)) / d
    a1 = math.atan2(y1 - uy, x1 - ux)
    am = math.atan2(y2 - uy, x2 - ux)
    a3 = math.atan2(y3 - uy, x3 - ux)
    ccw_span = (a3 - a1) % (2 * math.pi)
    ccw_mid = (am - a1) % (2 * math.pi)
    span = ccw_span if ccw_mid <= ccw_span else -((a1 - a3) % (2 * math.pi))
    steps = max(6, int(abs(span) / (math.pi / 24)))
    radius = math.hypot(x1 - ux, y1 - uy)
    return [(ux + radius * math.cos(a1 + span * i / steps), uy + radius * math.sin(a1 + span * i / steps)) for i in range(steps + 1)]


def extract_edge_paths(board: Sequence[Any]) -> list[list[tuple[float, float]]]:
    paths: list[list[tuple[float, float]]] = []
    for node in board[1:]:
        if not isinstance(node, list) or not node or not _on_edge_cuts(node):
            continue
        if node[0] == "gr_line":
            start, end = _xy(node, "start"), _xy(node, "end")
            if start and end:
                paths.append([start, end])
        elif node[0] == "gr_arc":
            start, mid, end = _xy(node, "start"), _xy(node, "mid"), _xy(node, "end")
            if start and mid and end:
                paths.append(_arc_points(start, mid, end))
        elif node[0] == "gr_rect":
            start, end = _xy(node, "start"), _xy(node, "end")
            if start and end:
                x1, y1 = start
                x2, y2 = end
                paths.append([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)])
        elif node[0] in {"gr_poly", "gr_curve"}:
            pts_node = _child(node, "pts")
            if pts_node:
                pts = [(float(x[1]), float(x[2])) for x in pts_node[1:] if isinstance(x, list) and x and x[0] == "xy"]
                if len(pts) >= 2:
                    paths.append(pts)
    if not paths:
        raise ValueError("No Edge.Cuts geometry found")
    return paths


def board_metadata(board: Sequence[Any]) -> tuple[str, str]:
    title_block = _child(board, "title_block")
    if not title_block:
        return "", ""
    title = _child(title_block, "title")
    rev = _child(title_block, "rev")
    return (
        str(title[1]) if title and len(title) > 1 else "",
        str(rev[1]) if rev and len(rev) > 1 else "",
    )


def _run_git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=PROJECT_ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def legacy_component_count() -> int | None:
    legacy = PROJECT_ROOT / "output/assembly/smartpaddle_solder_checklist_v3.csv"
    if not legacy.exists():
        return None
    with legacy.open(encoding="utf-8-sig", newline="") as stream:
        return sum(1 for _ in csv.DictReader(stream))


def register_font() -> str:
    candidates = [
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            pdfmetrics.registerFont(TTFont("SmartPaddleCJK", str(candidate)))
            return "SmartPaddleCJK"
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def wrap_text(text: str, font: str, size: float, width: float, max_lines: int | None = None) -> list[str]:
    text = str(text).replace("\n", " ").strip()
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and pdfmetrics.stringWidth(candidate, font, size) > width:
            lines.append(current.rstrip())
            current = char.lstrip()
            if max_lines and len(lines) >= max_lines:
                break
        else:
            current = candidate
    if (not max_lines or len(lines) < max_lines) and current:
        lines.append(current.rstrip())
    if max_lines and len(lines) == max_lines and "".join(lines) != text:
        ellipsis = "..."
        while lines[-1] and pdfmetrics.stringWidth(lines[-1] + ellipsis, font, size) > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += ellipsis
    return lines


class PdfBuilder:
    def __init__(self, path: Path, font: str, total_pages: int, context: PackageContext):
        self.canvas = canvas.Canvas(str(path), pagesize=PAGE_SIZE, pageCompression=1)
        self.font = font
        self.total_pages = total_pages
        self.page_no = 0
        self.context = context

    def start_page(self, title: str, subtitle: str = "") -> None:
        if self.page_no:
            self.canvas.showPage()
        self.page_no += 1
        c = self.canvas
        width, height = PAGE_SIZE
        c.setFillColor(colors.HexColor("#102A43"))
        c.rect(0, height - 17 * mm, width, 17 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(self.font, 14)
        c.drawString(9 * mm, height - 10.6 * mm, title)
        if subtitle:
            c.setFont(self.font, 7.2)
            c.drawRightString(width - 9 * mm, height - 10.2 * mm, subtitle)
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.line(8 * mm, 10 * mm, width - 8 * mm, 10 * mm)
        c.setFillColor(colors.HexColor("#52606D"))
        c.setFont(self.font, 6.8)
        c.drawString(8 * mm, 6.2 * mm, f"PCB snapshot sha256 {self.context.source_sha256[:16]}... | print at 100% actual size")
        c.drawRightString(width - 8 * mm, 6.2 * mm, f"Page {self.page_no}/{self.total_pages}")

    def finish(self) -> None:
        self.canvas.save()


def _status_colors(status: str) -> tuple[colors.Color, colors.Color]:
    if status == VERIFIED:
        return colors.HexColor("#E7F6EC"), colors.HexColor("#217A3C")
    return colors.HexColor("#FFF2CC"), colors.HexColor("#8A5B00")


def draw_badge(c: canvas.Canvas, font: str, x: float, y: float, status: str, label: str | None = None) -> float:
    text = label or ("[OK] 已验证" if status == VERIFIED else "[CHECK] 待确认")
    fill, ink = _status_colors(status)
    width = pdfmetrics.stringWidth(text, font, 7.2) + 5 * mm
    c.setFillColor(fill)
    c.setStrokeColor(ink)
    c.roundRect(x, y - 3.2 * mm, width, 5.8 * mm, 1.3 * mm, fill=1, stroke=1)
    c.setFillColor(ink)
    c.setFont(font, 7.2)
    c.drawCentredString(x + width / 2, y - 1.15 * mm, text)
    return width


def draw_wrapped(c: canvas.Canvas, font: str, text: str, x: float, y: float, width: float, size: float, leading: float, max_lines: int | None = None, color: colors.Color = colors.black) -> float:
    c.setFont(font, size)
    c.setFillColor(color)
    lines = wrap_text(text, font, size, width, max_lines)
    for idx, line in enumerate(lines):
        c.drawString(x, y - idx * leading, line)
    return y - len(lines) * leading


def draw_cover(builder: PdfBuilder, parts: list[Part], ctx: PackageContext) -> None:
    builder.start_page("SmartPaddle 可打印焊接装配包", "一条命令生成 | 数据来自当前 PCB 快照")
    c, font = builder.canvas, builder.font
    width, height = PAGE_SIZE
    ok_count = sum(p.orientation_status == VERIFIED for p in parts)
    check_count = len(parts) - ok_count
    place_count = sum(p.install == "PLACE" for p in parts)
    dnp_count = sum(p.install == "DNP" for p in parts)
    inspect_count = sum(p.install == "INSPECT" for p in parts)

    c.setFillColor(colors.HexColor("#F4F7FA"))
    c.roundRect(9 * mm, height - 70 * mm, 180 * mm, 45 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#102A43"))
    c.setFont(font, 11)
    c.drawString(15 * mm, height - 34 * mm, "本包对应的唯一数据快照")
    source_lines = [
        f"文件: {ctx.source_path}",
        f"SHA256: {ctx.source_sha256}",
        f"Git: {ctx.git_commit or '[unknown]'} | 工作树: {'有未提交改动' if ctx.git_dirty else 'clean'}",
        f"PCB 标题/版本: {ctx.board_title or '[未填写]'} / {ctx.board_revision or '[未填写]'}",
    ]
    y = height - 43 * mm
    for line in source_lines:
        y = draw_wrapped(c, font, line, 15 * mm, y, 168 * mm, 7.6, 4.2 * mm, 2, colors.HexColor("#334E68"))

    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.roundRect(197 * mm, height - 70 * mm, 91 * mm, 45 * mm, 2 * mm, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#102A43"))
    c.setFont(font, 10)
    c.drawString(203 * mm, height - 34 * mm, "内容统计")
    c.setFont(font, 8.2)
    lines = [
        f"封装实例: {len(parts)}",
        f"待安装: {place_count} | DNP: {dnp_count} | 仅检查: {inspect_count}",
        f"方向已验证: {ok_count} | 待确认: {check_count}",
        f"顶面: {sum(p.side == 'top' for p in parts)} | 底面: {sum(p.side == 'bottom' for p in parts)}",
    ]
    for idx, line in enumerate(lines):
        c.drawString(203 * mm, height - (43 + idx * 6.2) * mm, line)

    y = height - 82 * mm
    c.setFillColor(colors.HexColor("#102A43"))
    c.setFont(font, 11)
    c.drawString(10 * mm, y, "开焊前的放行门")
    y -= 8 * mm
    gate = [
        (TO_CONFIRM, "将实物裸板的版本/丝印与上方 SHA 对应的设计快照核对；PCB 文件不能证明你手里的板就是这一版。"),
        (TO_CONFIRM, "逐项解决所有 [CHECK]，尤其是二极管、MOS、IC、模块和连接器的实物 Pin 1 / 极性标记。"),
        (VERIFIED, "位置、面别、旋转、封装名、Pad 1 位置和 Pad 网络均直接取自 PCB 快照，不取旧图坐标。"),
    ]
    for status, line in gate:
        badge_w = draw_badge(c, font, 12 * mm, y, status)
        draw_wrapped(c, font, line, 15 * mm + badge_w, y + 0.5 * mm, 265 * mm - badge_w, 8.2, 4.2 * mm, 2)
        y -= 13 * mm

    c.setFillColor(colors.HexColor("#102A43"))
    c.setFont(font, 11)
    c.drawString(10 * mm, y, "建议安装顺序")
    y -= 7 * mm
    steps = [
        "0. 先留空 DNP，并确认测试点只检查、不加器件。",
        "1. 焊低矮非极性 R/C；每一区完成后就地复检数值和焊桥。",
        "2. 焊 LED/二极管/IC/MOS；每颗先查实物标记，再对红色 Pad 1。",
        "3. 焊模块、开关、顶/底连接器；先干装确认机械方向。",
        "4. 最后焊 PZT 线；确认每根线的 SIG/GND 身份并做应力释放。",
    ]
    for step in steps:
        c.setFillColor(colors.HexColor("#334E68"))
        c.setFont(font, 8.1)
        c.drawString(14 * mm, y, step)
        y -= 5.6 * mm

    c.setFillColor(colors.HexColor("#FFF7E6"))
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.roundRect(9 * mm, 17 * mm, 279 * mm, 27 * mm, 2 * mm, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#8A4B08"))
    c.setFont(font, 9)
    c.drawString(15 * mm, 36 * mm, "打印设置: A4 横向 | 实际大小 100% | 不要选择‘适合页面’")
    c.setFont(font, 7.5)
    c.drawString(15 * mm, 28 * mm, "下方标尺打印后应为 20 mm；不符时不要把图纸当作尺寸模板。")
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(202 * mm, 27 * mm, 222 * mm, 27 * mm)
    for offset in (0, 10, 20):
        c.line((202 + offset) * mm, 24.5 * mm, (202 + offset) * mm, 29.5 * mm)
    c.setFillColor(colors.black)
    c.setFont(font, 7)
    c.drawCentredString(212 * mm, 20.5 * mm, "20 mm")


def _board_bounds(paths: list[list[tuple[float, float]]]) -> tuple[float, float, float, float]:
    pts = [point for path in paths for point in path]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _view_xy(x: float, y: float, mirror: bool) -> tuple[float, float]:
    return (-x if mirror else x), -y


def _mapper(bounds: tuple[float, float, float, float], rect: tuple[float, float, float, float], mirror: bool):
    x0, y0, x1, y1 = bounds
    corners = [_view_xy(x0, y0, mirror), _view_xy(x1, y1, mirror)]
    vx0, vx1 = sorted([corners[0][0], corners[1][0]])
    vy0, vy1 = sorted([corners[0][1], corners[1][1]])
    rx, ry, rw, rh = rect
    scale = min(rw / max(vx1 - vx0, 1e-6), rh / max(vy1 - vy0, 1e-6))
    ox = rx + (rw - (vx1 - vx0) * scale) / 2 - vx0 * scale
    oy = ry + (rh - (vy1 - vy0) * scale) / 2 - vy0 * scale
    return lambda x, y: (ox + _view_xy(x, y, mirror)[0] * scale, oy + _view_xy(x, y, mirror)[1] * scale), scale


def draw_board(c: canvas.Canvas, paths: list[list[tuple[float, float]]], transform, clip_rect: tuple[float, float, float, float]) -> None:
    rx, ry, rw, rh = clip_rect
    c.saveState()
    clip = c.beginPath()
    clip.rect(rx, ry, rw, rh)
    c.clipPath(clip, stroke=0, fill=0)
    c.setStrokeColor(colors.HexColor("#263238"))
    c.setLineWidth(0.55)
    for points in paths:
        if len(points) < 2:
            continue
        path = c.beginPath()
        sx, sy = transform(*points[0])
        path.moveTo(sx, sy)
        for point in points[1:]:
            px, py = transform(*point)
            path.lineTo(px, py)
        c.drawPath(path, stroke=1, fill=0)
    c.restoreState()


def draw_part_marker(c: canvas.Canvas, font: str, part: Part, transform, scale: float) -> tuple[float, float]:
    x, y = transform(part.x, part.y)
    color = COLORS.get(part.kind, colors.HexColor("#333333"))
    pad_pts = [transform(p.x, p.y) for p in part.pads if p.number not in {"", "MP"}]
    if pad_pts:
        xs, ys = [p[0] for p in pad_pts], [p[1] for p in pad_pts]
        w = max(max(xs) - min(xs) + 1.2 * mm, 1.5 * mm)
        h = max(max(ys) - min(ys) + 1.2 * mm, 1.5 * mm)
    else:
        w = h = 2.2 * mm
    c.setFillColor(colors.Color(color.red, color.green, color.blue, alpha=0.12))
    c.setStrokeColor(color)
    c.setLineWidth(0.5)
    c.rect(x - w / 2, y - h / 2, w, h, fill=1, stroke=1)
    c.setFillColor(color)
    c.circle(x, y, max(0.7 * mm, min(1.2 * mm, scale * 0.28)), stroke=0, fill=1)
    if part.install == "DNP":
        c.setStrokeColor(colors.HexColor("#B91C1C"))
        c.setLineWidth(1)
        c.line(x - 2 * mm, y - 2 * mm, x + 2 * mm, y + 2 * mm)
        c.line(x - 2 * mm, y + 2 * mm, x + 2 * mm, y - 2 * mm)
    numbered_pads = [p for p in part.pads if p.number not in {"", "MP"}]
    show_all_pads = scale >= 5 and part.kind == "PAD" and len(numbered_pads) <= 12
    pads_to_draw = numbered_pads if show_all_pads else ([part.pad1] if part.pad1 else [])
    for pad in pads_to_draw:
        if pad is None:
            continue
        pad_x, pad_y = transform(pad.x, pad.y)
        is_pin1 = pad.number == "1"
        c.setFillColor(colors.HexColor("#D62828") if is_pin1 else colors.HexColor("#64748B"))
        c.setStrokeColor(colors.white)
        c.circle(pad_x, pad_y, 1.15 * mm, stroke=1, fill=1)
        c.setFillColor(colors.white)
        c.setFont(font, 5.2)
        c.drawCentredString(pad_x, pad_y - 0.62 * mm, pad.number[:3])
    return x, y


def _short_package(package: str, length: int = 28) -> str:
    short = package.split(":")[-1]
    return short if len(short) <= length else short[: length - 3] + "..."


def draw_map_page(builder: PdfBuilder, title: str, note: str, parts: list[Part], paths: list[list[tuple[float, float]]], bounds: tuple[float, float, float, float], side: str = "top", mirror: bool = False) -> None:
    view_label = "底面视角(从板底看，左右已镜像)" if side == "bottom" else "顶面视角(从板顶看)"
    builder.start_page(title, f"{view_label} | 红点 1 = PCB Pad 1")
    c, font = builder.canvas, builder.font
    map_rect = (69 * mm, 18 * mm, 159 * mm, 166 * mm)
    transform, scale = _mapper(bounds, map_rect, mirror)
    draw_board(c, paths, transform, map_rect)
    points: dict[str, tuple[float, float]] = {}
    for part in parts:
        points[part.ref] = draw_part_marker(c, font, part, transform, scale)

    center_x = (bounds[0] + bounds[2]) / 2
    left = [p for p in parts if (_view_xy(p.x, p.y, mirror)[0] < _view_xy(center_x, p.y, mirror)[0])]
    right = [p for p in parts if p not in left]
    while len(left) > len(right) + 2:
        right.append(left.pop())
    while len(right) > len(left) + 2:
        left.append(right.pop())
    left.sort(key=lambda p: points[p.ref][1], reverse=True)
    right.sort(key=lambda p: points[p.ref][1], reverse=True)

    def callout_column(items: list[Part], x: float, anchor_x: float, align: str) -> None:
        if not items:
            return
        top, bottom = 180 * mm, 19 * mm
        step = min(14 * mm, (top - bottom) / max(len(items), 1))
        for idx, part in enumerate(items):
            y = top - idx * step
            px, py = points[part.ref]
            color = COLORS.get(part.kind, colors.HexColor("#333333"))
            c.setStrokeColor(color)
            c.setLineWidth(0.35)
            c.line(px, py, anchor_x, y)
            status_fill, status_ink = _status_colors(part.orientation_status)
            c.setFillColor(status_fill)
            c.setStrokeColor(status_ink)
            box_x = x if align == "left" else x - 58 * mm
            c.roundRect(box_x, y - 4.7 * mm, 58 * mm, 9.3 * mm, 1.1 * mm, fill=1, stroke=1)
            c.setFillColor(status_ink)
            c.setFont(font, 7.0)
            prefix = "[OK]" if part.orientation_status == VERIFIED else "[CHECK]"
            c.drawString(box_x + 1.5 * mm, y + 1.1 * mm, f"{prefix} {part.ref}")
            c.setFillColor(colors.HexColor("#243B53"))
            c.setFont(font, 6.2)
            detail = f"S{part.stage} {part.value} | {_short_package(part.package, 26)}"
            detail_line = wrap_text(detail, font, 6.2, 55 * mm, max_lines=1)[0]
            c.drawString(box_x + 1.5 * mm, y - 2.3 * mm, detail_line)

    callout_column(left, 8 * mm, 67 * mm, "left")
    callout_column(right, 289 * mm, 230 * mm, "right")
    c.setFillColor(colors.HexColor("#52606D"))
    c.setFont(font, 7.2)
    draw_wrapped(c, font, note, 72 * mm, 15.2 * mm, 153 * mm, 7.0, 3.5 * mm, 2, colors.HexColor("#52606D"))


def draw_overview(builder: PdfBuilder, parts: list[Part], paths: list[list[tuple[float, float]]], board_bounds: tuple[float, float, float, float], zones: list[tuple[str, tuple[float, float, float, float]]]) -> None:
    builder.start_page("顶面总览与分区索引", "顶面视角 | 用后续分区页实际焊接")
    c, font = builder.canvas, builder.font
    map_rect = (12 * mm, 18 * mm, 135 * mm, 166 * mm)
    transform, scale = _mapper(board_bounds, map_rect, False)
    draw_board(c, paths, transform, map_rect)
    for part in [p for p in parts if p.side == "top"]:
        draw_part_marker(c, font, part, transform, scale)
    zone_palette = ["#2563EB", "#7C3AED", "#059669", "#D97706", "#DC2626", "#0891B2"]
    for idx, (name, bounds) in enumerate(zones):
        x0, y0 = transform(bounds[0], bounds[1])
        x1, y1 = transform(bounds[2], bounds[3])
        left, right = sorted([x0, x1])
        bottom, top = sorted([y0, y1])
        color = colors.HexColor(zone_palette[idx % len(zone_palette)])
        c.setStrokeColor(color)
        c.setLineWidth(1.1)
        c.rect(left, bottom, right - left, top - bottom, fill=0, stroke=1)
        c.setFillColor(color)
        c.setFont(font, 6.5)
        c.drawString(left + 1 * mm, top - 3.2 * mm, f"Z{idx + 1} {name}")

    c.setFillColor(colors.HexColor("#F4F7FA"))
    c.roundRect(155 * mm, 18 * mm, 133 * mm, 166 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#102A43"))
    c.setFont(font, 11)
    c.drawString(162 * mm, 174 * mm, "地图阅读方法")
    instructions = [
        "圆点/框 = 封装位置；引线 = 参考标号与元件值/封装。",
        "红色 1 = PCB Pad 1，仅证明板上 Pad 1 在哪里。",
        "[OK] = 方向结论由当前 PCB 数据或受控证据支持。",
        "[CHECK] = 必须用实物丝印/数据手册/供应商料号再确认。",
        "S0-S4 = 安装顺序；红叉 = DNP，不装。",
    ]
    y = 164 * mm
    for line in instructions:
        c.setFillColor(colors.HexColor("#334E68"))
        c.setFont(font, 8.0)
        y = draw_wrapped(c, font, f"- {line}", 163 * mm, y, 118 * mm, 8.0, 4.3 * mm, 2) - 2 * mm
    c.setFillColor(colors.HexColor("#102A43"))
    c.setFont(font, 10)
    c.drawString(162 * mm, y - 1 * mm, "分区页")
    y -= 9 * mm
    for idx, (name, bounds) in enumerate(zones):
        count = sum(p.side == "top" and bounds[0] <= p.x <= bounds[2] and bounds[1] <= p.y <= bounds[3] for p in parts)
        color = colors.HexColor(zone_palette[idx % len(zone_palette)])
        c.setFillColor(color)
        c.circle(165 * mm, y + 1 * mm, 1.7 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#243B53"))
        c.setFont(font, 8.0)
        c.drawString(170 * mm, y - 0.5 * mm, f"Z{idx + 1} {name}: {count} 项")
        y -= 7.5 * mm


def draw_bottom_page(builder: PdfBuilder, bottom_parts: list[Part], paths: list[list[tuple[float, float]]], board_bounds: tuple[float, float, float, float]) -> None:
    builder.start_page("底面定位与尾插方向", "从板底看 | 左右已镜像 | 红点 1 = PCB Pad 1")
    c, font = builder.canvas, builder.font
    full_rect = (10 * mm, 18 * mm, 85 * mm, 166 * mm)
    full_transform, scale = _mapper(board_bounds, full_rect, True)
    draw_board(c, paths, full_transform, full_rect)
    for part in bottom_parts:
        draw_part_marker(c, font, part, full_transform, scale)
    c.setFillColor(colors.HexColor("#52606D"))
    c.setFont(font, 7)
    c.drawCentredString(52.5 * mm, 20 * mm, "底面全板定位")

    if not bottom_parts:
        draw_badge(c, font, 110 * mm, 165 * mm, VERIFIED, "[OK] 当前快照无底面封装")
        return
    xs = [p.x for p in bottom_parts]
    ys = [p.y for p in bottom_parts]
    close_bounds = (min(xs) - 10, min(ys) - 8, max(xs) + 10, max(ys) + 8)
    close_rect = (105 * mm, 94 * mm, 80 * mm, 75 * mm)
    close_transform, close_scale = _mapper(close_bounds, close_rect, True)
    draw_board(c, paths, close_transform, close_rect)
    for part in bottom_parts:
        draw_part_marker(c, font, part, close_transform, close_scale)
        c.setFillColor(colors.HexColor("#102A43"))
        c.setFont(font, 8)
        c.drawCentredString(145 * mm, 88 * mm, f"[CHECK] {part.ref} | {part.value} | rot {part.rotation:.1f} deg")

    part = bottom_parts[0]
    c.setFillColor(colors.HexColor("#F4F7FA"))
    c.roundRect(195 * mm, 18 * mm, 93 * mm, 151 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#102A43"))
    c.setFont(font, 10)
    c.drawString(201 * mm, 159 * mm, f"{part.ref} Pad -> PCB net")
    y = 149 * mm
    c.setFont(font, 8)
    for pad in sorted([p for p in part.pads if p.number not in {"", "MP"}], key=lambda p: (len(p.number), p.number)):
        c.setFillColor(colors.HexColor("#D62828") if pad.number == "1" else colors.HexColor("#334E68"))
        c.drawString(203 * mm, y, f"Pad {pad.number}: {pad.net or '[no net]'}")
        y -= 7 * mm
    y -= 4 * mm
    draw_badge(c, font, 201 * mm, y, TO_CONFIRM)
    y -= 11 * mm
    note = "PCB 只能证明 Pad 号和网络。焊前仍要用收到的连接器料号/图纸确认插口朝向、Pin 1 实物标记与配套线序。"
    draw_wrapped(c, font, note, 201 * mm, y, 81 * mm, 8.0, 4.3 * mm, 8)


def _table_chunks(parts: list[Part], size: int = 16) -> list[tuple[str, list[Part]]]:
    chunks: list[tuple[str, list[Part]]] = []
    for stage in sorted(STAGE_NAMES):
        group = [p for p in parts if p.stage == stage]
        for offset in range(0, len(group), size):
            chunks.append((STAGE_NAMES[stage], group[offset : offset + size]))
    return chunks


def draw_component_table(builder: PdfBuilder, stage_name: str, parts: list[Part]) -> None:
    builder.start_page(f"元件表 | {stage_name}", "坐标、面别、旋转均取自 PCB；方向状态单独判断")
    c, font = builder.canvas, builder.font
    x0, y_top = 8 * mm, 181 * mm
    widths = [45, 34, 45, 21, 21, 21, 27, 75]
    widths = [w * mm for w in widths]
    headers = ["参考标号", "值", "封装", "面", "X / Y mm", "旋转", "状态", "方向/动作"]
    row_h = min(10.3 * mm, 154 * mm / max(len(parts), 1))
    c.setFillColor(colors.HexColor("#D9E2EC"))
    c.rect(x0, y_top - 8 * mm, sum(widths), 8 * mm, fill=1, stroke=0)
    cursor = x0
    c.setFillColor(colors.HexColor("#102A43"))
    c.setFont(font, 7.2)
    for header, width in zip(headers, widths):
        c.drawString(cursor + 1.3 * mm, y_top - 5.2 * mm, header)
        cursor += width
    y = y_top - 8 * mm
    for idx, part in enumerate(parts):
        fill = colors.white if idx % 2 == 0 else colors.HexColor("#F7F9FB")
        c.setFillColor(fill)
        c.rect(x0, y - row_h, sum(widths), row_h, fill=1, stroke=0)
        cursor = x0
        cells = [
            part.ref,
            part.value,
            _short_package(part.package, 42),
            "底" if part.side == "bottom" else "顶",
            f"{part.x:.2f} / {part.y:.2f}",
            f"{part.rotation:.1f} deg",
            "[OK]" if part.orientation_status == VERIFIED else "[CHECK]",
            part.orientation_instruction,
        ]
        for col, (text, width) in enumerate(zip(cells, widths)):
            ink = colors.HexColor("#217A3C") if col == 6 and part.orientation_status == VERIFIED else colors.HexColor("#8A5B00") if col == 6 else colors.HexColor("#243B53")
            draw_wrapped(c, font, text, cursor + 1.2 * mm, y - 3.5 * mm, width - 2.4 * mm, 6.3, 3.1 * mm, 2 if col in {0, 1, 2, 7} else 1, ink)
            cursor += width
        c.setStrokeColor(colors.HexColor("#D9E2EC"))
        c.line(x0, y - row_h, x0 + sum(widths), y - row_h)
        y -= row_h


def draw_checklists(builder: PdfBuilder, ctx: PackageContext) -> None:
    builder.start_page("焊前 / 焊后检查清单", "遇到 [CHECK] 未解决时停下，不凭外观猜方向")
    c, font = builder.canvas, builder.font
    columns = [
        (
            "焊前检查",
            [
                "[ ] 实物板版本/丝印与本包 PCB 快照一致；已记录 SHA256。",
                "[ ] 20 mm 打印标尺实测正确，地图方向按‘从顶/底看’使用。",
                "[ ] 元件值、封装、数量已按 CSV 分装；替代料逐项复核。",
                "[ ] DNP 项保持空焊盘；测试点不误装器件。",
                "[ ] 所有 [CHECK] 已用确切料号数据手册/供应商图纸确认。",
                "[ ] IC/模块/连接器已干装，对齐红色 Pad 1 与机械开口。",
                "[ ] PZT 的每根 SIG/GND 线身份已标记，不凭颜色假定。",
                "[ ] 烙铁、焊锡、助焊剂、ESD 与通风条件已准备。",
            ],
        ),
        (
            "焊后检查(不上电)",
            [
                "[ ] 放大检查少锡、虚焊、连锡、翘脚、错位和反装。",
                "[ ] 用 CSV 逐项点数；DNP 与测试点状态符合预期。",
                "[ ] 再核 LED/二极管/MOS/IC/模块/连接器的 Pin 1/极性。",
                "[ ] 检查电源与 GND 无意外短路；判定阈值按已批准测试规范。",
                "[ ] 检查 PZT SIG/GND 连续性、绝缘和机械应力释放。",
                "[ ] 清洁助焊剂残留并检查细间距焊盘周边。",
            ],
        ),
        (
            "首次上电与记录",
            [
                "[ ] 使用限流电源和已批准的上电步骤，不直接接最终电池试错。",
                "[ ] 在 TP_GND / TP_3V3 / TP_5VSW 测量并记录结果。",
                "[ ] 电压/电流验收范围来自设计测试规范；本包不编造阈值。",
                "[ ] 异常发热、异味或电流超限时立即断电。",
                "[ ] 记录板号、装配人、日期、实测值、返修点与最终结论。",
                "[ ] 通过后再接模块、传感器和电池完成系统测试。",
            ],
        ),
    ]
    for col, (title, items) in enumerate(columns):
        x = (8 + col * 96) * mm
        c.setFillColor(colors.HexColor("#F4F7FA"))
        c.roundRect(x, 22 * mm, 89 * mm, 158 * mm, 2 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#102A43"))
        c.setFont(font, 10.5)
        c.drawString(x + 6 * mm, 169 * mm, title)
        y = 157 * mm
        for item in items:
            y = draw_wrapped(c, font, item, x + 6 * mm, y, 77 * mm, 8.0, 4.4 * mm, 3, colors.HexColor("#334E68")) - 4 * mm
    c.setFillColor(colors.HexColor("#FFF2CC"))
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.roundRect(8 * mm, 13 * mm, 281 * mm, 7 * mm, 1 * mm, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#8A5B00"))
    c.setFont(font, 7.5)
    c.drawCentredString(148.5 * mm, 15.4 * mm, "最终签字表示实物与本快照已核对；本文件不是电气设计验证或替代料批准。")


def write_csv(path: Path, parts: list[Part], source_sha: str) -> None:
    fields = [
        "reference", "value", "package", "side", "x_mm", "y_mm", "rotation_deg",
        "stage", "install", "location_status", "orientation_status", "orientation_instruction",
        "orientation_evidence", "pad1_x_mm", "pad1_y_mm", "pad1_net", "source_sha256",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for part in parts:
            pad1 = part.pad1
            writer.writerow({
                "reference": part.ref,
                "value": part.value,
                "package": part.package,
                "side": part.side,
                "x_mm": f"{part.x:.4f}",
                "y_mm": f"{part.y:.4f}",
                "rotation_deg": f"{part.rotation:.2f}",
                "stage": f"{part.stage} {STAGE_NAMES[part.stage]}",
                "install": part.install,
                "location_status": part.location_status,
                "orientation_status": part.orientation_status,
                "orientation_instruction": part.orientation_instruction,
                "orientation_evidence": part.orientation_evidence,
                "pad1_x_mm": f"{pad1.x:.4f}" if pad1 else "",
                "pad1_y_mm": f"{pad1.y:.4f}" if pad1 else "",
                "pad1_net": pad1.net if pad1 else "",
                "source_sha256": source_sha,
            })


def _find_pdftoppm() -> str | None:
    direct = shutil.which("pdftoppm")
    if direct:
        return direct
    candidate = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/bin/pdftoppm"
    return str(candidate) if candidate.exists() else None


def run_qa(pdf_path: Path, out_dir: Path, expected_pages: int, source_sha: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": "PASS",
        "pdf": str(pdf_path),
        "expected_pages": expected_pages,
        "checks": {},
        "visual_review": "Contact sheet generated; a human/Codex visual inspection is still required.",
    }
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        report["checks"]["page_count"] = {"actual": len(reader.pages), "pass": len(reader.pages) == expected_pages}
        required = ["SmartPaddle", "已验证", "待确认", "顶面", "底面", "焊前", "焊后"]
        missing = [term for term in required if term not in text]
        report["checks"]["required_text"] = {"missing": missing, "pass": not missing}
        sizes = []
        target = PAGE_SIZE
        for page in reader.pages:
            sizes.append((float(page.mediabox.width), float(page.mediabox.height)))
        report["checks"]["a4_landscape"] = {
            "page_sizes_pt": sizes,
            "pass": all(abs(w - target[0]) < 1 and abs(h - target[1]) < 1 for w, h in sizes),
        }
    except Exception as exc:
        report["status"] = "CHECK"
        report["checks"]["pdf_structure"] = {"pass": False, "error": str(exc)}

    renderer = _find_pdftoppm()
    if renderer:
        render_dir = PROJECT_ROOT / "tmp/pdfs/assembly-package" / source_sha[:12]
        render_dir.mkdir(parents=True, exist_ok=True)
        prefix = render_dir / "page"
        for stale_page in render_dir.glob("page-*.png"):
            stale_page.unlink()
        subprocess.run([renderer, "-r", "120", "-png", str(pdf_path), str(prefix)], check=True)
        pngs = sorted(render_dir.glob("page-*.png"))
        report["checks"]["rendered_pages"] = {"actual": len(pngs), "pass": len(pngs) == expected_pages}
        try:
            from PIL import Image, ImageOps, ImageStat

            thumbs = []
            nonblank = []
            for png in pngs:
                image = Image.open(png).convert("RGB")
                stat = ImageStat.Stat(ImageOps.grayscale(image))
                nonblank.append(stat.var[0] > 20)
                image.thumbnail((390, 275))
                framed = ImageOps.expand(image, border=2, fill="#64748B")
                thumbs.append(framed)
            cols = 3
            rows = math.ceil(len(thumbs) / cols)
            cell_w = max(i.width for i in thumbs) + 12
            cell_h = max(i.height for i in thumbs) + 12
            sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
            for idx, thumb in enumerate(thumbs):
                sheet.paste(thumb, ((idx % cols) * cell_w + 6, (idx // cols) * cell_h + 6))
            sheet.save(out_dir / CONTACT_NAME, optimize=True)
            report["checks"]["nonblank_pages"] = {"pass": all(nonblank), "values": nonblank}
            report["contact_sheet"] = str(out_dir / CONTACT_NAME)
            report["render_dir"] = str(render_dir)
        except Exception as exc:
            report["status"] = "CHECK"
            report["checks"]["contact_sheet"] = {"pass": False, "error": str(exc)}
    else:
        report["status"] = "CHECK"
        report["checks"]["rendered_pages"] = {"pass": False, "error": "pdftoppm not found"}

    if any(isinstance(value, dict) and value.get("pass") is False for value in report["checks"].values()):
        report["status"] = "CHECK"
    (out_dir / QA_NAME).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def write_readme(path: Path, ctx: PackageContext, parts: list[Part], qa: dict[str, Any] | None) -> None:
    text = f"""# SmartPaddle assembly package

Generated from the exact read-only PCB snapshot below. Do not mix this package with older V3 assembly drawings.

- PCB: `{ctx.source_path}`
- SHA256: `{ctx.source_sha256}`
- Git commit: `{ctx.git_commit or '[unknown]'}`
- PCB title-block revision: `{ctx.board_revision or '[missing - confirm against the physical board]'}`
- Footprints: {len(parts)}
- Orientation VERIFIED: {sum(p.orientation_status == VERIFIED for p in parts)}
- Orientation TO_CONFIRM: {sum(p.orientation_status == TO_CONFIRM for p in parts)}
- QA: {(qa or {}).get('status', 'not run')}

Files:

- `{PDF_NAME}`: A4 landscape printable assembly maps, tables, and checklists.
- `{CSV_NAME}`: source-auditable placement and status table.
- `{MANIFEST_NAME}`: source hash, warnings, and machine-readable metadata.
- `{QA_NAME}`: structural/render checks when `--qa` is used.
- `{CONTACT_NAME}`: rendered contact sheet when Poppler and Pillow are available.

Regenerate from the project root with:

```bash
./steps/assembly-package.sh "板子到手了，生成可打印焊接装配包"
```

The quoted sentence is accepted as a human-readable invocation note. It does not change source data.
"""
    path.write_text(text, encoding="utf-8")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("invocation", nargs="?", help="Optional human-readable one-sentence invocation note")
    parser.add_argument("--pcb", type=Path, default=DEFAULT_PCB, help="Read-only KiCad PCB source")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Independent output directory")
    parser.add_argument("--qa", action="store_true", help="Render and structurally inspect the PDF")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    pcb_path = args.pcb.resolve()
    out_dir = args.out.resolve()
    source_bytes = pcb_path.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    board = parse_sexpr(source_bytes.decode("utf-8"))
    parts = extract_parts(board)
    apply_evidence(parts, EVIDENCE_PATH)
    paths = extract_edge_paths(board)
    bounds = _board_bounds(paths)
    title, revision = board_metadata(board)
    relative_source = str(pcb_path.relative_to(PROJECT_ROOT)) if pcb_path.is_relative_to(PROJECT_ROOT) else str(pcb_path)
    legacy_count = legacy_component_count()
    git_status = _run_git(["status", "--porcelain", "--", relative_source])
    warnings: list[str] = []
    if not revision:
        warnings.append("PCB title-block revision is missing; confirm the physical board identity before soldering.")
    if git_status:
        warnings.append("PCB source has uncommitted changes; this package is a design snapshot, not a released board revision.")
    if legacy_count is not None and legacy_count != len(parts):
        warnings.append(f"Legacy V3 package has {legacy_count} rows but this snapshot has {len(parts)} footprints; do not mix them.")
    build_bom = PROJECT_ROOT / "pcb/build/builds/default/default.bom.csv"
    if not build_bom.exists() or build_bom.stat().st_size == 0:
        warnings.append("Current build BOM is empty/missing; quantities come from PCB footprint instances and supplier MPNs are unverified.")
    if any(p.orientation_status == TO_CONFIRM for p in parts):
        warnings.append("Some polarity/orientation items need exact received-part datasheets or supplier drawings.")
    ctx = PackageContext(
        source_path=relative_source,
        source_sha256=source_sha,
        generated_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        git_commit=_run_git(["rev-parse", "--short", "HEAD"]),
        git_dirty=bool(git_status),
        board_title=title,
        board_revision=revision,
        legacy_count=legacy_count,
        warnings=warnings,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    font = register_font()

    zones = [
        ("拍头上沿 PZT TL/TR", (-45, -63, 45, -40)),
        ("核心上半 模拟/电源", (-25, -38, 25, -15)),
        ("核心下半 MCU/ADC", (-25, -16, 4, 20)),
        ("核心下半 电源控制", (3, -16, 24, 20)),
        ("拍头下沿 PZT BL/BR", (-45, 20, 45, 41)),
        ("拍柄 开关/尾插", (-22, 40, 22, 96)),
    ]
    top_parts = [p for p in parts if p.side == "top"]
    bottom_parts = [p for p in parts if p.side == "bottom"]
    zone_parts = [
        [p for p in top_parts if b[0] <= p.x <= b[2] and b[1] <= p.y <= b[3]]
        for _, b in zones
    ]
    table_chunks = _table_chunks(parts)
    total_pages = 1 + 1 + len(zones) + 1 + len(table_chunks) + 1
    pdf_path = out_dir / PDF_NAME
    builder = PdfBuilder(pdf_path, font, total_pages, ctx)
    draw_cover(builder, parts, ctx)
    draw_overview(builder, parts, paths, bounds, zones)
    for (name, zone_bounds), local_parts in zip(zones, zone_parts):
        note = "先按参考标号和值定位，再看状态；[CHECK] 项必须查实物标记。红点 1 仅代表 PCB Pad 1。"
        draw_map_page(builder, f"顶面分区 | {name}", note, local_parts, paths, zone_bounds, "top", False)
    draw_bottom_page(builder, bottom_parts, paths, bounds)
    for stage_name, chunk in table_chunks:
        draw_component_table(builder, stage_name, chunk)
    draw_checklists(builder, ctx)
    builder.finish()

    ctx.current_at_finish = hashlib.sha256(pcb_path.read_bytes()).hexdigest() == source_sha
    if not ctx.current_at_finish:
        ctx.warnings.append("PCB source changed while the package was generated; regenerate before use.")
    write_csv(out_dir / CSV_NAME, parts, source_sha)

    manifest = {
        "schema_version": 1,
        "package_status": TO_CONFIRM if warnings else VERIFIED,
        "invocation": args.invocation or "",
        "context": asdict(ctx),
        "counts": {
            "footprints": len(parts),
            "top": len(top_parts),
            "bottom": len(bottom_parts),
            "place": sum(p.install == "PLACE" for p in parts),
            "dnp": sum(p.install == "DNP" for p in parts),
            "inspect_only": sum(p.install == "INSPECT" for p in parts),
            "orientation_verified": sum(p.orientation_status == VERIFIED for p in parts),
            "orientation_to_confirm": sum(p.orientation_status == TO_CONFIRM for p in parts),
            "pdf_pages": total_pages,
        },
        "source_policy": {
            "location_value_package_side_rotation": "Extracted from exact PCB snapshot",
            "pad1_and_net": "Extracted from exact PCB snapshot",
            "orientation": "Conservative classifier plus source-gated orientation_evidence.json",
            "unknowns": "Marked TO_CONFIRM; never inferred from old coordinates or undocumented polarity notes",
        },
        "outputs": {
            "pdf": PDF_NAME,
            "csv": CSV_NAME,
            "qa": QA_NAME if args.qa else None,
            "contact_sheet": CONTACT_NAME if args.qa else None,
        },
    }
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    qa = run_qa(pdf_path, out_dir, total_pages, source_sha) if args.qa else None
    write_readme(out_dir / "README.md", ctx, parts, qa)
    print(f"PDF: {pdf_path}")
    print(f"CSV: {out_dir / CSV_NAME}")
    print(f"Manifest: {out_dir / MANIFEST_NAME}")
    if qa:
        print(f"QA: {qa['status']} ({out_dir / QA_NAME})")
    print(f"footprints={len(parts)} top={len(top_parts)} bottom={len(bottom_parts)} pages={total_pages} sha256={source_sha[:16]}...")
    if not ctx.current_at_finish:
        print("ERROR: PCB changed during generation; regenerate before use.", file=sys.stderr)
        return 3
    return 0 if not qa or qa.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
