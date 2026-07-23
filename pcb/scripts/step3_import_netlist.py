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

# 板上网名 = main.ato 顶层 signal，必须已是小写。不做别名、不做自动改写。
# ===== 常量/配置 =====


# ===== 模型/类型 =====
def _board_net_name(name: str) -> str:
    """校验网名：必须小写，与 main.ato signal 一致。"""
    name = name.strip()
    if not name:
        raise ValueError("空网名")
    if name != name.lower():
        raise ValueError(
            f"网名必须小写（与 main.ato signal 一致），收到: {name!r}"
        )
    return name


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
    "tail.conn_f": {
        "1": "sys_5v_in",
        "2": "sys_5v_sw",
        "3": "btn_sw",
        "4": "usb_dp",
        "5": "uart_tx",
    },
    "tail.conn_b": {
        "1": "gnd",
        "2": "led_din",
        "3": "bat_cell_p",
        "4": "usb_dn",
        "5": "uart_rx",
    },
}


def _ensure_net(board, pcbnew, name: str):
    name = _board_net_name(name)
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


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
            pad.SetNet(_ensure_net(board, pcbnew, pin_nets[pn]))
            assigned += 1
    return assigned


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

            net_name = None
            if pad_num in pin_nets:
                net_name = pin_nets[pad_num]
            elif pad_pname in pin_nets:
                net_name = pin_nets[pad_pname]
            elif semantic_pin in pin_nets:
                net_name = pin_nets[semantic_pin]
            elif sole_net is not None:
                net_name = sole_net

            if net_name:
                pad.SetNet(_ensure_net(board, pcbnew, net_name))
                assigned += 1
            else:
                missed += 1

    tail_n = _assign_tail_nets(board)
    if tail_n > 0:
        assigned += tail_n
        print(f"\n  尾插 fallback: 分配了 {tail_n} 个焊盘网络")

    print(f"\n  匹配封装: {matched}/{len(addr_nets)}")
    print(f"  分配焊盘: {assigned}, 未匹配: {missed}")
    print(f"  创建网络: {board.GetNetCount() - 1}")

    board.BuildListOfNets()
    board.SanitizeNetcodes()

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
