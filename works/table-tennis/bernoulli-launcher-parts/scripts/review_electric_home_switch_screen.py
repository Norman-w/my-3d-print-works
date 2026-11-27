#!/usr/bin/env python3
"""Screen an independent mechanical-zero switch beside the selected stop.

The switch, tab and their settings are candidate envelopes. This does not
design the adjustable bracket or validate an actual switch's click point.
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
CAD = ROOT / "cad/electric-home-switch-screen.scad"
OUT = ROOT / "output/electric-home-switch-screen"
INTEGRATION = ROOT / "output/electric-trigger-integration/review.json"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
POSES = (0, .05, .25, .5, .75, 1)  # u = 0,1,5,10,15,20 mm
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


def scalar(source: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(-?\d+(?:\.\d+)?);",
                      source, re.M)
    if not match:
        raise RuntimeError(f"Home-switch CAD parameter missing: {name}")
    return float(match.group(1))


def probe(kind: str, pose: float) -> tuple[str, dict]:
    tag = f"{kind}-t{pose:.2f}"
    destination = OUT / f"{tag}.stl"
    destination.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'hs_probe="{kind}"', "-D", f"hs_t={pose}",
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
           "--camera=60,32,3,65,0,145,300", "-D", 'hs_part="context"',
           "-D", f"hs_t={pose}", "-o", str(image), str(CAD)]
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
    integration = json.loads(INTEGRATION.read_text())
    if (integration["status"] != "SELECTED_TRIGGER_GEOMETRY_PASS_UNRELEASED"
            or integration["manufacturing_release"]):
        raise RuntimeError("Selected integrated trigger baseline missing")
    for name, expected in integration["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"Selected geometry changed: {name}")
    OUT.mkdir(parents=True, exist_ok=True)
    tracked = sources(CAD) | {Path(__file__).resolve()}
    before = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    cad_source = CAD.read_text()
    params = {name: scalar(cad_source, name) for name in
              ("hs_case_x", "hs_case_y", "hs_case_z", "hs_case_l",
               "hs_case_w", "hs_case_h", "hs_plunger_dx", "hs_tab_z0",
               "hs_tab_z1", "hs_tab_x0", "hs_tab_y0", "hs_tab_end_margin")}
    rows = [(kind, pose) for kind in CLEARANCE_KINDS for pose in POSES]
    rows += [("zero-contact", 0), ("one-mm-free-clearance", .05),
             ("tab-root-control", 0)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        probes = dict(pool.map(lambda row: probe(*row), rows))
    images = {name: render(pose, name) for pose, name in
              ((0, "home-context.png"), (.05, "one-mm-context.png"))}
    after = {str(path.relative_to(ROOT)): sha(path) for path in sorted(tracked)}
    failures = [tag for tag, row in probes.items() if row.get("error")]
    failures += [tag for tag, row in probes.items()
                 if tag.split("-t")[0] in CLEARANCE_KINDS and row.get("occupied")]
    for kind, pose, expected in (("zero-contact", 0, True),
                                 ("one-mm-free-clearance", .05, False),
                                 ("tab-root-control", 0, True)):
        tag = f"{kind}-t{pose:.2f}"
        if probes[tag].get("occupied") is not expected:
            failures.append(f"{tag}: wrong occupancy")
    failures += [name for name, row in images.items() if "error" in row]
    if before != after:
        failures.append("CAD source changed during review")

    # OP is 5.5 +/- 0.3 mm, with PT <=0.5, OT >=0.25 and MD <=0.12.
    # After measuring the actual switch, shift it vertically so the u=0 tab
    # depresses its OP by 0.10..0.20 mm. The bracket adjustment interval is
    # derived from catalogue extremes; this bracket has not been designed.
    tab_at_home = params["hs_tab_z0"]
    press_range = (.10, .20)
    op_range = (5.2, 5.8)
    case_z_range = (round(tab_at_home-op_range[1]-press_range[1], 3),
                    round(tab_at_home-op_range[0]-press_range[0], 3))
    shift_range = (round(case_z_range[0]-params["hs_case_z"], 3),
                   round(case_z_range[1]-params["hs_case_z"], 3))
    free_upper_after_calibration = tab_at_home+press_range[1]+.5
    release_gap_at_u1 = tab_at_home+1-free_upper_after_calibration
    if release_gap_at_u1 <= 0 or press_range[1] >= .25:
        failures.append("Catalogue switching window has no positive margin")
    if tab_at_home-5 < .5:
        failures.append("Tab lacks even nominal clearance over fixed guide")
    if abs(params["hs_case_z"]+5.5-tab_at_home-.15) > 1e-9:
        failures.append("Nominal switch and tab positions do not match")

    report = {
        "status": "HOME_SWITCH_PACKAGING_SCREEN_ONLY" if not failures else "FAIL",
        "source_sha256": before,
        "integrated_trigger_review_sha256": sha(INTEGRATION),
        "catalogue": {
            "part_candidate": "Omron D2F-01F-D3 pin plunger",
            "url": "https://omronfs.omron.com/en_US/ecb/products/pdf/en-d2f.pdf",
            "case_envelope_mm": [params["hs_case_l"], params["hs_case_w"],
                                 params["hs_case_h"]],
            "operating_position_from_case_datum_mm": [5.2, 5.8],
            "pretravel_max_mm": .5, "overtravel_min_mm": .25,
            "movement_differential_max_mm": .12,
            "operating_force_max_N": .74,
            "mechanical_frequency_limit_operations_per_min": 200,
            "electrical_rating_test_frequency_operations_per_min": 30,
        },
        "candidate_geometry": {
            "feeder_axis": "+Z", "mechanical_home_travel_mm": 0,
            "tab_bottom_z_at_home_mm": tab_at_home,
            "fixed_guide_top_z_mm": 5,
            "nominal_gap_over_fixed_stop_mm": tab_at_home-5,
            "switch_case_xyz_min_mm": [params["hs_case_x"],
                                       params["hs_case_y"], params["hs_case_z"]],
            "switch_case_xyz_max_mm": [params["hs_case_x"]+params["hs_case_l"],
                                       params["hs_case_y"]+params["hs_case_w"],
                                       params["hs_case_z"]+params["hs_case_h"]],
            "tab_xyz_at_home_mm": [
                [params["hs_tab_x0"], params["hs_tab_y0"], params["hs_tab_z0"]],
                [params["hs_case_x"]+params["hs_plunger_dx"]+params["hs_tab_end_margin"],
                 params["hs_case_y"]+params["hs_case_w"]/2+params["hs_tab_end_margin"],
                 params["hs_tab_z1"]]],
            "tab_root_overlaps_existing_upper_shoulder": probes["tab-root-control-t0.00"].get("occupied"),
            "upper_shoulder_and_fixed_guide_continue_to_carry_stop_load": True,
        },
        "catalogue_only_calibration_window": {
            "intended_press_past_actual_OP_at_home_mm": list(press_range),
            "required_absolute_case_z_datum_mm": list(case_z_range),
            "required_case_z_shift_from_nominal_mm": list(shift_range),
            "max_free_plunger_height_after_calibration_mm": free_upper_after_calibration,
            "one_mm_return_nominal_release_gap_min_mm": round(release_gap_at_u1, 3),
            "requires_actual_switch_click_and_mechanical_stop_calibration": True,
        },
        "pose_travel_mm": [round(p*20, 4) for p in POSES],
        "probe_count": len(rows), "probes": probes, "images": images,
        "mounting_bracket_designed": False,
        "full_stroke_sensor_designed": False,
        "real_switch_in_hand": False,
        "real_motor_stopping_position_measured": False,
        "case_terminal_and_wire_clearance_physically_verified": False,
        "manufacturing_release": False, "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False,
                                                 indent=2) + "\n")
    print(f"Independent home-switch packaging screen: {len(rows)} probes, "
          f"{len(failures)} errors")
    for failure in failures:
        print("  ERROR " + failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
