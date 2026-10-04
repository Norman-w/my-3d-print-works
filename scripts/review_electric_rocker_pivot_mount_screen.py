#!/usr/bin/env python3
"""Check a seam-bolt rocker-pivot bracket candidate against current CAD.

This is a deterministic nominal-space screen. It cannot certify PETG strength,
seam clamp preload, rocker bearings, or the as-purchased motor interface.
"""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electric-rocker-pivot-mount-screen.scad"
OUT = ROOT / "output/electric-rocker-pivot-mount-screen"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
ROCKER_REPORT = ROOT / "output/electric-rocker-bridge-screen/review.json"
POSES = (0, .25, .5, .75, 1)
STATIC = (
    "bracket-fixed", "bracket-switch", "bracket-motor",
    "anchor-contact-upper", "anchor-contact-lower",
    "screw-tool-with-cap", "screw-tool-cap-off", "pivot-tool",
    "replacement-screw-bracket", "positive-control",
)
DYNAMIC = (
    "bracket-moving", "bracket-moving-clearance-1mm",
    "bracket-rocker", "bracket-rocker-clearance-1mm",
    "bracket-bridge", "bracket-hardware",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def sources(path: Path, found: set[Path] | None = None) -> set[Path]:
    found = found if found is not None else set()
    path = path.resolve()
    if path in found:
        return found
    found.add(path)
    for name in re.findall(r"\b(?:use|include)\s*<([^>]+)>", path.read_text()):
        sources(path.parent / name, found)
    return found


def build(name: str, pose: float = 0, part: str = "probe") -> dict:
    target = OUT / "probes" / f"{name}-t{pose:.2f}.stl"
    if part == "bracket":
        target = OUT / "bracket.stl"
    elif part == "rocker-phase":
        target = OUT / "phase" / f"rocker-t{pose:.2f}.stl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'pm_part="{part}"', "-D", f'pm_probe="{name}"',
           "-D", f"pm_t={pose}", "-D", f"rb_t={pose}",
           "-o", str(target), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                         timeout=120)
    log = run.stdout + run.stderr
    if run.returncode == 1 and "Current top level object is empty" in log \
            and "WARNING:" not in log and "ERROR:" not in log:
        return {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log \
            or not target.is_file():
        return {"error": log[-1200:]}
    check = subprocess.run(["python3", str(INSPECT), str(target), "--json"],
                           cwd=ROOT, capture_output=True, text=True, timeout=30)
    if check.returncode:
        return {"error": (check.stderr + check.stdout)[-1200:]}
    mesh = json.loads(check.stdout)
    return {"occupied": mesh["volume"] > 1e-6,
            "volume_mm3": round(mesh["volume"], 5),
            "bounds": mesh["bounds"] if mesh["volume"] > 1e-6 else None,
            "watertight": mesh["watertightByEdgeTopology"]}


def render(pose: float, name: str) -> dict:
    target = OUT / name
    target.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "--render", "--imgsize=1400,1000",
           "--camera=36,48,14,66,0,145,215",
           "-D", 'pm_part="context"', "-D", f"pm_t={pose}",
           "-D", f"rb_t={pose}",
           "-o", str(target), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                         timeout=120)
    log = run.stdout + run.stderr
    raw = target.read_bytes() if target.exists() else b""
    if run.returncode or "WARNING:" in log or "ERROR:" in log \
            or raw[:8] != b"\x89PNG\r\n\x1a\n" \
            or struct.unpack(">II", raw[16:24]) != (1400, 1000):
        return {"error": log[-1200:] or "Invalid image"}
    return {"path": str(target.relative_to(ROOT)), "sha256": digest(target),
            "feeder_travel_mm": pose*20}


def main() -> int:
    rocker = json.loads(ROCKER_REPORT.read_text())
    if rocker["status"] != "OUTPUT_BRIDGE_LAYOUT_SCREEN_ONLY" \
            or rocker["manufacturing_release"]:
        raise RuntimeError("Upstream rocker screen is not the expected candidate")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probes").mkdir(exist_ok=True)
    tracked = sources(CAD) | {Path(__file__).resolve()}
    before = {str(p.relative_to(ROOT)): digest(p) for p in sorted(tracked)}
    rows = [(name, 0) for name in STATIC]
    rows += [(name, pose) for name in DYNAMIC for pose in POSES]
    with ThreadPoolExecutor(max_workers=4) as pool:
        checks = dict(zip((f"{name}-t{pose:.2f}" for name, pose in rows),
                          pool.map(lambda row: build(*row), rows)))
    bracket = build("bracket", 0, "bracket")
    phase = {f"t{pose:.2f}": build("rocker-phase", pose, "rocker-phase")
             for pose in (0, 1)}
    images = {name: render(pose, name) for pose, name in
              ((0, "pivot-home.png"), (1, "pivot-full.png"))}
    after = {str(p.relative_to(ROOT)): digest(p) for p in sorted(tracked)}

    expected_present = {"anchor-contact-upper-t0.00",
                        "anchor-contact-lower-t0.00",
                        "positive-control-t0.00",
                        "screw-tool-with-cap-t0.00"}
    failures = []
    for key, row in checks.items():
        if row.get("error") or (row.get("occupied") != (key in expected_present)):
            failures.append(key)
    if bracket.get("error") or not bracket.get("occupied") \
            or not bracket.get("watertight"):
        failures.append("bracket-mesh")
    if any(row.get("error") or not row.get("watertight")
           for row in phase.values()):
        failures.append("rocker-phase-mesh")
    else:
        home, full = phase["t0.00"], phase["t1.00"]
        z_shift = full["bounds"]["max"][2] - home["bounds"]["max"][2]
        if not 13 < z_shift < 14 \
                or abs(full["volume_mm3"]-home["volume_mm3"]) > .001:
            failures.append("rocker-phase-did-not-move")
    if any(row.get("error") for row in images.values()):
        failures.append("render")
    if before != after:
        failures.append("source-changed")
    report = {
        "status": "FAIL" if failures else "PIVOT_MOUNT_LAYOUT_SCREEN_ONLY",
        "source_sha256": before,
        "rocker_report_sha256": digest(ROCKER_REPORT),
        "nominal_mount_contract": {
            "process": "X1C 0.4 mm nozzle, PETG, FDM",
            "host_split_plane": "X=0; bracket touches only +X shell boss faces",
            "shared_seam_screw_stations_yz_mm": [[40,16],[40,-10]],
            "bracket_contact_face_x_mm": 7,
            "old_screw_heads_replaced_not_stacked": True,
            "proposed_new_screw": "M3x20, screw/head only represented as an envelope",
            "nominal_new_screw_underhead_length_mm": 20,
            "screw_entry": "+X; remove right switch cap for lower screw tool",
            "pivot_xyz_mm": [round(85-(75*75-15*15)**.5,4),62,25],
            "fork_inner_y_gap_mm": 8,
            "shaft_bore_d_mm": 6.4,
            "shaft_and_bearing_design_complete": False,
            "bracket_strength_and_fastener_preload_verified": False,
            "as_purchased_motor_interface_verified": False,
            "seam_seal_unchanged_by_CAD": True,
            "seam_clamping_after_fastener_substitution_verified": False,
        },
        "bracket_mesh": bracket,
        "rocker_phase_witness": phase,
        "probes": checks,
        "images": images,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(report["status"], len(checks), "probes", len(failures), "failures")
    for key in failures:
        print(key, checks.get(key, {}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
