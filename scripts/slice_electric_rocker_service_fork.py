#!/usr/bin/env python3
"""Offline X1C/PETG slicing screen for the two unreleased service-fork parts."""

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
OUT = ROOT / "output/electric-rocker-service-fork-screen"
CONFIG = ROOT / "output/print-review/config"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
PROFILES = (("base-x-plus-90-tree", "base", 90, True),
            ("rear-x-minus-90-tree", "rear", -90, True))
PIVOT_X = 85-math.sqrt(75*75-15*15)
NUT_R = (5.8/math.cos(math.radians(30)))/2
REGIONS = {
    "base": {
        "bolt_lower": ((13.3, 60.9, -15.7), (16.7, 68.1, -12.3)),
        "bolt_upper": ((13.3, 60.9, .3), (16.7, 68.1, 3.7)),
        "nut_lower": ((15-NUT_R, 65.2, -14-NUT_R),
                      (15+NUT_R, 68.1, -14+NUT_R)),
        "nut_upper": ((15-NUT_R, 65.2, 2-NUT_R),
                      (15+NUT_R, 68.1, 2+NUT_R)),
        "pivot_bore": ((PIVOT_X-3.2, 57.9, 25-3.2),
                       (PIVOT_X+3.2, 61.1, 25+3.2)),
    },
    "rear": {
        "bolt_lower": ((13.3, 67.9, -15.7), (16.7, 76.1, -12.3)),
        "bolt_upper": ((13.3, 67.9, .3), (16.7, 76.1, 3.7)),
        "key_pocket": ((9.7, 67.9, -8.3), (20.3, 72.3, -3.7)),
        "pivot_bore": ((PIVOT_X-3.2, 68.9, 25-3.2),
                       (PIVOT_X+3.2, 73.1, 25+3.2)),
    },
}
POCKET_OPEN_FACES = {
    "base": {"nut_lower": "high_y", "nut_upper": "high_y"},
    "rear": {"key_pocket": "low_y"},
}


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def transform(point: tuple[float, float, float], v: list[float]) -> tuple[float, float, float]:
    x, y, z = point
    return (v[0]*x+v[3]*y+v[6]*z+v[9],
            v[1]*x+v[4]*y+v[7]*z+v[10],
            v[2]*x+v[5]*y+v[8]*z+v[11])


def mapped_regions(archive: Path, source_bounds: dict,
                   regions: dict[str, tuple[tuple[float, ...], tuple[float, ...]]],
                   open_faces: dict[str, str]) -> tuple[dict, dict]:
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
          "p": "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"}
    with zipfile.ZipFile(archive) as z:
        model = ET.fromstring(z.read("3D/3dmodel.model"))
        components = model.findall(".//m:component", ns)
        items = model.findall(".//m:item", ns)
        if len(components) != 1 or len(items) != 1:
            raise RuntimeError("Expected one 3MF part instance")
        source_path = components[0].attrib[f"{{{ns['p']}}}path"].lstrip("/")
        source = ET.fromstring(z.read(source_path))
        vertices = source.findall(".//m:vertex", ns)
        if not vertices:
            raise RuntimeError("No 3MF mesh vertices")
        comp = [float(value) for value in components[0].attrib["transform"].split()]
        item = [float(value) for value in items[0].attrib["transform"].split()]
        if len(comp) != 12 or len(item) != 12:
            raise RuntimeError("Unexpected 3MF transform")
        actual = [[min(float(v.attrib[axis]) for v in vertices),
                   max(float(v.attrib[axis]) for v in vertices)] for axis in "xyz"]
    center = [(source_bounds["min"][i]+source_bounds["max"][i])/2 for i in range(3)]
    for axis in range(3):
        for edge in range(2):
            expected = source_bounds["min" if edge == 0 else "max"][axis]-center[axis]
            if abs(actual[axis][edge]-expected) > .01:
                raise RuntimeError("3MF source mesh bounds do not match reviewed STL")
    result = {}
    opens_upward = {}
    for name, (lo, hi) in regions.items():
        corners = [(x, y, z) for x in (lo[0], hi[0])
                   for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        machine = [transform(transform(tuple(p[i]-center[i] for i in range(3)),
                                       comp), item) for p in corners]
        box = [[min(p[i] for p in machine), max(p[i] for p in machine)]
               for i in range(3)]
        # The pocket and pivot axes run along CAD Y and must become machine Z.
        if abs((box[2][1]-box[2][0])-(hi[1]-lo[1])) > .02:
            raise RuntimeError(f"{name} is not vertical after 3MF placement")
        result[name] = [[round(edge, 4) for edge in axis] for axis in box]
        if name in open_faces:
            center_x = (lo[0]+hi[0])/2
            center_z = (lo[2]+hi[2])/2
            machine_low = transform(transform(
                (center_x-center[0],lo[1]-center[1],center_z-center[2]),
                comp), item)[2]
            machine_high = transform(transform(
                (center_x-center[0],hi[1]-center[1],center_z-center[2]),
                comp), item)[2]
            opens_upward[name] = (machine_high > machine_low if
                                  open_faces[name] == "high_y" else
                                  machine_low > machine_high)
            if not opens_upward[name]:
                raise RuntimeError(f"{name} pocket mouth is not on the upward face")
    return result, opens_upward


def support_crossings(gcode: Path, boxes: dict[str, list[list[float]]]) -> dict[str, int]:
    margin = .25  # about half a 0.4 mm extrusion width plus a small allowance
    hits = {name: 0 for name in boxes}
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
        if (feature not in ("Support", "Support interface") or "E" not in fields
                or extrusion <= 0 or x is None or y is None
                or old_x is None or old_y is None
                or math.hypot(x-old_x, y-old_y) <= 1e-6):
            # G1 E... with no XY movement is a prime/unretract, not a
            # support path crossing a functional void.
            continue
        for name, box in boxes.items():
            if not box[2][0] < z < box[2][1]:
                continue
            xlo, xhi = box[0][0]-margin, box[0][1]+margin
            ylo, yhi = box[1][0]-margin, box[1][1]+margin
            if max(min(old_x, x), xlo) <= min(max(old_x, x), xhi) \
                    and max(min(old_y, y), ylo) <= min(max(old_y, y), yhi):
                hits[name] += 1
    return hits


def slice_part(label: str, part: str, rotation_x: int,
               support: bool, geometry: dict) -> dict:
    folder = OUT / "slices" / label
    folder.mkdir(parents=True, exist_ok=True)
    for profile in ("machine", "filament"):
        shutil.copy2(CONFIG / f"{profile}.json", folder / f"{profile}.json")
    process = json.loads((CONFIG / "process.json").read_text())
    process.update(enable_support="1" if support else "0",
                   support_type="tree(auto)",
                   support_on_build_plate_only="1",
                   layer_height="0.2", initial_layer_print_height="0.2",
                   wall_loops="4", sparse_infill_density="25%",
                   brim_type="outer_only", brim_width="5")
    (folder / "process.json").write_text(json.dumps(process, indent=2) + "\n")
    for stale in ("result.json", "slice-review.3mf", "plate_1.gcode", "plate-preview.png"):
        (folder / stale).unlink(missing_ok=True)
    mesh = OUT / f"{part}.stl"
    cmd = [str(BAMBU), "--datadir", str(folder / "app-data"),
           "--load-settings", f"{folder/'machine.json'};{folder/'process.json'}",
           "--load-filaments", str(folder / "filament.json"),
           "--orient", "0", "--rotate-x", str(rotation_x), "--arrange", "1",
           "--ensure-on-bed", "--slice", "0", "--export-3mf", "slice-review.3mf",
           "--outputdir", str(folder), str(mesh)]
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
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
    grams = sum(f.get("total_used_g", 0) for f in plate.get("filaments", []))
    warnings = [p.get("warning_message") for p in plates if p.get("warning_message")]
    boxes, opens_upward = mapped_regions(
        archive, geometry["parts"][part]["bounds_mm"], REGIONS[part],
        POCKET_OPEN_FACES[part]) if archive_ok else (None, None)
    hits = support_crossings(gcode, boxes) if boxes is not None and gcode.exists() else None
    passed = all((run.returncode == 0, native.get("return_code") == 0,
                  archive_ok, gcode.exists(), header is not None,
                  layers == (int(header.group(1)) if header else -1),
                  "; FEATURE: Outer wall" in gcode_text,
                  plate.get("triangle_count") == geometry["parts"][part]["triangle_count"],
                  grams > 0, not warnings,
                  opens_upward is not None and all(opens_upward.values()),
                  hits is not None and all(value == 0 for value in hits.values())))
    return {
        "status": "SLICED_UNRELEASED" if passed else "SLICE_SCREEN_FAILED",
        "part": part, "source_stl_sha256": sha(mesh),
        "rotation_x_deg": rotation_x, "support": "tree, build plate only" if support else "off",
        "machine": "Bambu Lab X1 Carbon, 0.4 mm nozzle, Textured PEI Plate",
        "material_profile": "Generic PETG", "layer_height_mm": .2,
        "wall_loops": 4, "infill": "25%", "brim_mm": 5,
        "cli_return_code": run.returncode,
        "native_return_code": native.get("return_code"),
        "native_warnings": warnings, "archive_integrity_pass": archive_ok,
        "gcode_layers": layers, "header_layers": int(header.group(1)) if header else 0,
        "filament_g": grams, "estimated_time_s": plate.get("total_predication"),
        "native_triangle_count": plate.get("triangle_count"),
        "gcode_sha256": sha(gcode) if gcode.exists() else None,
        "slice_3mf_sha256": sha(archive) if archive.exists() else None,
        "preview_sha256": sha(folder / "plate-preview.png")
        if (folder / "plate-preview.png").exists() else None,
        "critical_feature_machine_boxes_mm": boxes,
        "critical_pockets_open_upward_after_3mf_rotation": opens_upward,
        "support_extrusion_segments_crossing_critical_feature_with_0p25mm_margin": hits,
    }


def main() -> int:
    review_path = OUT / "review.json"
    geometry = json.loads(review_path.read_text())
    if (geometry["status"] != "SERVICE_FORK_NOMINAL_ASSEMBLY_PATH_ONLY"
            or geometry["manufacturing_release"]
            or any(geometry["parts"][part]["sha256"] != sha(OUT / f"{part}.stl")
                   for part in ("base", "rear"))):
        raise RuntimeError("Rebuild the service-fork geometry before slicing")
    rows = {}
    failures = []
    for label, part, rotation, support in PROFILES:
        row = slice_part(label, part, rotation, support, geometry)
        rows[label] = row
        if row["status"] != "SLICED_UNRELEASED":
            failures.append(label)
        print(f"{label}: {row['status']}, {row['filament_g']:.3f} g, "
              f"support hits={row['support_extrusion_segments_crossing_critical_feature_with_0p25mm_margin']}",
              flush=True)
    report = {
        "status": "SERVICE_FORK_SLICED_UNRELEASED" if not failures
                  else "SERVICE_FORK_SLICE_SCREEN_FAILED",
        "geometry_review_sha256": sha(review_path),
        "source_sha256": {
            "scripts/slice_electric_rocker_service_fork.py": sha(Path(__file__).resolve()),
            "output/print-review/config/machine.json": sha(CONFIG / "machine.json"),
            "output/print-review/config/filament.json": sha(CONFIG / "filament.json"),
            "output/print-review/config/process.json": sha(CONFIG / "process.json"),
        },
        "orientations": rows, "printer_sent": False,
        "manufacturing_release": False, "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "slice-review.json").write_text(json.dumps(report, ensure_ascii=False,
                                                  indent=2) + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
