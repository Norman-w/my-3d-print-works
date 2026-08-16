#!/usr/bin/env python3
"""Validate the documented mechanical handoff against live PCB/CAD facts."""

from __future__ import annotations

import ast
import importlib.util
import json
import math
import re
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/mechanical-handoff/mechanical-contract.scad"
PARAMETERS = ROOT / "enclosure/parameters.scad"
SHELL = ROOT / "enclosure/paddle_shell.scad"
BOARD = ROOT / "pcb/layouts/default/default.kicad_pcb"
HARNESS = ROOT / "pcb-tail/harness/adapter.json"
TAIL_FACTS = ROOT / "enclosure/stl/interference/tail_interference.json"
SCREW_FACTS = ROOT / "enclosure/generated/m6_screw_safety.json"
BEZIER = ROOT / "scripts/bezier_to_openscad.py"

PZT_ADDRESSES = {
    "pzt_bl.pzt_gnd_pad", "pzt_bl.pzt_signal_pad",
    "pzt_br.pzt_gnd_pad", "pzt_br.pzt_signal_pad",
    "pzt_tl.pzt_gnd_pad", "pzt_tl.pzt_signal_pad",
    "pzt_tr.pzt_gnd_pad", "pzt_tr.pzt_signal_pad",
}


class HandoffError(RuntimeError):
    pass


def _scalar(text: str, name: str) -> float:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*([-+0-9.]+)\s*;", text)
    if not match:
        raise HandoffError(f"missing scalar {name}")
    return float(match.group(1))


def _array(text: str, name: str):
    match = re.search(
        rf"(?ms)^\s*{re.escape(name)}\s*=\s*(\[.*?\])\s*;",
        text,
    )
    if not match:
        raise HandoffError(f"missing array {name}")
    clean = re.sub(r"//[^\n]*", "", match.group(1))
    return ast.literal_eval(clean)


def _literal_coordinate_pairs(text: str, name: str) -> list[tuple[float, float]]:
    match = re.search(
        rf"(?ms)^\s*{re.escape(name)}\s*=\s*(\[.*?\])\s*;",
        text,
    )
    if not match:
        raise HandoffError(f"missing coordinate list {name}")
    clean = re.sub(r"//[^\n]*", "", match.group(1))
    return [
        (float(x), float(y))
        for x, y in re.findall(r"\[\s*([-+0-9.]+)\s*,\s*([-+0-9.]+)\s*\]", clean)
    ]


def _field(fp: "pcbnew.FOOTPRINT", name: str) -> str:
    return fp.GetFieldByName(name).GetText() if fp.HasFieldByName(name) else ""


def _point_in_polygon(point, polygon) -> bool:
    x, y = point
    inside = False
    for index, (x1, y1) in enumerate(polygon):
        x2, y2 = polygon[(index + 1) % len(polygon)]
        if ((y1 > y) != (y2 > y)) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _point_segment_distance(point, a, b) -> float:
    px, py = point
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _boundary_distance(point, polygon) -> float:
    return min(
        _point_segment_distance(point, polygon[index], polygon[(index + 1) % len(polygon)])
        for index in range(len(polygon))
    )


def _xy_mm(point) -> tuple[float, float]:
    return point.x / 1e6, point.y / 1e6


def _edge_distance(point: tuple[float, float], drawings) -> float:
    distances: list[float] = []
    for drawing in drawings:
        shape = drawing.GetShape()
        if shape == pcbnew.SHAPE_T_SEGMENT:
            distances.append(
                _point_segment_distance(point, _xy_mm(drawing.GetStart()), _xy_mm(drawing.GetEnd()))
            )
        elif shape == pcbnew.SHAPE_T_CIRCLE:
            center = _xy_mm(drawing.GetCenter())
            radius = drawing.GetRadius() / 1e6
            distances.append(abs(math.dist(point, center) - radius))
        else:
            raise HandoffError(f"unsupported Edge.Cuts shape {shape}; extend the physical-edge audit")
    if not distances:
        raise HandoffError("current PCB has no usable Edge.Cuts geometry")
    return min(distances)


def _load_bezier_module():
    spec = importlib.util.spec_from_file_location("smartpaddle_bezier", BEZIER)
    if spec is None or spec.loader is None:
        raise HandoffError("cannot load bezier generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rect_perimeter(cx: float, size: float) -> list[tuple[float, float]]:
    half = size / 2
    points = []
    for step in range(11):
        t = -half + size * step / 10
        points.extend(((cx + t, -half), (cx + t, half), (cx - half, t), (cx + half, t)))
    return points


def main() -> int:
    contract = CONTRACT.read_text(encoding="utf-8")
    parameters = PARAMETERS.read_text(encoding="utf-8")
    shell = SHELL.read_text(encoding="utf-8")
    harness = json.loads(HARNESS.read_text(encoding="utf-8"))
    tail = json.loads(TAIL_FACTS.read_text(encoding="utf-8"))
    screw = json.loads(SCREW_FACTS.read_text(encoding="utf-8"))

    battery_d = _scalar(contract, "protected_14500_max_d")
    battery_l = _scalar(contract, "protected_14500_max_l")
    radial_clear = _scalar(contract, "protected_14500_fit_radial_clearance")
    axial_clear = _scalar(contract, "protected_14500_fit_axial_clearance")
    battery_center = _array(contract, "protected_14500_center")
    fit_radius = battery_d / 2 + radial_clear
    fit_length = battery_l + 2 * axial_clear
    battery_y0 = battery_center[1] - fit_length / 2
    battery_y1 = battery_center[1] + fit_length / 2
    if not (math.isclose(battery_d, 14.0) and battery_l <= 52.0):
        raise HandoffError("protected 14500 envelope no longer matches the user-supplied limit")

    wire_od = _scalar(contract, "handle_wire_od")
    corridor_size = _scalar(contract, "handle_wire_corridor_size")
    corridor_x = _scalar(contract, "handle_wire_corridor_center_x")
    corridor_y0 = _scalar(contract, "handle_wire_corridor_y0")
    corridor_y1 = _scalar(contract, "handle_wire_corridor_y1")
    neck_x = _scalar(contract, "handle_wire_neck_center_x")
    neck_y = _scalar(contract, "handle_wire_neck_y")
    if not (
        math.isclose(corridor_y0, battery_y0)
        and math.isclose(corridor_y1, battery_y1)
    ):
        raise HandoffError("battery-side wire corridor no longer spans the protected-cell envelope")
    if corridor_size + 1e-6 < 2 * wire_od:
        raise HandoffError("a 2x2 wire branch cannot fit the documented corridor")
    wire = harness.get("wireConstruction", {})
    if (
        wire.get("marking") != "UL1571 28AWG"
        or wire.get("conductor") != "7 x 0.12 mm tinned copper"
        or not math.isclose(float(wire.get("outerDiameterMm", 0)), wire_od)
        or not math.isclose(float(wire.get("tinnedFreeEndMm", 0)), 3.0)
        or {int(item["wireAwg"]) for item in harness["conductors"]} != {28}
        or len(harness["conductors"]) != 8
    ):
        raise HandoffError("harness JSON does not match the purchased finished-wire construction")

    board = pcbnew.LoadBoard(str(BOARD))
    actual_pzt = []
    actual_pzt_kicad: dict[str, tuple[float, float]] = {}
    pad_d = _scalar(contract, "pzt_wire_pad_d")
    drill = _scalar(contract, "pzt_wire_pad_drill")
    scad_y_offset = _scalar(parameters, "blade_ellipse_cy")
    seen = set()
    for fp in board.GetFootprints():
        address = _field(fp, "atopile_address")
        if address not in PZT_ADDRESSES:
            continue
        pads = [pad for pad in fp.Pads() if pad.GetNumber() == "1"]
        if len(pads) != 1:
            raise HandoffError(f"{address} does not have exactly one pad 1")
        pad = pads[0]
        size = pad.GetSize()
        hole = pad.GetDrillSize()
        if not (
            math.isclose(size.x / 1e6, pad_d, abs_tol=0.001)
            and math.isclose(size.y / 1e6, pad_d, abs_tol=0.001)
            and math.isclose(hole.x / 1e6, drill, abs_tol=0.001)
        ):
            raise HandoffError(f"{address} pad/drill geometry changed")
        pos = pad.GetPosition()
        actual_pzt.append((pos.x / 1e6, -pos.y / 1e6 + scad_y_offset))
        actual_pzt_kicad[address] = _xy_mm(pos)
        seen.add(address)
    if seen != PZT_ADDRESSES:
        raise HandoffError(f"PZT wire-pad inventory differs: {sorted(PZT_ADDRESSES ^ seen)}")
    documented_pzt = [tuple(map(float, point)) for point in _array(contract, "pzt_solder_pad_centers_scad")]
    if sorted(actual_pzt) != sorted(documented_pzt):
        raise HandoffError(f"PZT relief centers are stale: {sorted(actual_pzt)}")
    relief_d = _scalar(contract, "pzt_solder_relief_d")
    extra_depth = _scalar(contract, "pzt_solder_relief_extra_depth")
    if not math.isclose((relief_d - pad_d) / 2, 0.5) or not math.isclose(extra_depth, 0.5):
        raise HandoffError("PZT relief must remain 0.5 mm radial and 0.5 mm deeper")
    edge_drawings = [
        drawing for drawing in board.GetDrawings()
        if drawing.GetLayer() == pcbnew.Edge_Cuts
    ]
    pzt_edge_offsets = {
        address: _edge_distance(position, edge_drawings)
        for address, position in actual_pzt_kicad.items()
    }
    outside_drill = {
        address: offset for address, offset in pzt_edge_offsets.items()
        if offset > drill / 2 + 0.001
    }
    if outside_drill:
        raise HandoffError(
            "PZT Edge.Cuts no longer crosses every drilled wire pad: "
            + ", ".join(f"{address}={offset:.3f}mm" for address, offset in sorted(outside_drill.items()))
        )

    bezier = _load_bezier_module()
    design = json.loads(bezier.DEFAULT_JSON.read_text(encoding="utf-8"))
    params = bezier.parse_params(bezier.DEFAULT_PARAMS)
    slices = bezier.handle_loft_slices(
        design["handle-front"], design["handle-bottom"],
        design.get("side") or bezier.DEFAULT_SIDE,
        params["handle_join_y"], params["blade_core_t"] / 2, 256,
    )
    battery_surface = [
        (fit_radius * math.cos(math.radians(degree)), fit_radius * math.sin(math.radians(degree)))
        for degree in range(0, 360, 2)
    ]
    corridor_surface = _rect_perimeter(corridor_x, corridor_size) + _rect_perimeter(-corridor_x, corridor_size)
    minimum_battery_wall = math.inf
    minimum_corridor_wall = math.inf
    for y, outer in slices:
        if not (battery_y0 <= y <= battery_y1):
            continue
        for point in battery_surface:
            if not _point_in_polygon(point, outer):
                raise HandoffError(f"protected 14500 envelope exits handle at y={y:.3f}")
            minimum_battery_wall = min(minimum_battery_wall, _boundary_distance(point, outer))
        for point in corridor_surface:
            if not _point_in_polygon(point, outer):
                raise HandoffError(f"wire corridor exits handle at y={y:.3f}")
            minimum_corridor_wall = min(minimum_corridor_wall, _boundary_distance(point, outer))
    if minimum_battery_wall < 2.0 or minimum_corridor_wall < 2.0:
        raise HandoffError(
            f"local cavity leaves too little outer wall: battery={minimum_battery_wall:.3f}, "
            f"wire={minimum_corridor_wall:.3f} mm"
        )

    battery_wire_gap = corridor_x - corridor_size / 2 - fit_radius
    if battery_wire_gap < 0.049:
        raise HandoffError(f"wire corridor overlaps protected-cell envelope by {-battery_wire_gap:.3f} mm")
    wire_segments = []
    for side in (-1, 1):
        straight_start = (side * corridor_x, corridor_y0)
        straight_end = (side * corridor_x, corridor_y1)
        neck_end = (side * neck_x, neck_y)
        wire_segments.extend(((straight_start, straight_end), (straight_end, neck_end)))

    side_boss_radius = float(screw["bossDiameterMm"]) / 2
    side_boss_centers = [tuple(map(float, point)) for point in screw["finalPositions"]]
    side_battery_gap = min(
        _point_segment_distance(point, (battery_center[0], battery_y0), (battery_center[0], battery_y1))
        - fit_radius - side_boss_radius
        for point in side_boss_centers
    )
    side_wire_gap = min(
        _point_segment_distance(point, start, end) - side_boss_radius - corridor_size / 2
        for point in side_boss_centers
        for start, end in wire_segments
    )
    if side_battery_gap < 0.5:
        raise HandoffError(f"protected cell hits a side screw boss: {side_battery_gap:.3f} mm")
    if side_wire_gap < 0.05:
        raise HandoffError(f"battery-side wire corridor hits a side screw boss: {side_wire_gap:.3f} mm")

    through_function = re.search(
        r"function\s+m6_handle_through_screw_positions\(\)\s*=\s*\[(.*?)\];",
        shell,
        flags=re.DOTALL,
    )
    if (
        through_function is None
        or "for (p = pcb_through_screw_positions)" not in through_function.group(1)
        or re.search(r"for\s*\(p\s*=\s*screw_positions\)", through_function.group(1))
    ):
        raise HandoffError("M6 handle through-boss inventory is not tied only to PCB through-screw positions")
    shoulder_bottom_y = _scalar(parameters, "shoulder_bottom_y")
    m2_boss_radius = _scalar(parameters, "screw_d_boss") / 2
    required_m2_boss_centers = [
        tuple(map(float, point))
        for point in _array(parameters, "pcb_through_screw_positions")
        if float(point[1]) <= shoulder_bottom_y - 10
    ]
    if not required_m2_boss_centers:
        raise HandoffError("no required handle PCB-through M2 boss remains")
    legacy_m2_boss_centers = [
        point for point in _literal_coordinate_pairs(parameters, "screw_positions")
        if point[1] <= shoulder_bottom_y - 10
    ]
    m2_boss_centers = required_m2_boss_centers + legacy_m2_boss_centers
    m2_battery_gap = min(
        _point_segment_distance(point, (battery_center[0], battery_y0), (battery_center[0], battery_y1))
        - fit_radius - m2_boss_radius
        for point in m2_boss_centers
    )
    m2_wire_gap = min(
        _point_segment_distance(point, start, end) - m2_boss_radius - corridor_size / 2
        for point in m2_boss_centers
        for start, end in wire_segments
    )
    if m2_battery_gap < 0.5 or m2_wire_gap < 0.5:
        raise HandoffError(
            f"protected cell/wire hits a required M2 boss: battery={m2_battery_gap:.3f}, "
            f"wire={m2_wire_gap:.3f} mm"
        )

    j4 = tail.get("battery_connector", {})
    connector_y1 = float(j4.get("handle_y_range", [0, 0])[1])
    tail_service_gap = battery_y0 - connector_y1
    head_gap = float(harness["mechanical"]["mainConnectorWorldYRangeMm"][0]) - battery_y1
    if tail_service_gap < 3.0 or head_gap < 3.0:
        raise HandoffError(
            f"battery leaves insufficient lead space: tail={tail_service_gap:.3f}, head={head_gap:.3f} mm"
        )

    print("Mechanical handoff audit PASS")
    print(
        f"  protected 14500 fit Ø{2 * fit_radius:.2f} x {fit_length:.2f} mm; "
        f"minimum retained outer wall={minimum_battery_wall:.3f} mm"
    )
    print(
        f"  two 4-wire UL1571 28AWG branches: {corridor_size:.1f} mm square at "
        f"X=±{corridor_x:.1f}; battery gap={battery_wire_gap:.3f} mm; "
        f"side-boss gap={side_wire_gap:.3f} mm"
    )
    print(
        f"  boss clearance: cell-to-side={side_battery_gap:.3f} mm; "
        f"cell-to-required-M2={m2_battery_gap:.3f} mm; wire-to-required-M2={m2_wire_gap:.3f} mm"
    )
    print(
        f"  J4-to-cell service gap={tail_service_gap:.3f} mm; "
        f"cell-to-main-connector gap={head_gap:.3f} mm"
    )
    print(
        f"  8 PZT pad-center reliefs: Ø3.5 mm, +0.5 mm depth; "
        f"Edge.Cuts crosses every Ø{drill:.1f} mm drill (max center offset={max(pzt_edge_offsets.values()):.3f} mm)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
