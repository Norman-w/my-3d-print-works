#!/usr/bin/env python3
# ===== 分区：导入/依赖 =====
"""用 MX1.25 / PicoBlade 53261-1071 替换尾插金手指（及加强垫片）。

不手搓封装：从 SmartPaddle 校本库加载官方 Molex 几何 + 本地 3D。
KiCad 9：Remove/Save 后 PCB_IO 会坏 → 清板与加件分两进程。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# ===== 分区：常量/配置 =====

ROOT = Path(__file__).resolve().parents[2]
LOCAL_PRETTY = ROOT / "pcb" / "layouts" / "lib" / "footprints.pretty"
FP_NAME = "Molex_PicoBlade_53261-1071_1x10-1MP_P1.25mm_Horizontal"
ADDR = "tail.conn"
REF = "TAIL_MX125"
VALUE = "MX1.25-10P"
# 居中；拍尾端面（F.Fab +Y=2.6）与板尾边平齐。
# 板尾 ≈ SUBSTRATE_TAIL_MAX_Y(90) − 内缩 0.3 → 89.7；原点 Y = 89.7 − 2.6 = 87.1
PLACE_XY = (0.0, 87.1)
PLACE_ROT = 0.0

PAD_NETS = {
    "1": "sys_5v_in",
    "2": "gnd",
    "3": "sys_5v_sw",
    "4": "led_din",
    "5": "btn_sw",
    "6": "bat_cell_p",
    "7": "usb_dp",
    "8": "usb_dn",
    "9": "uart_tx",
    "10": "uart_rx",
}

REMOVE_REFS = {
    "TAIL_PWR",
    "TAIL_LED",
    "TAIL_CTL",
    "TAIL_USB",
    "TAIL_UART",
    "TAIL_TIP",
    "TAIL_STIFF_L",
    "TAIL_STIFF_R",
    "TAIL_MB_L",
    "TAIL_MB_R",
    REF,
}

# ===== 分区：私有成员 =====


def _addr(fp) -> str | None:
    try:
        if fp.HasFieldByName("atopile_address"):
            return fp.GetFieldByName("atopile_address").GetText()
    except Exception:
        pass
    try:
        return fp.GetProperty("atopile_address")
    except Exception:
        return None


def _set_addr(fp, addr: str) -> None:
    if fp.HasFieldByName("atopile_address"):
        fp.GetFieldByName("atopile_address").SetText(addr)
        return
    fp.SetField("atopile_address", addr)


def _ensure_net(board, pcbnew, name: str):
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def _load_fp(pcbnew):
    io = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    if not hasattr(io, "FootprintLoad"):
        raise RuntimeError("PCB_IO invalid; need fresh KiCad python process")
    fp = io.FootprintLoad(str(LOCAL_PRETTY), FP_NAME)
    if fp is None:
        raise RuntimeError(f"FootprintLoad failed: {LOCAL_PRETTY} / {FP_NAME}")
    return fp


def _clear(board_path: Path) -> int:
    import pcbnew

    board = pcbnew.LoadBoard(str(board_path))
    removed = 0
    for old in list(board.GetFootprints()):
        addr = _addr(old) or ""
        if old.GetReference() in REMOVE_REFS or addr.startswith("tail."):
            board.Remove(old)
            removed += 1
    board.Save(str(board_path))
    print(f"- cleared {removed} old tail parts")
    return removed


def _add(board_path: Path) -> None:
    import pcbnew

    board = pcbnew.LoadBoard(str(board_path))
    fp = _load_fp(pcbnew)
    pads = list(fp.Pads())
    fp.SetReference(REF)
    fp.SetValue(VALUE)
    fp.SetFPIDAsString(f"SmartPaddle:{FP_NAME}")
    _set_addr(fp, ADDR)
    fp.SetPosition(
        pcbnew.VECTOR2I(
            pcbnew.FromMM(PLACE_XY[0]), pcbnew.FromMM(PLACE_XY[1])
        )
    )
    fp.SetOrientation(pcbnew.EDA_ANGLE(PLACE_ROT, pcbnew.DEGREES_T))
    for pad in pads:
        net_name = PAD_NETS.get(pad.GetNumber())
        if net_name:
            pad.SetNet(_ensure_net(board, pcbnew, net_name))
    fp.SetParent(board)
    board.Add(fp)
    board.Save(str(board_path))
    print(f"+ added {REF} @ {PLACE_XY} rot={PLACE_ROT}")


# ===== 分区：公开 API =====


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--board",
        type=Path,
        default=ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb",
    )
    parser.add_argument(
        "--phase",
        choices=("all", "clear", "add"),
        default="all",
    )
    args = parser.parse_args()
    board_path = args.board.resolve()

    try:
        import pcbnew  # noqa: F401
    except ImportError:
        print("need KiCad pcbnew python", file=sys.stderr)
        return 1

    if args.phase == "clear":
        _clear(board_path)
        return 0
    if args.phase == "add":
        _add(board_path)
        print("  note: 拍尾 F.Fab 与板尾边齐平；courtyard 侧耳≈±9.7 vs 栈道±8.7")
        return 0

    # all: clear in this process, add in a fresh subprocess
    _clear(board_path)
    env = os.environ.copy()
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--board",
        str(board_path),
        "--phase",
        "add",
    ]
    rc = subprocess.call(cmd, env=env)
    if rc != 0:
        return rc
    print(f"✓ TAIL_MX125 ready → {board_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
