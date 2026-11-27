#!/usr/bin/env python3
"""Export and intersect real spin-head solids; no force or airflow prediction."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "spin-head"
SOURCE = ROOT / "cad" / "spin-head.scad"
OPENSCAD = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
PARTS = ("body", "carriage", "pad", "pad-keeper", "opposite-guide", "cover", "spring-cage", "spring-seat", "pull-cap", "hold-fork")


def parameters() -> dict:
    values = {}
    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.List):
            return [evaluate(value) for value in node.elts]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -evaluate(node.operand)
        if isinstance(node, ast.BinOp):
            a, b = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if isinstance(node.op, ast.Div): return a / b
        raise ValueError("Unsupported SCAD parameter expression")
    for name in ("parameters.scad", "spin-parameters.scad"):
        source = re.sub(r"//[^\n]*", "", (ROOT / "cad" / name).read_text())
        for match in re.finditer(r"^([A-Za-z_]\w*)\s*=\s*([^;]+);", source, re.MULTILINE):
            values[match[1]] = evaluate(ast.parse(match[2], mode="eval").body)
    return values


def inspect_mesh(path: Path) -> dict:
    raw = path.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) != 84 + count * 50:
        raise ValueError(f"Expected binary STL: {path}")
    triangles = []
    for i in range(count):
        row = struct.unpack_from("<12f", raw, 84 + 50 * i)
        triangles.append(tuple(tuple(row[j:j+3]) for j in (3, 6, 9)))
    vertices = [point for triangle in triangles for point in triangle]
    edges, orientation = Counter(), Counter()
    volume, area = 0.0, 0.0
    parent = list(range(count))
    first_face = {}
    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index
    for index, tri in enumerate(triangles):
        a, b, c = tri
        cross = (b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0])
        volume += sum(a[i]*cross[i] for i in range(3))/6
        u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
        area += math.sqrt(sum(x*x for x in (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])))/2
        keys = [tuple(round(x, 5) for x in point) for point in tri]
        for start, end in zip(keys, keys[1:]+keys[:1]):
            edge = tuple(sorted((start, end)))
            edges[edge] += 1
            orientation[edge] += 1 if start <= end else -1
            if edge in first_face:
                parent[find(index)] = find(first_face[edge])
            else:
                first_face[edge] = index
    minimum = [min(point[i] for point in vertices) for i in range(3)]
    maximum = [max(point[i] for point in vertices) for i in range(3)]
    component_vertices = {}
    for index, tri in enumerate(triangles):
        component_vertices.setdefault(find(index), []).extend(tri)
    component_bounds = []
    for points in component_vertices.values():
        lo = [min(point[i] for point in points) for i in range(3)]
        hi = [max(point[i] for point in points) for i in range(3)]
        component_bounds.append({"min":lo,"max":hi,"size":[hi[i]-lo[i] for i in range(3)]})
    return {
        "file": path.relative_to(ROOT).as_posix(), "units_assumed_from_scad": "mm",
        "sha256":hashlib.sha256(raw).hexdigest(),
        "triangles": count, "bounds_min_mm": minimum, "bounds_max_mm": maximum,
        "size_mm": [maximum[i]-minimum[i] for i in range(3)],
        "volume_mm3": abs(volume), "surface_area_mm2": area,
        "boundary_edges": sum(n == 1 for n in edges.values()),
        "nonmanifold_edges": sum(n > 2 for n in edges.values()),
        "inconsistent_edge_orientation": sum(n != 0 for n in orientation.values()),
        "connected_components": len({find(i) for i in range(count)}),
        "component_bounds_mm": component_bounds,
        "watertight": bool(count) and all(n == 2 for n in edges.values()) and not any(orientation.values()),
    }


def x_surface_intersections(path: Path, y: float, z: float) -> list[float]:
    """Intersect an X-directed line with exported triangles, independently of SCAD variables."""
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    hits = set()
    for index in range(count):
        row = struct.unpack_from("<12f", data, 84+50*index)
        a,b,c = [row[j:j+3] for j in (3,6,9)]
        uy,uz,vy,vz = b[1]-a[1],b[2]-a[2],c[1]-a[1],c[2]-a[2]
        determinant = uy*vz-uz*vy
        if abs(determinant) < 1e-10:
            continue
        dy,dz = y-a[1],z-a[2]
        s,t = (dy*vz-dz*vy)/determinant,(uy*dz-uz*dy)/determinant
        if s >= -1e-7 and t >= -1e-7 and s+t <= 1+1e-7:
            hits.add(round(a[0]+s*(b[0]-a[0])+t*(c[0]-a[0]),5))
    return sorted(hits)


def export(name: str, part: str, definitions: dict | None = None, expect_empty: bool = False) -> dict:
    destination = OUT / (name + ".stl")
    destination.unlink(missing_ok=True)
    command = [OPENSCAD, "--hardwarnings", "--backend", "Manifold", "--export-format", "binstl", "-o", str(destination), "-D", f'part="{part}"']
    for key, value in (definitions or {}).items():
        command.extend(["-D", f"{key}={value}"])
    command.append(str(SOURCE))
    run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    log = run.stdout + run.stderr
    (OUT / (name + ".log")).write_text(log)
    empty = "Current top level object is empty" in log and not destination.exists()
    if not empty and run.returncode:
        raise RuntimeError(f"OpenSCAD failed: {name}\n{log}")
    result = {"name": name, "part": part, "definitions": definitions or {}, "empty": empty,
              "expected_empty": expect_empty, "matches_expectation": empty == expect_empty,
              "command": command}
    if destination.exists():
        result["mesh"] = inspect_mesh(destination)
        mesh = result["mesh"]
        planar_contact = all(min(item["size"]) <= 1e-7 for item in mesh["component_bounds_mm"]) and mesh["volume_mm3"] <= 1e-7
        if part == 'hardware-interference' and not planar_contact:
            # The repaired DIN7991 seats intentionally touch along a 90-degree
            # faceted cone, not an axis-aligned plane. Validate every triangle
            # against the named bearing surfaces; volume alone is insufficient.
            from spin_complete_hardware import classify as classify_metal_contact
            contact = classify_metal_contact(destination, (definitions or {}).get('float_shift', 0), (definitions or {}).get('preload_shift', 0))
            result['named_bearing_contact_review'] = contact
            planar_contact = contact.get('zero_thickness_bearing_contact', False)
        result["zero_volume_planar_contact_at_stop"] = planar_contact
        result["matches_expectation"] = (empty or planar_contact) == expect_empty
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    p = parameters()
    part_reports = [export("spin-"+part, part) for part in PARTS]
    tests = []
    for bore in (p["spin_guide_id"]-2*p["guide_clearance_budget"], p["spin_guide_id"], p["spin_guide_id"]+2*p["guide_clearance_budget"]):
        for shift in (0, p["sh_float_travel"]/2, p["sh_float_travel"]):
            for preload in (0, p["sh_preload_travel"]):
                tests.append(export(f"spin-probe-b{bore:g}-f{shift:g}-p{preload:g}", "hard-corridor", {"bore_d":bore,"float_shift":shift,"preload_shift":preload}, True))
    for index in range(31):
        shift = round(p["sh_float_travel"]*index/30,6)
        tests.append(export(f"spin-slide-f{shift:g}", "slide-collision", {"float_shift":shift}, True))
    for preload in (0, p["sh_preload_travel"]/2, p["sh_preload_travel"]):
        tests.append(export(f"spin-seat-p{preload:g}", "seat-collision", {"preload_shift":preload}, True))
    tests.append(export("spin-pad-carriage-fit", "pad-hard-collision", {}, True))
    tests.append(export("spin-fixed-parts-fit", "fixed-parts-collision", {}, True))
    tests.append(export("spin-driver-access", "tool-access", {"float_shift":p["sh_float_travel"]}, True))
    for shift,preload in ((0,0),(p["sh_float_travel"],p["sh_preload_travel"])):
        tests.append(export(f"spin-hardware-f{shift:g}-p{preload:g}", "hardware-interference", {"float_shift":shift,"preload_shift":preload}, True))
    for distance in (0,5,10,20):
        tests.append(export(f"spin-cover-removal-{distance}", "cover-removal-collision", {"service_shift":distance}, True))
        tests.append(export(f"spin-carriage-removal-{distance}", "carriage-removal-collision", {"service_shift":distance}, True))
    # Positive controls prove that the same intersections detect deliberate stop overrun.
    tests.append(export("spin-control-slide-overrun", "slide-collision", {"float_shift":p["sh_float_travel"]+0.8}, False))
    tests.append(export("spin-control-seat-overrun", "seat-collision", {"preload_shift":p["sh_preload_travel"]+1}, False))
    tests.append(export("spin-soft-small-ball-contact", "soft-ball-overlap", {"bore_d":43,"probe_ball_d":40}, False))
    tests.append(export("spin-soft-large-ball-retracted", "soft-ball-overlap", {"bore_d":42,"probe_ball_d":41,"float_shift":p["sh_float_travel"]}, True))
    for shift in (0,2.25,p["sh_hold_shift"],p["sh_float_travel"]):
        for preload in (0,p["sh_preload_travel"]):
            state={"float_shift":shift,"preload_shift":preload,"hold_mode":"true" if shift==p["sh_hold_shift"] else "false"}
            tests.append(export(f"spin-added-f{shift:g}-p{preload:g}","added-parts-collision",state,True))
            tests.append(export(f"spin-spring-f{shift:g}-p{preload:g}","spring-clearance",state,True))
            tests.append(export(f"spin-spring-budget-f{shift:g}-p{preload:g}","spring-budget-clearance",state,True))
            tests.append(export(f"spin-pull-tool-f{shift:g}-p{preload:g}","pull-tool-access",state,True))
    for offset in (0,2,5,10,15,25):
        tests.append(export(f"spin-latch-insertion-{offset:g}","added-parts-collision",
            {"float_shift":p["sh_float_travel"],"preload_shift":p["sh_preload_travel"],"hold_mode":"true","latch_install_shift":offset,"latch_bolt_installed":"false"},True))
    tests.append(export("spin-pull-nut-insertion","nut-insertion",{},True))
    tests.append(export("spin-latch-nut-insertion","latch-nut-insertion",{},True))
    tests.append(export("spin-control-nut-insertion","nut-insertion-control",{},False))
    tests.append(export("spin-held-full-bore-plus-budget","no-contact-envelope",{"float_shift":p["sh_hold_shift"],"hold_mode":"true","bore_d":43},True))
    tests.append(export("spin-control-old-three-mm-retreat","no-contact-envelope",{"float_shift":3,"bore_d":43},False))
    by_part = {item["part"]:item["mesh"] for item in part_reports}
    # Independent readback from exported entities, then an interval inequality.
    free_face = by_part["pad"]["bounds_min_mm"][0]
    hard_front = by_part["carriage"]["bounds_min_mm"][0]
    bore_min = p["spin_guide_id"]-2*p["guide_clearance_budget"]
    bore_max = p["spin_guide_id"]+2*p["guide_clearance_budget"]
    min_ball_rightmost = p["ball_min_d"]-bore_max/2
    max_ball_rightmost = p["ball_max_d"]-bore_min/2
    plate_section = x_surface_intersections(OUT/"spin-carriage.stl",9,43)
    retreat_stop_section = x_surface_intersections(OUT/"spin-cover.stl",9,32)
    cage_stop_section = x_surface_intersections(OUT/"spin-spring-cage.stl",5.8,43)
    seat_section = x_surface_intersections(OUT/"spin-spring-seat.stl",5.8,43)
    seat_outer_stop_section = x_surface_intersections(OUT/"spin-cover.stl",5.8,43)
    measured_retreat = retreat_stop_section[0]-plate_section[-1]
    measured_preload = seat_section[0]-cage_stop_section[-1]
    cap_section=x_surface_intersections(OUT/"spin-pull-cap.stl",4,57)
    fork_section=x_surface_intersections(OUT/"spin-hold-fork.stl",4,57)
    cover_face=x_surface_intersections(OUT/"spin-cover.stl",4,57)
    hold_from_entities=fork_section[-1]-cap_section[0]
    no_contact_gap=free_face+hold_from_entities-bore_max/2
    spring_max_from_entities=seat_section[0]-plate_section[-1]
    spring_min_from_entities=spring_max_from_entities-measured_preload-measured_retreat
    report = {
        "status": "CANDIDATE_GEOMETRY_ONLY_PHYSICAL_VALIDATION_OPEN",
        "source_sha256": {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ("cad/parameters.scad","cad/spin-parameters.scad","cad/spin-head.scad","analysis/spin_head_geometry.py","analysis/spin_complete_hardware.py","analysis/feeder_body_geometry.py")},
        "parts": part_reports, "entity_intersections": tests,
        "all_expected_intersections_match": all(item["matches_expectation"] for item in tests),
        "all_part_meshes_watertight": all(item["mesh"]["watertight"] for item in part_reports),
        "all_parts_single_component": all(item["mesh"]["connected_components"] == 1 for item in part_reports),
        "independent_geometry_from_exported_meshes": {
            "soft_face_x_mm": free_face, "rigid_carrier_front_x_mm": hard_front,
            "small_ball_opposite_guide_rightmost_x_mm": min_ball_rightmost,
            "large_ball_opposite_guide_rightmost_x_mm": max_ball_rightmost,
            "small_ball_lifts_pad_off_inward_stop_mm": min_ball_rightmost-free_face,
            "available_radial_retreat_mm": p["sh_float_travel"],
            "largest_ball_required_retreat_mm": max_ball_rightmost-free_face,
            "remaining_retreat_at_large_ball_tangency_mm": free_face+p["sh_float_travel"]-max_ball_rightmost,
            "rigid_carrier_front_beyond_probe_radius_mm": hard_front-p["sh_clearance_probe_d"]/2,
            "datum_note": "Actual CAD uses a fixed X datum; opposite wall moves by half the bore change. This differs from per-bore p-coordinate stop budgets.",
            "actual_triangle_section_hits_x_mm": {
                "carriage_at_y9_z43":plate_section,
                "cover_retreat_stop_at_y9_z32":retreat_stop_section,
                "cage_inner_stop_at_y5p8_z43":cage_stop_section,
                "seat_at_y5p8_z43":seat_section,
                "cover_outer_seat_stop_at_y5p8_z43":seat_outer_stop_section,
            },
            "retreat_from_entity_sections_mm":measured_retreat,
            "preload_stroke_from_entity_sections_mm":measured_preload,
            "preload_zero_outer_stop_gap_from_entities_mm":seat_outer_stop_section[0]-seat_section[-1],
            "section_checks": {
                "retreat_meets_configured_value":abs(measured_retreat-p["sh_float_travel"])<1e-4,
                "preload_meets_configured_value":abs(measured_preload-p["sh_preload_travel"])<1e-4,
                "largest_ball_has_retreat_margin":free_face+measured_retreat>max_ball_rightmost,
                "smallest_ball_can_lift_pad_off_stop":min_ball_rightmost>free_face,
                "hold_position_measured_from_fork_and_cap":abs(hold_from_entities-p["sh_hold_shift"])<1e-4,
                "fork_reacts_on_cover_outer_face":abs(fork_section[0]-cover_face[-1])<1e-4,
                "soft_pad_full_bore_clearance_at_least_one_mm":no_contact_gap>=1,
                "manufacturing_budget_leaves_positive_clearance":no_contact_gap>p["sh_no_contact_budget"],
            },
        },
        "pad_held_clear_only_not_zero_spin": {
            "cap_section_x_mm":cap_section,"fork_section_x_mm":fork_section,"cover_section_x_mm":cover_face,
            "hold_shift_from_mesh_sections_mm":hold_from_entities,
            "held_face_x_mm":free_face+hold_from_entities,
            "largest_bore_radius_mm":bore_max/2,
            "nominal_full_bore_clearance_mm":no_contact_gap,
            "combined_print_position_and_pad_sag_budget_mm":p["sh_no_contact_budget"],
            "remaining_budgeted_clearance_mm":no_contact_gap-p["sh_no_contact_budget"],
            "budget_verified_by_print_or_measurement":False,
            "install_overtravel_mm":measured_retreat-hold_from_entities,
            "normal_work_requires_fork_removed":True,
            "new_fasteners_nominal": {"M3x45_socket_head":1,"M3x16_socket_head":1,"M3_hex_nut_AF5p5_h2p4":2,"M3_plain_washer_0p5":1},
            "pull_screw_tip_x_mm":p["sh_pull_cap_x"]+p["sh_pull_cap_length"]-p["sh_pull_screw_length"],
            "pull_nut_axial_span_mm":[p["sh_pull_nut_x"]+0.3,p["sh_pull_nut_x"]+2.7],
            "screw_head_diameter_height_mm":[5.5,3],
            "minimum_upper_pin_radial_wall_around_hole_mm":(p["sh_guide_pin_d"]-3.4)/2,
            "cover_removal_precondition":"Remove pull cap and M3x45 first; tests assume cap removed.",
            "retention_load_path":"carriage captive nut -> M3x45 -> cap -> fork -> cover -> four M3 cover screws -> body",
            "tether":"2.5 mm cord eyes on fork and cover; cord routing and strength physically OPEN",
        },
        "spring_geometry_only": {
            "seat_spacing_max_mm": p["sh_spring_seat_front_x"]-p["sh_carrier_back_x"],
            "seat_spacing_min_at_max_preload_and_retreat_mm": p["sh_spring_seat_front_x"]-p["sh_preload_travel"]-p["sh_carrier_back_x"]-p["sh_float_travel"],
            "outer_diameter_envelope_mm":p["sh_spring_envelope_od"],
            "pilot_diameter_mm":p["sh_spring_pilot_d"],
            "spring_selected_as_design_candidate":"Lee Spring LC 016DE 10M",
            "catalog_source":"https://www.leespring.co.uk/sites/default/files/2020-01/Compression_Springs_Lee_Spring_UK_Eng.pdf",
            "catalog_od_free_wire_solid_mm":[p["sh_spring_candidate_od"],p["sh_spring_candidate_free_length"],p["sh_spring_candidate_wire"],p["sh_spring_candidate_solid_height"]],
            "catalog_rate_N_per_mm":p["sh_spring_candidate_rate"],
            "catalog_inner_diameter_from_wire_mm":p["sh_spring_candidate_od"]-2*p["sh_spring_candidate_wire"],
            "support_lengths_from_entity_sections_mm":[spring_min_from_entities,spring_max_from_entities],
            "calculated_nominal_force_range_N":[p["sh_spring_candidate_rate"]*(p["sh_spring_candidate_free_length"]-length) for length in (spring_max_from_entities,spring_min_from_entities)],
            "minimum_space_minus_catalog_solid_height_mm":spring_min_from_entities-p["sh_spring_candidate_solid_height"],
            "source_note":"Catalog values supplied/read by main task; approximate solid height and nominal linear rate. No actual spring purchased or tested.",
            "spring_force_verified":False,"solid_height_physically_verified":False,
        },
        "collar_nominal_circumference_budget_only": {
            "slot_width_mm":p["sh_socket_slit"],
            "ideal_circumference_reduction_to_nominal_pipe_mm":math.pi*2*p["interface_radial_clearance"],
            "nominal_slot_remaining_mm":p["sh_socket_slit"]-math.pi*2*p["interface_radial_clearance"],
            "real_clamping_deformation_and_torque_verified":False,
        },
        "pad_material_selection":"Bambu TPU 95A HF; other printed spin parts PETG",
        "open_evidence": ["actual tube and ball dimensions", "clamp torque, pipe ovalization and locking", "spring dimensions, solid height and force curve", "selected TPU95A HF pad wear and compliant deformation", "PETG opposing guide friction", "FDM fit, support removal and fastener access in print", "actual airflow, speed and spin", "full dynamic ball and pad motion"],
    }
    if args.render:
        report["rendered_views"] = []
        for name, part, camera, definitions in (
            ("spin-isometric","assembly","155,-190,130,0,0,25",{}),
            ("spin-front","assembly","150,0,35,0,0,35",{}),
            ("spin-top","assembly","0,0,220,0,0,20",{}),
            ("spin-section","section","135,185,115,8,0,25",{}),
            ("spin-exploded","exploded","180,-210,160,25,0,30",{}),
            ("spin-work-section","section","35,220,47,35,0,47",{"float_shift":2.25,"preload_shift":4}),
            ("spin-hold-section","section","35,220,47,35,0,47",{"float_shift":p["sh_hold_shift"],"preload_shift":4,"hold_mode":"true"}),
            ("spin-held-section","section","35,220,47,35,0,47",{"float_shift":p["sh_hold_shift"],"preload_shift":4,"hold_mode":"true"}),
            ("spin-hold-isometric","assembly","155,-190,130,0,0,25",{"float_shift":p["sh_hold_shift"],"preload_shift":4,"hold_mode":"true"}),
        ):
            command=[OPENSCAD,"--hardwarnings","--backend","Manifold","--render","--imgsize","1300,1000","--projection","o","--viewall","--colorscheme","Tomorrow","--camera",camera,"-D",f'part="{part}"',"-o",str(OUT/(name+".png")),str(SOURCE)]
            for key,value in definitions.items(): command.extend(["-D",f"{key}={value}"])
            subprocess.run(command,cwd=ROOT,check=True,capture_output=True,text=True)
            report["rendered_views"].append({"file":str((OUT/(name+".png")).relative_to(ROOT)),"part":part,"definitions":definitions,"sha256":hashlib.sha256((OUT/(name+".png")).read_bytes()).hexdigest()})
    target = ROOT / "output" / "analysis" / "spin-head-geometry.json"
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    failed = [item["name"] for item in tests if not item["matches_expectation"]]
    section_checks = report["independent_geometry_from_exported_meshes"]["section_checks"]
    print(json.dumps({"report":str(target),"unexpected_intersections":failed,"watertight":report["all_part_meshes_watertight"],"single_components":report["all_parts_single_component"]},ensure_ascii=False))
    if failed or not report["all_part_meshes_watertight"] or not report["all_parts_single_component"] or not all(section_checks.values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
