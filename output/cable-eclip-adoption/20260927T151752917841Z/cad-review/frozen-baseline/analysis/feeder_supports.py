#!/usr/bin/env python3
"""Actual CSG intersection and disassembly-path samples for support candidate.

Run with native OpenSCAD access. This does not simulate air, elasticity or wear.
Nonempty expected-to-be-empty cases are retained as counterexample STL files.
"""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import struct

ROOT = Path(__file__).resolve().parents[1]
SCAD = ROOT / "cad/feeder-supports.scad"
OPENSCAD = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
OUT = ROOT / "output/analysis"
CASES = OUT / "feeder-cases"


def stl_volume_and_bounds(path: Path) -> tuple[float, list]:
    data = path.read_bytes()
    if data[:5] == b"solid":
        vertices = [tuple(map(float, line.split()[1:])) for line in data.decode().splitlines()
                    if line.strip().startswith("vertex")]
    else:
        vertices = []
        for i in range(struct.unpack_from("<I", data, 80)[0]):
            f = struct.unpack_from("<12fH", data, 84+50*i)
            vertices.extend([f[3:6], f[6:9], f[9:12]])
    def det(a, b, c):
        return (a[0]*(b[1]*c[2]-b[2]*c[1]) + a[1]*(b[2]*c[0]-b[0]*c[2])
                + a[2]*(b[0]*c[1]-b[1]*c[0]))
    volume = abs(sum(det(*vertices[i:i+3]) for i in range(0,len(vertices),3))/6)
    return volume, [[min(v[j] for v in vertices), max(v[j] for v in vertices)] for j in range(3)]


def invoke(label: str, definitions: dict, expect_empty: bool) -> dict:
    destination = CASES / f"{label}.stl"
    destination.unlink(missing_ok=True)
    args = [OPENSCAD, "--render", "--backend", "Manifold", "-o", str(destination)]
    for key, value in definitions.items():
        args += ["-D", f"{key}={json.dumps(value)}"]
    args += [str(SCAD)]
    p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    empty = "Current top level object is empty." in p.stderr
    nonempty = p.returncode == 0 and destination.exists() and destination.stat().st_size > 0
    volume, bounds = stl_volume_and_bounds(destination) if nonempty else (0, None)
    # Exact stop/seating faces may export a degenerate sheet. Permit only a
    # nearly-zero volume AND one collapsed AABB dimension, never volume alone.
    contact_sheet = bool(nonempty and volume < 1e-7 and min(b[1]-b[0] for b in bounds)<1e-7)
    penetration = nonempty and not contact_sheet
    passed = (empty or contact_sheet) if expect_empty else penetration
    return {
        "name": label, "definitions": definitions, "expected_empty": expect_empty,
        "empty_intersection": empty, "nonempty_intersection": nonempty,
        "zero_thickness_contact_sheet": contact_sheet,
        "intersection_volume_mm3": volume, "intersection_bounds_mm": bounds,
        "passed": passed,
        "exit_code": p.returncode,
        "counterexample_or_control_stl": str(destination.relative_to(ROOT)) if nonempty else None,
        "diagnostic": p.stderr[-1400:] if not passed else "",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    CASES.mkdir(parents=True, exist_ok=True)
    inputs = [ROOT / "cad/parameters.scad", ROOT / "cad/cam-study.scad", SCAD,
              Path(__file__).resolve()]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    jobs = []
    for i in range(41):
        jobs.append((f"motion-{i:02d}", {"support_part": "probe", "support_fraction": i/40}, True))
    for name, t in [("stop-before-zero", -.025), ("stop-beyond-full", 1.025)]:
        jobs.append((name, {"support_part": "probe", "support_fraction": t}, False))
    for kind in ["remove_pins", "lift_frame", "extract_fingers"]:
        for i in range(21):
            jobs.append((f"{kind}-{i:02d}", {"support_part": "probe",
                "support_fraction": .5, "support_probe_kind": kind,
                "support_probe_fraction": i/20}, True))
    for i in [0, 10, 20, 30, 40]:
        jobs.append((f"tool-{i:02d}", {"support_part": "tool_probe", "support_fraction": i/40}, True))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda j: invoke(*j), jobs))
    failures = [r for r in results if not r["passed"]]
    report = {
        "analysis_kind": "support_candidate_actual_csg_intersection_samples",
        "source_sha256": hashes,
        "scope": "Nominal modeled rigid parts. 41 motion poses, two stop-overtravel positive controls, 21 samples each of three service paths, five screwdriver clearances.",
        "status": "NOMINAL_CSG_SAMPLES_PASS_PHYSICAL_OPEN" if not failures else "COUNTEREXAMPLES_RETAINED",
        "pass_count": len(results)-len(failures), "case_count": len(results),
        "failure_count": len(failures), "failures": failures, "cases": results,
        "limits": [
            "Finite samples do not prove a continuous collision-free path.",
            "Thread unwinding is represented as axial extraction; no thread-force simulation.",
            "Body reference is not the root's finished sealed body or connectors.",
            "No structural stiffness, return-force, airflow, printing tolerance or wear acceptance.",
            "Spring dimensions and preload remain unselected; only adjustable M3 interfaces exist.",
        ],
    }
    (OUT / "feeder-support-check.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n")
    print(json.dumps({k: report[k] for k in ["status", "pass_count", "case_count", "failure_count"]}, indent=2))
    for failure in failures:
        print(failure["name"], failure["counterexample_or_control_stl"] or failure["diagnostic"])
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
