#!/usr/bin/env python3
"""Compare offline PETG slice orientations for the unreleased service-fork base."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
from xml.etree import ElementTree as ET

from slice_electric_rocker_service_fork import (
    BAMBU, CONFIG, OUT, REGIONS, sha, support_crossings, transform,
)


ROOT = Path(__file__).resolve().parents[1]
GEOMETRY = OUT / "review.json"
SOURCE_SLICE = OUT / "slice-review.json"
REPORT = OUT / "orientation-screen.json"
ANGLES = (0, 30, 35, 40, 42, 45, 48, 50, 55, 60, 75)


def placement(archive: Path, bounds: dict) -> tuple[list[float], list[float], list[float]]:
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
          "p": "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"}
    with zipfile.ZipFile(archive) as z:
        root = ET.fromstring(z.read("3D/3dmodel.model"))
        component = root.find(".//m:component", ns)
        item = root.find(".//m:item", ns)
        if component is None or item is None:
            raise RuntimeError("Expected one 3MF component and item")
        source_path = component.attrib[f"{{{ns['p']}}}path"].lstrip("/")
        source = ET.fromstring(z.read(source_path))
        vertices = source.findall(".//m:vertex", ns)
        actual = [[min(float(v.attrib[axis]) for v in vertices),
                   max(float(v.attrib[axis]) for v in vertices)] for axis in "xyz"]
        comp = [float(v) for v in component.attrib["transform"].split()]
        plate = [float(v) for v in item.attrib["transform"].split()]
    center = [(bounds["min"][i]+bounds["max"][i])/2 for i in range(3)]
    if len(comp) != 12 or len(plate) != 12:
        raise RuntimeError("Unexpected 3MF transform")
    for axis in range(3):
        for edge in range(2):
            expected = bounds["min" if edge == 0 else "max"][axis]-center[axis]
            if abs(actual[axis][edge]-expected) > .01:
                raise RuntimeError("3MF mesh bounds differ from reviewed STL")
    return comp, plate, center


def mapped_boxes(comp: list[float], plate: list[float], center: list[float]) -> dict:
    boxes = {}
    for name, (lo, hi) in REGIONS["base"].items():
        corners = [(x, y, z) for x in (lo[0], hi[0])
                   for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        points = [transform(transform(tuple(p[i]-center[i] for i in range(3)),
                                      comp), plate) for p in corners]
        boxes[name] = [[round(min(p[i] for p in points), 4),
                        round(max(p[i] for p in points), 4)] for i in range(3)]
    return boxes


def inverse_transform(point: tuple[float, float, float],
                      matrix: list[float]) -> tuple[float, float, float]:
    # Bambu's two 3MF placements are rigid transforms; the inverse of each
    # orthogonal rotation is its transpose.
    v = [point[i]-matrix[9+i] for i in range(3)]
    axes = ((matrix[0], matrix[1], matrix[2]),
            (matrix[3], matrix[4], matrix[5]),
            (matrix[6], matrix[7], matrix[8]))
    return tuple(sum(axes[i][j]*v[j] for j in range(3)) for i in range(3))


def source_point(point: tuple[float, float, float], comp: list[float],
                 plate: list[float], center: list[float]) -> tuple[float, float, float]:
    local = inverse_transform(inverse_transform(point, plate), comp)
    return tuple(local[i]+center[i] for i in range(3))


def void_core(point: tuple[float, float, float]) -> tuple[str, ...]:
    x, y, z = point
    pivot_x = 85-math.sqrt(75*75-15*15)
    found = []
    for name, zc in (("bolt_lower", -14), ("bolt_upper", 2)):
        if 60.9 <= y <= 68.1 and (x-15)**2+(z-zc)**2 <= 1.45**2:
            found.append(name)
    for name, zc in (("nut_lower", -14), ("nut_upper", 2)):
        if 65.2 <= y <= 68.1 and (x-15)**2+(z-zc)**2 <= 2.65**2:
            found.append(name)
    if 57.9 <= y <= 61.1 and (x-pivot_x)**2+(z-25)**2 <= 2.95**2:
        found.append("pivot_bore")
    return tuple(found)


def supports_in_void_core(gcode: Path, comp: list[float], plate: list[float],
                          center: list[float]) -> dict[str, int]:
    hits = {name: 0 for name in REGIONS["base"]}
    x = y = None
    z = 0.0
    feature = ""
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
            extrusion = float(fields["E"]) if "E" in fields else 0.0
        except ValueError:
            continue
        if feature not in ("Support", "Support interface") or "E" not in fields \
                or extrusion <= 0 or x is None or y is None \
                or old_x is None or old_y is None \
                or math.hypot(x-old_x, y-old_y) <= 1e-6:
            continue
        found = set()
        steps = max(1, math.ceil(math.hypot(x-old_x, y-old_y)/.15))
        for step in range(steps+1):
            t = step/steps
            point = (old_x+(x-old_x)*t, old_y+(y-old_y)*t, z)
            found.update(void_core(source_point(point, comp, plate, center)))
        for name in found:
            hits[name] += 1
    return hits


def slice_angle(angle: int, geometry: dict) -> dict:
    folder = OUT / "orientation-screen" / f"base-x-plus-{angle}-tree"
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
    for stale in ("result.json", "slice-review.3mf", "plate_1.gcode", "plate-preview.png"):
        (folder / stale).unlink(missing_ok=True)
    run = subprocess.run([
        str(BAMBU), "--datadir", str(folder / "app-data"),
        "--load-settings", f"{folder/'machine.json'};{folder/'process.json'}",
        "--load-filaments", str(folder / "filament.json"),
        "--orient", "0", "--rotate-x", str(angle), "--arrange", "1",
        "--ensure-on-bed", "--slice", "0", "--export-3mf", "slice-review.3mf",
        "--outputdir", str(folder), str(OUT / "base.stl"),
    ], cwd=ROOT, text=True, capture_output=True, timeout=240)
    (folder / "bambu-cli.log").write_text(run.stdout + run.stderr)
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
    boxes = hits = core_hits = None
    source_y_build_z = None
    if archive_ok:
        comp, item, center = placement(archive, geometry["parts"]["base"]["bounds_mm"])
        boxes = mapped_boxes(comp, item, center)
        origin = transform(transform((0, 0, 0), comp), item)
        recovered_origin = source_point(origin, comp, item, center)
        if max(abs(recovered_origin[i]-center[i]) for i in range(3)) > .001:
            raise RuntimeError("Could not invert 3MF print placement")
        e_y = transform(transform((0, 1, 0), comp), item)
        source_y_build_z = round(e_y[2]-origin[2], 6)
        if gcode.exists():
            hits = support_crossings(gcode, boxes)
            core_hits = supports_in_void_core(gcode, comp, item, center)
    gcode_text = gcode.read_text(errors="replace") if gcode.exists() else ""
    header = re.search(r"^; total layer number: (\d+)$", gcode_text, re.M)
    layers = len(re.findall(r"^; CHANGE_LAYER$", gcode_text, re.M))
    warnings = [p.get("warning_message") for p in plates if p.get("warning_message")]
    passed = all((run.returncode == 0, native.get("return_code") == 0,
                  archive_ok, gcode.exists(), header is not None,
                  layers == (int(header.group(1)) if header else -1),
                  plate.get("triangle_count") == geometry["parts"]["base"]["triangle_count"],
                  source_y_build_z is not None,
                  abs(source_y_build_z-math.sin(math.radians(angle))) < .01,
                  not warnings))
    return {
        "status": "OFFLINE_SLICE_ONLY" if passed else "SLICE_SCREEN_FAILED",
        "rotation_x_deg": angle,
        "source_y_beam_axis_build_z_component": source_y_build_z,
        "source_stl_sha256": sha(OUT / "base.stl"),
        "cli_return_code": run.returncode,
        "native_return_code": native.get("return_code"),
        "native_warnings": warnings,
        "archive_integrity_pass": archive_ok,
        "gcode_layers": layers,
        "filament_g": sum(f.get("total_used_g", 0) for f in plate.get("filaments", [])),
        "estimated_time_s": plate.get("total_predication"),
        "support_time_s": plate.get("feature_type_times", {}).get("Support"),
        "support_interface_time_s": plate.get("feature_type_times", {}).get("Support interface"),
        "critical_feature_projected_boxes_mm": boxes,
        "support_extrusion_segments_in_critical_feature_boxes": hits,
        "sampled_support_extrusion_segments_in_void_cores": core_hits,
        "slice_3mf_sha256": sha(archive) if archive.exists() else None,
        "preview_sha256": sha(folder / "plate-preview.png")
        if (folder / "plate-preview.png").exists() else None,
    }


def main() -> int:
    geometry = json.loads(GEOMETRY.read_text())
    current = json.loads(SOURCE_SLICE.read_text())
    if geometry["status"] != "SERVICE_FORK_NOMINAL_ASSEMBLY_PATH_ONLY" \
            or geometry["parts"]["base"]["sha256"] != sha(OUT / "base.stl") \
            or current["geometry_review_sha256"] != sha(GEOMETRY):
        raise RuntimeError("The reviewed service-fork geometry/slice is stale")
    rows = {f"x{angle}": slice_angle(angle, geometry) for angle in ANGLES}
    baseline = current["orientations"]["base-x-plus-90-tree"]
    rows["x90"] = {
        "status": "OFFLINE_SLICE_ONLY", "rotation_x_deg": 90,
        "source_y_beam_axis_build_z_component": 1.0,
        "source_stl_sha256": baseline["source_stl_sha256"],
        "native_warnings": baseline["native_warnings"],
        "gcode_layers": baseline["gcode_layers"],
        "filament_g": baseline["filament_g"],
        "estimated_time_s": baseline["estimated_time_s"],
        "support_time_s": None,
        "support_interface_time_s": None,
        "support_extrusion_segments_in_critical_feature_boxes":
            baseline["support_extrusion_segments_crossing_critical_feature_with_0p25mm_margin"],
        "sampled_support_extrusion_segments_in_void_cores": {name: 0 for name in REGIONS["base"]},
        "slice_3mf_sha256": baseline["slice_3mf_sha256"],
        "preview_sha256": baseline["preview_sha256"],
    }
    report = {
        "status": "ORIENTATION_COMPARISON_ONLY",
        "source_sha256": {
            str(path.relative_to(ROOT)): sha(path)
            for path in (Path(__file__).resolve(), GEOMETRY, SOURCE_SLICE,
                         CONFIG / "machine.json", CONFIG / "filament.json",
                         CONFIG / "process.json")
        },
        "machine": "Bambu Lab X1 Carbon; 0.4 mm nozzle; Textured PEI",
        "material_profile": "Generic PETG",
        "process": "0.2 mm; 4 walls; 25% infill; 5 mm brim; tree support from bed only",
        "void_scan_step_mm": .15,
        "void_scan_limit": "Support extrusion segment centerlines sampled in nominal cylinder and inscribed hexagon cores; extrusion width, printed tolerance and support removal are not certified.",
        "orientations": rows,
        "best_orientation_selected": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for name, row in rows.items():
        print(name, row["status"], "grams", round(row["filament_g"], 3),
              "layers", row["gcode_layers"], "beam-Z", row["source_y_beam_axis_build_z_component"],
              "support-hits", row["support_extrusion_segments_in_critical_feature_boxes"],
              "core-hits", row["sampled_support_extrusion_segments_in_void_cores"],
              flush=True)
    return 1 if any(row["status"] == "SLICE_SCREEN_FAILED" for row in rows.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
