#!/usr/bin/env python3
# ===== 分区：导入/依赖 =====
"""应用 V3 装配反馈到板（不手搓焊盘几何）。

来源：
  - parts.ato / main.ato 脚位与网络约定
  - corridor_snapshot / mainland_snapshot / dock_snapshot 放置
  - KiCad 官方库：D_SOD-323_HandSoldering、TestPoint
  - 校本 4.5×4.5 THT：SW_SPST_4.5x4.5（与尾键同规格）

动作：
  1. 二极管 → HandSoldering；BOOT/EN/PWR → 4.5×4.5 THT
  2. 缺则补 SW_PWR、TP_GND，并接到 btn_sw / gnd
  3. 从 snapshot 恢复位置/旋转（含 PZT clamp 朝向校正）
  4. 写可读 Reference

用法（KiCad python；每次进程只做一步突变，exit 2=需重跑，0=完成）：
  KIPY=.../KiCad.app/.../python3
  until $KIPY pcb/scripts/apply_bringup_refs.py; do [ $? -eq 2 ] || exit $?; done
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ===== 分区：常量/配置 =====

ROOT = Path(__file__).resolve().parents[2]
LOCAL_PRETTY = ROOT / "pcb" / "layouts" / "lib" / "footprints.pretty"
CORRIDOR_SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "corridor_snapshot.json"
MAINLAND_SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "mainland_snapshot.json"
DOCK_SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "dock_snapshot.json"

READABLE = {
    "debug_sw.sw_boot": ("SW_BOOT", "4.5x4.5"),
    "debug_sw.sw_en": ("SW_EN", "4.5x4.5"),
    "debug_sw.sw_pwr": ("SW_PWR", "4.5x4.5"),
    "bringup.vcc_pad": ("TP_3V3", "3V3"),
    "bringup.sys5_pad": ("TP_SYS_5V_SW", "sys_5v_sw"),
    "bringup.gnd_pad": ("TP_GND", "GND"),
}

# 校本库：HandSoldering 二极管 + 4.5×4.5 THT 轻触
FP_EXCHANGE = {
    "power.d_btn_start": "D_SOD-323_HandSoldering",
    "debug_sw.sw_boot": "SW_SPST_4.5x4.5",
    "debug_sw.sw_en": "SW_SPST_4.5x4.5",
    "debug_sw.sw_pwr": "SW_SPST_4.5x4.5",
}

# ===== 分区：私有成员 =====


def _load_snap(path: Path) -> dict:
    if not path.is_file():
        return {}
    return {e["addr"]: e for e in json.loads(path.read_text(encoding="utf-8"))}


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


def _pad_nets_snapshot(fp) -> dict[str, object]:
    by_num: dict[str, object] = {}
    for pad in list(fp.Pads()):
        by_num.setdefault(pad.GetNumber(), pad.GetNet())
    return by_num


def _apply_pad_nets(fp, by_num: dict[str, object]) -> None:
    for pad in list(fp.Pads()):
        net = by_num.get(pad.GetNumber())
        if net is not None:
            pad.SetNet(net)


def _load_one_fp(pcbnew, fp_name: str):
    """单次加载。PCB_IO 在 Save/Reload 后可能坏掉，调用方应在新进程里用。"""
    io = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    if not hasattr(io, "FootprintLoad"):
        raise RuntimeError("PCB_IO plugin invalid; rerun in a fresh KiCad python process")
    fp = io.FootprintLoad(str(LOCAL_PRETTY), fp_name)
    if fp is None:
        raise RuntimeError(f"FootprintLoad failed: {LOCAL_PRETTY} / {fp_name}")
    return fp


def _replace_footprint(board, pcbnew, old_fp, fp_name: str):
    # 先快照再动板，避免 Remove 后旧 FOOTPRINT 句柄失效
    pos = old_fp.GetPosition()
    orient = old_fp.GetOrientation()
    ref = old_fp.GetReference()
    value = old_fp.GetValue()
    layer = old_fp.GetLayer()
    addr = _addr(old_fp)
    nets = _pad_nets_snapshot(old_fp)

    new_fp = _load_one_fp(pcbnew, fp_name)
    new_fp.SetParent(board)
    new_fp.SetPosition(pos)
    new_fp.SetOrientation(orient)
    new_fp.SetReference(ref)
    new_fp.SetValue(value)
    new_fp.SetLayer(layer)
    new_fp.SetFPIDAsString(f"SmartPaddle:{fp_name}")
    if addr:
        _set_addr(new_fp, addr)
    _apply_pad_nets(new_fp, nets)
    board.Add(new_fp)
    board.Remove(old_fp)
    return new_fp


def _add_footprint(
    board,
    pcbnew,
    fp_name: str,
    *,
    addr: str,
    ref: str,
    value: str,
    x: float,
    y: float,
    rot: float,
    pad_nets: dict[str, str],
):
    fp = _load_one_fp(pcbnew, fp_name)
    fp.SetParent(board)
    fp.SetPosition(
        pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
    )
    fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetFPIDAsString(f"SmartPaddle:{fp_name}")
    _set_addr(fp, addr)
    for pad in fp.Pads():
        net_name = pad_nets.get(pad.GetNumber())
        if net_name:
            pad.SetNet(_ensure_net(board, pcbnew, net_name))
    board.Add(fp)
    return fp


# ===== 分区：公开 API =====


def _live_by_addr(board) -> dict:
    out = {}
    for fp in board.GetFootprints():
        a = _addr(fp)
        if a:
            out[a] = fp
    return out


def _open(pcbnew, board_path: Path):
    board = pcbnew.LoadBoard(str(board_path))
    if board is None:
        raise RuntimeError(f"LoadBoard failed: {board_path}")
    return board


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--board",
        type=Path,
        default=ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb",
    )
    args = ap.parse_args()
    board_path = args.board.resolve()

    import pcbnew

    snap = {}
    snap.update(_load_snap(MAINLAND_SNAPSHOT))
    snap.update(_load_snap(DOCK_SNAPSHOT))
    snap.update(_load_snap(CORRIDOR_SNAPSHOT))

    # KiCad 9：Save/Reload 后 PCB_IO 句柄会坏 → 每次只做一步突变，exit 2 让外层重跑
    board = _open(pcbnew, board_path)
    by_addr = _live_by_addr(board)

    if "debug_sw.sw_pwr" not in by_addr:
        e = snap.get("debug_sw.sw_pwr", {"x": 4.87, "y": 66.294, "rot": 90.0})
        _add_footprint(
            board,
            pcbnew,
            "SW_SPST_4.5x4.5",
            addr="debug_sw.sw_pwr",
            ref="SW_PWR",
            value="4.5x4.5",
            x=float(e["x"]),
            y=float(e["y"]),
            rot=float(e.get("rot", 0)),
            pad_nets={"1": "btn_sw", "2": "gnd"},
        )
        board.Save(str(board_path))
        print("+ added SW_PWR (btn_sw↔gnd); rerun")
        return 2

    if "bringup.gnd_pad" not in by_addr:
        e = snap.get("bringup.gnd_pad", {"x": 19.05, "y": -19.558, "rot": 0.0})
        _add_footprint(
            board,
            pcbnew,
            "TestPoint_THTPad_D2.0mm_Drill1.0mm",
            addr="bringup.gnd_pad",
            ref="TP_GND",
            value="GND",
            x=float(e["x"]),
            y=float(e["y"]),
            rot=float(e.get("rot", 0)),
            pad_nets={"1": "gnd"},
        )
        board.Save(str(board_path))
        print("+ added TP_GND; rerun")
        return 2

    for addr, fp_name in FP_EXCHANGE.items():
        fp = by_addr.get(addr)
        if fp is None:
            continue
        cur = fp.GetFPIDAsString()
        if fp_name in cur or cur.endswith(fp_name):
            continue
        _replace_footprint(board, pcbnew, fp, fp_name)
        board.Save(str(board_path))
        print(f"↔ {addr}: {cur} → {fp_name}; rerun")
        return 2

    moved = 0
    for addr, e in snap.items():
        fp = by_addr.get(addr)
        if fp is None:
            continue
        fp.SetPosition(
            pcbnew.VECTOR2I(
                pcbnew.FromMM(float(e["x"])), pcbnew.FromMM(float(e["y"]))
            )
        )
        fp.SetOrientation(
            pcbnew.EDA_ANGLE(float(e.get("rot", 0)), pcbnew.DEGREES_T)
        )
        moved += 1

    for addr, (ref, val) in READABLE.items():
        fp = by_addr.get(addr)
        if fp is None:
            continue
        fp.SetReference(ref)
        fp.SetValue(val)

    sw = by_addr.get("debug_sw.sw_pwr")
    if sw is not None:
        for pad in list(sw.Pads()):
            if pad.GetNumber() == "1":
                pad.SetNet(_ensure_net(board, pcbnew, "btn_sw"))
            elif pad.GetNumber() == "2":
                pad.SetNet(_ensure_net(board, pcbnew, "gnd"))

    board.Save(str(board_path))
    print(f"✓ applied V3 fab feedback → {board_path} (moved {moved})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
