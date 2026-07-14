#!/usr/bin/env python3
"""清掉已知机械/布线垃圾：叠孔、指定悬空线/过孔。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pcb.tools.kicad_update_utils import load_board, save_board

DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"

# DRC 报告里的明确悬空短线端点（mm）
DANGLING_TRACK_HINTS = [
    ("pzt_tl_signal", -15.367, -30.226),
    ("vcc", -16.002, -17.78),
    ("en", -15.951, -10.331),
]

DANGLING_VIA_HINTS = [
    ("gnd", -6.35, 88.265),
]


def _near(x: float, y: float, tx: float, ty: float, tol: float = 0.05) -> bool:
    return abs(x - tx) <= tol and abs(y - ty) <= tol


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 5: DRC cleanup (duplicate vias / dangling)")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = parser.parse_args()

    import pcbnew

    board = load_board(pcbnew, args.board)
    removed_vias = 0
    removed_tracks = 0

    # 同坐标叠孔：同网只留一个
    buckets: dict[tuple[float, float, str], list] = {}
    for item in list(board.GetTracks()):
        if item.Type() != pcbnew.PCB_VIA_T:
            continue
        p = item.GetPosition()
        key = (
            round(pcbnew.ToMM(p.x), 3),
            round(pcbnew.ToMM(p.y), 3),
            item.GetNetname(),
        )
        buckets.setdefault(key, []).append(item)

    for key, vias in buckets.items():
        if len(vias) < 2:
            continue
        for extra in vias[1:]:
            board.Remove(extra)
            removed_vias += 1
        print(f"  叠孔 {key}: 删除 {len(vias) - 1} 个重复过孔")

    # 悬空过孔
    for item in list(board.GetTracks()):
        if item.Type() != pcbnew.PCB_VIA_T:
            continue
        p = item.GetPosition()
        x, y = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
        net = item.GetNetname()
        if any(net == n and _near(x, y, vx, vy) for n, vx, vy in DANGLING_VIA_HINTS):
            board.Remove(item)
            removed_vias += 1
            print(f"  悬空过孔 {net} @({x:.3f},{y:.3f})")

    # 悬空短线：端点落在提示附近且很短
    for item in list(board.GetTracks()):
        if item.Type() == pcbnew.PCB_VIA_T:
            continue
        a, b = item.GetStart(), item.GetEnd()
        ax, ay = pcbnew.ToMM(a.x), pcbnew.ToMM(a.y)
        bx, by = pcbnew.ToMM(b.x), pcbnew.ToMM(b.y)
        length = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
        net = item.GetNetname()
        if length > 0.6:
            continue
        hit = any(
            net == n and (_near(ax, ay, hx, hy, 0.15) or _near(bx, by, hx, hy, 0.15))
            for n, hx, hy in DANGLING_TRACK_HINTS
        )
        if hit:
            board.Remove(item)
            removed_tracks += 1
            print(f"  悬空短线 {net} L={length:.3f} ({ax:.2f},{ay:.2f})-({bx:.2f},{by:.2f})")

    save_board(board, args.board)
    print(f"=== DRC cleanup 完成：过孔 -{removed_vias}，走线 -{removed_tracks} ===")


if __name__ == "__main__":
    main()
