#!/usr/bin/env python3
"""Step 4.4 — 尾插 0.8→1.6mm F 面加强小板（左右各一，同拼可掰）。

几何（不加长计费包围盒）：
  - 主板尖端恢复原尖端边 + TAIL_TIP 半孔开窗（不往 +Y 伸出）
  - 在拍柄侧墙 x=±8.70 近尖端处左右各挂一块 8×8 mm coupon
  - 侧挂：外轮廓绕行 + 中间铣槽 + NPTH 掰桥（禁止 Edge.Cuts 圆）
  - 尖端/拍柄边：Edge.Cuts 半圆开窗 + PTH 半孔

可重复运行；须在 step2/step3 之后运行。
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
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
FINGER_F_NETS = ("vbat_in", "vbat_sw", "btn_sw", "usb_dp", "uart_tx")

MAIN_TIP_Y = 97.7
MAIN_TIP_HALF_W = 3.51

# 侧墙（拍柄近尖端竖边）；coupon 顶边对齐肩线，不越过尖端
WALL_X = 8.70
SHOULDER_Y = 89.70
MOUSE_GAP = 1.2
DAUGHTER = 8.0
COUPON_Y_HI = SHOULDER_Y  # tip 边（朝尖端 / +Y）
COUPON_Y_LO = COUPON_Y_HI - DAUGHTER  # 81.70
# 铣槽：上下各留掰桥
BRIDGE = 1.1
SLOT_Y_LO = COUPON_Y_LO + BRIDGE
SLOT_Y_HI = COUPON_Y_HI - BRIDGE
COUPON_CY = COUPON_Y_HI - DAUGHTER / 2

CASTEL_DRILL = 0.70
CASTEL_PAD = 1.10
CASTEL_R = CASTEL_DRILL / 2
MOUSE_DRILL = 0.60
EDGE_W = 0.10


# ===== 分区：私有成员 =====
def _ensure_net(board, pcbnew, name: str):
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def _near(a: float, b: float, tol: float = 0.08) -> bool:
    return abs(a - b) <= tol


def _coupon_xs(side: int) -> tuple[float, float, float]:
    """side=-1 左 / +1 右 → (wall_x, inner_x, outer_x)。"""
    wall_x = side * WALL_X
    inner_x = wall_x + side * MOUSE_GAP
    outer_x = inner_x + side * DAUGHTER
    return wall_x, inner_x, outer_x


def _iter_drawings(board):
    try:
        return list(board.GetDrawings())
    except TypeError:
        raw = board.Drawings()
        try:
            return list(raw)
        except TypeError:
            n = raw.size() if hasattr(raw, "size") else len(raw)
            return [raw[i] if hasattr(raw, "__getitem__") else raw.Get(i) for i in range(n)]


def _remove_owned(board, pcbnew) -> tuple[int, int]:
    """清掉本脚本生成物；侧墙附着窗在单次快照里处理，避免 SWIG 迭代崩。"""
    n_fp = n_draw = 0
    drawings = _iter_drawings(board)
    to_remove = []
    # wall_x -> list of (lo, hi) segments overlapping coupon window
    wall_segs: dict[float, list[tuple[float, float]]] = {-WALL_X: [], WALL_X: []}

    for drawing in drawings:
        if drawing.GetLayer() != pcbnew.Edge_Cuts:
            continue
        bbox = drawing.GetBoundingBox()
        y0 = pcbnew.ToMM(bbox.GetY())
        y1 = y0 + pcbnew.ToMM(bbox.GetHeight())
        x0 = pcbnew.ToMM(bbox.GetX())
        x1 = x0 + pcbnew.ToMM(bbox.GetWidth())

        if y0 > MAIN_TIP_Y + 0.05:
            to_remove.append(drawing)
            continue
        # 任何越过尖端的残余（旧外伸竖边 y 到 106、半孔弧到 tip+0.35）
        if y1 > MAIN_TIP_Y + 0.2:
            to_remove.append(drawing)
            continue
        # 尖端横边（与上一条互补：高度很矮的 tip 线段）
        if (
            y0 <= MAIN_TIP_Y + 0.15
            and y1 >= MAIN_TIP_Y - 0.1
            and x0 >= -MAIN_TIP_HALF_W - 0.5
            and x1 <= MAIN_TIP_HALF_W + 0.5
        ):
            to_remove.append(drawing)
            continue
        if y1 >= COUPON_Y_LO - 0.4 and y0 <= COUPON_Y_HI + 0.4:
            if x1 < -WALL_X + 0.25 or x0 > WALL_X - 0.25:
                to_remove.append(drawing)
                continue

        if drawing.GetShape() == pcbnew.SHAPE_T_SEGMENT:
            s, e = drawing.GetStart(), drawing.GetEnd()
            sx0, sy0 = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)
            sx1, sy1 = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
            for wx in (-WALL_X, WALL_X):
                if _near(sx0, wx, 0.12) and _near(sx1, wx, 0.12):
                    lo, hi = min(sy0, sy1), max(sy0, sy1)
                    if hi >= COUPON_Y_LO - 1e-3 and lo <= COUPON_Y_HI + 1e-3:
                        wall_segs[wx].append((lo, hi))
                        to_remove.append(drawing)

    # 去重（同一 drawing 可能被多次 append）
    seen = set()
    uniq = []
    for d in to_remove:
        i = id(d)
        if i not in seen:
            seen.add(i)
            uniq.append(d)
    for drawing in uniq:
        board.Remove(drawing)
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

    # 按快照补侧墙 stub + 附着窗实墙（之后再挖开挂小板）
    for wx, segs in wall_segs.items():
        stubs_lo = [lo for lo, hi in segs if lo < COUPON_Y_LO - 1e-3]
        stubs_hi = [hi for lo, hi in segs if hi > COUPON_Y_HI + 1e-3]
        if stubs_lo:
            shape_line(
                pcbnew, board, pcbnew.Edge_Cuts,
                (wx, min(stubs_lo)), (wx, COUPON_Y_LO), EDGE_W,
            )
        if stubs_hi:
            shape_line(
                pcbnew, board, pcbnew.Edge_Cuts,
                (wx, COUPON_Y_HI), (wx, max(stubs_hi)), EDGE_W,
            )
        shape_line(
            pcbnew, board, pcbnew.Edge_Cuts,
            (wx, COUPON_Y_LO), (wx, COUPON_Y_HI), EDGE_W,
        )

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


def _remove_wall_span(board, pcbnew, wall_x: float, y_lo: float, y_hi: float) -> None:
    """只删附着窗内刚补上的实墙段（用坐标匹配，避免再遍历全体 drawings）。"""
    # 在添加后立刻删：扫一遍但容忍失败时用坐标过滤的短列表
    try:
        drawings = list(board.GetDrawings())
    except TypeError:
        # SWIG 已坏则先落盘重载由调用方处理；这里尽量空操作
        return
    for drawing in drawings:
        if drawing.GetLayer() != pcbnew.Edge_Cuts:
            continue
        if drawing.GetShape() != pcbnew.SHAPE_T_SEGMENT:
            continue
        s, e = drawing.GetStart(), drawing.GetEnd()
        x0, y0 = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)
        x1, y1 = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
        if not (_near(x0, wall_x, 0.12) and _near(x1, wall_x, 0.12)):
            continue
        lo, hi = min(y0, y1), max(y0, y1)
        if _near(lo, y_lo, 0.05) and _near(hi, y_hi, 0.05):
            board.Remove(drawing)


def _add_side_coupon_outline(pcbnew, board, side: int) -> None:
    """side=-1 左 / +1 右：挖侧墙，绕行外轮廓 + 铣槽。"""
    wall_x, inner_x, outer_x = _coupon_xs(side)
    y_lo, y_hi = COUPON_Y_LO, COUPON_Y_HI
    cx = (inner_x + outer_x) / 2
    pad_xs = tuple(cx + f for f in FINGER_XS)

    _remove_wall_span(board, pcbnew, wall_x, y_lo, y_hi)

    # 外轮廓（从墙顶绕小板回到墙底）；走向：先到 tip 边再 outer 再 handle
    # 顶桥
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (wall_x, y_hi), (inner_x, y_hi), EDGE_W)
    # tip 半孔边（朝 +Y 外凸）
    _scalloped_horizontal(pcbnew, board, y_hi, inner_x, outer_x, pad_xs, bulge_sign=+1.0)
    # 外边
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (outer_x, y_hi), (outer_x, y_lo), EDGE_W)
    # handle 半孔边（朝 -Y 外凸）
    _scalloped_horizontal(pcbnew, board, y_lo, outer_x, inner_x, pad_xs, bulge_sign=-1.0)
    # 底桥
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (inner_x, y_lo), (wall_x, y_lo), EDGE_W)

    # 铣槽（闭合）：只留上下掰桥
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (wall_x, SLOT_Y_HI), (inner_x, SLOT_Y_HI), EDGE_W)
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (inner_x, SLOT_Y_HI), (inner_x, SLOT_Y_LO), EDGE_W)
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (inner_x, SLOT_Y_LO), (wall_x, SLOT_Y_LO), EDGE_W)
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (wall_x, SLOT_Y_LO), (wall_x, SLOT_Y_HI), EDGE_W)


def _add_main_tip_edge(pcbnew, board) -> None:
    _scalloped_horizontal(
        pcbnew,
        board,
        MAIN_TIP_Y,
        -MAIN_TIP_HALF_W,
        MAIN_TIP_HALF_W,
        FINGER_XS,
        bulge_sign=+1.0,
    )


def _write_tip_fp(path: Path) -> None:
    pads = [
        f'  (pad "{i}" thru_hole circle (at {x:.2f} 0) '
        f'(size {CASTEL_PAD} {CASTEL_PAD}) (drill {CASTEL_DRILL}) '
        f'(layers "*.Cu" "*.Mask"))'
        for i, x in enumerate(FINGER_XS, start=1)
    ]
    path.write_text(
        f"""(footprint "TailTipCastellation_5ch"
  (version 20240108)
  (generator "SmartPaddle")
  (layer "F.Cu")
  (descr "Main-board tip castellations for F-side stiffener stack")
  (attr through_hole)
  (fp_text reference "REF**" (at 0 -1.4) (layer "F.SilkS")
    (effects (font (size 0.5 0.5) (thickness 0.08)))
  )
  (fp_text value "TIP_CASTEL" (at 0 1.4) (layer "F.Fab") hide
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


def _add_pad_npth(pcbnew, fp, x: float, y: float, drill: float):
    pad = pcbnew.PAD(fp)
    pad.SetNumber("")
    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(mk(drill + 0.1), mk(drill + 0.1)))
    pad.SetDrillSize(pcbnew.VECTOR2I(mk(drill), mk(drill)))
    pad.SetLayerSet(pad.UnplatedHoleMask() if hasattr(pad, "UnplatedHoleMask") else pad.PTHMask())
    pad.SetFPRelativePosition(xy(pcbnew, x, y))
    fp.Add(pad)
    return pad


def _add_tip_castellation_footprint(pcbnew, board) -> None:
    _write_tip_fp(FP_LIB / "TailTipCastellation_5ch.kicad_mod")
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference("TAIL_TIP")
    fp.SetValue("tip castellation")
    fp.SetPosition(xy(pcbnew, 0.0, MAIN_TIP_Y))
    for i, (x, net_name) in enumerate(zip(FINGER_XS, FINGER_F_NETS), start=1):
        pad = _add_pad_pth(pcbnew, fp, str(i), x, 0.0, CASTEL_PAD, CASTEL_DRILL)
        pad.SetNet(_ensure_net(board, pcbnew, net_name))
    board.Add(fp)


def _add_stiffener_footprint(pcbnew, board, side: int, ref: str) -> None:
    _, inner_x, outer_x = _coupon_xs(side)
    cx = (inner_x + outer_x) / 2
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue("F stiffener coupon")
    fp.SetPosition(xy(pcbnew, cx, COUPON_CY))
    fp.SetOrientation(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
    for i, (x, net_name) in enumerate(zip(FINGER_XS, FINGER_F_NETS), start=1):
        net = _ensure_net(board, pcbnew, net_name)
        pad = _add_pad_smd_f(pcbnew, fp, str(i), x, 0.0, 0.8, 7.2)
        pad.SetNet(net)
        for pn, py in ((f"T{i}", 4.0), (f"H{i}", -4.0)):
            p = _add_pad_pth(pcbnew, fp, pn, x, py, CASTEL_PAD, CASTEL_DRILL)
            p.SetNet(net)
    board.Add(fp)


def _add_mousebite_footprint(pcbnew, board, side: int, ref: str) -> None:
    wall_x, inner_x, _ = _coupon_xs(side)
    mx = (wall_x + inner_x) / 2
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue("mousebites")
    fp.SetPosition(xy(pcbnew, mx, COUPON_CY))
    for y in (COUPON_Y_HI - BRIDGE / 2, COUPON_Y_LO + BRIDGE / 2):
        for dx in (-0.25, 0.0, 0.25):
            _add_pad_npth(pcbnew, fp, dx, y - COUPON_CY, MOUSE_DRILL)
    board.Add(fp)


# ===== 分区：公开 API =====
def _run_cleanup(board_path: Path) -> tuple[int, int]:
    import pcbnew

    board = load_board(pcbnew, board_path)
    n_fp, n_draw = _remove_owned(board, pcbnew)
    save_board(board, board_path)
    return n_fp, n_draw


def _run_build(board_path: Path) -> tuple[float, float]:
    import pcbnew

    board = load_board(pcbnew, board_path)
    _add_main_tip_edge(pcbnew, board)
    for side, tag in ((-1, "L"), (1, "R")):
        _add_side_coupon_outline(pcbnew, board, side)
        _add_stiffener_footprint(pcbnew, board, side, f"TAIL_STIFF_{tag}")
        _add_mousebite_footprint(pcbnew, board, side, f"TAIL_MB_{tag}")
    _add_tip_castellation_footprint(pcbnew, board)
    save_board(board, board_path)
    bb = board.GetBoardEdgesBoundingBox()
    return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 4.4: dual side-hang stiffener coupons")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument(
        "--phase",
        choices=("all", "cleanup", "build"),
        default="all",
        help="all=两进程清理+重建（避免 pcbnew SWIG 在大量 Remove 后崩溃）",
    )
    args = parser.parse_args()

    if args.phase == "cleanup":
        n_fp, n_draw = _run_cleanup(args.board)
        print(f"CLEANUP_OK footprints={n_fp} drawings={n_draw}")
        return
    if args.phase == "build":
        w, h = _run_build(args.board)
        print(f"BUILD_OK bbox={w:.2f}x{h:.2f}")
        return

    # all：子进程分别跑 cleanup / build，隔离 SWIG 状态
    import subprocess

    py = sys.executable
    script = str(Path(__file__).resolve())
    for phase in ("cleanup", "build"):
        r = subprocess.run(
            [py, script, "--board", str(args.board), "--phase", phase],
            check=False,
        )
        if r.returncode != 0:
            raise SystemExit(r.returncode)

    _, li, lo = _coupon_xs(-1)
    _, ri, ro = _coupon_xs(1)
    print("=== Step 4.4 完成 ===")
    print("几何: 尖端不外伸；左右侧挂 8×8 @ 侧墙 x=±{:.1f}".format(WALL_X))
    print(f"左小板: x=[{lo:.2f},{li:.2f}] y=[{COUPON_Y_LO:.2f},{COUPON_Y_HI:.2f}]")
    print(f"右小板: x=[{ri:.2f},{ro:.2f}] y=[{COUPON_Y_LO:.2f},{COUPON_Y_HI:.2f}]")
    print("装配: 掰下一侧 → 金手指朝上叠 F 面 → 尖端对焊 TAIL_TIP → 拍柄侧焊原 F 金手指")
    print("注意: 重跑 step2 后需再跑本脚本。")


if __name__ == "__main__":
    main()
