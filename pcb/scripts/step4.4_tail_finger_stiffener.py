#!/usr/bin/env python3
"""Step 4.4 — 尾插 0.8→1.6mm F 面加强小板（左右各一）。

几何原则：
  - 只增删本脚本产物；绝不改 step2 画的主板侧墙/尖端边
  - 左右各一块独立封闭外形（与侧墙留铣缝，不共边）
  - 小板约 8×6.8：尖端与叠焊对齐，拍柄侧比金手指短 ~1.2mm，便于中段焊接
  - 小板 tip/handle：半圆开窗 + PTH 半孔（孔心必须在 Edge.Cuts 上）
  - 主板尖端：只放 TAIL_TIP 焊盘（半孔靠 step2 尖端边切过孔心）

若外形曾被旧版脚本挖坏：先跑 step2 → step3，再跑本脚本。
可重复运行；须在 step2/step3 之后运行。
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
FINGER_F_NETS = ("SYS_5V_IN", "SYS_5V_SW", "btn_sw", "USB_DP", "UART_TX")

MAIN_TIP_Y = 97.7

WALL_X = 8.70
SHOULDER_Y = 89.70
MILL_GAP = 1.2
# 小板横向仍 8mm；纵向比金手指短 1.2mm（仅缩短拍柄侧），叠焊后 H 半孔落在手指中段。
COUPON_W = 8.0
COUPON_H = 6.8  # was 8.0; tip edge stays at SHOULDER_Y
COUPON_Y_HI = SHOULDER_Y
COUPON_Y_LO = COUPON_Y_HI - COUPON_H
COUPON_CY = COUPON_Y_HI - COUPON_H / 2
# cleanup 覆盖旧 8mm 与新 6.8mm 外形
COUPON_CLEAN_Y_LO = SHOULDER_Y - 9.0

CASTEL_DRILL = 0.70
CASTEL_PAD = 1.00  # 节距 1.27 → 间隙 0.27 ≥ 0.20 clearance
CASTEL_R = CASTEL_DRILL / 2
CASTEL_EDGE_Y = COUPON_H / 2  # T/H 孔心相对封装中心
STIFF_SMD_H = COUPON_H - 1.2  # 两端各留 0.6mm，避免盖住半孔
EDGE_W = 0.10
TIP_SMD_W = 0.80
TIP_SMD_H = 1.20


# ===== 分区：私有成员 =====
def _ensure_net(board, pcbnew, name: str):
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def _coupon_xs(side: int) -> tuple[float, float, float]:
    """side=-1 左 / +1 右 → (wall_x, inner_x, outer_x)。"""
    wall_x = side * WALL_X
    inner_x = wall_x + side * MILL_GAP
    outer_x = inner_x + side * COUPON_W
    return wall_x, inner_x, outer_x


def _iter_drawings(board):
    try:
        return list(board.GetDrawings())
    except TypeError:
        raw = board.Drawings()
        try:
            return list(raw)
        except TypeError:
            n = raw.size() if hasattr(raw, "size") else 0
            return [raw[i] for i in range(n)]


def _remove_owned(board, pcbnew) -> tuple[int, int]:
    """只删本脚本的小板外形 / 旧外伸 / 旧位号；不碰主板侧墙与 step2 尖端边。"""
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

        # 旧尖端外伸（y 越过 tip）
        if y0 > MAIN_TIP_Y + 0.05:
            to_remove.append(drawing)
            continue

        # 仅小板区域：完全在侧墙外侧（不删墙上的 step2 线段）
        if y1 >= COUPON_CLEAN_Y_LO - 0.4 and y0 <= COUPON_Y_HI + 0.4:
            if x1 < -WALL_X - 0.05 or x0 > WALL_X + 0.05:
                to_remove.append(drawing)

    seen: set[int] = set()
    for d in to_remove:
        i = id(d)
        if i in seen:
            continue
        seen.add(i)
        board.Remove(d)
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


def _add_detached_coupon_outline(pcbnew, board, side: int) -> None:
    _, inner_x, outer_x = _coupon_xs(side)
    y_lo, y_hi = COUPON_Y_LO, COUPON_Y_HI
    cx = (inner_x + outer_x) / 2
    pad_xs = tuple(cx + f for f in FINGER_XS)

    _scalloped_horizontal(pcbnew, board, y_hi, inner_x, outer_x, pad_xs, bulge_sign=+1.0)
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (outer_x, y_hi), (outer_x, y_lo), EDGE_W)
    _scalloped_horizontal(pcbnew, board, y_lo, outer_x, inner_x, pad_xs, bulge_sign=-1.0)
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (inner_x, y_lo), (inner_x, y_hi), EDGE_W)


def _add_tip_castellation_footprint(pcbnew, board) -> None:
    """主板尖端只做 F 面 SMD（禁止 PTH：会与 B 面异网金手指短路）。"""
    _write_tip_fp(FP_LIB / "TailTipCastellation_5ch.kicad_mod")
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPIDAsString("SmartPaddle:TailTipCastellation_5ch")
    fp.SetAttributes(pcbnew.FP_SMD)
    fp.SetReference("TAIL_TIP")
    fp.SetValue("tip F pads for stiffener")
    fp.SetPosition(xy(pcbnew, 0.0, MAIN_TIP_Y))
    for i, (x, net_name) in enumerate(zip(FINGER_XS, FINGER_F_NETS), start=1):
        # 焊盘中心在尖端边上，向板内偏半个高度，避免整颗掉出板外
        pad = _add_pad_smd_f(pcbnew, fp, str(i), x, -TIP_SMD_H / 2, TIP_SMD_W, TIP_SMD_H)
        pad.SetNet(_ensure_net(board, pcbnew, net_name))
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
  (descr "F-only tip pads for stiffener stack; NOT PTH (would short B-side fingers)")
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
    """同步库封装：半孔孔心在 ±CASTEL_EDGE_Y；Fab 边过孔心（看起来就是半孔，不是缩在框里）。"""
    ey = CASTEL_EDGE_Y
    smd_h = STIFF_SMD_H
    pad_d = CASTEL_PAD
    drill = CASTEL_DRILL
    # Fab 顶/底边过孔心；CrtYd 再外扩半圆铣削余量
    fab = f'  (fp_rect (start {-COUPON_W / 2:.2f} {-ey:.2f}) (end {COUPON_W / 2:.2f} {ey:.2f}) (stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))'
    crtyd = (
        f'  (fp_rect (start {-COUPON_W / 2 - 0.2:.2f} {-ey - CASTEL_R - 0.15:.2f}) '
        f'(end {COUPON_W / 2 + 0.2:.2f} {ey + CASTEL_R + 0.15:.2f}) '
        f'(stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))'
    )
    # Fab 半圆提示（与板上 Edge.Cuts 同向），避免只看到“整圆在框内”
    scallop_bits: list[str] = []
    for x in FINGER_XS:
        scallop_bits.append(
            f'  (fp_arc (start {x - CASTEL_R:.2f} {ey:.2f}) (mid {x:.2f} {ey + CASTEL_R:.2f}) '
            f'(end {x + CASTEL_R:.2f} {ey:.2f}) (stroke (width 0.10) (type solid)) (layer "F.Fab"))'
        )
        scallop_bits.append(
            f'  (fp_arc (start {x + CASTEL_R:.2f} {-ey:.2f}) (mid {x:.2f} {-ey - CASTEL_R:.2f}) '
            f'(end {x - CASTEL_R:.2f} {-ey:.2f}) (stroke (width 0.10) (type solid)) (layer "F.Fab"))'
        )
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
  (descr "F-side stiffener {COUPON_W:.1f}x{COUPON_H:.1f}mm; tip/handle PTH centers ON edge for castellations")
  (tags "gold finger stiffener castellation SmartPaddle")
  (attr through_hole)
  (fp_text reference "REF**" (at 0 0) (layer "F.SilkS")
    (effects (font (size 0.6 0.6) (thickness 0.1)))
  )
  (fp_text value "STIFFENER F stack" (at 0 0) (layer "F.Fab")
    (effects (font (size 0.45 0.45) (thickness 0.08)))
  )
{fab}
{crtyd}
{chr(10).join(scallop_bits)}
  (fp_text user "TIP" (at 0 {ey - 0.9:.2f}) (layer "F.SilkS")
    (effects (font (size 0.45 0.45) (thickness 0.08)))
  )
  (fp_text user "HANDLE" (at 0 {-ey + 0.9:.2f}) (layer "F.SilkS")
    (effects (font (size 0.4 0.4) (thickness 0.07)))
  )
{chr(10).join(smd)}
{chr(10).join(tip)}
{chr(10).join(handle)}
)
""",
        encoding="utf-8",
    )


def _add_stiffener_footprint(pcbnew, board, side: int, ref: str) -> None:
    _write_stiffener_fp(FP_LIB / "TailFingerStiffener_5ch_P1.27.kicad_mod")
    _, inner_x, outer_x = _coupon_xs(side)
    cx = (inner_x + outer_x) / 2
    ey = CASTEL_EDGE_Y
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPIDAsString("SmartPaddle:TailFingerStiffener_5ch_P1.27")
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    fp.SetReference(ref)
    fp.SetValue("F stiffener coupon")
    fp.SetPosition(xy(pcbnew, cx, COUPON_CY))
    fp.SetOrientation(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
    # 不在板上手动画 Fab/CrtYd：KiCad Python 的 PCB_SHAPE 坐标易成绝对坐标，会误报 courtyard。
    # 真实裁切以板级 Edge.Cuts 半圆为准（孔心压边）；库文件已同步 6.8mm 几何供对照。
    for i, (x, net_name) in enumerate(zip(FINGER_XS, FINGER_F_NETS), start=1):
        net = _ensure_net(board, pcbnew, net_name)
        pad = _add_pad_smd_f(pcbnew, fp, str(i), x, 0.0, 0.8, STIFF_SMD_H)
        pad.SetNet(net)
        for pn, py in ((f"T{i}", ey), (f"H{i}", -ey)):
            p = _add_pad_pth(pcbnew, fp, pn, x, py, CASTEL_PAD, CASTEL_DRILL)
            p.SetNet(net)
    board.Add(fp)


# ===== 分区：公开 API =====
def _run_cleanup(board_path: Path) -> tuple[int, int]:
    import pcbnew

    board = load_board(pcbnew, board_path)
    n_fp, n_draw = _remove_owned(board, pcbnew)
    save_board(board, board_path)
    return n_fp, n_draw


def _run_build(board_path: Path) -> tuple[float, float, bool, int]:
    import pcbnew

    board = load_board(pcbnew, board_path)
    for side, tag in ((-1, "L"), (1, "R")):
        _add_detached_coupon_outline(pcbnew, board, side)
        _add_stiffener_footprint(pcbnew, board, side, f"TAIL_STIFF_{tag}")
    _add_tip_castellation_footprint(pcbnew, board)
    save_board(board, board_path)

    bb = board.GetBoardEdgesBoundingBox()
    outlines = pcbnew.SHAPE_POLY_SET()
    ok = bool(board.GetBoardPolygonOutlines(outlines))
    return (
        pcbnew.ToMM(bb.GetWidth()),
        pcbnew.ToMM(bb.GetHeight()),
        ok,
        outlines.OutlineCount(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 4.4: detached dual stiffener coupons")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--phase", choices=("all", "cleanup", "build"), default="all")
    args = parser.parse_args()

    if args.phase == "cleanup":
        n_fp, n_draw = _run_cleanup(args.board)
        print(f"CLEANUP_OK footprints={n_fp} drawings={n_draw}")
        return
    if args.phase == "build":
        w, h, ok, n_out = _run_build(args.board)
        print(f"BUILD_OK bbox={w:.2f}x{h:.2f} outline_ok={ok} outlines={n_out}")
        return

    py = sys.executable
    script = str(Path(__file__).resolve())
    for phase in ("cleanup", "build"):
        r = subprocess.run([py, script, "--board", str(args.board), "--phase", phase], check=False)
        if r.returncode != 0:
            raise SystemExit(r.returncode)

    _, li, lo = _coupon_xs(-1)
    _, ri, ro = _coupon_xs(1)
    print("=== Step 4.4 完成 ===")
    print(
        "几何: 不改主板外形；左右独立 {:.1f}×{:.1f}（铣缝 {:.1f} mm；拍柄侧比金手指短 {:.1f} mm）".format(
            COUPON_W, COUPON_H, MILL_GAP, 8.0 - COUPON_H
        )
    )
    print(f"左小板: x=[{lo:.2f},{li:.2f}] y=[{COUPON_Y_LO:.2f},{COUPON_Y_HI:.2f}]")
    print(f"右小板: x=[{ri:.2f},{ro:.2f}] y=[{COUPON_Y_LO:.2f},{COUPON_Y_HI:.2f}]")
    print("半孔: tip/handle 孔心压在 Edge.Cuts；下单须选 Castellated/半孔电镀")
    print("若预览仍是矩形: 先 step2→step3 重绘主板外形，再跑本脚本")
    print("装配: 取下一块 → 金手指朝上叠 F 面 → 尖端对焊 TAIL_TIP → 拍柄侧焊原 F 金手指中段")


if __name__ == "__main__":
    main()
