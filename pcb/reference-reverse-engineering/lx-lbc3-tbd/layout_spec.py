#!/usr/bin/env python3
"""Photo-calibrated mechanical layout for the LX-LBC3 reference board.

Coordinates use the component-side view with Type-C at the left:

    x = 0..16 mm, Type-C -> battery pads
    y = 0..12 mm, B+ side -> B- side

Only the 16 x 12 mm board envelope is published. Component centres are
derived from the user's top photo after calibrating approximately
116.7 px/mm against that envelope. They remain visual/TBD coordinates,
not production placement data.
"""

from __future__ import annotations

from dataclasses import dataclass


BOARD_W = 16.0
BOARD_H = 12.0
MIN_BODY_CLEARANCE_MM = 0.12
PHOTO_BOARD_ORIGIN_PX = (670.0, 933.0)
PHOTO_SCALE_PX_PER_MM = 116.7
VISUAL_MARKER_EDGE = {
    # The two photographed LED packages show opposite internal coloured ends.
    # This records only the visible package direction, not electrical polarity.
    "D1": "bottom",
    "D2": "top",
}
OBSERVED_TOP_MARKS = {
    "L1": "2R2, text rotated 180 degrees in the Type-C-left view",
    "U1": "JNEC upright; dot at lower-left; C underlined",
    "R4": "square/口-shaped mark; may be a zero-ohm marking but not confirmed",
    "D1": "green internal end at bottom",
    "D2": "green internal end at top",
}


@dataclass(frozen=True)
class Placement:
    x: float
    y: float
    rotation: float = 0.0
    bottom: bool = False


# Centres measured from the uploaded 3072 x 4096 top photo. Pixel coordinates
# are kept here as an audit trail; the corresponding board coordinates are
# rounded to 0.01 mm below. "rotation" is the KiCad rotation after turning the
# portrait photo counter-clockwise so Type-C points left.
PHOTO_CENTRES_PX: dict[str, tuple[float, float]] = {
    "R1": (1590.0, 1665.0),
    "R2": (1435.0, 1665.0),
    "C1": (1155.0, 1685.0),
    "R4": (875.0, 1690.0),
    "D1": (850.0, 1940.0),
    "D2": (850.0, 2160.0),
    "L1": (1810.0, 2140.0),
    "U1": (1260.0, 2140.0),
    "R3": (820.0, 2410.0),
    "C3": (1280.0, 2510.0),
}


def photo_px_to_board_mm(px: float, py: float) -> tuple[float, float]:
    """Rotate/scale a photo centre into the Type-C-left board coordinate frame."""
    origin_x, origin_y = PHOTO_BOARD_ORIGIN_PX
    return (
        round((py - origin_y) / PHOTO_SCALE_PX_PER_MM, 2),
        round(BOARD_H - (px - origin_x) / PHOTO_SCALE_PX_PER_MM, 2),
    )


# J2/J3 are bottom-side pads and therefore retain the separately observed
# underside approximation. J4/J5 use the copper-pad centres rather than the
# oversized solder/wire blobs visible in the photo.
PLACEMENTS: dict[str, Placement] = {
    "J1": Placement(0.00, 6.00),
    "R1": Placement(*photo_px_to_board_mm(*PHOTO_CENTRES_PX["R1"]), 90.0),
    "R2": Placement(*photo_px_to_board_mm(*PHOTO_CENTRES_PX["R2"])),
    "C1": Placement(*photo_px_to_board_mm(*PHOTO_CENTRES_PX["C1"]), 90.0),
    "R4": Placement(*photo_px_to_board_mm(*PHOTO_CENTRES_PX["R4"]), 90.0),
    "D1": Placement(*photo_px_to_board_mm(*PHOTO_CENTRES_PX["D1"]), 90.0),
    "D2": Placement(*photo_px_to_board_mm(*PHOTO_CENTRES_PX["D2"]), 270.0),
    "L1": Placement(*photo_px_to_board_mm(*PHOTO_CENTRES_PX["L1"])),
    "U1": Placement(*photo_px_to_board_mm(*PHOTO_CENTRES_PX["U1"]), 90.0),
    "R3": Placement(*photo_px_to_board_mm(*PHOTO_CENTRES_PX["R3"]), 90.0),
    "C3": Placement(*photo_px_to_board_mm(*PHOTO_CENTRES_PX["C3"]), 90.0),
    "J4": Placement(15.00, 10.10),  # B- in the photographed orientation
    "J5": Placement(15.00, 1.90),  # B+ in the photographed orientation
    "J2": Placement(1.40, 2.30, bottom=True),
    "J3": Placement(1.40, 9.70, bottom=True),
}


# Conservative visible-body/courtyard envelopes. These are deliberately
# larger than the nominal chip bodies so the preview cannot silently regress
# to components drawn on top of one another.
ENVELOPE_MM: dict[str, tuple[float, float]] = {
    "R1": (1.40, 0.90),
    "R2": (1.40, 0.90),
    "R3": (1.40, 0.90),
    "C1": (1.80, 1.00),
    "R4": (1.80, 1.00),
    "C3": (1.80, 1.00),
    "D1": (1.80, 1.00),
    "D2": (1.80, 1.00),
    "L1": (4.00, 4.00),
    "U1": (3.00, 3.20),
    "J2": (2.40, 2.40),
    "J3": (2.40, 2.40),
    "J4": (2.40, 2.40),
    "J5": (2.40, 2.40),
}


def body_bounds(ref: str) -> tuple[float, float, float, float]:
    """Return absolute (left, right, top, bottom) visible-body bounds in mm."""
    if ref == "J1":
        # Photo-calibrated shell: about 4.05 mm ahead of the PCB edge and
        # 3.55 mm over the PCB, with an 8.90 mm visible width.
        return (-4.05, 3.55, 1.55, 10.45)

    placement = PLACEMENTS[ref]
    width, height = ENVELOPE_MM[ref]
    if round(placement.rotation) % 180 == 90:
        width, height = height, width
    return (
        placement.x - width / 2,
        placement.x + width / 2,
        placement.y - height / 2,
        placement.y + height / 2,
    )


def top_side_collisions(
    clearance_mm: float = MIN_BODY_CLEARANCE_MM,
) -> list[tuple[str, str]]:
    """Return same-side body pairs closer than the required clearance."""
    refs = [ref for ref, placement in PLACEMENTS.items() if not placement.bottom]
    collisions: list[tuple[str, str]] = []
    for index, ref_a in enumerate(refs):
        left_a, right_a, top_a, bottom_a = body_bounds(ref_a)
        for ref_b in refs[index + 1 :]:
            left_b, right_b, top_b, bottom_b = body_bounds(ref_b)
            separated = (
                right_a + clearance_mm <= left_b
                or right_b + clearance_mm <= left_a
                or bottom_a + clearance_mm <= top_b
                or bottom_b + clearance_mm <= top_a
            )
            if not separated:
                collisions.append((ref_a, ref_b))
    return collisions
