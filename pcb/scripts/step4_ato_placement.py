#!/usr/bin/env python3
"""Step 4 — atopile 组件放置 + Reference + 3D 修正 + 尾插网表分配。

将 ato 生成的封装放入机械定位点，分配可读 Reference，修正 3D 模型缩放，
显式分配 MX1.25 尾插座焊盘网络。不产生任何走线或过孔（fanout 由 step4.5 独立处理）。
"""
# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml

import pcbnew
from pcb.tools.kicad_update_utils import load_board, save_board, xy
from pcb.tools.mech_geometry import (
    ESP32_CUTOUT,
    IMU_CUTOUT,
    SUBSTRATE_EDGE_CLEARANCE,
    SUBSTRATE_TAIL_MAX_Y,
)

# ===== 分区：常量/配置 =====
BOARD_FILE = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
PARAMS_FILE = ROOT / "shared" / "board_params.yaml"
DOCK_SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "dock_snapshot.json"
MAINLAND_SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "mainland_snapshot.json"
CORRIDOR_SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "corridor_snapshot.json"
TAIL_SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "tail_snapshot.json"

KEEPOUT = 1.5
COL_SPACING_Y = 3.5
COL_MARGIN = 1.0
TEXT_THICKNESS = 0.10

# 可读 Reference 映射（atopile_address → (Reference, Value)）
READABLE_REFS = {
    'mcu': ('MCU_SGFK_C6', 'SGFK ESP32-C6-N8'),
    'imu': ('IMU_IM948', 'IM948'),
    'power.q_power': ('PW_Q_LOAD', 'P-MOS load switch'),
    'power.q_latch': ('PW_Q_LATCH', 'N-MOS latch'),
    'power.r_gate': ('PW_R_GATE_100K', '100k'),
    'power.r_button_series': ('PW_R_BTN_SER_1K', '1k'),
    'power.r_latch_pd': ('PW_R_LATCH_PD_100K', '100k'),
    'power.r_en_pullup': ('PW_R_EN_PU_10K', '10k'),
    'power.d_btn_start': ('D_BTN_START', '1N4148W'),
    'power.ldo': ('PW_LDO_3V3', 'AP2112K-3.3'),
    'power.c_in': ('PW_C_IN_10U', '10uF'),
    'power.c_out': ('PW_C_OUT_10U', '10uF'),
    'battery.r_top': ('BAT_R_TOP_1M', '1M'),
    'battery.r_bottom': ('BAT_R_BOT_1M', '1M'),
    'battery.c_filter': ('BAT_C_ADC_100N', '100nF'),
    'led_r_data': ('LED_R_DATA_330R', '330R'),
    'led_c_supply': ('LED_C_SUP_100N', '100nF'),
    'pwr_led.led': ('LED_MCU_PWR', '0603 power'),
    'pwr_led.r_lim': ('R_MCU_PWR_1K', '1k'),
    'debug_sw.sw_boot': ('SW_BOOT', '4.5x4.5'),
    'debug_sw.sw_en': ('SW_EN', '4.5x4.5'),
    'debug_sw.sw_pwr': ('SW_PWR', '4.5x4.5'),
    'tail.conn_f': ('TAIL_MX125_F', 'MX1.25-5P'),
    'tail.conn_b': ('TAIL_MX125_B', 'MX1.25-5P'),
    'bringup.vcc_pad': ('TP_3V3', '3V3'),
    'bringup.sys5_pad': ('TP_SYS_5V_SW', 'SYS_5V_SW'),
    'bringup.gnd_pad': ('TP_GND', 'GND'),
}

MODEL_SCALES = {'mcu': 0.3937008, 'imu': 0.3937008}

PZT_PREFIX = {'pzt_tr': 'PZT_TR', 'pzt_tl': 'PZT_TL', 'pzt_br': 'PZT_BR', 'pzt_bl': 'PZT_BL'}
PZT_PARTS = {
    'series_resistor': ('R_SER_4K7', '4.7k'),
    'bleed_resistor': ('R_DIS_1M', '1M'),
    'clamp_diode': ('D_CLAMP', 'BAT54S'),
    'pzt_signal_pad': ('SIG', 'PZT signal wire'),
    'pzt_gnd_pad': ('GND', 'PZT GND wire'),
}

TAIL_NET_MAP = {
    # MX1.25 / PicoBlade 53261-0571 ×2（F/B）— 见 docs/1.25x10p/README.md
    'tail.conn_f': {
        '1': 'sys_5v_in',
        '2': 'sys_5v_sw',
        '3': 'btn_sw',
        '4': 'usb_dp',
        '5': 'uart_tx',
    },
    'tail.conn_b': {
        '1': 'gnd',
        '2': 'led_din',
        '3': 'bat_cell_p',
        '4': 'usb_dn',
        '5': 'uart_rx',
    },
}


# ===== 分区：私有成员 — 辅助函数 =====

def _address(fp):
    if not fp.HasFieldByName('atopile_address'):
        return None
    return fp.GetFieldByName('atopile_address').GetText()


def _safe_id(text):
    return re.sub(r'[^A-Za-z0-9_+.-]+', '_', text.strip()) or 'Generated'


def _infer_attr(fp):
    for pad in fp.Pads():
        if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            return pcbnew.FP_THROUGH_HOLE
    return pcbnew.FP_SMD


def _readable_ref(addr):
    if addr in READABLE_REFS:
        return READABLE_REFS[addr]
    for pzt_addr, prefix in PZT_PREFIX.items():
        stem = pzt_addr + '.'
        if addr.startswith(stem):
            part = addr[len(stem):]
            if part in PZT_PARTS:
                suffix, value = PZT_PARTS[part]
                return f'{prefix}_{suffix}', value
    return None


def _set_text_size(field, size_mm):
    field.SetTextHeight(pcbnew.FromMM(size_mm))
    field.SetTextWidth(pcbnew.FromMM(size_mm))
    field.SetTextThickness(pcbnew.FromMM(TEXT_THICKNESS))


def _set_text_at(field, x, y, angle_deg=0):
    field.SetPosition(xy(pcbnew, x, y))
    field.SetTextAngleDegrees(angle_deg)


def _label_spec(addr, fp):
    pos = fp.GetPosition()
    x, y = pos.x / 1_000_000, pos.y / 1_000_000
    if addr == 'mcu':
        return 0.60, (x, y - ESP32_CUTOUT[3] / 2 - 1.4), 0
    if addr == 'imu':
        return 0.60, (x, y - IMU_CUTOUT[3] / 2 - 1.2), 0
    if addr.startswith('tail.'):
        return 0.38, (x, y + 1.4), 0
    if addr.startswith('pzt_'):
        return 0.38, (x, y + 1.2), fp.GetOrientationDegrees()
    # BOOT/EN 键：丝印放在键体上方/下方，避免叠在焊盘上
    if addr == 'debug_sw.sw_boot':
        return 0.70, (x, y - 3.9), 0
    if addr == 'debug_sw.sw_en':
        return 0.70, (x, y + 3.9), 0
    # 测试点：短丝印靠左，避免与键体重叠
    if addr.startswith('bringup.'):
        return 0.70, (x - 3.6, y), 0
    return 0.38, (x, y), 0


def _should_show_reference(addr):
    return (
        addr in {'mcu', 'imu'}
        or addr.startswith('tail.')
        or addr.startswith('bringup.')
        or addr.startswith('debug_sw.')
        or addr.endswith('.pzt_signal_pad')
        or addr.endswith('.pzt_gnd_pad')
    )


def _apply_readable_text(board):
    used, changed, visible = set(), 0, 0
    for fp in board.GetFootprints():
        addr = _address(fp)
        if not addr:
            continue
        alias = _readable_ref(addr)
        if not alias:
            continue
        ref, value = alias
        if ref in used:
            raise RuntimeError(f'duplicate ref: {ref}')
        used.add(ref)
        fp.SetReference(ref)
        fp.SetValue(value)
        size, (tx, ty), angle = _label_spec(addr, fp)
        ref_field, value_field = fp.Reference(), fp.Value()
        show_ref = _should_show_reference(addr)
        ref_field.SetVisible(show_ref)
        value_field.SetVisible(False)
        ref_field.SetLayer(pcbnew.F_SilkS)
        value_field.SetLayer(pcbnew.F_Fab)
        _set_text_size(ref_field, size)
        _set_text_size(value_field, 0.45)
        _set_text_at(ref_field, tx, ty, angle)
        changed += 1
        visible += 1 if show_ref else 0
    return changed, visible


def _apply_model_scales(board):
    changed = 0
    for fp in board.GetFootprints():
        addr = _address(fp)
        if addr not in MODEL_SCALES:
            continue
        models = fp.Models()
        fixed = []
        for model in models:
            s = MODEL_SCALES[addr]
            model.m_Scale.Set(s, s, s)
            fixed.append(model)
        models.clear()
        for model in fixed:
            models.append(model)
            changed += 1
    return changed


def _is_initial_grid(fp):
    pos = fp.GetPosition()
    x, y = pos.x / 1_000_000, pos.y / 1_000_000
    return math.isclose(x / 10, round(x / 10), abs_tol=1e-3) and math.isclose(y / 10, round(y / 10), abs_tol=1e-3)


def _snapshot_map(path: Path) -> dict[str, tuple[float, float, float]] | None:
    if not path.is_file():
        return None
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(entry["addr"]): (float(entry["x"]), float(entry["y"]), float(entry["rot"]))
        for entry in entries
    }


def _move_one(fp_by_addr, addr, x, y, rot, force, *, keep_flip: bool = False):
    fp = fp_by_addr.get(addr)
    if fp is None:
        return 0
    if not force and not _is_initial_grid(fp):
        return 0
    was_flipped = bool(fp.IsFlipped()) if hasattr(fp, 'IsFlipped') else False
    fp.SetPosition(xy(pcbnew, x, y))
    fp.SetOrientationDegrees(rot)
    if keep_flip or was_flipped:
        if hasattr(fp, 'IsFlipped') and not fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    return 1


def _place_map(fp_by_addr, placements, force):
    moved = 0
    for addr, (x, y, rot) in placements.items():
        moved += _move_one(fp_by_addr, addr, x, y, rot, force)
    return moved


# ===== 分区：私有成员 — 网表分配 =====

def _assign_tail_nets(board):
    """显式分配尾插焊盘网络（netlist 命名不一致的补偿）。"""
    assigned = 0
    for fp in board.GetFootprints():
        addr = _address(fp)
        if addr not in TAIL_NET_MAP:
            continue
        for pad in fp.Pads():
            pn = pad.GetNumber()
            if pn not in TAIL_NET_MAP[addr]:
                continue
            net_name = TAIL_NET_MAP[addr][pn]
            net = board.FindNet(net_name)
            if net is None:
                net = pcbnew.NETINFO_ITEM(board, net_name)
                board.Add(net)
            pad.SetNet(net)
            assigned += 1
    return assigned


# ===== 分区：公开 API =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Step 4: atopile placement")
    parser.add_argument("--force", action="store_true",
                        help="强制移动所有映射封装（含已手调位置）")
    args = parser.parse_args()
    force = args.force

    board = load_board(pcbnew, BOARD_FILE)

    # 4a. 规范化
    changed = 0
    for fp in board.GetFootprints():
        ref = fp.GetReference() or 'Generated'
        if not fp.GetFPIDAsString():
            fp.SetFPIDAsString(f'SmartPaddle:{_safe_id(ref)}')
            changed += 1
        if fp.GetAttributes() == 0:
            fp.SetAttributes(_infer_attr(fp))
            changed += 1
    print(f'4a. 规范化: 修正了 {changed} 个封装的元数据字段')

    params = yaml.safe_load(PARAMS_FILE.read_text())
    fp_by_addr = {addr: fp for fp in board.GetFootprints() if (addr := _address(fp))}
    if not fp_by_addr:
        print('4b. 警告: 未找到带 atopile_address 属性的封装')
        save_board(board, BOARD_FILE)
        sys.exit(0)

    moved = 0

    mainland_snap = _snapshot_map(MAINLAND_SNAPSHOT)
    if mainland_snap:
        moved += _place_map(fp_by_addr, mainland_snap, True)
        print(f'4b. 大陆: 从 mainland_snapshot 恢复 {len(mainland_snap)} 个')
    else:
        moved += _move_one(fp_by_addr, 'mcu', ESP32_CUTOUT[0], ESP32_CUTOUT[1], 0, force)
        moved += _move_one(fp_by_addr, 'imu', IMU_CUTOUT[0], IMU_CUTOUT[1], 0, force)

        power_x_a, power_x_b = 15.0, 19.2
        power_y = [-7.2, -2.8, 1.6, 6.0]
        power_zone = {
            'power.q_power': (power_x_a, power_y[0], 90),
            'power.q_latch': (power_x_a, power_y[1], 90),
            'power.r_gate': (power_x_b, power_y[1], 0),
            'power.r_latch_pd': (power_x_a, power_y[2], 0),
            'power.r_button_series': (power_x_b, power_y[2], 90),
            'power.r_en_pullup': (power_x_b, power_y[3], 90),
            'power.d_btn_start': (power_x_b, power_y[0], 0),
        }
        moved += _place_map(fp_by_addr, power_zone, force)

        regulator_zone = {
            'power.ldo': (14.0, -20.6, 90),
            # 远离 TP_GND (19.05,-19.558)，避免与 PW_C_IN_10U 过近
            'power.c_in': (18.402, -22.606, 0),
            'power.c_out': (18.3, -16.5, 0),
        }
        moved += _place_map(fp_by_addr, regulator_zone, force)

        sense_led_zone = {
            'battery.r_top': (-18.0, -20.6, 0),
            'battery.r_bottom': (-13.8, -20.6, 0),
            'battery.c_filter': (-18.0, -16.5, 0),
            'led_c_supply': (-13.8, -16.5, 0),
            'led_r_data': (-16.0, -12.4, 90),
            'pwr_led.led': (-17.0, 10.0, 0),
            'pwr_led.r_lim': (-16.0, 10.5, 90),
        }
        moved += _place_map(fp_by_addr, sense_led_zone, force)

    # 大陆快照缺失时，把两颗 bringup TP 放在电源区（与现行手布一致）
    if not mainland_snap:
        bringup_zone = {
            'bringup.vcc_pad': (19.05, -13.335, 0),
            'bringup.sys5_pad': (19.05, -25.781, 0),
        }
        moved += _place_map(fp_by_addr, bringup_zone, True)

    corridor_snap = _snapshot_map(CORRIDOR_SNAPSHOT)
    if corridor_snap:
        moved += _place_map(fp_by_addr, corridor_snap, True)
        print(f'4b. 宽栈道: 从 corridor_snapshot 恢复 {len(corridor_snap)} 个')
    else:
        # 宽栈道仅 BOOT/EN 轻触
        debug_zone = {
            # 4.5×4.5 THT（与尾键同规格）；宽栈道手布位
            'debug_sw.sw_boot': (4.87, 49.706, 90),
            'debug_sw.sw_en': (4.87, 57.995, 90),
            'debug_sw.sw_pwr': (4.87, 66.294, 90),
        }
        moved += _place_map(fp_by_addr, debug_zone, True)

    # PZT 前端：用 dock_snapshot 坐标（码头岛内），勿用 piezo 中心（在板外）
    if DOCK_SNAPSHOT.is_file():
        dock_entries = json.loads(DOCK_SNAPSHOT.read_text())
        pzt_on_docks = {
            entry['addr']: (float(entry['x']), float(entry['y']), float(entry['rot']))
            for entry in dock_entries
            if str(entry.get('addr', '')).startswith('pzt_')
        }
        moved += _place_map(fp_by_addr, pzt_on_docks, True)
    else:
        raise FileNotFoundError(f'missing dock snapshot: {DOCK_SNAPSHOT}')

    # 尾插 MX1.25 正反 5P：优先 tail_snapshot（含 flip），否则齐边默认位
    if TAIL_SNAPSHOT.is_file():
        tail_entries = json.loads(TAIL_SNAPSHOT.read_text(encoding="utf-8"))
        for entry in tail_entries:
            addr = entry["addr"]
            fp = fp_by_addr.get(addr)
            if fp is None:
                continue
            fp.SetPosition(xy(pcbnew, float(entry["x"]), float(entry["y"])))
            fp.SetOrientationDegrees(float(entry["rot"]))
            want_flip = bool(entry.get("flip"))
            if hasattr(fp, "IsFlipped"):
                if want_flip and not fp.IsFlipped():
                    fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
                elif (not want_flip) and fp.IsFlipped():
                    fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            moved += 1
        print(f'4b. 尾插: 从 tail_snapshot 恢复 {len(tail_entries)} 个')
    else:
        tail_y = SUBSTRATE_TAIL_MAX_Y - SUBSTRATE_EDGE_CLEARANCE - 2.6
        moved += _move_one(fp_by_addr, 'tail.conn_f', 0.0, tail_y, 0.0, force)
        moved += _move_one(
            fp_by_addr, 'tail.conn_b', 0.0, tail_y, 0.0, force, keep_flip=True
        )

    # 4e. 尾插网络
    tail_net_assigned = _assign_tail_nets(board)

    # 4c/4d. 标签与 3D
    labelled, visible_labels = _apply_readable_text(board)
    scaled = _apply_model_scales(board)

    save_board(board, BOARD_FILE)

    print(f'4b. 放置: 移动了 {moved} 个 atopile 封装到机械定位点')
    print(f'4c. 文本: 应用了 {labelled} 个可读Reference, 显示 {visible_labels} 个关键标签')
    print(f'4d. 3D: 应用了 {scaled} 个模块模型缩放修正')
    print(f'4e. 尾插网络: 分配了 {tail_net_assigned} 个焊盘')
    print(f'    总共 {len(fp_by_addr)} 个带 atopile_address 的封装')
    print(f'    ⚠ 无走线/过孔 — 纯放置步骤')


if __name__ == '__main__':
    main()
