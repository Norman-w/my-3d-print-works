#!/usr/bin/env python3
"""Step 4.5 — 布线预备：尾插 + IMU 拥挤区 fanout stub + via。

在布线之前，为尾插金手指和 IMU 拥挤区的每个焊盘生成 fanout stub
（短走线 + 过孔），将信号从狭窄区域引出到大陆宽敞布线区。

此步骤不执行路由搜索，仅放置帮助布线器的 stub 结构。
"""
# ===== 分区：导入/依赖 =====
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pcbnew
from rigid_pcb.tools.kicad_update_utils import load_board, save_board

# ===== 分区：常量/配置 =====
BOARD_FILE = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"
STUB_WIDTH = 0.15  # mm

# 尾插 fanout via（每个 pad 独立 via，F/B 面不同网）
# 螺丝孔 (0,79) r=3.5 → keepout Y≥75.5，via@Y=74 安全
# stub 路径: pad(Y≈96) → (pad_x, 83) → (via_x, 83) → (via_x, via_y)
TAIL_FANOUT = {
    ('tail.pos1', 'F'): (-5.5, 74.0),
    ('tail.pos1', 'B'): (-4.5, 74.0),
    ('tail.pos2', 'F'): (-3.5, 74.0),
    ('tail.pos2', 'B'): (-2.5, 74.0),
    ('tail.pos3', 'F'): ( 3.5, 74.0),
    ('tail.pos3', 'B'): ( 2.5, 74.0),
    ('tail.pos4', 'F'): ( 5.5, 74.0),
    ('tail.pos4', 'B'): ( 4.5, 74.0),
    ('tail.pos5', 'F'): ( 7.5, 74.0),
    ('tail.pos5', 'B'): ( 6.5, 74.0),
}

# IMU 拥挤区 fanout（cutout center (0,-21.5), 18.9×13.4）
# 每个 pad 从 cutout 内部 fan 到边界外 1mm + via
IMU_FANOUT = [
    ('imu', '1',  (-7.0, -32.0)),
    ('imu', '2',  (-4.0, -32.0)),
    ('imu', '3',  ( 4.0, -32.0)),
    ('imu', '4',  ( 7.0, -32.0)),
    ('imu', '5',  ( 12.0, -27.0)),
    ('imu', '6',  ( 12.0, -25.0)),
    ('imu', '7',  ( 12.0, -23.0)),
    ('imu', '8',  ( 12.0, -21.0)),
    ('imu', '9',  ( 7.0, -11.0)),
    ('imu', '10', ( 4.0, -11.0)),
    ('imu', '11', (-4.0, -11.0)),
    ('imu', '12', (-7.0, -11.0)),
    ('imu', '13', (-12.0, -21.0)),
    ('imu', '14', (-12.0, -23.0)),
    ('imu', '15', (-12.0, -25.0)),
    ('imu', '16', (-12.0, -27.0)),
]

# ===== 分区：私有成员 =====

def _address(fp):
    if not fp.HasFieldByName('atopile_address'):
        return None
    return fp.GetFieldByName('atopile_address').GetText()


def _add_tail_fanout(board):
    """为尾插每个焊盘生成 fanout stub + via（F/B 独立 via）。"""
    t_add = v_add = 0
    for fp in board.GetFootprints():
        addr = _address(fp)
        for pad in fp.Pads():
            pn = pad.GetNumber()
            key = (addr, pn)
            if key not in TAIL_FANOUT:
                continue
            net = pad.GetNet()
            if not str(net.GetNetname()):
                continue
            via_x, via_y = TAIL_FANOUT[key]
            pos = pad.GetPosition()
            pad_x, pad_y = pos.x / 1e6, pos.y / 1e6
            tl = pcbnew.B_Cu if pad.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu
            for (x1, y1), (x2, y2) in [
                ((pad_x, pad_y), (pad_x, 83.0)),
                ((pad_x, 83.0), (via_x, 83.0)),
                ((via_x, 83.0), (via_x, via_y)),
            ]:
                if abs(x1 - x2) < 0.001 and abs(y1 - y2) < 0.001:
                    continue
                track = pcbnew.PCB_TRACK(board)
                track.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
                track.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
                track.SetLayer(tl)
                track.SetWidth(int(STUB_WIDTH * 1e6))
                track.SetNet(net)
                board.Add(track)
                t_add += 1
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(int(via_x * 1e6), int(via_y * 1e6)))
            via.SetNet(net)
            via.SetWidth(int(0.5 * 1e6))
            via.SetDrill(int(0.3 * 1e6))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(via)
            v_add += 1
    return t_add, v_add


def _add_imu_fanout(board):
    """为 IMU 拥挤区每个焊盘生成 fanout stub + via。"""
    t_add = v_add = 0
    for fp in board.GetFootprints():
        if _address(fp) != 'imu':
            continue
        for pad in fp.Pads():
            pn = pad.GetNumber()
            net = pad.GetNet()
            if not str(net.GetNetname()):
                continue
            via_target = None
            for _ia, ip, iv in IMU_FANOUT:
                if ip == pn:
                    via_target = iv
                    break
            if via_target is None:
                continue
            via_x, via_y = via_target
            pos = pad.GetPosition()
            pad_x, pad_y = pos.x / 1e6, pos.y / 1e6
            tl = pcbnew.B_Cu if pad.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(pcbnew.VECTOR2I(int(pad_x * 1e6), int(pad_y * 1e6)))
            track.SetEnd(pcbnew.VECTOR2I(int(via_x * 1e6), int(via_y * 1e6)))
            track.SetLayer(tl)
            track.SetWidth(int(STUB_WIDTH * 1e6))
            track.SetNet(net)
            board.Add(track)
            t_add += 1
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(int(via_x * 1e6), int(via_y * 1e6)))
            via.SetNet(net)
            via.SetWidth(int(0.5 * 1e6))
            via.SetDrill(int(0.3 * 1e6))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(via)
            v_add += 1
    return t_add, v_add


# ===== 分区：公开 API =====

def main():
    board = load_board(pcbnew, BOARD_FILE)

    tail_t, tail_v = _add_tail_fanout(board)
    imu_t, imu_v = _add_imu_fanout(board)
    fanout_t = tail_t + imu_t
    fanout_v = tail_v + imu_v

    save_board(board, BOARD_FILE)

    print(f'4.5a. 尾插 fanout: 放置了 {tail_v} 个过孔 + {tail_t} 段 stub track')
    print(f'4.5b. IMU  fanout: 放置了 {imu_v} 个过孔 + {imu_t} 段 stub track')
    print(f'4.5.  总共: {fanout_v} 个过孔 + {fanout_t} 段 stub track')


if __name__ == '__main__':
    main()
