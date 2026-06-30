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
PY3="${PY3:-$HOME/.atopile-env/bin/python3}"
KICAD_CLI="${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}"

# 如果 PY3 不存在，回退到 which python3
if ! test -x "$PY3"; then
    PY3="$(which python3)"
fi

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

run_step4_1a() {
    title "Step 4.1a — 备份 PZT 码头至大陆走线"
    "$KIPY" "$SCRIPTS/step4.1a_backup_dock_routes.py" "$@"
    info "Step 4.1a 完成 ✓"
}

run_step4_2a() {
    title "Step 4.2a — 恢复 PZT 码头至大陆走线"
    "$KIPY" "$SCRIPTS/step4.2a_restore_dock_routes.py" "$@"
    info "Step 4.2a 完成 ✓"
}

run_step4_3() {
    title "Step 4.3 — PZT 换层补 via + B.Cu GND 铺铜"
    "$KIPY" "$SCRIPTS/step4.3_pzt_bridge_electrical_finish.py" "$@"
    info "Step 4.3 完成 ✓"
}

run_step5() {
    title "Step 5 — KiCadRoutingTools 自动布线"
    echo ""
    echo "  [1] 布线全部网络 (局部 fanout + 联合 A*)"
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

    # 确保 scipy 可用（KRT 依赖）
    if ! "$PY3" -c "import scipy" 2>/dev/null; then
        warn "scipy 未安装，正在自动安装..."
        "$PY3" -m pip install scipy 2>&1 | tail -3
    fi

    local work="$OUTPUT/step5_routing_work.kicad_pcb"
    local backup="$OUTPUT/step5_before_routing.kicad_pcb"
    local route_log="$OUTPUT/step5_route.log"
    local routed="$OUTPUT/step5_routing_result.kicad_pcb"
    local check_log="$OUTPUT/step5_connectivity.log"
    local kicad_drc_log="$OUTPUT/step5_kicad_drc.log"
    local kicad_drc_report="$OUTPUT/step5_kicad_drc.rpt"

    cp "$BOARD" "$backup"
    cp "$BOARD" "$work"
    "$KIPY" "$SCRIPTS/step5_controlled_escape.py" "$work"
    "$KIPY" "$SCRIPTS/step5_routing_view.py" prepare "$work"
    local global_nets
    global_nets="$("$KIPY" "$SCRIPTS/step5_routing_view.py" list-global-nets "$work")"
    info "全部网络联合自动布线 (A* + rip-up/reroute) ..."
    cd "$KRT"
    if ! "$PY3" route.py "$work" "$routed" \
        --nets $global_nets \
        --layers F.Cu B.Cu \
        --track-width 0.20 --grid-step 0.05 --clearance 0.20 \
        --power-nets gnd vcc vbus vbat_in vbat_sw \
        --power-nets-widths 0.35 0.35 0.60 0.60 0.60 \
        --layer-costs 1.0 1.0 \
        --max-ripup 20 \
        --max-iterations 2000000 \
        --routing-clearance-margin 1.10 \
        --board-edge-clearance 0.20 \
        --keepout --keepout-layer User.2 \
        --length-match-group usb_dp usb_dn --length-match-tolerance 0.50 \
        >"$route_log" 2>&1; then
        err "联合自动布线失败，详见 $route_log"
        return 1
    fi
    cp "$routed" "$work"
    "$KIPY" "$SCRIPTS/step5_routing_view.py" restore-pads "$work"
    "$KIPY" "$SCRIPTS/step2_substrate_outline.py" --board "$work"
    "$KIPY" "$SCRIPTS/step3_module_cutouts.py" --board "$work"

    "$KIPY" "$SCRIPTS/step5_sanitize_uuids.py" "$work"

    # KRT may exit zero with unrouted nets. Connectivity is the first gate.
    if ! "$PY3" check_connected.py "$work" >"$check_log" 2>&1; then
        err "布线结果仍有未连接网络，未覆盖正式 PCB"
        tail -40 "$check_log"
        warn "工作副本保留在 $work"
        warn "正式板备份保留在 $backup"
        return 1
    fi

    # KRT's geometric checker does not use KiCad's zone/connectivity engine.
    # Reject shorts, clearance failures, and official unconnected items before
    # the generated board is allowed to replace the formal layout.
    if test -x "$KICAD_CLI"; then
        "$KICAD_CLI" pcb drc "$work" -o "$kicad_drc_report" >"$kicad_drc_log" 2>&1 || true
        if grep -qE '^\[(shorting_items|clearance|unconnected_items)\]:' "$kicad_drc_report"; then
            err "KiCad 官方 DRC 发现短路、间距或未连接项目，未覆盖正式 PCB"
            grep -E '^\[(shorting_items|clearance|unconnected_items)\]:' "$kicad_drc_report" | sort | uniq -c
            warn "完整报告: $kicad_drc_report"
            warn "工作副本保留在 $work"
            return 1
        fi
    else
        warn "未找到 kicad-cli，无法执行官方 DRC 验收"
        return 1
    fi

    cp "$work" "$BOARD"
    info "KRT 连通性与 KiCad 官方 DRC 双重检查通过，已写回 $BOARD"
    info "布线前备份: $backup"
}

run_step5_planes() {
    if ! test -f "$KRT/rust_router/grid_router.so"; then
        err "KiCadRoutingTools Rust 路由器未安装"
        return 1
    fi
    # 确保 scipy 可用
    if ! "$PY3" -c "import scipy" 2>/dev/null; then
        warn "scipy 未安装，正在自动安装..."
        "$PY3" -m pip install scipy 2>&1 | tail -3
    fi
    info "铺 GND 电源层 (route_planes.py) ..."
    cd "$KRT"
    "$PY3" route_planes.py "$BOARD" --overwrite --nets gnd --plane-layers B.Cu
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
    run_step4_2a
    run_step4_3
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
        echo -e "${BLUE}║${NC}  ${YELLOW}[4.1]${NC} 备份码头位置                      ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[4.1a]${NC} 备份码头至大陆走线              ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[4.2]${NC} step4.2 — 恢复码头位置            ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[4.2a]${NC} 恢复码头至大陆走线              ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[4.3]${NC} PZT 换层补 via + B.Cu GND 铺铜     ${BLUE}║${NC}"
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
            4.1a) run_step4_1a ;;
            4.2)  run_step4_2 ;;
            4.2a) run_step4_2a ;;
            4.3)  run_step4_3 ;;
            5)    run_step5 ;;
            q|Q)  info "退出"; exit 0 ;;
            *)    warn "无效选择: $choice" ;;
        esac
    done
}

menu
