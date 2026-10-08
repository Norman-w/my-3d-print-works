#!/usr/bin/env python3
"""Prepare five clean meshes with the verified native X1C preset snapshot.

This is a geometry-only input project, not a sliced or dispatched job. Open it
in Bambu Studio, verify the settings, slice, then save/export NEW native files.
Never contacts a printer or changes the user's application configuration.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import uuid
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "output/fan-tee-narrow-nozzles-v5-20261007/print"
TEMPLATE = ROOT / "output/fan-tee-direct-print-v4-20261007/print/slice/fan-tee-v4-native-project.3mf"
CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PROD = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("", CORE)
ET.register_namespace("p", PROD)
IDENTITY = "1 0 0 0 1 0 0 0 1 0 0 0"
LAYOUT = [("connector", (64., 144.)), ("nozzle15", (128., 64.)),
          ("nozzle20", (192., 64.)), ("nozzle25", (128., 144.)),
          ("nozzle30", (192., 144.))]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def xml(element: ET.Element) -> bytes:
    return ET.tostring(element, encoding="utf-8", xml_declaration=True)


def binary_mesh(path: Path):
    data = path.read_bytes()
    assert len(data) >= 84, f"Missing binary STL header: {path}"
    count = struct.unpack_from("<I", data, 80)[0]
    assert count > 0 and len(data) == 84 + count * 50, f"Expected binary STL: {path}"
    vertices, faces, lookup = [], [], {}
    for i in range(count):
        face = struct.unpack_from("<12fH", data, 84 + i * 50)[3:12]
        indices = []
        for j in (0, 3, 6):
            point = tuple(face[j:j+3])
            assert all(math.isfinite(x) for x in point)
            if point not in lookup:
                lookup[point] = len(vertices)
                vertices.append(point)
            indices.append(lookup[point])
        assert len(set(indices)) == 3, f"Collapsed triangle in {path}"
        faces.append(indices)
    edges = Counter(tuple(sorted((f[i], f[(i+1) % 3]))) for f in faces for i in range(3))
    assert all(n == 2 for n in edges.values()), f"Not a closed edge manifold: {path}"
    bounds = [[min(v[i] for v in vertices), max(v[i] for v in vertices)] for i in range(3)]
    return vertices, faces, bounds


def metadata(parent, key, value):
    return ET.SubElement(parent, "metadata", key=key, value=str(value))


def build(stls: dict[str, Path], out: Path, template: Path, *, layout=LAYOUT,
          package_stem="fan-tee-v5", plate_name="v5 - connector and 15-20-25-30 mm",
          expected_parts=5, height_margin_mm=5) -> dict:
    with ZipFile(template) as archive:
        settings = json.loads(archive.read("Metadata/project_settings.config"))
        content_types = archive.read("[Content_Types].xml")
    assert settings["printer_settings_id"] == "Bambu Lab X1 Carbon 0.4 nozzle"
    assert settings["filament_type"] == ["PETG"]
    assert settings["nozzle_diameter"] == ["0.4"]
    assert settings["support_type"] == "tree(auto)"
    assert settings["enable_arc_fitting"] == "0", "Audit parses straight extrusion moves"
    assert float(settings["brim_width"]) <= 6, "Recheck layout for wider brims"
    assert expected_parts >= 1 and height_margin_mm >= 2
    height_limit = float(settings["printable_height"])
    assert math.isfinite(height_limit) and height_limit > height_margin_mm
    assert not set('<>:/\\|?*"') & set(plate_name+package_stem), "Bambu plate/file name contains reserved characters"
    out.mkdir(parents=True, exist_ok=True)
    root = ET.Element(f"{{{CORE}}}model", unit="millimeter", requiredextensions="p",
                      attrib={"xmlns:BambuStudio": "http://schemas.bambulab.com/package/2021"})
    for name, value in [("Application", "BambuStudio-02.08.02.61"),
                        ("BambuStudio:3mfVersion", "1"),
                        ("Title", package_stem+("-five-parts-prepared" if expected_parts == 5 else "-prepared")),
                        ("Description", f"{expected_parts} clean solids. Native slicing and audit still required.")]:
        ET.SubElement(root, f"{{{CORE}}}metadata", name=name).text = value
    resources = ET.SubElement(root, f"{{{CORE}}}resources")
    assembly = ET.SubElement(root, f"{{{CORE}}}build", {f"{{{PROD}}}UUID": str(uuid.uuid4())})
    config = ET.Element("config")
    plate = ET.Element("plate")
    for k, v in [("plater_id", "1"), ("plater_name", plate_name),
                 ("locked", "false"), ("filament_map_mode", "Auto For Flush"),
                 ("filament_maps", "1"), ("filament_volume_maps", "0")]:
        metadata(plate, k, v)
    # Bambu's OPC reader expects unprefixed Relationship tags. A technically
    # equivalent ns0:Relationship document is rejected by the native importer.
    rels = ET.Element("Relationships", xmlns=REL)
    entries, records = {}, []
    assert len(layout) == len(stls) == expected_parts and {role for role, _ in layout} == set(stls)
    for n, (role, center) in enumerate(layout, 1):
        path = stls[role].resolve()
        vertices, faces, box = binary_mesh(path)
        offset = [(lo+hi)/2 for lo, hi in box]
        height = box[2][1] - box[2][0]
        assert 0 < height <= height_limit-height_margin_mm, "Model exceeds native preset height allowance"
        leaf, container = 2*n-1, 2*n
        member = f"3D/Objects/object_{n}.model"
        model = ET.Element(f"{{{CORE}}}model", unit="millimeter")
        rs = ET.SubElement(model, f"{{{CORE}}}resources")
        ob = ET.SubElement(rs, f"{{{CORE}}}object", id=str(leaf), type="model")
        mesh = ET.SubElement(ob, f"{{{CORE}}}mesh")
        vs = ET.SubElement(mesh, f"{{{CORE}}}vertices")
        for v in vertices:
            ET.SubElement(vs, f"{{{CORE}}}vertex", {a: f"{v[i]-offset[i]:.9g}" for i, a in enumerate("xyz")})
        fs = ET.SubElement(mesh, f"{{{CORE}}}triangles")
        for f in faces:
            ET.SubElement(fs, f"{{{CORE}}}triangle", {f"v{i+1}": str(x) for i, x in enumerate(f)})
        entries[member] = xml(model)
        co = ET.SubElement(resources, f"{{{CORE}}}object", {"id": str(container), "type": "model", f"{{{PROD}}}UUID": str(uuid.uuid4())})
        comps = ET.SubElement(co, f"{{{CORE}}}components")
        ET.SubElement(comps, f"{{{CORE}}}component", {"objectid": str(leaf), "transform": IDENTITY,
                      f"{{{PROD}}}path": "/"+member, f"{{{PROD}}}UUID": str(uuid.uuid4())})
        transform = f"1 0 0 0 1 0 0 0 1 {center[0]} {center[1]} {height/2}"
        ET.SubElement(assembly, f"{{{CORE}}}item", {"objectid": str(container), "transform": transform,
                      "printable": "1", f"{{{PROD}}}UUID": str(uuid.uuid4())})
        ET.SubElement(rels, "Relationship", Target="/"+member, Id=f"rel-{n}",
                      Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel")
        oc = ET.SubElement(config, "object", id=str(container))
        metadata(oc, "name", path.name)
        metadata(oc, "extruder", "1")
        ET.SubElement(oc, "metadata", face_count=str(len(faces)))
        part = ET.SubElement(oc, "part", id=str(leaf), subtype="normal_part", uuid=str(uuid.uuid4()))
        matrix = f"1 0 0 {offset[0]} 0 1 0 {offset[1]} 0 0 1 {offset[2]} 0 0 0 1"
        for k, v in [("name", path.name), ("matrix", matrix), ("source_file", path.name),
                     ("source_object_id", "0"), ("source_volume_id", "0")]:
            metadata(part, k, v)
        for a, v in zip("xyz", offset):
            metadata(part, "source_offset_"+a, v)
        ET.SubElement(part, "mesh_stat", face_count=str(len(faces)), edges_fixed="0",
                      degenerate_facets="0", facets_removed="0", facets_reversed="0", backwards_edges="0")
        instance = ET.SubElement(plate, "model_instance")
        for k, v in [("object_id", container), ("instance_id", 0), ("identify_id", n)]:
            metadata(instance, k, v)
        # Conservative XY envelope includes outer brim and one millimetre spare.
        extents = [[center[i] + box[i][0] - offset[i] - 7,
                    center[i] + box[i][1] - offset[i] + 7] for i in (0, 1)]
        assert all(25 <= lo < hi <= 245 for lo, hi in extents), "Bed/wipe-area clearance"
        for prior in records:
            b = prior["xy_envelope_with_7mm_margin"]
            assert any(extents[i][1] < b[i][0] or b[i][1] < extents[i][0] for i in (0, 1)), "Plate envelopes overlap"
        records.append({"role": role, "file": str(path), "sha256": sha(path), "triangles": len(faces),
                        "bounds_mm": box, "source_offset": offset, "center_xy_mm": center,
                        "bed_translation_z_mm": -box[2][0], "scale": [1, 1, 1],
                        "xy_envelope_with_7mm_margin": extents, "quantity": 1})
    config.append(plate)
    entries.update({"[Content_Types].xml": content_types, "3D/3dmodel.model": xml(root),
                    "3D/_rels/3dmodel.model.rels": xml(rels), "Metadata/model_settings.config": xml(config),
                    "Metadata/project_settings.config": json.dumps(settings, ensure_ascii=False, indent=2).encode()})
    package_rels = ET.Element("Relationships", xmlns=REL)
    ET.SubElement(package_rels, "Relationship", Target="/3D/3dmodel.model", Id="rel-1",
                  Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel")
    entries["_rels/.rels"] = xml(package_rels)
    destination = out / (package_stem+"-prepared.3mf")
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    baseline = {"source_native_project": str(template), "source_sha256": sha(template),
                "source_is_provenance_only_after_packaging": True,
                "startup_sha256": hashlib.sha256(settings["machine_start_gcode"].encode()).hexdigest(),
                "end_sha256": hashlib.sha256(settings["machine_end_gcode"].encode()).hexdigest()}
    dump(out / "config/native-baseline.json", baseline)
    dump(out / "config/project-settings.json", settings)
    report = {"status": "PREPARED_GEOMETRY_ONLY_NATIVE_SLICE_REQUIRED", "package": str(destination),
              "sha256": sha(destination), "plate_count": 1, "part_count": expected_parts, "parts": records,
              "native_printable_height_mm": height_limit, "required_height_margin_mm": height_margin_mm,
              "no_embedded_supports": True, "printer_contacted": False,
              "bed": "X1C 256x256 Textured PEI", "material": "PETG; AMS mapping not yet confirmed",
              "native_sliced_package": None, "physical_acceptance": False}
    dump(out / "prepared-project.json", report)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for role, _ in LAYOUT:
        ap.add_argument("--"+role, type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--template", type=Path, default=TEMPLATE)
    args = ap.parse_args()
    result = build({role: getattr(args, role) for role, _ in LAYOUT}, args.out.resolve(), args.template.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
