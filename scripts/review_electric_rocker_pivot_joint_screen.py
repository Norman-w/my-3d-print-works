#!/usr/bin/env python3
"""Compare the current pivot plane with a pin-retained, bushed alternative.

Catalog geometry is only a spatial reference. Printed bore accuracy, actual
pin retention, motor load, and replacement seam-bolt preload remain open.
"""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electric-rocker-pivot-joint-screen.scad"
OUT = ROOT / "output/electric-rocker-pivot-joint-screen"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
MOUNT_REPORT = ROOT / "output/electric-rocker-pivot-mount-screen/review.json"
BRIDGE_REPORT = ROOT / "output/electric-rocker-bridge-screen/review.json"
PLANES = (62, 65)
POSES = (0, .25, .5, .75, 1)
FINE_POSES = tuple(i/20 for i in range(21))
PROBES = (
    "front-retainer-moving", "front-retainer-moving-clearance-1mm",
    "front-retainer-fixed",
    "rear-head-moving", "rear-head-fixed", "rocker-moving", "rocker-fixed",
    "bushing-rocker", "bushing-bracket", "pin-bushing", "pin-bracket",
    "bracket-moving", "bracket-fixed", "bridge-fixed-clearance-2mm",
    "bridge-motor-clearance-4mm", "bridge-motor-clearance-5mm",
)
FINE_PROBES = ("front-retainer-moving", "rocker-moving", "bracket-moving")


def sha(path: Path) -> str:
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


def mesh(path: Path) -> dict:
    run = subprocess.run(["python3", str(INSPECT), str(path), "--json"],
                         cwd=ROOT, capture_output=True, text=True, timeout=30)
    if run.returncode:
        return {"error": (run.stderr + run.stdout)[-1000:]}
    row = json.loads(run.stdout)
    return {"sha256": sha(path), "volume_mm3": round(row["volume"], 5),
            "bounds": row["bounds"],
            "watertight": row["watertightByEdgeTopology"],
            "degenerate_faces": row["degenerateTriangleCount"]}


def build(plane: int, pose: float, kind: str, part: str = "probe") -> dict:
    if part == "probe":
        target = OUT / "probes" / f"y{plane}-t{pose:.2f}-{kind}.stl"
    elif part == "rocker-phase":
        target = OUT / "phase" / f"rocker-y{plane}-t{pose:.2f}.stl"
    else:
        target = OUT / f"{part}-y{plane}.stl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'pj_part="{part}"', "-D", f'pj_probe="{kind}"',
           "-D", f"pm_pivot_y={plane}", "-D", f"rb_plane_y={plane}",
           "-D", f"pj_t={pose}", "-D", f"rb_t={pose}",
           "-o", str(target), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                         timeout=120)
    log = run.stdout + run.stderr
    if part == "probe" and run.returncode == 1 \
            and "Current top level object is empty" in log \
            and "WARNING:" not in log and "ERROR:" not in log:
        return {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log \
            or not target.is_file():
        return {"error": log[-1000:]}
    result = mesh(target)
    if part == "probe":
        return {"occupied": result.get("volume_mm3", 0) > 1e-6,
                "volume_mm3": result.get("volume_mm3", 0),
                "error": result.get("error")}
    return result


def render(plane: int, pose: float) -> dict:
    target = OUT / f"joint-y{plane}-mid.png"
    target.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "--render", "--imgsize=1400,1000",
           "--camera=36,48,14,66,0,145,215",
           "-D", 'pj_part="context"', "-D", f"pm_pivot_y={plane}",
           "-D", f"rb_plane_y={plane}", "-D", f"pj_t={pose}",
           "-D", f"rb_t={pose}",
           "-o", str(target), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                         timeout=120)
    log = run.stdout + run.stderr
    raw = target.read_bytes() if target.exists() else b""
    if run.returncode or "WARNING:" in log or "ERROR:" in log \
            or raw[:8] != b"\x89PNG\r\n\x1a\n" \
            or struct.unpack(">II", raw[16:24]) != (1400, 1000):
        return {"error": log[-1000:] or "Invalid image"}
    return {"path": str(target.relative_to(ROOT)), "sha256": sha(target),
            "feeder_travel_mm": pose*20}


def main() -> int:
    mount = json.loads(MOUNT_REPORT.read_text())
    bridge = json.loads(BRIDGE_REPORT.read_text())
    if mount["status"] != "PIVOT_MOUNT_LAYOUT_SCREEN_ONLY" \
            or bridge["status"] != "OUTPUT_BRIDGE_LAYOUT_SCREEN_ONLY":
        raise RuntimeError("Required earlier layout screens are not current")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probes").mkdir(exist_ok=True)
    tracked = sources(CAD) | {Path(__file__).resolve()}
    before = {str(p.relative_to(ROOT)): sha(p) for p in sorted(tracked)}
    rows = [(y, t, k) for y in PLANES for t in POSES for k in PROBES]
    with ThreadPoolExecutor(max_workers=4) as pool:
        checks = dict(zip((f"y{y}-t{t:.2f}-{k}" for y,t,k in rows),
                          pool.map(lambda row: build(*row), rows)))
        fine_rows = [(65, t, k) for t in FINE_POSES if t not in POSES
                     for k in FINE_PROBES]
        fine = dict(zip((f"y{y}-t{t:.2f}-{k}" for y,t,k in fine_rows),
                        pool.map(lambda row: build(*row), fine_rows)))
    parts = {name: build(65, 0, name, name) for name in ("rocker", "bracket")}
    phase = {f"t{pose:.2f}": build(65, pose, "rocker-phase", "rocker-phase")
             for pose in (0, 1)}
    images = {f"y{y}": render(y, .5) for y in PLANES}
    after = {str(p.relative_to(ROOT)): sha(p) for p in sorted(tracked)}

    intentional = {
        f"y62-t{t:.2f}-front-retainer-moving" for t in (.25,.5,.75,1)
    } | {
        f"y62-t{t:.2f}-front-retainer-moving-clearance-1mm"
        for t in (.25,.5,.75,1)
    } | {f"y65-t{t:.2f}-bridge-motor-clearance-5mm" for t in POSES}
    failures = []
    for key, row in checks.items():
        if row.get("error") or row.get("occupied") != (key in intentional):
            failures.append(key)
    for key, row in fine.items():
        if row.get("error") or row.get("occupied"):
            failures.append(key)
    for name,row in parts.items():
        if row.get("error") or not row.get("watertight") or row.get("degenerate_faces"):
            failures.append(name)
    if any(row.get("error") or not row.get("watertight")
           for row in phase.values()):
        failures.append("rocker-phase-mesh")
    else:
        home, full = phase["t0.00"], phase["t1.00"]
        z_shift = full["bounds"]["max"][2] - home["bounds"]["max"][2]
        if not 9 < z_shift < 12 \
                or abs(full["volume_mm3"]-home["volume_mm3"]) > .001:
            failures.append("rocker-phase-did-not-move")
    if any(row.get("error") for row in images.values()):
        failures.append("images")
    if before != after:
        failures.append("source-changed")

    pin_x = 85-math.sqrt(75**2-15**2)
    bridge_right_x = pin_x+50+3.5+.4+3
    gap = math.hypot(85-bridge_right_x,70-(65-3.5))-29/2
    report = {
        "status": "FAIL" if failures else "Y62_RETAINER_COLLISION_Y65_LAYOUT_SCREEN_ONLY",
        "source_sha256": before,
        "mount_report_sha256": sha(MOUNT_REPORT),
        "bridge_report_sha256": sha(BRIDGE_REPORT),
        "catalog_reference": {
            "part": "igus iglide G GFM-0608-06",
            "manufacturer_pdf": "https://www.igus.com/ContentData/Products/Downloads/iglide_G300_FM_USen.pdf",
            "id_after_pressfit_mm": [6.020,6.068],
            "od_mm": 8,
            "flange_od_mm": 12,
            "body_length_mm": 6,
            "flange_thickness_mm": 1,
            "required_housing_bore_mm": [8.000,8.015],
            "recommended_shaft_diameter_range_mm": [5.970,6.000],
            "catalog_tolerances_are_not_petg_print_tolerances": True,
        },
        "nominal_axial_budget": {
            "fork_inner_gap_mm": 8,
            "bushing_body_plus_flange_mm": 7,
            "total_free_gap_mm": 1,
            "centered_side_gaps_mm": [.5,.5],
            "rocker_hub_radial_wall_mm": 4,
            "installed_id_to_shaft_diametral_clearance_range_mm": [.020,.098],
            "real_pressfit_in_petg_verified": False,
            "real_clevis_pin_and_retainer_selected": False,
            "retainer_screen_envelope_diameter_mm": 16,
            "retainer_screen_envelope_axial_mm": 3,
        },
        "plane_comparison": {
            "current_y62_front_retainer_colliding_travel_mm": [5,10,15,20],
            "outer_y65_nominal_bridge_to_motor_proxy_gap_mm": round(gap,4),
            "outer_y65_bridge_motor_4mm_dilation_clear": True,
            "outer_y65_bridge_motor_5mm_dilation_clear": False,
            "actual_motor_envelope_and_load_verified": False,
            "y65_promoted_to_selected_assembly": False,
        },
        "probes": checks,
        "selected_y65_fine_probes": fine,
        "candidate_meshes": parts,
        "rocker_phase_witness": phase,
        "images": images,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(report["status"], len(checks), "coarse", len(fine), "fine",
          len(failures), "failures")
    for key in failures:
        print(key, checks.get(key, fine.get(key, {})))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
