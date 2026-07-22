"""Step 3.2: 解析 ato 网络表，按 atopile_address 匹配封装，分配网络到焊盘。

匹配策略：网络表 comp 的 sheetpath 中包含 "::address" 形式的 ato 地址，
与板上封装的 `atopile_address` 属性一一对应。

必须在 ato build 之后运行。可在 step4 前后运行。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ===== 常量/配置 =====
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "pcb"))
from lib.esp32c6n8.pinmap import PROJECT_BINDINGS  # 校本 MCU 脚位

BUILD_DIR = PROJECT_ROOT / "pcb" / "build"
NETLIST_FILE = BUILD_DIR / "default.net"
BOARD_FILE = PROJECT_ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"

# 网络表中 ato 地址与板上 ato 地址不一致的映射
# （因 ato 模块重命名导致）
ADDR_REMAP: dict[str, str] = {
    "bat_r_top": "battery.r_top",
    "bat_r_bottom": "battery.r_bottom",
    "bat_c_filter": "battery.c_filter",
}

# Symbols use readable pin names while the physical module footprints use
# numeric castellated-pad numbers. MCU 脚名来自校本 pinmap；IMU 仍就地维护。
MODULE_PIN_NAMES: dict[str, dict[str, str]] = {
    "imu": {
        "1": "GND_1", "2": "VBUS", "3": "VBAT_3", "4": "VDDIO",
        "7": "ADIN", "8": "GND_8", "9": "LED_B", "10": "LED_R",
        "11": "GPIO", "12": "KEY", "13": "RXD", "14": "TXD",
        "15": "VBAT_15", "16": "GND_16",
    },
    "mcu": {str(pad): name for pad, name in PROJECT_BINDINGS.items()},
}

# 模块脚名/网络表里常见大写名 → main.ato 顶层 signal（小写）
NET_CANONICAL: dict[str, str] = {
    "VBAT_SW": "vbat_sw",
    "USB_DP": "usb_dp",
    "USB_DN": "usb_dn",
    "UART_TX": "uart_tx",
    "UART_RX": "uart_rx",
    "USB_VBUS": "vbus",
    "PWR_LATCH": "pwr_latch",
    "EN": "en",
    "BOOT": "boot_btn",
    "imu_vddio": "vcc",
}
# ===== 常量/配置 =====


# ===== 模型/类型 =====
def _parse_netlist(path: Path) -> dict[str, dict[str, str]]:
    """解析 ato 网络表，返回 {atopile_address → {pin_number → net_name}}。"""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # 第一遍：comp → ref → address
    ref_to_addr: dict[str, str] = {}
    current_ref: str | None = None

    for line in lines:
        m = re.search(r'\(comp\s+\(ref\s+"([^"]+)"\)', line)
        if m:
            current_ref = m.group(1)
            continue

        if current_ref:
            m2 = re.search(r'::([a-zA-Z_][\w.]*)"\)', line)
            if m2:
                addr = m2.group(1).rstrip(")")
                # 应用地址重映射
                addr = ADDR_REMAP.get(addr, addr)
                ref_to_addr[current_ref] = addr
                current_ref = None

    print(f"  解析到 {len(ref_to_addr)} 个 ref → address 映射")

    # 第二遍：nets → ref+pin → net
    result: dict[str, dict[str, str]] = {}
    current_net: str | None = None

    for line in lines:
        m = re.search(r'\(net\s+.*\(name\s+"([^"]+)"\)', line)
        if m:
            current_net = m.group(1)
            continue

        if current_net:
            m2 = re.search(r'\(node\s+\(ref\s+"([^"]+)"\)\s+\(pin\s+"([^"]+)"\)', line)
            if m2:
                ref, pin = m2.group(1), m2.group(2)
                if ref and ref != "":
                    addr = ref_to_addr.get(ref)
                    if addr:
                        result.setdefault(addr, {})[pin] = current_net

    print(f"  解析到 {len(result)} 个地址的网络分配")
    print(f"  总计 {sum(len(v) for v in result.values())} 个焊盘-网络关系")
    return result
# ===== 模型/类型 =====


# ===== 常量/配置 =====
TAIL_NET_ASSIGNMENTS = {
    "tail.conn": {
        "1": "sys_5v_in",
        "2": "gnd",
        "3": "sys_5v_sw",
        "4": "led_din",
        "5": "btn_sw",
        "6": "bat_cell_p",
        "7": "usb_dp",
        "8": "usb_dn",
        "9": "uart_tx",
        "10": "uart_rx",
    },
}


def _assign_tail_nets(board):
    """显式分配尾插焊盘网络（netlist 中 tail.*pad 与板上 footprint 命名不一致的 fallback）。"""
    import pcbnew

    assigned = 0
    for fp in board.GetFootprints():
        addr = ""
        if fp.HasFieldByName("atopile_address"):
            addr = fp.GetFieldByName("atopile_address").GetText()
        if addr not in TAIL_NET_ASSIGNMENTS:
            continue
        pin_nets = TAIL_NET_ASSIGNMENTS[addr]
        for pad in fp.Pads():
            pn = pad.GetNumber()
            if pn not in pin_nets:
                continue
            net_name = NET_CANONICAL.get(pin_nets[pn], pin_nets[pn])
            net = board.FindNet(net_name)
            if net is None:
                net = pcbnew.NETINFO_ITEM(board, net_name)
                board.Add(net)
            pad.SetNet(net)
            assigned += 1
    return assigned


def _merge_canonical_nets(board) -> int:
    """把历史大写/别名网并到 main.ato 小写 signal，避免尾插与 MCU 各占半截。"""
    import pcbnew

    def ensure(name: str):
        net = board.FindNet(name)
        if net is None:
            net = pcbnew.NETINFO_ITEM(board, name)
            board.Add(net)
        return net

    moved = 0
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            old = pad.GetNetname()
            if old in NET_CANONICAL:
                pad.SetNet(ensure(NET_CANONICAL[old]))
                moved += 1
    for item in board.GetTracks():
        old = item.GetNetname()
        if old in NET_CANONICAL:
            item.SetNet(ensure(NET_CANONICAL[old]))
            moved += 1
    for zone in board.Zones():
        old = zone.GetNetname()
        if old in NET_CANONICAL:
            zone.SetNet(ensure(NET_CANONICAL[old]))
            moved += 1
    return moved


# ===== 公开 API =====
def import_netlist(netlist_path: Path, board_path: Path):
    """导入网络表到 KiCad 板文件中。"""
    import pcbnew

    print(f"导入网络表: {netlist_path}")
    addr_nets = _parse_netlist(netlist_path)

    print(f"加载板文件: {board_path}")
    board = pcbnew.LoadBoard(str(board_path))

    matched = 0
    assigned = 0
    missed = 0

    # 构建板上 address → footprint 索引
    fp_by_addr: dict[str, object] = {}
    for fp in board.GetFootprints():
        if fp.HasFieldByName("atopile_address"):
            addr = fp.GetFieldByName("atopile_address").GetText()
            if addr:
                fp_by_addr[addr] = fp

    for addr, pin_nets in addr_nets.items():
        fp = fp_by_addr.get(addr)
        if not fp:
            # 打印未匹配的地址（前几个）
            if matched < 5:
                print(f"  ⚠ 板上未找到地址: {addr}")
            continue

        matched += 1
        pads = list(fp.Pads())
        sole_net = next(iter(pin_nets.values())) if len(pads) == 1 and len(pin_nets) == 1 else None
        for pad in pads:
            pad_num = pad.GetNumber()
            pad_pname = getattr(pad, "GetPinName", lambda: "")() or ""
            semantic_pin = MODULE_PIN_NAMES.get(addr, {}).get(pad_num, "")

            # 匹配 pin
            net_name = None
            if pad_num in pin_nets:
                net_name = pin_nets[pad_num]
            elif pad_pname in pin_nets:
                net_name = pin_nets[pad_pname]
            elif semantic_pin in pin_nets:
                net_name = pin_nets[semantic_pin]
            elif sole_net is not None:
                net_name = sole_net
            # Deliberately do not use substring matching here: pin "1" must
            # never silently match pin "10". Footprint/netlist mismatches are
            # reported via `missed` and fixed at their source.

            if net_name:
                net_name = NET_CANONICAL.get(net_name, net_name)
                net = board.FindNet(net_name)
                if net is None:
                    net = pcbnew.NETINFO_ITEM(board, net_name)
                    board.Add(net)
                pad.SetNet(net)
                assigned += 1
            else:
                missed += 1

    # 金手指 fallback（address 命名不一致）
    tail_n = _assign_tail_nets(board)
    if tail_n > 0:
        assigned += tail_n
        print(f"\n  尾插 fallback: 分配了 {tail_n} 个焊盘网络")

    # 合并历史大小写分裂网（模块脚名大写 vs 顶层 signal 小写）
    merged = _merge_canonical_nets(board)
    if merged:
        print(f"\n  规范网名合并: {merged} 个焊盘/走线")

    print(f"\n  匹配封装: {matched}/{len(addr_nets)}")
    print(f"  分配焊盘: {assigned}, 未匹配: {missed}")
    print(f"  创建网络: {board.GetNetCount() - 1}")  # 减掉默认 ""

    board.BuildListOfNets()
    board.SanitizeNetcodes()

    # 两次保存确保持久化
    board.Save(str(board_path))
    board.Save(str(board_path))
    print(f"  已保存: {board_path}")


def main():
    if not NETLIST_FILE.exists():
        print(f"错误: 网络表不存在 ({NETLIST_FILE})", file=sys.stderr)
        sys.exit(1)
    if not BOARD_FILE.exists():
        print(f"错误: 板文件不存在 ({BOARD_FILE})", file=sys.stderr)
        sys.exit(1)

    import_netlist(NETLIST_FILE, BOARD_FILE)


if __name__ == "__main__":
    main()
# ===== 公开 API =====
