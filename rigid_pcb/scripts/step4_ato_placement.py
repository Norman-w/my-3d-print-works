#!/usr/bin/env python3
"""Step 4 — atopile 组件放置 + Reference + 3D 修正 + 尾插网表分配。

将 ato 生成的封装放入机械定位点，分配可读 Reference，修正 3D 模型缩放，
显式分配金手指焊盘网络。不产生任何走线或过孔（fanout 由 step4.5 独立处理）。
"""
# ===== 分区：导入/依赖 =====
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml

import pcbnew
from rigid_pcb.tools.kicad_update_utils import load_board, save_board, xy
from rigid_pcb.tools.mech_geometry import ESP32_CUTOUT, IMU_CUTOUT

# ===== 分区：常量/配置 =====
BOARD_FILE = ROOT / "rigid_pcb" / "layouts" / "default" / "default.kicad_pcb"
PARAMS_FILE = ROOT / "shared" / "board_params.yaml"

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
    'power.r_button_pullup': ('PW_R_BTN_PU_10K', '10k'),
    'power.r_latch_pd': ('PW_R_LATCH_PD_100K', '100k'),
    'power.r_en_pullup': ('PW_R_EN_PU_10K', '10k'),
    'power.d_button': ('PW_D_BTN', 'Schottky'),
    'power.ldo': ('PW_LDO_3V3', 'AP2112K-3.3'),
    'power.c_in': ('PW_C_IN_10U', '10uF'),
    'power.c_out': ('PW_C_OUT_10U', '10uF'),
    'battery.r_top': ('BAT_R_TOP_1M', '1M'),
    'battery.r_bottom': ('BAT_R_BOT_1M', '1M'),
    'battery.c_filter': ('BAT_C_ADC_100N', '100nF'),
    'led_r_data': ('LED_R_DATA_330R', '330R'),
    'led_c_supply': ('LED_C_SUP_100N', '100nF'),
    'tail.pos1':  ('TAIL01_VBAT_GND',     'VBAT F/GND B'),
    'tail.pos2':  ('TAIL02_LED+_DIN',     'LED+ F/DIN B'),
    'tail.pos3':  ('TAIL03_BTN_VBUS',     'BTN F/VBUS B'),
    'tail.pos4':  ('TAIL04_DP_DN',        'D+ F/D- B'),
    'tail.pos5':  ('TAIL05_TX_RX',        'TX F/RX B'),
    'bringup.gnd_pad': ('TP_GND', 'GND test'),
    'bringup.vcc_pad': ('TP_3V3', '3V3 test'),
    'bringup.vbat_pad': ('TP_VBAT_SW', 'VBAT_SW test'),
    'bringup.en_pad': ('TP_EN', 'EN test'),
    'bringup.boot_pad': ('TP_BOOT', 'BOOT test'),
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

# 金手指网络显式映射（netlist 中 tail 地址与板上 footprint 命名不一致的补偿）
TAIL_NET_MAP = {
    'tail.pos1': {'F': 'vbat_in',  'B': 'gnd'},
    'tail.pos2': {'F': 'vbat_sw',  'B': 'led_din'},
    'tail.pos3': {'F': 'btn_sw',   'B': 'vbus'},
    'tail.pos4': {'F': 'usb_dp',   'B': 'usb_dn'},
    'tail.pos5': {'F': 'uart_tx',  'B': 'uart_rx'},
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
    return 0.38, (x, y), 0


def _should_show_reference(addr):
    return addr in {'mcu', 'imu'} or addr.startswith('tail.') or addr.endswith('.pzt_signal_pad') or addr.endswith('.pzt_gnd_pad')


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


def _move_one(fp_by_addr, addr, x, y, rot, force):
    fp = fp_by_addr.get(addr)
    if fp is None:
        return 0
    if not force and not _is_initial_grid(fp):
        return 0
    fp.SetPosition(xy(pcbnew, x, y))
    fp.SetOrientationDegrees(rot)
    return 1


def _place_map(fp_by_addr, placements, force):
    moved = 0
    for addr, (x, y, rot) in placements.items():
        moved += _move_one(fp_by_addr, addr, x, y, rot, force)
    return moved


# ===== 分区：私有成员 — 网表分配 =====

def _assign_tail_nets(board):
    """显式分配金手指焊盘网络（netlist 命名不一致的补偿）。"""
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
    moved += _move_one(fp_by_addr, 'mcu', ESP32_CUTOUT[0], ESP32_CUTOUT[1], 0, False)
    moved += _move_one(fp_by_addr, 'imu', IMU_CUTOUT[0], IMU_CUTOUT[1], 0, False)

    power_x_a, power_x_b = 15.0, 19.2
    power_y = [-7.2, -2.8, 1.6, 6.0]
    power_zone = {
        'power.q_power': (power_x_a, power_y[0], 90),
        'power.d_button': (power_x_b, power_y[0], 0),
        'power.q_latch': (power_x_a, power_y[1], 90),
        'power.r_gate': (power_x_b, power_y[1], 0),
        'power.r_latch_pd': (power_x_a, power_y[2], 0),
        'power.r_button_series': (power_x_b, power_y[2], 90),
        'power.r_button_pullup': (power_x_a, power_y[3], 90),
        'power.r_en_pullup': (power_x_b, power_y[3], 90),
    }
    moved += _place_map(fp_by_addr, power_zone, False)

    regulator_zone = {
        'power.ldo': (14.0, -20.6, 90),
        'power.c_in': (18.3, -20.6, 0),
        'power.c_out': (18.3, -16.5, 0),
    }
    moved += _place_map(fp_by_addr, regulator_zone, False)

    sense_led_zone = {
        'battery.r_top': (-18.0, -20.6, 0),
        'battery.r_bottom': (-13.8, -20.6, 0),
        'battery.c_filter': (-18.0, -16.5, 0),
        'led_c_supply': (-13.8, -16.5, 0),
        'led_r_data': (-16.0, -12.4, 90),
    }
    moved += _place_map(fp_by_addr, sense_led_zone, False)

    bringup = {
        'bringup.gnd_pad': (-5.5, 44.0, 0),
        'bringup.vcc_pad': (-5.5, 49.0, 0),
        'bringup.vbat_pad': (-5.5, 54.0, 0),
        'bringup.en_pad': (-5.5, 59.0, 0),
        'bringup.boot_pad': (-5.5, 64.0, 0),
    }
    moved += _place_map(fp_by_addr, bringup, False)

    pzt_mainland = {
        'pzt_tl.series_resistor': (-58.0, -78.0, 0),
        'pzt_tl.bleed_resistor': (-54.0, -78.0, 0),
        'pzt_tl.clamp_diode': (-50.0, -78.0, 0),
        'pzt_tr.series_resistor': (50.0, -78.0, 0),
        'pzt_tr.bleed_resistor': (54.0, -78.0, 0),
        'pzt_tr.clamp_diode': (58.0, -78.0, 0),
        'pzt_bl.series_resistor': (-64.0, 58.0, 0),
        'pzt_bl.bleed_resistor': (-60.0, 58.0, 0),
        'pzt_bl.clamp_diode': (-56.0, 58.0, 0),
        'pzt_br.series_resistor': (56.0, 58.0, 0),
        'pzt_br.bleed_resistor': (60.0, 58.0, 0),
        'pzt_br.clamp_diode': (64.0, 58.0, 0),
    }
    moved += _place_map(fp_by_addr, pzt_mainland, False)

    tail_order = ['tail.pos1', 'tail.pos2', 'tail.pos3', 'tail.pos4', 'tail.pos5']
    pitch = 1.27
    span = (len(tail_order) - 1) * pitch
    start_x = -span / 2
    for i, addr in enumerate(tail_order):
        moved += _move_one(fp_by_addr, addr, round(start_x + i * pitch, 2), 96.0, 0, False)

    # 4e. 金手指网络
    tail_net_assigned = _assign_tail_nets(board)

    # 4c/4d. 标签与 3D
    labelled, visible_labels = _apply_readable_text(board)
    scaled = _apply_model_scales(board)

    save_board(board, BOARD_FILE)

    print(f'4b. 放置: 移动了 {moved} 个 atopile 封装到机械定位点')
    print(f'4c. 文本: 应用了 {labelled} 个可读Reference, 显示 {visible_labels} 个关键标签')
    print(f'4d. 3D: 应用了 {scaled} 个模块模型缩放修正')
    print(f'4e. 金手指网络: 分配了 {tail_net_assigned} 个焊盘')
    print(f'    总共 {len(fp_by_addr)} 个带 atopile_address 的封装')
    print(f'    ⚠ 无走线/过孔 — fanout 由 step4.5 独立处理')


if __name__ == '__main__':
    main()
