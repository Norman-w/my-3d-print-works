#!/usr/bin/env python3
"""凸轮 / 傅里叶 / 离心选择机构（保持原骨架，默认入口改为蛇形）。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import math

from fc_primitives import add_box, add_cylinder

# ===== 分区：常量/配置 =====
CARRIER_COLOR = (72, 122, 145)
FOURIER_COLOR = (190, 122, 118)
CAM_COLOR = (225, 185, 95)
CENTRIF_HOUSING = (87, 103, 122)

# ===== 分区：模型/类型 =====
# 非 snake 模式仍使用原 SelectorCarrier 覆盖盒与特征件。

# ===== 分区：私有成员 =====
def _add_carrier(doc, App, cfg, x0: float, y0: float, z0: float):
    add_box(
        doc,
        App,
        "SelectorCarrier",
        x0,
        y0,
        z0 + cfg.base_height,
        cfg.selector_length,
        cfg.selector_length * 0.82,
        cfg.selector_height,
        CARRIER_COLOR,
        0.1,
    )

# ===== 分区：公开 API =====
def build_legacy_selector(doc, App, cfg, x0: float, y0: float, z0: float):
    _add_carrier(doc, App, cfg, x0, y0, z0)
    if cfg.selector_mode == "fourier":
        for i in range(cfg.fourier_ridges):
            t = (2 * math.pi / cfg.fourier_ridges) * i
            x = x0 + 12 + (cfg.selector_length - 20) * i / max(1, cfg.fourier_ridges - 1)
            y = y0 + 0.5 * cfg.selector_length + math.cos(3 * t) * cfg.selector_length * 0.12
            add_box(doc, App, f"SelectorFourierRidge_{i:02d}", x, y, z0 + cfg.base_height + cfg.selector_height * 0.42, 10.0, cfg.selector_link_width, cfg.selector_ridge_depth, FOURIER_COLOR, 0.2)
        return
    if cfg.selector_mode == "centrifugal":
        add_box(doc, App, "SelectorCentrifugalHousing", x0 + cfg.selector_length * 0.18, y0 + cfg.selector_length * 0.12, z0 + cfg.base_height + cfg.selector_height * 0.08, cfg.selector_length * 0.74, cfg.selector_length * 0.74, cfg.selector_height * 0.78, CENTRIF_HOUSING, 0.06)
        add_cylinder(doc, App, "SelectorCentrifugalCore", x0 + cfg.selector_length * 0.5, y0 + cfg.selector_length * 0.55, z0 + cfg.base_height + cfg.selector_height * 0.09, cfg.selector_length * 0.29, cfg.selector_height * 0.7, (108, 120, 140), 0.04)
        for i in range(cfg.fourier_ridges):
            angle = (360.0 / max(1, cfg.fourier_ridges)) * i
            x = x0 + cfg.selector_length * 0.5 + math.cos(math.radians(angle)) * cfg.selector_length * 0.34
            y = y0 + cfg.selector_length * 0.55 + math.sin(math.radians(angle)) * cfg.selector_length * 0.34 * 0.82
            add_box(doc, App, f"SelectorCentrifugalRib_{i:02d}", x, y, z0 + cfg.base_height + cfg.selector_height * 0.45, 8.2, 3.6, cfg.selector_ridge_depth, (196, 125, 120), 0.22)
            add_box(doc, App, f"SelectorCentrifugalContact_{i:02d}", x + 2.7, y + 0.9, z0 + cfg.base_height + cfg.selector_height * 0.45 + 0.35, 1.2, 1.2, 2.2, (235, 220, 165), 0.15)
        return
    for i in range(cfg.cam_pins):
        add_cylinder(doc, App, f"SelectorCamPin_{i:02d}", x0 + 10 + 7.5 * i, y0 + cfg.selector_length * 0.55, z0 + cfg.base_height + cfg.selector_height * 0.34, 3.2, cfg.selector_ridge_depth * 1.2, CAM_COLOR, 0.1)

# ===== 分区：业务逻辑 =====
def legacy_selector_map(cfg) -> dict:
    selector = {"mode": cfg.selector_mode, "carrier": "SelectorCarrier"}
    if cfg.selector_mode == "fourier":
        selector["segments"] = cfg.fourier_ridges
        selector["features"] = [f"SelectorFourierRidge_{i:02d}" for i in range(cfg.fourier_ridges)]
    elif cfg.selector_mode == "centrifugal":
        selector["featureCount"] = cfg.fourier_ridges
        selector["ribs"] = [f"SelectorCentrifugalRib_{i:02d}" for i in range(cfg.fourier_ridges)]
        selector["contacts"] = [f"SelectorCentrifugalContact_{i:02d}" for i in range(cfg.fourier_ridges)]
        selector["housing"] = "SelectorCentrifugalHousing"
        selector["core"] = "SelectorCentrifugalCore"
    else:
        selector["pins"] = [f"SelectorCamPin_{i:02d}" for i in range(cfg.cam_pins)]
    return selector

# ===== 分区：方法/工具 =====
def selector_patterns(cfg) -> list[str]:
    if cfg.selector_mode == "snake":
        return [
            "MotorMA_*",
            "SelectorDrivePulley_20T",
            "SelectorBelt_HTD3M9",
            "SelectorGuide*",
            "SelectorIdler*",
            "SelectorCarriage*",
            "SelectorFinger",
            "SelectorContactPin",
            "ClutchFixed_*",
            "ClutchSliding_*",
            "Fastener_*",
        ]
    if cfg.selector_mode == "fourier":
        return ["SelectorCarrier", "SelectorFourierRidge_*"]
    if cfg.selector_mode == "centrifugal":
        return ["SelectorCarrier", "SelectorCentrifugal*"]
    return ["SelectorCarrier", "SelectorCamPin_*"]
