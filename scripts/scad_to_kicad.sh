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

run_step4() {
    title "Step 4 — atopile 组件放置 + Reference + 3D 修正"
    # pcbnew wxApp 初始化偶发 Bus Error，自动重试最多 3 次
    local retry=0
    while (( retry < 3 )); do
        if "$KIPY" "$SCRIPTS/step4_ato_placement.py" "${@}" 2>/dev/null; then
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
