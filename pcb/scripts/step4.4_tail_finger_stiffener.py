#!/usr/bin/env python3
"""Step 4.4 — 尾插 F 面机械加厚垫片（左右各一，无电气网络）。

几何原则：
  - 垫片只做 0.8→≈1.6mm 叠焊加厚，不赋任何网络（避免 unconnected / 电气误导）
  - 铜条加长，与 tip/handle 邮票孔铜环搭接（焊接可视化）
  - tip/handle Edge.Cuts 过孔心 + 外凸半圆（半孔电镀）
  - 与宽栈道侧墙（x=±8.70）共边成同一块板：切开侧墙 Y 段，外绕垫片半岛
  - 共边内侧打 NPTH 鼠咬孔，掰开用；不另开独立外形 / Different Design
  - 垫片区覆铜禁布，避免空网络焊盘与主板灌铜打架
  - 主板尖端保留 TAIL_TIP（F 面 SMD，带金手指网络，供叠焊对位）

可重复运行；须在 step2/step3 之后。若侧墙曾被挖坏：先 step2→step3 再跑本脚本。
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import (
    load_board,
    mk,
    save_board,
    shape_arc,
    shape_line,
    xy,
)

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
FP_LIB = ROOT / "pcb" / "layouts" / "lib" / "footprints.pretty"

FINGER_XS = (-2.54, -1.27, 0.0, 1.27, 2.54)
# 仅 TAIL_TIP（主板尖端）需要金手指网络；垫片本身无网络。
TIP_NETS = ("SYS_5V_IN", "SYS_5V_SW", "btn_sw", "USB_DP", "UART_TX")

MAIN_TIP_Y = 97.7
WALL_X = 8.70
SHOULDER_Y = 89.70

# 垫片比金手指短 1.2mm（仅缩短拍柄侧），H 半孔落在手指中段。
COUPON_W = 8.0
COUPON_H = 6.8
COUPON_Y_HI = SHOULDER_Y
COUPON_Y_LO = COUPON_Y_HI - COUPON_H
COUPON_CY = COUPON_Y_HI - COUPON_H / 2
COUPON_CLEAN_Y_LO = SHOULDER_Y - 10.0

CASTEL_DRILL = 0.70
CASTEL_PAD = 1.00
CASTEL_R = CASTEL_DRILL / 2
CASTEL_EDGE_Y = COUPON_H / 2
# 铜条与 tip/handle 环搭接：半高各伸入环内约 0.3mm
STIFF_SMD_H = COUPON_H - 0.40
EDGE_W = 0.10
TIP_SMD_W = 0.80
TIP_SMD_H = 1.20

# 鼠咬：嘉立创推荐 Ø0.60 NPTH，每组 5–8 孔，孔边间隙 0.35–0.4（板薄略加大）
# 孔心距 = 0.60 + 0.40 = 1.00mm（0.8mm 板用偏保守间隙）
MOUSE_DRILL = 0.60
MOUSE_PAD = 0.60
MOUSE_PITCH = 1.00  # 孔心距 → 孔边间隙 0.40mm
MOUSE_COUNT = 6  # 一组 6 孔，沿共边均匀排布
MOUSE_INSET = 0.55  # 墙与最近铜条之间，避免与手指条撞


# ===== 分区：私有成员 =====
def _ensure_net(board, pcbnew, name: str):
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def _near(a: float, b: float, tol: float = 0.12) -> bool:
    return abs(a - b) <= tol


def _coupon_xs(side: int) -> tuple[float, float, float]:
    """side=-1 左 / +1 右 → (wall_x, outer_x, cx)。垫片内边=侧墙共边。"""
    wall_x = side * WALL_X
    outer_x = wall_x + side * COUPON_W
    cx = (wall_x + outer_x) / 2
    return wall_x, outer_x, cx


def _iter_drawings(board):
    """稳健遍历板级图形（避免 Remove 后 GetDrawings 迭代器异常）。"""
    try:
        return list(board.GetDrawings())
    except (TypeError, AttributeError):
        raw = board.Drawings()
        out = []
        n = raw.size() if hasattr(raw, "size") else 0
        for i in range(n):
            item = raw[i]
            # DRAWINGS 可能返回基类，需要 Cast
            casted = None
            try:
                casted = pcbnew_cast_shape(item)
            except Exception:
                casted = item
            out.append(casted if casted is not None else item)
        return out


def pcbnew_cast_shape(item):
    import pcbnew

    if hasattr(pcbnew, "Cast_to_PCB_SHAPE"):
        return pcbnew.Cast_to_PCB_SHAPE(item)
    return item


def _edge_endpoints(pcbnew, drawing) -> tuple[float, float, float, float] | None:
    """线段/圆弧端点 (x0,y0,x1,y1)；其它形状返回 None。"""
    try:
        shape = drawing.GetShape()
    except AttributeError:
        drawing = pcbnew_cast_shape(drawing)
        shape = drawing.GetShape()
    if shape == pcbnew.SHAPE_T_SEGMENT:
        s, e = drawing.GetStart(), drawing.GetEnd()
        return (
            pcbnew.ToMM(s.x),
            pcbnew.ToMM(s.y),
            pcbnew.ToMM(e.x),
            pcbnew.ToMM(e.y),
        )
    if shape == pcbnew.SHAPE_T_ARC:
        s, e = drawing.GetStart(), drawing.GetEnd()
        return (
            pcbnew.ToMM(s.x),
            pcbnew.ToMM(s.y),
            pcbnew.ToMM(e.x),
            pcbnew.ToMM(e.y),
        )
    return None


def _remove_owned(board, pcbnew) -> tuple[int, int]:
    """删旧垫片半岛/独立小板外形与位号，并恢复侧墙连续竖边。"""
    n_fp = n_draw = 0
    to_remove = []

    for drawing in _iter_drawings(board):
        if drawing.GetLayer() != pcbnew.Edge_Cuts:
            continue
        bbox = drawing.GetBoundingBox()
        y0 = pcbnew.ToMM(bbox.GetY())
        y1 = y0 + pcbnew.ToMM(bbox.GetHeight())
        x0 = pcbnew.ToMM(bbox.GetX())
        x1 = x0 + pcbnew.ToMM(bbox.GetWidth())

        # 旧尖端外伸
        if y0 > MAIN_TIP_Y + 0.05:
            to_remove.append(drawing)
            continue

        # 垫片 Y 带：伸到侧墙外侧的边（半孔/外边/旧独立小板）；不删墙上竖线本身
        if y1 >= COUPON_CLEAN_Y_LO - 0.4 and y0 <= COUPON_Y_HI + 0.6:
            if max(abs(x0), abs(x1)) > WALL_X + 0.25:
                to_remove.append(drawing)
                continue

    seen: set[int] = set()
    for d in to_remove:
        i = id(d)
        if i in seen:
            continue
        seen.add(i)
        board.Remove(d)
        n_draw += 1

    for zone in list(board.Zones()):
        name = zone.GetZoneName() if hasattr(zone, "GetZoneName") else ""
        if name.startswith("STIFF_KO_"):
            board.Remove(zone)
            n_draw += 1

    for fp in list(board.GetFootprints()):
        ref = fp.GetReference()
        if (
            ref in ("TAIL_TIP", "TAIL_STIFF", "TAIL_MB")
            or ref.startswith("TAIL_STIFF")
            or ref.startswith("TAIL_MB")
            or ref.startswith("TAIL_TIP")
        ):
            board.Remove(fp)
            n_fp += 1

    return n_fp, n_draw


def _ensure_wall_span(pcbnew, board, wall_x: float, y_lo: float, y_hi: float) -> int:
    """若侧墙在 [y_lo,y_hi] 覆盖不全，补一条竖线（可与碎段重叠，build 会重切）。"""
    segs: list[tuple[float, float]] = []
    for drawing in _iter_drawings(board):
        if drawing.GetLayer() != pcbnew.Edge_Cuts:
            continue
        ends = _edge_endpoints(pcbnew, drawing)
        if ends is None:
            continue
        x0, y0, x1, y1 = ends
        if not (_near(x0, wall_x) and _near(x1, wall_x)):
            continue
        segs.append((min(y0, y1), max(y0, y1)))
    if any(lo <= y_lo + 0.05 and hi >= y_hi - 0.05 for lo, hi in segs):
        return 0
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (wall_x, y_lo), (wall_x, y_hi), EDGE_W)
    return 1


def _cut_both_walls(pcbnew, board) -> int:
    """一次收集左右侧墙开窗段并删除，再写回窗外 stubs（避免边删边扫）。"""
    y_lo, y_hi = COUPON_Y_LO, COUPON_Y_HI
    walls = (-WALL_X, WALL_X)
    to_remove = []
    stubs: dict[float, list[tuple[float, float]]] = {w: [] for w in walls}

    for drawing in _iter_drawings(board):
        if drawing.GetLayer() != pcbnew.Edge_Cuts:
            continue
        ends = _edge_endpoints(pcbnew, drawing)
        if ends is None:
            continue
        x0, y0, x1, y1 = ends
        # 只要竖线
        if abs(x0 - x1) > 0.05:
            continue
        wall_x = None
        for w in walls:
            if _near(x0, w) and _near(x1, w):
                wall_x = w
                break
        if wall_x is None:
            continue
        lo, hi = min(y0, y1), max(y0, y1)
        if hi <= y_lo + 1e-4 or lo >= y_hi - 1e-4:
            continue
        to_remove.append(drawing)
        if lo < y_lo - 1e-4:
            stubs[wall_x].append((lo, y_lo))
        if hi > y_hi + 1e-4:
            stubs[wall_x].append((y_hi, hi))

    seen: set[int] = set()
    for d in to_remove:
        i = id(d)
        if i in seen:
            continue
        seen.add(i)
        board.Remove(d)

    added = 0
    for wall_x, pairs in stubs.items():
        pairs.sort()
        merged: list[tuple[float, float]] = []
        for lo, hi in pairs:
            if not merged or lo > merged[-1][1] + 0.02:
                merged.append((lo, hi))
            else:
                merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        for lo, hi in merged:
            if hi - lo > 0.02:
                shape_line(pcbnew, board, pcbnew.Edge_Cuts, (wall_x, lo), (wall_x, hi), EDGE_W)
                added += 1
    return len(seen)


def _scalloped_horizontal(
    pcbnew,
    board,
    y: float,
    x_from: float,
    x_to: float,
    xs: tuple[float, ...],
    bulge_sign: float,
) -> None:
    lo, hi = (x_from, x_to) if x_to >= x_from else (x_to, x_from)
    going_right = x_to >= x_from
    segments: list[tuple[str, tuple]] = []
    cursor = lo
    for x in sorted(xs):
        left, right = x - CASTEL_R, x + CASTEL_R
        if right <= lo or left >= hi:
            continue
        left = max(left, lo)
        right = min(right, hi)
        if cursor < left - 1e-6:
            segments.append(("line", (cursor, left)))
        mid = (x, y + bulge_sign * CASTEL_R)
        segments.append(("arc", (left, mid, right)))
        cursor = right
    if cursor < hi - 1e-6:
        segments.append(("line", (cursor, hi)))

    ordered = segments if going_right else list(reversed(segments))
    for kind, data in ordered:
        if kind == "line":
            a, b = data
            if going_right:
                shape_line(pcbnew, board, pcbnew.Edge_Cuts, (a, y), (b, y), EDGE_W)
            else:
                shape_line(pcbnew, board, pcbnew.Edge_Cuts, (b, y), (a, y), EDGE_W)
        else:
            left, mid, right = data
            if going_right:
                shape_arc(pcbnew, board, pcbnew.Edge_Cuts, (left, y), mid, (right, y), EDGE_W)
            else:
                shape_arc(pcbnew, board, pcbnew.Edge_Cuts, (right, y), mid, (left, y), EDGE_W)


def _add_peninsula_outline(pcbnew, board, side: int) -> None:
    """侧墙已开窗后外绕：tip 半孔边 → 外边 → handle 半孔边。"""
    wall_x, outer_x, cx = _coupon_xs(side)
    y_lo, y_hi = COUPON_Y_LO, COUPON_Y_HI
    pad_xs = tuple(cx + f for f in FINGER_XS)

    _scalloped_horizontal(pcbnew, board, y_hi, wall_x, outer_x, pad_xs, bulge_sign=+1.0)
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (outer_x, y_hi), (outer_x, y_lo), EDGE_W)
    _scalloped_horizontal(pcbnew, board, y_lo, outer_x, wall_x, pad_xs, bulge_sign=-1.0)


def _add_keepout(pcbnew, board, side: int, tag: str) -> None:
    """垫片矩形禁布，避免空网络铜与主板灌铜 clearance。"""
    wall_x, outer_x, _cx = _coupon_xs(side)
    x0, x1 = sorted((wall_x, outer_x))
    margin = 0.15
    pts = [
        (x0 + margin, COUPON_Y_LO + margin),
        (x1 - margin, COUPON_Y_LO + margin),
        (x1 - margin, COUPON_Y_HI - margin),
        (x0 + margin, COUPON_Y_HI - margin),
    ]
    zone = pcbnew.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowCopperPour(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False)
    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_Cu)
    layers.AddLayer(pcbnew.B_Cu)
    zone.SetLayerSet(layers)
    if hasattr(zone, "SetZoneName"):
        zone.SetZoneName(f"STIFF_KO_{tag}")
    for x, y in pts:
        zone.AppendCorner(xy(pcbnew, x, y), -1)
    board.Add(zone)


def _add_pad_pth(pcbnew, fp, number: str, x: float, y: float, pad_d: float, drill: float):
    pad = pcbnew.PAD(fp)
    pad.SetNumber(number)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(mk(pad_d), mk(pad_d)))
    pad.SetDrillSize(pcbnew.VECTOR2I(mk(drill), mk(drill)))
    pad.SetLayerSet(pad.PTHMask())
    pad.SetFPRelativePosition(xy(pcbnew, x, y))
    fp.Add(pad)
    return pad


def _add_pad_npth(pcbnew, fp, x: float, y: float, pad_d: float, drill: float):
    pad = pcbnew.PAD(fp)
    pad.SetNumber("")
    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(mk(pad_d), mk(pad_d)))
    pad.SetDrillSize(pcbnew.VECTOR2I(mk(drill), mk(drill)))
    pad.SetLayerSet(pad.UnplatedHoleMask())
    pad.SetFPRelativePosition(xy(pcbnew, x, y))
    fp.Add(pad)
    return pad


def _add_pad_smd_f(pcbnew, fp, number: str, x: float, y: float, w: float, h: float):
    pad = pcbnew.PAD(fp)
    pad.SetNumber(number)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetShape(pcbnew.PAD_SHAPE_RECT)
    pad.SetSize(pcbnew.VECTOR2I(mk(w), mk(h)))
    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_Cu)
    layers.AddLayer(pcbnew.F_Mask)
    pad.SetLayerSet(layers)
    pad.SetFPRelativePosition(xy(pcbnew, x, y))
    fp.Add(pad)
    return pad


def _write_stiffener_fp(path: Path) -> None:
    ey = CASTEL_EDGE_Y
    smd_h = STIFF_SMD_H
    pad_d = CASTEL_PAD
    drill = CASTEL_DRILL
    smd = [
        f'  (pad "{i}" smd rect (at {x:.2f} 0) (size 0.8 {smd_h:.2f}) (layers "F.Cu" "F.Mask"))'
        for i, x in enumerate(FINGER_XS, start=1)
    ]
    tip = [
        f'  (pad "T{i}" thru_hole circle (at {x:.2f} {ey:.2f}) '
        f'(size {pad_d:.2f} {pad_d:.2f}) (drill {drill:.2f}) (layers "*.Cu" "*.Mask"))'
        for i, x in enumerate(FINGER_XS, start=1)
    ]
    handle = [
        f'  (pad "H{i}" thru_hole circle (at {x:.2f} {-ey:.2f}) '
        f'(size {pad_d:.2f} {pad_d:.2f}) (drill {drill:.2f}) (layers "*.Cu" "*.Mask"))'
        for i, x in enumerate(FINGER_XS, start=1)
    ]
    path.write_text(
        f"""(footprint "TailFingerStiffener_5ch_P1.27"
  (version 20240108)
  (generator "SmartPaddle")
  (layer "F.Cu")
  (descr "Mechanical F stiffener shim only — NO nets; strips meet tip/handle castellations")
  (tags "stiffener mechanical castellation SmartPaddle")
  (attr through_hole exclude_from_bom)
  (fp_text reference "REF**" (at 0 0) (layer "F.SilkS")
    (effects (font (size 0.5 0.5) (thickness 0.08)))
  )
  (fp_text value "MECH SHIM" (at 0 0) (layer "F.Fab")
    (effects (font (size 0.4 0.4) (thickness 0.07)))
  )
  (fp_rect (start {-COUPON_W / 2:.2f} {-ey:.2f}) (end {COUPON_W / 2:.2f} {ey:.2f})
    (stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))
{chr(10).join(smd)}
{chr(10).join(tip)}
{chr(10).join(handle)}
)
""",
        encoding="utf-8",
    )


def _add_stiffener_footprint(pcbnew, board, side: int, ref: str) -> None:
    """机械垫片：铜条+邮票孔。

    不接原理图电源/信号网。每通道用独立 MECH_STIFF_* 网名，仅让铜条与
    tip/handle 孔在 DRC 上视为同网搭接（避免空网络互撞），无电路含义。
    """
    _write_stiffener_fp(FP_LIB / "TailFingerStiffener_5ch_P1.27.kicad_mod")
    _wall_x, _outer_x, cx = _coupon_xs(side)
    ey = CASTEL_EDGE_Y
    tag = "L" if side < 0 else "R"
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPIDAsString("SmartPaddle:TailFingerStiffener_5ch_P1.27")
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    fp.SetReference(ref)
    fp.SetValue("mech shim")
    fp.SetPosition(xy(pcbnew, cx, COUPON_CY))
    fp.SetOrientation(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
    for i, x in enumerate(FINGER_XS, start=1):
        net = _ensure_net(board, pcbnew, f"MECH_STIFF_{tag}{i}")
        for pad in (
            _add_pad_smd_f(pcbnew, fp, str(i), x, 0.0, 0.8, STIFF_SMD_H),
            _add_pad_pth(pcbnew, fp, f"T{i}", x, ey, CASTEL_PAD, CASTEL_DRILL),
            _add_pad_pth(pcbnew, fp, f"H{i}", x, -ey, CASTEL_PAD, CASTEL_DRILL),
        ):
            pad.SetNet(net)
    board.Add(fp)


def _mouse_ys() -> tuple[float, ...]:
    """共边上均匀排布的鼠咬孔 Y 坐标（板坐标）。"""
    span = (MOUSE_COUNT - 1) * MOUSE_PITCH
    y0 = COUPON_CY - span / 2
    return tuple(y0 + i * MOUSE_PITCH for i in range(MOUSE_COUNT))


def _add_mousebite_footprint(pcbnew, board, side: int, ref: str) -> None:
    """鼠咬 NPTH：嘉立创规格 Ø0.60、孔边间隙≈0.40，靠垫片内侧。"""
    wall_x, _outer_x, _cx = _coupon_xs(side)
    bite_x = wall_x + side * MOUSE_INSET
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPIDAsString("SmartPaddle:TailStiffenerMousebites")
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    fp.SetReference(ref)
    fp.SetValue("mousebite NPTH")
    fp.SetPosition(xy(pcbnew, bite_x, COUPON_CY))
    for by in _mouse_ys():
        _add_pad_npth(pcbnew, fp, 0.0, by - COUPON_CY, MOUSE_PAD, MOUSE_DRILL)
    board.Add(fp)


def _write_tip_fp(path: Path) -> None:
    pads = [
        f'  (pad "{i}" smd rect (at {x:.2f} {-TIP_SMD_H / 2:.2f}) '
        f'(size {TIP_SMD_W} {TIP_SMD_H}) (layers "F.Cu" "F.Mask"))'
        for i, x in enumerate(FINGER_XS, start=1)
    ]
    path.write_text(
        f"""(footprint "TailTipCastellation_5ch"
  (version 20240108)
  (generator "SmartPaddle")
  (layer "F.Cu")
  (descr "F-only tip pads for stiffener stack; NOT PTH")
  (attr smd)
  (fp_text reference "REF**" (at 0 -1.8) (layer "F.SilkS")
    (effects (font (size 0.5 0.5) (thickness 0.08)))
  )
  (fp_text value "TIP_F" (at 0 0.8) (layer "F.Fab") hide
    (effects (font (size 0.4 0.4) (thickness 0.07)))
  )
{chr(10).join(pads)}
)
""",
        encoding="utf-8",
    )


def _add_tip_castellation_footprint(pcbnew, board) -> None:
    """主板尖端 F 面 SMD（叠焊对位；保留金手指网络）。"""
    _write_tip_fp(FP_LIB / "TailTipCastellation_5ch.kicad_mod")
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPIDAsString("SmartPaddle:TailTipCastellation_5ch")
    fp.SetAttributes(pcbnew.FP_SMD)
    fp.SetReference("TAIL_TIP")
    fp.SetValue("tip F pads for stiffener")
    fp.SetPosition(xy(pcbnew, 0.0, MAIN_TIP_Y))
    for i, (x, net_name) in enumerate(zip(FINGER_XS, TIP_NETS), start=1):
        pad = _add_pad_smd_f(pcbnew, fp, str(i), x, -TIP_SMD_H / 2, TIP_SMD_W, TIP_SMD_H)
        pad.SetNet(_ensure_net(board, pcbnew, net_name))
    board.Add(fp)


# ===== 分区：公开 API =====
def _run_cleanup(board_path: Path) -> tuple[int, int]:
    """cleanup 拆成独立子进程：删 → 重载补墙，避免 KiCad SWIG 在 Remove 后崩溃。"""
    py = sys.executable
    script = str(Path(__file__).resolve())
    r1 = subprocess.run(
        [py, script, "--board", str(board_path), "--phase", "cleanup_delete"],
        check=False,
    )
    if r1.returncode != 0:
        raise SystemExit(r1.returncode)
    r2 = subprocess.run(
        [py, script, "--board", str(board_path), "--phase", "cleanup_wall"],
        check=False,
    )
    if r2.returncode != 0:
        raise SystemExit(r2.returncode)
    return 0, 0


def _run_cleanup_delete(board_path: Path) -> tuple[int, int]:
    import pcbnew

    board = load_board(pcbnew, board_path)
    n_fp, n_draw = _remove_owned(board, pcbnew)
    save_board(board, board_path)
    print(f"CLEANUP_DELETE footprints={n_fp} drawings={n_draw}")
    return n_fp, n_draw


def _run_cleanup_wall(board_path: Path) -> int:
    import pcbnew

    board = load_board(pcbnew, board_path)
    n = 0
    for wx in (-WALL_X, WALL_X):
        n += _ensure_wall_span(pcbnew, board, wx, COUPON_Y_LO, COUPON_Y_HI)
    save_board(board, board_path)
    print(f"CLEANUP_WALL stubs_added={n}")
    return n


def _run_build(board_path: Path) -> tuple[float, float, bool, int]:
    import pcbnew

    board = load_board(pcbnew, board_path)
    n_cut = _cut_both_walls(pcbnew, board)
    print(f"WALL_CUT removed={n_cut}")
    for side, tag in ((-1, "L"), (1, "R")):
        _add_peninsula_outline(pcbnew, board, side)
        _add_stiffener_footprint(pcbnew, board, side, f"TAIL_STIFF_{tag}")
        _add_mousebite_footprint(pcbnew, board, side, f"TAIL_MB_{tag}")
        _add_keepout(pcbnew, board, side, tag)
    _add_tip_castellation_footprint(pcbnew, board)
    save_board(board, board_path)
    # 不在同进程再 Load/验外形（SWIG 在大量 Add 后易损坏）；由调用方另开进程检查。
    return (0.0, 0.0, True, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 4.4: wall-attached mech stiffener shims")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument(
        "--phase",
        choices=("all", "cleanup", "cleanup_delete", "cleanup_wall", "build"),
        default="all",
    )
    args = parser.parse_args()

    if args.phase == "cleanup_delete":
        _run_cleanup_delete(args.board)
        return
    if args.phase == "cleanup_wall":
        _run_cleanup_wall(args.board)
        return
    if args.phase == "cleanup":
        _run_cleanup(args.board)
        print("CLEANUP_OK")
        return
    if args.phase == "build":
        _run_build(args.board)
        # 独立进程验证外形
        v = subprocess.run(
            [
                sys.executable,
                "-c",
                "import pcbnew; b=pcbnew.LoadBoard(r'%s'); o=pcbnew.SHAPE_POLY_SET(); "
                "ok=bool(b.GetBoardPolygonOutlines(o)); "
                "print(f'VERIFY outline_ok={ok} outlines={o.OutlineCount()}')"
                % str(args.board.resolve()),
            ],
            check=False,
        )
        if v.returncode != 0:
            raise SystemExit(v.returncode)
        print("BUILD_OK")
        return

    py = sys.executable
    script = str(Path(__file__).resolve())
    for phase in ("cleanup", "build"):
        r = subprocess.run([py, script, "--board", str(args.board), "--phase", phase], check=False)
        if r.returncode != 0:
            raise SystemExit(r.returncode)

    wall_l, outer_l, _ = _coupon_xs(-1)
    wall_r, outer_r, _ = _coupon_xs(1)
    print("=== Step 4.4 完成 ===")
    print(
        "几何: 垫片 {:.1f}×{:.1f} 半岛外绕侧墙+鼠咬孔；铜条搭接邮票孔；无电源/信号网".format(
            COUPON_W, COUPON_H
        )
    )
    print(f"左垫片: x=[{outer_l:.2f},{wall_l:.2f}] y=[{COUPON_Y_LO:.2f},{COUPON_Y_HI:.2f}]")
    print(f"右垫片: x=[{wall_r:.2f},{outer_r:.2f}] y=[{COUPON_Y_LO:.2f},{COUPON_Y_HI:.2f}]")
    print(f"鼠咬孔 {MOUSE_COUNT}×Ø{MOUSE_DRILL} pitch={MOUSE_PITCH} @ x=±{WALL_X}±{MOUSE_INSET}")
    print("半孔: tip/handle 孔心在 Edge.Cuts；下单选 Castellated")
    print("装配: 沿鼠咬孔掰下 → 叠 F 金手指 → 尖端对焊 TAIL_TIP → 拍柄侧焊手指中段")


if __name__ == "__main__":
    main()
