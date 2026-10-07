#!/usr/bin/env python3
"""Ø41 v5 geometry only: actual meshes, full-path samples and continuous turn count.

No slicer/printer/skill mutation. numpy, trimesh, manifold3d required.
Optional v4 STL is read once for an interface comparison, never required later.
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
DEFAULT_OUT = ROOT/"output/fan-tee-narrow-nozzles-v5-20261007"
IDS = ["mother", "nozzle15", "nozzle20", "nozzle25", "nozzle30"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n")


def solid(mesh):
    assert mesh.is_watertight and mesh.is_volume
    result = mf.Manifold(mf.Mesh(np.asarray(mesh.vertices, dtype=np.float32),
                               np.asarray(mesh.faces, dtype=np.uint32)))
    assert result.status() == mf.Error.NoError
    return result


def slab(lo, hi):
    return mf.Manifold.cube([60, 60, hi-lo]).translate([-30, -30, lo])


def vertical_hits(mesh, xy):
    """Exact triangle/vertical-line intersections; no extra ray dependencies."""
    t = mesh.triangles
    e1, e2, q = t[:, 1, :2]-t[:, 0, :2], t[:, 2, :2]-t[:, 0, :2], xy-t[:, 0, :2]
    det = e1[:, 0]*e2[:, 1]-e1[:, 1]*e2[:, 0]
    take = np.abs(det)>1e-10
    u = np.zeros(len(t)); v = np.zeros(len(t))
    u[take] = (q[take, 0]*e2[take, 1]-q[take, 1]*e2[take, 0])/det[take]
    v[take] = (e1[take, 0]*q[take, 1]-e1[take, 1]*q[take, 0])/det[take]
    take &= (u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)
    z = t[take, 0, 2]+u[take]*(t[take, 1, 2]-t[take, 0, 2])+v[take]*(t[take, 2, 2]-t[take, 0, 2])
    z = np.sort(z)
    if len(z)==0:
        return z
    return z[np.r_[True, np.diff(z)>1e-5]]


def profile_interval_probes(mesh, radius, lo, hi):
    result = []
    for angle in range(0, 360, 15):
        hits = vertical_hits(mesh, radius*np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))]))
        assert len(hits)%2 == 0, (radius, angle, hits)
        intervals = [(float(a), float(b)) for a, b in zip(hits[::2], hits[1::2]) if a>lo and b<hi]
        assert intervals, (radius, angle)
        result.append({"angle_deg": angle, "radius_mm": radius, "material_intervals_mm": intervals,
                       "minimum_axial_width_mm": min(b-a for a, b in intervals)})
    return result


def annulus_sections(mesh, stations, inner, outer):
    rows = []
    for z in stations:
        points = trimesh.intersections.mesh_plane(mesh, [0, 0, 1], [0, 0, z]).reshape(-1, 3)
        r = np.linalg.norm(points[:, :2], axis=1)
        ri, ro = inner(z), outer(z)
        small, big = r[r<(ri+ro)/2], r[r>(ri+ro)/2]
        assert len(small)>20 and len(big)>20
        # A regular polygon's apothem is slightly smaller than its radius.
        assert abs(max(small)-ri)<.0001 and abs(max(big)-ro)<.0001, (z, max(small), ri, max(big), ro)
        rows.append({"z_mm": float(z), "inside_d_max_mm": float(max(small)*2),
                     "outside_d_max_mm": float(max(big)*2),
                     "radial_wall_vertex_mm": float(max(big)-max(small))})
    return rows


def turn_count(p):
    # Entire tooth strip, not just its helix centre, must lie beyond all runouts.
    h = .4+(.9+.05)*math.tan(math.radians(p["flank_angle_horizontal"]))
    male = [p["male_z0"]+p["runout_l"]+h, p["male_z1"]-p["runout_l"]-h]
    female = [p["female_z0"]+h+p["axial_clearance"], p["entry_cone_z0"]-h-p["axial_clearance"]]
    low, high = p["core_seated_z"], p["core_extended_z"]
    pitch, anchor = p["pitch"], p["female_z0"]
    def at(z):
        a, b = max(female[0], z+male[0]), min(female[1], z+male[1])
        first, last = math.ceil((a-anchor)/pitch-1e-10), math.floor((b-anchor)/pitch+1e-10)
        return {"core_z_mm": z, "full_profile_helix_centre_interval_mm": [a, b],
                "complete_phase_zero_turns": last-first,
                "counted_full_turn_start_z_mm": [anchor+pitch*k for k in range(first, last)]}
    # Integer count can only change where one moving end crosses a phase-zero
    # helix plane or where max/min switches to a fixed end. Evaluate every open
    # interval and exact breakpoint; this is not a discrete travel-length guess.
    breaks = {low, high}
    for end in male:
        for k in range(-50, 80):
            z = anchor+pitch*k-end
            if low<z<high:
                breaks.add(z)
        for bound in female:
            if low<bound-end<high:
                breaks.add(bound-end)
    breaks = sorted(breaks)
    tests = [at(z) for z in breaks]+[at((a+b)/2) for a, b in zip(breaks, breaks[1:])]
    minimum = min(r["complete_phase_zero_turns"] for r in tests)
    assert p["pitch"] == 4 and high-low>=40 and minimum>=3
    return {"method": "continuous breakpoint proof on fully present tooth strips; conservative common phase-zero full turns",
            "effective_travel_mm": high-low, "travel_turns": (high-low)/pitch,
            "mother_cut_length_mm": p["female_z1"]-p["female_z0"],
            "male_full_profile_centre_interval_local_mm": male,
            "mother_full_profile_centre_interval_mm": female,
            "minimum_complete_engaged_turns": minimum,
            "complete_turns_are_retained_in_addition_to_travel": True,
            "breakpoint_samples": tests}


def motion(out, p, meshes, solids):
    mother, witness = solids["mother"], solids["nozzle30"]
    common = slab(0, p["core_mount_l"])
    lower = witness ^ common
    equality = {}
    for name in IDS[1:]:
        target = solids[name] ^ common
        difference = (target-lower).volume()+(lower-target).volume()
        assert abs(difference)<1e-5
        # Above Z46 every nozzle is inside the smooth Ø40 envelope, which
        # clears even the most restrictive Ø40.6 female minor at any azimuth.
        v = meshes[name].vertices
        radius = np.linalg.norm(v[v[:, 2]>=p["core_mount_l"]-1e-5, :2], axis=1)
        assert max(radius)<=20.00001
        equality[name] = {"mount_segment_symmetric_difference_mm3": difference,
                          "upper_segment_max_radius_mm": float(max(radius))}
    rows = []
    seat, handoff, pitch = p["core_seated_z"], p["tee_z0"], p["pitch"]
    angle_at_handoff = 360*(handoff-seat)/pitch
    for z in np.arange(p["tee_z1"]+10, handoff-.01, -.5):
        vol = (mother ^ witness.rotate([0, 0, angle_at_handoff]).translate([0, 0, float(z)])).volume()
        rows.append({"mode": "straight_approach", "core_z_mm": float(z), "angle_deg": angle_at_handoff,
                     "intersection_mm3": vol})
    dz_half_facet = pitch/p["steps_per_turn"]/2
    poses = sorted(set(np.arange(handoff, seat-.001, -.125)) |
                   set(np.arange(handoff-dz_half_facet, seat, -.125)), reverse=True)
    for i, z in enumerate(poses):
        angle = 360*(float(z)-seat)/pitch
        vol = (mother ^ witness.rotate([0, 0, angle]).translate([0, 0, float(z)])).volume()
        rows.append({"mode": "screw", "core_z_mm": float(z), "angle_deg": angle, "intersection_mm3": vol})
        if i%250 == 0:
            print("motion", i, "/", len(poses), "z", z, "intersection", vol, flush=True)
    controls = {}
    independent = {}
    for name in IDS[1:]:
        controls[name] = []; independent[name] = []
        for offset in [0, .5, 4, 19.75, 20, 36, 39.5, 40]:
            z, angle = seat+offset, 360*offset/pitch
            volume = (mother ^ solids[name].rotate([0, 0, angle]).translate([0, 0, z])).volume()
            wrong = (mother ^ solids[name].rotate([0, 0, angle+180]).translate([0, 0, z])).volume()
            independent[name].append({"offset_mm": offset, "intersection_mm3": volume})
            controls[name].append({"offset_mm": offset, "wrong_phase_180_intersection_mm3": wrong})
            assert abs(volume)<1e-5 and wrong>1, (name, offset, volume, wrong)
    peak = max(abs(r["intersection_mm3"]) for r in rows)
    assert peak<1e-5, peak
    report = {"status": "PASS_DIGITAL_SAMPLED_PATH_WITH_ANALYTIC_HELIX_ENVELOPE",
              "phase": "angle_deg = 360*(core_z_mm-34)/4; +Z air; insert from +Z towards -Z",
              "approach_z_interval_mm": [p["tee_z1"]+10, handoff],
              "screw_z_interval_mm": [handoff, seat], "normal_work_z_interval_mm": [seat, seat+40],
              "entrance_min_id_mm": p["tee_id"]-2*p["tip_radial_chamfer"],
              "male_major_mm": p["male_major"], "sample_count": len(rows),
              "max_abs_intersection_mm3": peak,
              "exit_path": "exact reverse of verified poses, same static intersections; no dynamic friction assertion",
              "shared_geometry_proof": equality,
              "all_core_independent_spot_checks": independent,
              "wrong_phase_controls": controls, "samples": rows,
              "analytic_complement": "Common anchored P4 helix and radially/axially expanded mating profile are invariant under pitch-linked continuous motion. Root/runout ends only remove male material. Whole upper bodies fit the minor bore at every azimuth. Polygonal meshes also sampled at aligned and half-facet offsets.",
              "limits": "Finite mesh sampling is not an exhaustive floating-point sweep; no physical shrinkage, friction, torque or first-article test.",
              "physical_fit_verified": False}
    dump(out/"verification/motion.json", report)
    return {k: v for k, v in report.items() if k != "samples"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--baseline-stl", type=Path)
    a = ap.parse_args(); out = a.out.resolve()
    p = json.loads((out/"verification/parameters.json").read_text())
    export = json.loads((out/"verification/export.json").read_text())
    for name, digest in export["source_sha256"].items():
        assert sha(out/"source"/name) == digest == sha(ROOT/"cad"/name)
    for row in export["files"]:
        assert sha(out/row["file"]) == row["sha256"]
    paths = {name: out/f"stl/fan-tee-v5-{name}-clean.stl" for name in IDS}
    meshes = {k: trimesh.load_mesh(v) for k, v in paths.items()}
    solids = {k: solid(v) for k, v in meshes.items()}
    measurements, down_report = {}, {}
    for name, mesh in meshes.items():
        assert len(solids[name].decompose()) == 1
        expected = [[-25, -25, -18.5], [25, 25, 128]] if name=="mother" else [[-20.9, -20.9, 0], [20.9, 20.9, 106]]
        assert np.allclose(mesh.bounds, expected, atol=1e-5)
        c, n = mesh.triangles_center, mesh.face_normals
        angles = np.degrees(np.arctan2(np.linalg.norm(n[:, :2], axis=1), np.abs(n[:, 2])))
        down = (n[:, 2]<-1e-6)&(c[:, 2]>mesh.bounds[0, 2]+1e-4)
        bad = down&(angles<45)
        lug_region = (np.abs(c[:, 0])>17.69)&(np.abs(c[:, 0])<21.2)&(np.abs(c[:, 1])<=3.01)&(c[:, 2]>=-10.501)&(c[:, 2]<=-4.499) if name=="mother" else np.zeros(len(c), dtype=bool)
        assert not np.any(bad&~lug_region)
        thread = down&(c[:, 2]>37)&(c[:, 2]<103) if name=="mother" else down&(c[:, 2]>3)&(c[:, 2]<29)
        assert sum(thread)>1000 and min(angles[thread])>49
        down_report[name] = {"angle_datum": "degrees above horizontal build plate; +Z up",
                            "thread_min_deg": float(min(angles[thread])), "thread_triangle_count": int(sum(thread)),
                            "all_nonbed_down_min_deg": float(min(angles[down])),
                            "below_45_nonbed_count": int(sum(bad)), "below_45_outside_lugs": int(sum(bad&~lug_region)),
                            "low_angle_centroid_bounds_mm": [c[bad].min(axis=0).tolist(), c[bad].max(axis=0).tolist()] if any(bad) else None,
                            "actual_slice_checked": False}
        measurements[name] = {"sha256": sha(paths[name]), "triangles": len(mesh.faces), "size_mm": mesh.extents.tolist(),
                              "bounds_mm": mesh.bounds.tolist(), "volume_mm3": float(mesh.volume), "connected_solids": 1,
                              "print_translate_z_mm": -float(mesh.bounds[0, 2])}
    dump(out/"verification/downward-surfaces.json", down_report)
    print("All five closed/single solid; actual thread flanks >49deg; only mother lugs <45deg", flush=True)
    mother = meshes["mother"]
    roots = (solid(trimesh.load_mesh(out/"review/review-lugs.stl")) ^ solid(trimesh.load_mesh(out/"review/review-shell.stl"))).decompose()
    assert len(roots)==2 and min(r.volume() for r in roots)>35
    lugs = []
    for sign in [-1, 1]:
        selected = mother.vertices[np.isclose(mother.vertices[:, 0], sign*17.7, atol=1e-5)&(mother.vertices[:, 2]<0)]
        assert len(selected)>50
        bounds = np.asarray([selected.min(axis=0), selected.max(axis=0)])
        assert np.allclose(bounds[:, 1:], [[-3, -10.5], [3, -4.5]], atol=1e-5)
        lugs.append({"side": sign, "bounds_mm": bounds.tolist(), "centre_z_mm": -7.5,
                     "diameter_mm": 6, "inward_projection_mm": 3.4, "nominal_embed_mm": 1.2})
    tee = annulus_sections(mother, [103.5, 108, 115, 126, 127.5],
        lambda z: 22 if z<=127.2 else 22-(z-127.2)/.8*.35,
        lambda z: 25 if z<=127.2 else 25-(z-127.2)/.8*.35)
    female_web = profile_interval_probes(mother, 20.3001, 40, 97)
    male_crest = profile_interval_probes(meshes["nozzle15"], 20.89, 7, 25)
    assert min(x["minimum_axial_width_mm"] for x in female_web)>.76
    assert min(x["minimum_axial_width_mm"] for x in male_crest)>.79
    for name in IDS[1:]:
        aperture = int(name[6:]); m = meshes[name]
        ri = lambda z: 18 if z<=46 else (aperture/2 if z>=90 else 18+(aperture/2-18)*(z-46)/44)
        measurements[name]["annular_sections"] = annulus_sections(m, [1, 31, 45, 47, 60, 80, 89, 92, 105.9], ri, lambda z: ri(z)+2)
        # Centre-axis no intersections plus a minimum clear cylinder prove an
        # unobstructed through-bore digitally, not aerodynamic performance.
        assert len(vertical_hits(m, np.array([0.0, 0.0])))==0
        probe = mf.Manifold.cylinder(106.2, aperture/2-.02, aperture/2-.02, 96).translate([0, 0, -.1])
        assert abs((solids[name]^probe).volume())<1e-5
        slope = (18-aperture/2)/44
        measurements[name].update({"outlet_id_mm": aperture, "inlet_id_mm": 36, "radial_wall_mm": 2,
                                  "cone_normal_wall_analytic_mm": 2/math.sqrt(1+slope*slope),
                                  "minimum_clear_through_cylinder_mm": aperture-.04,
                                  "exit_protrusion_work_range_mm": [12, 52]})
    baseline = json.loads((out/"verification/v4-baseline.json").read_text()) if (out/"verification/v4-baseline.json").exists() else None
    comparison = {"current_pitch": p["pitch"], "pitch_increase_forbidden": True}
    if baseline:
        old = baseline["parameters"]
        invariants = ["fan_back_z", "fan_od", "fan_radial_clearance", "socket_id", "socket_od", "body_od", "fan_face_extra", "air_transition_end", "lug_d", "lug_radial_h", "lug_embed", "lug_z", "tee_od", "tee_id", "tip_l", "tip_radial_chamfer", "pitch", "thread_h", "male_major", "female_minor", "female_major", "radial_clearance", "axial_clearance"]
        assert all(p[k]==old[k] for k in invariants)
        comparison.update({"unchanged_interface_and_thread_envelope_keys": invariants,
                           "changed_common_parameters": {k: {"v4": old[k], "v5": v} for k, v in p.items() if k in old and v!=old[k]},
                           "tee_insert_length_v4_v5_mm": [old["tee_z1"]-old["tee_z0"], p["tee_l"]],
                           "mother_thread_cut_length_v4_v5_mm": [old["female_z1"]-old["female_z0"], p["female_z1"]-p["female_z0"]]})
        if a.baseline_stl:
            assert sha(a.baseline_stl)==baseline["mother_stl_sha256"]
            old_solid = solid(trimesh.load_mesh(a.baseline_stl))
            pairs = [("fan_interface_below_thread", old_solid^slab(-19, 37.5), solids["mother"]^slab(-19, 37.5)),
                     ("tee_interface_translated_48mm", (old_solid^slab(55, 81)).translate([0, 0, 48]), solids["mother"]^slab(103, 129))]
            comparison["actual_mesh_interface_difference"] = []
            for label, before, after in pairs:
                add, remove = (after-before).volume(), (before-after).volume()
                assert abs(add)+abs(remove)<.01, (label, add, remove)
                comparison["actual_mesh_interface_difference"].append({"region": label, "added_mm3": add, "removed_mm3": remove})
    dump(out/"verification/parameter-diff.json", comparison)
    turns = turn_count(p); dump(out/"verification/engagement.json", turns)
    print("Continuous40mm turn-count PASS, retained complete turns", turns["minimum_complete_engaged_turns"], flush=True)
    path = motion(out, p, meshes, solids)
    # Deliberately do not imply old 45mm nozzles reach through this long body.
    legacy = {"functional_compatibility": "NOT_RELEASED_USE_NEW_V5_MATCHED_SET",
              "reason": "Old core length45 exits at Z79..119 at these working datums, below mother outlet128. New profiles also differ; no old-core interchange claim.",
              "old_core_included_for_print": False}
    geometry = {"parts": measurements, "lugs": lugs, "lug_root_intersection_volumes_mm3": [r.volume() for r in roots],
                "tee_sections": tee, "tee_length_mm": 25, "tee_full_od_length_mm": 24.2,
                "female_root_wall_nominal_mm": 3.85, "female_tip_web_nominal_mm": p["female_tip_web"],
                "female_tip_web_actual_probes": female_web, "male_crest_actual_probes": male_crest,
                "male_nominal_radial_engagement_mm": .6, "female_clearances_radial_axial_each_mm": [.25, .20],
                "fan_unknowns": ["fan inner wall", "slot floor depth", "as-printed fit"],
                "Y_unknowns": ["junction axial datum", "ball swept path", "allowable maximum52mm nozzle protrusion"],
                "physical_fit_or_strength_verified": False}
    dump(out/"verification/geometry.json", geometry)
    report = {"status": "DIGITAL_GEOMETRY_PASS_SLICE_AND_PHYSICAL_PENDING", "geometry": geometry,
              "downward_surfaces": down_report, "motion": path, "legacy_core": legacy,
              "engagement_min_full_turns": turns["minimum_complete_engaged_turns"], "effective_travel_mm": 40,
              "pitch_mm": 4, "slicer_verified_here": False, "physical_fit_verified": False,
              "dependencies": {n: importlib.metadata.version(n) for n in ["numpy", "trimesh", "manifold3d"]}}
    dump(out/"verification/geometry-acceptance.json", report)
    print(report["status"], flush=True)


if __name__ == "__main__":
    main()
