#!/usr/bin/env python3
"""Reproducible JLCPCB order-package selector for SmartPaddle boards.

The main PCB keeps its established C4 production gates.  The tail PCB is
exported as an explicitly experimental prototype and never combined into the
same Gerber archive as the main PCB.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAIN_EXPORTER = ROOT / "pcb" / "scripts" / "export_jlcpcb.py"
TAIL_BOARD = ROOT / "pcb-tail" / "layouts" / "default" / "default.kicad_pcb"
TAIL_CONNECTION = ROOT / "pcb-tail" / "C4_ADAPTER_HARNESS.md"
MAIN_FAB_NOTES = ROOT / "pcb" / "C4_FAB_NOTES.md"
MAIN_FAB_READINESS = ROOT / "pcb" / "C4_FAB_READINESS.md"
DEFAULT_KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

TAIL_ORDER_README = """\
SmartPaddle M5 Tail PCB — JLCPCB prototype review notes

IDENTITY / STATUS
- Board: SmartPaddle M5 Tail (repository title currently M5-TAIL-BARE)
- Order type: single-board engineering prototype; NOT a panel
- Recommended quantity: 5 pcs or the manufacturer's minimum prototype quantity
- Status: experimental; DRC-clean at export time, but not physically assembled,
  powered, charged, enumerated over USB, thermally tested, or production-qualified

KNOWN BOARD PARAMETERS FROM THE PCB FILE
- Copper layers: 2
- Finished board thickness: 1.00 mm
- Outline: use the supplied Edge_Cuts Gerber without reshaping
- Copper weight: NOT SPECIFIED in the project; user must confirm on the order page
- Surface finish: NOT SPECIFIED/frozen; user must choose and record it on the order page
- Solder-mask/silkscreen colors: NOT SPECIFIED; user must choose on the order page
- Panelization: none; upload as one independent single-board design

ORDER-PAGE CHECKS
1. Confirm the viewer detects exactly one closed outline, about 29.736 x 19.320 mm.
2. Confirm 2 copper layers and 1.00 mm thickness.
3. Confirm F/B copper, solder mask, silkscreen, Edge_Cuts and Excellon drill are present.
4. Confirm the vertical USB-C shell slots and THT switch holes appear in drill preview.
5. Do not accept automatic outline repair, panelization, copper-weight or finish changes
   without recording the choice and checking mechanical/electrical consequences.
6. This package is PCB-only. Component assembly/BOM/CPL is not qualified for the tail board.

Suggested Chinese order remark:
SmartPaddle M5 尾板工程样板，单板、2层、板厚1.0mm，按Gerber板框生产，不拼板。
USB-C外壳槽孔及按键通孔按钻孔文件加工；如需修改板框、槽孔或加价工艺请先联系。
铜厚、表面处理及颜色由下单人在页面确认并记录，本项目当前未冻结这些选项。

UPLOAD
- Upload only the sibling *_tail_jlcpcb_upload.zip to the Gerber uploader.
- Keep this README, reports, fabrication PDF, manifest and connection pinout for review.
- Do not merge this ZIP with the C4 main-board ZIP; they are separate orders.
"""

MAIN_ORDER_README = """\
SmartPaddle C4 Main PCB — JLCPCB order review notes

IDENTITY / STATUS
- Board: SmartPaddle Rigid PCB / C4
- Order type: one independent single-board engineering-prototype order; NOT a panel
- Recommended quantity: 5 pcs or the manufacturer's minimum prototype quantity
- Current production gates: must be OK in reports/export_gates.txt before a ZIP exists

FROZEN PARAMETERS
- Copper layers: 2
- Finished board thickness: 0.80 mm
- Surface finish: ENIG / immersion gold (沉金)
- Copper weight: NOT SPECIFIED in the project; user must confirm on the order page
- Solder-mask/silkscreen colors: NOT SPECIFIED; user must choose on the order page
- Keep the supplied Edge_Cuts, internal routed module openings and intentional PTH cuts
- Panelization: none; upload as one independent single-board design

ORDER-PAGE CHECKS
1. Upload only the sibling *_smartpaddle_c4_jlcpcb.zip.
2. Confirm 2 layers, 0.80 mm, ENIG, single board, quantity 5 or minimum.
3. Confirm copper weight and colors explicitly; the repository does not freeze them.
4. Paste the Chinese manufacturer remark from C4_FAB_NOTES.md.
5. Inspect the outer outline, ESP32-S3/IM948 internal routed openings, copper, mask,
   silkscreen and drill preview.  Do not permit automatic outline straightening.
6. This is an engineering prototype release, not whole-product production approval.

The review bundle also contains the C4 fabrication/readiness notes and the C4-to-tail pinout.
The C4 and tail upload ZIPs are separate orders and must never be merged.
"""


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def zip_files(destination: Path, files: list[Path], base: Path | None = None) -> None:
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            arcname = path.name if base is None else str(path.relative_to(base))
            archive.write(path, arcname=arcname)


def export_tail(out: Path, kicad_cli: str) -> tuple[Path, Path]:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"tail output is not empty: {out}")
    gerbers = out / "gerbers"
    drill = out / "drill"
    reports = out / "reports"
    gerbers.mkdir(parents=True, exist_ok=True)
    drill.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    before = sha256(TAIL_BOARD)
    drc_json = reports / "drc.json"
    drc_report = reports / "drc.rpt"
    run([
        kicad_cli, "pcb", "drc", "--format", "json", "--units", "mm",
        "--severity-all", "--output", str(drc_json), str(TAIL_BOARD),
    ])
    run([
        kicad_cli, "pcb", "drc", "--format", "report", "--units", "mm",
        "--severity-all", "--output", str(drc_report), str(TAIL_BOARD),
    ])
    data = json.loads(drc_json.read_text(encoding="utf-8"))
    errors = [item for item in data.get("violations", []) if item.get("severity") == "error"]
    unconnected = data.get("unconnected_items", [])
    if errors or unconnected:
        raise RuntimeError(
            f"tail export blocked: DRC errors={len(errors)}, unconnected={len(unconnected)}"
        )

    run([
        kicad_cli, "pcb", "export", "gerbers", "--layers",
        "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts",
        "--output", str(gerbers), str(TAIL_BOARD),
    ])
    run([
        kicad_cli, "pcb", "export", "drill", "--output", str(drill),
        "--format", "excellon", "--excellon-units", "mm", "--generate-map",
        "--map-format", "pdf", str(TAIL_BOARD),
    ])
    fab_pdf = out / "M5_tail_fabrication_drawing.pdf"
    run([
        kicad_cli, "pcb", "export", "pdf", "--layers", "F.Fab,B.Fab,Edge.Cuts",
        "--sketch-pads-on-fab-layers", "--mode-single", "--output", str(fab_pdf),
        str(TAIL_BOARD),
    ])
    after = sha256(TAIL_BOARD)
    if after != before:
        raise RuntimeError(f"tail board changed during export: {before} -> {after}")

    upload_files = [path for path in gerbers.iterdir() if path.is_file()]
    upload_files += list(drill.glob("*.drl"))
    edge_files = [path for path in upload_files if "Edge_Cuts" in path.name]
    drill_files = [path for path in upload_files if path.suffix == ".drl"]
    if not edge_files or not drill_files:
        raise RuntimeError(
            f"tail package incomplete: edge_cuts={len(edge_files)}, drill={len(drill_files)}"
        )

    readme = out / "ORDER_README.txt"
    readme.write_text(TAIL_ORDER_README, encoding="utf-8")
    shutil.copy2(TAIL_CONNECTION, out / "C4_TO_TAIL_PINOUT.md")
    manifest = {
        "schema_version": 1,
        "board": str(TAIL_BOARD.resolve()),
        "board_sha256": before,
        "identity": "SmartPaddle M5 Tail / M5-TAIL-BARE",
        "order_type": "single_board_experimental_prototype",
        "copper_layers": 2,
        "board_thickness_mm": 1.0,
        "copper_weight": None,
        "surface_finish": None,
        "recommended_quantity": "5 or manufacturer minimum",
        "drc_errors": len(errors),
        "unconnected_items": len(unconnected),
        "physical_validation": False,
        "production_ready": False,
        "gerber_count": len([path for path in gerbers.iterdir() if path.is_file()]),
        "drill_count": len(drill_files),
    }
    (reports / "manufacturing_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    upload_zip = out.parent / f"{out.name}_tail_jlcpcb_upload.zip"
    zip_files(upload_zip, upload_files)
    review_files = [path for path in out.rglob("*") if path.is_file()]
    review_zip = out.parent / f"{out.name}_tail_review_bundle.zip"
    zip_files(review_zip, review_files, base=out)
    print(f"Tail upload archive: {upload_zip}")
    print(f"Tail review bundle: {review_zip}")
    return upload_zip, review_zip


def export_main(out: Path, kicad_cli: str) -> tuple[Path, Path]:
    run([
        sys.executable, str(MAIN_EXPORTER), "--kicad-cli", kicad_cli,
        "--output", str(out),
    ])
    candidates = sorted(out.parent.glob(f"{out.name}_smartpaddle_c4_jlcpcb.zip"))
    if len(candidates) != 1:
        raise RuntimeError(f"expected one C4 upload ZIP, found {len(candidates)}")
    (out / "ORDER_README.txt").write_text(MAIN_ORDER_README, encoding="utf-8")
    shutil.copy2(MAIN_FAB_NOTES, out / "C4_FAB_NOTES.md")
    shutil.copy2(MAIN_FAB_READINESS, out / "C4_FAB_READINESS.md")
    shutil.copy2(TAIL_CONNECTION, out / "C4_TO_TAIL_PINOUT.md")
    review_files = [path for path in out.rglob("*") if path.is_file()]
    review_zip = out.parent / f"{out.name}_main_review_bundle.zip"
    zip_files(review_zip, review_files, base=out)
    return candidates[0], review_zip


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Select and export independent SmartPaddle JLCPCB order packages"
    )
    parser.add_argument(
        "--target", required=True, choices=("main", "tail", "separate", "panel"),
        help="main=C4 only; tail=experimental tail only; separate=both as two orders",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--kicad-cli", default=DEFAULT_KICAD_CLI)
    args = parser.parse_args()

    if args.target == "panel":
        print("PANEL EXPORT REFUSED: no reviewed panel project, rails, tabs, fiducials, or V-score/mouse-bite contract exists.")
        print("Use --target separate; it produces two independent Gerber upload archives.")
        return 2

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root_out = args.output or ROOT / "fab" / "jlcpcb-orders" / stamp
    if root_out.exists() and any(root_out.iterdir()):
        print(f"Output directory is not empty: {root_out}")
        return 2
    root_out.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, str] = {}
    if args.target in ("main", "separate"):
        upload, review = export_main(root_out / "main_c4", args.kicad_cli)
        outputs["main_upload_zip"] = str(upload)
        outputs["main_review_bundle"] = str(review)
    if args.target in ("tail", "separate"):
        upload, review = export_tail(root_out / "tail_m5", args.kicad_cli)
        outputs["tail_upload_zip"] = str(upload)
        outputs["tail_review_bundle"] = str(review)
    summary = {
        "target": args.target,
        "panelized": False,
        "independent_orders": args.target == "separate",
        "outputs": outputs,
    }
    (root_out / "ORDER_PACKAGE_INDEX.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
