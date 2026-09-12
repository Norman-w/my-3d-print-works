#!/usr/bin/env python3
"""蛇形 HTD3M-9：闭带贴节圆包角，绿色拨叉是带子上的固定夹具。"""

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
    make_rect_belt,
)
from fc_snake_path import build_snake_path

# ===== 分区：常量/配置 =====
CYAN = (53, 169, 212)
GREEN = (90, 210, 92)
ORANGE = (255, 173, 102)
STEEL = (168, 176, 184)
MOTOR = (72, 80, 90)
BRONZE = (168, 108, 63)
NEMA_BOLT_CIRCLE = 31.0
CLUTCH_STROKE_MM = 3.0
FORK_CLEAR_MM = 7.0
FORK_LIFT_MM = 9.0

# ===== 分区：模型/类型 =====
# animation 含 pulleys / loop / fork，apply_mechanism 只转带轮并移动拨叉夹具。

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
    body = Part.makeBox(10.0, 8.0, 6.0, App.Vector(-5.0, -4.0, 0.0))
    mast = Part.makeBox(4.0, 4.0, 12.0, App.Vector(-2.0, -2.0, 5.0))
    add_placed_shape(doc, App, "SelectorFinger", body.fuse(mast), 0.0, 0.0, 0.0, GREEN, 0.0)
    spec = {"name": "SelectorFinger", "lx": 0.0, "ly": 0.0, "lz": 0.0, "yaw": 0.0, "spin": False}
    doc.getObject(spec["name"]).Placement = fork_placement(App, home)
    return {"parts": [spec], "green": ["SelectorFinger"]}

def _clutches(doc, Part, App, cfg, path: dict) -> list[dict]:
    records = []
    for cell in path["cells"]:
        x = cell["x"]
        y = cell["y"] + cfg.cell_depth * 0.38
        z = cell["z"] - 4.0
        prefix = f"L{cell['layer']:02d}_C{cell['col']:02d}"
        fixed_name = f"ClutchFixed_{prefix}"
        sliding_name = f"ClutchSliding_{prefix}"
        add_cylinder(doc, App, fixed_name, x, y, z, 7.4, 4.0, BRONZE, 0.05)
        sliding = add_cylinder(doc, App, sliding_name, x, y, z + 4.2, 6.6, 3.6, STEEL, 0.0)
        records.append({
            "index": cell["index"],
            "fixed": fixed_name,
            "sliding": sliding_name,
            "x": x,
            "y": y,
            "homeZ": sliding.Placement.Base.z,
            "engagedZ": sliding.Placement.Base.z + CLUTCH_STROKE_MM,
        })
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
    animation = {
        "mode": "snake",
        "speedMmS": cfg.selector_speed_mm_s,
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
        "clutches": [],
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
        "names": motor_names + spool_names + [belt_name] + [p["name"] for p in fork["parts"]],
    }

def snake_selector_map(cfg, animation: dict | None) -> dict:
    payload = {
        "mode": "snake",
        "drive": "SelectorDrivePulley_20T",
        "belt": "SelectorBelt_HTD3M9",
        "finger": "SelectorFinger",
        "motor": "MotorMA_Case",
        "closed": True,
        "formula": f"n=60v/({HTD_DRIVE_TEETH}×{HTD_PITCH_MM}mm)  θ=s/R",
    }
    if animation:
        payload["anchors"] = animation.get("anchors")
        payload["workingLength"] = animation.get("workingLength")
        payload["loopLength"] = animation.get("loopLength")
        payload["beltTeeth"] = animation.get("beltTeeth")
        payload["greenParts"] = animation.get("greenParts")
        payload["clutches"] = [item["sliding"] for item in animation.get("clutches", [])]
    return payload

# ===== 分区：业务逻辑 =====
def apply_mechanism(doc, App, animation: dict, pose: dict) -> None:
    position = pose["position"]
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

def apply_carriage_pose(doc, App, animation: dict, position: dict, engaged: bool) -> None:
    apply_mechanism(doc, App, animation, {"position": position, "engaged": engaged, "spools": [], "teeth": [], "progress": 0, "busOn": False, "targetIndex": 0, "rollerDeg": 0.0})

def apply_pulley_pose(doc, App, animation: dict, pulley_deg: float) -> None:
    drive = animation["drive"]
    apply_mechanism(doc, App, animation, {
        "position": (animation.get("working") or [{}])[0],
        "engaged": False,
        "spools": [{"name": animation.get("drivePulley"), "x": drive["x"], "y": drive["y"], "z": drive["z"], "width": drive.get("width") or 12.0, "deg": pulley_deg}],
        "teeth": [],
        "progress": 0,
        "busOn": False,
        "targetIndex": 0,
        "rollerDeg": 0.0,
    })

def apply_bus_pose(doc, App, animation: dict, bus_deg: float) -> None:
    return

def apply_clutch_pose(doc, App, animation: dict, target_index: int, engaged: bool) -> None:
    return

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
