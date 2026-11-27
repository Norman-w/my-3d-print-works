#!/usr/bin/env python3
"""Step 6 — 用 pcb-tail 干涉已导出的 M7 四层与合体件。

输入（须已由 export-stl.sh / OpenSCAD 生成）：
  enclosure/stl/paddle_m7_layer{1..4}_*.stl
  enclosure/stl/paddle_m7_monolithic_{front,back}.stl
  enclosure/stl/paddle_m7_fasteners.stl

输出会覆盖上述打印件，并重建 M7 装配、爆炸图和尾段试片。
另输出独立安装的 B3U 导向活动推杆：
  enclosure/stl/paddle_m7_tail_button_plunger.stl

诊断（不覆盖打印件）：
  enclosure/stl/interference/board_slot.stl
  enclosure/stl/interference/ui_cuts.stl
  enclosure/stl/interference/component_keepouts.stl

  python3 scripts/step6_tail_board_interfere_handle.py
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path


# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "enclosure" / "stl"
INTER_DIR = STL / "interference"
INTERFERENCE_JSON = INTER_DIR / "tail_interference.json"
EXPORT_SCRIPT = ROOT / "pcb-tail" / "scripts" / "export_tail_interference.py"
PCB = ROOT / "pcb-tail" / "layouts" / "default" / "default.kicad_pcb"
KICAD_PY = Path(
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/"
    "Python.framework/Versions/Current/bin/python3"
)
VENV_PY = (
    ROOT / "scripts" / ".venv-stl" / "bin" / "python"
    if (ROOT / "scripts" / ".venv-stl" / "bin" / "python").is_file()
    else Path(sys.executable)
)

BUTT_Y = -178.0962
TIP_LENGTH = 25.0


# ===== 分区：私有成员 =====
def _py() -> str:
    return str(VENV_PY) if VENV_PY.is_file() else sys.executable


def _ensure_trimesh():
    try:
        import trimesh  # noqa: F401
        import shapely  # noqa: F401
    except ImportError:
        if VENV_PY.is_file() and Path(sys.executable) != VENV_PY:
            raise SystemExit(
                subprocess.call([str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])
            )
        venv = ROOT / "scripts" / ".venv-stl"
        subprocess.check_call(["uv", "venv", str(venv)])
        subprocess.check_call(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(venv / "bin" / "python"),
                "trimesh",
                "manifold3d",
                "numpy",
                "shapely",
                "networkx",
                "mapbox-earcut",
            ]
        )
        raise SystemExit(
            subprocess.call([str(venv / "bin" / "python"), str(Path(__file__).resolve()), *sys.argv[1:]])
        )


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


def _box_xz_rotated(center, extents, rot_deg: float):
    """Create a box and rotate its XZ footprint around the handle Y axis."""
    import trimesh

    mesh = _box(center, extents)
    if abs(rot_deg) > 1e-9:
        mesh.apply_transform(
            trimesh.transformations.rotation_matrix(
                math.radians(rot_deg), [0, 1, 0], point=center
            )
        )
    return mesh


def _cyl_y(radius: float, height: float, center, sections: int = 48):
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
    if not mesh.is_volume:
        mesh = trimesh.Trimesh(
            vertices=mesh.vertices.copy(), faces=mesh.faces.copy(), process=True
        )
        if mesh.volume < 0:
            mesh.invert()
    if not mesh.is_volume:
        raise RuntimeError(f"cutter not a volume (V={getattr(mesh, 'volume', '?')})")
    return mesh


def _extrude_xz_along_y(points_xz, y0: float, y1: float):
    import trimesh
    from shapely.geometry import Polygon

    poly = Polygon([(float(p[0]), float(p[1])) for p in points_xz])
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.area < 1.0:
        raise RuntimeError("invalid Edge.Cuts polygon")
    mesh = trimesh.creation.extrude_polygon(poly, height=y1 - y0)
    return _map_extrude_xy_to_handle_y(mesh, y0)


def _stadium_y(
    cx: float,
    cz: float,
    w: float,
    d: float,
    y0: float,
    y1: float,
    rot_deg: float = 0.0,
    n: int = 48,
):
    """Type-C 等跑道孔：局部 X=w 长轴，再按 footprint rot 转到 handle XZ。"""
    import trimesh
    from shapely.geometry import Polygon
    from shapely import affinity

    r = min(d / 2.0, w / 2.0)
    straight = max(0.0, w - 2 * r)
    pts = []
    for i in range(n // 2 + 1):
        a = -math.pi / 2 + math.pi * i / (n // 2)
        pts.append((straight / 2 + r * math.cos(a), r * math.sin(a)))
    for i in range(n // 2 + 1):
        a = math.pi / 2 + math.pi * i / (n // 2)
        pts.append((-straight / 2 + r * math.cos(a), r * math.sin(a)))
    poly = Polygon(pts)
    if not poly.is_valid:
        poly = poly.buffer(0)
    # KiCad rot：绕板法向；映射到 handle XZ 后同为绕 Y
    if abs(rot_deg) > 1e-6:
        poly = affinity.rotate(poly, rot_deg, origin=(0.0, 0.0), use_radians=False)
    mesh = trimesh.creation.extrude_polygon(poly, height=y1 - y0)
    mesh.apply_translation([cx, cz, 0.0])
    return _map_extrude_xy_to_handle_y(mesh, y0)


def _run_kicad_export() -> dict:
    if not PCB.is_file():
        raise FileNotFoundError(f"missing {PCB}")
    kpy = str(KICAD_PY if KICAD_PY.is_file() else sys.executable)
    r = subprocess.run([kpy, str(EXPORT_SCRIPT)], cwd=str(ROOT))
    if r.returncode != 0:
        raise RuntimeError("export_tail_interference.py failed")
    INTER_DIR.mkdir(parents=True, exist_ok=True)
    if not INTERFERENCE_JSON.is_file():
        raise FileNotFoundError(f"missing {INTERFERENCE_JSON}")
    return json.loads(INTERFERENCE_JSON.read_text(encoding="utf-8"))


def _board_and_ui_cutters(info: dict):
    pcb_y = float(info["pcb_y"])
    butt_y = float(info["butt_y"])
    t = float(info["board_thickness"])
    axial = float(info["board_axial_clear"])
    board = _extrude_xz_along_y(
        info["edge_cuts_xy"], pcb_y - axial, pcb_y + t + axial
    )

    usb = info["usb"]
    clear = float(usb["clear"])
    # 只挖拍尾端壁：从壳外到板面；跑道长轴跟 J1 rot（0°=口宽沿 handle X）
    usb_cut = _stadium_y(
        float(usb["x"]),
        float(usb["y"]),
        float(usb["shell_w"]) + 2 * clear,
        float(usb["shell_d"]) + 2 * clear,
        butt_y - 1.5,
        pcb_y + 0.35,
        rot_deg=float(usb.get("rot_deg", 0.0)),
    )

    btn = info["button"]
    y0, y1 = butt_y - 1.5, pcb_y + 0.35
    btn_hole = _cyl_y(
        float(btn["hole_d"]) / 2,
        y1 - y0,
        [float(btn["x"]), (y0 + y1) / 2, float(btn["y"])],
    )
    btn_pocket = _box_xz_rotated(
        [float(btn["x"]), pcb_y - float(btn["body_h"]) / 2, float(btn["y"])],
        [float(btn["pocket_w"]), float(btn["body_h"]) + 0.35, float(btn["pocket_d"])],
        float(btn.get("rot_deg", 0.0)),
    )

    flange_y0 = (
        butt_y
        + float(btn["wall_t"])
        - float(btn["plunger_flange_pocket_wall_overlap"])
    )
    flange_y1 = (
        butt_y
        + float(btn["wall_t"])
        + float(btn["plunger_flange_pocket_depth"])
    )
    flange_pocket = _cyl_y(
        float(btn["plunger_flange_pocket_d"]) / 2,
        flange_y1 - flange_y0,
        [float(btn["x"]), (flange_y0 + flange_y1) / 2, float(btn["y"])],
        sections=48,
    )

    ui_cuts = [usb_cut, btn_hole, flange_pocket, btn_pocket]
    for key in ("led_rgb", "led_status"):
        led = info[key]
        ly0, ly1 = butt_y - 1.2, pcb_y + 0.25
        ui_cuts.append(
            _cyl_y(
                float(led["hole_d"]) / 2,
                ly1 - ly0,
                [float(led["x"]), (ly0 + ly1) / 2, float(led["y"])],
            )
        )

    component_cuts = []
    for item in info.get("component_keepouts", []):
        x0, ky0, z0, x1, ky1, z1 = map(float, item["handle_box_xyz"])
        component_cuts.append(
            _box(
                [(x0 + x1) / 2, (ky0 + ky1) / 2, (z0 + z1) / 2],
                [x1 - x0, ky1 - ky0, z1 - z0],
            )
        )
    if len(component_cuts) != 12:
        raise RuntimeError(
            f"expected 12 KiCad-derived component keepouts, got {len(component_cuts)}"
        )
    mated_housing_cuts = []
    housing_refs = set()
    for item in info.get("harness_connectors", []):
        values = item.get("housing_keepout_handle_box_xyz", [])
        if len(values) != 6:
            raise RuntimeError(f"invalid inserted-housing keepout for {item.get('ref')}")
        x0, ky0, z0, x1, ky1, z1 = map(float, values)
        mated_housing_cuts.append(
            _box(
                [(x0 + x1) / 2, (ky0 + ky1) / 2, (z0 + z1) / 2],
                [x1 - x0, ky1 - ky0, z1 - z0],
            )
        )
        housing_refs.add(str(item.get("ref")))
    if housing_refs != {"J2", "J3"} or len(mated_housing_cuts) != 2:
        raise RuntimeError(
            "expected inserted 51021 housing keepouts for exactly J2/J3"
        )
    component_cuts.extend(mated_housing_cuts)
    return board, ui_cuts, component_cuts, [board, *ui_cuts, *component_cuts]


def _button_plunger(info: dict):
    """Build the separate, inside-loaded B3U guided plunger in its rest pose."""

    import trimesh

    btn = info["button"]
    butt_y = float(info["butt_y"])
    pcb_y = float(info["pcb_y"])
    outer_y = butt_y - float(btn["plunger_outer_projection"])
    tip_y = pcb_y - float(btn["operation_h"]) - float(btn["plunger_rest_gap"])
    if tip_y <= outer_y:
        raise RuntimeError("button plunger has non-positive shaft length")

    center_xz = [float(btn["x"]), float(btn["y"])]
    shaft = _cyl_y(
        float(btn["plunger_shaft_d"]) / 2,
        tip_y - outer_y,
        [center_xz[0], (outer_y + tip_y) / 2, center_xz[1]],
    )
    flange_y0 = butt_y + float(btn["wall_t"]) + 0.05
    flange_h = float(btn["plunger_flange_h"])
    flange = _cyl_y(
        float(btn["plunger_flange_d"]) / 2,
        flange_h,
        [center_xz[0], flange_y0 + flange_h / 2, center_xz[1]],
    )
    try:
        plunger = trimesh.boolean.union([shaft, flange], check_volume=False)
    except TypeError:
        plunger = trimesh.boolean.union([shaft, flange])
    if plunger is None or getattr(plunger, "is_empty", False):
        raise RuntimeError("button plunger union failed")
    return plunger


def _difference_all(mesh, cutters):
    out = mesh
    for i, cutter in enumerate(cutters):
        try:
            out = out.difference(cutter, check_volume=False)
        except TypeError:
            out = out.difference(cutter)
        if out is None or getattr(out, "is_empty", False):
            raise RuntimeError(f"boolean empty after cutter#{i}")
    return out


def _crop_tip(handle_back, butt_y: float, tip_len: float = TIP_LENGTH):
    y0 = butt_y - 1.0
    y1 = butt_y + tip_len
    box = _box([0.0, (y0 + y1) / 2, 0.0], [120.0, y1 - y0, 80.0])
    return handle_back.intersection(box)


# ===== 分区：公开 API =====
def pcb_ready() -> bool:
    return PCB.is_file()


def main() -> int:
    parser = argparse.ArgumentParser(description="Step6: pcb-tail 干涉已导出 M7 拍体")
    parser.add_argument("--skip-export", action="store_true")
    parser.add_argument("--check-only", action="store_true", help="仅检查 pcb-tail 是否可干涉")
    args = parser.parse_args()

    if args.check_only:
        print("pcb-tail ready" if pcb_ready() else "pcb-tail missing")
        return 0 if pcb_ready() else 2

    if not pcb_ready():
        print(f"跳过 Step6：无 {PCB}", file=sys.stderr)
        return 2

    _ensure_trimesh()
    import trimesh

    parts = {
        "skin_front": STL / "paddle_m7_layer1_handle_skin_front.stl",
        "core_front": STL / "paddle_m7_layer2_core_front.stl",
        "core_back": STL / "paddle_m7_layer3_core_back.stl",
        "skin_back": STL / "paddle_m7_layer4_handle_skin_back.stl",
        "monolithic_front": STL / "paddle_m7_monolithic_front.stl",
        "monolithic_back": STL / "paddle_m7_monolithic_back.stl",
    }
    fasteners_path = STL / "paddle_m7_fasteners.stl"
    for p in (*parts.values(), fasteners_path):
        if not p.is_file():
            print(f"缺少已导出 M7 零件: {p}\n请先跑 ./scripts/export-stl.sh", file=sys.stderr)
            return 1

    info = (
        json.loads(INTERFERENCE_JSON.read_text(encoding="utf-8"))
        if args.skip_export and INTERFERENCE_JSON.is_file()
        else _run_kicad_export()
    )

    print(
        f"→ Step6 干涉拍柄  Edge.Cuts={len(info['edge_cuts_xy'])}pts  "
        f"usb=({info['usb']['x']:.2f},{info['usb']['y']:.2f})  "
        f"sw=({info['button']['x']:.2f},{info['button']['y']:.2f})"
    )

    board, ui, component_cuts, all_cuts = _board_and_ui_cutters(info)
    plunger = _button_plunger(info)
    INTER_DIR.mkdir(parents=True, exist_ok=True)
    _export(board, INTER_DIR / "board_slot.stl")
    _export(trimesh.util.concatenate(ui), INTER_DIR / "ui_cuts.stl")
    _export(
        trimesh.util.concatenate(component_cuts),
        INTER_DIR / "component_keepouts.stl",
    )
    _export(trimesh.util.concatenate(all_cuts), INTER_DIR / "all_cuts.stl")
    _export(plunger, INTER_DIR / "button_plunger.stl")
    _export(plunger, STL / "paddle_m7_tail_button_plunger.stl")

    print("→ 干涉 M7 四层与正反合体件 …")
    cut_parts = {
        name: _difference_all(_load_stl(path), all_cuts)
        for name, path in parts.items()
    }
    for name, path in parts.items():
        _export(cut_parts[name], path)

    assembly_order = ("skin_front", "core_front", "core_back", "skin_back")
    fasteners = _load_stl(fasteners_path)
    assembly = trimesh.util.concatenate(
        [cut_parts[name] for name in assembly_order]
    )
    _export(assembly, STL / "paddle_m7_assembly.stl")

    exploded_parts = []
    for name, dz in zip(assembly_order, (12.0, 4.0, -4.0, -12.0)):
        mesh = cut_parts[name].copy()
        mesh.apply_translation([0.0, 0.0, dz])
        exploded_parts.append(mesh)
    _export(trimesh.util.concatenate(exploded_parts), STL / "paddle_m7_exploded.stl")

    butt_y = float(info.get("butt_y", BUTT_Y))
    try:
        tip_back = _crop_tip(cut_parts["monolithic_back"], butt_y)
        _export(tip_back, STL / "paddle_m7_handle_back_tip.stl")
        tip_full = _crop_tip(
            trimesh.util.concatenate(
                [cut_parts["monolithic_front"], cut_parts["monolithic_back"]]
            ),
            butt_y,
        )
        _export(tip_full, STL / "paddle_m7_handle_tail.stl")
    except Exception as exc:
        print(f"  tip 裁切跳过: {exc}")

    print("Step6 完成 ✓  M7 最终打印件与可选按钮推杆已写入 enclosure/stl/")
    print("  Ø2.0 mm 针孔可直接操作；推杆须从壳内装入，采用前先做尾段行程试片。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
