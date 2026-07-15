#!/usr/bin/env python3
"""Step 4.4 — 尾插 0.8→1.6mm F 面加强小板（同拼可掰）。

几何（避免 Edge.Cuts 圆打断外形 → 预览退化成大矩形）：
  - 小板作为主板尖端的连续外轮廓突出，左右留掰桥
  - 中间铣槽（闭合内轮廓）分隔主板尖端与小板
  - 尖端/拍柄边：Edge.Cuts 半圆开窗（可见邮票孔切削轮廓）+ PTH 半孔焊盘
  - 掰桥上：NPTH 掰孔（不要用 Edge.Cuts 圆）

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
STIFF_FP_NAME = "TailFingerStiffener_5ch_P1.27"
OWNER = "tail_finger_stiffener"
REF = "TAIL_STIFF"
MOUSE_REF = "TAIL_MB"

FINGER_XS = (-2.54, -1.27, 0.0, 1.27, 2.54)
FINGER_F_NETS = ("vbat_in", "vbat_sw", "btn_sw", "usb_dp", "uart_tx")

MAIN_TIP_Y = 97.7
MAIN_TIP_HALF_W = 3.51
MOUSE_GAP = 1.2
DAUGHTER_W = 8.0
DAUGHTER_H = 8.0
DAUGHTER_Y_INNER = MAIN_TIP_Y + MOUSE_GAP  # 98.9 handle / 邮票孔边
DAUGHTER_Y_OUTER = DAUGHTER_Y_INNER + DAUGHTER_H  # 106.9 tip
DAUGHTER_CX = 0.0
DAUGHTER_CY = (DAUGHTER_Y_INNER + DAUGHTER_Y_OUTER) / 2
COUPON_HALF_W = DAUGHTER_W / 2  # 4.0
# 中间铣槽半宽：左右各留 ~1mm 掰桥
SLOT_HALF_W = 3.0

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


def _iter_drawings(board):
    """KiCad SWIG: 先快照 drawings，避免 Remove(footprint) 后 GetDrawings 崩。"""
    try:
        return list(board.GetDrawings())
    except TypeError:
        drawings = []
        d = board.GetFirstDrawing() if hasattr(board, "GetFirstDrawing") else None
        if d is None:
            # 退路：Drawings() 在部分版本是裸 SWIG 容器
            raw = board.Drawings()
            try:
                return list(raw)
            except TypeError:
                n = raw.size() if hasattr(raw, "size") else len(raw)
                for i in range(n):
                    drawings.append(raw[i] if hasattr(raw, "__getitem__") else raw.Get(i))
                return drawings
        while d:
            drawings.append(d)
            d = d.Next() if hasattr(d, "Next") else None
        return drawings


def _remove_owned(board, pcbnew) -> tuple[int, int]:
    """删除本脚本上次生成的封装与小板相关 Edge.Cuts。"""
    n_fp = n_draw = 0

    # 必须先收集 Edge.Cuts，再删封装（删 FP 后部分 KiCad 版本 GetDrawings 会坏）
    to_remove_draw = []
    for drawing in _iter_drawings(board):
        if drawing.GetLayer() != pcbnew.Edge_Cuts:
            continue
        bbox = drawing.GetBoundingBox()
        y0 = pcbnew.ToMM(bbox.GetY())
        y1 = y0 + pcbnew.ToMM(bbox.GetHeight())
        x0 = pcbnew.ToMM(bbox.GetX())
        x1 = x0 + pcbnew.ToMM(bbox.GetWidth())
        # 小板外延 / 铣槽 / 旧掰孔圆（y 越过尖端）
        if y0 > MAIN_TIP_Y + 0.15 or (y1 > MAIN_TIP_Y + 0.4 and y0 >= MAIN_TIP_Y - 0.2):
            if y0 > MAIN_TIP_Y - 0.05:
                to_remove_draw.append(drawing)
                continue
        # 尖端横边线段（将被半孔弧替换）
        if (
            _near(y0, MAIN_TIP_Y, 0.12)
            and _near(y1, MAIN_TIP_Y, 0.12)
            and x0 >= -MAIN_TIP_HALF_W - 0.2
            and x1 <= MAIN_TIP_HALF_W + 0.2
        ):
            to_remove_draw.append(drawing)

    for drawing in to_remove_draw:
        board.Remove(drawing)
        n_draw += 1

    for fp in list(board.GetFootprints()):
        ref = fp.GetReference()
        if ref in (REF, "TAIL_TIP", MOUSE_REF) or ref.startswith("TAIL_TIP"):
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
    """沿 y=const 从 x_from→x_to 画直线+半圆开窗。bulge_sign=+1 朝 +Y。"""
    lo, hi = (x_from, x_to) if x_to >= x_from else (x_to, x_from)
    going_right = x_to >= x_from
    # 始终按从左到右生成几何，再按走向拼接
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


def _add_protrusion_and_slot(pcbnew, board) -> None:
    """小板外轮廓突出 + 中间铣槽（半孔开窗）+ 左右掰桥。"""
    hw = COUPON_HALF_W
    y_tip = MAIN_TIP_Y
    y_h = DAUGHTER_Y_INNER
    y_o = DAUGHTER_Y_OUTER

    # 外轮廓：从原尖端左右角接到小板，尖端外边半孔开窗
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (-MAIN_TIP_HALF_W, y_tip), (-hw, y_tip), EDGE_W)
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (-hw, y_tip), (-hw, y_o), EDGE_W)
    _scalloped_horizontal(pcbnew, board, y_o, -hw, hw, FINGER_XS, bulge_sign=+1.0)
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (hw, y_o), (hw, y_tip), EDGE_W)
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (hw, y_tip), (MAIN_TIP_HALF_W, y_tip), EDGE_W)

    # 内铣槽：尖端半孔朝槽内(+Y)，拍柄半孔朝槽内(-Y)
    sx = SLOT_HALF_W
    _scalloped_horizontal(pcbnew, board, y_tip, -sx, sx, FINGER_XS, bulge_sign=+1.0)
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (sx, y_tip), (sx, y_h), EDGE_W)
    _scalloped_horizontal(pcbnew, board, y_h, sx, -sx, FINGER_XS, bulge_sign=-1.0)
    shape_line(pcbnew, board, pcbnew.Edge_Cuts, (-sx, y_h), (-sx, y_tip), EDGE_W)


def _write_tip_fp(path: Path) -> None:
    pads = []
    for i, x in enumerate(FINGER_XS, start=1):
        pads.append(
            f'  (pad "{i}" thru_hole circle (at {x:.2f} 0) '
            f'(size {CASTEL_PAD} {CASTEL_PAD}) (drill {CASTEL_DRILL}) '
            f'(layers "*.Cu" "*.Mask"))'
        )
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


def _write_mousebite_fp(path: Path) -> None:
    """左右掰桥 NPTH；本地坐标原点放在槽中线。"""
    pads = []
    # 左桥 x≈-3.5，右桥 x≈+3.5；沿缝 3 孔
    for side in (-1, 1):
        x = side * (SLOT_HALF_W + COUPON_HALF_W) / 2  # -3.5 / +3.5
        for dy in (-0.35, 0.0, 0.35):
            pads.append(
                f'  (pad "" npth circle (at {x:.2f} {dy:.2f}) '
                f'(size {MOUSE_DRILL + 0.1:.2f} {MOUSE_DRILL + 0.1:.2f}) '
                f'(drill {MOUSE_DRILL:.2f}) (layers "*.Cu" "*.Mask"))'
            )
    path.write_text(
        f"""(footprint "TailStiffenerMousebites"
  (version 20240108)
  (generator "SmartPaddle")
  (layer "F.Cu")
  (descr "NPTH mousebites on stiffener breakaway bridges (not Edge.Cuts circles)")
  (attr board_only exclude_from_pos_files exclude_from_bom)
  (fp_text reference "REF**" (at 0 -1.2) (layer "F.SilkS") hide
    (effects (font (size 0.4 0.4) (thickness 0.07)))
  )
  (fp_text value "MOUSEBITE" (at 0 1.2) (layer "F.Fab") hide
    (effects (font (size 0.35 0.35) (thickness 0.06)))
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


def _add_stiffener_footprint(pcbnew, board) -> None:
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(REF)
    fp.SetValue("F stiffener coupon")
    fp.SetPosition(xy(pcbnew, DAUGHTER_CX, DAUGHTER_CY))
    fp.SetOrientation(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
    for i, (x, net_name) in enumerate(zip(FINGER_XS, FINGER_F_NETS), start=1):
        net = _ensure_net(board, pcbnew, net_name)
        pad = _add_pad_smd_f(pcbnew, fp, str(i), x, 0.0, 0.8, 7.2)
        pad.SetNet(net)
        for pn, py in ((f"T{i}", 4.0), (f"H{i}", -4.0)):
            p = _add_pad_pth(pcbnew, fp, pn, x, py, CASTEL_PAD, CASTEL_DRILL)
            p.SetNet(net)
    board.Add(fp)


def _add_mousebite_footprint(pcbnew, board) -> None:
    _write_mousebite_fp(FP_LIB / "TailStiffenerMousebites.kicad_mod")
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(MOUSE_REF)
    fp.SetValue("mousebites")
    fp.SetPosition(xy(pcbnew, 0.0, (MAIN_TIP_Y + DAUGHTER_Y_INNER) / 2))
    for side in (-1, 1):
        x = side * (SLOT_HALF_W + COUPON_HALF_W) / 2
        for dy in (-0.35, 0.0, 0.35):
            _add_pad_npth(pcbnew, fp, x, dy, MOUSE_DRILL)
    board.Add(fp)


# ===== 分区：公开 API =====
def main() -> None:
    parser = argparse.ArgumentParser(description="Step 4.4: Tail finger F-side stiffener coupon")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    n_fp, n_draw = _remove_owned(board, pcbnew)
    _add_protrusion_and_slot(pcbnew, board)
    _write_tip_fp(FP_LIB / "TailTipCastellation_5ch.kicad_mod")
    _write_mousebite_fp(FP_LIB / "TailStiffenerMousebites.kicad_mod")
    _add_tip_castellation_footprint(pcbnew, board)
    _add_stiffener_footprint(pcbnew, board)
    _add_mousebite_footprint(pcbnew, board)
    save_board(board, args.board)

    print("=== Step 4.4 完成 ===")
    print(f"清理: footprints={n_fp}, edge_drawings≈{n_draw}")
    print(f"几何: 尖端突出小板 + 中间铣槽 + 半孔弧开窗 + NPTH 掰桥")
    print(f"主板尖端邮票孔: TAIL_TIP @ y={MAIN_TIP_Y}")
    print(
        f"加强小板: {REF} 中心=({DAUGHTER_CX},{DAUGHTER_CY:.2f}) "
        f"外形 {DAUGHTER_W}×{DAUGHTER_H} mm, y=[{DAUGHTER_Y_INNER:.1f},{DAUGHTER_Y_OUTER:.1f}]"
    )
    print(
        "装配: 掰断左右桥 → 金手指朝上叠到主板 F 面 → 尖端邮票孔对焊 → "
        "拍柄侧邮票孔焊在原 F 金手指上；B 面金手指仍直接接触尾插。"
    )
    print("注意: 若重跑 step2，需再跑本脚本以恢复小板 Edge.Cuts。")


if __name__ == "__main__":
    main()
