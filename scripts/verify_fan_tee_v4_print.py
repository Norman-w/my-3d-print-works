#!/usr/bin/env python3
"""Read-only evidence for a one-part v4 native slice, never a print dispatch."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/fan-tee-direct-print-v4-20261007/print"
CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def support_paths(gcode: str) -> tuple[list[dict], Counter]:
    role, layer, position, epos, relative_e = "", None, [0., 0., 0.], 0., True
    segments, counts = [], Counter()
    for line in gcode.splitlines():
        if line.startswith("; FEATURE: "):
            role = line[11:].strip()
        if line.startswith("; Z_HEIGHT: "):
            layer = float(line.split(":", 1)[1])
        code = line.split(";", 1)[0].strip()
        if code == "M83":
            relative_e = True
        elif code == "M82":
            relative_e = False
        if code.startswith("G92"):
            values = dict((k, float(v)) for k, v in re.findall(r"([XYZE])([-+0-9.eE]+)", code))
            epos = values.get("E", epos)
            continue
        if not re.match(r"^G[01]\s", code):
            continue
        values = dict((k, float(v)) for k, v in re.findall(r"([XYZE])([-+0-9.eE]+)", code))
        nxt = [values.get(axis, position[i]) for i, axis in enumerate("XYZ")]
        extrusion = values.get("E", 0) if relative_e else values.get("E", epos) - epos
        if "E" in values:
            epos = epos + values["E"] if relative_e else values["E"]
        if layer is not None and extrusion > 0 and math.hypot(nxt[0]-position[0], nxt[1]-position[1]) > 0 and role in {"Support", "Support interface"}:
            counts[role] += 1
            segments.append({"role": role, "z": layer, "start": position[:], "end": nxt[:]})
        position = nxt
    return segments, counts


def bounds(segments: list[dict]):
    if not segments:
        return None
    points = [p for s in segments for p in (s["start"], s["end"])]
    return [[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)]


def native_geometry_and_contacts(project: Path, segments: list[dict]) -> dict:
    """Project-specific final STL identity and both radial lug contacts."""
    stl = OUT.parent / "stl/fan-tee-v4-connector-clean.stl"
    data = stl.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    source = [struct.unpack_from("<12fH", data, 84 + 50*i)[3:12] for i in range(count)]
    with ZipFile(project) as archive:
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
        component = next(root.iter(CORE + "component"))
        assert component.get("transform") == "1 0 0 0 1 0 0 0 1 0 0 0", "Native single-part transform changed"
        model = ET.fromstring(archive.read("3D/Objects/object_1.model"))
        vertices = [tuple(float(v.get(a)) for a in "xyz") for v in model.iter(CORE + "vertex")]
        faces = [tuple(int(f.get(a)) for a in ("v1", "v2", "v3")) for f in model.iter(CORE + "triangle")]
        transform = [float(x) for x in next(root.iter(CORE + "item")).get("transform").split()]
        settings = ET.fromstring(archive.read("Metadata/model_settings.config"))
        part = next(settings.iter("part"))
        metadata = {m.get("key"): m.get("value") for m in part.iter("metadata")}
        offset = [float(metadata[f"source_offset_{a}"]) for a in "xyz"]
    reconstructed = [tuple(vertices[i][a] + offset[a] for i in f for a in range(3)) for f in faces]
    def signature(triangles):
        return Counter(tuple(sorted(tuple(round(v, 3) for v in face[i:i+3]) for i in (0, 3, 6))) for face in triangles)
    upright_unit_scale = (all(abs(transform[i]) < 1e-8 for i in (2, 5, 6, 7))
                          and abs(transform[8]-1) < 1e-8
                          and abs(transform[0]**2+transform[1]**2-1) < 1e-8
                          and abs(transform[3]**2+transform[4]**2-1) < 1e-8
                          and abs(transform[0]*transform[3]+transform[1]*transform[4]) < 1e-8)
    assert upright_unit_scale, "Expected upright unscaled print pose"
    def local(point):
        x, y = point[0]-transform[9], point[1]-transform[10]
        return (transform[0]*x+transform[1]*y+offset[0],
                transform[3]*x+transform[4]*y+offset[1], point[2]-transform[11]+offset[2])
    contacts = []
    for side in (-1, 1):
        points = [local(p) for s in segments if s["role"] == "Support interface" and s["z"] >= 7.79
                  for p in (s["start"], s["end"]) if local(p)[0]*side > 0]
        directly_below = [p for p in points if 17.7 <= abs(p[0]) <= 21.1 and abs(p[1]) < 1.5]
        gaps = [-7.5-math.sqrt(9-p[1]**2)-p[2] for p in directly_below]
        contacts.append({"lug_side_x": side, "interface_endpoints_below_lug": len(gaps),
                         "vertical_gap_to_round_lug_mm": [min(gaps), max(gaps)] if gaps else None,
                         "contact_screen_pass": bool(gaps) and .15 <= min(gaps) <= .3 and max(gaps) < .6})
    return {"stl": str(stl), "stl_sha256": sha(stl),
            "all_triangles_match_stl_at_0_001_mm": signature(source) == signature(reconstructed),
            "upright_unit_scale": upright_unit_scale, "contacts": contacts,
            "both_lugs_supported": all(c["contact_screen_pass"] for c in contacts),
            "digital_contact_screen_not_physical_support_acceptance": True}


def audit(package: Path, support_ceiling: float, geometry_package: Path | None = None) -> dict:
    with ZipFile(package) as archive:
        settings = json.loads(archive.read("Metadata/project_settings.config"))
        gcode_names = [n for n in archive.namelist() if n.endswith(".gcode")]
        assert len(gcode_names) == 1, "Expected exactly one sliced plate"
        gcode = archive.read(gcode_names[0]).decode("utf-8")
        slice_info = archive.read("Metadata/slice_info.config").decode("utf-8") if "Metadata/slice_info.config" in archive.namelist() else None
    # A native sliced-only export deliberately has no model mesh. Bind it to
    # the separately saved editable native project, never pretend it has one.
    geometry_package = geometry_package or package
    with ZipFile(geometry_package) as archive:
        geometry_settings = json.loads(archive.read("Metadata/project_settings.config"))
        mesh_objects = []
        for name in archive.namelist():
            if name.endswith(".model"):
                model = ET.fromstring(archive.read(name))
                for obj in model.iter(CORE + "object"):
                    mesh = obj.find(CORE + "mesh")
                    if mesh is not None:
                        mesh_objects.append({"member": name, "id": obj.get("id"),
                                             "triangles": len(list(mesh.iter(CORE + "triangle")))})
        model_settings = ET.fromstring(archive.read("Metadata/model_settings.config"))
        subtypes = [p.get("subtype") for p in model_settings.iter("part")]
        instances = list(model_settings.iter("model_instance"))
    baseline = json.loads((OUT / "config/native-baseline.json").read_text())
    segments, counts = support_paths(gcode)
    interface = [s for s in segments if s["role"] == "Support interface"]
    high = [s for s in segments if s["z"] > support_ceiling]
    preparation = gcode.split("; Z_HEIGHT:", 1)[0]
    startup_markers = {label: bool(re.search(pattern, preparation, re.M)) for label, pattern in {
        "homing_command": r"^\s*G28(?:\s|$)",
        "bed_level_command": r"^\s*G29(?:\s|$)",
        "bed_heat_wait": r"^\s*M190(?:\s|$)",
        "nozzle_heat_wait": r"^\s*M109(?:\s|$)",
        "ams_selection": r"^\s*M620(?:\s|$)",
    }.items()}
    start_hash = hashlib.sha256(settings["machine_start_gcode"].encode()).hexdigest()
    end_hash = hashlib.sha256(settings["machine_end_gcode"].encode()).hexdigest()
    checks = {
        "one_mesh": len(mesh_objects) == 1 and mesh_objects[0]["triangles"] > 0,
        "no_embedded_support_objects": all(t == "normal_part" for t in subtypes) and len(subtypes) == 1,
        "x1c_04": settings.get("printer_settings_id") == "Bambu Lab X1 Carbon 0.4 nozzle" and settings.get("nozzle_diameter") == ["0.4"],
        "petg": settings.get("filament_type") == ["PETG"],
        "native_startup_preserved": start_hash == baseline["native_start_gcode_sha256"],
        "native_end_preserved": end_hash == baseline["native_end_gcode_sha256"],
        "preparation_commands_present": all(startup_markers.values()),
        "ordinary_and_interface_support_exist": counts["Support"] > 0 and counts["Support interface"] > 0,
        "no_support_above_project_lug_zone": not high,
        "one_geometry_instance": len(instances) == 1,
        "geometry_slice_settings_match": settings == geometry_settings,
    }
    contact_review = None
    if geometry_package != package:
        contact_review = native_geometry_and_contacts(geometry_package, segments)
        checks["actual_stl_identity"] = contact_review["all_triangles_match_stl_at_0_001_mm"]
        checks["both_lug_contacts"] = contact_review["both_lugs_supported"]
        checks["native_x1c_model_id"] = 'key="printer_model_id" value="BL-P001"' in (slice_info or "")
    return {
        "status": ("DIGITAL_NATIVE_SLICE_AND_LUG_CONTACT_PASS" if contact_review else
                   "NUMERICAL_SLICE_SCREEN_PASS_CONTACT_REVIEW_REQUIRED") if all(checks.values()) else "SLICE_REVIEW_REQUIRED",
        "package": str(package), "package_sha256": sha(package), "checks": checks,
        "geometry_package": str(geometry_package), "geometry_package_sha256": sha(geometry_package),
        "mesh_objects": mesh_objects, "part_subtypes": subtypes,
        "layers": gcode.count("; Z_HEIGHT:"), "startup_markers": startup_markers,
        "startup_commands_do_not_prove_execution_or_checkbox_state": True,
        "support_counts": dict(counts), "all_support_bounds_mm": bounds(segments),
        "support_interface_bounds_mm": bounds(interface),
        "support_interface_layer_z_mm": sorted({s["z"] for s in interface}),
        "project_lug_support_ceiling_print_z_mm": support_ceiling,
        "support_segments_above_ceiling": len(high),
        "support_contact_geometry_review_still_required": contact_review is None,
        "contact_review": contact_review,
        "slice_info_xml": slice_info,
        "support_settings": {k: settings.get(k) for k in ["enable_support", "support_type", "support_threshold_angle", "support_on_build_plate_only", "support_remove_small_overhang", "support_top_z_distance"]},
        "sent_to_printer": False, "physical_acceptance": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--lug-support-ceiling", type=float, required=True,
                        help="Project-specific print-Z ceiling, not a reusable thread rule")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--geometry-package", type=Path,
                        help="Paired editable native project for a sliced-only native export")
    args = parser.parse_args()
    report = audit(args.package.resolve(), args.lug_support_ceiling,
                   args.geometry_package.resolve() if args.geometry_package else None)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n")
    print(text)
    return 0 if all(report["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
