#!/usr/bin/env python3
"""Screen a second endpoint switch beside the existing full-stroke stop."""

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
CAD = ROOT / "cad/electric-full-stroke-switch-screen.scad"
OUT = ROOT / "output/electric-full-stroke-switch-screen"
HOME = ROOT / "output/electric-home-switch-screen/review.json"
INTEGRATION = ROOT / "output/electric-trigger-integration/review.json"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
POSES = (0, .05, .25, .5, .75, 1)
CLEARANCE_KINDS = ("switch-fixed", "switch-moving", "switch-hardware",
                   "tab-fixed", "tab-hardware")


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


def probe(kind: str, pose: float) -> tuple[str, dict]:
    tag = f"{kind}-t{pose:.2f}"
    destination = OUT / f"{tag}.stl"
    destination.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'fs_probe="{kind}"', "-D", f"fs_t={pose}",
           "-o", str(destination), str(CAD)]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=120)
    log = result.stdout + result.stderr
    if (result.returncode == 1 and "Current top level object is empty" in log
            and "WARNING:" not in log and "ERROR:" not in log):
        return tag, {"occupied": False, "volume_mm3": 0}
    if result.returncode or "WARNING:" in log or "ERROR:" in log:
        return tag, {"error": log[-1400:]}
    inspected = subprocess.run([sys.executable, str(INSPECT), str(destination),
                                "--json", "--require-watertight"], cwd=ROOT,
                               text=True, capture_output=True, timeout=60)
    if inspected.returncode:
        return tag, {"error": inspected.stdout[-1000:] + inspected.stderr[-1000:]}
    mesh = json.loads(inspected.stdout)
    return tag, {"occupied": mesh["volume"] > 1e-9,
                 "volume_mm3": mesh["volume"],
                 "bounds": mesh["bounds"], "stl_sha256": sha(destination)}


def render(pose: float, name: str) -> dict:
    image = OUT / name
    image.unlink(missing_ok=True)
    size = (1400, 1000)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "--render", f"--imgsize={size[0]},{size[1]}",
           "--camera=60,32,-34,65,0,145,300", "-D", 'fs_part="context"',
           "-D", f"fs_t={pose}", "-o", str(image), str(CAD)]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                            timeout=120)
    log = result.stdout + result.stderr
    data = image.read_bytes() if image.exists() else b""
    if (result.returncode or "WARNING:" in log or "ERROR:" in log
            or data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24
            or struct.unpack(">II", data[16:24]) != size):
        return {"error": log[-1500:] or "Missing/invalid context PNG"}
    return {"file": str(image.relative_to(ROOT)), "sha256": sha(image),
            "pixels": list(size), "feeder_travel_mm": pose*20}


def main() -> int:
    home = json.loads(HOME.read_text())
    integration = json.loads(INTEGRATION.read_text())
    if (home["status"] != "HOME_SWITCH_PACKAGING_SCREEN_ONLY"
            or integration["status"] != "SELECTED_TRIGGER_GEOMETRY_PASS_UNRELEASED"
            or home["integrated_trigger_review_sha256"] != sha(INTEGRATION)
            or home["mounting_bracket_designed"]):
        raise RuntimeError("Current home-switch or integrated assembly screen missing")
    for name, expected in home["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"Home-switch source changed: {name}")
    OUT.mkdir(parents=True, exist_ok=True)
    tracked = sources(CAD) | {Path(__file__).resolve()}
    before = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    rows = [(kind, pose) for kind in CLEARANCE_KINDS for pose in POSES]
    rows += [("full-contact", 1), ("one-mm-before-free-clearance", .95),
             ("tab-root-control", 1), ("home-switch-separation", 1)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        probes = dict(pool.map(lambda row: probe(*row), rows))
    images = {name: render(pose, name) for pose, name in
              ((1, "full-context.png"), (.95, "one-mm-before-context.png"))}
    after = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    failures = [tag for tag, row in probes.items() if row.get("error")]
    failures += [tag for tag, row in probes.items()
                 if tag.split("-t")[0] in CLEARANCE_KINDS and row.get("occupied")]
    for kind, pose, expected in (("full-contact", 1, True),
                                 ("one-mm-before-free-clearance", .95, False),
                                 ("tab-root-control", 1, True),
                                 ("home-switch-separation", 1, False)):
        tag = f"{kind}-t{pose:.2f}"
        if probes[tag].get("occupied") is not expected:
            failures.append(f"{tag}: wrong occupancy")
    failures += [name for name, row in images.items() if "error" in row]
    if before != after:
        failures.append("source changed during review")

    home_geo = home["candidate_geometry"]
    home_case_min = home_geo["switch_case_xyz_min_mm"]
    home_case_max = home_geo["switch_case_xyz_max_mm"]
    home_tab_min, home_tab_max = home_geo["tab_xyz_at_home_mm"]
    mirror = lambda z: -30-z
    report = {
        "status": "FULL_STROKE_SWITCH_PACKAGING_SCREEN_ONLY" if not failures else "FAIL",
        "source_sha256": before,
        "home_switch_review_sha256": sha(HOME),
        "integrated_trigger_review_sha256": sha(INTEGRATION),
        "catalogue_part_candidate": home["catalogue"]["part_candidate"],
        "catalogue_source_url": home["catalogue"]["url"],
        "candidate_geometry": {
            "feeder_axis": "+Z", "full_stroke_travel_mm": 20,
            "fixed_guide_bottom_z_mm": -35,
            "tab_top_z_at_full_mm": mirror(home_tab_min[2]),
            "nominal_gap_below_fixed_stop_mm":
                -35-mirror(home_tab_min[2]),
            "switch_case_xyz_min_mm": [home_case_min[0], home_case_min[1],
                                       mirror(home_case_max[2])],
            "switch_case_xyz_max_mm": [home_case_max[0], home_case_max[1],
                                       mirror(home_case_min[2])],
            "tab_xyz_at_full_mm": [
                [home_tab_min[0], home_tab_min[1], mirror(home_tab_max[2])],
                [home_tab_max[0], home_tab_max[1], mirror(home_tab_min[2])]],
            "lower_shoulder_and_fixed_guide_continue_to_carry_stop_load": True,
        },
        "catalogue_only_calibration_window": {
            "intended_press_past_actual_OP_at_full_mm":
                home["catalogue_only_calibration_window"]["intended_press_past_actual_OP_at_home_mm"],
            "one_mm_before_full_nominal_release_gap_min_mm":
                home["catalogue_only_calibration_window"]["one_mm_return_nominal_release_gap_min_mm"],
            "requires_actual_switch_click_and_mechanical_stop_calibration": True,
        },
        "pose_travel_mm": [round(p*20, 4) for p in POSES],
        "probe_count": len(rows), "probes": probes, "images": images,
        "mounting_bracket_designed": False,
        "moving_tab_promoted_to_selected_carriage": False,
        "switches_electrically_wired": False,
        "real_motor_stopping_position_measured": False,
        "manufacturing_release": False, "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False,
                                                 indent=2) + "\n")
    print(f"Full-stroke switch packaging screen: {len(rows)} probes, "
          f"{len(failures)} errors")
    for failure in failures:
        print("  ERROR " + failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
