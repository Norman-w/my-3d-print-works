#!/usr/bin/env python3
"""Independent supplied-STL/source check of the candidate feeder body.

Run with the bundled geometry runtime (no installation needed):
/Applications/FreeCAD.app/Contents/Resources/bin/python -B analysis/feeder_body_geometry.py

Connectivity means geometry only, not measured flow, strength or airtightness.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box
from shapely.ops import polygonize, unary_union

try:
    from .guide_openings import module_body, read_scalar_parameters, scalar, without_comments
except ImportError:
    from guide_openings import module_body, read_scalar_parameters, scalar, without_comments


def body_parameters(path: Path, base: dict) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    p = dict(base)
    for name, expression in re.findall(r"^\s*(body_\w+)\s*=\s*([^;]+);", without_comments(raw.decode()), re.M):
        node = ast.parse(expression.strip(), mode="eval").body
        if isinstance(node, ast.List):
            p[name] = [scalar(item, p) for item in node.elts]
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            p[name] = node.value
        elif expression.strip() in ("true", "false"):
            p[name] = expression.strip() == "true"
        else:
            p[name] = scalar(node, p)
    return p, raw


def read_mesh(path: Path) -> tuple[np.ndarray, bytes]:
    raw = path.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0] if len(raw) >= 84 else -1
    if len(raw) == 84 + count * 50:
        dtype = np.dtype([("normal", "<f4", 3), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
        triangles = np.frombuffer(raw, dtype=dtype, offset=84, count=count)["vertices"].astype(float)
    else:
        triples = re.findall(rb"vertex\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)", raw)
        triangles = np.asarray(triples, dtype=float).reshape(-1, 3, 3)
    if not triangles.size or not np.isfinite(triangles).all():
        raise ValueError("Empty or non-finite STL")
    return triangles, raw


def mesh_topology(t: np.ndarray) -> dict:
    vertices, inverse = np.unique(np.round(t.reshape(-1, 3), 8), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    directed = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    edges = np.sort(directed, axis=1)
    unique, edge_id, counts = np.unique(edges, axis=0, return_inverse=True, return_counts=True)
    owner = np.tile(np.arange(len(faces)), 3)
    order = np.argsort(edge_id, kind="stable")
    starts = np.concatenate(([0], np.cumsum(counts)))
    paired = np.where(counts == 2)[0]
    f1, f2 = owner[order[starts[paired]]], owner[order[starts[paired] + 1]]
    graph = coo_matrix((np.ones(len(f1)), (f1, f2)), shape=(len(faces), len(faces)))
    components, labels = connected_components(graph, directed=False)
    balance = np.bincount(edge_id, weights=np.where(directed[:, 0] < directed[:, 1], 1, -1))
    areas = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1) / 2
    return {
        "triangles": len(t), "unique_vertices": len(vertices),
        "bounds_min_mm": t.min(axis=(0, 1)).tolist(),
        "bounds_max_mm": t.max(axis=(0, 1)).tolist(),
        "signed_volume_mm3": float(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6),
        "surface_area_mm2": float(areas.sum()),
        "degenerate_triangles": int((areas < 1e-10).sum()),
        "boundary_edges": int((counts == 1).sum()),
        "nonmanifold_edges": int((counts > 2).sum()),
        "inconsistently_oriented_two_face_edges": int(((counts == 2) & (balance != 0)).sum()),
        "edge_connected_surface_components": int(components),
        "component_triangle_counts": np.bincount(labels).tolist(),
        "scope": "Surface topology at 1e-8 mm vertex welding precision. No general triangle self-intersection proof and no mechanical strength or split-half sealing claim.",
    }


class Sections:
    def __init__(self, triangles: np.ndarray):
        self.t = triangles
        self.zmin = triangles[:, :, 2].min(axis=1)
        self.zmax = triangles[:, :, 2].max(axis=1)
        self.vertex_z = np.unique(triangles[:, :, 2])
        self.cache = {}

    def at(self, requested_z: float):
        z = float(requested_z)
        if np.any(np.abs(self.vertex_z - z) < 1e-8):
            z += 0.000013579
        key = round(z, 9)
        if key in self.cache:
            return z, self.cache[key]
        active = self.t[(self.zmin < z) & (self.zmax > z)]
        segments = []
        for tri in active:
            points = []
            for i, j in ((0, 1), (1, 2), (2, 0)):
                d1, d2 = tri[i, 2] - z, tri[j, 2] - z
                if d1 * d2 < 0:
                    point = tri[i] + (tri[j] - tri[i]) * (-d1 / (d2 - d1))
                    points.append(np.round(point[:2], 7))
            if len(points) == 2 and np.linalg.norm(points[1] - points[0]) > 1e-9:
                segments.append(points)
        if not segments:
            self.cache[key] = Polygon()
            return z, self.cache[key]
        lines = unary_union(MultiLineString(segments))
        line_parts = list(lines.geoms) if hasattr(lines, "geoms") else [lines]
        unique_segments = []
        for line in line_parts:
            coords = list(line.coords)
            unique_segments.extend(zip(coords[:-1], coords[1:]))
        edges = np.asarray(unique_segments)
        solid_faces = []
        for face in polygonize(lines):
            point = face.representative_point()
            px, py = point.x, point.y
            x1, y1, x2, y2 = edges[:, 0, 0], edges[:, 0, 1], edges[:, 1, 0], edges[:, 1, 1]
            crossing = (y1 > py) != (y2 > py)
            positions = x1[crossing] + (py - y1[crossing]) * (x2[crossing] - x1[crossing]) / (y2[crossing] - y1[crossing])
            if int((positions > px).sum()) % 2:
                solid_faces.append(face)
        result = unary_union(solid_faces)
        if not result.is_valid:
            raise ValueError(f"Invalid polygonized mesh section at z={z}")
        self.cache[key] = result
        return z, result


def segment_hits(t: np.ndarray, start, end) -> list[int]:
    """Triangle intersection along a full segment, including coplanar candidates."""
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    direction = end - start
    edge1, edge2 = t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]
    h = np.cross(direction, edge2)
    determinant = np.einsum("ij,ij->i", edge1, h)
    valid = np.abs(determinant) > 1e-10
    reciprocal = np.zeros(len(t))
    reciprocal[valid] = 1 / determinant[valid]
    s = start - t[:, 0]
    u = reciprocal * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, edge1)
    v = reciprocal * np.einsum("j,ij->i", direction, q)
    along = reciprocal * np.einsum("ij,ij->i", edge2, q)
    hit = valid & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (along >= 0) & (along <= 1)
    indices = set(np.where(hit)[0].tolist())
    normals = np.cross(edge1, edge2)
    norm = np.linalg.norm(normals, axis=1)
    plane_dist = np.abs(np.einsum("ij,ij->i", s, normals)) / np.maximum(norm, 1e-20)
    for index in np.where((~valid) & (plane_dist < 1e-9) & (norm > 1e-10))[0]:
        drop = int(np.argmax(np.abs(normals[index])))
        keep = [i for i in range(3) if i != drop]
        shape = Polygon(t[index][:, keep])
        line = LineString([start[keep], end[keep]])
        if shape.intersects(line):
            indices.add(int(index))
    return sorted(indices)


def regular_polygon(radius: float, n: int = 72) -> Polygon:
    return Polygon([(radius * math.cos(2 * math.pi * i / n), radius * math.sin(2 * math.pi * i / n)) for i in range(n)])


def analyze(p: dict, triangles: np.ndarray, source_text: str) -> dict:
    sections = Sections(triangles)
    topology = mesh_topology(triangles)
    g0, g1 = p["guide_start_z"], p["body_guide_end"]
    hole_r = p["finger_tip_radius"] + p["radial_print_clearance"]
    source = without_comments(source_text)
    # Only the current allowed inner-guide cut topology may inherit the round-hole theorem.
    inner = re.sub(r"\s+", "", module_body(source, "body_inner_guide", ""))
    expected_inner = (
        "difference(){union(){body_tube(guide_start_z,guide_length,guide_od,guide_id);"
        "body_taper(body_inlet_shoulder,transition_length,body_spigot_bore+4,guide_od,body_spigot_bore,guide_id);"
        "body_taper(body_guide_end,transition_length,guide_od,body_spigot_bore+4,guide_id,body_spigot_bore);}"
        "for(z=[body_inlet_shoulder+transition_length/2,body_guide_end+transition_length/2],a=[45,135,225,315])body_port(z,a);"
        "for(z=body_side_seat_z)translate([-60,0,z])rotate([0,90,0])cylinder(h=120,r=finger_tip_radius+radial_print_clearance);}")
    inner_contract = inner == expected_inner
    port_module = re.sub(r"\s+", "", module_body(source, "body_port", "z,angle"))
    expected_port = ("rotate([0,0,angle])hull()for(dz=[-(body_port_length-body_port_width)/2,"
                     "(body_port_length-body_port_width)/2])translate([10,0,z+dz])rotate([0,90,0])"
                     "cylinder(h=26,d=body_port_width,$fn=40);")
    port_contract = port_module == expected_port and 0 < p["body_port_width"] <= p["body_port_length"]
    port_centers = [p["body_inlet_shoulder"] + p["transition_length"] / 2,
                    g1 + p["transition_length"] / 2]
    port_ranges = [[z - p["body_port_length"] / 2, z + p["body_port_length"] / 2] for z in port_centers]
    port_outside_guide = port_ranges[0][1] < g0 and port_ranges[1][0] > g1
    tolerance = .02  # Inspection exclusion at mesh boundaries; not a manufacturing allowance.
    facets = p["_guide_mesh_fn"]
    inner_void = regular_polygon(p["guide_id"] / 2, facets).buffer(-tolerance)
    guide_material = regular_polygon(p["guide_od"] / 2, facets).buffer(-tolerance).difference(regular_polygon(p["guide_id"] / 2, facets).buffer(tolerance))
    planes = set(np.linspace(g0 + .01, g1 - .01, 209).tolist())
    for seat in p["body_side_seat_z"]:
        planes.update(seat + d for d in (-hole_r-.01, -hole_r+.01, -1, 0, 1, hole_r-.01, hole_r+.01))
    max_missing, max_intrusion, guide_failures = 0.0, 0.0, []
    for requested in sorted(planes):
        z, solid = sections.at(requested)
        expected = guide_material
        for seat in p["body_side_seat_z"]:
            if abs(z - seat) < hole_r:
                k = math.sqrt(hole_r ** 2 - (z - seat) ** 2)
                expected = expected.difference(box(-100, -k-tolerance, 100, k+tolerance))
        missing = expected.difference(solid.buffer(1e-5)).area
        intrusion = inner_void.intersection(solid).area
        max_missing, max_intrusion = max(max_missing, missing), max(max_intrusion, intrusion)
        if missing > 1e-4 or intrusion > 1e-4:
            guide_failures.append({"z_mm": z, "missing_protected_wall_mm2": missing, "bore_intrusion_mm2": intrusion})
    # A radius halfway between the two taper walls at each port center is kept
    # inside the annular channel throughout the straight axial witness paths.
    guide_outer_mid = (p["body_spigot_bore"] + 4 + p["guide_od"]) / 4
    shell_inner_mid = (p["body_spigot_bore"] + p["body_id"]) / 4
    route_r = (guide_outer_mid + shell_inner_mid) / 2
    paths = []
    for degrees in (45, 135, 225, 315):
        angle = math.radians(degrees)
        xy = [route_r * math.cos(angle), route_r * math.sin(angle)]
        vertices = [[0, 0, p["body_inlet_start"] + .5], [0, 0, port_centers[0]],
                    [*xy, port_centers[0]], [*xy, port_centers[1]],
                    [0, 0, port_centers[1]], [0, 0, p["body_outlet_end"] - .5]]
        intersections = []
        for i, (a, b) in enumerate(zip(vertices[:-1], vertices[1:])):
            hits = segment_hits(triangles, a, b)
            if hits:
                intersections.append({"segment": i, "triangle_ids": hits[:12], "count": len(hits)})
        endpoint_inside_solid = []
        for point in vertices:
            _, solid = sections.at(point[2])
            endpoint_inside_solid.append(solid.covers(Point(point[:2])))
        paths.append({"angle_degrees": degrees, "vertices_mm": vertices,
                      "mesh_surface_intersections": intersections,
                      "any_vertex_inside_solid": any(endpoint_inside_solid),
                      "clear_in_supplied_mesh": not intersections and not any(endpoint_inside_solid)})
    # Strong over-approximation of both fingers: long radial rectangular strips
    # through the annular channel. This covers the rounded caps and outward rods
    # over the declared radial travel, but not a complete unmodeled actuator.
    annulus = regular_polygon(p["body_id"] / 2, facets).difference(regular_polygon(p["guide_od"] / 2, facets))
    finger_strips = box(-100, -p["finger_tip_radius"], 100, p["finger_tip_radius"])
    gate_sections = []
    for seat in p["body_side_seat_z"]:
        z, solid = sections.at(seat)
        free = annulus.difference(solid).difference(finger_strips)
        gate_sections.append({"z_mm": z, "annular_free_area_with_finger_strip_mm2": free.area,
                              "free_polygon_components": len(free.geoms) if hasattr(free, "geoms") else int(not free.is_empty),
                              "diagonal_witnesses_clear": all(free.contains(Point(route_r*math.cos(math.radians(a)),route_r*math.sin(math.radians(a)))) for a in (45,135,225,315))})
    # Blind screw and hex-nut cuts are bounded by their circumcircles in YZ.
    # The actual hex profile is smaller, so this is a lower bound on radial wall.
    blind_x = p["body_side_mount_blind_end"] - p["body_eps"]
    nut_x = p["body_side_mount_x"] - p["nut_depth"] - p["body_eps"]
    bore_y = abs(p["body_side_mount_y"]) - p["fastener_d"] / 2
    nut_y = abs(p["body_side_mount_y"]) - p["nut_af"] / math.sqrt(3)
    blind_clearance = math.hypot(blind_x, max(0, bore_y)) - p["body_id"] / 2
    nut_clearance = math.hypot(nut_x, max(0, nut_y)) - p["body_id"] / 2
    mount_circumradius = max(p["fastener_d"] / 2, p["nut_af"] / math.sqrt(3))
    mount_in_straight_zone = min(p["body_side_mount_z"]) - mount_circumradius > g0 and max(p["body_side_mount_z"]) + mount_circumradius < g1
    # Detect any mesh removal through the proposed residual wall on each mount
    # center plane, independently of the source inequality above.
    blind_witnesses = []
    for side in (-1, 1):
        for seat in p["body_side_mount_z"]:
            z, solid = sections.at(seat)
            xy = (side * (blind_x - .10), p["body_side_mount_y"])
            blind_witnesses.append({"z_mm": z, "xy_mm": list(xy), "inside_remaining_material": solid.contains(Point(xy))})
    rib_start = p["guide_od"] / 2 - p["body_rib_embed"]
    rib_outer_edge = math.sqrt((p["guide_od"] / 2) ** 2 - (p["body_rib_thickness"] / 2) ** 2)
    _, rib_slice = sections.at((g0 + g1) / 2 + .117)
    rib_connections = []
    for sign in (-1, 1):
        for half in (-1, 1):
            x = half * p["body_rib_thickness"] / 4
            line = LineString([(x, sign*(p["guide_id"] / 2 + .2)), (x, sign*(p["body_id"] / 2 + .2))])
            rib_connections.append({"side_y": sign, "half_x": half, "path_x_mm": x,
                                    "whole_radial_load_path_inside_material": rib_slice.buffer(1e-6).covers(line)})
    checks = {
        "watertight_oriented_nondegenerate_surface": not any(topology[k] for k in ("boundary_edges","nonmanifold_edges","inconsistently_oriented_two_face_edges","degenerate_triangles")),
        "one_edge_connected_surface": topology["edge_connected_surface_components"] == 1,
        "recognized_inner_guide_cut_contract": inner_contract,
        "recognized_transition_port_contract": port_contract,
        "transition_windows_outside_straight_guide": port_outside_guide,
        "sampled_guide_wall_and_bore_preserved": not guide_failures,
        "four_continuous_inlet_annulus_outlet_mesh_paths": all(pth["clear_in_supplied_mesh"] for pth in paths),
        "annulus_not_fully_blocked_by_ribs_and_finger_strips": all(row["annular_free_area_with_finger_strip_mm2"] > 0 and row["diagonal_witnesses_clear"] for row in gate_sections),
        "blind_mount_cuts_outside_ID64_cavity": mount_in_straight_zone and min(blind_clearance,nut_clearance) > 0 and all(row["inside_remaining_material"] for row in blind_witnesses),
        "rib_connections_present_in_mesh": all(row["whole_radial_load_path_inside_material"] for row in rib_connections),
        "ribs_do_not_enter_ball_bore": rib_start > p["guide_id"] / 2,
    }
    return {
        "analysis_status": "NO_COUNTEREXAMPLE_IN_COVERED_NOMINAL_GEOMETRY" if all(checks.values()) else "COVERED_GEOMETRY_FAILURE",
        "physical_acceptance": "OPEN_NOT_EVALUATED", "checks": checks,
        "mesh": topology,
        "straight_guide": {"axial_interval_mm": [g0,g1], "recognized_source_contract": inner_contract,
            "nominal_cylinder_facets_from_parameters": facets,
            "nominal_allowed_radial_hole_radius_mm": hole_r, "sampled_sections": len(planes),
            "boundary_exclusion_mm": tolerance,
            "max_missing_protected_wall_mm2": max_missing, "max_bore_intrusion_mm2": max_intrusion,
            "counterexamples": guide_failures[:20],
            "scope": "CSG cut-location argument plus supplied-mesh sections. Protected wall excludes 0.02 mm boundary bands solely to avoid floating-point/tessellation edge comparisons; this is not a print tolerance."},
        "air_path_geometry": {"port_center_z_mm": port_centers,"port_axial_ranges_mm": port_ranges,
            "recognized_port_shape_contract": port_contract,
            "radial_windows_per_end": 4,"total_transition_windows": 8,
            "straight_annular_witness_radius_mm": route_r,"continuous_mesh_paths": paths,
            "axial_witness_tangential_clearance_from_finger_strip_mm": route_r / math.sqrt(2) - p["finger_tip_radius"],
            "gate_sections_with_conservative_finger_strips": gate_sections,
            "scope": "Each full piecewise-linear path has clear endpoints and no segment/triangle surface crossings. These paths stay inside the intended cavity and do not rely on going around the exterior. Finger strips over-approximate nominal caps/rods at gate sections. Connectivity and free area do not predict flow, pressure loss, leakage, feed force or rate."},
        "side_mounts": {"interface_x_mm": [-p['body_side_mount_x'],p['body_side_mount_x']],
            "interface_y_mm": p['body_side_mount_y'],"interface_z_mm":p['body_side_mount_z'],
            "screw_cut_radial_clearance_to_ID64_mm":blind_clearance,
            "nut_cut_circumcircle_radial_clearance_to_ID64_mm":nut_clearance,
            "all_mount_cuts_inside_constant_ID64_axial_zone":mount_in_straight_zone,
            "mesh_residual_wall_witnesses":blind_witnesses,
            "scope":"Lower bounds against an ideal ID64 cylindrical cavity; circumcircle bounds overestimate the hex opening. Blind-hole depth, print error and fastener length still need actual assembly verification."},
        "connections": {"rib_embed_mm":p['body_rib_embed'],
            "rib_inner_edge_to_bore_radial_gap_mm":rib_start-p['guide_id']/2,
            "ideal_circle_overlap_at_full_rib_half_width_mm":rib_outer_edge-rib_start,
            "mesh_radial_load_path_checks":rib_connections,
            "scope":"One connected watertight mesh and finite radial rib paths establish nominal joining, not fastener load capacity, interlayer strength, fatigue or bond quality."},
        "open_items":[
            "Split plane X=0 has no verified sealing path, compression stops or locating features. The assembled full STL does not certify either printed half or the seam.",
            "Radial finger penetrations and guide cartridges need an assembled leakage review; existing openings are not an airtightness claim.",
            "Positive geometric flow paths do not establish blower pressure, practical flow, ball transport or valve timing under a full hose load.",
            "Actual Y coupling, hose clamp, fastener lengths, access, FDM tolerance and material strength remain unverified.",
            "No complete assembly mesh, post-print deformation, physical load or first-article tests were provided.",
        ],
    }


def main() -> int:
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,default=root/'cad/parameters.scad')
    parser.add_argument('--source',type=Path,default=root/'cad/feeder-body.scad')
    parser.add_argument('--mesh',type=Path,default=root/'output/analysis/feeder-body-full.stl')
    parser.add_argument('--output',type=Path,default=root/'output/analysis/feeder-body-geometry.json')
    args=parser.parse_args()
    try:
        base,parameter_raw=read_scalar_parameters(args.parameters)
        p,source_raw=body_parameters(args.source,base)
        fn = re.findall(r"\$fn\s*=\s*([0-9]+)\s*;", without_comments(parameter_raw.decode()))
        if len(fn) != 1 or int(fn[0]) < 3:
            raise ValueError("Expected one explicit integral $fn>=3 for the guide cylinders")
        p['_guide_mesh_fn']=int(fn[0])
        t,mesh_raw=read_mesh(args.mesh)
        result=analyze(p,t,source_raw.decode())
        result['schema_version']=1
        result['generated_at_utc']=datetime.now(timezone.utc).isoformat()
        result['units']='mm, mm2 and mm3 as labeled; STL interpreted in the CAD millimeter convention'
        result['sources']={name:{'path':str(path.resolve()),'sha256':hashlib.sha256(raw).hexdigest()} for name,path,raw in (
            ('parameters',args.parameters,parameter_raw),('body_scad',args.source,source_raw),('supplied_stl',args.mesh,mesh_raw))}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    except (OSError,ValueError,KeyError) as error:
        print(f'FEEDER_GEOMETRY_ERROR: {error}',file=sys.stderr)
        return 2
    print(result['analysis_status'])
    print('Triangles:',result['mesh']['triangles'],'surface components:',result['mesh']['edge_connected_surface_components'])
    for key,value in result['checks'].items():
        print(key, value)
    print('Physical acceptance: OPEN_NOT_EVALUATED')
    print(args.output.resolve())
    return 0 if all(result['checks'].values()) else 1


if __name__=='__main__':
    raise SystemExit(main())
