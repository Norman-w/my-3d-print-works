#!/usr/bin/env python3
"""Build a parametric SmartPartsDrawer mechanism in FreeCAD and export STL/STEP groups."""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fc_assembly import build_mechanism, preview_mechanism_map
from fc_config import parse_args
from fc_export import export_step_parts, export_stl_groups, write_animation_json, write_manifest

# ===== 分区：常量/配置 =====
# 默认 selector-mode=snake，见 fc_config.Config。

# ===== 分区：模型/类型 =====
# CLI 入口只负责解析、建模、落盘。

# ===== 分区：私有成员 =====
def _require_freecad():
    try:
        import FreeCAD as App  # type: ignore
        import Mesh  # type: ignore
        import Part  # type: ignore
    except Exception as exc:  # pragma: no cover (environment dependent)
        raise RuntimeError(
            "FreeCAD Python 环境未检测到。请使用 freecadcmd 运行：\n"
            "freecadcmd -P scripts scripts/freecad_drawer_pipeline.py --pass \"--help\""
        ) from exc
    return App, Part, Mesh

# ===== 分区：公开 API =====
def main(argv=None) -> None:
    cfg, args = parse_args(argv)
    if args.dry_run:
        print("参数检查通过（dry-run）")
        mechanism_map = preview_mechanism_map(cfg)
        print("参数与机构映射（预览）:")
        print(json.dumps({"config": cfg.__dict__, "mechanismMap": mechanism_map}, ensure_ascii=False, indent=2))
        return
    App, Part, Mesh = _require_freecad()
    doc, width_total, depth_total, mechanism_map, animation = build_mechanism(App, Part, cfg)
    cfg.width_total = width_total
    cfg.depth_total = depth_total
    fcstd_path = Path(cfg.fcstd).resolve()
    fcstd_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveAs(str(fcstd_path))
    print(f"FCStd 已保存: {fcstd_path}")
    anim_path = write_animation_json(fcstd_path, animation)
    if anim_path:
        print(f"动画清单: {anim_path}")
    if not cfg.export:
        return
    out_dir = Path(cfg.out).resolve()
    manifest = export_stl_groups(doc, Mesh, out_dir, cfg)
    write_manifest(out_dir, cfg, manifest, mechanism_map)
    print(f"STL 已导出: {out_dir}")
    print(f"manifest 已写入: {out_dir / 'manifest.json'}")
    if cfg.export_step:
        step_paths = export_step_parts(doc, Path(cfg.step_dir).resolve())
        print(f"STEP 分件已导出: {len(step_paths)} -> {Path(cfg.step_dir).resolve()}")

# ===== 分区：业务逻辑 =====
# 建模逻辑在 fc_assembly / fc_snake_parts，本文件不重复。

# ===== 分区：方法/工具 =====
def _should_run() -> bool:
    if __name__ == "__main__":
        return True
    exe = Path(sys.argv[0]).name.lower() if sys.argv else ""
    return "freecad" in exe

if _should_run():
    main()
