#!/usr/bin/env python3
"""Version-selected final-mesh topology, insertion, thread-phase and bayonet audit.

Finite pose sampling and analytic invariants, not CFD or physical fit acceptance.
No mesh repair, slicing, printer access, old-package changes or Git mutation.
"""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import math
import time

import manifold3d as mf
import numpy as np
import trimesh

from build_fan76_smooth_v2 import ROOT, sha, dump
from fan76_smooth_release import smooth_release


def read(path):
    mesh = trimesh.load_mesh(path, process=True)
    assert mesh.is_watertight and mesh.is_volume and mesh.is_winding_consistent, path
    solid = mf.Manifold(mf.Mesh(np.asarray(mesh.vertices, dtype=np.float32),
                                np.asarray(mesh.faces, dtype=np.uint32)))
    assert solid.status() == mf.Error.NoError, path
    return mesh, solid


def posed(solid, z, angle):
    return solid.rotate([0, 0, float(angle)]).translate([0, 0, float(z)])


def audit_thin_shell(mesh, out, p):
    """Independent radial wall witnesses from planes through the FINAL STL."""
    samples = np.asarray(json.loads((out / "verification/profile-samples.json").read_text()))
    z, inner, outer = samples.T
    reducer = (z >= p["blend_z0"]) & (z <= p["blend_z1"])
    witnesses = []
    for degrees in np.arange(0, 180, 22.5):
        theta = np.radians(degrees)
        axis = np.array([np.cos(theta), np.sin(theta), 0])
        normal = np.array([-np.sin(theta), np.cos(theta), 0])
        segments = trimesh.intersections.mesh_plane(mesh, normal, normal*.017)
        rz = np.stack([segments @ axis, segments[:, :, 2]], axis=2)
        for height in np.arange(26.125, p["body_height"]-.5, .5):
            zs = rz[:, :, 1]
            hit = rz[(zs.min(axis=1) < height) & (zs.max(axis=1) > height)]
            alpha = (height-hit[:, 0, 1])/(hit[:, 1, 1]-hit[:, 0, 1])
            radii = hit[:, 0, 0]+alpha*(hit[:, 1, 0]-hit[:, 0, 0])
            for side in [-1, 1]:
                vals = np.sort(radii[radii*side > 0]*side)
                vals = vals[np.r_[True, np.diff(vals) > 1e-5]]
                assert len(vals) == 2, (height, degrees, side, vals)
                witnesses.append([float(degrees), side, float(height), float(vals[1]-vals[0])])
    measured_min = min(row[3] for row in witnesses)
    checks = {
        "actual_radial_wall_matches_contract": measured_min >= p["thin_wall_radial_nominal"]-.01,
        "nominal_bore_wall_matches_contract": np.min(outer[z >= 26]-inner[z >= 26]) >= p["thin_wall_radial_nominal"]-.0002,
        "monotone_reducer_inner": bool(np.all(np.diff(inner[reducer]) <= 1e-4)),
        "monotone_reducer_outer": bool(np.all(np.diff(outer[reducer]) <= 1e-4)),
        "paired_thread_root_wall_2_4": abs((p["thread_shell_od"]-p["female_major"])/2-2.4) < 1e-6,
        "spigot_wall_still_3": (p["spigot_od"]-p["spigot_id"])/2 == 3,
    }
    checks = {key: bool(value) for key, value in checks.items()}
    report = {"pass": all(checks.values()), "checks": checks, "sampled_radial_wall_min_mm": measured_min,
              "required_radial_wall_mm": p["thin_wall_radial_nominal"],
              "witness_count": len(witnesses), "witnesses_degrees_side_z_wall": witnesses,
              "method": "8 final-mesh section planes, both radial sides, 0.5mm axial spacing; excludes bayonet below Z26.",
              "scope": "Radial thickness, not surface-normal thickness or strength acceptance."}
    dump(out / "verification/wall-thickness.json", report)
    return {k: v for k, v in report.items() if k != "witnesses_degrees_side_z_wall"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", type=int, choices=[2, 3, 4, 5], default=2)
    release = smooth_release(parser.parse_args().revision)
    OUT, SOURCES = release.out, release.sources
    start = time.monotonic()
    exported = json.loads((OUT / "verification/export.json").read_text())
    p = json.loads((OUT / "verification/parameters.json").read_text())
    for name in SOURCES:
        assert sha(ROOT / "cad" / name) == exported["source_sha256"][name]
    records = {r["part_id"]: r for r in exported["files"]}
    meshes, solids, topology = {}, {}, []
    for part, record in records.items():
        path = OUT / record["file"]
        assert sha(path) == record["sha256"]
        if part.startswith("core"):
            assert path.read_bytes() == (ROOT / record["copied_from"]).read_bytes()
        mesh, solid = read(path)
        meshes[part], solids[part] = mesh, solid
        if not record["print_target"]:
            continue
        c, n, area = mesh.triangles_center, mesh.face_normals, mesh.area_faces
        radius = np.linalg.norm(c[:, :2], axis=1)
        region = ((c[:, 2] >= p["female_cut_z0"]) & (c[:, 2] <= p["female_cut_z1"]) & (radius < 21.5)) if part == "body" else (
            (c[:, 2] >= 4) & (c[:, 2] <= 28) & (radius > 19.85))
        down = region & (n[:, 2] < -1e-5)
        alpha = np.degrees(np.arccos(np.clip(-n[:, 2], -1, 1)))
        low_area = float(area[down & (alpha < 49.8)].sum())
        expected = [86, 86, release.body_height] if part == "body" else [41.8, 41.8, 106]
        row = {"part": part, "sha256": sha(path), "bounds": mesh.bounds.tolist(),
               "size_mm": mesh.extents.tolist(), "volume_mm3": float(mesh.volume), "faces": len(mesh.faces),
               "closed_positive_volume": True, "connected_components": len(solid.decompose()),
               "dimension_match": bool(np.allclose(mesh.extents, expected, atol=.002)),
               "thread_min_angle_to_horizontal_deg": float(alpha[down].min()),
               "thread_area_below_49_8_deg_mm2": low_area,
               "source_reused_byte_for_byte": record.get("unchanged_bytes", False)}
        row["pass"] = row["connected_components"] == 1 and row["dimension_match"] and low_area < 1e-4
        topology.append(row)
        print(part, "topology/size/thread-normal", row["pass"], flush=True)
    dump(OUT / "verification/mesh.json", {"pass": all(r["pass"] for r in topology), "parts": topology})

    body = solids["body"]
    angle = lambda z: 360 * (z + p["male_z0"] - p["female_z0"]) / p["pitch"]
    def motion(part):
        core = solids[part]
        handoff = p["straight_handoff_z"]
        axial = [{"z": float(z), "intersection_mm3": float((body ^ posed(core, z, angle(handoff))).volume())}
                 for z in np.arange(p["body_height"] + 1, handoff - .001, -.5)]
        # The FULL screw insertion is longer than the intended working travel.
        # At least 32 samples/turn, plus fine entry and limit neighborhoods.
        zs = np.unique(np.concatenate([
            np.arange(p["core_min_z"], handoff + .001, .125),
            np.arange(handoff-4, handoff + .001, .03125),
            np.arange(p["core_min_z"], p["core_min_z"]+.501, .03125),
            np.arange(p["core_max_z"]-.5, p["core_max_z"]+.001, .03125)]))
        helical = [{"z": float(z), "angle": angle(z),
                    "intersection_mm3": float((body ^ posed(core, z, angle(z))).volume())} for z in zs]
        wrong = [{"z": z, "intersection_mm3": float((body ^ posed(core, z, angle(z)+180)).volume())}
                 for z in [p["core_min_z"], (p["core_min_z"]+p["core_max_z"])/2, p["core_max_z"]]]
        peak = max(r["intersection_mm3"] for r in axial+helical)
        result = {"part": part, "pass": peak < 1e-5 and all(r["intersection_mm3"] > 1 for r in wrong),
                  "max_correct_intersection_mm3": peak, "wrong_phase_counterexamples": wrong,
                  "axial_approach": axial, "helical_approach_and_working_travel": helical,
                  "sampled_pose_count": len(axial)+len(helical), "body_sha256": records["body"]["sha256"],
                  "core_sha256": records[part]["sha256"], "physical_fit_verified": False}
        dump(OUT / f"verification/motion-{part}.json", result)
        print(part, "full approach/screw path", result["pass"], peak, flush=True)
        return {key: result[key] for key in ["part", "pass", "max_correct_intersection_mm3", "sampled_pose_count", "wrong_phase_counterexamples"]}
    with ThreadPoolExecutor(max_workers=2) as pool:
        motions = list(pool.map(motion, [f"core{d}" for d in p["outlet_ids"]]))

    fan = solids["review-fan-envelope"]
    poses = [(z, 0) for z in np.arange(-25, .001, .5)]
    poses += [(z, a) for z in [0, .25, .5] for a in np.arange(0, 18.001, .25)]
    correct = [{"z": float(z), "angle": float(a), "intersection_mm3": float((body ^ posed(fan, z, a)).volume())}
               for z, a in poses]
    wrong = [{"label": label, "intersection_mm3": float((body ^ posed(fan, z, a)).volume())}
             for label, z, a in [("locked pullout", -1, 18), ("over-rotation", 0, 22), ("roof stop", 1, 18)]]
    peak = max(r["intersection_mm3"] for r in correct)
    bayonet = {"pass": peak < 1e-5 and all(r["intersection_mm3"] > 1 for r in wrong),
               "max_correct_intersection_mm3": peak, "poses": correct, "counterexamples": wrong,
               "nominal_socket_id": 76, "positive_dimensional_allowance_mm": 0,
               "minimum_radial_slot_roof_web_mm": 43-p["slot_outer_r"],
               "physical_fit_verified": False}
    dump(OUT / "verification/bayonet.json", bayonet)
    previous = json.loads((ROOT / "output" / release.previous_package / "verification/parameters.json").read_text())
    old_peak_angle = previous.get("peak_inner_wall_angle_to_axis_deg", math.degrees(math.atan(1.5*(76.6/2-21.3)/44)))
    shape = {"previous_release": release.previous_package,
             "old_body_mm": previous["body_height"], "new_body_mm": p["body_height"],
             "shorter_mm": previous["body_height"]-p["body_height"],
             "old_fan_face_to_y_mouth_mm": previous["spigot_z0"]-previous["face_z"],
             "new_fan_face_to_y_mouth_mm": p["spigot_z0"]-p["face_z"],
             "old_peak_reducer_wall_angle_to_axis_deg": old_peak_angle,
             "new_peak_reducer_wall_angle_to_axis_deg": p["peak_inner_wall_angle_to_axis_deg"],
             "smooth_function": p["blend_polynomial"],
             "C2_at_reducer_endpoints": True, "radial_wall_min_outside_bayonet_mm": p.get("thin_wall_radial_nominal", 3),
             "contraction_length_mm": p["blend_length"],
             "female_length_mm": p["female_length"],
             "pitch_mm": p["pitch"], "working_turns": p["travel"] / p["pitch"],
             "female_major_wall_mm": (p.get("thread_shell_od", p["tube_od"])-p["female_major"])/2,
             "full_complete_turns_at_limits": [p["complete_turns_min"], p["complete_turns_max"]],
             "v5_core_inlet_lip_retained_mm": 2,
             "limitations": "Core inlet lip and its original straight/conical junctions are retained by requirement. Not every adjusted assembly is a continuous smooth flow wall. No CFD or measured pressure/flow result."}
    design_checks = {
        "body_height_matches_release": p["body_height"] == release.body_height,
        "height_within_design_budget": p["body_height"] <= p.get("design_height_budget", 245),
        "pitch_unchanged": p["pitch"] == 4,
        "complete_turns_both_limits": min(p["complete_turns_min"], p["complete_turns_max"]) >= 4,
        "spigot_od_50": p["spigot_od"] == 50,
        "socket_id_76": p["socket_id"] == 76,
        "gentler_than_previous_contraction": p["peak_inner_wall_angle_to_axis_deg"] < old_peak_angle,
    }
    if release.revision >= 3:
        design_checks.update({
            "contraction_length_matches_release": p["blend_length"] == {3: 110, 4: 120, 5: 124}[release.revision],
            "female_thread_44_and_travel_20": p["female_length"] == 44 and p["travel"] == 20,
            "default_is_retracted": p["default_travel"] == 0,
            "tip_endpoints_4_24": (p["protrusion_min"], p["protrusion_max"]) == (4, 24),
            "tip_calculated_from_unchanged_core": p["core_min_z"]+p["core_height"]-p["body_height"] == 4,
            "thread_profile_unchanged": all(p[k] == previous[k] for k in ["male_profile", "female_profile", "male_major", "female_minor", "female_major"]),
        })
        shape.update({"old_tip_protrusion_mm": [previous["protrusion_min"], previous["protrusion_max"]],
                      "new_tip_protrusion_mm": [p["protrusion_min"], p["protrusion_max"]],
                      "default_tip_from_body_end_mm": 4,
                      "tip_from_illustrative_y_mouth_mm": [p["spigot_length"]+p["protrusion_min"], p["spigot_length"]+p["protrusion_max"]],
                      "y_mouth_depth_is_reference_not_measured": True})
    shape["design_checks"] = design_checks
    if release.revision >= 4:
        wall = audit_thin_shell(meshes["body"], OUT, p)
        old_path = ROOT / "output" / release.previous_package / "stl" / f"{release.previous_stem}-body-clean.stl"
        old_mesh, old_solid = read(old_path)
        socket_zone = mf.Manifold.cube([100, 100, 25.99]).translate([-50, -50, 0])
        old_socket, new_socket = old_solid ^ socket_zone, body ^ socket_zone
        socket_delta = abs((old_socket-new_socket).volume()) + abs((new_socket-old_socket).volume())
        design_checks.update({"thin_wall_final_stl": wall["pass"],
                              "fan_socket_geometry_preserved": socket_delta < 1e-4,
                              "body_solid_volume_reduced": meshes["body"].volume < old_mesh.volume})
        shape.update({"thin_wall_audit": wall, "fan_socket_symmetric_difference_mm3": socket_delta,
                      "old_solid_volume_mm3": float(old_mesh.volume), "new_solid_volume_mm3": float(meshes["body"].volume),
                      "solid_volume_reduction_percent": float(100*(1-meshes["body"].volume/old_mesh.volume)),
                      "volume_is_not_sliced_filament_or_time": True})
    if release.revision >= 5:
        curve = json.loads((OUT / "verification/curve-smoothness.json").read_text())
        design_checks.update({"independent_curve_audit": curve["pass"],
                              "curve_audit_matches_samples": curve["cases"][-1]["source_samples_sha256"] == sha(OUT / "verification/profile-samples.json"),
                              "thin_wall_2_thread_root_2_4": p["thin_wall_radial_nominal"] == 2 and p["thread_root_wall"] == 2.4,
                              "slicer_height_margin_2": p["slicer_height_limit"]-p["body_height"] >= 2})
        shape["curve_audit"] = {k: v for k, v in curve.items() if k != "joins"}
    shape["design_checks"] = {key: bool(value) for key, value in design_checks.items()}
    shape["pass"] = all(shape["design_checks"].values())
    dump(OUT / "verification/profile-comparison.json", shape)
    result = {"status": "PASS_DIGITAL_GEOMETRY_NOT_SLICED" if all(r["pass"] for r in topology+motions+[bayonet, shape]) else "FAIL",
              "source_sha256": exported["source_sha256"],
              "file_sha256": {r["part_id"]: r["sha256"] for r in exported["files"]},
              "motion": motions, "bayonet_pass": bayonet["pass"], "shape": shape,
              "elapsed_seconds": time.monotonic()-start, "sliced": False, "physical_fit_verified": False,
              "flow_performance_verified": False, "flow_guide_status": p["flow_guide_status"],
              "limitations": ["Finite mesh samples plus analytic phase/radius relations, not manufacturing tolerance proof.",
                              "Nominal socket ID76 requested by user: zero designed clearance, PETG shrinkage fit test required.",
                              "Y junction dimensions are reference-only; mechanical travel is not a ball-safe travel guarantee.",
                              "Clean model has no supports; bayonet roof support and thread no-support must be checked in slicer."]}
    dump(OUT / "verification/summary.json", result)
    print(result["status"], "bayonet", bayonet["pass"], "elapsed", result["elapsed_seconds"], flush=True)
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
