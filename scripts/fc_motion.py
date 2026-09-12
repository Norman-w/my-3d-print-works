#!/usr/bin/env python3
"""选择机构运动轮廓：snake 用真实弧长，其余保持原采样。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import math

from fc_snake_path import build_snake_path, motion_profile_from_path

# ===== 分区：常量/配置 =====
# selector_steps 控制 mechanismMap.motionProfile 采样密度。

# ===== 分区：模型/类型 =====
# 返回 JSON 友好的 dict，供 manifest 与 dry-run 使用。

# ===== 分区：私有成员 =====
def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

# ===== 分区：公开 API =====
def build_selector_motion_profile(cfg, x0: float, y0: float) -> dict:
    if cfg.selector_mode == "snake":
        return motion_profile_from_path(build_snake_path(cfg), cfg.selector_steps)
    steps = max(8, int(cfg.selector_steps))
    samples = []
    if cfg.selector_mode == "fourier":
        for i in range(steps + 1):
            t = (i / max(1, steps)) * (2.0 * math.pi)
            x = x0 + 12 + (cfg.selector_length - 20) * (i / max(1, steps))
            y = y0 + 0.5 * cfg.selector_length + (math.cos(3 * t) + 0.35 * math.cos(5 * t + 0.4) + 0.18 * math.sin(7 * t)) * cfg.selector_length * 0.1
            samples.append({"t": t, "x": round(x, 3), "y": round(y, 3), "z": round(cfg.base_height + cfg.selector_height * 0.42, 3)})
        return _pack(cfg, "fourier-trace", samples, False, steps)
    if cfg.selector_mode == "centrifugal":
        cx = x0 + cfg.selector_length * 0.5
        cy = y0 + cfg.selector_length * 0.55
        for i in range(steps + 1):
            t = (i / max(1, steps)) * (2.0 * math.pi)
            radius = cfg.selector_length * 0.34 + (math.sin(t * 2) * 1.8)
            samples.append({
                "t": round(t, 6),
                "x": round(cx + radius * math.cos(t), 3),
                "y": round(cy + radius * math.sin(t) * 0.82, 3),
                "z": round(cfg.base_height + cfg.selector_height * 0.45, 3),
            })
        return _pack(cfg, "radial-ring", samples, True, steps)
    rail_len = cfg.selector_length - 20
    y = y0 + cfg.selector_length * 0.55
    for i in range(steps + 1):
        t = i / max(1, steps)
        x = x0 + 10 + (rail_len / max(1, cfg.cam_pins)) * (t * cfg.cam_pins % cfg.cam_pins)
        z = cfg.base_height + cfg.selector_height * 0.34
        z = _clamp(z + (0.15 if (int(t * cfg.cam_pins) % 2 == 0) else -0.05), cfg.base_height * 0.1, cfg.base_height + cfg.selector_height * 0.34 + 1.0)
        samples.append({"t": round(t, 6), "x": round(x, 3), "y": round(y, 3), "z": round(z, 3)})
    return _pack(cfg, "cam-pins", samples, False, steps)

# ===== 分区：业务逻辑 =====
def _pack(cfg, kind: str, samples: list[dict], closed: bool, steps: int) -> dict:
    return {
        "mode": cfg.selector_mode,
        "kind": kind,
        "samples": samples,
        "steps": steps,
        "closed": closed,
        "bounds": {
            "xMin": min((p["x"] for p in samples), default=0.0),
            "xMax": max((p["x"] for p in samples), default=0.0),
            "yMin": min((p["y"] for p in samples), default=0.0),
            "yMax": max((p["y"] for p in samples), default=0.0),
            "zMin": min((p["z"] for p in samples), default=0.0),
            "zMax": max((p["z"] for p in samples), default=0.0),
        },
    }

# ===== 分区：方法/工具 =====
def selector_origin(cfg) -> tuple[float, float]:
    return cfg.width_total * 0.50 - cfg.selector_length * 0.48, cfg.depth_total * 0.12
