# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import math
import os
import traceback
from pathlib import Path

import FreeCAD as App
import Import
import Part


# ===== 分区：常量/配置 =====
ROOT = Path(os.environ["PROJECT_ROOT"])
CATALOG_PATH = ROOT / "parts" / "catalog.json"
OUT_DIR = ROOT / "output" / "simulation" / "parts"
ASSEMBLY_STEP = ROOT / "output" / "simulation" / "drive_module.step"
DOCUMENT_PATH = ROOT / "output" / "simulation" / "drive_module.FCStd"
COMMON_KINDS = {"dc_motor", "spur_gear", "metric_screw"}


# ===== 分区：私有成员 =====
def _vector(values):
    return App.Vector(float(values[0]), float(values[1]), float(values[2]))


def _axis_vector(values):
    axis = _vector(values)
    if axis.Length < 1e-9:
        raise ValueError("零件轴线长度不能为零。")
    return axis.normalize()


def _placed_shape(shape: Part.Shape) -> Part.Shape:
    return shape.transformGeometry(shape.Placement.toMatrix())


def _export_step(shape, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _placed_shape(shape).exportStep(str(path))


def _motor_shape(part: dict) -> Part.Shape:
    gearbox = part["gearbox_mm"]
    body = Part.makeBox(float(gearbox[0]), float(gearbox[1]), float(gearbox[2]))
    body.translate(App.Vector(-float(gearbox[0]), -float(gearbox[1]) / 2, -float(gearbox[2]) / 2))
    can = Part.makeCylinder(
        float(part["body_diameter_mm"]) / 2,
        float(part["motor_length_mm"]),
        App.Vector(-float(gearbox[0]) - float(part["motor_length_mm"]), 0, 0),
        App.Vector(1, 0, 0),
    )
    shaft = Part.makeCylinder(
        float(part["shaft_diameter_mm"]) / 2,
        float(part["shaft_length_mm"]),
        App.Vector(0, 0, 0),
        App.Vector(1, 0, 0),
    )
    fused = body.fuse(can).fuse(shaft)
    return fused


def _gear_shape(part: dict) -> Part.Shape:
    module = float(part["module_mm"])
    teeth = int(part["teeth"])
    width = float(part["width_mm"])
    bore = float(part["bore_mm"])
    pitch_r = module * teeth / 2.0
    outer_r = pitch_r + module
    root_r = max(pitch_r - 1.25 * module, bore / 2 + 0.3)
    blank = Part.makeCylinder(root_r, width, App.Vector(-width / 2, 0, 0), App.Vector(1, 0, 0))
    tooth_w = max(module * 0.8, 0.3)
    tooth_h = outer_r - root_r + 0.05
    teeth_solid = blank
    for index in range(teeth):
        tooth = Part.makeBox(width, tooth_w, tooth_h)
        tooth.translate(App.Vector(-width / 2, -tooth_w / 2, root_r - 0.05))
        tooth.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), math.degrees(index * 2 * math.pi / teeth))
        teeth_solid = teeth_solid.fuse(tooth)
    hole = Part.makeCylinder(bore / 2, width + 2, App.Vector(-width / 2 - 1, 0, 0), App.Vector(1, 0, 0))
    gear = teeth_solid.cut(hole)
    return gear


def _screw_shape(part: dict) -> Part.Shape:
    head_d = float(part["head_diameter_mm"])
    head_h = float(part["head_height_mm"])
    major = float(part["thread_major_mm"])
    length = float(part["length_mm"])
    shank = Part.makeCylinder(major / 2, length, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    head = Part.makeCylinder(head_d / 2, head_h, App.Vector(0, 0, length), App.Vector(0, 0, 1), 6)
    screw = head.fuse(shank)
    return screw


def placement_for(part: dict) -> App.Placement:
    kind = part["kind"]
    origin = _vector(part["origin_mm"])
    if kind == "dc_motor":
        return App.Placement(origin, App.Rotation(App.Vector(1, 0, 0), _axis_vector(part["shaft_axis"])))
    if kind == "spur_gear":
        return App.Placement(origin, App.Rotation(App.Vector(1, 0, 0), _axis_vector(part["axis"])))
    if kind == "metric_screw":
        return App.Placement(origin, App.Rotation(App.Vector(0, 0, 1), _axis_vector(part.get("axis", [0, 0, 1]))))
    raise ValueError(f"没有放置规则: {kind}")


BUILDERS = {
    "dc_motor": _motor_shape,
    "spur_gear": _gear_shape,
    "metric_screw": _screw_shape,
}


# ===== 分区：公开 API =====
def build_parts() -> dict:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    doc = App.newDocument("CotsDrive")
    exported = []
    objects = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for part in catalog["parts"]:
        kind = part["kind"]
        if kind not in COMMON_KINDS:
            continue
        builder = BUILDERS[kind]
        shape = builder(part)
        feature = doc.addObject("Part::Feature", part["id"])
        feature.Shape = shape
        feature.Placement = placement_for(part)
        objects.append(feature)
        step_path = OUT_DIR / f"{part['id']}.step"
        placed = shape.copy()
        placed.Placement = feature.Placement
        _export_step(placed, step_path)
        exported.append(
            {
                "id": part["id"],
                "kind": kind,
                "step": str(step_path.relative_to(ROOT)),
                "volume_mm3": float(shape.Volume),
            }
        )
    if not objects:
        raise RuntimeError("目录里没有可导出的标准件。")
    Import.export(objects, str(ASSEMBLY_STEP))
    DOCUMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.recompute()
    doc.saveAs(str(DOCUMENT_PATH))
    return {
        "document": str(DOCUMENT_PATH.relative_to(ROOT)),
        "parts": exported,
        "assembly": str(ASSEMBLY_STEP.relative_to(ROOT)),
        "freecad": list(App.Version()[:3]),
        "format": "step",
        "shell_included": False,
    }


# ===== 分区：方法/工具 =====
def main() -> int:
    try:
        result = build_parts()
        report_path = ROOT / "output" / "simulation" / "freecad-parts.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"FreeCAD 标准件 STEP 导出失败：{type(exc).__name__}: {exc}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    code = main()
    raise SystemExit(code)
