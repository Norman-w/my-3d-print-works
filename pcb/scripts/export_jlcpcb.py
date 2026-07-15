#!/usr/bin/env python3
"""Export SmartPaddle PCB manufacturing files for JLCPCB/JLC ordering."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"
DEFAULT_KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

ORDER_NOTES = """\
SmartPaddle PCB manufacturing notes

Board
- PCB thickness: 0.8 mm
- Surface finish: ENIG (gold fingers + castellations)

Embedded modules
- IMU / MCU / PZT edge interfaces are intentional castellated / edge-solder structures.
- Edge.Cuts crossing PTH pads or edge pads in those areas is intentional.
- Please process IMU and PZT PTH edge pads as castellated / plated half-hole features.
- Please inspect the embedded MCU/ESP edge-pad cutout and confirm edge solderability.
- Confirm plated hole wall copper remains, no copper burrs, and no adjacent-pad shorts.

Tail gold fingers + F-side stiffener coupons (TAIL_STIFF_L / TAIL_STIFF_R)
- Main handle tip has 5 plated castellations (TAIL_TIP) on F-side nets (pads on step2 tip edge).
- Two detached 8x8 mm coupons outside handle side-walls (x=±8.7), mill-gap separated (no shared Edge.Cuts).
- step4.4 never edits the main substrate outline from step2; if outline was damaged, re-run step2→step3 first.
- Coupon edges: Edge.Cuts semicircle scallops at tip/handle (castellation cut contour).
- After depaneling: stack one coupon onto main F fingers (fingers face up), solder tip castellations
  aligned to TAIL_TIP, and solder handle castellations onto the original F gold-finger pads.
- Goal: local thickness ~1.6 mm for the existing edge connector; B-side fingers stay on the main board.
- Do not tin-bridge adjacent 1.27 mm fingers.
"""


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Gerber, drill, DRC, and order notes for JLCPCB")
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--kicad-cli", default=DEFAULT_KICAD_CLI)
    parser.add_argument("--keep-existing", action="store_true", help="Do not remove an existing output directory")
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

    drc_json = reports / "drc.json"
    drc_report = reports / "drc.rpt"
    run([args.kicad_cli, "pcb", "drc", "--format", "json", "--units", "mm", "--severity-all", "--output", str(drc_json), str(args.board)])
    run([args.kicad_cli, "pcb", "drc", "--format", "report", "--units", "mm", "--severity-all", "--output", str(drc_report), str(args.board)])
    (reports / "drc_summary.txt").write_text(summarize_drc(drc_json), encoding="utf-8")

    run([args.kicad_cli, "pcb", "export", "gerbers", "--board-plot-params", "--output", str(gerbers), str(args.board)])
    run([
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
    ])

    (out / "ORDER_NOTES.txt").write_text(ORDER_NOTES, encoding="utf-8")
    zip_base = out / "smartpaddle_jlcpcb"
    shutil.make_archive(str(zip_base), "zip", out)
    print(f"Export complete: {out}")
    print(f"Upload archive: {zip_base.with_suffix('.zip')}")


if __name__ == "__main__":
    main()
