#!/usr/bin/env python3
"""Generate the exact H=5.8 short-pin 16P vertical Type-C land pattern.

Only what the recommended PCB shows: 16 SMT pads + 2 oval slots + courtyard/silk.
No decorative 'mouth' oval through the pads (that was misleading).

Primary source:
  docs/usb-c-vertical-16p-short/Type-C-16PIN-vertical-H5.8-short-datasheet.pdf
  page 1, "16P立贴PCB板焊盘位置图"

  0.43×1.40 pads, P0.78, span 5.46, row outer span 3.70
  oval slots 0.50×1.25, centers 8.68, outer copper R0.40
  F.Fab / F.CrtYd concentric around copper (same aspect)

  python3 pcb-tail/scripts/gen_usb_16p_vert_smt_fp.py
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import uuid
from pathlib import Path


# ===== 分区：常量/配置 =====
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "lib" / "footprints.pretty" / "USB_C_Receptacle_16P_Vertical_SMT_Short.kicad_mod"
PREVIEW = HERE.parent / "layouts" / "default" / "export-preview" / "fp-usb16p-selfcheck.png"
DATASHEET_PDF = (
    HERE.parents[1]
    / "docs"
    / "usb-c-vertical-16p-short"
    / "Type-C-16PIN-vertical-H5.8-short-datasheet.pdf"
)
DATASHEET_DETAIL = (
    HERE.parents[1]
    / "docs"
    / "usb-c-vertical-16p-short"
    / "Type-C-16PIN-vertical-H5.8-short-footprint-detail.png"
)
NAME = "USB_C_Receptacle_16P_Vertical_SMT_Short"

PAD_W = 0.43
PAD_H = 1.40
PITCH = 0.78
SPAN = 5.46
ROW_OUTER_SPAN = 3.70
SLOT_W = 0.50
SLOT_H = 1.25
SLOT_SPAN = 8.68
SLOT_PAD_W = 0.80  # PDF outer copper radius R0.40
SLOT_PAD_H = 1.55  # same 0.15 mm annulus and straight section as the slot
FAB_CLEAR = 0.10
CRT_CLEAR = 0.25

ROW_C2C = ROW_OUTER_SPAN - PAD_H
ROW_EDGE_GAP = ROW_C2C - PAD_H
YA = -ROW_C2C / 2.0
YB = ROW_C2C / 2.0
XS = [-SPAN / 2.0 + i * PITCH for i in range(8)]
SLOT_X = SLOT_SPAN / 2.0
# Fab / courtyard both hug copper (same center & aspect) — no separate mismatched shell box
COPPER_W = 2 * (SLOT_X + SLOT_PAD_W / 2)
COPPER_D = ROW_OUTER_SPAN
FAB_W = COPPER_W + 2 * FAB_CLEAR
FAB_D = COPPER_D + 2 * FAB_CLEAR
CRT_W = FAB_W + 2 * CRT_CLEAR
CRT_D = FAB_D + 2 * CRT_CLEAR

A_PADS = ["A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12"]
B_PADS = ["B12", "B9", "B8", "B7", "B6", "B5", "B4", "B1"]
SHIELD_PAD = "S1"
_UID_INDEX = 0


# ===== 分区：私有成员 =====
def _uid() -> str:
    global _UID_INDEX
    value = uuid.uuid5(uuid.NAMESPACE_URL, f"SmartPaddle/{NAME}/{_UID_INDEX}")
    _UID_INDEX += 1
    return str(value)


def _line(x1: float, y1: float, x2: float, y2: float, layer: str, width: float = 0.12) -> str:
    return f"""\t(fp_line
\t\t(start {x1:.4f} {y1:.4f})
\t\t(end {x2:.4f} {y2:.4f})
\t\t(stroke
\t\t\t(width {width})
\t\t\t(type solid)
\t\t)
\t\t(layer "{layer}")
\t\t(uuid "{_uid()}")
\t)
"""


def _rect(x0: float, y0: float, x1: float, y1: float, layer: str, width: float) -> str:
    return "".join(
        [
            _line(x0, y0, x1, y0, layer, width),
            _line(x1, y0, x1, y1, layer, width),
            _line(x1, y1, x0, y1, layer, width),
            _line(x0, y1, x0, y0, layer, width),
        ]
    )


def _smd(name: str, x: float, y: float) -> str:
    return f"""\t(pad "{name}" smd rect
\t\t(at {x:.4f} {y:.4f})
\t\t(size {PAD_W} {PAD_H})
\t\t(layers "F.Cu" "F.Mask" "F.Paste")
\t\t(uuid "{_uid()}")
\t)
"""


def _slot(name: str, x: float) -> str:
    return f"""\t(pad "{name}" thru_hole oval
\t\t(at {x:.4f} 0)
\t\t(size {SLOT_PAD_W:.2f} {SLOT_PAD_H:.2f})
\t\t(drill oval {SLOT_W} {SLOT_H})
\t\t(layers "*.Cu" "*.Mask")
\t\t(remove_unused_layers no)
\t\t(uuid "{_uid()}")
\t)
"""


def _build() -> str:
    global _UID_INDEX
    _UID_INDEX = 0
    assert abs(7 * PITCH - SPAN) < 1e-9
    chw, chd = CRT_W / 2, CRT_D / 2
    fhw, fhd = FAB_W / 2, FAB_D / 2
    parts = [
        f"""(footprint "{NAME}"
\t(version 20241229)
\t(generator "gen_usb_16p_vert_smt_fp.py")
\t(generator_version "9.0")
\t(layer "F.Cu")
\t(descr "TYPE-C 16P vertical SMT, H=5.8 short pin. Exact land pattern and contact order from docs/usb-c-vertical-16p-short/Type-C-16PIN-vertical-H5.8-short-datasheet.pdf")
\t(tags "USB C Type-C Receptacle SMD Vertical 16P")
\t(property "Reference" "REF**"
\t\t(at 0 {-chd - 1.0:.2f} 0)
\t\t(layer "F.SilkS")
\t\t(uuid "{_uid()}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1 1)
\t\t\t\t(thickness 0.15)
\t\t\t)
\t\t)
\t)
\t(property "Value" "{NAME}"
\t\t(at 0 {chd + 1.0:.2f} 0)
\t\t(layer "F.Fab")
\t\t(uuid "{_uid()}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size 0.7 0.7)
\t\t\t\t(thickness 0.1)
\t\t\t)
\t\t)
\t)
\t(property "Datasheet" "${{KIPRJMOD}}/../../../docs/usb-c-vertical-16p-short/Type-C-16PIN-vertical-H5.8-short-datasheet.pdf"
\t\t(at 0 0 0)
\t\t(layer "F.Fab")
\t\t(hide yes)
\t\t(uuid "{_uid()}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1 1)
\t\t\t\t(thickness 0.15)
\t\t\t)
\t\t)
\t)
\t(attr smd)
"""
    ]
    # Concentric: courtyard > fab > copper
    parts.append(_rect(-chw, -chd, chw, chd, "F.CrtYd", 0.05))
    parts.append(_rect(-fhw, -fhd, fhw, fhd, "F.Fab", 0.1))
    parts.append(
        _line(XS[0] - 0.3, YA - PAD_H / 2 - 0.25, XS[0] + 0.3, YA - PAD_H / 2 - 0.25, "F.SilkS")
    )

    for name, x in zip(A_PADS, XS, strict=True):
        parts.append(_smd(name, x, YA))
    for name, x in zip(B_PADS, XS, strict=True):
        parts.append(_smd(name, x, YB))
    parts.append(_slot(SHIELD_PAD, -SLOT_X))
    parts.append(_slot(SHIELD_PAD, SLOT_X))
    parts.append(
        """\t(embedded_fonts no)
\t(model "${KIPRJMOD}/../../lib/3dmodels/USB_C_Receptacle_16P_Vertical_SMT_Short.step"
\t\t(offset
\t\t\t(xyz 0 0 0)
\t\t)
\t\t(scale
\t\t\t(xyz 1 1 1)
\t\t)
\t\t(rotate
\t\t\t(xyz 0 0 0)
\t\t)
\t)
)
"""
    )
    return "".join(parts)


def _selfcheck_preview() -> None:
    from PIL import Image, ImageDraw, ImageFont

    assert abs(7 * PITCH - SPAN) < 1e-9
    scale = 55
    minx, maxx = -CRT_W / 2 - 0.5, CRT_W / 2 + 0.5
    miny, maxy = -CRT_D / 2 - 0.5, CRT_D / 2 + 0.5
    fw = int((maxx - minx) * scale)
    fh = int((maxy - miny) * scale)

    def xy(x: float, y: float) -> tuple[int, int]:
        # KiCad board view uses +Y downward, so A (negative Y) stays above B.
        return int((x - minx) * scale), int((y - miny) * scale)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_s = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
        font_pin = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
    except Exception:
        font = font_s = font_pin = ImageFont.load_default()

    left = Image.new("RGB", (fw, fh), (255, 255, 255))
    d = ImageDraw.Draw(left)
    d.rectangle(
        [xy(-CRT_W / 2, -CRT_D / 2), xy(CRT_W / 2, CRT_D / 2)],
        outline=(200, 80, 200),
        width=2,
    )
    d.rectangle(
        [xy(-FAB_W / 2, -FAB_D / 2), xy(FAB_W / 2, FAB_D / 2)],
        outline=(40, 40, 40),
        width=2,
    )
    for x in XS:
        for y in (YA, YB):
            d.rectangle(
                [xy(x - PAD_W / 2, y - PAD_H / 2), xy(x + PAD_W / 2, y + PAD_H / 2)],
                fill=(200, 40, 40),
                outline=(120, 10, 10),
            )
    for name, x in zip(A_PADS, XS, strict=True):
        d.text(
            xy(x, YA - PAD_H / 2 - 0.12),
            name,
            anchor="ms",
            fill=(20, 20, 20),
            font=font_pin,
        )
    for name, x in zip(B_PADS, XS, strict=True):
        d.text(
            xy(x, YB + PAD_H / 2 + 0.12),
            name,
            anchor="mt",
            fill=(20, 20, 20),
            font=font_pin,
        )
    for x in (-SLOT_X, SLOT_X):
        d.ellipse(
            [
                xy(x - SLOT_PAD_W / 2, -SLOT_PAD_H / 2),
                xy(x + SLOT_PAD_W / 2, SLOT_PAD_H / 2),
            ],
            outline=(0, 120, 40),
            width=2,
            fill=(220, 255, 220),
        )
        d.ellipse(
            [xy(x - SLOT_W / 2, -SLOT_H / 2), xy(x + SLOT_W / 2, SLOT_H / 2)],
            outline=(0, 80, 30),
            width=1,
            fill=(255, 255, 255),
        )

    crop = Image.open(DATASHEET_DETAIL).convert("RGB")
    rh = fh
    rw = int(crop.width * (rh / crop.height))
    crop = crop.resize((rw, rh), Image.Resampling.LANCZOS)

    margin = 70
    canvas = Image.new("RGB", (fw + rw + margin * 3, fh + margin * 2 + 36), (245, 246, 248))
    canvas.paste(left, (margin, margin + 28))
    canvas.paste(crop, (margin * 2 + fw, margin + 28))
    cd = ImageDraw.Draw(canvas)
    cd.text((margin, 6), "GENERATED land pattern", fill=(0, 0, 0), font=font)
    cd.text((margin * 2 + fw, 6), "H=5.8 SHORT-PIN PDF (page 1)", fill=(0, 0, 0), font=font)
    cd.text(
        (margin, margin + 28 + fh + 4),
        f"16x {PAD_W}x{PAD_H}  P{PITCH}  span{SPAN}  rowOuter{ROW_OUTER_SPAN}  "
        f"slot {SLOT_W}x{SLOT_H} @ {SLOT_SPAN}; outer {SLOT_PAD_W}x{SLOT_PAD_H}",
        fill=(30, 30, 30),
        font=font_s,
    )
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(PREVIEW)

    # Geometric and semantic self-check vs the H=5.8 short-pin PDF.
    checks = [
        ("datasheet_pdf_present", DATASHEET_PDF.is_file()),
        ("datasheet_detail_present", DATASHEET_DETAIL.is_file()),
        (
            "16_unique_contacts",
            len(A_PADS + B_PADS) == 16 and len(set(A_PADS + B_PADS)) == 16,
        ),
        (
            "contact_order",
            A_PADS[0] == "A1"
            and A_PADS[-1] == "A12"
            and B_PADS[0] == "B12"
            and B_PADS[-1] == "B1",
        ),
        ("pitch*7", abs(7 * PITCH - SPAN) < 1e-9),
        ("row_outer_span", abs(ROW_C2C + PAD_H - ROW_OUTER_SPAN) < 1e-9),
        ("slot_span", abs(2 * SLOT_X - SLOT_SPAN) < 1e-9),
        ("slot_annulus", SLOT_PAD_W > SLOT_W and SLOT_PAD_H > SLOT_H),
        ("fab_contains_copper", FAB_W >= COPPER_W - 1e-9 and FAB_D >= COPPER_D - 1e-9),
        ("crt_contains_fab", CRT_W >= FAB_W - 1e-9 and CRT_D >= FAB_D - 1e-9),
        ("concentric", abs(CRT_W - FAB_W - 2 * CRT_CLEAR) < 1e-9),
        ("no_mouth_graphic", "fp_arc" not in _build()),
    ]
    bad = [n for n, ok in checks if not ok]
    if bad:
        raise RuntimeError(f"selfcheck failed: {bad}")
    print(f"selfcheck OK -> {PREVIEW}")


# ===== 分区：公开 API =====
def main() -> int:
    OUT.write_text(_build(), encoding="utf-8")
    _selfcheck_preview()
    print(f"wrote {OUT}")
    return 0


# ===== 分区：方法/工具 =====
if __name__ == "__main__":
    raise SystemExit(main())
