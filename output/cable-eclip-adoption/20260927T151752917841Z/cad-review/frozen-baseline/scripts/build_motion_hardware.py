#!/usr/bin/env python3
"""Partition existing display hardware by rigid motion; never invokes CAD.

The source is a frozen assembled STL, containing fixed hardware, four radial
follower assemblies, and the upper return-spring attachment. This script only
routes its original facet blocks into display meshes. It does not repair,
remesh, validate manufacture, or assess physical motion.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "output/revision-review"
SOURCE = PREVIEW / "models/feeder/hardware.stl"
DESTINATION = PREVIEW / "motion-hardware"
FACET = re.compile(rb"facet\s+normal\s+.*?endfacet", re.DOTALL)
VERTEX = re.compile(rb"vertex\s+([^\r\n]+)")
GROUP_ORDER = [
    "fixed", "finger-right-front", "finger-right-rear",
    "finger-left-front", "finger-left-rear", "frame",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_facets(data: bytes):
    # This exact preserved source is ASCII. Reject a format change explicitly.
    if not data.lstrip().startswith(b"solid"):
        raise ValueError("Expected the preserved ASCII hardware display STL")
    facets = []
    for block in FACET.findall(data):
        vertices = tuple(tuple(map(float, v.split())) for v in VERTEX.findall(block))
        if len(vertices) != 3 or any(len(v) != 3 for v in vertices):
            raise ValueError("A source facet does not contain exactly three 3D vertices")
        facets.append((block, vertices))
    if not facets:
        raise ValueError("No source facets found")
    return facets


def bounds(vertices):
    vertices = list(vertices)
    low = [min(v[k] for v in vertices) for k in range(3)]
    high = [max(v[k] for v in vertices) for k in range(3)]
    return {"min": low, "max": high, "size": [b - a for a, b in zip(low, high)]}


def triangle_multiset_hash(facets):
    """Ignore facet ordering, preserve every vertex and each triangle's winding."""
    triangles = []
    for _, vertices in facets:
        # Cyclic permutation keeps winding while giving a stable start vertex.
        encoded = [",".join(x.hex() for x in vertex) for vertex in vertices]
        canonical = min(";".join(encoded[i:] + encoded[:i]) for i in range(3))
        triangles.append(canonical)
    return sha256("\n".join(sorted(triangles)).encode("ascii"))


def connected_components(facets):
    parent = {}

    def find(vertex):
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for _, vertices in facets:
        for vertex in vertices:
            parent.setdefault(vertex, vertex)
        anchor = find(vertices[0])
        for vertex in vertices[1:]:
            parent[find(vertex)] = anchor
    result = defaultdict(list)
    for facet in facets:
        result[find(facet[1][0])].append(facet)
    return list(result.values())


def close(actual, expected, tolerance=0.00001):
    return all(abs(a - b) <= tolerance for a, b in zip(actual, expected))


def motion_group(component):
    box = bounds(vertex for _, vertices in component for vertex in vertices)
    low, high = box["min"], box["max"]

    # These envelopes identify existing assembled connected bodies only.
    # Both upper spring-pin bodies translate with the original cam frame.
    if close(low, [-76, 15.5, 9]) and close(high, [-68, 37.5, 17]):
        return "frame"
    if close(low, [-76, 31.7, 9]) and close(high, [-68, 32.2, 17]):
        return "frame"

    for side, sign in [("right", 1), ("left", -1)]:
        for end, radius, z in [("front", 21, 0), ("rear", 26, -28.5)]:
            center = sign * (radius + 20)
            pin_low = [center - 3.5, -5.25, z - 3.5]
            pin_high = [center + 3.5, 16.75, z + 3.5]
            if close(low, pin_low) and close(high, pin_high):
                return f"finger-{side}-{end}"
            x_limits = sorted([sign * (radius + 23.6), sign * (radius + 27.6)])
            if (close([low[0], low[1], high[0], high[1]],
                      [x_limits[0], -.5, x_limits[1], 3.5])
                    and abs((low[2] + high[2]) / 2 - z) < .00001
                    and abs(high[2] - low[2] - 8 / (3 ** .5)) < .00001):
                return f"finger-{side}-{end}"
    return "fixed"


def main():
    source_data = SOURCE.read_bytes()
    facets = read_facets(source_data)
    components = connected_components(facets)
    grouped = {group: [] for group in GROUP_ORDER}
    component_counts = dict.fromkeys(GROUP_ORDER, 0)
    for component in components:
        group = motion_group(component)
        grouped[group].extend(component)
        component_counts[group] += 1

    # Fail closed if the frozen asset or classification has changed.
    expected_counts = {group: 64 if group == "fixed" else 2 for group in GROUP_ORDER}
    if len(components) != 74 or component_counts != expected_counts:
        raise ValueError(f"Unexpected display component mapping: {component_counts}")
    expected_triangles = len(facets)
    if sum(map(len, grouped.values())) != expected_triangles:
        raise ValueError("Source/output triangle counts differ")

    source_triangle_hash = triangle_multiset_hash(facets)
    source_facet_hash = sha256(b"\n".join(sorted(block for block, _ in facets)))
    prepared = {}
    round_trip = []
    parts = []
    for group in GROUP_ORDER:
        data = (f"solid hardware_{group}\n".encode()
                + b"\n".join(block for block, _ in grouped[group])
                + f"\nendsolid hardware_{group}\n".encode())
        parsed = read_facets(data)
        round_trip.extend(parsed)
        prepared[group] = data
        parts.append({
            "id": group, "file": f"motion-hardware/{group}.stl",
            "sha256": sha256(data), "motionGroup": group,
            "bounds": bounds(vertex for _, vertices in parsed for vertex in vertices),
            "components": component_counts[group], "triangles": len(parsed),
        })

    output_triangle_hash = triangle_multiset_hash(round_trip)
    output_facet_hash = sha256(b"\n".join(sorted(block for block, _ in round_trip)))
    if source_triangle_hash != output_triangle_hash or source_facet_hash != output_facet_hash:
        raise ValueError("An original triangle, winding, normal, or facet text was altered")

    manifest = {
        "schema": "display-hardware-motion-groups-v1", "units": "mm",
        "source": {"file": "models/feeder/hardware.stl", "sha256": sha256(source_data),
                   "components": len(components), "triangles": expected_triangles},
        "parts": parts,
        "preservation": {
            "sourceTriangles": expected_triangles, "outputTriangles": len(round_trip),
            "sourceTriangleMultisetSha256": source_triangle_hash,
            "outputTriangleMultisetSha256": output_triangle_hash,
            "sourceFacetTextMultisetSha256": source_facet_hash,
            "outputFacetTextMultisetSha256": output_facet_hash,
            "allOriginalFacetsPreserved": True,
        },
        "scope": "Display-only partition of existing facets; not manufacturing or physical validation.",
        "rendering": "Render these six meshes instead of the combined source and procedural duplicate pins.",
    }
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for group, data in prepared.items():
        (DESTINATION / f"{group}.stl").write_bytes(data)
    path = DESTINATION / "hardware-manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"manifest": str(path), "sourceTriangles": expected_triangles,
                      "outputTriangles": len(round_trip), "components": component_counts,
                      "allOriginalFacetsPreserved": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
