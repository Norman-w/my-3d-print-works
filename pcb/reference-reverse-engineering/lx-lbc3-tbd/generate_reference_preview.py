#!/usr/bin/env python3
"""Generate the isolated LX-LBC3 reference-reverse-engineering preview.

This script intentionally creates no nets, tracks, vias, or copper zones.  Its
only purpose is to make the photograph-derived mechanical inventory visible in
KiCad 2D/3D.  It must be run with KiCad 9's bundled Python.
"""

from __future__ import annotations

import math
from pathlib import Path

import wx

# KiCad 9's pcbnew bindings require a wx application even for headless board
# creation.  Without it, macOS aborts in stdpbase before any file is written.
WX_APP = wx.App(False)

import pcbnew  # noqa: E402
from layout_spec import (  # noqa: E402
    BOARD_H,
    BOARD_W,
    PLACEMENTS,
    VISUAL_MARKER_EDGE,
    body_bounds,
    top_side_collisions,
)


HERE = Path(__file__).resolve().parent
FP_DIR = HERE / "footprints.pretty"
MODEL_DIR = HERE / "models"
BOARD_PATH = HERE / "lx-lbc3-reference-tbd.kicad_pcb"
OUTPUT_DIR = HERE / "output"
KICAD_ROOT = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")

OX = 100.0
OY = 100.0


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def xy(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def fmt(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


PIXEL_FONT_3X5 = {
    "2": ("111", "001", "111", "100", "111"),
    "C": ("111", "100", "100", "100", "111"),
    "E": ("111", "100", "110", "100", "111"),
    "J": ("111", "001", "001", "101", "111"),
    "N": ("101", "111", "111", "111", "101"),
    "R": ("110", "101", "110", "101", "101"),
}


def vrml_box(
    size_mm: tuple[float, float, float],
    center_mm: tuple[float, float, float],
    color: tuple[float, float, float],
) -> list[str]:
    """Return one VRML box node in KiCad's 2.54 mm/unit convention."""
    sx, sy, sz = (value / 2.54 for value in size_mm)
    tx, ty, tz = (value / 2.54 for value in center_mm)
    return [
        "Transform {",
        f"  translation {fmt(tx)} {fmt(ty)} {fmt(tz)}",
        "  children [",
        "    Shape {",
        "      appearance Appearance {",
        f"        material Material {{ diffuseColor {fmt(color[0])} {fmt(color[1])} {fmt(color[2])} }}",
        "      }",
        f"      geometry Box {{ size {fmt(sx)} {fmt(sy)} {fmt(sz)} }}",
        "    }",
        "  ]",
        "}",
    ]


def pixel_label_nodes(
    text: str,
    pixel_mm: float,
    z_mm: float,
    color: tuple[float, float, float],
    rotation_degrees: float = 0.0,
    underline_last: bool = False,
) -> list[str]:
    """Build a small extruded 3x5 label without relying on VRML font support."""
    pitch = pixel_mm * 1.35
    glyph_pitch = pitch * 4
    total_width = glyph_pitch * len(text) - pitch
    total_height = pitch * 5
    angle = math.radians(rotation_degrees)
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)
    nodes: list[str] = []

    def add_pixel(x: float, y: float, width: float = pixel_mm, height: float = pixel_mm) -> None:
        rotated_x = x * cos_angle - y * sin_angle
        rotated_y = x * sin_angle + y * cos_angle
        nodes.extend(vrml_box((width, height, 0.035), (rotated_x, rotated_y, z_mm), color))

    for glyph_index, glyph in enumerate(text):
        pattern = PIXEL_FONT_3X5[glyph]
        glyph_x = -total_width / 2 + glyph_index * glyph_pitch
        for row_index, row in enumerate(pattern):
            for column_index, enabled in enumerate(row):
                if enabled == "1":
                    x = glyph_x + column_index * pitch
                    y = total_height / 2 - row_index * pitch
                    add_pixel(x, y)

    if underline_last:
        glyph_x = -total_width / 2 + (len(text) - 1) * glyph_pitch
        underline_x = glyph_x + pitch
        underline_y = -total_height / 2 - pitch * 0.38
        # Build the underline in label coordinates, then rotate with the text.
        rotated_x = underline_x * cos_angle - underline_y * sin_angle
        rotated_y = underline_x * sin_angle + underline_y * cos_angle
        if round(rotation_degrees) % 180 == 90:
            size = (pixel_mm * 0.42, pitch * 3.0, 0.035)
        else:
            size = (pitch * 3.0, pixel_mm * 0.42, 0.035)
        nodes.extend(vrml_box(size, (rotated_x, rotated_y, z_mm), color))
    return nodes


def write_vrml_scene(path: Path, nodes: list[str]) -> None:
    path.write_text("\n".join(["#VRML V2.0 utf8", *nodes, ""]), encoding="utf-8")


def write_box_wrl(path: Path, size_mm: tuple[float, float, float], color: tuple[float, float, float]) -> None:
    """Write a simple KiCad-scaled VRML box (1 VRML unit = 2.54 mm)."""
    write_vrml_scene(path, vrml_box(size_mm, (0.0, 0.0, size_mm[2] / 2), color))


def generate_models() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    write_box_wrl(MODEL_DIR / "usb_c_6p_reference.wrl", (7.60, 8.90, 3.0), (0.64, 0.67, 0.70))
    inductor_nodes = vrml_box((4.0, 4.0, 2.2), (0.0, 0.0, 1.1), (0.38, 0.39, 0.36))
    inductor_nodes.extend(pixel_label_nodes("2R2", 0.20, 2.22, (0.08, 0.08, 0.07), 180.0))
    write_vrml_scene(MODEL_DIR / "inductor_wound_4x4_tbd.wrl", inductor_nodes)

    u1_nodes = vrml_box((1.8, 3.0, 1.0), (0.0, 0.0, 0.5), (0.055, 0.055, 0.055))
    u1_nodes.extend(pixel_label_nodes("JNEC", 0.105, 1.02, (0.78, 0.78, 0.73), -90.0, True))
    # Local (-x,+y) becomes board-view lower-left after U1's 90-degree placement.
    u1_nodes.extend(vrml_box((0.18, 0.18, 0.035), (-0.56, 1.16, 1.02), (0.78, 0.78, 0.73)))
    write_vrml_scene(MODEL_DIR / "u1_jnec_observed.wrl", u1_nodes)

    r4_mark_nodes = [
        *vrml_box((0.50, 0.07, 0.03), (0.0, -0.20, 0.58), (0.82, 0.82, 0.78)),
        *vrml_box((0.50, 0.07, 0.03), (0.0, 0.20, 0.58), (0.82, 0.82, 0.78)),
        *vrml_box((0.07, 0.47, 0.03), (-0.215, 0.0, 0.58), (0.82, 0.82, 0.78)),
        *vrml_box((0.07, 0.47, 0.03), (0.215, 0.0, 0.58), (0.82, 0.82, 0.78)),
    ]
    write_vrml_scene(MODEL_DIR / "r4_square_or_zero_mark.wrl", r4_mark_nodes)

    led_mark_nodes = vrml_box((0.34, 0.56, 0.035), (-0.48, 0.0, 0.72), (0.08, 0.70, 0.27))
    write_vrml_scene(MODEL_DIR / "led_green_observed_end.wrl", led_mark_nodes)


def generate_measurement_map() -> None:
    """Write a scale-true SVG audit map of every visible component envelope."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    colors = {
        "J": "#94a3b8",
        "R": "#f59e0b",
        "C": "#d97706",
        "D": "#22c55e",
        "L": "#64748b",
        "U": "#111827",
    }
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="950" viewBox="-4.8 -1.6 22.4 15.2">',
        '<rect x="-4.8" y="-1.6" width="22.4" height="15.2" fill="#f8fafc"/>',
        '<rect x="0" y="0" width="16" height="12" rx="0.25" fill="#e2e8f0" stroke="#0f172a" stroke-width="0.08"/>',
        '<g font-family="monospace" font-size="0.42" text-anchor="middle">',
    ]
    for ref, placement in PLACEMENTS.items():
        if placement.bottom:
            continue
        left, right, top, bottom = body_bounds(ref)
        width = right - left
        height = bottom - top
        color = colors.get(ref[0], "#64748b")
        lines.append(
            f'<rect x="{fmt(left)}" y="{fmt(top)}" width="{fmt(width)}" '
            f'height="{fmt(height)}" rx="0.08" fill="{color}" fill-opacity="0.58" '
            'stroke="#0f172a" stroke-width="0.05"/>'
        )
        if ref not in {"J1", "J4", "J5", "L1", "U1", "R4"}:
            if width >= height:
                x1, y1, x2, y2 = left + width * 0.18, placement.y, right - width * 0.18, placement.y
            else:
                x1, y1, x2, y2 = placement.x, top + height * 0.18, placement.x, bottom - height * 0.18
            lines.append(
                f'<line x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" '
                'stroke="#ffffff" stroke-width="0.09" stroke-linecap="round"/>'
            )
        marker_edge = VISUAL_MARKER_EDGE.get(ref)
        if marker_edge:
            marker_y = top + 0.16 if marker_edge == "top" else bottom - 0.16
            lines.append(
                f'<circle cx="{fmt(placement.x)}" cy="{fmt(marker_y)}" r="0.11" '
                'fill="#14532d" stroke="#ffffff" stroke-width="0.035"/>'
            )
        text_color = "#ffffff" if ref.startswith(("U", "L")) else "#0f172a"
        if ref == "L1":
            lines.append(
                f'<text x="{fmt(placement.x)}" y="{fmt(placement.y + 0.15)}" '
                f'fill="{text_color}" transform="rotate(180 {fmt(placement.x)} {fmt(placement.y)})">2R2</text>'
            )
        elif ref == "U1":
            lines.append(
                f'<text x="{fmt(placement.x)}" y="{fmt(placement.y + 0.14)}" '
                'fill="#ffffff">JNE<tspan text-decoration="underline">C</tspan></text>'
            )
            lines.append(
                f'<circle cx="{fmt(left + 0.24)}" cy="{fmt(bottom - 0.24)}" r="0.10" fill="#d6d3d1"/>'
            )
        elif ref == "R4":
            lines.append(
                f'<rect x="{fmt(placement.x - 0.18)}" y="{fmt(placement.y - 0.18)}" '
                'width="0.36" height="0.36" fill="none" stroke="#ffffff" stroke-width="0.07"/>'
            )
        else:
            lines.append(
                f'<text x="{fmt(placement.x)}" y="{fmt(placement.y + 0.14)}" '
                f'fill="{text_color}">{ref}</text>'
            )
    lines.extend(
        [
            "</g>",
            '<g font-family="sans-serif" fill="#0f172a">',
            '<text x="8" y="-0.65" font-size="0.52" text-anchor="middle">PHOTO-CALIBRATED TOP — 16 × 12 mm — TYPE-C LEFT</text>',
            '<text x="8" y="12.85" font-size="0.38" text-anchor="middle">body/axis replicated; dark LED dot = photographed coloured end, not asserted electrical polarity</text>',
            "</g>",
            "</svg>",
            "",
        ]
    )
    (OUTPUT_DIR / "photo_calibrated_layout.svg").write_text("\n".join(lines), encoding="utf-8")


def generate_footprints() -> None:
    FP_DIR.mkdir(parents=True, exist_ok=True)
    usb_lines = [
        '(footprint "USB_C_6P_POWER_ONLY_TBD"',
        '  (version 20240108)',
        '  (generator "generate_reference_preview.py")',
        '  (layer "F.Cu")',
        '  (descr "REFERENCE REVERSE ENGINEERING ONLY; approximate 6-pad power-only Type-C; pinout TBD")',
        '  (tags "reference-reverse-engineering TBD Type-C 6P power-only")',
        '  (attr smd)',
        '  (fp_text reference "REF**" (at 0 -5.5) (layer "F.SilkS") hide',
        '    (effects (font (size 0.8 0.8) (thickness 0.12))))',
        '  (fp_text value "USB-C_6P_POWER_ONLY_TBD" (at 0 5.5) (layer "F.Fab")',
        '    (effects (font (size 0.6 0.6) (thickness 0.1))))',
        '  (fp_rect (start -4.05 -4.45) (end 3.55 4.45)',
        '    (stroke (width 0.12) (type solid)) (fill none) (layer "F.Fab"))',
        '  (fp_rect (start -4.12 -4.52) (end 3.62 4.52)',
        '    (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))',
        '  (fp_text user "6P / NO D+ D-" (at -0.3 0 90) (layer "F.SilkS")',
        '    (effects (font (size 0.45 0.45) (thickness 0.08))))',
    ]
    for number, y_pos in enumerate((-3.25, -2.0, -0.7, 0.7, 2.0, 3.25), 1):
        usb_lines.append(
            f'  (pad "{number}" smd roundrect (at 3.75 {fmt(y_pos)}) '
            '(size 1.15 0.85) (layers "F.Cu" "F.Paste" "F.Mask") '
            '(roundrect_rratio 0.2))'
        )
    for name, x_pos, y_pos in (
        ("SH1", -0.75, -4.05),
        ("SH2", 3.05, -4.05),
        ("SH3", -0.75, 4.05),
        ("SH4", 3.05, 4.05),
    ):
        usb_lines.append(
            f'  (pad "{name}" thru_hole oval (at {fmt(x_pos)} {fmt(y_pos)}) '
            '(size 1.6 2.0) (drill oval 0.8 1.2) (layers "*.Cu" "*.Mask"))'
        )
    usb_lines.extend(
        [
            '  (model "${KIPRJMOD}/models/usb_c_6p_reference.wrl"',
            '    (offset (xyz -0.25 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))',
            ')',
            '',
        ]
    )
    (FP_DIR / "USB_C_6P_POWER_ONLY_TBD.kicad_mod").write_text(
        "\n".join(usb_lines), encoding="utf-8"
    )

    inductor = """(footprint "Inductor_Wound_4x4_TBD"
  (version 20240108)
  (generator "generate_reference_preview.py")
  (layer "F.Cu")
  (descr "REFERENCE REVERSE ENGINEERING ONLY; approximate 4x4 mm power inductor")
  (tags "reference-reverse-engineering TBD inductor")
  (attr smd)
  (fp_text reference "REF**" (at 0 -2.8) (layer "F.SilkS")
    (effects (font (size 0.7 0.7) (thickness 0.11))))
  (fp_text value "L_TBD" (at 0 2.8) (layer "F.Fab")
    (effects (font (size 0.6 0.6) (thickness 0.1))))
  (fp_rect (start -2 -2) (end 2 2)
    (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))
  (fp_rect (start -2 -2) (end 2 2)
    (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
  (pad "1" smd roundrect (at -1.55 0) (size 1.2 3.4)
    (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.18))
  (pad "2" smd roundrect (at 1.55 0) (size 1.2 3.4)
    (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.18))
  (model "${KIPRJMOD}/models/inductor_wound_4x4_tbd.wrl"
    (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
)
"""
    (FP_DIR / "Inductor_Wound_4x4_TBD.kicad_mod").write_text(
        inductor, encoding="utf-8"
    )

    wire_pad = """(footprint "WirePad_2p4mm_TBD"
  (version 20240108)
  (generator "generate_reference_preview.py")
  (layer "F.Cu")
  (descr "REFERENCE REVERSE ENGINEERING ONLY; approximate photographed wire pad")
  (tags "reference-reverse-engineering TBD wire pad")
  (attr smd)
  (fp_text reference "REF**" (at 0 -1.8) (layer "F.SilkS")
    (effects (font (size 0.65 0.65) (thickness 0.1))))
  (fp_text value "PAD_TBD" (at 0 1.8) (layer "F.Fab")
    (effects (font (size 0.55 0.55) (thickness 0.08))))
  (fp_circle (center 0 0) (end 1.25 0)
    (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
  (pad "1" smd roundrect (at 0 0) (size 2.4 2.4)
    (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.35))
)
"""
    (FP_DIR / "WirePad_2p4mm_TBD.kicad_mod").write_text(
        wire_pad, encoding="utf-8"
    )


def load_fp(library: Path, name: str) -> pcbnew.FOOTPRINT:
    footprint = pcbnew.FootprintLoad(str(library), name)
    if footprint is None:
        raise RuntimeError(f"cannot load footprint {library}:{name}")
    return footprint


def add_fp(
    board: pcbnew.BOARD,
    library: Path,
    name: str,
    ref: str,
    value: str,
    x_mm: float,
    y_mm: float,
    rotation: float = 0.0,
    bottom: bool = False,
) -> pcbnew.FOOTPRINT:
    footprint = load_fp(library, name)
    footprint.SetReference(ref)
    footprint.SetValue(value)
    footprint.Reference().SetVisible(False)
    position = xy(OX + x_mm, OY + y_mm)
    footprint.SetPosition(position)
    footprint.SetOrientationDegrees(rotation)
    footprint.SetParent(board)
    board.Add(footprint)
    if bottom:
        # KiCad 9 requires a footprint to belong to a board before Flip().
        footprint.Flip(position, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    return footprint


def attach_model(footprint: pcbnew.FOOTPRINT, filename: str, replace: bool = False) -> None:
    """Attach a project-local visual marking/body model to a footprint."""
    models = footprint.Models()
    if replace:
        models.clear()
    model = pcbnew.FP_3DMODEL()
    model.m_Filename = f"${{KIPRJMOD}}/models/{filename}"
    model.m_Offset = pcbnew.VECTOR3D(0.0, 0.0, 0.0)
    model.m_Scale = pcbnew.VECTOR3D(1.0, 1.0, 1.0)
    model.m_Rotation = pcbnew.VECTOR3D(0.0, 0.0, 0.0)
    model.m_Opacity = 1.0
    model.m_Show = True
    models.append(model)


def add_text(
    board: pcbnew.BOARD,
    text: str,
    x_mm: float,
    y_mm: float,
    size_mm: float = 0.55,
    layer: int = pcbnew.F_SilkS,
    angle: float = 0.0,
) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetLayer(layer)
    item.SetPosition(xy(OX + x_mm, OY + y_mm))
    item.SetTextHeight(mm(size_mm))
    item.SetTextWidth(mm(size_mm))
    item.SetTextThickness(mm(max(0.08, size_mm * 0.14)))
    item.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
    board.Add(item)


def add_outline(board: pcbnew.BOARD) -> None:
    # Photo-derived top/bottom notches near the connector are approximated with
    # line segments.  The 16x12 mm envelope is the only published dimension.
    top_notch = [
        (2.10, 0.00),
        (2.16, 0.28),
        (2.35, 0.52),
        (2.62, 0.67),
        (2.90, 0.70),
        (3.18, 0.62),
        (3.40, 0.42),
        (3.50, 0.00),
    ]
    bottom_notch = [(x, BOARD_H - y) for x, y in reversed(top_notch)]
    points = [
        (0.45, 0.00),
        *top_notch,
        (15.55, 0.00),
        (16.00, 0.45),
        (16.00, 11.55),
        (15.55, 12.00),
        *bottom_notch,
        (0.45, 12.00),
        (0.00, 11.55),
        (0.00, 0.45),
        (0.45, 0.00),
    ]
    for start, end in zip(points, points[1:]):
        segment = pcbnew.PCB_SHAPE(board)
        segment.SetShape(pcbnew.SHAPE_T_SEGMENT)
        segment.SetStart(xy(OX + start[0], OY + start[1]))
        segment.SetEnd(xy(OX + end[0], OY + end[1]))
        segment.SetLayer(pcbnew.Edge_Cuts)
        segment.SetWidth(mm(0.05))
        board.Add(segment)


def build_board() -> pcbnew.BOARD:
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    add_outline(board)

    resistor_lib = KICAD_ROOT / "Resistor_SMD.pretty"
    capacitor_lib = KICAD_ROOT / "Capacitor_SMD.pretty"
    led_lib = KICAD_ROOT / "LED_SMD.pretty"
    package_lib = KICAD_ROOT / "Package_TO_SOT_SMD.pretty"

    def place(
        library: Path,
        name: str,
        ref: str,
        value: str,
    ) -> pcbnew.FOOTPRINT:
        placement = PLACEMENTS[ref]
        return add_fp(
            board,
            library,
            name,
            ref,
            value,
            placement.x,
            placement.y,
            placement.rotation,
            placement.bottom,
        )

    place(FP_DIR, "USB_C_6P_POWER_ONLY_TBD", "J1", "USB-C_6P_POWER_ONLY_TBD")
    place(resistor_lib, "R_0402_1005Metric", "R1", "CC_OR_CFG_TBD")
    place(resistor_lib, "R_0402_1005Metric", "R2", "CC_OR_CFG_TBD")
    place(capacitor_lib, "C_0603_1608Metric", "C1", "C_TBD")
    r4 = place(resistor_lib, "R_0603_1608Metric", "R4", "SQUARE_OR_ZERO_MARK_TBD")
    attach_model(r4, "r4_square_or_zero_mark.wrl")
    place(FP_DIR, "Inductor_Wound_4x4_TBD", "L1", "L_TBD_2u2_TO_4u7_CANDIDATE")
    u1 = place(package_lib, "SOT-23-6", "U1", "PMIC_JNEC_MARK_TBD")
    attach_model(u1, "u1_jnec_observed.wrl", replace=True)
    d1 = place(led_lib, "LED_0603_1608Metric", "D1", "LED_GREEN_END_DOWN_TBD_POLARITY")
    attach_model(d1, "led_green_observed_end.wrl")
    d2 = place(led_lib, "LED_0603_1608Metric", "D2", "LED_GREEN_END_UP_TBD_POLARITY")
    attach_model(d2, "led_green_observed_end.wrl")
    place(resistor_lib, "R_0402_1005Metric", "R3", "LED_OR_CFG_TBD")
    place(capacitor_lib, "C_0603_1608Metric", "C3", "C_TBD_BETWEEN_B_PADS")
    place(FP_DIR, "WirePad_2p4mm_TBD", "J4", "B-_PHOTO_LABEL")
    place(FP_DIR, "WirePad_2p4mm_TBD", "J5", "B+_PHOTO_LABEL")
    place(FP_DIR, "WirePad_2p4mm_TBD", "J2", "5V-_PHOTO_LABEL_NET_TBD")
    place(FP_DIR, "WirePad_2p4mm_TBD", "J3", "5V+_PHOTO_LABEL_NET_TBD")

    # Stock references are hidden. Concise labels sit in measured empty areas
    # so the reference drawing does not obscure or appear to merge components.
    add_text(board, "6P", 4.30, 6.00, 0.38, angle=90.0)
    add_text(board, "L1", 12.65, 3.10, 0.38)
    add_text(board, "U1?", 10.34, 8.85, 0.38)
    add_text(board, "D1", 8.63, 11.48, 0.34)
    add_text(board, "D2", 10.51, 11.48, 0.34)
    add_text(board, "R3", 12.66, 11.48, 0.34)
    add_text(board, "B+", 13.55, 1.90, 0.62)
    add_text(board, "B-", 13.55, 10.10, 0.62)
    add_text(board, "5V- TBD", 2.7, 2.3, 0.55, pcbnew.B_SilkS)
    add_text(board, "5V+ TBD", 2.7, 9.7, 0.55, pcbnew.B_SilkS)
    add_text(board, "PHOTO CAL / TBD / NO NETS", 8.7, 0.58, 0.35, pcbnew.B_SilkS)

    # A visual-only title block on Dwgs.User stays out of fabrication layers.
    add_text(board, "LX-LBC3 REFERENCE REVERSE ENGINEERING", 8.0, -1.4, 0.8, pcbnew.Dwgs_User)
    add_text(board, "16x12 mm envelope; photo-calibrated placement; electrical nets TBD", 8.0, -0.4, 0.48, pcbnew.Dwgs_User)
    return board


def main() -> int:
    if not KICAD_ROOT.is_dir():
        raise SystemExit(f"KiCad footprint root not found: {KICAD_ROOT}")
    collisions = top_side_collisions()
    if collisions:
        raise SystemExit(f"photo layout contains overlapping body envelopes: {collisions}")
    generate_models()
    generate_measurement_map()
    generate_footprints()
    board = build_board()
    pcbnew.SaveBoard(str(BOARD_PATH), board)

    named_nets = [str(name) for name in board.GetNetInfo().NetsByName().keys() if str(name)]
    if named_nets:
        raise SystemExit(f"unsafe reference board: named nets were generated: {named_nets}")
    if len(list(board.GetTracks())) != 0:
        raise SystemExit("unsafe reference board: tracks/vias were generated")
    if board.GetAreaCount() != 0:
        raise SystemExit("unsafe reference board: copper zones were generated")
    print(f"wrote {BOARD_PATH}")
    print(f"footprints={len(list(board.GetFootprints()))} named_nets=0 tracks=0 zones=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
