#!/usr/bin/env python3
"""从已导出的 M4 拍柄前后半壳合成真实尾段，再挖 M5 电池仓，并处理螺丝干涉。

本脚本不依赖 pcb-tail 布局（无尾板 Edge.Cuts / 器件开孔）。
尾板干涉见独立 Step 6：scripts/step6_tail_board_interfere_handle.py
"""
# ===== 分区：导入/依赖 =====
from __future__ import annotations

import sys
from pathlib import Path

# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[1]
STL_DIR = ROOT / "enclosure" / "stl"
OUT_DIR = ROOT / "enclosure" / "m5" / "build"
FRONT = STL_DIR / "paddle_handle_front.stl"
BACK = STL_DIR / "paddle_handle_back.stl"

BUTT_Y = -178.0962
TAIL_LEN = 70.0

# 电池匣 / 仓（X+ 抽屉；不再用旧充电板窄槽定位）
CART_CX = 5.6
CART_X = 16.0
CART_Z = 16.0
CART_Y = 57.0
BAY_CLEAR = 0.5
BAY_DEPTH = CART_Y + 4.0 + 0.8  # 匣长 + 顶出 + 止挡

# M4 拍柄螺丝：与电池 Y 行程冲突，必须迁移（不得留在仓内）
# M4: (±7,-160) 合壳螺丝；(±10,-120) 定位销
M4_CONFLICT_SCREWS = [(7.0, -160.0), (-7.0, -160.0)]
M4_CONFLICT_PINS = [(10.0, -120.0), (-10.0, -120.0)]
# M5 新位：电池内端之后（匣末端约 -121），贴左右壁，避开匣/板包络
M5_SCREWS = [(11.0, -108.0), (-11.0, -108.0)]
BOSS_D = 5.5
BOSS_H = 8.0
HOLE_D = 2.2

# ===== 分区：私有成员 =====
def _load_stl(path: Path):
    import trimesh

    mesh = trimesh.load_mesh(path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def _box(center, extents):
    import trimesh

    return trimesh.creation.box(
        extents=extents,
        transform=trimesh.transformations.translation_matrix(center),
    )


def _cyl_y(radius: float, height: float, center, sections: int = 28):
    """圆柱轴向 = +Y（插入方向），不是默认 Z。"""
    import trimesh
    import numpy as np

    c = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    # trimesh 圆柱默认沿 Z → 转到 Y
    c.apply_transform(
        trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    )
    c.apply_translation(center)
    return c


def _cyl_z(radius: float, height: float, center, sections: int = 24):
    import trimesh

    c = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    c.apply_translation(center)
    return c


def _export(mesh, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(path)
    print(
        f"→ {path.name}  verts={len(mesh.vertices)}  faces={len(mesh.faces)}  "
        f"{path.stat().st_size / 1024:.0f}KB"
    )


def _crop_tail(mesh):
    y0 = BUTT_Y - 1.0
    y1 = BUTT_Y + TAIL_LEN
    cutter = _box([0.0, (y0 + y1) / 2, 0.0], [120.0, y1 - y0, 80.0])
    return mesh.intersection(cutter)


def _dig_m5(mesh):
    """电池仓 + 滑扣 + 清冲突螺丝。不含尾板开孔（留给 Step 6）。"""
    bay = _box(
        [CART_CX, BUTT_Y + BAY_DEPTH / 2 - 0.5, 0.0],
        [CART_X + 2 * BAY_CLEAR, BAY_DEPTH + 2.0, CART_Z + 2 * BAY_CLEAR],
    )
    latch_tunnel = _box(
        [CART_CX - CART_X / 2 - 1.0, BUTT_Y + 2.8, 0.0],
        [3.0, 9.0, 6.0],
    )
    latch_recess = _box(
        [CART_CX - 2.0, BUTT_Y - 0.2, 0.0],
        [10.0, 3.0, 6.2],
    )
    conflict_clear = []
    for x, y in M4_CONFLICT_SCREWS + M4_CONFLICT_PINS:
        conflict_clear.append(_cyl_z(BOSS_D / 2 + 0.8, 28.0, [x, y, 0.0]))

    out = mesh
    for i, cutter in enumerate((bay, latch_tunnel, latch_recess, *conflict_clear)):
        try:
            out = out.difference(cutter, check_volume=False)
        except TypeError:
            out = out.difference(cutter)
        if out is None or getattr(out, "is_empty", False):
            raise RuntimeError(f"布尔挖空后网格为空 (cutter#{i})")
    return out


def _add_m5_screw_bosses(mesh):
    """在电池行程之外补新合壳螺丝柱（示意可打印实体）。"""
    import trimesh

    parts = [mesh]
    for x, y in M5_SCREWS:
        boss = _cyl_z(BOSS_D / 2, BOSS_H, [x, y, 0.0])
        hole = _cyl_z(HOLE_D / 2, BOSS_H + 2.0, [x, y, 0.0])
        boss = boss.difference(hole)
        parts.append(boss)
    return trimesh.util.concatenate(parts)


def _make_cartridge():
    """匣体 + 内嵌电芯（沿 Y，不戳出匣外）。"""
    import trimesh

    body = _box(
        [CART_CX, BUTT_Y + CART_Y / 2, 0.0],
        [CART_X, CART_Y, CART_Z],
    )
    # 内腔（示意壁厚）
    cavity = _box(
        [CART_CX, BUTT_Y + CART_Y / 2 + 0.5, 0.0],
        [CART_X - 2.4, CART_Y - 3.0, CART_Z - 2.4],
    )
    shell = body.difference(cavity)
    # 电芯：Ø14.1×50，完全落在匣内
    cell = _cyl_y(7.05, 50.0, [CART_CX, BUTT_Y + 2.8 + 25.0, 0.0])
    # 锁舌凹槽：匣体 −X 侧（朝分隔墙/尾板），供尾面滑扣咬合
    pocket = _box(
        [CART_CX - CART_X / 2 + 0.5, BUTT_Y + CART_Y * 0.42, 0.0],
        [1.4, 5.5, 3.4],
    )
    shell = shell.difference(pocket)
    return trimesh.util.concatenate([shell, cell])


def _make_latch(open_mm: float = 0.0):
    """拍尾端面滑扣：沿 X 拨动；锁舌向 +Y 伸入。"""
    import trimesh

    pad = _box(
        [CART_CX - 2.0 + open_mm, BUTT_Y - 0.9, 0.0],
        [9.0, 2.0, 5.0],
    )
    tongue = _box(
        [CART_CX - CART_X / 2 - 0.2 + open_mm, BUTT_Y + 4.2, 0.0],
        [1.5, 6.5, 3.0],
    )
    return trimesh.util.concatenate([pad, tongue])


def _make_screw_markers():
    """冲突旧钉（红）与迁移新钉（绿）示意，单独一层方便预览开关。"""
    import trimesh

    old = []
    for x, y in M4_CONFLICT_SCREWS:
        old.append(_cyl_z(1.6, 22.0, [x, y, 0.0]))
    new = []
    for x, y in M5_SCREWS:
        new.append(_cyl_z(1.6, 18.0, [x, y, 0.0]))
    return trimesh.util.concatenate(old), trimesh.util.concatenate(new)


# ===== 分区：公开 API =====
def main() -> int:
    if not FRONT.exists() or not BACK.exists():
        print(f"缺少真实拍柄 STL：\n  {FRONT}\n  {BACK}", file=sys.stderr)
        return 1

    print("→ 加载真实拍柄前后半壳…")
    united = __import__("trimesh").util.concatenate([_load_stl(FRONT), _load_stl(BACK)])
    print(f"  合壳 verts={len(united.vertices)}")

    print("→ 裁切尾段 70mm…")
    try:
        tail = _crop_tail(united)
    except Exception as exc:
        print(f"  精确裁切失败 ({exc})，顶点过滤兜底")
        import numpy as np

        mask = (united.vertices[:, 1] >= BUTT_Y - 1.0) & (
            united.vertices[:, 1] <= BUTT_Y + TAIL_LEN
        )
        face_mask = mask[united.faces].any(axis=1)
        tail = united.submesh([face_mask], append=True)

    print("→ 挖仓 + 清除冲突螺丝柱 (±7,-160) / 销 (±10,-120)…")
    dug = _dig_m5(tail)
    print("→ 在 Y=-108 补 M5 合壳螺丝柱 (±11)…")
    dug = _add_m5_screw_bosses(dug)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # pre_board：供 Step 6 尾板干涉；同时作为无尾板时的预览网格
    _export(dug, OUT_DIR / "m5_handle_tail_pre_board.stl")
    _export(dug, OUT_DIR / "m5_handle_tail.stl")
    _export(_make_cartridge(), OUT_DIR / "m5_battery_cartridge.stl")
    _export(_make_latch(0.0), OUT_DIR / "m5_latch.stl")
    old_m, new_m = _make_screw_markers()
    _export(old_m, OUT_DIR / "m5_screws_conflict_old.stl")
    _export(new_m, OUT_DIR / "m5_screws_migrated_new.stl")

    print("螺丝干涉结论：")
    print("  M4 (±7,-160) 落在电池行程内 → 删除/迁移")
    print("  M5 新位 (±11,-108) 在匣内端之后、贴左右壁")
    print("尾板开孔：布局就绪后跑  python3 scripts/step6_tail_board_interfere_handle.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
