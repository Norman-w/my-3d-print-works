#!/usr/bin/env python3
# ===== 分区：导入/依赖 =====
"""主板柄尾 MX1.25：正反各一颗 PicoBlade 53261-0571（1×5 + 侧耳）。

替换旧金手指 / 单颗 10P。不手搓封装：校本库官方 Molex 几何 + 本地 3D。
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
FP_NAME = "Molex_PicoBlade_53261-0571_1x05-1MP_P1.25mm_Horizontal"
VALUE = "MX1.25-5P"
# 拍尾 F.Fab +Y=2.6 与板尾边平齐 → 原点 Y = 89.7 − 2.6 = 87.1
PLACE_XY = (0.0, 87.1)
PLACE_ROT = 0.0

# 正面 = 原金手指 F；背面 = 原金手指 B
CONN_F = {
    "addr": "tail.conn_f",
    "ref": "TAIL_MX125_F",
    "flip": False,
    "nets": {
        "1": "sys_5v_in",
        "2": "sys_5v_sw",
        "3": "btn_sw",
        "4": "usb_dp",
        "5": "uart_tx",
    },
}
CONN_B = {
    "addr": "tail.conn_b",
    "ref": "TAIL_MX125_B",
    "flip": True,
    "nets": {
        "1": "uart_rx",
        "2": "usb_dn",
        "3": "bat_cell_p",
        "4": "led_din",
        "5": "gnd",
    },
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
    "TAIL_MX125",
    "TAIL_MX125_F",
    "TAIL_MX125_B",
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


def _add_one(board, pcbnew, spec: dict) -> None:
    fp = _load_fp(pcbnew)
    pads = list(fp.Pads())
    fp.SetReference(spec["ref"])
    fp.SetValue(VALUE)
    fp.SetFPIDAsString(f"SmartPaddle:{FP_NAME}")
    _set_addr(fp, spec["addr"])
    fp.SetPosition(
        pcbnew.VECTOR2I(
            pcbnew.FromMM(PLACE_XY[0]), pcbnew.FromMM(PLACE_XY[1])
        )
    )
    fp.SetOrientation(pcbnew.EDA_ANGLE(PLACE_ROT, pcbnew.DEGREES_T))
    for pad in pads:
        net_name = spec["nets"].get(pad.GetNumber())
        if net_name:
            pad.SetNet(_ensure_net(board, pcbnew, net_name))
    fp.SetParent(board)
    board.Add(fp)
    if spec["flip"]:
        # KiCad 9：必须先 Add 再 Flip，否则会崩
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    side = "B" if spec["flip"] else "F"
    print(f"+ added {spec['ref']} ({side}) @ {PLACE_XY} rot={PLACE_ROT}")


def _add(board_path: Path) -> None:
    import pcbnew

    board = pcbnew.LoadBoard(str(board_path))
    _add_one(board, pcbnew, CONN_F)
    _add_one(board, pcbnew, CONN_B)
    board.Save(str(board_path))


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
        print("  note: Fab 半宽≈5.7 vs 拍柄 cav_hx≈8.5 / 栈道±9.0")
        return 0

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
    print(f"✓ TAIL_MX125_F/B ready → {board_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
