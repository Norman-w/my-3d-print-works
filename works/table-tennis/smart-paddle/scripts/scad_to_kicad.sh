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
SCRIPTS="$ROOT/pcb/scripts"
OUTPUT="$ROOT/pcb/output"
BOARD="$ROOT/pcb/layouts/default/default.kicad_pcb"
ATO_PROJ="$ROOT/pcb"
KRT="$ROOT/pcb/tools/KiCadRoutingTools"   # KiCadRoutingTools 目录

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
require_script() {
    local script="$SCRIPTS/$1"
    if ! test -f "$script"; then
        err "缺少脚本: $script"
        return 1
    fi
}
run_logged() {
    local log="$1"
    shift
    if ! "$@" >>"$log" 2>&1; then
        err "命令失败: $*"
        warn "日志尾部: $log"
        tail -80 "$log"
        return 1
    fi
}

# ---- 工具检查 ----
check_tools() {
    local ok=true
    for tool in "$KIPY"; do
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
    local ato_version build_log
    if ! command -v "$ATO" &>/dev/null && ! test -x "$ATO"; then
        err "找不到 atopile: $ATO"
        err "仅 Step 3.1 暂停；其他标准 Python 步骤仍可从菜单运行"
        return 1
    fi
    ato_version="$("$ATO" --version)"
    info "atopile 可执行文件: $ATO"
    info "atopile 实际版本: $ato_version"
    if [[ "$ato_version" != *"0.12.5"* ]]; then
        err "版本不符：pcb/ato.yaml 锁定 0.12.5，拒绝用其他版本生成"
        return 1
    fi
    cd "$ATO_PROJ"
    build_log="$(mktemp -t smartpaddle-ato-build.XXXXXX)"
    if ! "$ATO" build 2>&1 | tee "$build_log"; then
        err "ato build 命令失败（日志: $build_log）"
        return 1
    fi
    # atopile 0.12.5 may return zero even after reporting a build-stopping
    # decode error, so its explicit success marker is the authoritative gate.
    if ! grep -q "Build successful" "$build_log"; then
        err "ato build 未出现成功标记（日志: $build_log）"
        return 1
    fi
    rm -f "$build_log"
    info "ato build 完成 ✓"
}

run_step3_2() {
    title "Step 3.2 — 导入 ato 网络表到 KiCad"
    "$KIPY" "$SCRIPTS/validate_esp32s3wroom1_pinmap.py"
    "$KIPY" "$SCRIPTS/step3_import_netlist.py"
    "$KIPY" "$SCRIPTS/step3_finalize_generated_board.py"
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

run_step4_1e() {
    title "Step 4.1e — 备份 C4 全部器件位置"
    "$KIPY" "$SCRIPTS/step4.1e_backup_c4_placement.py" "$@"
    info "Step 4.1e 完成 ✓"
}

run_step4_2() {
    title "Step 4.2 — 恢复 PZT 码头组件位置"
    "$KIPY" "$SCRIPTS/step4.2_restore_docks.py" "$@"
    info "Step 4.2 完成 ✓"
}

run_step4_2b() {
    title "Step 4.2b — PZT 焊线焊盘安全内收"
    require_script "step4.2b_pzt_wire_pad_safety.py" || return 1
    "$KIPY" "$SCRIPTS/step4.2b_pzt_wire_pad_safety.py" "$@"
    info "Step 4.2b 完成 ✓"
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
    echo "  [1] 重填现有 copper zones"
    echo "  [2] 仅铺 GND 电源层 (route_planes.py)"
    echo "  [3] 旧版逐网自动布线 (当前仓库缺少若干 step5 脚本，默认禁用)"
    echo ""
    read -rp "  选择 [1-3]（默认 1）: " rt_choice

    case "${rt_choice:-1}" in
        1) run_step5_refill_zones ;;
        2) run_step5_planes ;;
        3) run_step5_route_all ;;
        *) warn "无效选择" ;;
    esac
}

run_step5_refill_zones() {
    title "Step 5.0 — 重填 copper zones"
    "$KIPY" "$SCRIPTS/step5_refill_zones.py" "$BOARD"
    info "Copper zones 已重填 ✓"
}

run_step5_route_all() {
    local missing=()
    for script in \
        step5_clean_routing_input.py \
        step4.2b_pzt_wire_pad_safety.py \
        step5_controlled_escape.py \
        step5_routing_view.py \
        step5_geometry_gate.py \
        step5_safe_post_route_closure.py \
        step5_ground_stitch.py \
        step5_sanitize_uuids.py
    do
        if ! test -f "$SCRIPTS/$script"; then
            missing+=("$script")
        fi
    done
    if ((${#missing[@]})); then
        err "旧版逐网自动布线需要的脚本当前不在仓库中，已禁用以避免破坏 PCB。"
        printf '  - %s\n' "${missing[@]}"
        return 1
    fi

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
    local foundation_log="$OUTPUT/step5_foundation_route.log"
    local routed="$OUTPUT/step5_routing_result.kicad_pcb"
    local check_log="$OUTPUT/step5_connectivity.log"
    local kicad_drc_log="$OUTPUT/step5_kicad_drc.log"
    local kicad_drc_report="$OUTPUT/step5_kicad_drc.rpt"
    local prep_log="$OUTPUT/step5_prepare.log"
    local post_log="$OUTPUT/step5_post_restore.log"
    local safe_closure_log="$OUTPUT/step5_safe_post_route_closure.log"

    drc_hard_count() {
        local pcb="$1"
        local report="$2"
        local log="$3"
        "$KIPY" "$SCRIPTS/step5_refill_zones.py" "$pcb" >/dev/null 2>&1
        "$KICAD_CLI" pcb drc "$pcb" -o "$report" >"$log" 2>&1 || true
        python3 - "$report" <<'PY'
from pathlib import Path
import sys

report = Path(sys.argv[1])
text = report.read_text(errors="ignore") if report.exists() else ""
hard = ("shorting_items", "clearance", "tracks_crossing", "hole_clearance")
count = 0
for line in text.splitlines():
    if any(line.startswith(f"[{item}]:") for item in hard):
        count += 1
print(count)
PY
    }

    krt_summary_ok() {
        local log="$1"
        python3 - "$log" <<'PY'
import json
import re
import sys

text = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
if "All nets are already fully connected - nothing to route!" in text:
    sys.exit(0)
matches = re.findall(r"JSON_SUMMARY:\s*(\{.*\})", text)
if not matches:
    sys.exit(2)
data = json.loads(matches[-1])
if data.get("failed_single") or data.get("failed_multipoint") or data.get("failed", 0):
    sys.exit(1)
PY
    }

    drc_hard_delta_bad() {
        local before_report="$1"
        local after_report="$2"
        python3 - "$before_report" "$after_report" <<'PY'
from collections import Counter
from pathlib import Path
import sys

hard = {
    "shorting_items",
    "clearance",
    "tracks_crossing",
    "hole_clearance",
    "copper_edge_clearance",
}

def counts(path: str) -> Counter[str]:
    report = Path(path)
    out: Counter[str] = Counter()
    if not report.exists():
        return out
    for line in report.read_text(errors="ignore").splitlines():
        if line.startswith("[") and "]:" in line:
            category = line[1:line.index("]:")]
            if category in hard:
                out[category] += 1
    return out

before = counts(sys.argv[1])
after = counts(sys.argv[2])
bad = [name for name in sorted(hard) if after[name] > before[name]]
if bad:
    print(", ".join(f"{name}: {before[name]}->{after[name]}" for name in bad))
    sys.exit(1)
PY
    }

    route_one_checked() {
        local net="$1"
        local width="$2"
        local log="$3"
        local safe="${net//[^A-Za-z0-9_]/_}"
        local net_log="$OUTPUT/step5_${safe}_route.log"
        local before="$OUTPUT/step5_before_${safe}.kicad_pcb"
        local candidate_report="$OUTPUT/step5_${safe}_candidate_drc.rpt"
        local candidate_log="$OUTPUT/step5_${safe}_candidate_drc.log"
        local candidate_geometry_log="$OUTPUT/step5_${safe}_candidate_geometry.log"
        local before_report="$OUTPUT/step5_${safe}_before_drc.rpt"
        local before_log="$OUTPUT/step5_${safe}_before_drc.log"
        local before_hard
        local after_hard

        if "$PY3" check_connected.py "$work" --nets "$net" --quiet >/dev/null 2>&1; then
            info "  - $net: 已连通，跳过 KRT"
            return 0
        fi
        cp "$work" "$before"
        before_hard="$(drc_hard_count "$work" "$before_report" "$before_log")"
        rm -f "$routed"
        if ! "$PY3" route.py "$work" "$routed" \
            --nets "$net" \
            --layers F.Cu B.Cu \
            --track-width "$width" --grid-step 0.05 --clearance 0.20 \
            --layer-costs 1.0 1.0 \
            --max-ripup 20 \
            --max-iterations 2000000 \
            --routing-clearance-margin 1.10 \
            --board-edge-clearance 0.50 \
            --keepout --keepout-layer User.2 \
            >"$net_log" 2>&1; then
            {
                echo ""
                echo "===== $net FAILED COMMAND ====="
                cat "$net_log"
            } >>"$log"
            warn "  - $net: KRT 命令失败，已回滚"
            cp "$before" "$work"
            return 1
        fi
        {
            echo ""
            echo "===== $net ====="
            cat "$net_log"
        } >>"$log"
        if ! krt_summary_ok "$net_log"; then
            warn "  - $net: KRT 自报未完全布通，已回滚"
            cp "$before" "$work"
            return 1
        fi
        if test -f "$routed"; then
            cp "$routed" "$work"
        else
            warn "  - $net: KRT 判断已连通且未生成新板，保留当前工作板"
        fi
        if ! "$KIPY" "$SCRIPTS/step5_geometry_gate.py" "$work" >"$candidate_geometry_log" 2>&1; then
            warn "  - $net: 引入生产几何错误，已回滚"
            tail -20 "$candidate_geometry_log"
            cp "$before" "$work"
            return 1
        fi
        after_hard="$(drc_hard_count "$work" "$candidate_report" "$candidate_log")"
        if ! delta="$(drc_hard_delta_bad "$before_report" "$candidate_report")"; then
            warn "  - $net: 引入 KiCad 硬 DRC (${delta})，已回滚"
            cp "$before" "$work"
            return 1
        fi
        info "  - $net: 已接受 (KiCad 硬 DRC ${before_hard}->${after_hard})"
        return 0
    }

    cp "$BOARD" "$backup"
    cp "$BOARD" "$work"
    : >"$prep_log"
    : >"$post_log"
    run_logged "$prep_log" "$KIPY" "$SCRIPTS/step5_clean_routing_input.py" "$work"
    run_logged "$prep_log" "$KIPY" "$SCRIPTS/step4.2b_pzt_wire_pad_safety.py" --board "$work"
    run_logged "$prep_log" "$KIPY" "$SCRIPTS/step4.2a_restore_dock_routes.py" --board "$work" --skip-pzt-raw --allow-module-entry-routes --allow-pad-conflicts
    run_logged "$prep_log" "$KIPY" "$SCRIPTS/step5_controlled_escape.py" "$work"
    run_logged "$prep_log" "$KIPY" "$SCRIPTS/step4.3_pzt_bridge_electrical_finish.py" --board "$work"
    run_logged "$prep_log" "$KIPY" "$SCRIPTS/step5_refill_zones.py" "$work"
    run_logged "$prep_log" "$KIPY" "$SCRIPTS/step5_routing_view.py" prepare "$work"
    local signal_nets
    signal_nets="$("$KIPY" "$SCRIPTS/step5_routing_view.py" list-nets "$work")"
    if test -z "$signal_nets"; then
        err "没有可交给 KiCadRoutingTools 的普通信号网络"
        return 1
    fi

    local tail_signal_priority=""
    local tail_power_priority=""
    local control_signal_priority=""
    local pzt_signal_priority=""
    local all_priority_nets=""
    local remaining_signal_nets=""
    for priority_net in uart_tx uart_rx usb_dp usb_dn; do
        if [[ " $signal_nets " == *" $priority_net "* ]] || [[ " usb_dp usb_dn " == *" $priority_net "* ]]; then
            tail_signal_priority="$tail_signal_priority $priority_net"
            all_priority_nets="$all_priority_nets $priority_net"
        fi
    done
    for priority_net in vbus vbat_in vbat_sw; do
        if [[ " $signal_nets " == *" $priority_net "* ]] || [[ " vbus vbat_in vbat_sw " == *" $priority_net "* ]]; then
            tail_power_priority="$tail_power_priority $priority_net"
            all_priority_nets="$all_priority_nets $priority_net"
        fi
    done
    for priority_net in en led_din boot_btn btn_sw user_btn; do
        if [[ " $signal_nets " == *" $priority_net "* ]]; then
            control_signal_priority="$control_signal_priority $priority_net"
            all_priority_nets="$all_priority_nets $priority_net"
        fi
    done
    for priority_net in pzt_bl_signal pzt_br_signal pzt_tl_signal pzt_tr_signal; do
        if [[ " $signal_nets " == *" $priority_net "* ]]; then
            pzt_signal_priority="$pzt_signal_priority $priority_net"
            all_priority_nets="$all_priority_nets $priority_net"
        fi
    done
    for signal_net in $signal_nets; do
        if [[ " $all_priority_nets " == *" $signal_net "* ]]; then
            continue
        fi
        remaining_signal_nets="$remaining_signal_nets $signal_net"
    done

    cd "$KRT"
    : >"$route_log"
    local routed_signal_count=0
    local failed_signal_count=0
    if test -n "$tail_signal_priority"; then
        info "尾插 UART/USB 受限长线优先布线 ..."
        info "网络:$tail_signal_priority"
        for signal_net in $tail_signal_priority; do
            if route_one_checked "$signal_net" 0.20 "$route_log"; then
                ((routed_signal_count++))
            else
                ((failed_signal_count++))
            fi
        done
    fi

    if test -n "$tail_power_priority"; then
        info "尾插电源网络优先布线 ..."
        info "网络:$tail_power_priority"
        for signal_net in $tail_power_priority; do
            if route_one_checked "$signal_net" 0.25 "$route_log"; then
                ((routed_signal_count++))
            else
                ((failed_signal_count++))
            fi
        done
    fi

    if test -n "$control_signal_priority"; then
        info "控制/LED 网络优先布线 ..."
        info "网络:$control_signal_priority"
        for signal_net in $control_signal_priority; do
            if route_one_checked "$signal_net" 0.20 "$route_log"; then
                ((routed_signal_count++))
            else
                ((failed_signal_count++))
            fi
        done
    fi

    if test -n "$pzt_signal_priority"; then
        info "PZT signal 网络优先布线 ..."
        info "网络:$pzt_signal_priority"
        for signal_net in $pzt_signal_priority; do
            if route_one_checked "$signal_net" 0.20 "$route_log"; then
                ((routed_signal_count++))
            else
                ((failed_signal_count++))
            fi
        done
    fi

    local foundation_nets
    foundation_nets="vcc"
    info "基础电源/USB 网络布线 (受控逃逸后 KRT 短补) ..."
    info "网络: $foundation_nets"
    : >"$foundation_log"
    for foundation_net in $foundation_nets; do
        info "  - $foundation_net"
        if ! route_one_checked "$foundation_net" 0.25 "$foundation_log"; then
            warn "基础网络 $foundation_net 暂未接受；继续尝试其他网络，最终由连通性闸门汇总"
        fi
    done

    info "普通信号网络逐网自动布线 (A* + DRC 接受/回滚) ..."
    info "网络:$remaining_signal_nets"
    for signal_net in $remaining_signal_nets; do
        if route_one_checked "$signal_net" 0.20 "$route_log"; then
            ((routed_signal_count++))
        else
            ((failed_signal_count++))
        fi
    done
    if (( failed_signal_count > 0 )); then
        warn "普通信号逐网布线: 接受 ${routed_signal_count} 个，回滚 ${failed_signal_count} 个；后续连通性闸门会列出剩余网络"
    fi

    : >"$safe_closure_log"
    run_logged "$safe_closure_log" "$KIPY" "$SCRIPTS/step5_safe_post_route_closure.py" "$work" \
        --kicad-cli "$KICAD_CLI" \
        --krt "$KRT" \
        --krt-py "$PY3"

    run_logged "$post_log" "$KIPY" "$SCRIPTS/step5_routing_view.py" restore-pads "$work"
    run_logged "$post_log" "$KIPY" "$SCRIPTS/step2_substrate_outline.py" --board "$work"
    run_logged "$post_log" "$KIPY" "$SCRIPTS/step3_module_cutouts.py" --board "$work"
    run_logged "$post_log" "$KIPY" "$SCRIPTS/step5_ground_stitch.py" "$work"
    run_logged "$post_log" "$KIPY" "$SCRIPTS/step4.3_pzt_bridge_electrical_finish.py" --board "$work" --zone-only

    run_logged "$post_log" "$KIPY" "$SCRIPTS/step5_sanitize_uuids.py" "$work"
    if ! "$KIPY" "$SCRIPTS/step5_geometry_gate.py" "$work"; then
        err "生产几何闸门失败，未覆盖正式 PCB"
        warn "工作副本保留在 $work"
        warn "正式板备份保留在 $backup"
        return 1
    fi

    # KRT may exit zero with unrouted nets. Connectivity is the first gate.
    local connectivity_nets=""
    for signal_net in $signal_nets; do
        if [[ "$signal_net" == "gnd" ]]; then
            continue
        fi
        connectivity_nets="$connectivity_nets $signal_net"
    done
    if ! "$PY3" check_connected.py "$work" --nets $connectivity_nets >"$check_log" 2>&1; then
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
        if grep -qE '^\[(shorting_items|clearance|tracks_crossing|hole_clearance|unconnected_items)\]:' "$kicad_drc_report"; then
            err "KiCad 官方 DRC 发现短路、间距、交叉、孔间距或未连接项目，未覆盖正式 PCB"
            grep -E '^\[(shorting_items|clearance|tracks_crossing|hole_clearance|unconnected_items)\]:' "$kicad_drc_report" | sort | uniq -c
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
    if test -f "$SCRIPTS/step4.2b_pzt_wire_pad_safety.py"; then
        run_step4_2b
    else
        warn "缺少 step4.2b_pzt_wire_pad_safety.py，跳过 PZT 焊线焊盘安全内收"
    fi
    run_step4_2a --skip-pzt-raw --allow-module-entry-routes --allow-pad-conflicts
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
        echo -e "${BLUE}║${NC}  ${YELLOW}[4.1e]${NC} 备份 C4 全部器件位置              ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[4.1a]${NC} 备份码头至大陆走线              ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[4.2]${NC} step4.2 — 恢复码头位置            ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}  ${YELLOW}[4.2b]${NC} PZT 焊线焊盘安全内收             ${BLUE}║${NC}"
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
            3.1)  if ! run_step3_1; then warn "Step 3.1 未完成，菜单继续可用"; fi ;;
            3.2)  run_step3_2 ;;
            4)    run_step4 ;;
            4.1)  run_step4_1 ;;
            4.1e) run_step4_1e ;;
            4.1a) run_step4_1a ;;
            4.2)  run_step4_2 ;;
            4.2b) run_step4_2b ;;
            4.2a) run_step4_2a ;;
            4.3)  run_step4_3 ;;
            5)    run_step5 ;;
            q|Q)  info "退出"; exit 0 ;;
            *)    warn "无效选择: $choice" ;;
        esac
    done
}

menu
