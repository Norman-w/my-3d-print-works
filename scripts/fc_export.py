#!/usr/bin/env python3
"""STL 分组导出、分件 STEP、manifest 与动画 JSON。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable

from fc_selectors import selector_patterns

# ===== 分区：常量/配置 =====
GROUP_COLORS = {"cabinet": "#6f7f8f", "drawers": "#9ab2c9", "drive": "#9ab2c9", "selector": "#9ab2c9"}

# ===== 分区：模型/类型 =====
# manifest.json 供网页 STL 预览；snake_animation.json 供 FreeCAD GUI 动画。

# ===== 分区：私有成员 =====
def _collect_names(doc, patterns: Iterable[str]) -> list[str]:
    result = []
    for ptn in patterns:
        if ptn.endswith("*"):
            prefix = ptn[:-1]
            result.extend([obj.Name for obj in doc.Objects if obj.Name.startswith(prefix)])
        else:
            target = doc.getObject(ptn)
            if target is not None and target.Name not in result:
                result.append(target.Name)
    seen = []
    for name in result:
        if name not in seen:
            seen.append(name)
    return seen

def _shaped(doc, names: list[str]):
    objects = []
    for name in names:
        obj = doc.getObject(name)
        if obj is not None and getattr(obj, "Shape", None) is not None:
            objects.append(obj)
    return objects

# ===== 分区：公开 API =====
def export_stl_groups(doc, Mesh, out_dir: Path, cfg) -> list[dict]:
    groups = {
        "cabinet": ["CabinetBase", "CabinetShell", "FrontWall", "BackWall"],
        "drawers": [
            "DrawerBody_*",
            "DrawerFrontPanel_*",
            "DrawerGuideLeft_*",
            "DrawerGuideRight_*",
            "DrawerCouplerBody_*",
            "DrawerCouplerGear_*",
            "DrawerSelectionPin_*",
        ],
        "drive": [
            "MotorA_*",
            "MotorMB_*",
            "BusShaft_*",
            "RowShaft_*",
            "RowCouplerGear_*",
            "RowRail_*",
            "RowRailBeltPad_*",
        ],
        "selector": selector_patterns(cfg),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for key, patterns in groups.items():
        names = _collect_names(doc, patterns)
        objects = _shaped(doc, names)
        if not objects:
            continue
        file_path = out_dir / f"{key}.stl"
        Mesh.export(objects, str(file_path))
        manifest.append({
            "name": key,
            "displayName": key,
            "file": f"{key}.stl",
            "color": GROUP_COLORS.get(key, "#9ab2c9"),
            "visible": key in {"cabinet", "drawers", "selector"},
        })
    all_objs = [obj for obj in doc.Objects if getattr(obj, "Shape", None) is not None]
    Mesh.export(all_objs, str(out_dir / "all.stl"))
    manifest.append({"name": "all", "displayName": "full_assembly", "file": "all.stl", "color": "#d6e6ff", "visible": False})
    return manifest

def export_step_parts(doc, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    try:
        import Import  # type: ignore
    except Exception:
        Import = None
    for obj in doc.Objects:
        shape = getattr(obj, "Shape", None)
        if shape is None or getattr(shape, "isNull", lambda: True)():
            continue
        path = out_dir / f"{obj.Name}.step"
        try:
            if Import is not None:
                Import.export([obj], str(path))
            else:
                shape.exportStep(str(path))
            written.append(str(path))
        except Exception as exc:
            print(f"STEP 导出跳过 {obj.Name}: {exc}")
    return written

def write_manifest(out_dir: Path, cfg, manifest, mechanism_map) -> None:
    payload = {
        "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "columns": cfg.columns,
            "layers": cfg.layers,
            "selectorMode": cfg.selector_mode,
            "drawerWidth": cfg.cell_width,
            "drawerDepth": cfg.cell_depth,
            "drawerHeight": cfg.drawer_height,
            "widthTotal": cfg.width_total,
            "depthTotal": cfg.depth_total,
            "selectorSpeedMmS": cfg.selector_speed_mm_s,
            "driveRpm": cfg.drive_rpm,
            "targetIndex": cfg.target_index,
        },
        "models": manifest,
        "mechanismMap": mechanism_map,
    }
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)

def write_animation_json(fcstd_path: Path, animation: dict | None) -> Path | None:
    if not animation:
        return None
    path = Path(fcstd_path).resolve().parent / "snake_animation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(animation, fp, ensure_ascii=False, indent=2)
    return path

# ===== 分区：业务逻辑 =====
def load_animation_json(fcstd_path: Path) -> dict:
    path = Path(fcstd_path).resolve().parent / "snake_animation.json"
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)

# ===== 分区：方法/工具 =====
def step_dir_for(cfg) -> Path:
    return Path(cfg.step_dir).resolve()
