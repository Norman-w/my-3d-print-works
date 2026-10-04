#!/usr/bin/env python3
"""Offline X1C/PETG tie-hole check of the selected trigger beam."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from slice_electric_rocker_service_fork import (
    BAMBU, CONFIG, mapped_regions, sha, support_crossings,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/electronic-trigger-wire-relief"
REVIEW = OUT / "review.json"
REGIONS = {
    "tie_left": ((41, -59.1, -15), (44, -54.9, -12)),
    "tie_right": ((47, -59.1, -15), (50, -54.9, -12)),
}


def main() -> int:
    review = json.loads(REVIEW.read_text())
    mesh = OUT / "beam-candidate.stl"
    if review["status"] != "WIRE_RELIEF_NOMINAL_GEOMETRY_ONLY" \
            or review["part"]["sha256"] != sha(mesh) \
            or review["promoted_to_selected_beam"] is not True:
        raise RuntimeError("Wire-relief geometry has not passed its own review")
    folder = OUT / "slice-x-minus-90-tree"
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("machine", "filament"):
        shutil.copy2(CONFIG / f"{name}.json", folder / f"{name}.json")
    process = json.loads((CONFIG / "process.json").read_text())
    process.update(enable_support="1", support_type="tree(auto)",
                   support_on_build_plate_only="1", layer_height="0.2",
                   initial_layer_print_height="0.2", wall_loops="4",
                   sparse_infill_density="25%", brim_type="outer_only",
                   brim_width="5")
    (folder / "process.json").write_text(json.dumps(process, indent=2) + "\n")
    for name in ("result.json", "slice-review.3mf", "plate_1.gcode", "plate-preview.png"):
        (folder / name).unlink(missing_ok=True)
    cmd = [str(BAMBU), "--datadir", str(folder / "app-data"),
           "--load-settings", f"{folder/'machine.json'};{folder/'process.json'}",
           "--load-filaments", str(folder / "filament.json"),
           "--orient", "0", "--rotate-x", "-90", "--arrange", "1",
           "--ensure-on-bed", "--slice", "0", "--export-3mf", "slice-review.3mf",
           "--outputdir", str(folder), str(mesh)]
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=240)
    (folder / "bambu-cli.log").write_text(run.stdout+run.stderr)
    native_path = folder / "result.json"
    native = json.loads(native_path.read_text()) if native_path.exists() else {}
    plates = native.get("sliced_plates", [])
    plate = plates[0] if len(plates) == 1 else {}
    archive = folder / "slice-review.3mf"
    gcode = folder / "plate_1.gcode"
    archive_ok = False
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            archive_ok = z.testzip() is None and "Metadata/plate_1.gcode" in z.namelist()
            if "Metadata/plate_1.png" in z.namelist():
                (folder / "plate-preview.png").write_bytes(z.read("Metadata/plate_1.png"))
    boxes, _ = mapped_regions(archive, review["part"]["bounds_mm"],
                              REGIONS, {}) if archive_ok else (None, None)
    hits = support_crossings(gcode, boxes) if boxes is not None and gcode.exists() else None
    text = gcode.read_text(errors="replace") if gcode.exists() else ""
    header = re.search(r"^; total layer number: (\d+)$", text, re.M)
    layers = len(re.findall(r"^; CHANGE_LAYER$", text, re.M))
    warnings = [p.get("warning_message") for p in plates if p.get("warning_message")]
    grams = sum(f.get("total_used_g", 0) for f in plate.get("filaments", []))
    passed = all((run.returncode == 0, native.get("return_code") == 0,
                  archive_ok, gcode.exists(), header is not None,
                  layers == (int(header.group(1)) if header else -1),
                  plate.get("triangle_count") == review["part"]["triangle_count"],
                  grams > 0, not warnings,
                  hits is not None and all(v == 0 for v in hits.values())))
    report = {
        "status": "WIRE_RELIEF_SLICED_UNRELEASED" if passed else "FAIL",
        "geometry_review_sha256": sha(REVIEW),
        "source_sha256": {
            str(p.relative_to(ROOT)): sha(p) for p in
            (Path(__file__).resolve(), CONFIG / "machine.json",
             CONFIG / "filament.json", CONFIG / "process.json")
        },
        "source_stl_sha256": sha(mesh),
        "rotation_x_deg": -90,
        "machine": "Bambu Lab X1 Carbon, 0.4 mm nozzle, Textured PEI Plate",
        "material_profile": "Generic PETG",
        "process": "0.2 mm; 4 walls; 25% infill; 5 mm brim; tree support from bed only",
        "cli_return_code": run.returncode,
        "native_return_code": native.get("return_code"),
        "native_warnings": warnings,
        "archive_integrity_pass": archive_ok,
        "gcode_layers": layers,
        "filament_g": grams,
        "estimated_time_s": plate.get("total_predication"),
        "tie_hole_machine_boxes_mm": boxes,
        "support_extrusion_segments_crossing_tie_holes_with_0p25mm_margin": hits,
        "slice_3mf_sha256": sha(archive) if archive.exists() else None,
        "preview_sha256": sha(folder / "plate-preview.png")
        if (folder / "plate-preview.png").exists() else None,
        "promoted_to_selected_beam": True,
        "printer_sent": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
    }
    (OUT / "slice-review.json").write_text(json.dumps(report, ensure_ascii=False,
                                                   indent=2) + "\n")
    print(report["status"], f"{grams:.3f} g", hits)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
