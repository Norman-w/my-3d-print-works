#!/usr/bin/env python3
"""Offline X1C/PETG slice check of the unreleased trigger candidate."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from slice_electric_rocker_service_fork import mapped_regions, support_crossings


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/electronic-trigger-candidate"
CONFIG = ROOT / "output/print-review/config"
CAD = ROOT / "cad/electronic-trigger-candidate.scad"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
PARTS = {"beam": True, "lever": True}
SLOT_REGIONS = {
    "lower_m2_slot_core": ((44.05, -58.8, -4.45),
                           (47.45, -55.2, -3.05)),
    "upper_m2_slot_core": ((44.05, -58.8, 2.05),
                           (47.45, -55.2, 3.45)),
}


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    review = json.loads((OUT / "review.json").read_text())
    assert review["status"] == "TRIGGER_CANDIDATE_GEOMETRY_PASS_UNRELEASED"
    assert review["source_sha256"]["cad/electronic-trigger-candidate.scad"] == sha(CAD)
    cad_source = CAD.read_text()
    for reviewed_literal in (
            "et_switch_z = -6.9;", "et_switch_hole_z_offset = 3.15;",
            "et_switch_slot_x_min = 43.8;", "et_switch_slot_x_max = 47.7;",
            "et_switch_slot_d = 2.8;", "et_backplate_front_y = -55;",
            "et_box(39,70,-59,et_backplate_front_y,-39,7);"):
        if reviewed_literal not in cad_source:
            raise RuntimeError("M2 slot core boxes need review against changed CAD")
    summary = {}
    failures = []
    for name, support in PARTS.items():
        folder = OUT / "slices" / name
        folder.mkdir(parents=True, exist_ok=True)
        for profile in ("machine", "filament"):
            shutil.copy2(CONFIG / f"{profile}.json", folder / f"{profile}.json")
        process = json.loads((CONFIG / "process.json").read_text())
        process.update(
            enable_support="1" if support else "0",
            support_type="tree(auto)",
            support_on_build_plate_only="1",
            layer_height="0.2", initial_layer_print_height="0.2",
            wall_loops="4", sparse_infill_density="25%",
            brim_type="outer_only", brim_width="5",
        )
        (folder / "process.json").write_text(json.dumps(process, indent=2) + "\n")
        for stale in ("result.json", "slice-review.3mf", "plate_1.gcode",
                      "plate-preview.png"):
            (folder / stale).unlink(missing_ok=True)
        source_stl = OUT / f"{name}.stl"
        command = [
            str(BAMBU), "--datadir", str(folder / "app-data"),
            "--load-settings", f"{folder / 'machine.json'};{folder / 'process.json'}",
            "--load-filaments", str(folder / "filament.json"),
            "--orient", "0", "--rotate-x", "-90", "--arrange", "1",
            "--ensure-on-bed", "--slice", "0", "--export-3mf", "slice-review.3mf",
            "--outputdir", str(folder), str(source_stl),
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                timeout=240)
        (folder / "bambu-cli.log").write_text(result.stdout + result.stderr)
        native_path = folder / "result.json"
        native = json.loads(native_path.read_text()) if native_path.exists() else {}
        archive = folder / "slice-review.3mf"
        gcode = folder / "plate_1.gcode"
        archive_ok = False
        if archive.exists():
            with zipfile.ZipFile(archive) as z:
                archive_ok = z.testzip() is None and "Metadata/plate_1.gcode" in z.namelist()
                if "Metadata/plate_1.png" in z.namelist():
                    (folder / "plate-preview.png").write_bytes(z.read("Metadata/plate_1.png"))
        slot_boxes = None
        slot_support_hits = None
        if name == "beam" and archive_ok and gcode.exists():
            slot_boxes, _ = mapped_regions(
                archive, review["parts"][name]["bounds"], SLOT_REGIONS, {})
            slot_support_hits = support_crossings(gcode, slot_boxes)
        gcode_text = gcode.read_text(errors="replace") if gcode.exists() else ""
        layer_match = re.search(r"^; total layer number: (\d+)$", gcode_text, re.M)
        layer_count = len(re.findall(r"^; CHANGE_LAYER$", gcode_text, re.M))
        header_layers = int(layer_match.group(1)) if layer_match else 0
        plates = native.get("sliced_plates", [])
        plate = plates[0] if len(plates) == 1 else {}
        filament_g = sum(f.get("total_used_g", 0) for f in plate.get("filaments", []))
        native_warnings = [p.get("warning_message") for p in plates if p.get("warning_message")]
        passed = all((
            result.returncode == 0, native.get("return_code") == 0, archive_ok,
            gcode.exists(), header_layers > 0, layer_count == header_layers,
            "; FEATURE: Outer wall" in gcode_text,
            plate.get("triangle_count") == review["parts"][name]["triangle_count"],
            filament_g > 0, not native_warnings,
            name != "beam" or (slot_support_hits is not None
                               and all(value == 0 for value in
                                       slot_support_hits.values())),
        ))
        row = {
            "part": name, "source_stl_sha256": sha(source_stl),
            "rotation_x_deg": -90,
            "support": "tree, build plate only" if support else "off",
            "layer_height_mm": 0.2, "brim_mm": 5,
            "machine": "Bambu Lab X1 Carbon, 0.4 mm nozzle",
            "material_profile": "Generic PETG", "printer_sent": False,
            "cli_return_code": result.returncode, "native_result": native,
            "archive_integrity_pass": archive_ok,
            "gcode_layers": layer_count, "header_layers": header_layers,
            "filament_g": filament_g,
            "estimated_time_s": plate.get("total_predication"),
            "native_warnings": native_warnings,
            "m2_slot_core_machine_boxes_mm": slot_boxes,
            "support_extrusion_segments_crossing_m2_slot_cores_with_0p25mm_margin":
                slot_support_hits,
            "gcode_sha256": sha(gcode) if gcode.exists() else None,
            "slice_3mf_sha256": sha(archive) if archive.exists() else None,
            "slice_generated": passed,
            "manufacturing_release": False, "physical_acceptance": False,
        }
        (folder / "review.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n")
        summary[name] = {key: row[key] for key in
                         ("slice_generated", "source_stl_sha256", "gcode_layers",
                          "filament_g", "estimated_time_s", "native_warnings",
                          "support_extrusion_segments_crossing_m2_slot_cores_with_0p25mm_margin")}
        if not passed:
            failures.append(name)
        print(f"{name}: {'SLICE_GENERATED' if passed else 'SLICE_FAILED'}", flush=True)
    (OUT / "slice-review.json").write_text(json.dumps({
        "status": "CANDIDATE_SLICED_UNRELEASED" if not failures else "FAIL",
        "parts": summary, "printer_sent": False,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in
                          (Path(__file__).resolve(), ROOT / "scripts/slice_electric_rocker_service_fork.py",
                           CAD,
                           CONFIG / "machine.json", CONFIG / "filament.json",
                           CONFIG / "process.json")},
        "manufacturing_release": False, "physical_acceptance": False,
    }, ensure_ascii=False, indent=2) + "\n")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
