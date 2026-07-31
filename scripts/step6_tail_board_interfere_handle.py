#!/usr/bin/env python3
"""Step 6 — 用 pcb-tail 尾板干涉真实拍柄尾段（独立于 step1–5）。

前置（可不依赖尾板布局完成）：
  ./scripts/export-m5-preview.sh
  → 写出 enclosure/m5/build/m5_handle_tail_pre_board.stl

本步（需要尾板 Edge.Cuts + J1/SW1/D1/LED1 已就位）：
  1) 从 KiCad 导出干涉事实 JSON / SCAD
  2) 从 pre_board 网格减去板槽 + Type-C/按钮/LED 开孔
  3) 写出 m5_handle_tail.stl + m5_tail_interference.stl

  python3 scripts/step6_tail_board_interfere_handle.py
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "enclosure" / "m5" / "build"
PRE_BOARD = OUT_DIR / "m5_handle_tail_pre_board.stl"
OUT_HANDLE = OUT_DIR / "m5_handle_tail.stl"
OUT_CUTTERS = OUT_DIR / "m5_tail_interference.stl"
INTERFERENCE = OUT_DIR / "tail_interference.json"
EXPORT_SCRIPT = ROOT / "pcb-tail" / "scripts" / "export_tail_interference.py"
KICAD_PY = Path(
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/"
    "Python.framework/Versions/Current/bin/python3"
)


# ===== 分区：私有成员 =====
def _load_stl(path: Path):
    import trimesh

    mesh = trimesh.load_mesh(path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def _export(mesh, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(path)
    print(
        f"→ {path.name}  verts={len(mesh.vertices)}  faces={len(mesh.faces)}  "
        f"{path.stat().st_size / 1024:.0f}KB"
    )


def _box(center, extents):
    import trimesh

    return trimesh.creation.box(
        extents=extents,
        transform=trimesh.transformations.translation_matrix(center),
    )


def _cyl_y(radius: float, height: float, center, sections: int = 28):
    import numpy as np
    import trimesh

    c = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation(center)
    return c


def _map_extrude_xy_to_handle_y(mesh, y0: float):
    import numpy as np
    import trimesh

    t = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, y0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    mesh.apply_transform(t)
    mesh.invert()
    mesh.remove_unreferenced_vertices()
    if not mesh.is_watertight:
        raise RuntimeError("cutter not watertight after transform")
    if not mesh.is_volume:
        mesh = trimesh.Trimesh(
            vertices=mesh.vertices.copy(), faces=mesh.faces.copy(), process=True
        )
        if mesh.volume < 0:
            mesh.invert()
    if not mesh.is_volume:
        raise RuntimeError(f"cutter still not a volume (V={mesh.volume})")
    return mesh


def _extrude_xz_along_y(points_xz, y0: float, y1: float):
    import trimesh
    from shapely.geometry import Polygon

    if y1 <= y0:
        raise ValueError("y1 must be > y0")
    poly = Polygon([(float(p[0]), float(p[1])) for p in points_xz])
    if not poly.is_valid or poly.area < 1.0:
        raise RuntimeError("invalid Edge.Cuts polygon")
    mesh = trimesh.creation.extrude_polygon(poly, height=y1 - y0)
    return _map_extrude_xy_to_handle_y(mesh, y0)


def _stadium_y(cx: float, cz: float, w: float, d: float, y0: float, y1: float):
    import trimesh
    from shapely.geometry import Point, box

    r = min(d / 2, w / 2)
    core = Point(0, 0).buffer(r)
    if w > 2 * r:
        core = core.union(box(-(w / 2 - r), -r, (w / 2 - r), r)).convex_hull
    mesh = trimesh.creation.extrude_polygon(core, height=y1 - y0)
    mesh.apply_translation([cx, cz, 0.0])
    return _map_extrude_xy_to_handle_y(mesh, y0)


def _tail_board_cutters(info: dict):
    pcb_y = float(info["pcb_y"])
    butt_y = float(info["butt_y"])
    t = float(info["board_thickness"])
    axial = float(info["board_axial_clear"])
    y0 = pcb_y - axial
    y1 = pcb_y + t + axial
    board = _extrude_xz_along_y(info["edge_cuts_xy"], y0, y1)

    usb = info["usb"]
    clear = float(usb["clear"])
    usb_cut = _stadium_y(
        float(usb["x"]),
        float(usb["y"]),
        float(usb["shell_w"]) + 2 * clear,
        float(usb["shell_d"]) + 2 * clear,
        butt_y - 3.0,
        pcb_y + 0.8,
    )

    btn = info["button"]
    btn_cut = _cyl_y(
        float(btn["hole_d"]) / 2,
        (pcb_y + 1.0) - (butt_y - 3.0),
        [float(btn["x"]), (butt_y - 3.0 + pcb_y + 1.0) / 2, float(btn["y"])],
    )
    btn_pocket = _box(
        [float(btn["x"]), pcb_y - float(btn["body_h"]) / 2, float(btn["y"])],
        [float(btn["pocket"]), float(btn["body_h"]) + 0.6, float(btn["pocket"])],
    )

    cuts = [board, usb_cut, btn_cut, btn_pocket]
    for key in ("led_rgb", "led_status"):
        led = info[key]
        cuts.append(
            _cyl_y(
                float(led["hole_d"]) / 2,
                (pcb_y + 0.5) - (butt_y - 2.5),
                [float(led["x"]), (butt_y - 2.5 + pcb_y + 0.5) / 2, float(led["y"])],
            )
        )
    return cuts


def _run_export_interference() -> dict:
    py = str(KICAD_PY if KICAD_PY.is_file() else Path(sys.executable))
    print(f"→ 从 KiCad 导出尾板干涉事实 ({py})…")
    r = subprocess.run([py, str(EXPORT_SCRIPT)], cwd=str(ROOT))
    if r.returncode != 0:
        raise RuntimeError("export_tail_interference.py failed")
    if not INTERFERENCE.is_file():
        raise FileNotFoundError(INTERFERENCE)
    return json.loads(INTERFERENCE.read_text(encoding="utf-8"))


def _difference_all(mesh, cutters):
    out = mesh
    for i, cutter in enumerate(cutters):
        try:
            out = out.difference(cutter, check_volume=False)
        except TypeError:
            out = out.difference(cutter)
        if out is None or getattr(out, "is_empty", False):
            raise RuntimeError(f"布尔挖空后网格为空 (cutter#{i})")
    return out


# ===== 分区：公开 API =====
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Step 6: pcb-tail 尾板干涉拍柄（独立于 step1–5）"
    )
    parser.add_argument(
        "--pre-board",
        type=Path,
        default=PRE_BOARD,
        help="未挖尾板的拍柄尾段 STL（由 export-m5-preview / build-m5 生成）",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="复用已有 tail_interference.json，不重新跑 KiCad 导出",
    )
    args = parser.parse_args()

    if not args.pre_board.is_file():
        print(
            f"缺少 {args.pre_board}\n"
            "请先跑不影响尾板布局的预览生成：\n"
            "  ./scripts/export-m5-preview.sh\n"
            "它会写出 m5_handle_tail_pre_board.stl",
            file=sys.stderr,
        )
        return 1

    info = (
        json.loads(INTERFERENCE.read_text(encoding="utf-8"))
        if args.skip_export and INTERFERENCE.is_file()
        else _run_export_interference()
    )

    print(
        f"  pcb_y={info['pcb_y']:.3f}  "
        f"usb=({info['usb']['x']:.2f},{info['usb']['y']:.2f})  "
        f"sw=({info['button']['x']:.2f},{info['button']['y']:.2f})"
    )

    print(f"→ 加载预挖尾板拍柄 {args.pre_board.name}…")
    base = _load_stl(args.pre_board)
    cutters = _tail_board_cutters(info)
    import trimesh

    _export(trimesh.util.concatenate(cutters), OUT_CUTTERS)

    print("→ 减去尾板 Edge.Cuts 卡槽 + Type-C/按钮/LED 开孔…")
    dug = _difference_all(base, cutters)
    _export(dug, OUT_HANDLE)
    print("Step 6 完成 ✓  （预览: ./scripts/preview-m5.sh）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
