#!/usr/bin/env python3
"""Step 5 — Route all signal nets on the rigid PCB using kicad_tools autorouter.

Power nets (gnd, vcc, VBAT_SW, VBUS, vbat_in, PWR_LATCH) are skipped —
they will be handled with copper pours (zones).

The router uses:
- board outline from Edge.Cuts (with 0.5mm edge clearance)
- design rules parsed from the PCB file setup section
- Manhattan routing with pure-Python fallback when C++ backend unavailable
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import sys
from pathlib import Path

# Use the kicad-tools MCP Python packages
MCP_VENV = Path.home() / ".local" / "mcp-venvs" / "kicad-tools" / "lib" / "python3.13" / "site-packages"
sys.path.insert(0, str(MCP_VENV))

# ===== 分区：常量/配置 =====
BOARD_PATH = Path(__file__).resolve().parents[1] / "layouts" / "default" / "default.kicad_pcb"
POWER_NETS = {"gnd", "vcc", "VBAT_SW", "VBUS", "vbat_in", "PWR_LATCH"}

# ===== 分区：方法/工具 =====


def route_board(pcb_path: Path) -> dict:
    from kicad_tools.schema.pcb import PCB
    from kicad_tools.router.io import load_pcb_for_routing, merge_routes_into_pcb

    pcb = PCB.load(str(pcb_path))

    # ---- Discover nets ----
    signal_nets = []
    for num, net in pcb.nets.items():
        if not net.name or net.name.startswith("N-"):
            continue
        if net.name in POWER_NETS:
            continue
        pad_count = sum(
            1 for fp in pcb.footprints
            for pad in fp.pads
            if pad.net_number == num
        )
        if pad_count >= 2:
            signal_nets.append((num, net.name, pad_count))

    print(f"信号网: {len(signal_nets)} ({', '.join(n for _,n,_ in signal_nets)})")
    print(f"跳过电源网: {POWER_NETS}")

    # ---- Route all at once ----
    router, _netmap = load_pcb_for_routing(
        str(pcb_path),
        skip_nets=list(POWER_NETS),
        use_pcb_rules=True,
        edge_clearance=0.5,
    )

    all_routes = []
    for net_num, name, pad_count in signal_nets:
        routes = router.route_net(net_num)
        if routes:
            all_routes.extend(routes)
            length = sum(
                ((s.x2 - s.x1)**2 + (s.y2 - s.y1)**2)**0.5
                for r in routes for s in r.segments
            )
            print(f"  OK  {name}: {pad_count} pads, {length:.1f}mm, {len(routes)} segments")
        else:
            print(f"  FAIL {name}: no routes")

    # ---- Merge all routes into PCB ----
    route_sexp = "\n".join(r.to_sexp() for r in all_routes)
    pcb_text = pcb_path.read_text()
    merged = merge_routes_into_pcb(pcb_text, route_sexp)

    # Save routed PCB (overwrite)
    pcb_path.write_text(merged)

    total_len = sum(
        ((s.x2 - s.x1)**2 + (s.y2 - s.y1)**2)**0.5
        for r in all_routes for s in r.segments
    )
    return {
        "routed_nets": len([n for n,_,_ in signal_nets]),
        "segments": sum(len(r.segments) for r in all_routes),
        "vias": sum(len(r.vias) for r in all_routes),
        "total_length_mm": total_len,
    }


def main() -> None:
    stats = route_board(BOARD_PATH)
    print(f"\n布线完成: {stats['routed_nets']} nets, "
          f"{stats['segments']} segments, "
          f"{stats['vias']} vias, "
          f"{stats['total_length_mm']:.0f}mm")


if __name__ == "__main__":
    main()
