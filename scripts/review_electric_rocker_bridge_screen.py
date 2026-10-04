#!/usr/bin/env python3
"""Screen a closed-slot output bridge against the current switch candidate.

The probe is an intentionally solid minimum envelope, not an installable
rocker, motor mount, carriage, or print release. Motor geometry is a seller
image proxy; sample clearance cannot replace a measured actuator interface.
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
CAD = ROOT / "cad/electric-rocker-bridge-screen.scad"
OUT = ROOT / "output/electric-rocker-bridge-screen"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
SIDE = ROOT / "output/electric-end-switch-side-cap/review.json"
ENVELOPE = ROOT / "output/by141-envelope-screen/review.json"
RADII = (45, 60, 75)
PLANES = (52, 55, 58, 62, 63)
POSES = (0, .5, 1)
FINE_POSES = tuple(i/20 for i in range(21))
PROBES = (
    "bridge-fixed", "bridge-hardware", "bridge-switch", "bridge-motor",
    "motor-proxy-fixed", "motor-proxy-moving", "motor-proxy-hardware",
    "rocker-fixed", "rocker-moving", "rocker-hardware", "rocker-switch",
    "rocker-bridge-visual",
)
MARGIN_PROBES = (
    "bridge-fixed-clearance-2mm", "bridge-switch-clearance-2mm",
    "bridge-hardware-clearance-2mm", "bridge-motor-clearance-5mm",
    "rocker-fixed-clearance-2mm", "rocker-moving-clearance-2mm",
    "rocker-switch-clearance-2mm", "rocker-hardware-clearance-2mm",
)
FINE_PROBES = PROBES + MARGIN_PROBES


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


def probe(row: tuple[int, int, float, str], pivot_z: int = 25) -> tuple[str, dict]:
    radius, plane, pose, kind = row
    key = (f"r{radius}-y{plane}"
           f"{'-z'+str(pivot_z) if pivot_z != 25 else ''}"
           f"-t{pose:.2f}-{kind}")
    target = OUT / "probes" / f"{key}.stl"
    target.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", 'rb_part="probe"', "-D", f'rb_probe="{kind}"',
           "-D", f"rb_input_r={radius}", "-D", f"rb_plane_y={plane}",
           "-D", f"rb_pivot_z={pivot_z}", "-D", f"rb_t={pose}",
           "-o", str(target), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                         timeout=120)
    log = run.stdout + run.stderr
    if run.returncode == 1 and "Current top level object is empty" in log \
            and "WARNING:" not in log and "ERROR:" not in log:
        return key, {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log or not target.exists():
        return key, {"error": log[-1000:]}
    # OpenSCAD emits ASCII STL for these probes. Parse the signed volume via
    # the project-independent inspector, so contact faces are not collisions.
    check = subprocess.run(
        ["python3", str(INSPECT), str(target), "--json"],
        cwd=ROOT, text=True, capture_output=True, timeout=30)
    if check.returncode:
        return key, {"error": check.stderr[-1000:] + check.stdout[-1000:]}
    mesh = json.loads(check.stdout)
    volume = mesh["volume"]
    return key, {"occupied": volume > 1e-6, "volume_mm3": round(volume, 5),
                 "bounds": mesh["bounds"] if volume > 1e-6 else None}


def render(pose: float, name: str) -> dict:
    path = OUT / name
    path.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "--render", "--imgsize=1400,1000",
           "--camera=50,48,13,66,0,155,230",
           "-D", 'rb_part="context"', "-D", "rb_input_r=75",
           "-D", "rb_plane_y=62", "-D", f"rb_t={pose}",
           "-o", str(path), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                         timeout=120)
    log = run.stdout + run.stderr
    data = path.read_bytes() if path.exists() else b""
    if run.returncode or "WARNING:" in log or "ERROR:" in log \
            or data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24 \
            or struct.unpack(">II", data[16:24]) != (1400, 1000):
        return {"error": log[-1000:] or "Missing or invalid rendered image"}
    return {"file": str(path.relative_to(ROOT)), "sha256": sha(path),
            "pixels": [1400, 1000], "feeder_travel_mm": pose*20}


def main() -> int:
    side = json.loads(SIDE.read_text())
    envelope = json.loads(ENVELOPE.read_text())
    if side["status"] != "SIDE_BOLTED_ENDPOINT_CAP_GEOMETRY_PASS_UNRELEASED" \
            or side["promoted_to_selected_parts"] \
            or envelope["status"] != "SCHEMATIC_SELLER_ENVELOPE_SCREEN_ONLY" \
            or not envelope["candidates"]["d29-x85-y70"]["sampled_collision_free"]:
        raise RuntimeError("Upstream switch/motor proxy review changed")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probes").mkdir(exist_ok=True)
    tracked = sources(CAD) | {Path(__file__).resolve()}
    before = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    rows = [(r, y, t, kind) for r in RADII for y in PLANES
            for t in POSES for kind in PROBES]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(probe, rows))
        fine_rows = [(75, 62, t, kind) for t in FINE_POSES
                     if t not in POSES for kind in FINE_PROBES]
        fine_results = dict(pool.map(probe, fine_rows))
        selected_end_clearances = dict(pool.map(probe, [
            (75, 62, t, kind) for t in POSES for kind in MARGIN_PROBES]))
    controls = dict((probe((75, 62, 0, kind))) for kind in
                    ("bridge-tab-root", "visual-bridge-tab-root",
                     "positive-control"))
    old_clearance = dict([probe(
        (75, 62, 0, "bridge-fixed-clearance-2mm"), pivot_z=23)])
    images = {name: render(pose, name) for pose, name in
              ((0, "r75-y62-home.png"), (1, "r75-y62-full.png"))}
    after = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    candidates = []
    for radius in RADII:
        angle = math.asin(15/radius)
        pivot_x = 85-math.sqrt(radius*radius-15*15)
        output_r = radius*2/3
        pin_min = pivot_x+output_r*math.cos(angle)
        pin_max = pivot_x+output_r
        bridge_x = [pin_min-3.5-.4-3, pin_max+3.5+.4+3]
        for plane in PLANES:
            prefix = f"r{radius}-y{plane}-"
            collisions = [key for key, row in results.items()
                          if key.startswith(prefix) and row.get("occupied")]
            errors = [key for key, row in results.items()
                      if key.startswith(prefix) and row.get("error")]
            candidates.append({
                "input_radius_mm": radius,
                "output_radius_mm": output_r,
                "rocker_plane_y_mm": plane,
                "motor_proxy_axis_xy_mm": [85, 70],
                "pivot_xyz_mm": [round(pivot_x, 4), plane, 25],
                "half_swing_deg": round(math.degrees(angle), 4),
                "output_pin_x_range_mm": [round(pin_min, 4), round(pin_max, 4)],
                "minimum_solid_bridge_x_range_mm": [round(n, 4) for n in bridge_x],
                "bridge_y_range_mm": [35.5, plane-3.5],
                "bridge_z_range_at_home_mm": [8.1, 21.9],
                "integral_root_web_bottom_z_at_home_mm": 7.1,
                "collisions": collisions,
                "errors": errors,
                "sampled_clearance": not collisions and not errors,
            })
    failures = [name for name, row in results.items() if row.get("error")]
    failures += [name for name, row in fine_results.items()
                 if row.get("error") or row.get("occupied")]
    failures += [name for name, row in selected_end_clearances.items()
                 if row.get("error") or row.get("occupied")]
    failures += [name for name, row in old_clearance.items()
                 if row.get("error") or not row.get("occupied")]
    failures += [name for name, row in controls.items()
                 if row.get("error") or not row.get("occupied")]
    failures += [name for name, row in images.items() if row.get("error")]
    kinematic_residual = max(
        max(abs((23+75*math.sin(math.asin((30*t-15)/75)))-(8+30*t)),
            abs((23+50*math.sin(math.asin((30*t-15)/75)))-(13+20*t)))
        for t in FINE_POSES)
    if kinematic_residual > 1e-10:
        failures.append("30-to-20-mm kinematic identity drifted")
    if before != after:
        failures.append("source changed during review")
    report = {
        "status": "FAIL" if failures else "OUTPUT_BRIDGE_LAYOUT_SCREEN_ONLY",
        "source_sha256": before,
        "side_switch_review_sha256": sha(SIDE),
        "motor_envelope_review_sha256": sha(ENVELOPE),
        "screen_contract": {
            "input_full_stroke_mm": 30,
            "output_full_stroke_mm": 20,
            "same_side_rocker_ratio": 2/3,
            "angle_from_input_displacement": "asin((30*t-15)/input_radius)",
            "max_input_output_position_identity_residual_mm": kinematic_residual,
            "sampled_feeder_travel_mm": [0, 10, 20],
            "selected_fine_sampled_feeder_travel_mm": [i for i in range(21)],
            "motor_proxy": "seller-gallery full-length diameter-29-mm cylinder",
            "motor_proxy_z_shift_for_lifted_layout_mm": 2,
            "minimum_bridge_is_solid_occupied_envelope_not_a_slotted_part": True,
            "mount_pivot_motor_clevis_and_pin_retention_designed": False,
            "actual_motor_body_rod_and_force_verified": False,
            "selected_r75_y62_cap_top_to_bridge_bottom_nominal_mm": 2.7,
            "selected_r75_y62_dilated_neighbor_clearance_screen_mm": 2,
            "selected_r75_y62_motor_bridge_clearance_screen_mm": 5,
            "prior_z23_dilated_fixed_clearance_fails": True,
            "selected_r75_y62_motor_radial_gap_to_bridge_nominal_mm": round(
                math.hypot(85-((85-math.sqrt(75*75-15*15))+50+3.5+.4+3),
                           70-(62-3.5))-14.5, 4),
            "nominal_gap_is_not_print_or_dynamic_clearance": True,
        },
        "candidates": candidates,
        "probes": results,
        "selected_fine_probes": fine_results,
        "selected_end_clearance_probes": selected_end_clearances,
        "prior_z23_clearance_probe": old_clearance,
        "positive_controls": controls,
        "images": images,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    for row in candidates:
        print(f"R{row['input_radius_mm']:>2} Y{row['rocker_plane_y_mm']:>2}: "
              f"{'space-clear' if row['sampled_clearance'] else 'COLLISION'} "
              f"{len(row['collisions'])} occupied, {len(row['errors'])} errors")
    print(report["status"], "coarse probes", len(results),
          "fine probes", len(fine_results), "end clearances",
          len(selected_end_clearances), "failures", len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
