#!/usr/bin/env python3
"""Step 3.2: validate a freshly generated C4 atopile netlist and apply it.

The project has used more than one atopile build-output layout, so this step
does not assume ``pcb/build/default.net``.  It finds the newest
``default.net`` below ``pcb/build`` and refuses to use it when it predates the
C4 electrical sources.

Before touching KiCad, the importer verifies all 63 physical component
addresses and the complete expected pad connectivity topology.  This rejects
the checked-in C3 history netlist and prevents an old ESP32-C6 build from being
applied to the C4 ESP32-S3 handoff board.  Applying nets is allowed only while
the board still has no tracks, vias, or non-rule copper zones.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PCB_ROOT = PROJECT_ROOT / "pcb"
SCRIPTS = PCB_ROOT / "scripts"
sys.path.insert(0, str(PCB_ROOT))
sys.path.insert(0, str(SCRIPTS))

from lib.esp32s3wroom1.pinmap import PROJECT_BINDINGS
from migrate_c3_to_c4_unrouted import DNP_ADDRESSES, PAD_NETS, _addr, _source_guard


BUILD_DIR = PCB_ROOT / "build"
BOARD_FILE = PCB_ROOT / "layouts" / "default" / "default.kicad_pcb"
SOURCE_FILES = (
    PCB_ROOT / "ato.yaml",
    PCB_ROOT / "main.ato",
    PCB_ROOT / "parts.ato",
    PCB_ROOT / "lib" / "esp32s3wroom1" / "pinmap.py",
)


# Older source revisions used a few flat addresses.  Keeping the remap makes
# the parser diagnostic useful for those files, but the C4 identity gate still
# requires the complete current address set before any board can be changed.
ADDR_REMAP: dict[str, str] = {
    "bat_r_top": "battery.r_top",
    "bat_r_bottom": "battery.r_bottom",
    "bat_c_filter": "battery.c_filter",
}


# Module netlists may describe the same physical pin by both pad number and
# semantic pin name.  All other C4 footprints use numeric pin identifiers.
MODULE_PIN_NAMES: dict[str, dict[str, str]] = {
    "imu": {
        "1": "GND_1", "2": "VBUS", "3": "VBAT_3", "4": "VDDIO",
        "7": "ADIN", "8": "GND_8", "9": "LED_B", "10": "LED_R",
        "11": "GPIO", "12": "KEY", "13": "RXD", "14": "TXD",
        "15": "VBAT_15", "16": "GND_16",
    },
    "mcu": {str(pad): name for pad, name in PROJECT_BINDINGS.items()},
}


def _paren_delta(line: str) -> int:
    """Count structural parentheses while ignoring quoted strings."""
    scrubbed = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
    return scrubbed.count("(") - scrubbed.count(")")


def _component_addresses(lines: list[str]) -> dict[str, str]:
    ref_to_addr: dict[str, str] = {}
    depth = 0
    comp_depth: int | None = None
    property_depth: int | None = None
    current_ref: str | None = None
    current_addr: str | None = None
    property_name: str | None = None
    property_value: str | None = None

    for line in lines:
        stripped = line.strip()
        after = depth + _paren_delta(line)

        if comp_depth is None and re.match(r"^\(comp(?:\s|$)", stripped):
            comp_depth = after
            current_ref = None
            current_addr = None

        if comp_depth is not None:
            match = re.match(r'^\(ref\s+"([^"]+)"\)', stripped)
            if match and property_depth is None:
                current_ref = match.group(1)

            if property_depth is None and re.match(r"^\(property(?:\s|$)", stripped):
                property_depth = after
                property_name = None
                property_value = None
            elif property_depth is not None:
                name_match = re.match(r'^\(name\s+"([^"]+)"\)', stripped)
                value_match = re.match(r'^\(value\s+"([^"]*)"\)', stripped)
                if name_match:
                    property_name = name_match.group(1)
                if value_match:
                    property_value = value_match.group(1)

            # Legacy atopile exports encoded the address in sheetpath/tstamp
            # text rather than an explicit property.
            legacy = re.search(r"::([a-zA-Z_][\w.]*)", line)
            if legacy:
                current_addr = legacy.group(1).rstrip(")")

        depth = after

        if property_depth is not None and depth < property_depth:
            if property_name == "atopile_address" and property_value:
                current_addr = property_value
            property_depth = None
            property_name = None
            property_value = None

        if comp_depth is not None and depth < comp_depth:
            if current_ref and current_addr:
                address = ADDR_REMAP.get(current_addr, current_addr)
                if current_ref in ref_to_addr and ref_to_addr[current_ref] != address:
                    raise ValueError(f"component {current_ref} has conflicting addresses")
                ref_to_addr[current_ref] = address
            comp_depth = None
            current_ref = None
            current_addr = None

    refs_by_address: dict[str, list[str]] = defaultdict(list)
    for ref, address in ref_to_addr.items():
        refs_by_address[address].append(ref)
    duplicates = {
        address: refs for address, refs in refs_by_address.items() if len(refs) > 1
    }
    if duplicates:
        raise ValueError(f"multiple refs claim the same atopile_address: {duplicates}")
    return ref_to_addr


def _net_nodes(lines: list[str], ref_to_addr: dict[str, str]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    depth = 0
    net_depth: int | None = None
    node_depth: int | None = None
    current_net: str | None = None
    node_ref: str | None = None
    node_pin: str | None = None

    for line in lines:
        stripped = line.strip()
        after = depth + _paren_delta(line)

        if net_depth is None and re.match(r"^\(net(?:\s|$)", stripped):
            net_depth = after
            current_net = None

        if net_depth is not None:
            if node_depth is None:
                name_match = re.match(r'^\(name\s+"([^"]+)"\)', stripped)
                if name_match:
                    current_net = name_match.group(1)

                if re.match(r"^\(node(?:\s|$)", stripped):
                    node_depth = after
                    node_ref = None
                    node_pin = None
            else:
                ref_match = re.match(r'^\(ref\s+"([^"]+)"\)', stripped)
                pin_match = re.match(r'^\(pin\s+"([^"]+)"\)', stripped)
                if ref_match:
                    node_ref = ref_match.group(1)
                if pin_match:
                    node_pin = pin_match.group(1)

        depth = after

        if node_depth is not None and depth < node_depth:
            if current_net and node_ref and node_pin:
                address = ref_to_addr.get(node_ref)
                if address is None:
                    raise ValueError(
                        f"net {current_net!r} references {node_ref}.pin{node_pin} "
                        "without an atopile_address"
                    )
                pins = result.setdefault(address, {})
                previous = pins.get(node_pin)
                if previous is not None and previous != current_net:
                    raise ValueError(
                        f"{address}.pin{node_pin} appears on both {previous!r} and {current_net!r}"
                    )
                pins[node_pin] = current_net
            node_depth = None
            node_ref = None
            node_pin = None

        if net_depth is not None and depth < net_depth:
            net_depth = None
            current_net = None

    return result


def _parse_netlist_text(text: str) -> dict[str, dict[str, str]]:
    lines = text.splitlines()
    ref_to_addr = _component_addresses(lines)
    result = _net_nodes(lines, ref_to_addr)
    print(f"  解析到 {len(ref_to_addr)} 个 ref → address 映射")
    print(f"  解析到 {len(result)} 个地址的网络分配")
    print(f"  总计 {sum(len(pins) for pins in result.values())} 个引脚-网络关系")
    return result


def _parse_netlist(path: Path) -> dict[str, dict[str, str]]:
    """Return ``{atopile_address: {pin_identifier: generated_net}}``."""
    return _parse_netlist_text(path.read_text(encoding="utf-8"))


def _resolve_netlist(explicit: Path | None) -> Path:
    if explicit is not None:
        candidates = [explicit.resolve()]
    else:
        candidates = sorted(BUILD_DIR.rglob("default.net")) if BUILD_DIR.is_dir() else []
    existing = [path for path in candidates if path.is_file()]
    if not existing:
        requested = explicit if explicit is not None else BUILD_DIR / "**" / "default.net"
        raise FileNotFoundError(f"网络表不存在: {requested}")

    newest = max(existing, key=lambda path: path.stat().st_mtime_ns)
    newest_source = max(SOURCE_FILES, key=lambda path: path.stat().st_mtime_ns)
    if newest.stat().st_mtime_ns < newest_source.stat().st_mtime_ns:
        raise RuntimeError(
            "拒绝旧网表："
            f"{newest} 早于 C4 源文件 {newest_source}；请先通过项目 Step 3.1 生成"
        )
    return newest


def _actual_net_for_pad(
    addr_nets: dict[str, dict[str, str]], addr: str, pad_number: str
) -> set[str]:
    identifiers = {pad_number}
    semantic = MODULE_PIN_NAMES.get(addr, {}).get(pad_number)
    if semantic:
        identifiers.add(semantic)
    pins = addr_nets.get(addr, {})
    return {pins[identifier] for identifier in identifiers if identifier in pins}


def _canonical_pad(addr: str, identifier: str) -> str | None:
    if identifier in PAD_NETS.get(addr, {}):
        return identifier
    for pad_number, semantic in MODULE_PIN_NAMES.get(addr, {}).items():
        if identifier == semantic:
            return pad_number
    return None


def _validate_c4_topology(addr_nets: dict[str, dict[str, str]]) -> None:
    errors: list[str] = []
    expected_addresses = set(PAD_NETS)
    actual_addresses = set(addr_nets)
    missing = sorted(expected_addresses - actual_addresses)
    unexpected = sorted(actual_addresses - expected_addresses)
    if missing:
        errors.append(f"缺少 C4 地址 ({len(missing)}): {missing}")
    if unexpected:
        errors.append(f"出现非 C4 地址 ({len(unexpected)}): {unexpected}")

    generated_endpoints: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for addr, pins in addr_nets.items():
        for identifier, generated_net in pins.items():
            canonical = _canonical_pad(addr, identifier)
            if canonical is None:
                errors.append(
                    f"{addr} 出现未受审 pin identifier {identifier!r} "
                    f"(生成网 {generated_net!r})"
                )
                continue
            generated_endpoints[generated_net].add((addr, canonical))

    expected_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    endpoint_actual: dict[tuple[str, str], str] = {}
    for addr, pad_nets in PAD_NETS.items():
        for pad_number, expected_net in pad_nets.items():
            actual_nets = _actual_net_for_pad(addr_nets, addr, pad_number)
            if not expected_net:
                external_nets = {
                    generated_net
                    for generated_net in actual_nets
                    if generated_endpoints[generated_net] - {(addr, pad_number)}
                }
                if external_nets:
                    errors.append(
                        f"{addr}.pad{pad_number} 应悬空，却连接生成网 "
                        f"{sorted(external_nets)}"
                    )
                continue
            expected_groups[expected_net].append((addr, pad_number))
            if not actual_nets:
                errors.append(f"{addr}.pad{pad_number} 缺少生成网络")
                continue
            if len(actual_nets) != 1:
                errors.append(
                    f"{addr}.pad{pad_number} 同时落在多个生成网: {sorted(actual_nets)}"
                )
                continue
            endpoint_actual[(addr, pad_number)] = next(iter(actual_nets))

    generated_to_expected: dict[str, set[str]] = defaultdict(set)
    for expected_net, endpoints in expected_groups.items():
        generated = {
            endpoint_actual[endpoint]
            for endpoint in endpoints
            if endpoint in endpoint_actual
        }
        if len(generated) > 1:
            errors.append(
                f"期望网 {expected_net!r} 被生成器拆成 {sorted(generated)}"
            )
        for generated_net in generated:
            generated_to_expected[generated_net].add(expected_net)

    for generated_net, expected in sorted(generated_to_expected.items()):
        if len(expected) > 1:
            errors.append(
                f"生成网 {generated_net!r} 错误合并期望网络 {sorted(expected)}"
            )

    if errors:
        preview = "\n  - ".join(errors[:30])
        suffix = f"\n  ... 另有 {len(errors) - 30} 项" if len(errors) > 30 else ""
        raise ValueError(f"C4 atopile 网表门禁失败:\n  - {preview}{suffix}")

    print(
        "  C4 拓扑门禁通过: "
        f"{len(expected_addresses)} 个地址, "
        f"{sum(bool(net) for pins in PAD_NETS.values() for net in pins.values())} 个已连接焊盘号"
    )


def _ensure_net(board, pcbnew, name: str):
    if not name or name != name.lower():
        raise ValueError(f"板上网名必须为非空小写，收到 {name!r}")
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def import_netlist(netlist_path: Path, board_path: Path, check_only: bool = False) -> None:
    """Validate generated topology, then apply reviewed C4 board net names."""
    print(f"检查网表: {netlist_path}")
    addr_nets = _parse_netlist(netlist_path)
    _validate_c4_topology(addr_nets)
    if check_only:
        print("  仅检查：未修改 KiCad 板")
        return

    import pcbnew

    print(f"加载板文件: {board_path}")
    board = pcbnew.LoadBoard(str(board_path))
    tracks = list(board.GetTracks())
    copper_zones = [
        board.GetArea(index)
        for index in range(board.GetAreaCount())
        if not board.GetArea(index).GetIsRuleArea()
    ]
    if tracks or copper_zones:
        raise RuntimeError(
            "Step 3.2 只允许写入无布线交接板；"
            f"当前有 {len(tracks)} tracks/vias、{len(copper_zones)} copper zones"
        )

    fp_by_addr = {_addr(fp): fp for fp in board.GetFootprints() if _addr(fp)}
    missing_board_addresses = sorted(set(PAD_NETS) - set(fp_by_addr))
    unexpected_board_addresses = sorted(set(fp_by_addr) - set(PAD_NETS))
    if missing_board_addresses or unexpected_board_addresses:
        raise RuntimeError(
            "KiCad C4 地址集不匹配: "
            f"missing={missing_board_addresses}, unexpected={unexpected_board_addresses}"
        )

    assigned = 0
    cleared = 0
    for addr, expected_pads in PAD_NETS.items():
        fp = fp_by_addr[addr]
        actual_pads: dict[str, list] = defaultdict(list)
        for pad in fp.Pads():
            actual_pads[pad.GetNumber()].append(pad)
        if set(actual_pads) != set(expected_pads):
            raise RuntimeError(
                f"{addr} pad 集不匹配: expected={sorted(expected_pads)}, "
                f"actual={sorted(actual_pads)}"
            )
        for pad_number, expected_net in expected_pads.items():
            for pad in actual_pads[pad_number]:
                if expected_net:
                    pad.SetNet(_ensure_net(board, pcbnew, expected_net))
                    assigned += 1
                else:
                    pad.SetNetCode(0)
                    cleared += 1
        if addr in DNP_ADDRESSES:
            fp.SetDNP(True)

    board.BuildListOfNets()
    board.SanitizeNetcodes()
    board.Save(str(board_path))
    print(f"  已保存: {board_path}")
    print(f"  分配 {assigned} 个焊盘，明确清空 {cleared} 个 DNP/NC/未用焊盘")


def main() -> int:
    parser = argparse.ArgumentParser(description="Step 3.2: C4 atopile netlist gate/import")
    parser.add_argument("--netlist", type=Path, default=None)
    parser.add_argument("--board", type=Path, default=BOARD_FILE)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    _source_guard()
    try:
        netlist = _resolve_netlist(args.netlist)
        if not args.board.is_file():
            raise FileNotFoundError(f"板文件不存在: {args.board}")
        import_netlist(netlist, args.board.resolve(), args.check_only)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
