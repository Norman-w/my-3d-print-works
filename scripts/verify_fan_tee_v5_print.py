#!/usr/bin/env python3
"""Audit the paired native v5 project/slice; never contact a printer.

Checks five exact clean STLs, preserved startup, upright placement, and support
confined to the connector's two inherited radial lugs. This is digital evidence,
not proof of machine execution, successful printing or mechanical fit.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import product
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from prepare_fan_tee_v5_print import binary_mesh, sha

CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
PROD = "{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}"


def extrusion_paths(gcode):
    role, layer, point, epos, relative = "", None, [0., 0., 0.], 0., True
    width = None
    for line in gcode.splitlines():
        if line.startswith("; FEATURE: "):
            role = line[11:].strip()
        if line.startswith("; Z_HEIGHT: "):
            layer = float(line.split(":", 1)[1])
        if line.startswith("; LINE_WIDTH: "):
            width = float(line.split(":", 1)[1])
        code = line.split(";", 1)[0].strip()
        if code == "M83":
            relative = True
        elif code == "M82":
            relative = False
        if code.startswith("G92"):
            values = dict((k, float(v)) for k, v in re.findall(r"([XYZE])([-+0-9.eE]+)", code))
            epos = values.get("E", epos)
            continue
        if not re.match(r"^G[01]\s", code):
            continue
        values = dict((k, float(v)) for k, v in re.findall(r"([XYZE])([-+0-9.eE]+)", code))
        nxt = [values.get(axis, point[i]) for i, axis in enumerate("XYZ")]
        extrusion = values.get("E", 0) if relative else values.get("E", epos) - epos
        if "E" in values:
            epos = epos + values["E"] if relative else values["E"]
        if layer is not None and extrusion > 0 and math.hypot(nxt[0]-point[0], nxt[1]-point[1]) > 0:
            yield {"role": role, "z": layer, "width": width, "start": point[:], "end": nxt[:]}
        point = nxt


def support_paths(gcode):
    segments, counts = [], Counter()
    for segment in extrusion_paths(gcode):
        if segment["role"] in {"Support", "Support interface"}:
            segments.append(segment)
            counts[segment["role"]] += 1
    return segments, counts


def nozzle_xy_offset(settings):
    values = settings.get("extruder_offset", ["0x0"])
    assert len(values) == 1, "Single-extruder package required"
    offset = tuple(float(x) for x in values[0].lower().split("x"))
    assert len(offset) == 2 and all(math.isfinite(x) for x in offset)
    return offset


def thread_wall_screen(gcode, records, mother_z_interval, xy_offset=(0., 0.)):
    """Screen native wall-path radii, not a strength or full bead-volume proof.

    Each sampled layer intersects all helix phases around the circular wall.
    Verify both root and crest excursions survived slicing at the toolpath
    centerline, with >=0.5 mm contrast rather than a plain cylinder.
    """
    layers = {r["role"]: {} for r in records}
    for segment in extrusion_paths(gcode):
        if segment["role"] != "Outer wall":
            continue
        for record in records:
            tf, offset = record["transform"], record["source_offset"]
            local_z = segment["z"]-tf[11]+offset[2]
            is_mother = record["role"] == "connector"
            lo, hi = mother_z_interval if is_mother else (8, 24)
            if not lo <= local_z <= hi:
                continue
            x, y = (segment["end"][i]+xy_offset[i]-tf[9+i] for i in (0, 1))
            radius = math.hypot(x, y)
            if not (20.0 <= radius <= 22.0 if is_mother else 19.5 <= radius <= 21.0):
                continue
            row = layers[record["role"]].setdefault(segment["z"], [math.inf, -math.inf, 0])
            row[0], row[1], row[2] = min(row[0], radius), max(row[1], radius), row[2]+1
    results = []
    for role, sample in layers.items():
        spans = [row[1]-row[0] for row in sample.values()]
        results.append({"role": role, "sampled_layers": len(sample),
                        "smallest_radial_root_crest_contrast_mm": min(spans) if spans else None,
                        "smallest_wall_segment_count_per_layer": min(r[2] for r in sample.values()) if sample else 0,
                        "pass": len(sample) >= 60 and min(spans) > .5})
    return {"parts": results, "pass": all(r["pass"] for r in results),
            "scope": "Native outer-wall centerline radial excursion over fully developed thread layers; not bead fusion, load or physical-fit proof."}


def signature(vertices, faces):
    def triangle(face):
        points = tuple(tuple(round(x, 3) for x in vertices[i]) for i in face)
        # Face order and starting vertex can change, but winding must not.
        return min(points, points[1:]+points[:1], points[2:]+points[:2])
    return Counter(triangle(face) for face in faces)


def mesh_equivalence(vertices, faces, original_vertices, original_faces, tolerance=.0001):
    """Bijective vertex comparison with cyclic (not reversed) face winding.

    Native float32 re-centering can shift a coordinate by a few micrometres
    across a rounding boundary. Fixed-decimal signatures then incorrectly
    reject unchanged triangles. This uses an actual bounded distance, not
    a looser rounding bin, and rejects merged/ambiguous vertices.
    """
    if len(vertices) != len(original_vertices) or len(faces) != len(original_faces):
        return False, None
    grid = {}
    for i, point in enumerate(original_vertices):
        key = tuple(math.floor(x/tolerance) for x in point)
        grid.setdefault(key, []).append(i)
    mapping, used, maximum = [], set(), 0.
    for point in vertices:
        key = tuple(math.floor(x/tolerance) for x in point)
        matches = []
        for delta in product((-1, 0, 1), repeat=3):
            for i in grid.get(tuple(key[a]+delta[a] for a in range(3)), ()):
                distance = max(abs(point[a]-original_vertices[i][a]) for a in range(3))
                if distance <= tolerance:
                    matches.append((i, distance))
        if len(matches) != 1 or matches[0][0] in used:
            return False, None
        i, distance = matches[0]
        mapping.append(i)
        used.add(i)
        maximum = max(maximum, distance)
    def cyclic(face):
        points = tuple(face)
        return min(points, points[1:]+points[:1], points[2:]+points[:2])
    actual = Counter(cyclic(mapping[i] for i in face) for face in faces)
    expected = Counter(cyclic(face) for face in original_faces)
    return actual == expected, maximum


def is_upright(transform):
    return (len(transform) == 12 and all(abs(transform[i]) < 1e-8 for i in (2, 5, 6, 7))
            and abs(transform[8]-1) < 1e-8
            and abs(transform[0]**2+transform[1]**2-1) < 1e-8
            and abs(transform[3]**2+transform[4]**2-1) < 1e-8
            and abs(transform[0]*transform[3]+transform[1]*transform[4]) < 1e-8
            and abs(transform[0]*transform[4]-transform[1]*transform[3]-1) < 1e-8)


def geometry(project, layout):
    expected = {Path(p["file"]).name: p for p in layout["parts"]}
    records = []
    with ZipFile(project) as archive:
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
        assert root.get("unit") == "millimeter"
        model_settings = ET.fromstring(archive.read("Metadata/model_settings.config"))
        objects = {o.get("id"): o for o in root.iter(CORE+"object")}
        configs = {o.get("id"): o for o in model_settings.findall("object")}
        assert len(list(root.iter(CORE+"item"))) == len(expected) == 5
        assert len(list(model_settings.iter("model_instance"))) == 5
        assert len(list(model_settings.iter("part"))) == 5
        for item in root.iter(CORE+"item"):
            config = configs[item.get("objectid")]
            part = config.find("part")
            assert part is not None and part.get("subtype") == "normal_part"
            meta = {m.get("key"): m.get("value") for m in part.iter("metadata") if m.get("key")}
            name = Path(meta["source_file"]).name
            source = expected.pop(name)
            stl = Path(source["file"])
            assert sha(stl) == source["sha256"], f"Source changed: {name}"
            original_vertices, original_faces, box = binary_mesh(stl)
            offset = [float(meta["source_offset_"+a]) for a in "xyz"]
            component = objects[item.get("objectid")].find(".//"+CORE+"component")
            assert component is not None
            ct = [float(x) for x in component.get("transform", "1 0 0 0 1 0 0 0 1 0 0 0").split()]
            assert ct == [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0], "Unexpected part transform"
            mesh_root = ET.fromstring(archive.read(component.get(PROD+"path").lstrip("/")))
            leaf = next(o for o in mesh_root.iter(CORE+"object") if o.get("id") == component.get("objectid"))
            vertices = [tuple(float(v.get(a))+offset[i] for i, a in enumerate("xyz")) for v in leaf.iter(CORE+"vertex")]
            faces = [tuple(int(f.get(a)) for a in ("v1", "v2", "v3")) for f in leaf.iter(CORE+"triangle")]
            transform = [float(x) for x in item.get("transform").split()]
            assert is_upright(transform), f"Expected upright unit-scale pose: {name}"
            assert item.get("printable", "1") == "1"
            assert abs(box[2][0]-offset[2]+transform[11]) < .002, f"Not on bed: {name}"
            footprint = [[min(transform[i]*(v[0]-offset[0])+transform[3+i]*(v[1]-offset[1])+transform[9+i] for v in vertices)-6.5,
                          max(transform[i]*(v[0]-offset[0])+transform[3+i]*(v[1]-offset[1])+transform[9+i] for v in vertices)+6.5] for i in (0, 1)]
            assert all(24 < lo < hi < 246 for lo, hi in footprint)
            for prior in records:
                other = prior["xy_with_brim_mm"]
                assert any(footprint[i][1] < other[i][0] or other[i][1] < footprint[i][0] for i in (0, 1))
            equivalent, maximum_error = mesh_equivalence(vertices, faces, original_vertices, original_faces)
            records.append({"role": source["role"], "source": name, "sha256": sha(stl), "triangles": len(faces),
                            "all_triangles_match_at_0_001_mm": equivalent,
                            "mesh_tolerance_mm": .0001, "maximum_vertex_component_error_mm": maximum_error,
                            "upright_unscaled_on_bed": True, "transform": transform, "source_offset": offset,
                            "xy_with_brim_mm": footprint})
    assert not expected
    return records


def audit(package, project, layout_path, support_ceiling):
    layout = json.loads(layout_path.read_text())
    baseline = json.loads((layout_path.parent/"config/native-baseline.json").read_text())
    records = geometry(project, layout)
    with ZipFile(package) as archive:
        settings = json.loads(archive.read("Metadata/project_settings.config"))
        names = [n for n in archive.namelist() if n.endswith(".gcode")]
        assert len(names) == 1
        gcode = archive.read(names[0]).decode()
        slice_info = ET.fromstring(archive.read("Metadata/slice_info.config"))
        assert len(slice_info.findall("plate")) == 1
        plate_info = {m.get("key"): m.get("value") for m in slice_info.find("plate").findall("metadata")}
        sliced_objects = list(slice_info.iter("object"))
    with ZipFile(project) as archive:
        project_settings = json.loads(archive.read("Metadata/project_settings.config"))
    segments, counts = support_paths(gcode)
    xy_offset = nozzle_xy_offset(settings)
    wall_screen = thread_wall_screen(gcode, records, (42, 96), xy_offset)
    connector = next(r for r in records if r["role"] == "connector")
    tf, offset = connector["transform"], connector["source_offset"]
    def local(p):
        x, y = p[0]+xy_offset[0]-tf[9], p[1]+xy_offset[1]-tf[10]
        return (tf[0]*x+tf[1]*y+offset[0], tf[3]*x+tf[4]*y+offset[1], p[2]-tf[11]+offset[2])
    outside = [s for s in segments if s["z"] > support_ceiling or any(math.hypot(*local(p)[:2]) > 30 for p in (s["start"], s["end"]))]
    contacts = []
    for side in (-1, 1):
        points = [local(p) for s in segments if s["role"] == "Support interface" and s["z"] >= 7.79 for p in (s["start"], s["end"])]
        below = [p for p in points if 17.7 <= p[0]*side <= 21.1 and abs(p[1]) < 1.5]
        gaps = [-7.5-math.sqrt(9-p[1]**2)-p[2] for p in below]
        contacts.append({"side": side, "interface_endpoints": len(gaps), "gap_mm": [min(gaps), max(gaps)] if gaps else None,
                         "pass": bool(gaps) and .15 <= min(gaps) <= .30 and max(gaps) < .60})
    prep = gcode.split("; Z_HEIGHT:", 1)[0]
    markers = {name: bool(re.search(pattern, prep, re.M)) for name, pattern in {
        "home": r"^\s*G28(?:\s|$)", "level": r"^\s*G29(?:\s|$)", "bed_wait": r"^\s*M190(?:\s|$)",
        "nozzle_wait": r"^\s*M109(?:\s|$)", "ams": r"^\s*M620(?:\s|$)"}.items()}
    checks = {
        "five_exact_source_meshes": len(records) == 5 and all(r["all_triangles_match_at_0_001_mm"] for r in records),
        "five_sliced_objects": len(sliced_objects) == 5
            and all(o.get("skipped", "false") == "false" for o in sliced_objects)
            and Counter(o.get("name") for o in sliced_objects) == Counter(r["source"] for r in records),
        "native_geometry_slice_settings_match": project_settings == settings,
        "x1c_04": settings.get("printer_settings_id") == "Bambu Lab X1 Carbon 0.4 nozzle" and settings.get("nozzle_diameter") == ["0.4"] and plate_info.get("printer_model_id") == "BL-P001",
        "petg": settings.get("filament_type") == ["PETG"],
        "startup_preserved": hashlib.sha256(settings["machine_start_gcode"].encode()).hexdigest() == baseline["startup_sha256"],
        "end_preserved": hashlib.sha256(settings["machine_end_gcode"].encode()).hexdigest() == baseline["end_sha256"],
        "prep_commands_exist": all(markers.values()),
        "linear_extrusion_paths": settings.get("enable_arc_fitting") == "0",
        "tree_support_enabled": settings.get("enable_support") == "1" and settings.get("support_type") == "tree(auto)",
        "both_lug_contacts": all(c["pass"] for c in contacts),
        "support_only_near_connector_lugs": len(segments) > 0 and not outside,
        "thread_root_and_crest_survive_native_slicing": wall_screen["pass"],
    }
    return {"status": "DIGITAL_FIVE_PART_SLICE_PASS" if all(checks.values()) else "SLICE_REVIEW_REQUIRED",
            "checks": checks, "package": str(package), "package_sha256": sha(package),
            "native_project": str(project), "project_sha256": sha(project), "parts": records,
            "layers": gcode.count("; Z_HEIGHT:"), "plate_info": plate_info,
            "support_counts": dict(counts), "support_z_range_mm": [min(s["z"] for s in segments), max(s["z"] for s in segments)] if segments else None,
            "support_outside_connector_lug_zone": len(outside), "lug_contacts": contacts,
            "thread_wall_screen": wall_screen,
            "gcode_to_bed_xy_offset_mm": xy_offset,
            "preparation_markers": markers, "commands_do_not_prove_machine_execution": True,
            "sent_to_printer": False, "physical_acceptance": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("package", type=Path)
    ap.add_argument("--project", type=Path, required=True)
    ap.add_argument("--layout", type=Path, required=True)
    ap.add_argument("--lug-support-ceiling", type=float, default=12)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    result = audit(args.package.resolve(), args.project.resolve(), args.layout.resolve(), args.lug_support_ceiling)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text+"\n")
    print(text)
    return int(not all(result["checks"].values()))


if __name__ == "__main__":
    raise SystemExit(main())
