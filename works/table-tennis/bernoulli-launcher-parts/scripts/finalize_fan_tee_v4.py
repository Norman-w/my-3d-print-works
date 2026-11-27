#!/usr/bin/env python3
"""Bind geometry evidence and prove standalone source rebuild, without slicing."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np
import trimesh
import manifold3d as mf

from export_fan_tee_v4 import SOURCE_NAMES, TARGETS, dump, sha
from verify_fan_tee_v4 import solid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT/"output/fan-tee-direct-print-v4-20261007"
SCRIPT_NAMES = ["export_fan_tee_v4.py", "verify_fan_tee_v4.py",
                "render_fan_tee_v4_review.py", "finalize_fan_tee_v4.py"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--openscad", default="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    args = ap.parse_args(); out = args.out.resolve()
    acceptance = json.loads((out/"verification/geometry-acceptance.json").read_text())
    export = json.loads((out/"verification/export.json").read_text())
    visual = json.loads((out/"verification/visual-review.json").read_text())
    stl = out/"stl/fan-tee-v4-connector-clean.stl"
    assert sha(stl) == acceptance["sha256"] == visual["stl_sha256"]
    for name, digest in visual["images_reviewed"].items():
        assert sha(out/name) == digest, "Visual evidence changed; re-inspect rather than silently updating acceptance"
    edges = []
    for name in SOURCE_NAMES:
        p = out/"source"/name
        assert sha(p) == export["source_sha256"][name] == sha(ROOT/"cad"/name)
        for dep in re.findall(r"(?:include|use)\s*<([^>]+)>", p.read_text()):
            resolved = (p.parent/dep).resolve()
            assert resolved.parent == (out/"source").resolve() and resolved.name in SOURCE_NAMES
            edges.append({"source": name, "include": dep})
    # Copy ONLY v4 sources into a new isolated scratch directory, explicitly
    # empty the OpenSCAD library path, compile, and compare solid geometry.
    # TemporaryDirectory removes only this newly-created scratch directory.
    with tempfile.TemporaryDirectory(prefix="fan-tee-v4-independent-") as scratch:
        temp = Path(scratch)
        for name in SOURCE_NAMES:
            shutil.copy2(out/"source"/name, temp/name)
        rebuilt = temp/"connector.stl"
        env = dict(os.environ); env["OPENSCADPATH"] = ""
        cmd = [args.openscad, "--backend", "Manifold", "--hardwarnings", "--export-format", "binstl",
               "-D", 'part="connector"', "-o", str(rebuilt), str(temp/"fan-tee-direct-v4.scad")]
        run = subprocess.run(cmd, capture_output=True, text=True, env=env)
        (out/"logs/independent-rebuild.log").write_text(run.stdout+run.stderr)
        assert run.returncode == 0, run.stderr
        rebuilt_sha = sha(rebuilt)
        A, B = solid(trimesh.load_mesh(stl)), solid(trimesh.load_mesh(rebuilt))
        difference = abs((A-B).volume())+abs((B-A).volume())
        assert difference < 1e-5
    dependency_audit = {
        "status": "PASS_SELF_CONTAINED_SOURCE_REBUILD",
        "include_graph": edges, "source_files": SOURCE_NAMES,
        "legacy_cad_or_output_runtime_dependencies": [],
        "library_search_path": "explicitly empty during independent rebuild",
        "rebuilt_stl_sha256": rebuilt_sha, "delivered_stl_sha256": sha(stl),
        "binary_identical": rebuilt_sha == sha(stl), "symmetric_difference_mm3": difference,
        "compatibility_witness_is_package_local": "verification/reference/printed-core36.stl",
        "rebuild_tools": "OpenSCAD; geometry verification additionally uses numpy/trimesh/manifold3d and installed generic inspect_stl.py",
        "old_versions_can_be_retired_by_main_thread": True,
    }
    dump(out/"verification/dependency-audit.json", dependency_audit)
    excluded = ["print/", "verification/retirement.json"]
    own_paths = [ROOT/"cad"/n for n in SOURCE_NAMES] + [ROOT/"scripts"/n for n in SCRIPT_NAMES]
    # Enumerate only geometry-owned files. Main-thread slice and retirement
    # outputs are excluded even when they are being written concurrently.
    verification_names = {
        "baseline.json", "parameters.json", "export.json", "parameter-diff.json",
        "downward-surfaces.json", "geometry.json", "baseline-mesh-difference.json",
        "geometry-acceptance.json", "motion-printed-core36.json", "motion-baseline-anchored-core36.json",
        "render-provenance.json", "visual-review.json", "dependency-audit.json",
    } | {f"topology-{name}.json" for name in TARGETS}
    for folder in ["source", "stl", "review", "render"]:
        own_paths += [p for p in (out/folder).rglob("*") if p.is_file()]
    own_paths += [out/"verification"/n for n in verification_names if (out/"verification"/n).exists()]
    own_paths += [p for p in (out/"verification/reference").rglob("*") if p.is_file()]
    log_names = {f"{name}.log" for name in TARGETS} | {
        "parameters.echo", "render-front.log", "render-top.log", "render-iso.log", "independent-rebuild.log"}
    own_paths += [out/"logs"/n for n in log_names if (out/"logs"/n).exists()]
    own_paths += [out/"README.md"]
    owned = {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(own_paths))}
    dump(out/"verification/owned-files.json", {"geometry_owned_files_sha256": owned,
                                             "excluded_main_thread_paths": excluded,
                                             "unhashed_generated_metadata": ["manifest.json", "verification/owned-files.json"],
                                             "self_and_manifest_are_not_hashed_to_avoid_self_reference": True})
    manifest = {
        "owner": "geometry-apprentice", "artifact": "fan-tee-direct-print-v4-20261007",
        "geometry_status": "READY_FOR_MAIN_THREAD_SLICE_AND_FIRST_ARTICLE",
        "units": "mm by source convention", "print_quantity": 1,
        "print_targets": [{"file": str(stl.relative_to(out)), "sha256": sha(stl),
                           "size_mm": acceptance["geometry"]["size_mm"],
                           "triangle_count": export["files"][0]["topology"]["triangleCount"],
                           "connected_solids": 1, "watertight": True,
                           "embedded_supports": False}],
        "do_not_print": ["review/*", "verification/reference/*", "all nozzle cores"],
        "print_pose": {"axis": "+Z", "model_base_z_mm": -18.5,
                       "bed_translation_z_mm": 18.5, "scale": [1, 1, 1]},
        "source_sha256": export["source_sha256"],
        "changes": acceptance["parameter_diff"],
        "compatibility": acceptance["compatibility"],
        "geometry": acceptance["geometry"],
        "thread_overhang": acceptance["downward_surfaces"],
        "dependency_audit": "verification/dependency-audit.json",
        "owned_files": "verification/owned-files.json",
        "views": list(visual["images_reviewed"]),
        "skills_used_not_modified": ["openscad-stl-print", "helical-thread-workflow",
                                     "socket-bayonet-fit", "parametric-mounting-interface"],
        "slicing_and_printer_status": "owned by main thread; not assessed or overwritten by this manifest",
        "main_thread_paths": excluded,
        "physical_acceptance": False,
        "remaining_gates": [
            "Actual slicer tree-support contact/removal audit; only local lugs may need supports",
            "Fan slot-bottom depth / inside-wall clearance for increased 2.8 mm nominal radial engagement",
            "Measured tee ovality/taper and PETG first-fit at nominal 0.1 mm radial gap",
            "Physical screw-in/exit and load testing: female minor-tip axial web reduced from 1.12 to 0.787 mm",
        ],
    }
    destination = out/"manifest.json"
    if destination.exists():
        existing = json.loads(destination.read_text())
        assert existing.get("owner") == "geometry-apprentice", "Do not overwrite a main-thread manifest"
    dump(destination, manifest)
    print("Geometry manifest complete; standalone rebuild", dependency_audit["status"],
          "binary-identical", dependency_audit["binary_identical"], "files", len(owned), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
