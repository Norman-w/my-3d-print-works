#!/usr/bin/env python3
"""Export SmartPaddle PCB manufacturing files for JLCPCB/JLC ordering.

By default this script REFUSES to write an uploadable ZIP when gates fail.
Use --allow-errors only for local debug dumps (still prints FAIL).
"""

from __future__ import annotations

# ===== 分区：导入/依赖 =====
import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
DEFAULT_KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KICAD_PYTHON = (
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/"
    "Python.framework/Versions/Current/bin/python3"
)

# Intentional DRC error types that may remain if listed in board exclusions.
# Until exclusions are authored, copper_edge_clearance still counts as a gate failure
# unless --allow-intentional-castellation is set.
INTENTIONAL_DRC_TYPES = {"copper_edge_clearance"}

ORDER_NOTES = """\
SmartPaddle PCB manufacturing notes

Board
- PCB thickness: 0.8 mm
- Surface finish: ENIG (gold fingers + castellations)
- Delivery: this Gerber contains ONE main outline + TWO detached ~8x6.8 mm stiffener coupons
  (mill-gap separated). Treat as Different Design = 3 / Panel-by-Customer if your DFM requires it.
  Coupons are spare stiffeners, not a V-cut production panel of many copies.
  *** Confirm with JLCPCB/JLC that multi-outline / Different Design = 3 is accepted before pay. ***

Embedded modules
- IMU / MCU / PZT edge interfaces are intentional castellated / edge-solder structures.
- Edge.Cuts crossing PTH pads or edge pads in those areas is intentional.
- Please process IMU and PZT PTH edge pads as castellated / plated half-hole features.
- Please inspect the embedded MCU/ESP edge-pad cutout and confirm edge solderability.
- Confirm plated hole wall copper remains, no copper burrs, and no adjacent-pad shorts.

Tail gold fingers + F-side stiffener coupons (TAIL_STIFF_L / TAIL_STIFF_R)
- Main handle tip has 5 F-only SMD pads (TAIL_TIP) on F-side nets for stacking (NOT PTH).
- Two detached ~8x6.8 mm coupons outside handle side-walls (x=±8.7), mill-gap separated.
  Coupons are 1.2 mm shorter than the 8 mm gold fingers on the handle side so stacked H
  castellations land mid-finger; tip edge stays flush for TAIL_TIP soldering.
- *** MUST enable Castellated Holes / half-hole plating for coupon tip+handle PTH rows
  (hole centers lie on Edge.Cuts with outward scallops). Do not ship as full enclosed drills. ***
- After depaneling: stack one coupon onto main F fingers; do not discard coupons.

Power path (assembler note)
- Sole system input: charger-module **5V OUT** → gold-finger SYS_5V_IN → PMOS → SYS_5V_SW → AP2112.
- No USB/battery OR diodes (SS14 removed).
- IM948 powered from SYS_5V_SW on VBUS only; VBAT/VDDIO pads must remain open.
- Optional cell sense: wire charger B+ to BAT_CELL_P finger (not SYS_5V).
- Programming: use gold-finger USB D+/D− (charger Type-C usually has no data). Power board via charger 5V OUT while flashing.
"""


# ===== 分区：私有成员 =====
def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def summarize_drc(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    violations = data.get("violations", [])
    unconnected = data.get("unconnected_items", [])
    by_severity = Counter(item.get("severity", "?") for item in violations)
    by_type = Counter(item.get("type", "?") for item in violations)
    lines = [
        f"violations_total: {len(violations)}",
        f"unconnected_total: {len(unconnected)}",
        f"by_severity: {dict(sorted(by_severity.items()))}",
        f"by_type: {dict(sorted(by_type.items()))}",
    ]
    return "\n".join(lines) + "\n"


def _board_gates(board: Path) -> list[str]:
    """Return list of gate failure strings for refs / no-net copper."""
    script = r"""
import pcbnew, sys
from collections import Counter
board = pcbnew.LoadBoard(sys.argv[1])
fails = []
refs = [fp.GetReference() for fp in board.GetFootprints()]
c = Counter(refs)
if c.get('REF**', 0) or c.get('', 0):
    fails.append(f"REF**= {c.get('REF**',0)} empty={c.get('',0)}")
dups = [f"{r}x{n}" for r,n in c.items() if n>1 and r not in ('',)]
if dups:
    fails.append("duplicate_refs=" + ",".join(dups[:12]))
nn = sum(1 for t in board.GetTracks() if not (t.GetNetname() or ''))
if nn:
    fails.append(f"no_net_copper={nn}")
print("\n".join(fails))
"""
    proc = subprocess.run(
        [KICAD_PYTHON, "-c", script, str(board)],
        check=False,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "").strip()
    return [line for line in out.splitlines() if line.strip()]


def _drc_gates(drc_json: Path, allow_castellation: bool) -> list[str]:
    data = json.loads(drc_json.read_text(encoding="utf-8"))
    violations = data.get("violations", [])
    unconnected = data.get("unconnected_items", [])
    fails: list[str] = []
    errors = [v for v in violations if v.get("severity") == "error"]
    if allow_castellation:
        errors = [v for v in errors if v.get("type") not in INTENTIONAL_DRC_TYPES]
    if errors:
        by_type = Counter(v.get("type", "?") for v in errors)
        fails.append(f"drc_error={len(errors)} types={dict(by_type)}")
    if unconnected:
        fails.append(f"unconnected={len(unconnected)}")
    return fails


def _ato_build_ok() -> bool:
    script = ROOT / "pcb" / "scripts" / "ato_build_safe.sh"
    proc = subprocess.run(
        ["bash", str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    text = proc.stdout + proc.stderr
    ok = proc.returncode == 0 and "Build successful" in text
    if not ok:
        print(text[-2500:])
    return ok


# ===== 分区：公开 API =====
def main() -> int:
    parser = argparse.ArgumentParser(description="Export Gerber/drill/DRC for JLCPCB")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--kicad-cli", default=DEFAULT_KICAD_CLI)
    parser.add_argument("--keep-existing", action="store_true")
    parser.add_argument(
        "--allow-errors",
        action="store_true",
        help="Still write ZIP even if gates fail (debug only)",
    )
    parser.add_argument(
        "--allow-intentional-castellation",
        action="store_true",
        help="Ignore copper_edge_clearance errors (prefer real KiCad exclusions later)",
    )
    parser.add_argument(
        "--skip-ato-build-gate",
        action="store_true",
        help="Do not run ato build as a gate (use when exporting a frozen ECO board)",
    )
    args = parser.parse_args()

    if args.output is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        args.output = ROOT / "pcb" / "fab" / "jlcpcb" / stamp

    out = args.output
    gerbers = out / "gerbers"
    drill = out / "drill"
    reports = out / "reports"
    if out.exists() and not args.keep_existing:
        shutil.rmtree(out)
    gerbers.mkdir(parents=True, exist_ok=True)
    drill.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    gate_fails: list[str] = []
    gate_fails.extend(_board_gates(args.board))
    if not args.skip_ato_build_gate:
        if not _ato_build_ok():
            gate_fails.append("ato_build_failed")

    drc_json = reports / "drc.json"
    drc_report = reports / "drc.rpt"
    run(
        [
            args.kicad_cli,
            "pcb",
            "drc",
            "--format",
            "json",
            "--units",
            "mm",
            "--severity-all",
            "--output",
            str(drc_json),
            str(args.board),
        ]
    )
    run(
        [
            args.kicad_cli,
            "pcb",
            "drc",
            "--format",
            "report",
            "--units",
            "mm",
            "--severity-all",
            "--output",
            str(drc_report),
            str(args.board),
        ]
    )
    (reports / "drc_summary.txt").write_text(summarize_drc(drc_json), encoding="utf-8")
    gate_fails.extend(_drc_gates(drc_json, args.allow_intentional_castellation))

    (out / "ORDER_NOTES.txt").write_text(ORDER_NOTES, encoding="utf-8")
    (reports / "export_gates.txt").write_text(
        "\n".join(gate_fails) if gate_fails else "OK\n", encoding="utf-8"
    )

    if gate_fails and not args.allow_errors:
        print("EXPORT BLOCKED — gates failed:")
        for f in gate_fails:
            print(f"  - {f}")
        print(f"Reports kept under {reports} (no upload ZIP written).")
        print("Formal order packages remain disabled until gates are green.")
        return 1

    run(
        [
            args.kicad_cli,
            "pcb",
            "export",
            "gerbers",
            "--board-plot-params",
            "--output",
            str(gerbers),
            str(args.board),
        ]
    )
    run(
        [
            args.kicad_cli,
            "pcb",
            "export",
            "drill",
            "--output",
            str(drill),
            "--format",
            "excellon",
            "--excellon-units",
            "mm",
            "--generate-map",
            "--map-format",
            "pdf",
            str(args.board),
        ]
    )

    zip_path = out.parent / f"{out.name}_smartpaddle_jlcpcb.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", out)
    if gate_fails:
        print("WARNING: ZIP written with --allow-errors; DO NOT ORDER:")
        for f in gate_fails:
            print(f"  - {f}")
    print(f"Export complete: {out}")
    print(f"Upload archive: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
