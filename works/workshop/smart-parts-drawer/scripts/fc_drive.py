#!/usr/bin/env python3
"""共用动力总线：固定 M-B 与分层取力轴。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

from fc_primitives import add_box, add_cylinder, add_placed_gear_disc, set_color

# ===== 分区：常量/配置 =====
BUS_ORANGE = (255, 173, 102)
MOTOR_GRAY = (120, 120, 132)
SHAFT_COLOR = (72, 84, 99)
RAIL_COLOR = (150, 160, 170)

# ===== 分区：模型/类型 =====
# 现有 MotorA_* 对应柜体后部 M-B，选择电机 M-A 由蛇形模块另行创建。

# ===== 分区：私有成员 =====
def _motor_xy(cfg) -> tuple[float, float]:
    motor_x = cfg.margin_x * 0.6
    depth_total = cfg.depth_total or (2 * cfg.margin_y + cfg.layers * cfg.cell_depth + max(0, cfg.layers - 1) * cfg.cell_gap_y)
    motor_y = depth_total - cfg.wall_thickness - 2.6
    return motor_x, motor_y

def drive_axis_specs(cfg) -> dict:
    """Return the fixed-axis coordinates used by the selective clutch drive."""
    motor_x, motor_y = _motor_xy(cfg)
    depth_total = cfg.depth_total or (2 * cfg.margin_y + cfg.layers * cfg.cell_depth + max(0, cfg.layers - 1) * cfg.cell_gap_y)
    bus_y = depth_total - cfg.wall_thickness - cfg.rail_inset_y
    row_span = max(0.0, (cfg.columns - 1) * (cfg.cell_width + cfg.cell_gap_x))
    row_center_x = cfg.margin_x + cfg.rail_start_x + row_span * 0.5
    return {
        "motor": {
            "shaft": "MotorA_Shaft",
            "gear": "MotorA_Gear",
            "x": motor_x,
            "y": motor_y,
            "shaftZ": cfg.base_height + cfg.motor_length * 0.18,
            "gearZ": cfg.base_height + cfg.motor_length * 0.56,
        },
        "bus": {
            "shaft": "BusShaft_Main",
            "x": cfg.margin_x + cfg.rail_start_x + row_span * 0.5,
            "y": bus_y,
            "z": cfg.base_height + cfg.rail_depth * 0.24,
        },
        "rows": [
            {
                "layer": layer,
                "shaft": f"RowShaft_{layer:02d}",
                "gear": f"RowCouplerGear_{layer:02d}",
                "x": row_center_x,
                "y": cfg.margin_y + layer * (cfg.cell_depth + cfg.cell_gap_y) + cfg.cell_depth * 0.5,
                "shaftZ": cfg.base_height + cfg.rail_depth * 0.22,
                "gearZ": cfg.base_height + cfg.rail_depth * 0.18,
            }
            for layer in range(cfg.layers)
        ],
    }

# ===== 分区：公开 API =====
def build_drive_chain(doc, Part, App, cfg):
    motor_x, motor_y = _motor_xy(cfg)
    bus_y = cfg.depth_total - cfg.wall_thickness - cfg.rail_inset_y
    add_box(doc, App, "MotorA_Case", motor_x - 10, motor_y - 9, cfg.base_height, 20.0, 16.0, cfg.motor_length, MOTOR_GRAY, 0.05)
    add_cylinder(doc, App, "MotorA_Shaft", motor_x, motor_y, cfg.base_height + cfg.motor_length * 0.18, cfg.motor_shaft_radius, cfg.motor_shaft_height, (80, 80, 85), 0.0)
    add_placed_gear_disc(doc, Part, App, "MotorA_Gear", motor_x, motor_y, cfg.base_height + cfg.motor_length * 0.56, cfg.motor_tooth_radius, cfg.gear_thickness, 18, (205, 165, 95))
    add_box(doc, App, "MotorA_Bracket", motor_x - 11, motor_y - 11, cfg.base_height + cfg.motor_length + 2, 22.0, 8.0, 3.2, (95, 102, 118), 0.12)
    casing = add_box(
        doc,
        App,
        "BusShaft_Casing",
        cfg.margin_x + cfg.rail_start_x - 6.0,
        bus_y - 3.5,
        cfg.base_height + cfg.rail_depth * 0.24,
        cfg.columns * (cfg.cell_width + cfg.cell_gap_x) - 3.2,
        6.0,
        cfg.rail_depth * 0.26,
        (108, 120, 133),
        0.16,
    )
    bus = add_cylinder(
        doc,
        App,
        "BusShaft_Main",
        cfg.margin_x + cfg.rail_start_x + (cfg.columns - 1) * (cfg.cell_width + cfg.cell_gap_x) * 0.5,
        bus_y,
        cfg.base_height + cfg.rail_depth * 0.24 + cfg.rail_depth * 0.22,
        2.1,
        cfg.rail_depth * 1.9,
        SHAFT_COLOR,
        0.0,
    )
    if cfg.selector_mode == "snake":
        set_color(casing, BUS_ORANGE, 0.18)
        set_color(bus, BUS_ORANGE, 0.0)
        add_box(doc, App, "MotorMB_LabelBlock", motor_x - 8.0, motor_y - 14.0, cfg.base_height + cfg.motor_length + 6.0, 16.0, 4.0, 2.0, BUS_ORANGE, 0.0)
    for layer in range(cfg.layers):
        row_y = cfg.margin_y + layer * (cfg.cell_depth + cfg.cell_gap_y) + cfg.cell_depth * 0.5
        row_center_x = cfg.margin_x + cfg.rail_start_x + ((cfg.columns - 1) * (cfg.cell_width + cfg.cell_gap_x)) * 0.5
        add_cylinder(doc, App, f"RowShaft_{layer:02d}", row_center_x, row_y, cfg.base_height + cfg.rail_depth * 0.22, 2.1, cfg.rail_depth * 0.45, BUS_ORANGE if cfg.selector_mode == "snake" else SHAFT_COLOR, 0.0)
        add_placed_gear_disc(doc, Part, App, f"RowCouplerGear_{layer:02d}", row_center_x, row_y, cfg.base_height + cfg.rail_depth * 0.18, cfg.motor_tooth_radius * 0.72, cfg.gear_thickness * 0.55, 14, BUS_ORANGE if cfg.selector_mode == "snake" else (172, 142, 90))
        for i in range(cfg.columns + 1):
            x = cfg.margin_x + i * (cfg.cell_width + cfg.cell_gap_x) - 2.1
            add_box(doc, App, f"RowRail_{layer:02d}_{i:02d}", x, row_y - 0.8, cfg.base_height + cfg.rail_depth * 0.24, cfg.rail_width, cfg.cell_depth * 1.2, cfg.rail_depth * 0.24, RAIL_COLOR, 0.2)
            add_box(doc, App, f"RowRailBeltPad_{layer:02d}_{i:02d}", x, row_y + cfg.cell_depth * 1.2 * 0.48, cfg.base_height + cfg.rail_depth * 0.22, cfg.rail_width * 0.76, 1.9, 1.5, (120, 130, 146), 0.2)

# ===== 分区：业务逻辑 =====
def drive_mechanism_rows(cfg) -> list[dict]:
    cell_pitch_x = cfg.cell_width + cfg.cell_gap_x
    rail_span = max(0.0, (cfg.columns - 1) * cell_pitch_x)
    rows = []
    for layer in range(cfg.layers):
        row_y = cfg.margin_y + layer * (cfg.cell_depth + cfg.cell_gap_y) + cfg.cell_depth * 0.5
        row_center_x = cfg.margin_x + cfg.rail_start_x + rail_span * 0.5
        rows.append({
            "layer": layer,
            "rowShaft": f"RowShaft_{layer:02d}",
            "rowCouplerGear": f"RowCouplerGear_{layer:02d}",
            "centerX": row_center_x,
            "centerY": row_y,
            "shaftZ": cfg.base_height + cfg.rail_depth * 0.22,
            "gearZ": cfg.base_height + cfg.rail_depth * 0.18,
            "railRange": {
                "startX": cfg.margin_x + cfg.rail_start_x - 6.0,
                "endX": cfg.margin_x + cfg.rail_start_x + rail_span + 6.0,
                "z": cfg.base_height + cfg.rail_depth * 0.24,
            },
            "railPositions": [
                {
                    "index": i,
                    "railName": f"RowRail_{layer:02d}_{i:02d}",
                    "padName": f"RowRailBeltPad_{layer:02d}_{i:02d}",
                    "x": cfg.margin_x + i * cell_pitch_x - 2.1,
                }
                for i in range(cfg.columns + 1)
            ],
        })
    return rows

# ===== 分区：方法/工具 =====
def bus_center(cfg) -> tuple[float, float]:
    bus_y = cfg.depth_total - cfg.wall_thickness - cfg.rail_inset_y
    bus_x = cfg.margin_x + cfg.rail_start_x + (cfg.columns - 1) * (cfg.cell_width + cfg.cell_gap_x) * 0.5
    return bus_x, bus_y
