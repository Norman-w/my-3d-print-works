#!/usr/bin/env python3
"""Build a real arranged-model 3MF from a rigid STL print-plate manifest.

The input metadata is produced by build_print_plates.py.  Each source STL is
kept as an independent 3MF object and receives the exact rigid transform that
was used for the combined preview STL; no scaling or mesh boolean is applied.
"""

from __future__ import annotations

import argparse
import json
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


TRIANGLE = struct.Struct("<12fH")
CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_TYPE = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"


def load_binary_stl(path: Path) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"STL 文件过短: {path}")
    count = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + count * TRIANGLE.size
    if len(data) != expected:
        raise ValueError(f"仅支持 OpenSCAD 二进制 STL: {path}")
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    index_by_vertex: dict[tuple[float, float, float], int] = {}

    def vertex_index(value: tuple[float, float, float]) -> int:
        index = index_by_vertex.get(value)
        if index is None:
            index = len(vertices)
            vertices.append(value)
            index_by_vertex[value] = index
        return index

    offset = 84
    for _ in range(count):
        values = TRIANGLE.unpack_from(data, offset)
        offset += TRIANGLE.size
        face = tuple(
            vertex_index(tuple(float(values[start + axis]) for axis in range(3)))
            for start in (3, 6, 9)
        )
        faces.append(face)  # type: ignore[arg-type]
    return vertices, faces


def transform_string(matrix: list[list[float]], translation: list[float]) -> str:
    values = [
        matrix[0][0], matrix[0][1], matrix[0][2], translation[0],
        matrix[1][0], matrix[1][1], matrix[1][2], translation[1],
        matrix[2][0], matrix[2][1], matrix[2][2], translation[2],
    ]
    return " ".join(f"{float(value):.9g}" for value in values)


def model_xml(plate: dict[str, object], source_root: Path) -> bytes:
    ET.register_namespace("", CORE_NS)
    root = ET.Element(f"{{{CORE_NS}}}model", {"unit": "millimeter", "xml:lang": "zh-CN"})
    metadata = {
        "Application": "SmartPaddle M7-LB1 光板版",
        "Plate": str(plate.get("label", "")),
        "Kind": "arranged-model",
        "AssemblyGeometryUnchanged": str(bool(plate.get("assemblyGeometryUnchanged", True))).lower(),
    }
    for name, value in metadata.items():
        ET.SubElement(root, f"{{{CORE_NS}}}metadata", {"name": name}).text = value
    resources = ET.SubElement(root, f"{{{CORE_NS}}}resources")
    items = plate.get("parts")
    if not isinstance(items, list) or not items:
        raise ValueError("打印拼板没有可写入 3MF 的独立零件")
    transforms: list[tuple[int, str, str]] = []
    for object_id, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError("打印拼板零件元数据格式错误")
        source = str(item["source"])
        source_path = source_root / source
        vertices, faces = load_binary_stl(source_path)
        obj = ET.SubElement(resources, f"{{{CORE_NS}}}object", {
            "id": str(object_id),
            "type": "model",
            "name": source,
        })
        mesh = ET.SubElement(obj, f"{{{CORE_NS}}}mesh")
        vertex_block = ET.SubElement(mesh, f"{{{CORE_NS}}}vertices")
        for x, y, z in vertices:
            ET.SubElement(vertex_block, f"{{{CORE_NS}}}vertex", {
                "x": f"{x:.9g}", "y": f"{y:.9g}", "z": f"{z:.9g}",
            })
        triangle_block = ET.SubElement(mesh, f"{{{CORE_NS}}}triangles")
        for v1, v2, v3 in faces:
            ET.SubElement(triangle_block, f"{{{CORE_NS}}}triangle", {
                "v1": str(v1), "v2": str(v2), "v3": str(v3),
            })
        transforms.append((object_id, transform_string(
            item["rotationMatrix"], item["translationAfterRotation"]
        ), source))

    build = ET.SubElement(root, f"{{{CORE_NS}}}build")
    for object_id, transform, source in transforms:
        ET.SubElement(build, f"{{{CORE_NS}}}item", {
            "objectid": str(object_id),
            "transform": transform,
            "name": source,
        })
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def package_3mf(output: Path, model: bytes) -> None:
    content_types = f'''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="{CONTENT_NS}">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
'''.encode("utf-8")
    root_relationships = f'''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="{REL_NS}">
  <Relationship Id="rel0" Type="{REL_TYPE}" Target="/3D/3dmodel.model"/>
</Relationships>
'''.encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_relationships)
        archive.writestr("3D/3dmodel.model", model)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"3MF ZIP 校验失败: {output}")
        ET.fromstring(archive.read("3D/3dmodel.model"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stl-root", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--plate", choices=("layers_1_2", "layers_3_4"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.metadata.read_text(encoding="utf-8"))
    needle = f"paddle_m7_lb1_print_plate_{args.plate}.stl"
    matches = [
        plate for plate in report.get("plates", [])
        if Path(str(plate.get("path", ""))).name == needle
    ]
    if len(matches) != 1:
        raise ValueError(f"未找到唯一打印拼板: {needle}")
    model = model_xml(matches[0], args.stl_root)
    package_3mf(args.output, model)
    print(f"✓ {args.output}  arranged-model  objects={len(matches[0]['parts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
