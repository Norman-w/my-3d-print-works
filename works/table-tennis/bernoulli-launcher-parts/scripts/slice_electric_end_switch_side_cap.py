#!/usr/bin/env python3
"""Offline X1C/PETG slice screen for the unreleased side-bolted guide cap."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/electric-end-switch-side-cap"
CONFIG = ROOT / "output/print-review/config"
CAD = ROOT / "cad/electric-end-switch-side-cap.scad"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    geometry = json.loads((OUT / "review.json").read_text())
    if (geometry["status"] != "SIDE_BOLTED_ENDPOINT_CAP_GEOMETRY_PASS_UNRELEASED"
            or geometry["source_sha256"]["cad/electric-end-switch-side-cap.scad"]
            != sha(CAD)
            or geometry["part_meshes"]["cap"]["stl_sha256"]
            != sha(OUT / "cap.stl")
            or geometry["part_meshes"]["carriage"]["stl_sha256"]
            != sha(OUT / "carriage.stl")):
        raise RuntimeError("Rebuild the side-cap geometry before slicing")
    rows = {}
    failures = []
    for name, part, rotation_x, support in (
            ("cap-unsupported", "cap", -90, False),
            ("cap-tree-support", "cap", -90, True),
            ("carriage-tree-support", "carriage", 90, True)):
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
        command = [
            str(BAMBU), "--datadir", str(folder / "app-data"),
            "--load-settings", f"{folder/'machine.json'};{folder/'process.json'}",
            "--load-filaments", str(folder / "filament.json"),
            "--orient", "0", "--rotate-x", str(rotation_x), "--arrange", "1",
            "--ensure-on-bed", "--slice", "0", "--export-3mf", "slice-review.3mf",
            "--outputdir", str(folder), str(OUT / f"{part}.stl"),
        ]
        result = subprocess.run(command, cwd=ROOT, text=True,
                                capture_output=True, timeout=240)
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
        gcode_text = gcode.read_text(errors="replace") if gcode.exists() else ""
        header = re.search(r"^; total layer number: (\d+)$", gcode_text, re.M)
        layers = len(re.findall(r"^; CHANGE_LAYER$", gcode_text, re.M))
        plates = native.get("sliced_plates", [])
        plate = plates[0] if len(plates) == 1 else {}
        filament_g = sum(f.get("total_used_g", 0) for f in plate.get("filaments", []))
        warnings = [p.get("warning_message") for p in plates if p.get("warning_message")]
        passed = all((
            result.returncode == 0, native.get("return_code") == 0,
            archive_ok, gcode.exists(), header is not None,
            layers == (int(header.group(1)) if header else -1),
            "; FEATURE: Outer wall" in gcode_text,
            plate.get("triangle_count") == geometry["part_meshes"][part]["triangle_count"],
            filament_g > 0, not warnings,
        ))
        rows[name] = {
            "status": "SLICED_UNRELEASED" if passed else "FAIL",
            "part": part,
            "source_stl_sha256": sha(OUT / f"{part}.stl"),
            "machine": "Bambu Lab X1 Carbon, 0.4 mm nozzle",
            "material_profile": "Generic PETG",
            "rotation_x_deg": rotation_x,
            "layer_height_mm": .2, "wall_loops": 4,
            "infill": "25%", "brim_mm": 5,
            "support": "tree, build plate only" if support else "off",
            "cli_return_code": result.returncode,
            "native_return_code": native.get("return_code"),
            "native_warnings": warnings,
            "archive_integrity_pass": archive_ok,
            "gcode_layers": layers,
            "header_layers": int(header.group(1)) if header else 0,
            "filament_g": filament_g,
            "estimated_time_s": plate.get("total_predication"),
            "native_triangle_count": plate.get("triangle_count"),
            "gcode_sha256": sha(gcode) if gcode.exists() else None,
            "slice_3mf_sha256": sha(archive) if archive.exists() else None,
            "preview_sha256": sha(folder / "plate-preview.png")
            if (folder / "plate-preview.png").exists() else None,
        }
        if not passed and support:
            failures.append(name)
        print(f"{name}: {'SLICED_UNRELEASED' if passed else 'FAIL'}, "
              f"{filament_g:.3f} g", flush=True)
    unsupported_warning = rows["cap-unsupported"]["native_warnings"]
    unsupported_rejected = (rows["cap-unsupported"]["status"] == "FAIL"
                            and any("floating regions" in warning
                                    for warning in unsupported_warning))
    if rows["cap-unsupported"]["status"] == "FAIL" and not unsupported_rejected:
        failures.append("cap-unsupported-unexpected-error")
    report = {
        "status": "SIDE_CAP_AND_CARRIAGE_SLICED_UNRELEASED"
                  if not failures and unsupported_rejected else
                  "SIDE_CAP_SLICED_UNRELEASED"
                  if not failures else "FAIL",
        "geometry_review_sha256": sha(OUT / "review.json"),
        "source_sha256": {
            "scripts/slice_electric_end_switch_side_cap.py": sha(Path(__file__)),
            "cad/electric-end-switch-side-cap.scad": sha(CAD),
            "output/print-review/config/machine.json": sha(CONFIG / "machine.json"),
            "output/print-review/config/filament.json": sha(CONFIG / "filament.json"),
            "output/print-review/config/process.json": sha(CONFIG / "process.json"),
        },
        "orientations": rows,
        "unsupported_rejected_for_floating_regions": unsupported_rejected,
        "printer_sent": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "slice-review.json").write_text(json.dumps(report, ensure_ascii=False,
                                                 indent=2) + "\n")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
