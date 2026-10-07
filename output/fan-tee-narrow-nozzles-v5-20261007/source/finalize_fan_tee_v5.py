#!/usr/bin/env python3
"""Freeze Ø41 v5 geometry manifest, reproduce STL from isolated source closure.

Never reads or writes print/. No Git mutation, no slicing, no device calls.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT/"output/fan-tee-narrow-nozzles-v5-20261007"
SOURCES = ["fan-tee-narrow-v5.scad", "fan-tee-v5-parameters.scad", "fan-tee-v5-thread.scad"]
SCRIPTS = ["export_fan_tee_v5.py", "verify_fan_tee_v5.py", "render_fan_tee_v5_review.py", "finalize_fan_tee_v5.py"]
IDS = ["mother", "nozzle15", "nozzle20", "nozzle25", "nozzle30"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--openscad", default="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    a = ap.parse_args(); out = a.out.resolve()
    acceptance = json.loads((out/"verification/geometry-acceptance.json").read_text())
    export = json.loads((out/"verification/export.json").read_text())
    render = json.loads((out/"verification/render-provenance.json").read_text())
    assert acceptance["status"]=="DIGITAL_GEOMETRY_PASS_SLICE_AND_PHYSICAL_PENDING"
    assert acceptance["pitch_mm"]==4 and acceptance["effective_travel_mm"]==40
    rebuilt = out/"verification/rebuild"
    rebuilt.mkdir(parents=True, exist_ok=True)
    for name in SOURCES:
        path = out/"source"/name
        assert sha(path)==export["source_sha256"][name]==sha(ROOT/"cad"/name)
        references = re.findall(r"(?:include|use)\s*<([^>]+)>", path.read_text())
        assert all(reference in SOURCES for reference in references), references
        shutil.copy2(path, rebuilt/name)
    for name in SCRIPTS:
        shutil.copy2(ROOT/"scripts"/name, out/"source"/name)
    checks, parts = [], []
    for name in IDS:
        path = out/f"stl/fan-tee-v5-{name}-clean.stl"
        digest = sha(path)
        assert digest==acceptance["geometry"]["parts"][name]["sha256"]==render["input_stl_sha256"][name]
        raw = path.read_bytes()
        triangles = int.from_bytes(raw[80:84], "little")
        assert len(raw)==84+50*triangles, "Not exact binary STL"
        target = rebuilt/path.name
        cmd = [a.openscad, "--backend", "Manifold", "--hardwarnings", "--export-format", "binstl",
               "-D", f'part="{name}"', "-o", str(target), str(rebuilt/SOURCES[0])]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        (out/f"verification/logs/rebuild-{name}.log").write_text(run.stdout+run.stderr)
        assert run.returncode==0, run.stderr
        assert sha(target)==digest, (name, sha(target), digest)
        checks.append({"part": name, "original_sha256": digest, "isolated_sha256": sha(target), "identical_bytes": True})
        info = acceptance["geometry"]["parts"][name]
        parts.append({"part_id": name, "file": f"stl/{path.name}", "sha256": digest,
                      "quantity": 1, "format": "binary STL", "units": "mm", "scale": [1, 1, 1],
                      "dimensions_mm": info["size_mm"], "triangle_count": triangles,
                      "connected_solids": 1, "watertight": True, "embedded_supports": False,
                      "outlet_id_mm": None if name=="mother" else int(name[6:]),
                      "recommended_print_pose": {"rotation_xyz_deg": [0, 0, 0], "translation_xyz_mm": [0, 0, info["print_translate_z_mm"]]},
                      "assembly": {"frame": "mother-local", "translate_z_mm": 0, "rotate_z_deg": 0} if name=="mother" else
                                  {"frame": "mother-local", "normal_translate_z_range_mm": [34, 74], "rotation_z_deg": "360*(translate_z-34)/4", "exit_protrusion_range_mm": [12, 52]},
                      "support_intent": "slicer-generated local lug support only" if name=="mother" else "no supports; validate native toolpaths"})
        print("Isolated source-only rebuild", name, "byte-identical", flush=True)
    dump(out/"verification/self-contained-rebuild.json", {
        "status": "PASS_BYTE_IDENTICAL_SOURCE_ONLY_REBUILD", "source_closure": SOURCES,
        "old_version_runtime_dependencies": [], "skill_library_runtime_dependency_for_scad": False,
        "stl_rebuilds": checks,
        "python_tools_require": ["Python3", "numpy", "trimesh", "manifold3d", "matplotlib", "OpenSCAD Manifold"]})
    owned_files = []
    for dirname in ["source", "stl", "review", "render", "verification"]:
        owned_files += sorted(p for p in (out/dirname).rglob("*") if p.is_file())
    owned_files.append(out/"README.md")
    inventory = [{"file": str(p.relative_to(out)), "sha256": sha(p)} for p in owned_files]
    manifest = {
        "schema": "fan-tee-geometry-package/v5", "design": "Ø41 fan to direct Y tee, matched narrow nozzle set",
        "units": "mm", "status": "GEOMETRY_VALIDATED_NATIVE_SLICE_AND_FIRST_ARTICLE_PENDING",
        "scope": "Only Ø41 v5 CAD/STL/geometry verification; print/ is main-thread owned and excluded",
        "pitch_mm": 4, "effective_continuous_travel_mm": 40, "normal_adjustment_turns": 10,
        "minimum_complete_engaged_turns_excluding_leads": 3, "mother_groove_cut_length_mm": 64,
        "mother_body_height_mm": 146.5, "nozzle_length_mm": 106,
        "parts": parts, "print_part_count": 5, "embedded_supports": False,
        "source_files": {name: sha(out/"source"/name) for name in SOURCES},
        "tool_files": {name: sha(ROOT/"scripts"/name) for name in SCRIPTS},
        "mechanical_reference": "README.md",
        "reports": {"geometry": "verification/geometry-acceptance.json", "motion": "verification/motion.json",
                    "continuous_turn_count": "verification/engagement.json", "overhangs": "verification/downward-surfaces.json",
                    "source_closure": "verification/self-contained-rebuild.json", "v4_comparison": "verification/parameter-diff.json",
                    "images": "verification/render-provenance.json"},
        "legacy_core_compatibility": acceptance["legacy_core"],
        "geometry_gates": {"closed_single_solids": "PASS", "unchanged_external_interfaces": "PASS",
                           "40mm_travel_minimum_3_full_turns": "PASS", "1176_pose_path_plus_wrong_phase_controls": "PASS",
                           "actual_mesh_thread_angles_above49deg": "PASS", "only_lugs_below45deg": "PASS",
                           "source_only_identical_rebuild": "PASS"},
        "not_passed_here": ["native slicer all toolpaths/contact audit", "physical full-depth threaded fit", "bayonet slot floor clearance and strength", "Y insertion first article", "Y/ball path at maximum protrusion", "airflow performance"],
        "owner_changed_repo_files": [f"cad/{n}" for n in SOURCES]+[f"scripts/{n}" for n in SCRIPTS]+[str(out.relative_to(ROOT))+"/ (geometry-only subdirectories)"],
        "file_inventory_excludes_main_thread_print_directory": inventory,
    }
    dump(out/"manifest.json", manifest)
    print("Final geometry manifest", out/"manifest.json", flush=True)


if __name__ == "__main__":
    main()
