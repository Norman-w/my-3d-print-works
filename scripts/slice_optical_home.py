#!/usr/bin/env python3
"""Offline X1C/PETG slice review for the two optical-home replacement parts."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/optical-home-candidate"
CONFIG = ROOT / "output/print-review/config"
SOURCE = ROOT / "cad/feeder-optical-home.scad"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
PARTS = {
    "left-y-cap": ("-90", True),
    "moving-spring-spacer-flag": ("-90", True),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    review = json.loads((OUT / "review.json").read_text())
    assert review["geometry_review_pass"]
    assert review["source_sha256"] == sha(SOURCE), "Rebuild the geometry first"
    summary = {}
    failures = []
    for name, (rotation_x, support) in PARTS.items():
        folder = OUT / "slices" / name
        folder.mkdir(parents=True, exist_ok=True)
        for profile in ("machine", "filament"):
            shutil.copy2(CONFIG / f"{profile}.json", folder / f"{profile}.json")
        process = json.loads((CONFIG / "process.json").read_text())
        process.update(
            enable_support="1" if support else "0",
            support_type="tree(auto)",
            support_on_build_plate_only="1",
            layer_height="0.2",
            initial_layer_print_height="0.2",
            wall_loops="4",
            sparse_infill_density="25%",
            brim_type="outer_only",
            brim_width="5",
        )
        (folder / "process.json").write_text(json.dumps(process, indent=2) + "\n")
        source_stl = OUT / f"{name}.stl"
        command = [
            str(BAMBU), "--datadir", str(folder / "app-data"),
            "--load-settings", f"{folder / 'machine.json'};{folder / 'process.json'}",
            "--load-filaments", str(folder / "filament.json"),
            "--orient", "0", "--rotate-x", rotation_x, "--arrange", "1",
            "--ensure-on-bed", "--slice", "0", "--export-3mf", "slice-review.3mf",
            "--outputdir", str(folder), str(source_stl),
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=240)
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
        layer_match = re.search(r"^; total layer number: (\d+)$", gcode_text, re.M)
        layer_count = len(re.findall(r"^; CHANGE_LAYER$", gcode_text, re.M))
        header_layers = int(layer_match.group(1)) if layer_match else 0
        plates = native.get("sliced_plates", [])
        plate = plates[0] if len(plates) == 1 else {}
        filament_g = sum(f.get("total_used_g", 0) for f in plate.get("filaments", []))
        native_warnings = [p.get("warning_message") for p in plates if p.get("warning_message")]
        passed = all((
            result.returncode == 0,
            native.get("return_code") == 0,
            archive_ok,
            gcode.exists(),
            header_layers > 0,
            layer_count == header_layers,
            "; FEATURE: Outer wall" in gcode_text,
            plate.get("triangle_count") == review["printed_parts"][name]["triangle_count"],
            filament_g > 0,
            not native_warnings,
        ))
        row = {
            "part": name,
            "source_stl_sha256": sha(source_stl),
            "rotation_x_deg": int(rotation_x),
            "support": "tree, build plate only" if support else "off",
            "layer_height_mm": 0.2,
            "brim_mm": 5,
            "machine": "Bambu Lab X1 Carbon, 0.4 mm nozzle",
            "material_profile": "Generic PETG",
            "physical_acceptance": False,
            "printer_sent": False,
            "cli_return_code": result.returncode,
            "archive_integrity_pass": archive_ok,
            "gcode_layers": layer_count,
            "header_layers": header_layers,
            "filament_g": filament_g,
            "estimated_time_s": plate.get("total_predication"),
            "native_warnings": native_warnings,
            "native_result": native,
            "gcode_sha256": sha(gcode) if gcode.exists() else None,
            "slice_3mf_sha256": sha(archive) if archive.exists() else None,
            "slice_generated": passed,
        }
        (folder / "review.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n")
        summary[name] = {
            "slice_generated": passed,
            "source_stl_sha256": sha(source_stl),
            "gcode_layers": layer_count,
            "filament_g": round(filament_g, 3),
            "estimated_time_s": round(plate.get("total_predication", 0), 1),
            "native_warnings": native_warnings,
            "folder": str(folder.relative_to(ROOT)),
        }
        if not passed:
            failures.append(name)
        print(f"{name}: {'SLICE_GENERATED' if passed else 'SLICE_FAILED'}", flush=True)
    (OUT / "slice-review.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
