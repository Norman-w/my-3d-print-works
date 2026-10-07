#!/usr/bin/env python3
"""Digital FAN76 checks on final STL: topology, overhangs, motion and bayonet.

Finite mesh sampling plus analytic envelope/phase/complete-turn accounting.
This does not invoke a slicer and cannot verify printed fit or ball clearance.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import subprocess
import sys
import time

import manifold3d as mf
import numpy as np
import trimesh

from export_fan76_direct_v1 import OUT, ROOT, SKILL, SOURCES, PARTS, sha, dump

P = json.loads((OUT / "verification/parameters.json").read_text())
TOL = 1e-5


def mesh_path(part: str) -> Path:
    return OUT / "stl" / f"fan76-direct-v1-{part}-clean.stl"


def read(path: Path):
    mesh = trimesh.load_mesh(path, process=True)
    if not mesh.is_watertight or not mesh.is_volume:
        raise ValueError(f"Not a positive closed solid: {path}")
    solid = mf.Manifold(mf.Mesh(np.asarray(mesh.vertices, dtype=np.float32),
                                np.asarray(mesh.faces, dtype=np.uint32)))
    if solid.status() != mf.Error.NoError:
        raise ValueError(f"Manifold rejected {path}: {solid.status()}")
    return mesh, solid


def pose(solid, z: float, angle: float):
    return solid.rotate([0, 0, float(angle)]).translate([0, 0, float(z)])


def angle(z: float) -> float:
    return 360 * (z + P["male_z0"] - P["female_z0"]) / P["pitch"]


def normals_report(mesh, part: str):
    c, n, area = mesh.triangles_center, mesh.face_normals, mesh.area_faces
    r = np.linalg.norm(c[:, :2], axis=1)
    downward = (n[:, 2] < -1e-5) & (c[:, 2] > 0.05)
    alpha = np.degrees(np.arccos(np.clip(-n[:, 2], -1, 1)))
    # The FINAL mother material is examined; never substitute groove cutter normals.
    region = ((c[:, 2] >= 66) & (c[:, 2] <= 186) & (r < 21.5)) if part == "body" else (
        (c[:, 2] >= 4) & (c[:, 2] <= 28) & (r > 19.85))

    def summary(mask):
        ids = np.flatnonzero(mask)
        significant = mask & (area > 1e-6)
        return {"faces": len(ids), "area_mm2": float(area[mask].sum()),
                "min_angle_to_horizontal_deg": float(alpha[mask].min()) if len(ids) else None,
                "min_angle_faces_area_gt_1e_6_deg": float(alpha[significant].min()) if significant.any() else None,
                "area_below_49_8_deg_mm2": float(area[mask & (alpha < 49.8)].sum()),
                "area_below_45_deg_mm2": float(area[mask & (alpha < 45)].sum()),
                "area_below_10_deg_mm2": float(area[mask & (alpha < 10)].sum())}

    critical = downward & region & (alpha < 49.8)
    other = downward & ~region & (alpha < 49.8)
    report = {"part_id": part, "orientation": "+Z upright; z=0 on bed",
              "angle_convention": "Degrees to horizontal; 0 is underside, 90 is vertical",
              "thread_and_runout": summary(downward & region),
              "all_nonbed_downward": summary(downward),
              "thread_geometry_candidate_pass": float(area[critical].sum()) < 1e-4,
              "below_threshold_nonthread_regions": [],
              "slicer_validation": "PENDING; no support contact/G-code is present"}
    categorized = np.zeros(len(c), dtype=bool)
    for label, lo, hi in [("fan entry chamfer", .05, 1.21), ("bayonet roof", 21.49, 21.51),
                           ("fan face datum - no shoulder expected", 23.99, 24.01), ("other", 0.05, 400)]:
        mask = other & (c[:, 2] >= lo) & (c[:, 2] <= hi)
        if label == "other":
            mask &= ~categorized
        categorized |= mask
        if mask.any():
            report["below_threshold_nonthread_regions"].append({"region": label, **summary(mask),
                "bounds_min": mesh.triangles[mask].reshape(-1, 3).min(axis=0).tolist(),
                "bounds_max": mesh.triangles[mask].reshape(-1, 3).max(axis=0).tolist()})
    return report


def mesh_checks():
    rows = []
    for part in PARTS:
        path = mesh_path(part)
        mesh, solid = read(path)
        components = solid.decompose()
        normals = normals_report(mesh, part)
        expected = np.array([86, 86, 222]) if part == "body" else np.array([41.8, 41.8, 160])
        row = {"part_id": part, "sha256": sha(path), "bbox_min": mesh.bounds[0].tolist(),
               "bbox_max": mesh.bounds[1].tolist(), "size_mm": mesh.extents.tolist(),
               "volume_mm3": float(mesh.volume), "surface_area_mm2": float(mesh.area),
               "faces": len(mesh.faces), "watertight": bool(mesh.is_watertight),
               "winding_consistent": bool(mesh.is_winding_consistent), "one_connected_solid": len(components) == 1,
               "connected_solids": len(components), "manifold_status": str(solid.status()),
               "bounds_match_contract": bool(np.allclose(mesh.extents, expected, atol=0.002)),
               "fits_256_bed_and_245_preferred_height": bool(np.all(mesh.extents <= [256, 256, 245])),
               "normals": normals}
        row["pass"] = all([row["watertight"], row["winding_consistent"], row["one_connected_solid"],
                            row["bounds_match_contract"], row["fits_256_bed_and_245_preferred_height"],
                            normals["thread_geometry_candidate_pass"]])
        rows.append(row)
        print(part, "mesh + normals", "PASS" if row["pass"] else "FAIL",
              "thread angle", normals["thread_and_runout"]["min_angle_to_horizontal_deg"], flush=True)
    result = {"pass": all(r["pass"] for r in rows), "parts": rows,
              "limitations": "Triangle-normal geometry screening is not a no-support slicing or physical-print guarantee."}
    dump(OUT / "verification/mesh-and-overhang.json", result)
    return result["pass"]


def motion_checks(step: float):
    _, body = read(mesh_path("body"))
    started = time.monotonic()

    def check_core(part: str):
        path = mesh_path(part)
        report_path = OUT / f"verification/motion-{part}.json"
        command = [sys.executable, str(SKILL / "scripts/check_thread_motion.py"), str(mesh_path("body")), str(path),
                   "--seated-z", str(P["core_min_z"]), "--approach-z", str(P["straight_handoff_z"]),
                   "--pitch", str(P["pitch"]), "--phase", str(angle(P["core_min_z"])),
                   "--step", str(step), "--output", str(report_path)]
        result = subprocess.run(command, capture_output=True, text=True)
        (OUT / f"verification/logs/motion-{part}.log").write_text(result.stdout + result.stderr)
        if not report_path.exists():
            raise RuntimeError(result.stderr)
        helical = json.loads(report_path.read_text())
        _, core = read(path)
        # All cores start completely outside the outlet. No rotation in this section.
        straight = [{"core_z": float(z), "angle_deg": angle(P["straight_handoff_z"]),
                     "intersection_mm3": float((body ^ pose(core, z, angle(P["straight_handoff_z"]))).volume())}
                    for z in np.arange(223, P["straight_handoff_z"] - .001, -.5)]
        # Refine the last turn entering the female groove and both operating limits.
        fine_z = np.unique(np.concatenate([np.arange(176, 180.0001, .03125),
                                          np.arange(70, 70.501, .03125), np.arange(149.5, 150.001, .03125)]))
        fine = [{"core_z": float(z), "angle_deg": angle(z),
                 "intersection_mm3": float((body ^ pose(core, z, angle(z))).volume())} for z in fine_z]
        wrong = [{"core_z": z, "wrong_angle_deg": angle(z) + 180,
                  "intersection_mm3": float((body ^ pose(core, z, angle(z) + 180)).volume())}
                 for z in [P["core_min_z"], 110, P["core_max_z"]]]
        peak = max([helical["max_intersection_mm3"]] + [r["intersection_mm3"] for r in straight + fine])
        passed = result.returncode == 0 and peak <= TOL and all(r["intersection_mm3"] > 1 for r in wrong)
        row = {"part_id": part, "pass": passed, "stl_sha256": sha(path),
               "canonical_helper_command": command, "helical_result": str(report_path.relative_to(OUT)),
               "correct_path_max_intersection_mm3": peak, "axial_approach": straight,
               "entry_and_endpoint_refinement": fine, "wrong_phase_counterexamples": wrong,
               "rotation_translation_law": "angle=360*(core_z+4-70)/4; positive angle about +Z",
               "path_pose_count": len(helical["poses"]) + len(straight) + len(fine),
               "physical_fit_verified": False}
        dump(OUT / f"verification/wholepath-{part}.json", row)
        print(part, "wholepath", "PASS" if passed else "FAIL", "max intersection", peak,
              "wrong phase", [r["intersection_mm3"] for r in wrong], flush=True)
        return {k: row[k] for k in ["part_id", "pass", "stl_sha256", "correct_path_max_intersection_mm3",
                                     "path_pose_count", "wrong_phase_counterexamples"]}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(check_core, PARTS[1:]))
    result = {"pass": all(r["pass"] for r in results), "body_sha256": sha(mesh_path("body")),
              "elapsed_s": time.monotonic() - started, "helical_step_mm": step, "parts": results,
              "analytic_complement": "All nonthread core radii <=20, below female minor radius20.3. ID44 guide contains male radius20.9. Female cutter is the translated male r-z profile; same 4mm pitch and phase. Reverse traversal uses the same poses.",
              "limitations": "Finite mesh sampling, not continuous collision proof under printed tolerance/deformation."}
    dump(OUT / "verification/wholepath-summary.json", result)
    return result["pass"]


def bayonet_checks():
    _, body = read(mesh_path("body"))
    _, fan = read(OUT / "review/review-fan-envelope.stl")
    straight = [{"offset_z": float(z), "angle_deg": 0,
                 "intersection_mm3": float((body ^ pose(fan, z, 0)).volume())}
                for z in np.arange(-25, .0001, .25)]
    turned = [{"offset_z": 0, "angle_deg": float(a),
               "intersection_mm3": float((body ^ pose(fan, 0, a)).volume())}
              for a in np.arange(0, 18.0001, .25)]
    # Exercise the entire specified +0.5mm axial slack, including rotation.
    clearance_poses = [{"offset_z": float(z), "face_z": 24 + float(z), "angle_deg": float(a),
                        "intersection_mm3": float((body ^ pose(fan, z, a)).volume())}
                       for z in np.arange(0, .5001, .125) for a in np.arange(0, 18.0001, .5)]
    counterexamples = [{"state": label, "offset_z": z, "angle_deg": a,
                        "intersection_mm3": float((body ^ pose(fan, z, a)).volume())}
                       for label, z, a in [("locked withdrawal contacts bearing floor", -1, 18),
                                            ("overturn contacts endwall", 0, 22),
                                            ("lug roof limits axial overtravel - no fan-face shoulder", 1, 18)]]
    peak = max(r["intersection_mm3"] for r in straight + turned + clearance_poses)
    result = {"pass": peak <= TOL and all(r["intersection_mm3"] > 1 for r in counterexamples),
              "body_sha256": sha(mesh_path("body")),
              "fan_reference_sha256": sha(OUT / "review/review-fan-envelope.stl"),
              "max_correct_path_intersection_mm3": peak, "straight_insertion": straight,
              "rotation": turned, "face_z24_to_24_5_rotation_sweep": clearance_poses, "counterexamples": counterexamples,
              "structural_geometry": {"minimum_radial_outer_web_mm": 43 - P["slot_outer_r"],
                  "bearing_floor_z_mm": P["slot_floor_z"], "roof_z_mm": P["slot_roof_z"],
                  "roof_to_collar_top_mm": 30 - P["slot_roof_z"],
                  "radial_lug_overlap_past_socket_mm": 40 - P["socket_id"] / 2,
                  "nominal_projected_two_lug_bearing_area_mm2": 2 * 7.5 * (40 - P["socket_id"] / 2),
                  "bearing_area_note": "Projection estimate, not contact/stress/strength acceptance"},
              "support_access": "Only the horizontal z21.5 slot roofs remain; no z24 annular shoulder. Slot floors exist at z12.5, so buildplate-only trees may not reach every roof. Slicer must inspect/enforce contacts and may require support starting on internal slot floors. Extract inward into ID76.6 socket, then out fan mouth; narrow entry slots alone are not the removal route.",
              "unverified": ["lug manufacturing tolerance", "torsional retention/detent absent", "layer strength", "support removal", "air seal"]}
    dump(OUT / "verification/bayonet-path.json", result)
    print("bayonet", "PASS" if result["pass"] else "FAIL", "correct maximum", peak,
          "counterexamples", counterexamples, flush=True)
    return result["pass"]


def contract_checks():
    full_lo, full_hi, half, pitch = P["male_full_z0"], P["male_full_z1"], P["profile_half"], P["pitch"]
    # Four complete centerline turns whose ENTIRE profile, including buried root,
    # is inside the full-height male zone, rather than counting runout fragments.
    centers = [[8 + 4 * i, 12 + 4 * i] for i in range(4)]
    endpoints = []
    for offset in [P["core_min_z"], P["core_max_z"]]:
        turns = [{"local_centerline_z": pair, "world_full_profile_z": [offset + pair[0] - half,
                   offset + pair[1] + half], "complete": pair[0] - half >= full_lo and pair[1] + half <= full_hi
                   and offset + pair[0] - half >= P["female_z0"]
                   and offset + pair[1] + half <= P["female_z1"]} for pair in centers]
        endpoints.append({"core_z": offset, "complete_turn_count": sum(t["complete"] for t in turns), "turns": turns})
    samples = []
    body_mesh, body = read(mesh_path("body"))
    for z in [184.01, 190, 197.01, 210, 220, 221.19, 221.6]:
        segments = trimesh.intersections.mesh_plane(body_mesh, [0, 0, 1], [0, 0, z])
        radii = np.linalg.norm(segments[:, :, :2].reshape(-1, 2), axis=1)
        samples.append({"z": z, "min_inner_diameter_mm": float(2 * radii.min()),
                        "max_outer_diameter_mm": float(2 * radii.max())})
    gauge = mf.Manifold.cylinder(222 - 184, 20.9, 20.9, 192).translate([0, 0, 184])
    entry_intersection = float((body ^ gauge).volume())
    fan_datum_samples = []
    for z in [23.999, 24.001, 24.25, 24.5, 25, 30]:
        segments = trimesh.intersections.mesh_plane(body_mesh, [0, 0, 1], [0, 0, z])
        radii = np.linalg.norm(segments[:, :, :2].reshape(-1, 2), axis=1)
        fan_datum_samples.append({"z": z, "min_inscribed_section_id_mm": float(2 * radii.min())})
    c, n = body_mesh.triangles_center, body_mesh.face_normals
    face_shoulder_area = float(body_mesh.area_faces[(abs(c[:, 2] - 24) < .01) & (n[:, 2] < -.99)].sum())
    low_nonslot = (c[:, 2] > .05) & (abs(c[:, 2] - 21.5) > .01) & (n[:, 2] < -math.cos(math.radians(45)))
    low_nonslot_area = float(body_mesh.area_faces[low_nonslot].sum())
    checks = {"pitch_exactly_4": pitch == 4, "effective_travel_exactly_80": P["travel"] == 80,
              "twenty_adjustment_turns": P["travel"] / pitch == 20,
              "at_least_three_complete_turns_both_ends": min(r["complete_turn_count"] for r in endpoints) >= 3,
              "full_depth_major_diameter_gauge_free": entry_intersection <= TOL,
              "guide_bore_above_male_major": min(s["min_inner_diameter_mm"] for s in samples) > 41.8,
              "sources_match_snapshot": all(sha(ROOT / "cad" / n) == sha(OUT / "source" / n) for n in SOURCES),
              "five_clean_print_stls": len(list((OUT / "stl").glob("*.stl"))) == 5}
    checks["no_horizontal_fan_face_shoulder_z24"] = face_shoulder_area < 1e-6
    checks["fan_od76_clears_at_face_plus_0_5"] = fan_datum_samples[3]["min_inscribed_section_id_mm"] > 76
    checks["only_slot_roof_has_nonbed_faces_below_45deg"] = low_nonslot_area < 1e-4
    result = {"pass": all(checks.values()), "checks": checks, "engagement_endpoints": endpoints,
              "guide_major_gauge_intersection_mm3": entry_intersection, "sampled_guide_spigot_diameters": samples,
              "fan_datum_transition_sections": fan_datum_samples,
              "horizontal_fan_face_shoulder_z24_area_mm2": face_shoulder_area,
              "nonbed_nonslot_area_below_45deg_mm2": low_nonslot_area,
              "geometric_wall_budget_mm": {"spigot_nominal": 3, "spigot_short_chamfer_tip": 2.65,
                 "body_at_deepest_groove": (54 - 42.3) / 2, "core_radial_wall": 2,
                 "core_tip_grip_flats_minimum": 1.5, "mother_tooth_tip_web": P["female_min_web"]},
              "profile": {"style": "outward ridge / finite flat trapezoid with independent buried root",
                 "exposed_height": .9, "flat_crest_axial_width": .8, "buried_root_width": 2 * half,
                 "exposed_flank_to_horizontal_deg": 50, "root_embed": .2,
                 "root_shoulder_buried": .05, "male_core_od": 40, "male_major": 41.8,
                 "female_minor": 40.6, "female_major": 42.3, "groove_radial_clearance": .25,
                 "groove_axial_clearance_per_flank": .2,
                 "approx_radial_growth_per_0_2mm_layer": .2 / math.tan(math.radians(50))},
              "adjustment_use": {"core_inlet_z_mm": [70, 150], "tip_z_mm": [230, 310],
                 "tip_past_body_outlet_mm": [8, 88], "tip_past_assumed_Y_mouth_mm": [33, 113],
                 "effective_range_is_not_extra_engagement": True,
                 "grip": "Last 8mm carries opposed external flats; exposed at minimum. Adjust with Y detached unless actual Y tool-access is measured.",
                 "limits": "No captive stop or locking ring. Measure tip protrusion 8..88mm; 4mm per turn. Do not continue beyond this qualified window.",
                 "bypass": "No seal/crossbar. Clearance annulus remains, so outlet ID is not a calibrated sole flow area.",
                 "Y_ball_clearance": "UNKNOWN: actual stop depth, branch intersection and swept ball envelope must be measured before operating."}}
    dump(OUT / "verification/mechanical-contract.json", result)
    print("mechanical contract", checks, flush=True)
    return result["pass"]


def write_manifest():
    manifest = json.loads((OUT / "manifest.json").read_text())
    exported = json.loads((OUT / "verification/export.json").read_text())
    for key in ["files", "source_sha256", "skill_files_sha256", "openscad_version", "generated_utc"]:
        manifest[key] = exported[key]
    reports = {}
    names = ["mesh-and-overhang", "wholepath-summary", "bayonet-path", "mechanical-contract"]
    for name in names:
        path = OUT / "verification" / f"{name}.json"
        if path.exists():
            reports[name] = {"file": str(path.relative_to(OUT)), "sha256": sha(path),
                             "pass": json.loads(path.read_text())["pass"]}
    mesh_hashes = {part: sha(mesh_path(part)) for part in PARTS}
    bindings = {}
    mesh_report = OUT / "verification/mesh-and-overhang.json"
    if mesh_report.exists():
        bindings["mesh_report_bound_to_current_stl"] = all(mesh_hashes[r["part_id"]] == r["sha256"]
            for r in json.loads(mesh_report.read_text())["parts"])
    motion_report = OUT / "verification/wholepath-summary.json"
    if motion_report.exists():
        motion = json.loads(motion_report.read_text())
        bindings["motion_report_bound_to_current_stl"] = motion["body_sha256"] == mesh_hashes["body"] and all(
            mesh_hashes[r["part_id"]] == r["stl_sha256"] for r in motion["parts"])
    render_report = OUT / "verification/render-provenance.json"
    if render_report.exists():
        rendered = json.loads(render_report.read_text())
        bindings["render_bound_to_current_stl"] = rendered["mesh_sha256"] == mesh_hashes
        reports["render-provenance"] = {"file": str(render_report.relative_to(OUT)), "sha256": sha(render_report),
                                        "pass": bindings["render_bound_to_current_stl"]}
    visual_report = OUT / "verification/visual-review.json"
    if visual_report.exists():
        visual = json.loads(visual_report.read_text())
        bindings["visual_review_bound_to_current_images"] = all(sha(OUT / r["file"]) == r["sha256"] for r in visual["images"])
        reports["visual-review"] = {"file": str(visual_report.relative_to(OUT)), "sha256": sha(visual_report),
                                    "pass": bool(visual["pass"] and bindings["visual_review_bound_to_current_images"])}
    passed = all(n in reports and reports[n]["pass"] for n in names) and all(bindings.values())
    manifest.update({"status": "DIGITAL_GEOMETRY_PASS_PHYSICAL_AND_SLICE_PENDING" if passed else "DIGITAL_VALIDATION_INCOMPLETE_OR_FAILED",
                     "verification": reports, "current_evidence_bindings": bindings, "digital_geometry_pass": passed,
                     "sliced": False, "three_mf": None, "embedded_supports": False,
                     "physical_fit_verified": False, "Y_ball_path_verified": False,
                     "cad_worker_scope": "source, clean STL and digital evidence only; no print directory writes",
                     "script_sha256": {p.name: sha(p) for p in sorted((ROOT / "scripts").glob("*fan76_direct_v1*.py"))
                                       if p.name not in ["prepare_fan76_direct_v1_print.py", "verify_fan76_direct_v1_print.py"]}})
    if (OUT / "verification/mesh-and-overhang.json").exists():
        manifest["mesh_summary"] = json.loads((OUT / "verification/mesh-and-overhang.json").read_text())["parts"]
    # Canonical inspect was executed on a staging file; publish its final path.
    for row in manifest["files"]:
        row["topology"]["path"] = str(OUT / row["file"])
        report_path = OUT / "verification" / f'topology-{row["part_id"]}.json'
        if report_path.exists():
            topology = json.loads(report_path.read_text())
            topology["path"] = str(OUT / row["file"])
            dump(report_path, topology)
    manifest["cad_deliverables"] = [{"file": str(p.relative_to(OUT)), "sha256": sha(p)}
        for folder in ["source", "stl", "review", "render"] for p in sorted((OUT / folder).glob("*")) if p.is_file()]
    if (OUT / "README.md").exists():
        manifest["readme_sha256"] = sha(OUT / "README.md")
    dump(OUT / "manifest.json", manifest)
    package_files = [OUT / "manifest.json"] + [OUT / r["file"] for r in manifest["cad_deliverables"]]
    package_files += [p for p in sorted((OUT / "verification").glob("*.json"))]
    if (OUT / "README.md").exists():
        package_files.append(OUT / "README.md")
    (OUT / "verification/SHA256SUMS.txt").write_text("".join(
        f"{sha(p)}  {p.relative_to(OUT)}\n" for p in package_files))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checks", nargs="+", choices=["mesh", "motion", "bayonet", "contract"],
                    default=["mesh", "motion", "bayonet", "contract"])
    ap.add_argument("--step", type=float, default=.25)
    a = ap.parse_args()
    results = []
    for name in a.checks:
        results.append({"mesh": mesh_checks, "motion": lambda: motion_checks(a.step),
                        "bayonet": bayonet_checks, "contract": contract_checks}[name]())
    write_manifest()
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
