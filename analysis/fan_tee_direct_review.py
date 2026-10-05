#!/usr/bin/env python3
"""Offline dimensional review for the direct fan-to-Y-tee connector candidate.

This report checks the declared interface contract and print envelope. It does
not claim that the unmeasured fan bore, bayonet datum, printed fit, or airflow
has been physically accepted.
"""

from __future__ import annotations

import json
import math
import re
import struct
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "fan-tee-direct"

P = {
    "fan_outlet_od": 41.0,
    "fan_outlet_id_assumed": 35.0,
    "fan_socket_radial_clearance": 0.45,
    "fan_socket_outer_d": 48.0,
    "fan_bayonet_axial_back_l": 18.5,
    "fan_bayonet_turn_start_back": 7.0,
    "fan_bayonet_turn_arc_l": 20.0,
    "fan_bayonet_axial_slot_w": 7.0,
    "fan_bayonet_turn_slot_w": 6.5,
    "fan_bayonet_button_d": 6.0,
    "fan_bayonet_button_radial_h": 1.60,
    "tee_bore_id": 50.0,
    "tee_fit_radial_clearance": 0.40,
    "wall": 3.0,
    "tee_spigot_l": 25.0,
    "tee_spigot_z1": 80.0,
    "body_outer_d": 50.0,
    "socket_to_body_l": 30.0,
    "air_bore_id": 42.4,
    "core_seat_id": 42.4,
    "thread_bore_id": 40.6,
    "bore_expand_z1": 30.0,
    "bore_to_tee_z0": 68.0,
    "core_od": 40.0,
    "core_inlet_id": 38.0,
    "core_ids": [34.0, 36.0, 38.0],
    "core_l": 45.0,
    "core_mount_l": 22.0,
    "core_taper_l": 15.0,
    "core_exit_l": 8.0,
    "core_flange_od": 40.0,
    "core_flange_l": 0.0,
    "core_thread_l": 16.0,
    "core_thread_pitch": 4.0,
    "core_thread_height": 0.90,
    "core_thread_lead_l": 4.0,
    "core_thread_rel_z0": 4.0,
    "body_thread_z0": 52.0,
    "body_thread_groove_id": 42.8,
    "core_seat_z0": 48.0,
    "core_seat_l": 2.0,
    "core_nominal_z0": 48.0,
    "core_adjustment_range": 8.0,
}


def positive(name: str, value: float) -> None:
    if value <= 0:
        raise AssertionError(f"{name} must be positive, got {value}")


def inspect_stl(path: Path) -> dict:
    """Inspect exported STL edge topology without repairing or rewriting it."""

    raw = path.read_bytes()
    binary = (
        len(raw) >= 84
        and 84 + 50 * struct.unpack_from("<I", raw, 80)[0] == len(raw)
    )
    triangles: list[list[tuple[float, float, float]]] = []
    if binary:
        count = struct.unpack_from("<I", raw, 80)[0]
        for index in range(count):
            row = struct.unpack_from("<12f", raw, 84 + 50 * index)
            triangles.append([tuple(row[offset:offset + 3]) for offset in (3, 6, 9)])
    else:
        values = re.findall(
            rb"^\s*vertex\s+(\S+)\s+(\S+)\s+(\S+)\s*$",
            raw,
            re.MULTILINE,
        )
        if len(values) % 3:
            raise ValueError(f"invalid ASCII STL facet count: {path}")
        for offset in range(0, len(values), 3):
            triangles.append([
                tuple(float(value) for value in vertex)
                for vertex in values[offset:offset + 3]
            ])

    edge_faces: defaultdict[tuple, list[int]] = defaultdict(list)
    degenerate = 0
    for face_index, triangle in enumerate(triangles):
        first, second, third = triangle
        u = [second[index] - first[index] for index in range(3)]
        v = [third[index] - first[index] for index in range(3)]
        cross = (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )
        if not any(cross):
            degenerate += 1
        rounded = [tuple(round(value, 6) for value in vertex) for vertex in triangle]
        for edge_index in range(3):
            edge = tuple(sorted((rounded[edge_index], rounded[(edge_index + 1) % 3])))
            edge_faces[edge].append(face_index)

    face_neighbors = [set() for _ in triangles]
    for faces in edge_faces.values():
        for face_index in faces:
            face_neighbors[face_index].update(
                other for other in faces if other != face_index
            )
    components = 0
    seen: set[int] = set()
    for face_index in range(len(triangles)):
        if face_index in seen:
            continue
        components += 1
        stack = [face_index]
        seen.add(face_index)
        while stack:
            current = stack.pop()
            for neighbor in face_neighbors[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)

    all_vertices = [vertex for triangle in triangles for vertex in triangle]
    minimum = [min(vertex[index] for vertex in all_vertices) for index in range(3)]
    maximum = [max(vertex[index] for vertex in all_vertices) for index in range(3)]
    boundary_edges = sum(len(faces) == 1 for faces in edge_faces.values())
    nonmanifold_edges = sum(len(faces) > 2 for faces in edge_faces.values())
    return {
        "format": "binary" if binary else "ascii",
        "facets": len(triangles),
        "bbox_mm": [round(maximum[index] - minimum[index], 3) for index in range(3)],
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "degenerate_facets": degenerate,
        "connected_components": components,
        "manifold": not boundary_edges and not nonmanifold_edges and components == 1,
        "watertight": not boundary_edges and not nonmanifold_edges and components == 1,
    }


def main() -> int:
    tee_spigot_od = P["tee_bore_id"] - 2 * P["tee_fit_radial_clearance"]
    tee_spigot_id = tee_spigot_od - 2 * P["wall"]
    fan_socket_id = P["fan_outlet_od"] + 2 * P["fan_socket_radial_clearance"]
    bayonet_turn_angle_deg = (
        P["fan_bayonet_turn_arc_l"]
        / (math.pi * P["fan_outlet_od"])
        * 360.0
    )
    core_thread_major_od = P["core_od"] + 2 * P["core_thread_height"]
    body_thread_radial_clearance = (
        P["body_thread_groove_id"] - core_thread_major_od
    ) / 2
    core_walls = {
        str(core_id): (P["core_od"] - core_id) / 2
        for core_id in P["core_ids"]
    }
    tee_spigot_z0 = P["tee_spigot_z1"] - P["tee_spigot_l"]
    core_nominal_z1 = P["core_nominal_z0"] + P["core_l"]

    stl_paths = {
        "connector": OUTPUT / "fan-tee-direct-connector.stl",
        "core34": OUTPUT / "fan-tee-direct-core34.stl",
        "core36": OUTPUT / "fan-tee-direct-core36.stl",
        "core38": OUTPUT / "fan-tee-direct-core38.stl",
    }
    stl_verification = {}
    for name, path in stl_paths.items():
        relative = str(path.relative_to(ROOT))
        stl_verification[name] = {"stl": relative}
        if path.exists():
            stl_verification[name].update(inspect_stl(path))
        else:
            stl_verification[name].update({"missing": True, "watertight": False})

    checks = {
        "fan_socket": {
            "fan_outlet_od_mm": P["fan_outlet_od"],
            "socket_id_mm": fan_socket_id,
            "radial_clearance_mm": P["fan_socket_radial_clearance"],
            "button_d_mm": P["fan_bayonet_button_d"],
            "axial_slot_clearance_mm": (
                P["fan_bayonet_axial_slot_w"] - P["fan_bayonet_button_d"]
            ),
            "turn_slot_clearance_mm": (
                P["fan_bayonet_turn_slot_w"] - P["fan_bayonet_button_d"]
            ),
            "turn_angle_deg": round(bayonet_turn_angle_deg, 3),
            "opposed_buttons": 2,
            "axial_back_length_mm": P["fan_bayonet_axial_back_l"],
            "turn_start_back_mm": P["fan_bayonet_turn_start_back"],
        },
        "tee_spigot": {
            "tee_nominal_bore_id_mm": P["tee_bore_id"],
            "printed_spigot_od_mm": round(tee_spigot_od, 3),
            "printed_spigot_id_mm": round(tee_spigot_id, 3),
            "radial_fit_clearance_mm": P["tee_fit_radial_clearance"],
            "wall_mm": round((tee_spigot_od - tee_spigot_id) / 2, 3),
            "insertion_l_mm": P["tee_spigot_l"],
            "z_range_mm": [tee_spigot_z0, P["tee_spigot_z1"]],
        },
        "replaceable_core": {
            "core_od_mm": P["core_od"],
            "inlet_straight_id_mm": P["core_inlet_id"],
            "available_exit_ids_mm": P["core_ids"],
            "core_walls_mm": core_walls,
            "lead_bore_id_mm": P["core_seat_id"],
            "lead_bore_z_range_mm": [
                P["core_seat_z0"],
                P["core_seat_z0"] + P["core_seat_l"],
            ],
            "guide_and_thread_bore_id_mm": P["thread_bore_id"],
            "thread_pitch_mm": P["core_thread_pitch"],
            "thread_engagement_l_mm": P["core_thread_l"],
            "thread_start_after_lead_mm": P["core_thread_rel_z0"],
            "thread_major_od_mm": round(core_thread_major_od, 3),
            "body_groove_id_mm": P["body_thread_groove_id"],
            "thread_radial_clearance_mm": round(body_thread_radial_clearance, 3),
            "nominal_core_z_range_mm": [P["core_nominal_z0"], core_nominal_z1],
            "nominal_extension_past_tee_mm": round(
                core_nominal_z1 - P["tee_spigot_z1"], 3
            ),
            "adjustment_range_mm": P["core_adjustment_range"],
        },
        "print_envelope": {
            "connector_bbox_mm": [50.0, 50.0, 98.5],
            "core_bbox_mm": [41.8, 41.8, P["core_l"]],
            "x1c_bed_mm": [256.0, 256.0],
            "x1c_z_margin_mm": 256.0 - 98.5,
        },
    }

    positive("tee_spigot_od", tee_spigot_od)
    positive("tee_spigot_id", tee_spigot_id)
    positive("fan_socket_id", fan_socket_id - P["fan_outlet_od"])
    positive("body_thread_radial_clearance", body_thread_radial_clearance)
    assert tee_spigot_od < P["tee_bore_id"]
    assert abs((tee_spigot_od - tee_spigot_id) / 2 - P["wall"]) < 1e-9
    assert P["fan_bayonet_axial_slot_w"] > P["fan_bayonet_button_d"]
    assert P["fan_bayonet_turn_slot_w"] > P["fan_bayonet_button_d"]
    assert P["body_thread_z0"] > P["bore_expand_z1"]
    assert P["body_thread_z0"] + P["core_thread_l"] < P["tee_spigot_z1"]
    assert P["air_bore_id"] >= P["core_seat_id"]
    assert P["core_seat_id"] > P["core_od"]
    assert P["core_flange_l"] == 0
    assert P["core_flange_od"] == P["core_od"]
    assert P["core_seat_z0"] == P["core_nominal_z0"]
    assert P["core_thread_rel_z0"] + P["core_thread_l"] < P["core_l"]
    assert P["core_mount_l"] + P["core_taper_l"] + P["core_exit_l"] == P["core_l"]
    assert P["core_inlet_id"] < P["core_od"]
    assert P["core_adjustment_range"] >= P["core_thread_pitch"]
    assert all(wall >= 1.0 for wall in core_walls.values())
    assert P["fan_outlet_id_assumed"] < P["fan_outlet_od"]

    report = {
        "status": "contract-pass-with-stl-topology-pass" if all(
            row.get("watertight") is True for row in stl_verification.values()
        ) else "contract-pass-topology-incomplete",
        "scope": "declared interface dimensions, exported STL topology, and print envelope only",
        "assumptions": [
            "fan_outlet_id_assumed=35.0 mm must be replaced by a measured value",
            "tee_bore_id=50.0 mm is nominal and tee_fit_radial_clearance=0.40 mm is a PETG first-print starting point",
            "L-slot axial/circumferential datum is represented by button_z=-7.0 mm and requires physical orientation confirmation",
        ],
        "stl_verification": {
            "tool": "OpenSCAD 2026.04.26 CGAL export plus independent edge-topology inspection",
            **stl_verification,
        },
        "checks": checks,
        "not_verified": [
            "fan outlet measured inner diameter",
            "exact fan L-groove axial datum, handedness, and two-side angular datum",
            "actual Y-tee insertion stop and bore cylindricity",
            "printed button engagement, bayonet torque, pull-out, and repeated service life",
            "printed thread fit and actual core adjustment travel",
            "fan flow, pressure, noise, ball capture, and physical fit",
        ],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
