#!/usr/bin/env python3
"""Step 4.4 — 尾插 0.8→1.6mm F 面加强小板（同拼可掰）。

在主板尖端外挂一块 8×8mm 矩形 coupon：
  - 尖端边 / 拍柄边：邮票孔（与 5 路 F 面金手指同网）
  - 左右边：掰板孔（无电气）
  - 单面金手指朝上；掰下后叠焊到主板 F 面金手指上，总厚约 1.6mm
主板尖端同步加邮票孔，与小板尖端孔上下对齐焊接。

可重复运行：先按 owner 标记清掉旧物再重建。
须在 step2/step3 之后运行（step2 会清掉 Edge.Cuts）。
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import circle, load_board, mk, polyline, save_board, xy

# ===== 分区：常量/配置 =====
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
FP_LIB = ROOT / "pcb" / "layouts" / "lib" / "footprints.pretty"
STIFF_FP_NAME = "TailFingerStiffener_5ch_P1.27"
OWNER = "tail_finger_stiffener"
REF = "TAIL_STIFF"

FINGER_XS = (-2.54, -1.27, 0.0, 1.27, 2.54)
FINGER_F_NETS = ("vbat_in", "vbat_sw", "btn_sw", "usb_dp", "uart_tx")

MAIN_TIP_Y = 97.7
MOUSE_GAP = 1.2
DAUGHTER_W = 8.0
DAUGHTER_H = 8.0
# 小板：内边朝主板尖端，外边为叠放后的尖端
DAUGHTER_Y_INNER = MAIN_TIP_Y + MOUSE_GAP
DAUGHTER_Y_OUTER = DAUGHTER_Y_INNER + DAUGHTER_H
DAUGHTER_CX = 0.0
DAUGHTER_CY = (DAUGHTER_Y_INNER + DAUGHTER_Y_OUTER) / 2

CASTEL_DRILL = 0.70
CASTEL_PAD = 1.10
MOUSE_DRILL = 0.55


# ===== 分区：私有成员 =====
def _ensure_net(board, pcbnew, name: str):
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def _set_owner(item, key: str = OWNER) -> None:
    if hasattr(item, "SetField"):
        try:
            item.SetField("smartpaddle_owner", key)
            return
        except Exception:
            pass
    if hasattr(item, "AddField"):
        try:
            item.AddField("smartpaddle_owner", key)
            return
        except Exception:
            pass
    # 退路：用 Value / 注释无法覆盖所有类型；靠几何/位号清理


def _remove_owned(board, pcbnew) -> tuple[int, int, int]:
    """删除本脚本上次生成的封装 / 尖端焊盘 / Edge.Cuts / 掰板孔。"""
    n_fp = n_pad = n_draw = 0

    for fp in list(board.GetFootprints()):
        if fp.GetReference() == REF or fp.GetReference().startswith("TAIL_TIP"):
            board.Remove(fp)
            n_fp += 1

    # 尖端独立焊盘：用位号前缀无法挂载，按坐标窗口清 PTH
    for fp in list(board.GetFootprints()):
        pass

    # 扫描板级焊盘不方便；尖端孔做在 TAIL_TIP_* 虚拟封装里
    for drawing in list(board.GetDrawings()):
        if drawing.GetLayer() != pcbnew.Edge_Cuts:
            continue
        bbox = drawing.GetBoundingBox()
        y0 = pcbnew.ToMM(bbox.GetY())
        y1 = y0 + pcbnew.ToMM(bbox.GetHeight())
        # 小板区域 y>98
        if y0 >= MAIN_TIP_Y + 0.2 or y1 >= MAIN_TIP_Y + 0.5:
            # 小心别删主板尖端横线 y=97.7
            if y0 > MAIN_TIP_Y + 0.15:
                board.Remove(drawing)
                n_draw += 1

    return n_fp, n_pad, n_draw


def _add_tip_castellation_footprint(pcbnew, board) -> None:
    """主板尖端 5 路 F 网邮票孔（半孔落在 Edge.Cuts 尖端）。"""
    mod_path = FP_LIB / "TailTipCastellation_5ch.kicad_mod"
    if not mod_path.exists():
        _write_tip_fp(mod_path)

    io = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    fp = io.FootprintLoad(str(FP_LIB), "TailTipCastellation_5ch")
    if fp is None:
        raise RuntimeError("无法加载 TailTipCastellation_5ch")
    fp.SetReference("TAIL_TIP")
    fp.SetValue("tip castellation")
    fp.SetPosition(xy(pcbnew, 0.0, MAIN_TIP_Y))
    for i, net_name in enumerate(FINGER_F_NETS, start=1):
        pad = fp.FindPadByNumber(str(i))
        if pad:
            pad.SetNet(_ensure_net(board, pcbnew, net_name))
    board.Add(fp)


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


def _add_stiffener_footprint(pcbnew, board) -> None:
    io = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    fp = io.FootprintLoad(str(FP_LIB), STIFF_FP_NAME)
    if fp is None:
        raise RuntimeError(f"无法加载 {STIFF_FP_NAME}")
    fp.SetReference(REF)
    fp.SetValue("F stiffener coupon")
    # footprint 本地 +Y 为 TIP；板子上 TIP 在 +Y 外边
    fp.SetPosition(xy(pcbnew, DAUGHTER_CX, DAUGHTER_CY))
    fp.SetOrientation(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))

    # 指/尖端/拍柄孔同网
    for i, net_name in enumerate(FINGER_F_NETS, start=1):
        net = _ensure_net(board, pcbnew, net_name)
        for pn in (str(i), f"T{i}", f"H{i}"):
            pad = fp.FindPadByNumber(pn)
            if pad:
                pad.SetNet(net)
    board.Add(fp)


def _add_daughter_outline_and_mousebites(pcbnew, board) -> None:
    hw = DAUGHTER_W / 2
    y0, y1 = DAUGHTER_Y_INNER, DAUGHTER_Y_OUTER
    pts = [
        (-hw, y0),
        (hw, y0),
        (hw, y1),
        (-hw, y1),
        (-hw, y0),
    ]
    polyline(pcbnew, board, pcbnew.Edge_Cuts, pts, 0.10, closed=False)

    # 主板尖端 ↔ 小板：掰板孔
    gap_y = MAIN_TIP_Y + MOUSE_GAP / 2
    for x in (-2.54, -1.27, 0.0, 1.27, 2.54):
        circle(pcbnew, board, pcbnew.Edge_Cuts, x, gap_y, MOUSE_DRILL / 2, 0.10)

    # 小板左右掰板孔（无电气）
    for y in (y0 + 2.0, y0 + 4.0, y0 + 6.0):
        circle(pcbnew, board, pcbnew.Edge_Cuts, -hw, y, MOUSE_DRILL / 2, 0.10)
        circle(pcbnew, board, pcbnew.Edge_Cuts, hw, y, MOUSE_DRILL / 2, 0.10)


# ===== 分区：公开 API =====
def main() -> None:
    parser = argparse.ArgumentParser(description="Step 4.4: Tail finger F-side stiffener coupon")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    n_fp, _, n_draw = _remove_owned(board, pcbnew)
    _write_tip_fp(FP_LIB / "TailTipCastellation_5ch.kicad_mod")
    _add_tip_castellation_footprint(pcbnew, board)
    _add_stiffener_footprint(pcbnew, board)
    _add_daughter_outline_and_mousebites(pcbnew, board)
    save_board(board, args.board)

    print("=== Step 4.4 完成 ===")
    print(f"清理: footprints={n_fp}, edge_drawings≈{n_draw}")
    print(f"主板尖端邮票孔: TAIL_TIP @ y={MAIN_TIP_Y}")
    print(f"加强小板: {REF} 中心=({DAUGHTER_CX},{DAUGHTER_CY:.2f}) "
          f"外形 {DAUGHTER_W}×{DAUGHTER_H} mm, y=[{DAUGHTER_Y_INNER:.1f},{DAUGHTER_Y_OUTER:.1f}]")
    print("装配: 掰下小板 → 金手指朝上叠到主板 F 面 → 尖端邮票孔对焊 → "
          "拍柄侧邮票孔焊在原 F 金手指上；B 面金手指仍直接接触尾插。")
    print("注意: 若重跑 step2，需再跑本脚本以恢复小板 Edge.Cuts。")


if __name__ == "__main__":
    main()
