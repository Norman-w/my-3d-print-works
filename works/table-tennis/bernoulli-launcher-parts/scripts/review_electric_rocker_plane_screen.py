#!/usr/bin/env python3
"""Compare nominal rocker sweep planes against the current electric assembly."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electric-rocker-plane-screen.scad"
OUT = ROOT / "output/electric-rocker-plane-screen"
INTEGRATION = ROOT / "output/electric-trigger-integration/review.json"
DRIVE = ROOT / "output/electric-drive-feasibility/report.json"
ENVELOPE = ROOT / "output/by141-envelope-screen/review.json"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
POSES = (0, .25, .5, .75, 1)
PLANES = (45, 63)
TARGETS = ("fixed", "moving", "hardware")


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_tree(path: Path, found: set[Path] | None = None) -> set[Path]:
    found = found if found is not None else set()
    path = path.resolve()
    if path in found:
        return found
    found.add(path)
    for name in re.findall(r"\b(?:use|include)\s*<([^>]+)>", path.read_text()):
        source_tree(path.parent / name, found)
    return found


def probe(row: tuple[int, str, float]) -> tuple[str, dict]:
    plane, target, pose = row
    tag = f"y{plane}-{target}-t{pose:.2f}"
    path = OUT / f"{tag}.stl"
    path.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f"rp_plane_y={plane}", "-D", f'rp_target="{target}"',
           "-D", f"rp_t={pose}", "-o", str(path), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                         timeout=120)
    log = run.stdout + run.stderr
    if (run.returncode == 1 and "Current top level object is empty" in log
            and "WARNING:" not in log and "ERROR:" not in log):
        return tag, {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log:
        return tag, {"error": log[-1200:]}
    inspected = subprocess.run([sys.executable, str(INSPECT), str(path),
                                "--json", "--require-watertight"], cwd=ROOT,
                               text=True, capture_output=True, timeout=60)
    if inspected.returncode:
        return tag, {"error": inspected.stdout[-1000:] + inspected.stderr[-1000:]}
    mesh = json.loads(inspected.stdout)
    occupied = mesh["volume"] > 1e-9
    return tag, {"occupied": occupied, "volume_mm3": mesh["volume"],
                 "bounds": mesh["bounds"] if occupied else None,
                 "stl_sha256": sha(path)}


def render() -> dict:
    path = OUT / "outer-plane-context.png"
    path.unlink(missing_ok=True)
    size = (1400, 1000)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "--render", f"--imgsize={size[0]},{size[1]}",
           "--camera=0,0,-50,65,0,150,950", "-D", 'rp_part="context"',
           "-D", "rp_plane_y=63", "-D", "rp_t=0.5",
           "-o", str(path), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                         timeout=120)
    log = run.stdout + run.stderr
    data = path.read_bytes() if path.exists() else b""
    if (run.returncode or "WARNING:" in log or "ERROR:" in log
            or data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24
            or struct.unpack(">II", data[16:24]) != size):
        return {"error": log[-1200:] or "Missing/invalid PNG"}
    return {"file": str(path.relative_to(ROOT)), "sha256": sha(path),
            "pixels": list(size), "feeder_travel_mm": 10}


def main() -> int:
    integration = json.loads(INTEGRATION.read_text())
    drive = json.loads(DRIVE.read_text())
    envelope = json.loads(ENVELOPE.read_text())
    if (integration["status"] != "SELECTED_TRIGGER_GEOMETRY_PASS_UNRELEASED"
            or drive["status"] != "NECESSARY_LOAD_BOUND_ONLY_MOTOR_NOT_APPROVED"
            or envelope["status"] != "SCHEMATIC_SELLER_ENVELOPE_SCREEN_ONLY"
            or not envelope["candidates"]["d29-x85-y63"]["sampled_collision_free"]):
        raise RuntimeError("Selected assembly or seller motor envelope review is missing")
    for name, expected in integration["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"Selected assembly source changed: {name}")
    OUT.mkdir(parents=True, exist_ok=True)
    tracked = source_tree(CAD) | {Path(__file__).resolve()}
    before = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    rows = [(plane, target, pose) for plane in PLANES for target in TARGETS
            for pose in POSES]
    with ThreadPoolExecutor(max_workers=4) as pool:
        probes = dict(pool.map(probe, rows))
    image = render()
    after = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    errors = [tag for tag, row in probes.items() if "error" in row]
    inner_hits = [tag for tag, row in probes.items()
                  if tag.startswith("y45-") and row.get("occupied")]
    outer_hits = [tag for tag, row in probes.items()
                  if tag.startswith("y63-") and row.get("occupied")]
    failures = errors + outer_hits
    if not all(probes[f"y45-moving-t{pose:.2f}"].get("occupied")
               for pose in POSES):
        failures.append("inward-plane moving-part counterexample missing")
    if "error" in image:
        failures.append("context image failed: " + image["error"])
    if before != after:
        failures.append("source changed during review")
    report = {
        "status": "OUTER_ROCKER_PLANE_CLEARANCE_ONLY" if not failures else "FAIL",
        "source_sha256": before,
        "integrated_trigger_review_sha256": sha(INTEGRATION),
        "drive_report_sha256": sha(DRIVE),
        "motor_envelope_report_sha256": sha(ENVELOPE),
        "motor_axis_xy_mm": [85, 63],
        "motor_envelope_diameter_mm": 29,
        "rocker_pivot_xyz_mm": [40, 63, 23],
        "input_output_arm_radii_mm": [45, 30],
        "outer_plane_y_mm": 63,
        "inward_counterexample_plane_y_mm": 45,
        "feeder_travel_samples_mm": [round(20*p, 4) for p in POSES],
        "probe_count": len(rows), "probes": probes,
        "inner_plane_colliding_probes": inner_hits,
        "outer_plane_colliding_probes": outer_hits,
        "context_image": image,
        "minimum_y_offset_from_selected_right_rail_outer_edge_mm": 63-24,
        "output_crosshead_and_bearing_mount_designed": False,
        "motor_to_input_pin_connection_designed": False,
        "rocker_to_seller_motor_self_collision_checked": False,
        "continuous_sweep_proven": False,
        "structural_load_path_verified": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False,
                                                 indent=2) + "\n")
    print(f"Rocker sweep plane screen: {len(rows)} probes, "
          f"{len(inner_hits)} inward collisions, {len(outer_hits)} outward collisions, "
          f"{len(failures)} errors")
    for failure in failures:
        print("  ERROR " + failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
