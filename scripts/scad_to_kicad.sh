#!/usr/bin/env bash
# ===== scad_to_kicad.sh =====
# 交互式全链路 PCB 生成管线
# SCAD → KiCad (step1→step4) + FreeRouting 自动布线 (step5)
#
# 依赖:
#   - KiCad Python: $KIPY (自动检测)
#   - atopile:     $ATO  (自动检测)
#   - Java:        $JAVA (FreeRouting 必需)
#
# 用法: ./scripts/scad_to_kicad.sh
# =====
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$ROOT/rigid_pcb/scripts"
OUTPUT="$ROOT/rigid_pcb/output"
BOARD="$ROOT/rigid_pcb/layouts/default/default.kicad_pcb"
ATO_PROJ="$ROOT/rigid_pcb"

# ---- 自动检测工具路径 ----
KIPY="${KIPY:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3}"
ATO="${ATO:-$HOME/.local/share/uv/tools/atopile/bin/ato}"
JAVA="${JAVA:-$(which java 2>/dev/null || echo /opt/homebrew/opt/openjdk/bin/java)}"
FR_JAR="$OUTPUT/freerouting.jar"       # v1.9 — GUI 模式（更稳定）
FR2_JAR="$OUTPUT/freerouting2.jar"     # v2.x — 无头模式（内存大，可能不稳）
DSN="$OUTPUT/board.dsn"
SES="$OUTPUT/board.ses"

# 颜色输出
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
err()   { echo -e "${RED}[✗]${NC} $*"; }
title() { echo -e "\n${BLUE}━━━ $* ━━━${NC}"; }

# ---- 工具检查 ----
check_tools() {
    local ok=true
    for tool in "$KIPY" "$ATO" "$JAVA"; do
        if ! command -v "$tool" &>/dev/null && ! test -x "$tool"; then
            err "找不到: $tool"
            ok=false
        fi
    done
    for f in "$FR_JAR" "$FR2_JAR"; do
        if ! test -f "$f"; then
            err "找不到: $f"
            ok=false
        fi
    done
    $ok || exit 1
}

# ---- 步骤函数 ----

run_step1() {
    title "Step 1 — 清空 + SCAD 参考线、大陆区矩形"
    "$KIPY" "$SCRIPTS/step1_clear_and_reference.py" "$@"
    info "Step 1 完成 ✓"
}

run_step2() {
    title "Step 2 — PCB 基材轮廓 (Edge.Cuts)"
    "$KIPY" "$SCRIPTS/step2_substrate_outline.py" "$@"
    info "Step 2 完成 ✓"
}

run_step3() {
    title "Step 3 — IMU/MCU 模块开孔 + 螺丝让位"
    "$KIPY" "$SCRIPTS/step3_module_cutouts.py" "$@"
    info "Step 3 完成 ✓"
}

run_step3_1() {
    title "Step 3.1 — ato build"
    cd "$ATO_PROJ"
    "$ATO" build
    info "ato build 完成 ✓"
}

run_step3_2() {
    title "Step 3.2 — 导入 ato 网络表到 KiCad"
    "$KIPY" "$SCRIPTS/step3_import_netlist.py"
    info "Step 3.2 完成 ✓"
}

run_step4() {
    title "Step 4 — atopile 组件放置 + Reference + 3D 修正"
    # macOS Rosetta: step4_ato_placement.py 模块顶层导入与 pcbnew/wxWidgets
    # 初始化时序冲突导致 SIGBUS。所有逻辑内联到 -c 参数避免模块文件加载。
    local retry=0
    while (( retry < 3 )); do
        if "$KIPY" -c "
import sys; sys.path.insert(0, '$ROOT')
import argparse, math, re
from pathlib import Path
import yaml

import pcbnew
from rigid_pcb.tools.kicad_update_utils import load_board, save_board, slot_basis, xy
from rigid_pcb.tools.mech_geometry import ESP32_CUTOUT, IMU_CUTOUT

BOARD_FILE = Path('$BOARD')
PARAMS_FILE = Path('$ROOT/shared/board_params.yaml')

# ── 常量 ──
KEEPOUT = 1.5
COL_SPACING_Y = 3.5
COL_MARGIN = 1.0
TEXT_THICKNESS = 0.10

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
    # 5P×2 双面 1.27mm 金手指尾巴 (每个位置正/背面各一个信号)
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

PZT_READABLE_PREFIXES = {k: k.upper().replace('PZT_', 'PZT_') for k in ['pzt_tr','pzt_tl','pzt_br','pzt_bl']}
# simpler:
PZT_PREFIX = {'pzt_tr': 'PZT_TR', 'pzt_tl': 'PZT_TL', 'pzt_br': 'PZT_BR', 'pzt_bl': 'PZT_BL'}
PZT_PARTS = {
    'series_resistor': ('R_SER_4K7', '4.7k'),
    'bleed_resistor': ('R_DIS_1M', '1M'),
    'clamp_diode': ('D_CLAMP', 'BAT54S'),
    'pzt_signal_pad': ('SIG', 'PZT signal wire'),
    'pzt_gnd_pad': ('GND', 'PZT GND wire'),
}
MODEL_SCALES = {'mcu': 0.3937008, 'imu': 0.3937008}

# ── 辅助函数 ──
def safe_id(text):
    return re.sub(r'[^A-Za-z0-9_+.-]+', '_', text.strip()) or 'Generated'

def infer_attr(fp):
    for pad in fp.Pads():
        if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            return pcbnew.FP_THROUGH_HOLE
    return pcbnew.FP_SMD

def address(fp):
    if not fp.HasFieldByName('atopile_address'): return None
    return fp.GetFieldByName('atopile_address').GetText()

def readable_ref(addr):
    if addr in READABLE_REFS: return READABLE_REFS[addr]
    for pzt_addr, prefix in PZT_PREFIX.items():
        stem = pzt_addr + '.'
        if addr.startswith(stem):
            part = addr[len(stem):]
            if part in PZT_PARTS:
                suffix, value = PZT_PARTS[part]
                return f'{prefix}_{suffix}', value
    return None

def set_text_size(field, size_mm):
    field.SetTextHeight(pcbnew.FromMM(size_mm))
    field.SetTextWidth(pcbnew.FromMM(size_mm))
    field.SetTextThickness(pcbnew.FromMM(TEXT_THICKNESS))

def set_text_at(field, x, y, angle_deg=0):
    field.SetPosition(xy(pcbnew, x, y))
    field.SetTextAngleDegrees(angle_deg)

def label_spec(addr, fp):
    pos = fp.GetPosition()
    x, y = pos.x / 1_000_000, pos.y / 1_000_000
    if addr == 'mcu': return 0.60, (x, y - ESP32_CUTOUT[3]/2 - 1.4), 0
    if addr == 'imu': return 0.60, (x, y - IMU_CUTOUT[3]/2 - 1.2), 0
    if addr.startswith('tail.'): return 0.38, (x, y + 1.4), 0
    if addr.startswith('pzt_'): return 0.38, (x, y + 1.2), fp.GetOrientationDegrees()
    return 0.38, (x, y), 0

def should_show_reference(addr):
    return addr in {'mcu','imu'} or addr.startswith('tail.') or addr.endswith('.pzt_signal_pad') or addr.endswith('.pzt_gnd_pad')

def apply_readable_text(board):
    used, changed, visible = set(), 0, 0
    for fp in board.GetFootprints():
        addr = address(fp)
        if not addr: continue
        alias = readable_ref(addr)
        if not alias: continue
        ref, value = alias
        if ref in used: raise RuntimeError(f'duplicate ref: {ref}')
        used.add(ref)
        fp.SetReference(ref)
        fp.SetValue(value)
        size, (tx, ty), angle = label_spec(addr, fp)
        ref_field, value_field = fp.Reference(), fp.Value()
        show_ref = should_show_reference(addr)
        ref_field.SetVisible(show_ref)
        value_field.SetVisible(False)
        ref_field.SetLayer(pcbnew.F_SilkS)
        value_field.SetLayer(pcbnew.F_Fab)
        set_text_size(ref_field, size)
        set_text_size(value_field, 0.45)
        set_text_at(ref_field, tx, ty, angle)
        changed += 1
        visible += 1 if show_ref else 0
    return changed, visible

def apply_model_scales(board):
    changed = 0
    for fp in board.GetFootprints():
        addr = address(fp)
        if addr not in MODEL_SCALES: continue
        models = fp.Models()
        fixed = []
        for model in models:
            s = MODEL_SCALES[addr]
            model.m_Scale.Set(s, s, s)
            fixed.append(model)
        models.clear()
        for model in fixed: models.append(model); changed += 1
    return changed

def is_initial_grid(fp):
    pos = fp.GetPosition()
    x, y = pos.x/1_000_000, pos.y/1_000_000
    return math.isclose(x/10, round(x/10), abs_tol=1e-3) and math.isclose(y/10, round(y/10), abs_tol=1e-3)

def move_one(fp_by_addr, addr, x, y, rot, force):
    fp = fp_by_addr.get(addr)
    if fp is None: return 0
    if not force and not is_initial_grid(fp): return 0
    fp.SetPosition(xy(pcbnew, x, y))
    fp.SetOrientationDegrees(rot)
    return 1

def _cutout_edges(cutout):
    cx, cy, w, h = cutout
    hw, hh = w/2, h/2
    return {'left':cx-hw-KEEPOUT, 'right':cx+hw+KEEPOUT, 'top':cy-hh-KEEPOUT, 'bot':cy+hh+KEEPOUT, 'cx':cx, 'cy':cy}

def place_map(fp_by_addr, placements, force):
    moved = 0
    for addr, (x, y, rot) in placements.items():
        moved += move_one(fp_by_addr, addr, x, y, rot, force)
    return moved

# ── 主流程 ──
board = load_board(pcbnew, BOARD_FILE)

changed = 0
for fp in board.GetFootprints():
    ref = fp.GetReference() or 'Generated'
    if not fp.GetFPIDAsString():
        fp.SetFPIDAsString(f'SmartPaddle:{safe_id(ref)}')
        changed += 1
    if fp.GetAttributes() == 0:
        fp.SetAttributes(infer_attr(fp))
        changed += 1
print(f'4a. 规范化: 修正了 {changed} 个封装的元数据字段')

params = yaml.safe_load(PARAMS_FILE.read_text())
fp_by_addr = {addr: fp for fp in board.GetFootprints() if (addr := address(fp))}
if not fp_by_addr:
    print('4b. 警告: 未找到带 atopile_address 属性的封装')
    save_board(board, BOARD_FILE)
    sys.exit(0)

moved = 0
moved += move_one(fp_by_addr, 'mcu', ESP32_CUTOUT[0], ESP32_CUTOUT[1], 0, False)
moved += move_one(fp_by_addr, 'imu', IMU_CUTOUT[0], IMU_CUTOUT[1], 0, False)

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
moved += place_map(fp_by_addr, power_zone, False)

regulator_zone = {
    'power.ldo': (14.0, -20.6, 90),
    'power.c_in': (18.3, -20.6, 0),
    'power.c_out': (18.3, -16.5, 0),
}
moved += place_map(fp_by_addr, regulator_zone, False)

sense_led_zone = {
    'battery.r_top': (-18.0, -20.6, 0),
    'battery.r_bottom': (-13.8, -20.6, 0),
    'battery.c_filter': (-18.0, -16.5, 0),
    'led_c_supply': (-13.8, -16.5, 0),
    'led_r_data': (-16.0, -12.4, 90),
}
moved += place_map(fp_by_addr, sense_led_zone, False)

bringup = {
    'bringup.gnd_pad': (-5.5, 44.0, 0),
    'bringup.vcc_pad': (-5.5, 49.0, 0),
    'bringup.vbat_pad': (-5.5, 54.0, 0),
    'bringup.en_pad': (-5.5, 59.0, 0),
    'bringup.boot_pad': (-5.5, 64.0, 0),
}
moved += place_map(fp_by_addr, bringup, False)

pzt_mainland = {
    'pzt_tl.series_resistor': (-58.0, -78.0, 0), 'pzt_tl.bleed_resistor': (-54.0, -78.0, 0),
    'pzt_tl.clamp_diode': (-50.0, -78.0, 0),
    'pzt_tr.series_resistor': (50.0, -78.0, 0), 'pzt_tr.bleed_resistor': (54.0, -78.0, 0),
    'pzt_tr.clamp_diode': (58.0, -78.0, 0),
    'pzt_bl.series_resistor': (-64.0, 58.0, 0), 'pzt_bl.bleed_resistor': (-60.0, 58.0, 0),
    'pzt_bl.clamp_diode': (-56.0, 58.0, 0),
    'pzt_br.series_resistor': (56.0, 58.0, 0), 'pzt_br.bleed_resistor': (60.0, 58.0, 0),
    'pzt_br.clamp_diode': (64.0, 58.0, 0),
}
moved += place_map(fp_by_addr, pzt_mainland, False)

tail_order = ['tail.pos1','tail.pos2','tail.pos3','tail.pos4','tail.pos5']
pitch = 1.27  # 1.27mm 间距 5P×2 双面
span = (len(tail_order)-1)*pitch  # = 5.08mm
start_x = -span/2
for i, addr in enumerate(tail_order):
    # 金手指放在尾巴尖端，距尾端 2mm 留插拔导入边
    moved += move_one(fp_by_addr, addr, round(start_x+i*pitch,2), 96.0, 0, False)

labelled, visible_labels = apply_readable_text(board)
scaled = apply_model_scales(board)

# 网络同步（从最近的 ato backup）
import os
ato_backup_dir = Path('$ROOT/rigid_pcb/build/builds/default')
net_assigned, net_source = 0, None
if ato_backup_dir.exists():
    backups = sorted(ato_backup_dir.glob('default.20*.kicad_pcb'), key=lambda p: p.stat().st_mtime, reverse=True)
    for backup in backups:
        try:
            src = pcbnew.LoadBoard(str(backup))
            src_nets = {}
            for sfp in src.GetFootprints():
                saddr = address(sfp)
                if not saddr: continue
                for spad in sfp.Pads():
                    if spad.GetNetname():
                        src_nets[(saddr, spad.GetNumber())] = spad.GetNetname()
            if src_nets:
                net_cache = {}
                for fp in board.GetFootprints():
                    a = address(fp)
                    if not a: continue
                    for pad in fp.Pads():
                        n = src_nets.get((a, pad.GetNumber()))
                        if not n: continue
                        net = net_cache.get(n) or board.FindNet(n) or pcbnew.NETINFO_ITEM(board, n)
                        if net not in net_cache.values():
                            if board.FindNet(n) is None: board.Add(net)
                        net_cache[n] = net
                        pad.SetNet(net)
                        net_assigned += 1
                board.BuildListOfNets()
                board.SanitizeNetcodes()
                net_source = backup
                break
        except Exception:
            continue

save_board(board, BOARD_FILE)
print(f'4b. 放置: 移动了 {moved} 个 atopile 封装到机械定位点')
print(f'4c. 文本: 应用了 {labelled} 个可读Reference, 显示 {visible_labels} 个关键标签')
print(f'4d. 3D: 应用了 {scaled} 个模块模型缩放修正')
if net_source:
    print(f'4e. 网络: 从 {net_source.name} 同步了 {net_assigned} 个焊盘网络')
print(f'    总共 {len(fp_by_addr)} 个带 atopile_address 的封装')
" 2>/dev/null; then
            info "Step 4 完成 ✓"
            return 0
        fi
        ((retry++))
        warn "Step 4 崩溃 (尝试 $retry/3)，1秒后重试..."
        sleep 1
    done
    err "Step 4 重试 3 次均失败，请手动执行"
    return 1
}

run_step4_1() {
    title "Step 4.1 — 备份 PZT 码头组件位置"
    "$KIPY" "$SCRIPTS/step4.1_backup_docks.py" "$@"
    info "Step 4.1 完成 ✓"
}

run_step4_2() {
    title "Step 4.2 — 恢复 PZT 码头组件位置"
    "$KIPY" "$SCRIPTS/step4.2_restore_docks.py" "$@"
    info "Step 4.2 完成 ✓"
}

run_step5() {
    title "Step 5 — FreeRouting 自动布线"
    echo ""
    echo "  [1] 使用 FreeRouting v2 无头模式 (推荐)"
    echo "  [2] 使用 FreeRouting v1.9 GUI (需手动操作)"
    echo "  [3] 仅导出 DSN (不布线)"
    echo "  [4] 仅导入已有 SES"
    echo ""
    read -rp "  选择 [1-4]: " fr_choice

    case "${fr_choice:-1}" in
        1) run_step5_headless ;;
        2) run_step5_gui ;;
        3) run_step5_dsn_only ;;
        4) run_step5_ses_import ;;
        *) warn "无效选择" ;;
    esac
}

run_step5_dsn_only() {
    info "导出 DSN ..."
    "$KIPY" -c "
import sys; sys.path.insert(0,'$ROOT')
import pcbnew
board = pcbnew.LoadBoard('$BOARD')
pcbnew.ExportSpecctraDSN(board, '$DSN')
print(f'DSN → $DSN')
" 2>&1 | grep -vE "Debug:|swig|stdpbase|assert"
    info "DSN 导出完成 ✓"
}

run_step5_headless() {
    run_step5_dsn_only
    info "启动 FreeRouting v2 无头模式 ..."
    cd "$OUTPUT"
    "$JAVA" -Xmx4g -jar "$FR2_JAR" \
        --gui.enabled=false \
        -de "$DSN" \
        -do "$SES" \
        -mt 4 \
        2>&1 | tail -20
    if test -f "$SES" && grep -q "session" "$SES" 2>/dev/null; then
        run_step5_ses_import
    else
        err "FreeRouting 未生成有效 SES 文件，请尝试 GUI 模式"
    fi
}

run_step5_gui() {
    run_step5_dsn_only
    info "启动 FreeRouting v1.9 GUI ..."
    cd "$OUTPUT"
    echo ""
    echo "  ┌────────────────────────────────────────────┐"
    echo "  │  FreeRouting GUI 操作步骤:                  │"
    echo "  │  1. File → Open → 选择 board.dsn           │"
    echo "  │  2. Routing → Autorouting                  │"
    echo "  │  3. File → Export Specctra Session File    │"
    echo "  │     保存为 board.ses (覆盖已有)             │"
    echo "  │  4. 关闭 FreeRouting 窗口                   │"
    echo "  │  5. 回到此处按 [s] 导入 SES → KiCad         │"
    echo "  └────────────────────────────────────────────┘"
    echo ""
    "$JAVA" -jar "$FR_JAR" "$DSN" > /dev/null 2>&1 &
    FR_PID=$!
    info "FreeRouting PID=$FR_PID，请在 GUI 中完成布线后..."
    read -rp "  按 [s] 导入 SES 到 KiCad，其他键跳过: " do_import
    if [[ "$do_import" == "s" ]]; then
        run_step5_ses_import
    fi
}

run_step5_ses_import() {
    if ! test -f "$SES"; then
        err "SES 文件不存在: $SES"
        return 1
    fi
    info "导入 SES → KiCad ..."
    "$KIPY" -c "
import sys; sys.path.insert(0,'$ROOT')
import pcbnew
board = pcbnew.LoadBoard('$BOARD')
pcbnew.ImportSpecctraSES('$SES')
pcbnew.SaveBoard('$BOARD', board)
print(f'SES → $BOARD 导入完成')
" 2>&1 | grep -vE "Debug:|swig|stdpbase|assert"
    info "SES 导入完成 ✓"
}

run_all() {
    title "全链路执行 (跳过 step4.1)"
    run_step1
    run_step2
    run_step3
    run_step3_1
    run_step3_2
    run_step4
    run_step4_2
    echo ""
    read -rp "  是否继续 FreeRouting 自动布线? [y/N]: " do_fr
    if [[ "$do_fr" =~ ^[Yy]$ ]]; then
        run_step5
    fi
    title "全链路完成 🚀"
}

# ---- 交互菜单 ----
menu() {
    check_tools
    while true; do
        echo ""
        echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║${NC}     ${GREEN}SmartPaddle PCB 全链路管线${NC}          ${BLUE}║${NC}"
        echo -e "${BLUE}╠══════════════════════════════════════════╣${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[a]${NC}  全部 (skip 4.1)                   ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[1]${NC}  step1 — 清空 + 参考线+大陆区        ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[2]${NC}  step2 — PCB 基材轮廓               ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[3]${NC}  step3 — 模块开孔                   ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[3.1]${NC} ato build                        ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[3.2]${NC} step3.2 — 导入网络表                ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[4]${NC}  step4 — ato 组件放置               ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[4.2]${NC} step4.2 — 恢复码头位置            ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[5]${NC}  step5 — FreeRouting 自动布线       ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[q]${NC}  退出                              ${BLUE}║${NC}"
        echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
        echo ""
        read -rp "  选择: " choice

        case "$choice" in
            a|A)  run_all ;;
            1)    run_step1 ;;
            2)    run_step2 ;;
            3)    run_step3 ;;
            3.1)  run_step3_1 ;;
            3.2)  run_step3_2 ;;
            4)    run_step4 ;;
            4.1)  run_step4_1 ;;
            4.2)  run_step4_2 ;;
            5)    run_step5 ;;
            q|Q)  info "退出"; exit 0 ;;
            *)    warn "无效选择: $choice" ;;
        esac
    done
}

menu
