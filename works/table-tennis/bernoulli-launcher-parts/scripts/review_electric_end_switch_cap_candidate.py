#!/usr/bin/env python3
"""Review a replaceable right guide cap carrying two adjustable D2F switches.

The seller motor and catalogue switch envelopes are only packaging proxies.
Passing this screen does not promote the cap/tabs to the selected inventory.
"""

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
CAD = ROOT / "cad/electric-end-switch-cap-candidate.scad"
OUT = ROOT / "output/electric-end-switch-cap-candidate"
HOME = ROOT / "output/electric-home-switch-screen/review.json"
FULL = ROOT / "output/electric-full-stroke-switch-screen/review.json"
ENVELOPE = ROOT / "output/by141-envelope-screen/review.json"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
POSES = (0, .05, .25, .5, .75, 1)
CLEARANCE = (
    "cap-other-fixed", "cap-moving", "cap-hardware", "cap-motor-envelope",
    "cap-service-tools", "switch-cap", "switch-selected", "switch-hardware",
    "switch-motor-envelope", "tab-fixed", "tab-other-moving",
    "tab-hardware", "tab-cap",
)


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


def build(part: str, destination: Path, pose: float = 0,
          probe: str = "", shift: float = 0,
          motor_y: int = 70) -> tuple[bool, str]:
    destination.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'es_part="{part}"', "-D", f'es_probe="{probe}"',
           "-D", f"es_t={pose}", "-D", f"es_switch_shift_z={shift}",
           "-D", f"es_motor_y={motor_y}",
           "-o", str(destination), str(CAD)]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                            timeout=120)
    log = result.stdout + result.stderr
    if (result.returncode == 1 and "Current top level object is empty" in log
            and "WARNING:" not in log and "ERROR:" not in log):
        return False, ""
    if result.returncode or "WARNING:" in log or "ERROR:" in log:
        return False, log[-1400:]
    return True, ""


def inspect(path: Path) -> dict:
    result = subprocess.run([sys.executable, str(INSPECT), str(path),
                             "--json", "--require-watertight"], cwd=ROOT,
                            text=True, capture_output=True, timeout=60)
    if result.returncode:
        return {"error": result.stdout[-1000:] + result.stderr[-1000:]}
    mesh = json.loads(result.stdout)
    return {"occupied": mesh["volume"] > 1e-9,
            "volume_mm3": mesh["volume"],
            "bounds": mesh["bounds"], "stl_sha256": sha(path)}


def inspect_intersection(path: Path) -> dict:
    # Manifold may write coincident contact faces as a zero-volume STL. Those
    # are allowed face contacts, but any real occupied overlap still receives
    # the strict watertight inspection above.
    result = subprocess.run([sys.executable, str(INSPECT), str(path), "--json"],
                            cwd=ROOT, text=True, capture_output=True,
                            timeout=60)
    if result.returncode:
        return {"error": result.stdout[-1000:] + result.stderr[-1000:]}
    mesh = json.loads(result.stdout)
    if mesh["volume"] < 1e-6:
        return {"occupied": False, "volume_mm3": 0,
                "contact_faces_only": True}
    return inspect(path)


def probe(row: tuple[str, float, float, int]) -> tuple[str, dict]:
    kind, pose, shift, motor_y = row
    name = f"{kind}-t{pose:.2f}-s{shift:+.2f}-y{motor_y}"
    path = OUT / f"{name}.stl"
    occupied, error = build("probe", path, pose, kind, shift, motor_y)
    if error:
        return name, {"error": error}
    return name, inspect_intersection(path) if occupied else {"occupied": False,
                                                               "volume_mm3": 0}


def render(pose: float, name: str) -> dict:
    path = OUT / name
    path.unlink(missing_ok=True)
    size = (1400, 1000)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "--render", f"--imgsize={size[0]},{size[1]}",
           "--camera=64,52,-28,66,0,155,330", "-D", 'es_part="context"',
           "-D", f"es_t={pose}", "-o", str(path), str(CAD)]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                            timeout=120)
    log = result.stdout + result.stderr
    data = path.read_bytes() if path.exists() else b""
    if (result.returncode or "WARNING:" in log or "ERROR:" in log
            or data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24
            or struct.unpack(">II", data[16:24]) != size):
        return {"error": log[-1500:] or "Missing/invalid context PNG"}
    return {"file": str(path.relative_to(ROOT)), "sha256": sha(path),
            "pixels": list(size), "feeder_travel_mm": pose*20}


def main() -> int:
    home = json.loads(HOME.read_text())
    full = json.loads(FULL.read_text())
    envelope = json.loads(ENVELOPE.read_text())
    if (home["status"] != "HOME_SWITCH_PACKAGING_SCREEN_ONLY"
            or full["status"] != "FULL_STROKE_SWITCH_PACKAGING_SCREEN_ONLY"
            or full["home_switch_review_sha256"] != sha(HOME)
            or envelope["status"] != "SCHEMATIC_SELLER_ENVELOPE_SCREEN_ONLY"
            or not envelope["candidates"]["d29-x85-y63"]["sampled_collision_free"]
            or not envelope["candidates"]["d29-x85-y70"]["sampled_collision_free"]):
        raise RuntimeError("Prior switch or motor packaging screen changed")
    OUT.mkdir(parents=True, exist_ok=True)
    tracked = sources(CAD) | {Path(__file__).resolve()}
    before = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    parts = {}
    for part in ("cap", "home-tab", "full-tab"):
        path = OUT / f"{part}.stl"
        occupied, error = build(part, path)
        parts[part] = {"error": error} if error or not occupied else inspect(path)
        if "error" not in parts[part]:
            parts[part]["file"] = str(path.relative_to(ROOT))
    rows = [(kind, pose, 0, 70) for kind in CLEARANCE for pose in POSES]
    rows.extend((kind, pose, shift, 70)
                for kind in ("switch-cap", "switch-selected",
                             "switch-motor-envelope", "tab-cap")
                for pose in (0, 1) for shift in (-.8, .8))
    rows.extend((kind, pose, 0, 70) for kind, pose in
                (("tab-root-control", 0), ("tab-root-control", 1),
                 ("mount-slot-control", 0), ("cap-self-control", 0)))
    rows.extend((kind, pose, 0, 63)
                for kind in ("cap-motor-envelope", "switch-motor-envelope")
                for pose in (0, 1))
    rows.extend(("switch-tool-motor", 0, 0, motor_y)
                for motor_y in (63, 70))
    with ThreadPoolExecutor(max_workers=4) as pool:
        probes = dict(pool.map(probe, rows))
    images = {name: render(pose, name) for pose, name in
              ((0, "at-home.png"), (1, "at-full.png"))}
    after = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    failures = [name for name, row in probes.items() if row.get("error")]
    failures += [name for name, row in probes.items()
                 if name.split("-t")[0] in CLEARANCE and row.get("occupied")]
    blocked_tool_axes = [name for name, row in probes.items()
                         if name.startswith("switch-tool-motor") and row.get("occupied")]
    for kind, pose, expected in (("tab-root-control", 0, True),
                                 ("tab-root-control", 1, True),
                                 ("mount-slot-control", 0, False),
                                 ("cap-self-control", 0, True)):
        name = f"{kind}-t{pose:.2f}-s+0.00-y70"
        if probes[name].get("occupied") is not expected:
            failures.append(f"{name}: wrong occupancy")
    failures += [name for name, row in parts.items()
                 if row.get("error") or not row.get("occupied")]
    failures += [name for name, row in images.items() if row.get("error")]
    if before != after:
        failures.append("source changed during review")
    report = {
        "status": ("FAIL" if failures else
                   "REJECTED_MOTOR_BLOCKS_SWITCH_ADJUSTMENT"
                   if blocked_tool_axes else
                   "ENDPOINT_CAP_CANDIDATE_GEOMETRY_PASS_UNRELEASED"),
        "source_sha256": before,
        "home_switch_review_sha256": sha(HOME),
        "full_switch_review_sha256": sha(FULL),
        "motor_envelope_review_sha256": sha(ENVELOPE),
        "catalogue_switch_url": home["catalogue"]["url"],
        "geometry": {
            "replaced_selected_part": "right Y guide cap only",
            "switch_case_x_at_nominal_mm": [68,80.8],
            "switch_y_at_nominal_mm": [42,47.8],
            "home_switch_mount_holes_x_mm": [71.15,77.65],
            "home_switch_mount_holes_z_mm": 1.95,
            "full_switch_mount_holes_z_mm": -31.95,
            "switch_z_adjustment_each_way_mm": .8,
            "nominal_motor_envelope_radial_gap_to_switch_box_mm": {
                "axis_85_63": round(((85-80.8)**2+(63-47.8)**2)**.5-14.5, 4),
                "axis_85_70": round(((85-80.8)**2+(70-47.8)**2)**.5-14.5, 4),
            },
            "examined_motor_axis_xy_mm": [85,70],
            "adjustment_tool_blocked_by_motor_envelope": blocked_tool_axes,
            "motor_envelope_is_seller_proxy": True,
            "old_guide_screw_axes_and_hard_stops_unchanged": True,
            "M2_nut_footprint_only_not_purchased": True,
        },
        "part_meshes": parts,
        "pose_travel_mm": [round(p*20, 4) for p in POSES],
        "probe_count": len(rows), "probes": probes, "images": images,
        "service_access_pass": not blocked_tool_axes,
        "actual_M2_fasteners_and_nut_installation_verified": False,
        "tab_stiffness_and_switch_click_measured": False,
        "motor_wire_and_mount_clearance_verified": False,
        "promoted_to_selected_parts": False,
        "manufacturing_release": False, "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False,
                                                 indent=2) + "\n")
    print(f"Endpoint-cap candidate: {len(rows)} probes, {len(failures)} errors; "
          f"service-tool/motor overlaps: {len(blocked_tool_axes)}")
    for failure in failures:
        print("  ERROR " + failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
