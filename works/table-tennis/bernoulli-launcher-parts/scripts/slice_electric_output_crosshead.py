#!/usr/bin/env python3
"""Offline X1C/PETG slicing screen for the unreleased crosshead carriage."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/electric-output-crosshead-screen"
CONFIG = ROOT / "output/print-review/config"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def transform(point: tuple[float, float, float], values: list[float]) -> tuple[float, float, float]:
    x, y, z = point
    return (values[0]*x+values[3]*y+values[6]*z+values[9],
            values[1]*x+values[4]*y+values[7]*z+values[10],
            values[2]*x+values[5]*y+values[8]*z+values[11])


def slot_machine_box(archive: Path, source_bounds: dict) -> list[list[float]]:
    """Map the known Ø7+0.4 Y-through slot through the actual 3MF transforms."""
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
          "p": "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"}
    with zipfile.ZipFile(archive) as z:
        model = ET.fromstring(z.read("3D/3dmodel.model"))
        components = model.findall(".//m:component", ns)
        items = model.findall(".//m:item", ns)
        if len(components) != 1 or len(items) != 1:
            raise RuntimeError("Expected exactly one crosshead carriage 3MF instance")
        component = components[0]
        item = items[0]
        object_path = component.attrib[f"{{{ns['p']}}}path"].lstrip("/")
        source_model = ET.fromstring(z.read(object_path))
        vertices = source_model.findall(".//m:vertex", ns)
        if not vertices:
            raise RuntimeError("3MF carriage mesh has no vertices")
        actual_bounds = [[min(float(v.attrib[a]) for v in vertices),
                          max(float(v.attrib[a]) for v in vertices)]
                         for a in "xyz"]
        center = [(lo+hi)/2 for lo, hi in zip(source_bounds["min"], source_bounds["max"])]
        for axis in range(3):
            for edge in range(2):
                expected = source_bounds["min" if edge == 0 else "max"][axis]-center[axis]
                if abs(actual_bounds[axis][edge]-expected) > .01:
                    raise RuntimeError("3MF source was recentered or altered unexpectedly")
        comp_transform = [float(v) for v in component.attrib["transform"].split()]
        item_transform = [float(v) for v in item.attrib["transform"].split()]
        if len(comp_transform) != 12 or len(item_transform) != 12:
            raise RuntimeError("Unexpected 3MF transform")
    slot_r = 7/2+.4
    pivot_x = 85-math.sqrt(75*75-15*15)
    x_end = pivot_x+50*math.sqrt(1-(15/75)**2)
    x_mid = pivot_x+50
    corners = [(x, y, z) for x in (x_end-slot_r, x_mid+slot_r)
               for y in (50, 61.5) for z in (15-slot_r, 15+slot_r)]
    mapped = [transform(transform(tuple(p[i]-center[i] for i in range(3)),
                                  comp_transform), item_transform)
              for p in corners]
    box = [[min(p[axis] for p in mapped), max(p[axis] for p in mapped)]
           for axis in range(3)]
    if box[2][1]-box[2][0] < 11.4 or box[2][1]-box[2][0] > 11.6:
        raise RuntimeError("The slot's through-Y axis did not become vertical")
    return [[round(v, 4) for v in bounds] for bounds in box]


def count_support_crossing_slot(gcode: Path, box: list[list[float]]) -> int:
    """Conservative XY rectangle screen for actual support extrusion moves."""
    margin = .25  # includes roughly half a nominal 0.4 mm extrusion line
    xlo, xhi = box[0][0]-margin, box[0][1]+margin
    ylo, yhi = box[1][0]-margin, box[1][1]+margin
    zlo, zhi = box[2]
    x = y = None
    z = 0.0
    feature = ""
    hits = 0
    for line in gcode.open(errors="replace"):
        if line.startswith("; FEATURE:"):
            feature = line.partition(":")[2].strip()
        if not line.startswith(("G0 ", "G1 ")):
            continue
        fields = {token[0]: token[1:] for token in line.split()[1:]
                  if len(token) > 1 and token[0] in "XYZE"}
        old_x, old_y = x, y
        try:
            if "X" in fields:
                x = float(fields["X"])
            if "Y" in fields:
                y = float(fields["Y"])
            if "Z" in fields:
                z = float(fields["Z"])
        except ValueError:
            continue
        if feature not in ("Support", "Support interface") or "E" not in fields \
                or x is None or y is None or old_x is None or old_y is None \
                or not zlo < z < zhi:
            continue
        # A bounding-box hit may be a false positive, but zero is a useful
        # proof for this G-code that no support path crosses the slot region.
        if max(min(old_x, x), xlo) <= min(max(old_x, x), xhi) \
                and max(min(old_y, y), ylo) <= min(max(old_y, y), yhi):
            hits += 1
    return hits


def main() -> int:
    geometry_path = OUT / "review.json"
    geometry = json.loads(geometry_path.read_text())
    mesh = OUT / "carriage.stl"
    if geometry["status"] != "OUTPUT_CROSSHEAD_GEOMETRY_SCREEN_ONLY" \
            or geometry["parts"]["carriage"]["sha256"] != digest(mesh) \
            or geometry["promoted_to_selected_parts"] \
            or geometry["print_or_strength_release"]:
        raise RuntimeError("Rebuild the output crosshead before slicing")
    folder = OUT / "slices/carriage-x-plus-90-tree"
    folder.mkdir(parents=True, exist_ok=True)
    for profile in ("machine", "filament"):
        shutil.copy2(CONFIG / f"{profile}.json", folder / f"{profile}.json")
    process = json.loads((CONFIG / "process.json").read_text())
    process.update(enable_support="1", support_type="tree(auto)",
                   support_on_build_plate_only="1", layer_height="0.2",
                   initial_layer_print_height="0.2", wall_loops="4",
                   sparse_infill_density="25%", brim_type="outer_only",
                   brim_width="5")
    (folder / "process.json").write_text(json.dumps(process, indent=2) + "\n")
    command = [
        str(BAMBU), "--datadir", str(folder / "app-data"),
        "--load-settings", f"{folder/'machine.json'};{folder/'process.json'}",
        "--load-filaments", str(folder / "filament.json"),
        "--orient", "0", "--rotate-x", "90", "--arrange", "1",
        "--ensure-on-bed", "--slice", "0", "--export-3mf", "slice-review.3mf",
        "--outputdir", str(folder), str(mesh),
    ]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                         timeout=240)
    (folder / "bambu-cli.log").write_text(run.stdout + run.stderr)
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
    slot_box = slot_machine_box(archive, geometry["parts"]["carriage"]["bounds_mm"]) \
        if archive_ok else None
    support_slot_hits = count_support_crossing_slot(gcode, slot_box) \
        if gcode.exists() and slot_box is not None else None
    passed = all((
        run.returncode == 0, native.get("return_code") == 0,
        archive_ok, gcode.exists(), header is not None,
        layers == (int(header.group(1)) if header else -1),
        "; FEATURE: Outer wall" in gcode_text,
        plate.get("triangle_count") == geometry["parts"]["carriage"]["triangle_count"],
        filament_g > 0, not warnings, support_slot_hits == 0,
    ))
    report = {
        "status": "OUTPUT_CARRIAGE_SLICED_UNRELEASED" if passed else "OUTPUT_CARRIAGE_SLICE_FAILED",
        "geometry_review_sha256": digest(geometry_path),
        "source_sha256": {
            "scripts/slice_electric_output_crosshead.py": digest(Path(__file__).resolve()),
            "output/print-review/config/machine.json": digest(CONFIG / "machine.json"),
            "output/print-review/config/filament.json": digest(CONFIG / "filament.json"),
            "output/print-review/config/process.json": digest(CONFIG / "process.json"),
        },
        "part": "one-piece carriage with output crosshead",
        "source_stl_sha256": digest(mesh),
        "machine": "Bambu Lab X1 Carbon, 0.4 mm nozzle",
        "material_profile": "Generic PETG",
        "rotation_x_deg": 90, "layer_height_mm": .2,
        "wall_loops": 4, "infill": "25%", "brim_mm": 5,
        "support": "tree, build plate only",
        "cli_return_code": run.returncode,
        "native_return_code": native.get("return_code"),
        "native_warnings": warnings,
        "archive_integrity_pass": archive_ok,
        "gcode_layers": layers,
        "header_layers": int(header.group(1)) if header else 0,
        "filament_g": filament_g,
        "estimated_time_s": plate.get("total_predication"),
        "native_triangle_count": plate.get("triangle_count"),
        "gcode_sha256": digest(gcode) if gcode.exists() else None,
        "slice_3mf_sha256": digest(archive) if archive.exists() else None,
        "preview_sha256": digest(folder / "plate-preview.png")
        if (folder / "plate-preview.png").exists() else None,
        "slot_axis_vertical_after_rotation": slot_box is not None,
        "slot_machine_box_mm": slot_box,
        "support_extrusion_segments_crossing_slot_with_0p25mm_margin": support_slot_hits,
        "printer_sent": False, "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": [] if passed else ["native-offline-slice"],
    }
    (OUT / "slice-review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Output carriage X+90 tree: {report['status']}, {filament_g:.3f} g")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
