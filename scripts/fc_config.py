#!/usr/bin/env python3
"""SmartPartsDrawer FreeCAD 流水线配置与 CLI。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

# ===== 分区：常量/配置 =====
SELECTOR_MODES = ("snake", "cam", "fourier", "centrifugal")
HTD_PITCH_MM = 3.0
HTD_DRIVE_TEETH = 20
HTD_BELT_WIDTH_MM = 9.0
HTD_BELT_THICKNESS_MM = 1.9
DEFAULT_SELECTOR_SPEED_MM_S = 120.0
DEFAULT_DRIVE_RPM = 24.0
DEFAULT_TARGET_INDEX = 7
NEMA17_FACE_MM = 42.0
ISO_M3 = {"size": "M3", "d": 3.0, "dk": 5.5, "k": 3.0}
ISO_M4 = {"size": "M4", "d": 4.0, "dk": 7.0, "k": 4.0}

# ===== 分区：模型/类型 =====
@dataclass
class Config:
    columns: int = 4
    layers: int = 3
    cell_width: float = 132.0
    cell_depth: float = 88.0
    cell_gap_x: float = 14.0
    cell_gap_y: float = 10.5
    drawer_height: float = 48.0
    slide_inset: float = 6.0
    slide_depth: float = 4.6
    margin_x: float = 16.0
    margin_y: float = 16.0
    base_height: float = 10.0
    shell_height: float = 74.0
    wall_thickness: float = 6.2
    motor_length: float = 28.0
    motor_shaft_radius: float = 3.0
    motor_shaft_height: float = 12.0
    motor_tooth_radius: float = 11.0
    gear_thickness: float = 6.0
    coupler_radius: float = 8.1
    rail_width: float = 4.2
    rail_depth: float = 8.5
    selector_mode: str = "snake"
    selector_steps: int = 72
    selector_length: float = 98.0
    selector_height: float = 14.0
    selector_ridge_depth: float = 3.2
    selector_link_length: float = 11.4
    selector_link_width: float = 5.5
    cam_pins: int = 12
    snake_links: int = 16
    fourier_ridges: int = 18
    selector_speed_mm_s: float = DEFAULT_SELECTOR_SPEED_MM_S
    drive_rpm: float = DEFAULT_DRIVE_RPM
    target_index: int = DEFAULT_TARGET_INDEX
    out: str = "web/assets/stl"
    fcstd: str = "build/SmartPartsDrawer.FCStd"
    step_dir: str = "build/step"
    export: bool = True
    export_step: bool = True
    depth_total: float = 0.0
    width_total: float = 0.0
    rail_start_x: float = 0.0
    rail_inset_y: float = 8.4

# ===== 分区：私有成员 =====
def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("必须为正整数")
    return parsed

# ===== 分区：公开 API =====
def compute_geometry_totals(cfg: Config) -> tuple[float, float]:
    width_total = 2 * cfg.margin_x + cfg.columns * cfg.cell_width + max(0, cfg.columns - 1) * cfg.cell_gap_x
    depth_total = 2 * cfg.margin_y + cfg.layers * cfg.cell_depth + max(0, cfg.layers - 1) * cfg.cell_gap_y
    return width_total, depth_total

def build_parser() -> argparse.ArgumentParser:
    defaults = Config()
    parser = argparse.ArgumentParser(
        description="FreeCAD workflow for SmartPartsDrawer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--columns", type=_positive_int, default=defaults.columns)
    parser.add_argument("--layers", type=_positive_int, default=defaults.layers)
    parser.add_argument("--selector-mode", choices=SELECTOR_MODES, default=defaults.selector_mode, help="主仿真选择机构")
    parser.add_argument("--selector-steps", type=int, default=defaults.selector_steps, help="轨迹采样点数")
    parser.add_argument("--selector-speed", type=float, default=defaults.selector_speed_mm_s, help="蛇形弧长速度 mm/s")
    parser.add_argument("--drive-rpm", type=float, default=defaults.drive_rpm, help="方案1接合后的目标抽屉动力轴转速 rpm")
    parser.add_argument("--target-index", type=int, default=defaults.target_index, help="默认目标格位")
    parser.add_argument("--cell-width", type=float, default=defaults.cell_width)
    parser.add_argument("--cell-depth", type=float, default=defaults.cell_depth)
    parser.add_argument("--cell-height", type=float, default=defaults.drawer_height)
    parser.add_argument("--out", type=str, default=defaults.out)
    parser.add_argument("--fcstd", type=str, default=defaults.fcstd)
    parser.add_argument("--step-dir", type=str, default=defaults.step_dir)
    parser.add_argument("--no-export", action="store_true", help="只生成 FCStd，不导出 STL/STEP")
    parser.add_argument("--no-step", action="store_true", help="导出 STL 但不导出分件 STEP")
    parser.add_argument("--dry-run", action="store_true", help="只检查参数并退出")
    return parser

def cli_argv(argv=None) -> list[str]:
    raw = list(sys.argv if argv is None else argv)
    if "--pass" in raw:
        idx = raw.index("--pass")
        blob = raw[idx + 1] if idx + 1 < len(raw) else ""
        return blob.split()
    if "--" in raw:
        return raw[raw.index("--") + 1 :]
    cleaned: list[str] = []
    for token in raw[1:]:
        lower = token.lower()
        if token.endswith(".py") or "freecad" in lower or token in {"--python", "-c"}:
            continue
        cleaned.append(token)
    return cleaned

def parse_args(argv=None) -> tuple[Config, argparse.Namespace]:
    parser = build_parser()
    args = parser.parse_args(cli_argv(argv) if argv is None else argv)
    cfg = Config(
        columns=max(1, args.columns),
        layers=max(1, args.layers),
        selector_mode=args.selector_mode,
        selector_steps=max(8, args.selector_steps),
        selector_speed_mm_s=max(1.0, args.selector_speed),
        drive_rpm=max(0.0, args.drive_rpm),
        target_index=max(0, args.target_index),
        cell_width=max(50.0, args.cell_width),
        cell_depth=max(50.0, args.cell_depth),
        drawer_height=max(20.0, args.cell_height),
        out=args.out,
        fcstd=args.fcstd,
        step_dir=args.step_dir,
        export=(not args.no_export),
        export_step=(not args.no_export and not args.no_step),
    )
    cfg.width_total, cfg.depth_total = compute_geometry_totals(cfg)
    cell_count = cfg.columns * cfg.layers
    cfg.target_index = min(cfg.target_index, max(0, cell_count - 1))
    return cfg, args

# ===== 分区：业务逻辑 =====
def pulley_rpm(speed_mm_s: float, teeth: int = HTD_DRIVE_TEETH, pitch_mm: float = HTD_PITCH_MM) -> float:
    return 60.0 * speed_mm_s / (teeth * pitch_mm)

# ===== 分区：方法/工具 =====
def drive_pitch_radius_mm(teeth: int = HTD_DRIVE_TEETH, pitch_mm: float = HTD_PITCH_MM) -> float:
    return teeth * pitch_mm / (2.0 * 3.141592653589793)
