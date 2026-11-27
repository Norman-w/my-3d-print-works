#!/usr/bin/env python3
"""Reproduce two initial-snapshot nut-path counterexamples; never operate a printer.

This is a bounded manufacturing review, not a slicing or physical acceptance tool.
Uses only the standard library and the already-installed OpenSCAD executable.
Frozen source hashes are checked before every run; current CAD is never changed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "output/review-slice"
SNAPSHOT = REVIEW / "manufacturing-snapshot"
PROFILE_ROOT = Path("/Applications/BambuStudio.app/Contents/Resources/profiles/BBL")
OPENSCAD = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def triangles(path: Path) -> list:
    data = path.read_bytes()
    if len(data) >= 84:
        count = struct.unpack_from("<I", data, 80)[0]
        if len(data) == 84 + 50 * count:
            return [tuple(tuple(row[j:j+3]) for j in (3, 6, 9))
                    for row in (struct.unpack_from("<12f", data, 84+50*i)
                                for i in range(count))]
    points = [tuple(map(float, match)) for match in
              re.findall(r"vertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)",
                         data.decode())]
    if len(points) % 3:
        raise ValueError(f"Incomplete STL triangles: {path}")
    return [tuple(points[i:i+3]) for i in range(0, len(points), 3)]


def mesh_facts(path: Path) -> dict:
    faces = triangles(path)
    if not faces:
        raise ValueError(f"Empty STL: {path}")
    points = [point for face in faces for point in face]
    lo = [min(point[i] for point in points) for i in range(3)]
    hi = [max(point[i] for point in points) for i in range(3)]
    signed_volume = 0.0
    edges = Counter()
    orientation = Counter()
    for a, b, c in faces:
        signed_volume += (a[0]*(b[1]*c[2]-b[2]*c[1]) +
                          a[1]*(b[2]*c[0]-b[0]*c[2]) +
                          a[2]*(b[0]*c[1]-b[1]*c[0])) / 6
        keys = [tuple(round(v, 5) for v in p) for p in (a,b,c)]
        for start,end in zip(keys, keys[1:]+keys[:1]):
            edge = tuple(sorted((start,end)))
            edges[edge] += 1
            orientation[edge] += 1 if start <= end else -1
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path),
            "triangles": len(faces), "volume_mm3": abs(signed_volume),
            "bounds_min_mm": lo, "bounds_max_mm": hi,
            "size_mm": [b-a for a,b in zip(lo,hi)],
            "watertight_by_rounded_edges": all(v == 2 for v in edges.values())
                and not any(orientation.values())}


def z_intersections(path: Path, x: float, y: float) -> list[float]:
    """Read an upright Z ray from actual exported triangles, not SCAD bounds."""
    hits = set()
    for a,b,c in triangles(path):
        ux,uy,vx,vy = b[0]-a[0],b[1]-a[1],c[0]-a[0],c[1]-a[1]
        determinant = ux*vy-uy*vx
        if abs(determinant) < 1e-10:
            continue
        dx,dy = x-a[0],y-a[1]
        s,t = (dx*vy-dy*vx)/determinant,(ux*dy-uy*dx)/determinant
        if s >= -1e-7 and t >= -1e-7 and s+t <= 1+1e-7:
            hits.add(round(a[2]+s*(b[2]-a[2])+t*(c[2]-a[2]),5))
    return sorted(hits)


def export(name: str, source: Path, definitions: dict, expected_empty: bool) -> dict:
    output = REVIEW / (name + ".stl")
    output.unlink(missing_ok=True)
    command = [OPENSCAD, "--hardwarnings", "--backend", "Manifold",
               "--export-format", "binstl", "-o", str(output)]
    for key,value in definitions.items():
        command += ["-D", f"{key}={json.dumps(value)}"]
    command.append(str(source))
    run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    log = run.stdout + run.stderr
    (REVIEW / (name + ".log")).write_text(log)
    empty = "Current top level object is empty" in log and not output.exists()
    if run.returncode and not empty:
        raise RuntimeError(f"{name}: {log}")
    result = {"name":name, "command":command, "definitions":definitions,
              "expected_empty":expected_empty, "actual_empty":empty,
              "matches_expectation":empty == expected_empty}
    if not empty:
        result["mesh"] = mesh_facts(output)
    return result


def merged_profile(kind: str, name: str) -> tuple[dict, list]:
    path = PROFILE_ROOT / kind / (name + ".json")
    current = json.loads(path.read_text())
    if current.get("inherits"):
        merged, chain = merged_profile(kind,current["inherits"])
    else:
        merged, chain = {}, []
    merged.update(current)
    return merged, chain + [{"path":str(path),"sha256":sha256(path)}]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-csg",action="store_true",
                        help="Read existing report only; does not refresh its evidence")
    args = parser.parse_args()
    report_path = ROOT / "output/analysis/manufacturing-review.json"
    if args.skip_csg:
        print(report_path.read_text())
        return
    manifest_path = SNAPSHOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for item in manifest["sources"]:
        path = ROOT / item["snapshot_path"]
        if sha256(path) != item["sha256"]:
            raise RuntimeError(f"Frozen source was modified: {path}")
    probes = [
        ("manufacturing-feeder-nut-entry", "feeder", {"review_nut_z":-40},True),
        ("manufacturing-feeder-nut-mid", "feeder", {"review_nut_z":-15},False),
        ("manufacturing-feeder-nut-seated", "feeder", {"review_nut_z":-1},True),
        ("manufacturing-feeder-nut-without-brace", "feeder",
         {"review_nut_z":-15,"review_with_spring_interface":False},True),
        ("manufacturing-spin-nut-entry", "spin", {"review_nut_y":20},True),
        ("manufacturing-spin-nut-mid", "spin", {"review_nut_y":14.5},False),
        ("manufacturing-spin-nut-seated", "spin", {"review_nut_y":0},True),
        ("manufacturing-spin-nut-before-cage-bolt", "spin",
         {"review_nut_y":14.5,"review_with_cage_bolt":False},True),
    ]
    cases = [export(name,REVIEW/f"manufacturing-{kind}-nut-probe.scad",defs,empty)
             for name,kind,defs,empty in probes]
    part_requests = [
        ("manufacturing-spin-body", "spin-head.scad", {"part":"body"}),
        ("manufacturing-spin-cover", "spin-head.scad", {"part":"cover"}),
        ("manufacturing-feeder-left-support", "feeder-supports.scad",
         {"support_part":"left_support"}),
        ("manufacturing-feeder-carriage", "feeder-supports.scad",
         {"support_part":"carriage"}),
    ]
    parts = [export(name,SNAPSHOT/"cad"/source,defs,False)
             for name,source,defs in part_requests]
    machine, machine_chain = merged_profile("machine", "Bambu Lab X1 Carbon 0.4 nozzle")
    process, process_chain = merged_profile("process", machine["default_print_profile"])
    profile = {key:machine.get(key) for key in ("name","printable_area","printable_height",
                "bed_exclude_area","nozzle_diameter","default_print_profile")}
    process_values = {key:process.get(key) for key in ("name","layer_height","line_width",
                     "wall_loops","enable_support","support_type","support_on_build_plate_only")}
    body_path = REVIEW/"manufacturing-spin-body.stl"
    body_facts = next(p["mesh"] for p in parts if p["name"] == "manufacturing-spin-body")
    hits = z_intersections(body_path,45,0)
    current_sources = [{"path":i["original_path"],
                        "sha256_at_report_run":sha256(ROOT/i["original_path"]),
                        "matches_initial_snapshot":sha256(ROOT/i["original_path"]) == i["sha256"]}
                       for i in manifest["sources"]]
    report = {
        "status":"INITIAL_SNAPSHOT_HAS_TWO_BLOCKING_ASSEMBLY_COUNTEREXAMPLES",
        "report_generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope":"Frozen initial snapshot only; later root fixes need separate evidence",
        "frozen_snapshot":manifest, "current_sources_for_drift_notice_only":current_sources,
        "probe_sources":[{"path":str(p.relative_to(ROOT)),"sha256":sha256(p)} for p in
                         (REVIEW/"manufacturing-feeder-nut-probe.scad",
                          REVIEW/"manufacturing-spin-nut-probe.scad")],
        "fastener_envelopes":{
            "M3_probe":{"af_mm":5.5,"thickness_mm":2.4,"generous_hole_mm":3.2},
            "M4_probe":{"af_mm":7,"thickness_mm":3.2,"generous_hole_mm":4.5},
            "evidence_level":"Nominal review envelopes, no actual purchased lot or SKU verified"},
        "counterexample_cases":cases,
        "all_cases_match_expected_counterexamples_and_controls":all(c["matches_expectation"] for c in cases),
        "selected_exported_parts":parts,
        "installed_bundled_machine_profile":profile,
        "installed_bundled_process_profile":process_values,
        "profile_source_chain":{"machine":machine_chain,"process":process_chain},
        "profile_is_user_active_preset":False,
        "individual_unrotated_bbox_screen_only":[
            {"name":p["name"],"size_mm":p["mesh"]["size_mm"],
             "fits_simple_256_256_250_box":all(a<=b for a,b in zip(p["mesh"]["size_mm"],(256,256,250))),
             "exclusion_brim_support_and_toolpath_not_checked":True} for p in parts],
        "upright_body_cantilever_witness":{
            "actual_mesh":str(body_path.relative_to(ROOT)),"ray_xy_mm":[45,0],
            "ray_surface_z_mm":hits,"body_bed_z_mm":body_facts["bounds_min_mm"][2],
            "first_material_height_above_bed_mm":hits[0]-body_facts["bounds_min_mm"][2] if hits else None,
            "interpretation":"No material directly below the outboard floor; does not by itself prove print failure. Orientation/support and removable support paths need sliced inspection."},
        "sliced":False,"printer_accessed":False,"profiles_modified":False,
        "open_gates":["actual supplier/lot dimensions and screw head geometry",
                      "printed nut-pocket and sliding fits",
                      "external locknut and wrench swept path",
                      "layer orientation, support removal and actual sliced paths",
                      "spring free length, solid height, force curve and fatigue",
                      "soft-pad hardness, retention and wear",
                      "loaded physical assembly and launch acceptance"]}
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"report":str(report_path),"counterexample_controls_match":
                      report["all_cases_match_expected_counterexamples_and_controls"],
                      "intersection_volumes_mm3":{c["name"]:c["mesh"]["volume_mm3"]
                        for c in cases if "mesh" in c},
                      "cantilever_witness":report["upright_body_cantilever_witness"]},
                     ensure_ascii=False,indent=2))
    if not report["all_cases_match_expected_counterexamples_and_controls"]:
        raise SystemExit("Unexpected probe result: inspect cases before drawing conclusions")


if __name__ == "__main__":
    main()
