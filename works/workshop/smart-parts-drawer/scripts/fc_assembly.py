#!/usr/bin/env python3
"""组装柜体、抽屉、总线与选择机构。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

from fc_config import compute_geometry_totals
from fc_drawers import build_drawers_and_tracks, empty_drawer_map
from fc_drive import build_drive_chain, drive_axis_specs, drive_mechanism_rows
from fc_motion import build_selector_motion_profile, selector_origin
from fc_primitives import add_box
from fc_selectors import build_legacy_selector, legacy_selector_map
from fc_snake_parts import build_snake_selector, clutch_specs, snake_selector_map

# ===== 分区：常量/配置 =====
CABINET_BASE = (49, 63, 80)
CABINET_SHELL = (66, 79, 95)
WALL_COLOR = (102, 93, 84)

# ===== 分区：模型/类型 =====
# build_mechanism 返回 (doc, width, depth, mechanism_map, animation|None)

# ===== 分区：私有成员 =====
def _cabinet(doc, App, cfg, width_total: float, depth_total: float) -> None:
    add_box(doc, App, "CabinetBase", 0, 0, 0, width_total, depth_total, cfg.base_height, CABINET_BASE, 0.0)
    add_box(doc, App, "CabinetShell", 0, 0, cfg.base_height, width_total, depth_total, cfg.shell_height, CABINET_SHELL, 0.82)
    add_box(doc, App, "FrontWall", 0, 0, cfg.base_height, width_total, cfg.wall_thickness, cfg.shell_height, WALL_COLOR, 0.05)
    add_box(doc, App, "BackWall", 0, depth_total - cfg.wall_thickness, cfg.base_height, width_total, cfg.wall_thickness, cfg.shell_height, WALL_COLOR, 0.05)

# ===== 分区：公开 API =====
def build_mechanism_map(cfg, drawer_map: list, selector_origin_xy: tuple[float, float] = (0.0, 0.0), animation=None) -> dict:
    width_total, depth_total = compute_geometry_totals(cfg)
    if not drawer_map:
        drawer_map = empty_drawer_map(cfg)
    if cfg.selector_mode == "snake":
        selector = snake_selector_map(cfg, animation)
    else:
        selector = legacy_selector_map(cfg)
    selector["motionProfile"] = build_selector_motion_profile(cfg, selector_origin_xy[0], selector_origin_xy[1])
    drive_chain = {
        "motor": {"case": "MotorA_Case", "shaft": "MotorA_Shaft", "gear": "MotorA_Gear", "bracket": "MotorA_Bracket"},
        "selectorMotor": {"case": "MotorMA_Case", "shaft": "MotorMA_Shaft"} if cfg.selector_mode == "snake" else None,
        "busShaft": {"casing": "BusShaft_Casing", "shaft": "BusShaft_Main"},
        "rows": drive_mechanism_rows(cfg),
        "dimensions": {"widthTotal": width_total, "depthTotal": depth_total, "rowSpan": max(0.0, (cfg.columns - 1) * (cfg.cell_width + cfg.cell_gap_x))},
    }
    if cfg.selector_mode == "snake":
        drive_chain.update({
            "scheme": "scheme1-clutch-selective-drive",
            "powerPolicy": {
                "defaultOn": False,
                "engageOnlyWhenSelectorStopped": True,
                "activeTargetOnly": True,
                "releaseBeforeReturn": True,
            },
            "axes": drive_axis_specs(cfg),
        })
    return {
        "drawerCouplers": drawer_map,
        "driveChain": drive_chain,
        "selector": selector,
    }

def build_mechanism(App, Part, cfg):
    doc = App.newDocument("SmartPartsDrawer")
    width_total, depth_total = compute_geometry_totals(cfg)
    cfg.depth_total = depth_total
    cfg.width_total = width_total
    _cabinet(doc, App, cfg, width_total, depth_total)
    _, drawer_map = build_drawers_and_tracks(doc, Part, App, cfg)
    build_drive_chain(doc, Part, App, cfg)
    origin_x, origin_y = selector_origin(cfg)
    animation = None
    if cfg.selector_mode == "snake":
        built = build_snake_selector(doc, Part, App, cfg)
        animation = built["animation"]
    else:
        build_legacy_selector(doc, App, cfg, origin_x, origin_y, 0)
    doc.recompute()
    mechanism_map = build_mechanism_map(cfg, drawer_map, (origin_x, origin_y), animation)
    return doc, width_total, depth_total, mechanism_map, animation

# ===== 分区：业务逻辑 =====
def preview_mechanism_map(cfg) -> dict:
    origin_x, origin_y = selector_origin(cfg)
    animation = None
    if cfg.selector_mode == "snake":
        from fc_snake_path import build_snake_path
        path = build_snake_path(cfg)
        animation = {
            "scheme": "scheme1-clutch-selective-drive",
            "driveRpm": cfg.drive_rpm,
            "anchors": path["anchors"],
            "cells": path["cells"],
            "workingLength": path["workingLength"],
            "loopLength": path["loopLength"],
            "greenParts": ["SelectorFinger", "SelectorContactPin"],
            "clutches": clutch_specs(cfg, path),
            "powerPolicy": {
                "defaultOn": False,
                "engageOnlyWhenSelectorStopped": True,
                "activeTargetOnly": True,
                "releaseBeforeReturn": True,
            },
        }
    return build_mechanism_map(cfg, [], (origin_x, origin_y), animation)

# ===== 分区：方法/工具 =====
def document_label() -> str:
    return "SmartPartsDrawer"
