#!/usr/bin/env python3
"""旧方案 1 蛇形 FreeCAD 预览；不作为中心 R3C3 机械真值。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import math
from typing import Any

from fc_config import HTD_BELT_THICKNESS_MM, HTD_BELT_WIDTH_MM, HTD_DRIVE_TEETH, HTD_PITCH_MM, NEMA17_FACE_MM
from fc_htd import htd_pulley_shape
from fc_primitives import (
    add_box,
    add_cylinder,
    add_feature,
    add_iso_shcs,
    add_placed_shape,
    add_placed_gear_disc,
    make_rect_belt,
)
from fc_drive import drive_axis_specs, drive_mechanism_rows
from fc_snake_path import build_snake_path

# ===== 分区：常量/配置 =====
CYAN = (53, 169, 212)
GREEN = (90, 210, 92)
ORANGE = (255, 173, 102)
STEEL = (168, 176, 184)
MOTOR = (72, 80, 90)
BRONZE = (168, 108, 63)
NEMA_BOLT_CIRCLE = 31.0
# This module is retained for the historical scheme1 FreeCAD preview.  Its
# dog-clutch dimensions are deliberately legacy-only and must never define
# the center R3C3 mechanism.  The current center station is generated from
# the OpenSCAD centerClutch contract and is attached to cabinet_chain_motion.json
# by solve_cabinet_chain.py.  A future FreeCAD center animation must consume
# that contract instead of these fallback preview values.
LEGACY_SCHEME1_CLUTCH_STROKE_MM = 3.0
CLUTCH_FIXED_R = 7.4
CLUTCH_SLIDING_R = 6.6
CLUTCH_FIXED_T = 4.0
CLUTCH_SLIDING_T = 3.6
LEGACY_SCHEME1_CLUTCH_GAP_MM = 2.6
LEGACY_SCHEME1_CLUTCH_OVERLAP_MM = 0.4
LEGACY_SCHEME1_CLUTCH_Z_DROP_MM = 10.0
# The finger is centered over a station.  An outward offset would make the
# pusher miss the sliding dog when the belt is on a straight station.
FORK_CLEAR_MM = 0.0
FORK_LIFT_MM = 0.0

# ===== 分区：模型/类型 =====
# animation 含 pulleys / loop / fork / clutches；apply_mechanism 实现方案 1 的
# 选择、单离合接合、目标取力和释放时序。

# ===== 分区：私有成员 =====
def _nema17(doc, Part, App, drive: dict) -> list[str]:
    x, y, z = drive["x"], drive["y"], drive["z"]
    width = drive.get("width") or (HTD_BELT_WIDTH_MM + 3.0)
    body_len = 40.0
    body_z = z - width * 0.5 - body_len
    add_box(doc, App, "MotorMA_Case", x - NEMA17_FACE_MM * 0.5, y - NEMA17_FACE_MM * 0.5, body_z, NEMA17_FACE_MM, NEMA17_FACE_MM, body_len, MOTOR, 0.0)
    add_cylinder(doc, App, "MotorMA_Pilot", x, y, z - width * 0.5 - 2.0, 11.0, 2.0, STEEL, 0.0)
    add_cylinder(doc, App, "MotorMA_Shaft", x, y, z - width * 0.5 - 4.0, 2.5, 22.0, STEEL, 0.0)
    add_box(doc, App, "MotorMA_Mount", x - 28.0, y - 28.0, body_z - 6.0, 56.0, 56.0, 6.0, CYAN, 0.12)
    names = ["MotorMA_Case", "MotorMA_Pilot", "MotorMA_Shaft", "MotorMA_Mount"]
    for idx, ang in enumerate((45.0, 135.0, 225.0, 315.0)):
        rad = math.radians(ang)
        sx = x + math.cos(rad) * NEMA_BOLT_CIRCLE * 0.5
        sy = y + math.sin(rad) * NEMA_BOLT_CIRCLE * 0.5
        add_iso_shcs(doc, Part, App, f"Fastener_MA_M3_{idx + 1:02d}", sx, sy, body_z - 1.0, "M3", 12.0, "z")
        names.append(f"Fastener_MA_M3_{idx + 1:02d}")
    return names

def _spool(doc, Part, App, pulley: dict) -> str:
    width = pulley.get("width") or (HTD_BELT_WIDTH_MM + 3.0)
    shape = htd_pulley_shape(Part, App, pulley["teeth"], HTD_PITCH_MM, width)
    add_placed_shape(doc, App, pulley["name"], shape, pulley["x"], pulley["y"], pulley["z"] - width * 0.5, ORANGE if pulley["kind"] == "drive" else CYAN, 0.0)
    return pulley["name"]

def _belt(doc, Part, App, path: dict) -> str:
    shape = make_rect_belt(Part, App, path["loop"], HTD_BELT_WIDTH_MM, max(2.4, HTD_BELT_THICKNESS_MM))
    add_feature(doc, shape, "SelectorBelt_HTD3M9", ORANGE, 0.0)
    return "SelectorBelt_HTD3M9"

def _fork(doc, Part, App, home: dict) -> dict:
    # The carrier rides in the selector-belt plane.  Its pusher points down
    # toward the local dog-clutch slider; it does not spin the drawer while
    # passing over a station.
    body = Part.makeBox(10.0, 8.0, 4.0, App.Vector(-5.0, -4.0, -2.0))
    mast = Part.makeBox(4.0, 4.0, 14.0, App.Vector(-2.0, -2.0, -16.0))
    add_placed_shape(doc, App, "SelectorFinger", body.fuse(mast), 0.0, 0.0, 0.0, GREEN, 0.0)
    spec = {"name": "SelectorFinger", "lx": 0.0, "ly": 0.0, "lz": 0.0, "yaw": 0.0, "spin": False}
    doc.getObject(spec["name"]).Placement = fork_placement(App, home)
    return {"parts": [spec], "green": ["SelectorFinger"]}

def _dog_clutch_shape(Part, App, radius: float, thickness: float):
    """Local-axis dog clutch with visible drive dogs for the FreeCAD preview."""
    origin = App.Vector(0, 0, 0)
    shape = Part.makeCylinder(radius * 0.84, thickness, origin)
    hub = Part.makeCylinder(radius * 0.42, thickness * 1.16, App.Vector(0, 0, -thickness * 0.08))
    shape = shape.fuse(hub)
    dog_count = 8
    dog_w = max(0.8, radius * 0.16)
    dog_d = max(0.9, radius * 0.22)
    for index in range(dog_count):
        tooth = Part.makeBox(dog_d, dog_w, thickness, App.Vector(radius * 0.68, -dog_w * 0.5, 0))
        tooth.rotate(origin, App.Vector(0, 0, 1), index * 360.0 / dog_count)
        shape = shape.fuse(tooth)
    return shape

def clutch_specs(cfg, path: dict) -> list[dict]:
    """Return the legacy scheme1 station map without requiring FreeCAD.

    These records are not the center R3C3 mechanism.  The current center
    station uses the OpenSCAD-generated ``centerClutch`` object instead.
    """
    records = []
    for cell in path["cells"]:
        x = cell["x"]
        y = cell["y"]
        fixed_z = cell["z"] - LEGACY_SCHEME1_CLUTCH_Z_DROP_MM
        home_z = fixed_z + CLUTCH_FIXED_T + LEGACY_SCHEME1_CLUTCH_GAP_MM
        engaged_z = fixed_z + CLUTCH_FIXED_T - LEGACY_SCHEME1_CLUTCH_OVERLAP_MM
        prefix = f"L{cell['layer']:02d}_C{cell['col']:02d}"
        fixed_name = f"ClutchFixed_{prefix}"
        sliding_name = f"ClutchSliding_{prefix}"
        drawer_index = cell["index"]
        drawer_x = cfg.margin_x + cell["col"] * (cfg.cell_width + cfg.cell_gap_x)
        drawer_y = cfg.margin_y + cell["layer"] * (cfg.cell_depth + cfg.cell_gap_y)
        coupler_x = drawer_x + cfg.cell_width * 0.12
        coupler_y = drawer_y + cfg.cell_depth * 0.17
        records.append({
            "index": drawer_index,
            "layer": cell["layer"],
            "col": cell["col"],
            "fixed": fixed_name,
            "sliding": sliding_name,
            "x": x,
            "y": y,
            "fixedZ": fixed_z,
            "homeZ": home_z,
            "engagedZ": engaged_z,
            "strokeMm": home_z - engaged_z,
            "defaultState": "open",
            "engagementGapMm": LEGACY_SCHEME1_CLUTCH_GAP_MM,
            "drawerCoupler": f"DrawerCouplerBody_L{cell['layer']:02d}_C{cell['col']:02d}_{drawer_index + 1:02d}",
            "drawerCouplerGear": f"DrawerCouplerGear_L{cell['layer']:02d}_C{cell['col']:02d}_{drawer_index + 1:02d}",
            "drawerCouplerAxis": {"x": coupler_x, "y": coupler_y, "z": cfg.base_height + cfg.drawer_height * 0.3},
            "drawerCouplerGearAxis": {"x": coupler_x, "y": coupler_y, "z": cfg.base_height + cfg.drawer_height * 0.88},
        })
    return records

def _clutches(doc, Part, App, cfg, path: dict) -> list[dict]:
    records = clutch_specs(cfg, path)
    for clutch in records:
        add_placed_shape(
            doc,
            App,
            clutch["fixed"],
            _dog_clutch_shape(Part, App, CLUTCH_FIXED_R, CLUTCH_FIXED_T),
            clutch["x"],
            clutch["y"],
            clutch["fixedZ"],
            BRONZE,
            0.05,
        )
        add_placed_shape(
            doc,
            App,
            clutch["sliding"],
            _dog_clutch_shape(Part, App, CLUTCH_SLIDING_R, CLUTCH_SLIDING_T),
            clutch["x"],
            clutch["y"],
            clutch["homeZ"],
            STEEL,
            0.0,
        )
    return records

# ===== 分区：公开 API =====
def build_snake_selector(doc, Part, App, cfg) -> dict[str, Any]:
    path = build_snake_path(cfg)
    drive = path["drive"]
    home = (path.get("loop") or path["working"])[0]
    motor_names = _nema17(doc, Part, App, drive)
    spool_names = [_spool(doc, Part, App, pulley) for pulley in path["pulleys"]]
    belt_name = _belt(doc, Part, App, path)
    fork = _fork(doc, Part, App, home)
    clutches = _clutches(doc, Part, App, cfg, path)
    axes = drive_axis_specs(cfg)
    rows = drive_mechanism_rows(cfg)
    animation = {
        "scheme": "scheme1-clutch-selective-drive",
        "mode": "snake",
        "speedMmS": cfg.selector_speed_mm_s,
        "driveRpm": cfg.drive_rpm,
        "targetIndex": cfg.target_index,
        "drive": drive,
        "working": path["working"],
        "loop": path["loop"],
        "anchors": path["anchors"],
        "workingLength": path["workingLength"],
        "loopLength": path["loopLength"],
        "beltTeeth": path["beltTeeth"],
        "wrapRanges": path["wrapRanges"],
        "pulleys": path["pulleys"],
        "segments": path["segments"],
        "cells": path["cells"],
        "order": path["order"],
        "carriage": fork,
        "drivePulley": spool_names[0],
        "motorShaft": "MotorMA_Shaft",
        "busParts": ["BusShaft_Main"] + [f"RowShaft_{layer:02d}" for layer in range(cfg.layers)],
        "driveAxes": axes,
        "rows": rows,
        "clutches": clutches,
        "powerPolicy": {
            "defaultOn": False,
            "engageOnlyWhenSelectorStopped": True,
            "activeTargetOnly": True,
            "releaseBeforeReturn": True,
        },
        "greenParts": fork["green"],
        "formula": {
            "teeth": HTD_DRIVE_TEETH,
            "pitchMm": HTD_PITCH_MM,
            "n": f"60v/({HTD_DRIVE_TEETH}×{HTD_PITCH_MM}mm)",
            "vDefault": cfg.selector_speed_mm_s,
            "rpmDefault": drive["rpmAtDefault"],
            "noSlip": "θ=s/R, R=z p / 2π",
        },
    }
    return {
        "path": path,
        "animation": animation,
        "names": motor_names + spool_names + [belt_name] + [p["name"] for p in fork["parts"]]
        + [name for clutch in clutches for name in (clutch["fixed"], clutch["sliding"])],
    }

def snake_selector_map(cfg, animation: dict | None) -> dict:
    payload = {
        "mode": "snake",
        "drive": "SelectorDrivePulley_20T",
        "belt": "SelectorBelt_HTD3M9",
        "finger": "SelectorFinger",
        "motor": "MotorMA_Case",
        "closed": True,
        "scheme": "scheme1-clutch-selective-drive",
        "powerPolicy": {
            "defaultOn": False,
            "engageOnlyWhenSelectorStopped": True,
            "activeTargetOnly": True,
            "releaseBeforeReturn": True,
        },
        "formula": f"n=60v/({HTD_DRIVE_TEETH}×{HTD_PITCH_MM}mm)  θ=s/R",
    }
    if animation:
        payload["anchors"] = animation.get("anchors")
        payload["workingLength"] = animation.get("workingLength")
        payload["loopLength"] = animation.get("loopLength")
        payload["beltTeeth"] = animation.get("beltTeeth")
        payload["greenParts"] = animation.get("greenParts")
        payload["driveAxes"] = animation.get("driveAxes")
        payload["rows"] = animation.get("rows")
        payload["cells"] = animation.get("cells")
        payload["clutches"] = [
            {
                "index": item["index"],
                "fixed": item["fixed"],
                "sliding": item["sliding"],
                "strokeMm": item.get("strokeMm", LEGACY_SCHEME1_CLUTCH_STROKE_MM),
                "fixedZ": item.get("fixedZ"),
                "homeZ": item.get("homeZ"),
                "engagedZ": item.get("engagedZ"),
                "defaultState": item.get("defaultState", "open"),
                "engagementGapMm": item.get("engagementGapMm"),
                "layer": item.get("layer"),
                "col": item.get("col"),
                "drawerCoupler": item.get("drawerCoupler"),
                "drawerCouplerGear": item.get("drawerCouplerGear"),
            }
            for item in animation.get("clutches", [])
        ]
        payload["driveRpm"] = animation.get("driveRpm")
    return payload

# ===== 分区：业务逻辑 =====
def apply_mechanism(doc, App, animation: dict, pose: dict) -> None:
    position = pose.get("position") or home_position(animation)
    for spec in animation.get("carriage", {}).get("parts") or []:
        obj = doc.getObject(spec["name"])
        if obj is None:
            continue
        obj.Placement = fork_placement(App, position)
    for spool in pose.get("spools") or []:
        obj = doc.getObject(spool["name"])
        if obj is None:
            continue
        width = spool["width"]
        obj.Placement = App.Placement(App.Vector(spool["x"], spool["y"], spool["z"] - width * 0.5), App.Rotation(App.Vector(0, 0, 1), spool["deg"]))
        if spool["name"] == animation.get("drivePulley"):
            shaft = doc.getObject(animation.get("motorShaft"))
            if shaft is not None:
                shaft.Placement = App.Placement(App.Vector(spool["x"], spool["y"], spool["z"] - width * 0.5 - 4.0), App.Rotation(App.Vector(0, 0, 1), spool["deg"]))

    active_index = pose.get("selectedIndex")
    if active_index is None and pose.get("engaged"):
        active_index = pose.get("targetIndex")
    try:
        active_index = int(active_index) if active_index is not None else None
    except (TypeError, ValueError):
        active_index = None
    engagement = max(0.0, min(1.0, float(pose.get("engagement", 1.0 if pose.get("engaged") else 0.0))))
    power_on = bool(pose.get("powerOn", pose.get("busOn", False))) and engagement >= 0.999
    # driveDeg is an absolute stopped-at-last-position angle.  power_on only
    # controls whether the motor is currently energized, not whether the
    # already-driven parts jump back to their home angle.
    drive_deg = float(pose.get("driveDeg", pose.get("rollerDeg", 0.0)) or 0.0)

    driven_index = pose.get("drivenIndex")
    if driven_index is None and power_on and drive_deg:
        driven_index = active_index
    try:
        driven_index = int(driven_index) if driven_index is not None else None
    except (TypeError, ValueError):
        driven_index = None

    # Scheme 1: every station is open by default; only the selected slider is
    # stroked after the selector has stopped.  The fixed dog and drawer take-off
    # keep the last drive angle after power is removed; no other drawer receives
    # torque.
    for clutch in animation.get("clutches") or []:
        selected = active_index is not None and clutch.get("index") == active_index
        driven = driven_index is not None and clutch.get("index") == driven_index
        slide_z = clutch["homeZ"]
        if selected:
            slide_z = clutch["homeZ"] + (clutch["engagedZ"] - clutch["homeZ"]) * engagement
        fixed = doc.getObject(clutch.get("fixed"))
        sliding = doc.getObject(clutch.get("sliding"))
        if fixed is not None:
            _set_axis_placement(App, fixed, clutch["x"], clutch["y"], clutch["fixedZ"], drive_deg if driven else 0.0)
            _paint_clutch(fixed, active=selected and engagement > 0.01, engaged=selected and engagement >= 0.999)
        if sliding is not None:
            _set_axis_placement(App, sliding, clutch["x"], clutch["y"], slide_z, drive_deg if driven else 0.0)
            _paint_clutch(sliding, active=selected and engagement > 0.01, engaged=selected and engagement >= 0.999)

    axes = animation.get("driveAxes") or {}
    motor = axes.get("motor") or {}
    bus = axes.get("bus") or {}
    if motor:
        _set_axis_object(doc, App, motor.get("shaft"), motor.get("x"), motor.get("y"), motor.get("shaftZ"), drive_deg)
        _set_axis_object(doc, App, motor.get("gear"), motor.get("x"), motor.get("y"), motor.get("gearZ"), drive_deg)
    if bus:
        _set_axis_object(doc, App, bus.get("shaft"), bus.get("x"), bus.get("y"), bus.get("z"), drive_deg)

    active_layer = None
    active_clutch = next(
        (
            item
            for item in animation.get("clutches") or []
            if item.get("index") in {active_index, driven_index}
        ),
        None,
    )
    if active_clutch is not None:
        active_layer = active_clutch.get("layer")
    for row in axes.get("rows") or []:
        row_active = driven_index is not None and active_layer is not None and row.get("layer") == active_layer
        row_deg = drive_deg if row_active else 0.0
        _set_axis_object(doc, App, row.get("shaft"), row.get("x"), row.get("y"), row.get("shaftZ"), row_deg)
        _set_axis_object(doc, App, row.get("gear"), row.get("x"), row.get("y"), row.get("gearZ"), row_deg)

    for clutch in animation.get("clutches") or []:
        drawer_active = clutch.get("index") == driven_index
        angle = drive_deg if drawer_active else 0.0
        axis = clutch.get("drawerCouplerAxis") or {}
        gear_axis = clutch.get("drawerCouplerGearAxis") or {}
        _set_axis_object(doc, App, clutch.get("drawerCoupler"), axis.get("x"), axis.get("y"), axis.get("z"), angle)
        _set_axis_object(doc, App, clutch.get("drawerCouplerGear"), gear_axis.get("x"), gear_axis.get("y"), gear_axis.get("z"), angle)

def apply_carriage_pose(doc, App, animation: dict, position: dict, engaged: bool) -> None:
    apply_mechanism(doc, App, animation, {"position": position, "engaged": engaged, "engagement": 1.0 if engaged else 0.0, "spools": [], "teeth": [], "progress": 0, "busOn": False, "powerOn": False, "targetIndex": 0, "rollerDeg": 0.0})

def apply_pulley_pose(doc, App, animation: dict, pulley_deg: float) -> None:
    drive = animation["drive"]
    apply_mechanism(doc, App, animation, {
        "position": (animation.get("working") or [{}])[0],
        "engaged": False,
        "engagement": 0.0,
        "spools": [{"name": animation.get("drivePulley"), "x": drive["x"], "y": drive["y"], "z": drive["z"], "width": drive.get("width") or 12.0, "deg": pulley_deg}],
        "teeth": [],
        "progress": 0,
        "busOn": False,
        "targetIndex": 0,
        "rollerDeg": 0.0,
    })

def apply_bus_pose(doc, App, animation: dict, bus_deg: float) -> None:
    apply_mechanism(doc, App, animation, {
        "position": home_position(animation),
        "engaged": True,
        "engagement": 1.0,
        "powerOn": True,
        "busOn": True,
        "targetIndex": animation.get("targetIndex"),
        "selectedIndex": animation.get("targetIndex"),
        "driveDeg": bus_deg,
        "spools": [],
    })

def apply_clutch_pose(doc, App, animation: dict, target_index: int, engaged: bool) -> None:
    apply_mechanism(doc, App, animation, {
        "position": home_position(animation),
        "engaged": engaged,
        "engagement": 1.0 if engaged else 0.0,
        "powerOn": False,
        "busOn": False,
        "targetIndex": target_index,
        "selectedIndex": target_index if engaged else None,
        "drivenIndex": target_index if engaged else None,
        "driveDeg": 0.0,
        "spools": [],
    })

def _set_axis_placement(App, obj, x: float, y: float, z: float, angle_deg: float) -> None:
    if obj is None or x is None or y is None or z is None:
        return
    obj.Placement = App.Placement(
        App.Vector(float(x), float(y), float(z)),
        App.Rotation(App.Vector(0, 0, 1), float(angle_deg)),
    )

def _set_axis_object(doc, App, name: str | None, x, y, z, angle_deg: float) -> None:
    if not name:
        return
    _set_axis_placement(App, doc.getObject(name), x, y, z, angle_deg)

def _paint_clutch(obj, active: bool, engaged: bool) -> None:
    try:
        obj.ViewObject.ShapeColor = (1.0, 0.62, 0.12) if engaged else ((0.95, 0.80, 0.28) if active else (0.58, 0.64, 0.70))
    except Exception:
        pass

# ===== 分区：方法/工具 =====
def home_position(animation: dict) -> dict:
    loop = animation.get("loop") or animation.get("working") or []
    return loop[0] if loop else {"x": 0.0, "y": 0.0, "z": 0.0, "tx": 1.0, "ty": 0.0, "nx": 0.0, "ny": 1.0, "s": 0.0}

def fork_placement(App, position: dict):
    tx, ty = float(position.get("tx") or 1.0), float(position.get("ty") or 0.0)
    nx = float(position.get("nx") if position.get("nx") is not None else ty)
    ny = float(position.get("ny") if position.get("ny") is not None else -tx)
    mag = math.hypot(nx, ny) or 1.0
    nx, ny = nx / mag, ny / mag
    x = float(position.get("x") or 0.0) + nx * FORK_CLEAR_MM
    y = float(position.get("y") or 0.0) + ny * FORK_CLEAR_MM
    z = float(position.get("z") or 0.0) + FORK_LIFT_MM
    yaw = math.degrees(math.atan2(ty, tx))
    return App.Placement(App.Vector(x, y, z), App.Rotation(App.Vector(0, 0, 1), yaw))
