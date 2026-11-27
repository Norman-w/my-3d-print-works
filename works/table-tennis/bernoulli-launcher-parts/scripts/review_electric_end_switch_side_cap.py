#!/usr/bin/env python3
"""Review side-bolted endpoint switches on a replaceable right guide cap.

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
CAD = ROOT / "cad/electric-end-switch-side-cap.scad"
OUT = ROOT / "output/electric-end-switch-side-cap"
HOME = ROOT / "output/electric-home-switch-screen/review.json"
FULL = ROOT / "output/electric-full-stroke-switch-screen/review.json"
ENVELOPE = ROOT / "output/by141-envelope-screen/review.json"
REJECTED = ROOT / "output/electric-end-switch-cap-candidate/review.json"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
POSES = (0, .05, .25, .5, .75, 1)
CLEARANCE = (
    "cap-other-fixed", "cap-moving", "cap-hardware", "cap-motor",
    "cap-motor-removal",
    "cap-service-tools", "switch-cap", "switch-selected", "switch-hardware",
    "switch-motor", "switch-tool-motor", "switch-tool-selected",
    "fasteners-cap", "fasteners-selected", "fasteners-hardware",
    "fasteners-motor", "fasteners-tab",
    "tab-fixed", "tab-other-moving", "tab-hardware", "tab-cap",
    "tab-switch-case",
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
          probe: str = "", home_shift: float = 0,
          full_shift: float = 0,
          motor_y: int = 63) -> tuple[bool, str]:
    destination.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'ss_part="{part}"', "-D", f'ss_probe="{probe}"',
           "-D", f"ss_t={pose}",
           "-D", f"ss_home_shift_z={home_shift}",
           "-D", f"ss_full_shift_z={full_shift}",
           "-D", f"ss_motor_y={motor_y}",
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
            "bounds": mesh["bounds"],
            "triangle_count": mesh["triangleCount"],
            "watertight": mesh["watertightByEdgeTopology"],
            "stl_sha256": sha(path)}


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


def probe(row: tuple[str, float, float, float, int]) -> tuple[str, dict]:
    kind, pose, home_shift, full_shift, motor_y = row
    name = (f"{kind}-t{pose:.2f}-h{home_shift:+.2f}"
            f"-f{full_shift:+.2f}-y{motor_y}")
    path = OUT / f"{name}.stl"
    occupied, error = build("probe", path, pose, kind,
                            home_shift, full_shift, motor_y)
    if error:
        return name, {"error": error}
    return name, inspect_intersection(path) if occupied else {"occupied": False,
                                                               "volume_mm3": 0}


def render(pose: float, name: str, detail: bool = False) -> dict:
    path = OUT / name
    path.unlink(missing_ok=True)
    size = (1400, 1000)
    camera = ("66,38,-15,68,0,155,190" if detail else
              "64,52,-28,66,0,155,330")
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "--render", f"--imgsize={size[0]},{size[1]}",
           f"--camera={camera}", "-D", 'ss_part="context"',
           "-D", f"ss_t={pose}",
           "-D", f"ss_show_motor={'false' if detail else 'true'}",
           "-o", str(path), str(CAD)]
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
    rejected = json.loads(REJECTED.read_text())
    if (home["status"] != "HOME_SWITCH_PACKAGING_SCREEN_ONLY"
            or full["status"] != "FULL_STROKE_SWITCH_PACKAGING_SCREEN_ONLY"
            or full["home_switch_review_sha256"] != sha(HOME)
            or envelope["status"] != "SCHEMATIC_SELLER_ENVELOPE_SCREEN_ONLY"
            or not envelope["candidates"]["d29-x85-y63"]["sampled_collision_free"]
            or rejected["status"] != "REJECTED_MOTOR_BLOCKS_SWITCH_ADJUSTMENT"
            or rejected["service_access_pass"]):
        raise RuntimeError("Prior switch or motor packaging screen changed")
    OUT.mkdir(parents=True, exist_ok=True)
    tracked = sources(CAD) | {Path(__file__).resolve()}
    before = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    parts = {}
    for part in ("cap", "carriage", "home-tab", "full-tab"):
        path = OUT / f"{part}.stl"
        occupied, error = build(part, path)
        parts[part] = {"error": error} if error or not occupied else inspect(path)
        if "error" not in parts[part]:
            parts[part]["file"] = str(path.relative_to(ROOT))
    rows = [(kind, pose, 0, 0, 63) for kind in CLEARANCE for pose in POSES]
    rows.extend((kind, pose, home_shift, full_shift, 63)
                for kind in ("switch-cap", "switch-selected",
                             "switch-motor", "switch-tool-motor",
                             "fasteners-cap", "fasteners-selected",
                             "fasteners-motor", "fasteners-tab",
                             "tab-cap", "tab-switch-case")
                for pose in (0, 1)
                for home_shift in (-.75, .15)
                for full_shift in (-.15, .75))
    rows.extend((kind, pose, 0, 0, 63) for kind, pose in
                (("tab-root-control", 0), ("tab-root-control", 1),
                 ("nominal-contact-control", 0),
                 ("nominal-contact-control", 1),
                 ("old-cap-preserved", 0),
                 ("old-carriage-preserved", 0),
                 ("old-carriage-preserved", 1),
                 ("mount-slot-control", 0), ("cap-self-control", 0)))
    rows.extend((kind, pose, 0, 0, 70)
                for kind in ("cap-motor", "switch-motor", "switch-tool-motor")
                for pose in (0, 1))
    with ThreadPoolExecutor(max_workers=4) as pool:
        probes = dict(pool.map(probe, rows))
    images = {name: render(pose, name, detail) for pose, name, detail in
              ((0, "at-home.png", False), (1, "at-full.png", False),
               (0, "at-home-detail.png", True),
               (1, "at-full-detail.png", True))}
    after = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    failures = [name for name, row in probes.items() if row.get("error")]
    failures += [name for name, row in probes.items()
                 if name.split("-t")[0] in CLEARANCE and row.get("occupied")]
    blocked_tool_axes = [name for name, row in probes.items()
                         if name.startswith("switch-tool-motor") and row.get("occupied")]
    for kind, pose, expected in (("tab-root-control", 0, True),
                                 ("tab-root-control", 1, True),
                                 ("nominal-contact-control", 0, True),
                                 ("nominal-contact-control", 1, True),
                                 ("old-cap-preserved", 0, False),
                                 ("old-carriage-preserved", 0, False),
                                 ("old-carriage-preserved", 1, False),
                                 ("mount-slot-control", 0, False),
                                 ("cap-self-control", 0, True)):
        name = f"{kind}-t{pose:.2f}-h+0.00-f+0.00-y63"
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
                   "SIDE_BOLTED_ENDPOINT_CAP_GEOMETRY_PASS_UNRELEASED"),
        "source_sha256": before,
        "home_switch_review_sha256": sha(HOME),
        "full_switch_review_sha256": sha(FULL),
        "motor_envelope_review_sha256": sha(ENVELOPE),
        "rejected_front_bolt_review_sha256": sha(REJECTED),
        "catalogue_switch_url": home["catalogue"]["url"],
        "geometry": {
            "replaced_selected_parts": ["right Y guide cap", "moving feeder frame"],
            "new_tabs_are_integral_with_the_existing_moving_frame": True,
            "switch_case_x_at_nominal_mm": [70,75.8],
            "switch_y_at_nominal_mm": [35,47.8],
            "home_switch_mount_holes_y_mm": [38.15,44.65],
            "home_switch_mount_holes_z_mm": 1.95,
            "full_switch_mount_holes_z_mm": -31.95,
            "home_switch_required_case_shift_z_mm": [-.65,.05],
            "full_switch_required_case_shift_z_mm": [-.05,.65],
            "printed_home_slot_allowed_case_shift_z_mm": [-.75,.15],
            "printed_full_slot_allowed_case_shift_z_mm": [-.15,.75],
            "slot_end_extra_calibration_allowance_mm": .1,
            "M2_reference_nut_across_flats_mm": 4,
            "M2_reference_nut_thickness_mm": 1.2,
            "M2_reference_screw_length_mm": 10,
            "M2_nominal_thread_protrusion_past_nut_mm": .7,
            "M2_nut_dimensions_source_url": "https://www.accu.co.uk/thin-hexagon-nuts/73046-HFN-M2-A2",
            "nominal_motor_envelope_radial_gap_to_switch_box_mm": {
                "axis_85_63": round(((85-75.8)**2+(63-47.8)**2)**.5-14.5, 4),
                "axis_85_70": round(((85-75.8)**2+(70-47.8)**2)**.5-14.5, 4),
            },
            "examined_motor_axis_xy_mm": [85,63],
            "nominal_cap_removal_radial_x_margin_to_29mm_cylinder_mm": .5,
            "cap_removal_clearance_tolerance_verified": False,
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
