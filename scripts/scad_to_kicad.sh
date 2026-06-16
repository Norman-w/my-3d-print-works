#!/usr/bin/env bash
# ===== scad_to_kicad.sh =====
# 交互式全链路 PCB 生成管线
# SCAD → KiCad (step1→step4) + KiCadRoutingTools 自动布线 (step5)
#
# 依赖:
#   - KiCad Python: $KIPY (自动检测)
#   - atopile:      $ATO  (自动检测)
#   - sys Python3:  $PY3  (用于 KiCadRoutingTools CLI)
#
# 用法: ./scripts/scad_to_kicad.sh
# =====
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$ROOT/rigid_pcb/scripts"
OUTPUT="$ROOT/rigid_pcb/output"
BOARD="$ROOT/rigid_pcb/layouts/default/default.kicad_pcb"
ATO_PROJ="$ROOT/rigid_pcb"
KRT="$ROOT/rigid_pcb/tools/KiCadRoutingTools"   # KiCadRoutingTools 目录

# ---- 自动检测工具路径 ----
KIPY="${KIPY:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3}"
ATO="${ATO:-$HOME/.local/share/uv/tools/atopile/bin/ato}"
PY3="${PY3:-$(which python3)}"

# 颜色输出
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
err()   { echo -e "${RED}[✗]${NC} $*"; }
title() { echo -e "\n${BLUE}━━━ $* ━━━${NC}"; }

# ---- 工具检查 ----
check_tools() {
    local ok=true
    for tool in "$KIPY" "$ATO"; do
        if ! command -v "$tool" &>/dev/null && ! test -x "$tool"; then
            err "找不到: $tool"
            ok=false
        fi
    done
    if ! test -f "$KRT/rust_router/grid_router.so"; then
        warn "KiCadRoutingTools 路由器未安装，step5 将跳过"
        warn "安装: cd $KRT && python3 build_router.py"
    fi
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
    local retry=0
    while (( retry < 3 )); do
        if "$KIPY" "$SCRIPTS/step4_ato_placement.py" 2>/dev/null; then
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
    title "Step 5 — KiCadRoutingTools 自动布线"
    echo ""
    echo "  [1] 布线全部网络 (route.py --overwrite)"
    echo "  [2] 仅铺 GND 电源层 (route_planes.py)"
    echo "  [3] 全部布线 + GND 电源层"
    echo ""
    read -rp "  选择 [1-3]（默认 1）: " rt_choice

    case "${rt_choice:-1}" in
        1) run_step5_route_all ;;
        2) run_step5_planes ;;
        3) run_step5_route_all && run_step5_planes ;;
        *) warn "无效选择" ;;
    esac
}

run_step5_route_all() {
    if ! test -f "$KRT/rust_router/grid_router.so"; then
        err "KiCadRoutingTools Rust 路由器未安装，请先执行:"
        err "  cd $KRT && python3 build_router.py"
        return 1
    fi

    # 纯自动布线（keepout zone 已在 step4.2 注入，路由器自动避让螺丝孔）
    info "KiCadRoutingTools 自动布线 (A* + rip-up/reroute) ..."
    cd "$KRT"
    "$PY3" route.py "$BOARD" \
        --overwrite \
        --layer-costs 1.0 1.0 \
        --max-ripup 10 \
        --max-iterations 10000000 \
        2>&1 | tail -20
    info "布线完成，文件已写回 $BOARD"
}

run_step5_planes() {
    if ! test -f "$KRT/rust_router/grid_router.so"; then
        err "KiCadRoutingTools Rust 路由器未安装"
        return 1
    fi
    info "铺 GND 电源层 (route_planes.py) ..."
    cd "$KRT"
    "$PY3" route_planes.py "$BOARD" --overwrite --nets GND --plane-layers B.Cu 2>&1 | tail -10
    info "GND 层铺设完成 ✓"
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
    read -rp "  是否继续 KiCadRoutingTools 自动布线? [y/N]: " do_fr
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
        echo -e "${BLUE}║${NC}  ${YELLOW}[5]${NC}  step5 — KiCadRoutingTools 自动布线    ${BLUE}║${NC}"
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
