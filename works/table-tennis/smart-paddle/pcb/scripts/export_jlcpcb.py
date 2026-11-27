#!/usr/bin/env python3
"""Export SmartPaddle PCB manufacturing files for JLCPCB/JLC ordering.

By default this script REFUSES to write an uploadable ZIP when gates fail.
Use --allow-errors only for local debug dumps (still prints FAIL).
"""

from __future__ import annotations

# ===== 分区：导入/依赖 =====
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
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
POWER_REWORK_GATE = ROOT / "scripts" / "validate_power_rework.py"

ORDER_NOTES = """\
SmartPaddle main PCB — manufacturing notes

Board
- Thickness 0.8 mm, 2 layers, ENIG
- Confirm the title/revision shown in the fabrication drawing matches the current PCB
- Single outline; flat tail; MX1.25 5P x2 (Molex 53261-0571), hand-solder
- Programming: USB D+/D− on tail MX1.25; power via charger 5V OUT → sys_5v_in
- JP_ADC_TL/TR/BL/BR are DNP

Embedded MCU / IMU routed cutouts
- Internal Edge.Cuts through host PTH centers are intentional; do not move holes or slots
- These are internal routed PTH edges, not ordinary outer-board castellations
- If internal castellations are unavailable, prototype ordinary routing is acceptable
  (burrs / exposed copper / incomplete hole walls accepted). Contact before process change/upcharge.
- ESP32-S3 EP41 has no host land; assembly bonds perimeter GND pads 1 and 40

Outline internal corners
- Do NOT straighten outline; add corner holes (工艺角孔) at sharp re-entrant corners,
  then proceed without further confirmation.

Suggested JLCPCB remark (CN):
SmartPaddle 主板工程样板，按Gerber生产。MCU/IMU内部槽边故意穿过PTH中心，不要移动孔或修改开窗；若无法做内部半孔，可按普通锣槽生产，接受毛刺、露铜和孔壁不完整。无需自动升级加价工艺，如需改外形或加价请先联系。四臂与码头交接的内凹尖角请勿拉直，可按贵司工艺加角孔。0.8mm、2层、沉金、单板，不是拼板。
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
    """Return current main-board identity, metadata, routing and copper failures.

    Exact source/footprint/pad semantics are checked by the cross-layer power
    audit.  This local check deliberately contains no legacy C3 migration map.
    """
    script = r"""
import sys
import pcbnew
from collections import Counter
board = pcbnew.LoadBoard(sys.argv[1])
fails = []
fps = list(board.GetFootprints())
if len(fps) != 67:
    fails.append(f"footprint_count={len(fps)} expected=67")
refs = [fp.GetReference() for fp in fps]
c = Counter(refs)
if c.get('REF**', 0) or c.get('', 0):
    fails.append(f"REF**= {c.get('REF**',0)} empty={c.get('',0)}")
dups = [f"{r}x{n}" for r,n in c.items() if n>1 and r not in ('',)]
if dups:
    fails.append("duplicate_refs=" + ",".join(dups[:12]))
addresses = []
for fp in fps:
    if not fp.HasFieldByName('atopile_address'):
        fails.append(f"missing_atopile_address={fp.GetReference()}")
        continue
    address = fp.GetFieldByName('atopile_address').GetText()
    if not address:
        fails.append(f"empty_atopile_address={fp.GetReference()}")
    addresses.append(address)
address_counts = Counter(addresses)
duplicate_addresses = [f"{a}x{n}" for a,n in address_counts.items() if n > 1]
if duplicate_addresses:
    fails.append("duplicate_atopile_addresses=" + ",".join(duplicate_addresses[:12]))
title = board.GetTitleBlock().GetTitle()
revision = board.GetTitleBlock().GetRevision()
if title != 'SmartPaddle Main PCB' or not revision:
    fails.append(f"title_block title={title!r} revision={revision!r}")
legacy = [fp.GetReference() for fp in fps if 'ESP32-C6' in (fp.GetValue() + ' ' + fp.GetFPIDAsString())]
if legacy:
    fails.append("legacy_c6=" + ",".join(legacy))
tracks = list(board.GetTracks())
if not tracks:
    fails.append("routing_items=0")
copper_zones = [board.GetArea(i) for i in range(board.GetAreaCount())
                if not board.GetArea(i).GetIsRuleArea()]
if not copper_zones:
    fails.append("copper_zones=0")
elif not any((zone.GetNetname() or '') == 'gnd' for zone in copper_zones):
    fails.append("gnd_copper_zone=0")
if board.GetCopperLayerCount() != 2:
    fails.append(f"copper_layers={board.GetCopperLayerCount()} expected=2")
thickness_mm = pcbnew.ToMM(board.GetDesignSettings().GetBoardThickness())
if abs(thickness_mm - 0.8) > 0.001:
    fails.append(f"board_thickness_mm={thickness_mm:.6f} expected=0.8")
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
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "no diagnostic output").strip()
        return [f"board_gate_executor_failed rc={proc.returncode}: {detail[-500:]}"]
    out = (proc.stdout or "").strip()
    return [line for line in out.splitlines() if line.strip()]


def _power_rework_gate_ok() -> bool:
    proc = subprocess.run(
        [sys.executable, str(POWER_REWORK_GATE), "--release-gate"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "no diagnostic output").strip()
        print(detail)
        return False
    return True


def _drc_gates(drc_json: Path) -> list[str]:
    data = json.loads(drc_json.read_text(encoding="utf-8"))
    violations = data.get("violations", [])
    unconnected = data.get("unconnected_items", [])
    fails: list[str] = []
    errors = [v for v in violations if v.get("severity") == "error"]
    if errors:
        by_type = Counter(v.get("type", "?") for v in errors)
        fails.append(f"drc_error={len(errors)} types={dict(by_type)}")
    if unconnected:
        fails.append(f"unconnected={len(unconnected)}")
    return fails


def _write_shifted_fab_copy(source: Path, destination: Path) -> None:
    """Write a drawing-only copy translated into the printable A4 area."""
    script = r"""
import pcbnew, sys
source, destination = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(source)
box = board.GetBoardEdgesBoundingBox()
left = pcbnew.ToMM(box.GetLeft())
top = pcbnew.ToMM(box.GetTop())
# Keep 18 mm inside the A4 drawing border.  The entire board and the
# outboard Cmts.User note block move together; Gerber source is untouched.
board.Move(pcbnew.VECTOR2I_MM(18.0 - left, 18.0 - top))
board.Save(destination)
print(f"fab drawing translation: dx={18.0-left:.3f} dy={18.0-top:.3f} mm")
"""
    run([KICAD_PYTHON, "-c", script, str(source), str(destination)])


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
        help="Write local Gerber/drill debug dumps when gates fail; never writes a ZIP",
    )
    parser.add_argument(
        "--allow-intentional-castellation",
        action="store_true",
        help="Deprecated and refused; local .kicad_dru rules must yield zero DRC errors",
    )
    parser.add_argument(
        "--skip-netlist-gate",
        "--skip-ato-build-gate",
        dest="skip_netlist_gate",
        action="store_true",
        help="Deprecated diagnostic flag; requesting it forces manufacturing refusal",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Write reports and fabrication drawing only; never Gerber, drill or ZIP",
    )
    parser.add_argument(
        "--smt",
        action="store_true",
        help="Also export partial JLCPCB SMT BOM/CPL (excludes modules/tail/PZT pads/THT/DNP)",
    )
    parser.add_argument(
        "--smt-require-lcsc",
        action="store_true",
        help="With --smt, drop candidates that lack an LCSC C-number in smt_parts_map.yaml",
    )
    args = parser.parse_args()

    if args.output is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        args.output = ROOT / "pcb" / "fab" / "jlcpcb" / stamp

    out = args.output
    gerbers = out / "gerbers"
    drill = out / "drill"
    reports = out / "reports"
    if out.exists() and any(out.iterdir()) and not args.keep_existing:
        print(f"Output directory is not empty; refusing to delete it: {out}")
        print("Choose a new --output path or pass --keep-existing deliberately.")
        return 2

    gate_fails: list[str] = []
    gate_fails.extend(_board_gates(args.board))
    if not _power_rework_gate_ok():
        gate_fails.append("cross_layer_power_rework_release_gate_failed")
    if args.allow_intentional_castellation:
        gate_fails.append("deprecated_castellation_override_requested")
    if args.skip_netlist_gate:
        gate_fails.append("deprecated_netlist_gate_override_requested")

    # Normal manufacturing mode is fail-closed before creating even an output
    # directory.  Explicit preflight/debug modes may retain diagnostic files,
    # but can never write an upload ZIP while a gate is red.
    if gate_fails and not args.preflight_only and not args.allow_errors:
        print("EXPORT REFUSED BEFORE OUTPUT CREATION — gates failed:")
        for failure in gate_fails:
            print(f"  - {failure}")
        return 2

    gerbers.mkdir(parents=True, exist_ok=True)
    drill.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    board_sha = hashlib.sha256(args.board.read_bytes()).hexdigest()

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
    gate_fails.extend(_drc_gates(drc_json))

    (out / "ORDER_NOTES.txt").write_text(ORDER_NOTES, encoding="utf-8")
    (reports / "export_gates.txt").write_text(
        ("\n".join(gate_fails) + "\n") if gate_fails else "OK\n",
        encoding="utf-8",
    )

    fab_drawing = out / "main_fabrication_drawing.pdf"
    shifted_fab_dir = reports / "_fab_drawing_source"
    shifted_fab_dir.mkdir(parents=True, exist_ok=True)
    # Keep the original basename so the PDF title block identifies the real
    # design file rather than exposing an implementation-only temp filename.
    shifted_fab_board = shifted_fab_dir / args.board.name
    _write_shifted_fab_copy(args.board, shifted_fab_board)
    try:
        run(
            [
                args.kicad_cli,
                "pcb",
                "export",
                "pdf",
                "--layers",
                "F.Fab,Cmts.User,Edge.Cuts",
                "--include-border-title",
                "--sketch-pads-on-fab-layers",
                "--crossout-DNP-footprints-on-fab-layers",
                "--mode-single",
                "--output",
                str(fab_drawing),
                str(shifted_fab_board),
            ]
        )
    finally:
        shutil.rmtree(shifted_fab_dir, ignore_errors=True)
    board_sha_after_preflight = hashlib.sha256(args.board.read_bytes()).hexdigest()
    if board_sha_after_preflight != board_sha:
        gate_fails.append(
            "board_changed_during_preflight "
            f"before={board_sha} after={board_sha_after_preflight}"
        )
        (reports / "export_gates.txt").write_text(
            "\n".join(gate_fails) + "\n", encoding="utf-8"
        )
    manifest = {
        "schema_version": 1,
        "board": str(args.board.resolve()),
        "board_sha256": board_sha,
        "preflight_only": bool(args.preflight_only),
        "netlist_gate_skipped": bool(args.skip_netlist_gate),
        "gate_failures": gate_fails,
        "production_ready": not gate_fails,
        "upload_archive_written": False,
        "fabrication_drawing": str(fab_drawing),
        "fabrication_drawing_note": (
            "View translated to fit A4; source Gerber/drill coordinates are unchanged"
        ),
    }
    (reports / "manufacturing_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    def _maybe_export_smt() -> None:
        if not args.smt:
            return
        smt_script = Path(__file__).resolve().parent / "export_jlc_smt.py"
        cmd = [
            KICAD_PYTHON,
            str(smt_script),
            "--board",
            str(args.board.resolve()),
            "--output",
            str(out.resolve()),
            "--parts-map",
            str(ROOT / "pcb" / "jlcpcb" / "smt_parts_map.yaml"),
        ]
        if args.smt_require_lcsc:
            cmd.append("--require-lcsc")
        run(cmd)
        smt_manifest = reports / "smt_manifest.json"
        if smt_manifest.is_file():
            manifest["smt"] = json.loads(smt_manifest.read_text(encoding="utf-8"))
            (reports / "manufacturing_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            smt_summary = manifest["smt"]
            print(
                f"SMT package: {smt_summary['smt_count']} place / "
                f"{smt_summary['hand_count']} hand-solder → {out / 'smt'}"
            )

    if args.preflight_only:
        if gate_fails:
            print("PREFLIGHT BLOCKED — expected until routing/netlist gates are complete:")
            for failure in gate_fails:
                print(f"  - {failure}")
            print(f"Reports and fabrication drawing kept under {out}; no Gerber/drill/ZIP written.")
            return 1
        _maybe_export_smt()
        print(f"Preflight OK: {out}; no Gerber/drill/ZIP written by request.")
        return 0

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

    board_sha_after_export = hashlib.sha256(args.board.read_bytes()).hexdigest()
    if board_sha_after_export != board_sha:
        failure = (
            "board_changed_during_export "
            f"before={board_sha} after={board_sha_after_export}"
        )
        if failure not in gate_fails:
            gate_fails.append(failure)
        (reports / "export_gates.txt").write_text(
            "\n".join(gate_fails) + "\n", encoding="utf-8"
        )
        manifest["gate_failures"] = gate_fails
        manifest["production_ready"] = False

    if gate_fails:
        print("DEBUG export complete with failed gates; no upload ZIP is permitted:")
        for failure in gate_fails:
            print(f"  - {failure}")
        manifest["debug_gerber_drill_written"] = True
        (reports / "manufacturing_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return 1

    zip_path = out.parent / f"{out.name}_smartpaddle_main_jlcpcb.zip"
    if zip_path.exists():
        zip_path.unlink()
    # 嘉立创上传包保持扁平且只含制造数据；报告、订单说明和钻孔图留在导出目录供复核。
    upload_files = sorted(gerbers.glob("*.gbr"))
    upload_files += sorted(gerbers.glob("*.gbrjob"))
    upload_files += sorted(drill.glob("*.drl"))
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in upload_files:
            archive.write(path, arcname=path.name)
    manifest["upload_archive_written"] = True
    manifest["upload_archive"] = str(zip_path)
    (reports / "manufacturing_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _maybe_export_smt()
    print(f"Export complete: {out}")
    print(f"Upload archive: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
