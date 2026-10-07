#!/usr/bin/env python3
"""Geometry-only v4 acceptance, paired with unchanged core witnesses.

No printer/slicer access. Reads current output only; optional --baseline-stl
adds a one-time mesh difference audit without creating a runtime dependency.
Requires numpy, trimesh and manifold3d in the invoking Python environment.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT/"output/fan-tee-direct-print-v4-20261007"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n")


def solid(mesh: trimesh.Trimesh) -> mf.Manifold:
    result = mf.Manifold(mf.Mesh(np.asarray(mesh.vertices, dtype=np.float32),
                                np.asarray(mesh.faces, dtype=np.uint32)))
    assert result.status() == mf.Error.NoError
    assert mesh.is_watertight and mesh.is_volume
    return result


def vertical_hits(mesh: trimesh.Trimesh, xy: np.ndarray) -> np.ndarray:
    """All line/triangle intersections, without ray acceleration dependencies."""
    t = mesh.triangles
    e1, e2, q = t[:, 1, :2]-t[:, 0, :2], t[:, 2, :2]-t[:, 0, :2], xy-t[:, 0, :2]
    det = e1[:, 0]*e2[:, 1]-e1[:, 1]*e2[:, 0]
    usable = np.abs(det) > 1e-10
    u = np.zeros(len(t)); v = np.zeros(len(t))
    u[usable] = (q[usable, 0]*e2[usable, 1]-q[usable, 1]*e2[usable, 0])/det[usable]
    v[usable] = (e1[usable, 0]*q[usable, 1]-e1[usable, 1]*q[usable, 0])/det[usable]
    take = usable & (u >= -1e-8) & (v >= -1e-8) & (u+v <= 1+1e-8)
    z = t[take, 0, 2]+u[take]*(t[take, 1, 2]-t[take, 0, 2])+v[take]*(t[take, 2, 2]-t[take, 0, 2])
    z = np.sort(z)
    return z[np.r_[True, np.diff(z)>1e-5]]


def verify_motion(out: Path, female: mf.Manifold, p: dict, baseline: dict) -> dict:
    results = {}
    witnesses = [
        ("baseline-anchored-core36", 0.0),
        ("printed-core36", baseline["historical_printed_core"]["phase_at_v4_seated_z_deg"]),
    ]
    assert sha(out/"verification/reference/printed-core36.stl") == baseline["historical_printed_core"]["sha256"]
    for name, phase in witnesses:
        path = out/f"verification/reference/{name}.stl"
        male = solid(trimesh.load_mesh(path))
        rows = []
        seat = p["core_seated_z"]
        handoff = p["tee_z0"]
        handoff_angle = phase+360*(handoff-seat)/p["pitch"]
        for z in np.arange(90, handoff-0.01, -.5):
            volume = (female ^ male.rotate([0, 0, handoff_angle]).translate([0, 0, float(z)])).volume()
            rows.append({"mode": "straight_approach", "core_z_mm": float(z),
                         "angle_deg": handoff_angle, "intersection_mm3": volume})
        # 0.125 mm pitch-linked steps, plus a half-facet offset (0.015625 mm).
        dz_half_facet = p["pitch"]/p["steps_per_turn"]/2
        poses = sorted(set(np.arange(handoff, seat-.001, -.125)) |
                       set(np.arange(handoff-dz_half_facet, seat, -.125)), reverse=True)
        for z in poses:
            angle = phase+360*(z-seat)/p["pitch"]
            volume = (female ^ male.rotate([0, 0, float(angle)]).translate([0, 0, float(z)])).volume()
            rows.append({"mode": "screw", "core_z_mm": float(z),
                         "angle_deg": float(angle), "intersection_mm3": volume})
        peak = max(r["intersection_mm3"] for r in rows)
        controls = {}
        for extension in [0, 4, 8]:
            z = seat+extension
            angle = phase+360*extension/p["pitch"]+180
            controls[str(extension)] = (female ^ male.rotate([0, 0, angle]).translate([0, 0, z])).volume()
        assert peak <= 1e-5, (name, peak)
        assert min(controls.values()) > 1, (name, controls)
        report = {
            "status": "PASS_SAMPLED_DIGITAL_PATH", "file": str(path.relative_to(out)),
            "sha256": sha(path), "sample_count": len(rows),
            "seated_z_mm": seat, "phase_at_seated_z_deg": phase,
            "rotation_relation": f"angle = {phase} + 360*(core_z-{seat})/{p['pitch']}",
            "max_intersection_mm3": peak,
            "wrong_phase_180deg_intersection_by_extension_mm3": controls,
            "samples": rows, "physical_fit_verified": False,
            "limits": "Finite solid-intersection sampling + analytic fixed-lead relation. No deformation, shrinkage, torque, wear or physical identity proof.",
        }
        dump(out/f"verification/motion-{name}.json", report)
        results[name] = {k: v for k, v in report.items() if k != "samples"}
        print(name, len(rows), "poses; intersection", peak, "wrong-phase", controls, flush=True)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--baseline-stl", type=Path)
    args = ap.parse_args()
    out = args.out.resolve()
    p = json.loads((out/"verification/parameters.json").read_text())
    baseline = json.loads((out/"verification/baseline.json").read_text())
    exports = json.loads((out/"verification/export.json").read_text())
    for name, digest in exports["source_sha256"].items():
        assert sha(out/"source"/name) == digest == sha(ROOT/"cad"/name)
    for row in exports["files"]:
        assert sha(out/row["file"]) == row["sha256"]
    connector_path = out/"stl/fan-tee-v4-connector-clean.stl"
    mesh = trimesh.load_mesh(connector_path)
    female = solid(mesh)
    assert len(female.decompose()) == 1
    assert np.allclose(mesh.bounds, [[-25, -25, -18.5], [25, 25, 80]], atol=1e-5)

    # Validate both requested deltas and unchanged interface invariants.
    changes = {key: {"before": value, "after": p[key], "delta": p[key]-value}
               for key, value in baseline["parameters"].items() if abs(p[key]-value)>1e-7}
    expected = {"tee_measured_id", "tee_radial_clearance", "tee_od", "tee_id", "lug_radial_h", "lug_z"}
    assert set(changes) == expected, changes
    assert abs(changes["lug_z"]["delta"]+.5)<1e-7
    assert abs(changes["lug_radial_h"]["delta"]-1)<1e-7
    assert p["lug_d"] == 6 and p["lug_embed"] == 1.2
    assert p["tee_od"] == 50 and p["tee_id"] == 44 and p["wall"] == 3
    parameter_diff = {"changed_common_parameters": changes,
                      "unchanged_common_parameters": sorted(set(baseline["parameters"])-expected),
                      "additional_design_change": "Female groove upper roof relief only; original male and lower flank unchanged",
                      "old_groove_profile_rz": baseline["old_groove_profile_rz"],
                      "new_groove_profile_rz": p["female_profile"]}
    dump(out/"verification/parameter-diff.json", parameter_diff)

    # The new groove is an envelope enlargement, not a changed male. Audit
    # containment algebraically over the full radius (separate from mesh test).
    r = np.linspace(p["groove_r0"], p["groove_r1"], 1001)
    old_slope = (p["root_w"]-p["crest_w"])/2/(p["thread_h"]+p["root_embed"])
    old_upper = p["groove_top_outer"]+(p["groove_r1"]-r)*old_slope
    new_upper = p["groove_top_outer"]+(p["groove_r1"]-r)*math.tan(math.radians(p["roof_angle_horizontal"]))
    assert np.min(new_upper-old_upper)>-1e-9
    radius_minor = p["female_minor"]/2
    old_width_minor = 2*(p["root_w"]/2+p["axial_clearance"]-(radius_minor-p["groove_r0"])*old_slope)
    old_tip_web = p["pitch"]-old_width_minor
    new_tip_web = p["pitch"] - (
        p["groove_top_outer"]+(p["groove_r1"]-radius_minor)*math.tan(math.radians(p["roof_angle_horizontal"]))
        +p["root_w"]/2+p["axial_clearance"]-(radius_minor-p["groove_r0"])*old_slope)
    assert new_tip_web >= .70

    lug_solid = solid(trimesh.load_mesh(out/"review/lugs.stl"))
    shell = solid(trimesh.load_mesh(out/"review/shell.stl"))
    roots = (lug_solid ^ shell).decompose()
    assert len(roots) == 2 and min(x.volume() for x in roots)>20
    lug_measurements = []
    for sign in [-1, 1]:
        # Exposed circular disc face is selected from FINAL connector STL,
        # not merely its input cylinder. Both load-bearing roots also checked.
        face_x = sign*(p["socket_id"]/2-p["lug_radial_h"])
        v = mesh.vertices
        selected = v[np.isclose(v[:, 0], face_x, atol=1e-5) & (v[:, 2]<0)]
        assert len(selected)>50
        bounds = np.array([selected.min(axis=0), selected.max(axis=0)])
        centre_z = float(np.mean(bounds[:, 2]))
        assert abs(centre_z+7.5)<1e-5
        assert np.allclose(bounds[1, 1:]-bounds[0, 1:], [6, 6], atol=1e-5)
        lug_measurements.append({"side": sign, "exposed_face_bounds_mm": bounds.tolist(),
                                 "centre_z_mm": centre_z, "disc_diameter_mm": float(np.ptp(selected[:, 2])),
                                 "radial_projection_mm": p["socket_id"]/2-abs(float(selected[0, 0])),
                                 "print_lowest_z_mm": float(bounds[0, 2]-p["fan_back_z"])})

    # Section-derived insertion OD/ID and uninterrupted 3 mm annular wall.
    tee_sections = []
    for z in [55.5, 60, 75, 79, 79.5]:
        seg = trimesh.intersections.mesh_plane(mesh, [0, 0, 1], [0, 0, z])
        points = seg.reshape(-1, 3)
        radial = np.linalg.norm(points[:, :2], axis=1)
        outer, inner = radial[radial>23], radial[radial<23]
        expected_outer = 25 if z<=79.2 else 25-(z-79.2)/.8*.35
        expected_inner = expected_outer-3
        assert abs(max(outer)-expected_outer)<1e-5
        assert abs(max(inner)-expected_inner)<1e-5
        assert max(outer)-max(inner)>2.9999
        tee_sections.append({"z_mm": z, "outer_d_max_mm": float(max(outer)*2),
                             "inner_d_max_mm": float(max(inner)*2),
                             "radial_wall_at_vertices_mm": float(max(outer)-max(inner)),
                             "faceted_outer_d_min_mm": float(min(outer)*2)})

    # Thread/web section witness independent of input profile numbers.
    webs = []
    for angle in [0, 15, 47, 90, 137, 180, 225, 270, 315]:
        xy = 20.3001*np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
        hits = vertical_hits(mesh, xy)
        assert len(hits)%2 == 0, (angle, hits)
        intervals = [(float(a), float(b)) for a, b in zip(hits[::2], hits[1::2]) if a>39 and b<51.5]
        assert intervals
        widths = [b-a for a, b in intervals]
        assert min(widths)>.70
        webs.append({"angle_deg": angle, "probe_radius_mm": 20.3001,
                     "solid_z_intervals_mm": intervals, "minimum_width_mm": min(widths)})

    centres, normals = mesh.triangles_center, mesh.face_normals
    alpha = np.degrees(np.arctan2(np.linalg.norm(normals[:, :2], axis=1), np.abs(normals[:, 2])))
    down = normals[:, 2]<-1e-6
    thread = down & (centres[:, 2]>35) & (centres[:, 2]<55)
    assert sum(thread)>1000 and min(alpha[thread])>48
    unsupported = down & (alpha<45) & (centres[:, 2]>p["fan_back_z"]+1e-4)
    local = (np.abs(centres[:, 0])>17.69) & (np.abs(centres[:, 0])<21.2) & (np.abs(centres[:, 1])<=3.01) & (centres[:, 2]>=-10.501) & (centres[:, 2]<=-4.499)
    unexpected = unsupported & ~local
    assert not np.any(unexpected), centres[unexpected]
    down_report = {
        "angle_datum": "degrees to horizontal build plate; Z-up print",
        "all_thread_downward_triangles": int(sum(thread)),
        "thread_min_deg": float(min(alpha[thread])),
        "thread_median_deg": float(np.median(alpha[thread])),
        "thread_max_deg": float(max(alpha[thread])),
        "below_45_excluding_bed_triangles": int(sum(unsupported)),
        "below_45_excluding_bed_centroid_bounds_mm": [centres[unsupported].min(axis=0).tolist(), centres[unsupported].max(axis=0).tolist()],
        "below_45_outside_lugs_triangles": int(sum(unexpected)),
        "support_policy_geometry_screen": "PASS_ONLY_LUGS_BELOW_45_EXCLUDING_BUILD_BASE",
        "actual_slice_verified": False,
        "limits": "Mesh-angle screen only; check both Support and Support interface toolpaths/contact areas in actual slice.",
    }
    dump(out/"verification/downward-surfaces.json", down_report)
    geometry = {
        "connected_solids": len(female.decompose()), "bounds_mm": mesh.bounds.tolist(),
        "size_mm": mesh.extents.tolist(), "volume_mm3": float(mesh.volume),
        "lug_final_mesh_measurements": lug_measurements,
        "lug_root_intersection_volumes_mm3": [x.volume() for x in roots],
        "root_embed_nominal_mm": p["lug_embed"],
        "tee_sections": tee_sections,
        "tee_full_diameter_length_mm": p["tee_z1"]-p["tip_l"]-p["tee_z0"],
        "tee_total_insert_length_mm": p["tee_z1"]-p["tee_z0"],
        "female_groove_root_wall_nominal_mm": (p["body_od"]-p["female_major"])/2,
        "female_radial_tooth_engagement_nominal_mm": (p["male_major"]-p["female_minor"])/2,
        "female_tip_web_old_mm": old_tip_web, "female_tip_web_new_mm": new_tip_web,
        "female_tip_web_mesh_probes": webs,
        "female_roof_relief_increases_clearance_not_male_height": True,
        "female_entry_min_tip_id_mm": p["tee_id"]-2*p["tip_radial_chamfer"],
        "entry_cone_d_at_thread_upper_end_mm": p["female_minor"]+(p["tee_id"]-p["female_minor"])*(p["female_z1"]-p["entry_cone_z0"])/(p["tee_z0"]-p["entry_cone_z0"]),
        "insertion_through_all_threaded_depth": "see both motion reports; not just entry diameter",
        "fan_inner_wall_and_slot_depth_known": False,
        "lug_capture_beyond_fan_outer_surface_nominal_mm": p["lug_radial_h"]-p["fan_radial_clearance"],
        "physical_load_or_fit_verified": False,
    }
    dump(out/"verification/geometry.json", geometry)

    if args.baseline_stl:
        assert sha(args.baseline_stl) == baseline["connector_stl_sha256"]
        old = solid(trimesh.load_mesh(args.baseline_stl))
        added, removed = female-old, old-female
        slabs = []
        for name, lo, hi in [("lugs", -11, -3), ("unchanged_inlet", -3, 38),
                             ("thread_roof", 38, 51), ("thread_entry_and_tee", 51, 81)]:
            box = mf.Manifold.cube([60, 60, hi-lo]).translate([-30, -30, lo])
            slabs.append({"region": name, "z_range_mm": [lo, hi],
                          "added_mm3": (added ^ box).volume(), "removed_mm3": (removed ^ box).volume()})
        assert abs(slabs[1]["added_mm3"])+abs(slabs[1]["removed_mm3"])<.005
        assert abs(slabs[2]["added_mm3"])<.005
        dump(out/"verification/baseline-mesh-difference.json", {
            "old_sha256": sha(args.baseline_stl), "new_sha256": sha(connector_path),
            "old_file_is_runtime_dependency": False, "slabs": slabs,
            "added_volume_mm3": added.volume(), "removed_volume_mm3": removed.volume(),
        })

    motion = verify_motion(out, female, p, baseline)
    result = {
        "status": "DIGITAL_GEOMETRY_AND_SAMPLED_COMPATIBILITY_PASS_SLICE_AND_PHYSICAL_PENDING",
        "stl": "stl/fan-tee-v4-connector-clean.stl", "sha256": sha(connector_path),
        "geometry": geometry, "downward_surfaces": down_report, "compatibility": motion,
        "parameter_diff": parameter_diff,
        "dependency_versions": {n: importlib.metadata.version(n) for n in ["numpy", "trimesh", "manifold3d"]},
        "excluded": ["printer control", "slicing", "old version deletion", "skill edits", "new core print"],
        "slice_verified": False, "physical_fit_verified": False,
    }
    dump(out/"verification/geometry-acceptance.json", result)
    print(result["status"], "STL", result["sha256"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
