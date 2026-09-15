#!/usr/bin/env python3
"""抽屉格与滑轨。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

from fc_primitives import add_box, add_cylinder, add_placed_gear_disc

# ===== 分区：常量/配置 =====
DRAWER_BODY_COLOR = (175, 153, 123)
FRONT_COLOR = (120, 130, 145)
SLIDE_COLOR = (210, 210, 220)
COUPLER_COLOR = (95, 95, 95)
PIN_COLOR = (190, 180, 165)

# ===== 分区：模型/类型 =====
# drawer_map 项与 mechanismMap.drawerCouplers 对齐。

# ===== 分区：私有成员 =====
# 无额外私有状态。

# ===== 分区：公开 API =====
def build_drawers_and_tracks(doc, Part, App, cfg):
    items = []
    drawer_map = []
    for layer in range(cfg.layers):
        y = cfg.margin_y + layer * (cfg.cell_depth + cfg.cell_gap_y)
        for col in range(cfg.columns):
            idx = layer * cfg.columns + col
            x = cfg.margin_x + col * (cfg.cell_width + cfg.cell_gap_x)
            label = f"{idx + 1:02d}"
            prefix = f"L{layer:02d}_C{col:02d}"
            body_name = f"DrawerBody_{prefix}_{label}"
            front_name = f"DrawerFrontPanel_{prefix}_{label}"
            slide_a_name = f"DrawerGuideLeft_{prefix}_{label}"
            slide_b_name = f"DrawerGuideRight_{prefix}_{label}"
            coupler_name = f"DrawerCouplerBody_{prefix}_{label}"
            coupler_gear_name = f"DrawerCouplerGear_{prefix}_{label}"
            selector_pin_name = f"DrawerSelectionPin_{prefix}_{label}"
            tray = add_box(doc, App, body_name, x, y, cfg.base_height + cfg.rail_depth * 0.25, cfg.cell_width, cfg.cell_depth, cfg.drawer_height, DRAWER_BODY_COLOR, 0.08)
            front = add_box(doc, App, front_name, x + 4.0, y + 5.0, cfg.base_height + cfg.rail_depth * 0.25, cfg.cell_width - 8.0, 4.8, 5.2, FRONT_COLOR, 0.1)
            slide_a = add_box(doc, App, slide_a_name, x + cfg.slide_inset, y - cfg.slide_depth, cfg.base_height, cfg.cell_width - cfg.slide_inset * 2, cfg.slide_depth, cfg.slide_depth * 0.22, SLIDE_COLOR, 0.24)
            slide_b = add_box(doc, App, slide_b_name, x + cfg.slide_inset, y + cfg.cell_depth + cfg.slide_depth * 0.15, cfg.base_height, cfg.cell_width - cfg.slide_inset * 2, cfg.slide_depth, cfg.slide_depth * 0.22, SLIDE_COLOR, 0.24)
            coupler_x = x + cfg.cell_width * 0.12
            coupler_y = y + cfg.cell_depth * 0.17
            coupler_z = cfg.base_height + cfg.drawer_height * 0.88
            coupler = add_cylinder(doc, App, coupler_name, coupler_x, coupler_y, cfg.base_height + cfg.drawer_height * 0.3, cfg.coupler_radius, cfg.drawer_height * 0.88, COUPLER_COLOR, 0.0)
            # Keep this gear in local coordinates so scheme 1 can rotate it
            # about its own take-off axis without accumulating a world transform.
            add_placed_gear_disc(doc, Part, App, coupler_gear_name, coupler_x, coupler_y, coupler_z, cfg.coupler_radius * 1.04, cfg.gear_thickness * 0.72, 12, (220, 185, 95))
            add_cylinder(doc, App, selector_pin_name, x + cfg.cell_width * 0.76, y + cfg.cell_depth * 0.2, cfg.base_height + cfg.drawer_height * 0.62, 1.6, cfg.drawer_height * 0.45, PIN_COLOR, 0.15)
            items.extend((tray, front, slide_a, slide_b, coupler))
            drawer_map.append({
                "drawerId": f"{idx + 1}",
                "label": label,
                "layer": layer,
                "col": col,
                "origin": {"x": x, "y": y, "z": cfg.base_height + cfg.rail_depth * 0.25},
                "body": body_name,
                "frontPanel": front_name,
                "slideLeft": slide_a_name,
                "slideRight": slide_b_name,
                "couplerBody": coupler_name,
                "couplerGear": coupler_gear_name,
                "couplerAxis": {"x": coupler_x, "y": coupler_y, "z": cfg.base_height + cfg.drawer_height * 0.3},
                "couplerGearAxis": {"x": coupler_x, "y": coupler_y, "z": coupler_z},
                "selectionPin": selector_pin_name,
            })
    return items, drawer_map

# ===== 分区：业务逻辑 =====
def empty_drawer_map(cfg) -> list[dict]:
    drawer_map = []
    for layer in range(cfg.layers):
        y = cfg.margin_y + layer * (cfg.cell_depth + cfg.cell_gap_y)
        for col in range(cfg.columns):
            idx = layer * cfg.columns + col
            x = cfg.margin_x + col * (cfg.cell_width + cfg.cell_gap_x)
            label = f"{idx + 1:02d}"
            prefix = f"L{layer:02d}_C{col:02d}"
            drawer_map.append({
                "drawerId": f"{idx + 1}",
                "label": label,
                "layer": layer,
                "col": col,
                "origin": {"x": x, "y": y, "z": cfg.base_height + cfg.rail_depth * 0.25},
                "body": f"DrawerBody_{prefix}_{label}",
                "frontPanel": f"DrawerFrontPanel_{prefix}_{label}",
                "slideLeft": f"DrawerGuideLeft_{prefix}_{label}",
                "slideRight": f"DrawerGuideRight_{prefix}_{label}",
                "couplerBody": f"DrawerCouplerBody_{prefix}_{label}",
                "couplerGear": f"DrawerCouplerGear_{prefix}_{label}",
                "couplerAxis": {"x": x + cfg.cell_width * 0.12, "y": y + cfg.cell_depth * 0.17, "z": cfg.base_height + cfg.drawer_height * 0.3},
                "couplerGearAxis": {"x": x + cfg.cell_width * 0.12, "y": y + cfg.cell_depth * 0.17, "z": cfg.base_height + cfg.drawer_height * 0.88},
                "selectionPin": f"DrawerSelectionPin_{prefix}_{label}",
            })
    return drawer_map

# ===== 分区：方法/工具 =====
def cell_origin(cfg, col: int, layer: int) -> tuple[float, float]:
    x = cfg.margin_x + col * (cfg.cell_width + cfg.cell_gap_x)
    y = cfg.margin_y + layer * (cfg.cell_depth + cfg.cell_gap_y)
    return x, y
