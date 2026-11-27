#!/usr/bin/env python3
"""Export main-board component envelopes for OpenSCAD shell interference."""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# ===== 分区：常量/配置 =====
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PCB = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
PARAMETERS = ROOT / "enclosure" / "parameters.scad"
OUT = ROOT / "enclosure" / "stl" / "interference" / "main_interference.json"
OUT_SCAD = ROOT / "enclosure" / "stl" / "interference" / "main_board_cuts.scad"

BOARD_BACK_CLEAR_MM = 0.20
COMPONENT_TOP_CLEAR_MM = 0.20
MODULE_TOP_CLEAR_MM = 0.20
COURTYARD_EXTRA_CLEAR_MM = 0.10
BOARD_OVERLAP_MM = 0.10

MODULE_HEIGHT_MM = {
    "MCU_ESP32_S3": 3.20,
    "IMU_IM948": 3.00,
}

REFERENCE_HEIGHT_MM = {
    "PW_L_BUCK_2U2": 1.30,
    "PW_C_IN_10U": 1.45,
    "PW_C_OUT_22U": 0.95,
    "TAIL_MX125_F": 3.40,
    "TAIL_MX125_B": 3.40,
}

FOOTPRINT_HEIGHT_RULES = (
    ("C_0603_1608Metric", 0.95),
    ("C_0805_2012Metric", 1.45),
    ("C_1206_3216Metric", 1.80),
    ("R_0603_1608Metric", 0.65),
    ("LED_0603", 0.80),
    ("SOD-323", 1.00),
    ("SOT-23", 1.20),
    ("TSSOP-14", 1.20),
    ("MSOP-10", 1.10),
    ("WSON-8", 0.80),
    ("DSG0008", 0.80),
)

NON_BODY_FOOTPRINT_TOKENS = (
    "PZT_WirePad",
    "TestPoint",
    "MountingHole",
)


# ===== 分区：模型/类型 =====
class InterferenceError(RuntimeError):
    """Raised when a populated footprint lacks a mechanical envelope."""


# ===== 分区：私有成员 =====
def _kicad_python() -> str:
    mac = Path(
        "/Applications/KiCad/KiCad.app/Contents/Frameworks/"
        "Python.framework/Versions/3.9/bin/python3"
    )
    return str(mac) if mac.is_file() else sys.executable


def _parameter_scalar(name: str) -> float:
    text = PARAMETERS.read_text(encoding="utf-8")
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*([-+0-9.]+)\s*;", text)
    if match is None:
        raise InterferenceError(f"missing OpenSCAD parameter {name}")
    return float(match.group(1))


def _courtyard_box(board, pcbnew, footprint) -> list[float]:
    layer = pcbnew.F_CrtYd if footprint.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd
    boxes = [
        item.GetBoundingBox()
        for item in footprint.GraphicalItems()
        if item.GetLayer() == layer
    ]
    if not boxes:
        raise InterferenceError(f"{footprint.GetReference()} has no courtyard")
    return [
        min(box.GetX() for box in boxes) / 1e6,
        min(box.GetY() for box in boxes) / 1e6,
        max(box.GetRight() for box in boxes) / 1e6,
        max(box.GetBottom() for box in boxes) / 1e6,
    ]


def _height_for(reference: str, footprint_id: str) -> float | None:
    if reference in REFERENCE_HEIGHT_MM:
        return REFERENCE_HEIGHT_MM[reference]
    if any(token in footprint_id for token in NON_BODY_FOOTPRINT_TOKENS):
        return None
    for token, height in FOOTPRINT_HEIGHT_RULES:
        if token in footprint_id:
            return height
    raise InterferenceError(
        f"{reference} footprint {footprint_id!r} has no conservative height rule"
    )


def _to_scad_box(
    courtyard: list[float],
    layer_name: str,
    board_t: float,
    height: float,
    y_offset: float,
) -> list[float]:
    x0, ky0, x1, ky1 = courtyard
    sx0 = x0 - COURTYARD_EXTRA_CLEAR_MM
    sx1 = x1 + COURTYARD_EXTRA_CLEAR_MM
    sy0 = -ky1 + y_offset - COURTYARD_EXTRA_CLEAR_MM
    sy1 = -ky0 + y_offset + COURTYARD_EXTRA_CLEAR_MM
    if layer_name == "F.Cu":
        z0 = -BOARD_OVERLAP_MM
        z1 = height + COMPONENT_TOP_CLEAR_MM
    elif layer_name == "B.Cu":
        z0 = -board_t - height - COMPONENT_TOP_CLEAR_MM
        z1 = -board_t + BOARD_OVERLAP_MM
    else:
        raise InterferenceError(f"unsupported component layer {layer_name}")
    return [sx0, sy0, z0, sx1, sy1, z1]


def _extract() -> dict:
    import wx

    _app = wx.App(False)
    import pcbnew

    board = pcbnew.LoadBoard(str(PCB))
    board_t = board.GetDesignSettings().GetBoardThickness() / 1e6
    y_offset = _parameter_scalar("blade_ellipse_cy")
    blade_half_t = _parameter_scalar("blade_core_t") / 2
    shoulder_bottom_y = _parameter_scalar("shoulder_bottom_y")
    component_keepouts = []
    module_courtyards = []
    module_references = []
    skipped_dnp = []
    skipped_non_body = []
    footprint_count = 0

    for footprint in board.GetFootprints():
        footprint_count += 1
        reference = footprint.GetReference()
        value = footprint.GetValue()
        footprint_id = footprint.GetFPIDAsString()
        if "DNP" in value.upper():
            skipped_dnp.append(reference)
            continue
        courtyard = _courtyard_box(board, pcbnew, footprint)
        if reference in MODULE_HEIGHT_MM:
            module_courtyards.append(courtyard)
            module_references.append(reference)
            continue
        height = _height_for(reference, footprint_id)
        if height is None:
            skipped_non_body.append(reference)
            continue
        layer_name = board.GetLayerName(footprint.GetLayer())
        component_keepouts.append(
            {
                "ref": reference,
                "footprint": footprint_id,
                "layer": layer_name,
                "height_max": height,
                "courtyard_kicad_xy": courtyard,
                "scad_box_xyz": _to_scad_box(
                    courtyard,
                    layer_name,
                    board_t,
                    height,
                    y_offset,
                ),
            }
        )

    if len(module_courtyards) != len(MODULE_HEIGHT_MM):
        raise InterferenceError("MCU/IMU courtyard inventory is incomplete")
    accounted = (
        len(component_keepouts)
        + len(module_references)
        + len(skipped_dnp)
        + len(skipped_non_body)
    )
    if accounted != footprint_count:
        raise InterferenceError(
            f"footprint inventory is not closed: {accounted}/{footprint_count}"
        )
    flat_x0 = min(box[0] for box in module_courtyards) - COURTYARD_EXTRA_CLEAR_MM
    flat_x1 = max(box[2] for box in module_courtyards) + COURTYARD_EXTRA_CLEAR_MM
    flat_y0 = (
        -max(box[3] for box in module_courtyards) + y_offset - COURTYARD_EXTRA_CLEAR_MM
    )
    flat_y1 = (
        -min(box[1] for box in module_courtyards) + y_offset + COURTYARD_EXTRA_CLEAR_MM
    )
    module_back_z = -board_t - BOARD_BACK_CLEAR_MM
    module_front_z = max(MODULE_HEIGHT_MM.values()) - board_t + MODULE_TOP_CLEAR_MM
    blade_component_boxes = [
        item["scad_box_xyz"]
        for item in component_keepouts
        if item["scad_box_xyz"][4] >= shoulder_bottom_y
    ]
    maximum_blade_cut_z = max(
        [abs(module_back_z), module_front_z]
        + [max(abs(box[2]), abs(box[5])) for box in blade_component_boxes]
    )
    minimum_retained_blade_skin = blade_half_t - maximum_blade_cut_z
    if minimum_retained_blade_skin < 0.399:
        raise InterferenceError(
            "component interference would leave less than 0.40 mm blade skin: "
            f"{minimum_retained_blade_skin:.3f} mm"
        )

    return {
        "source_pcb": str(PCB.relative_to(ROOT)),
        "board_thickness": board_t,
        "board_back_clearance": BOARD_BACK_CLEAR_MM,
        "component_top_clearance": COMPONENT_TOP_CLEAR_MM,
        "module_top_clearance": MODULE_TOP_CLEAR_MM,
        "minimum_retained_blade_skin": minimum_retained_blade_skin,
        "scad_y_offset": y_offset,
        "inventory": {
            "footprint_count": footprint_count,
            "component_pockets": len(component_keepouts),
            "module_flat_pocket_refs": sorted(module_references),
            "skipped_dnp_refs": sorted(skipped_dnp),
            "skipped_non_body_refs": sorted(skipped_non_body),
        },
        "component_keepouts": sorted(component_keepouts, key=lambda item: item["ref"]),
        "module_flat_box_xyz": [
            flat_x0,
            flat_y0,
            module_back_z,
            flat_x1,
            flat_y1,
            module_front_z,
        ],
    }


def _box_rows(items: list[dict]) -> str:
    return ",\n".join(
        "    [" + ", ".join(f"{value:.5f}" for value in item["scad_box_xyz"]) + "]"
        for item in items
    )


def _write_scad(data: dict) -> None:
    flat = ", ".join(f"{value:.5f}" for value in data["module_flat_box_xyz"])
    text = f"""// AUTO-GENERATED by pcb/scripts/export_main_interference.py — do not edit
// KiCad XY → shell XY: (x, -y + main_if_scad_y_offset).
// PCB F.Cu is at Z=0; the complete 0.8 mm board sits in the back half.

main_if_board_t = {data["board_thickness"]:.3f};
main_if_board_back_clear = {data["board_back_clearance"]:.3f};
main_if_component_top_clear = {data["component_top_clearance"]:.3f};
main_if_module_top_clear = {data["module_top_clearance"]:.3f};
main_if_scad_y_offset = {data["scad_y_offset"]:.3f};

// [x0, y0, z0, x1, y1, z1], using live Courtyard XY and conservative height.
main_if_component_keepouts = [
{_box_rows(data["component_keepouts"])}
];

// MCU + IMU share one front-side flat pocket.  Its back limit equals the
// common PCB slot, so neither module creates an extra local back-side pit.
main_if_module_flat_box = [{flat}];

module main_board_component_interference_cuts() {{
    for (k = main_if_component_keepouts)
        translate([(k[0] + k[3]) / 2, (k[1] + k[4]) / 2, (k[2] + k[5]) / 2])
            cube([k[3] - k[0], k[4] - k[1], k[5] - k[2]], center = true);

    k = main_if_module_flat_box;
    translate([(k[0] + k[3]) / 2, (k[1] + k[4]) / 2, (k[2] + k[5]) / 2])
        cube([k[3] - k[0], k[4] - k[1], k[5] - k[2]], center = true);
}}
"""
    OUT_SCAD.write_text(text, encoding="utf-8")


# ===== 分区：公开 API =====
def main() -> int:
    data = _extract()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    _write_scad(data)
    print(f"wrote {OUT}")
    print(f"wrote {OUT_SCAD}")
    print(
        f"  component pockets={len(data['component_keepouts'])}; "
        f"module flat box={data['module_flat_box_xyz']}"
    )
    inventory = data["inventory"]
    print(
        f"  inventory={inventory['footprint_count']} = "
        f"{inventory['component_pockets']} pockets + "
        f"{len(inventory['module_flat_pocket_refs'])} modules + "
        f"{len(inventory['skipped_dnp_refs'])} DNP + "
        f"{len(inventory['skipped_non_body_refs'])} non-body"
    )
    print(f"  minimum retained blade skin={data['minimum_retained_blade_skin']:.3f} mm")
    return 0


# ===== 分区：方法/工具 =====
if __name__ == "__main__":
    try:
        import pcbnew  # noqa: F401
    except ImportError:
        raise SystemExit(
            subprocess.call(
                [_kicad_python(), str(Path(__file__).resolve()), *sys.argv[1:]]
            )
        )
    raise SystemExit(main())
