#!/usr/bin/env python3
"""Check M2 mounting, washer thickness, and two-sided calibration access."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electronic-trigger-fastener-access-screen.scad"
OUT = ROOT / "output/electronic-trigger-fastener-access"
TRIGGER = ROOT / "output/electronic-trigger-candidate/review.json"
INTEGRATION = ROOT / "output/electric-trigger-integration/review.json"
TRIGGER_CAD = ROOT / "cad/electronic-trigger-candidate.scad"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
SHIFTS = (-1.4, 0, 1.4)
ANGLES = (0, -8)
FEED = (0, .5, 1)
STATIC = (
    "shaft-mount", "shaft-switch", "head-beam", "head-other-fixed",
    "nut-beam", "nut-other-fixed", "nut-terminals", "driver-beam",
    "driver-other-fixed", "nut-tool-beam", "nut-tool-other-fixed",
    "nut-tool-terminals",
)
LEVER = (
    "shaft-lever", "head-lever", "nut-lever", "driver-lever",
    "nut-tool-lever",
)
MOVING = ("head-moving", "nut-moving", "driver-moving", "nut-tool-moving")
SWITCH_CASE_THICKNESS_NOMINAL_MM = 5.8
SWITCH_CASE_THICKNESS_CATALOG_TOLERANCE_MM = .15
SWITCH_HOLE_PITCH_CATALOG_TOLERANCE_MM = .15
WIDE_WASHER_MIN_OD_MM = 6.64
SWITCH_CATALOG_URL = (
    "https://components.omron.com/eu-en/sites/components.omron.com.eu/"
    "files/datasheet_pdf/B036-E1.pdf")


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def scalar(source: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(-?\d+(?:\.\d+)?)\s*;",
                      source, re.M)
    if not match:
        raise RuntimeError(f"Missing CAD scalar: {name}")
    return float(match.group(1))


def washer_supported_area_mm2(*, screw_x: float, slot_x_min: float,
                              slot_x_max: float, slot_d: float,
                              washer_od: float) -> float:
    """Raster area of washer over solid backplate, excluding its long slot."""
    step = .02
    radius = washer_od / 2
    count = round(washer_od / step)
    solid_samples = 0
    for ix in range(count):
        x = screw_x-radius+(ix+.5)*step
        dx_slot = max(slot_x_min-x, 0, x-slot_x_max)
        for iz in range(count):
            z = -radius+(iz+.5)*step
            if (x-screw_x)**2+z*z > radius**2:
                continue
            if dx_slot**2+z*z >= (slot_d/2)**2:
                solid_samples += 1
    return round(solid_samples*step*step, 2)


def source_closure(path: Path, found: set[Path] | None = None) -> set[Path]:
    found = found if found is not None else set()
    path = path.resolve()
    if path in found:
        return found
    found.add(path)
    for name in re.findall(r"\b(?:use|include)\s*<([^>]+)>", path.read_text()):
        source_closure(path.parent / name, found)
    return found


def command(target: Path, *, part: str, probe: str = "", shift: float = 0,
            angle: float = 0, feed: float = 0) -> subprocess.CompletedProcess[str]:
    target.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'fa_part="{part}"', "-D", f"fa_shift={shift}",
           "-D", f"et_switch_shift={shift}", "-D", f"fa_angle={angle}",
           "-D", f"fa_feed={feed}"]
    if probe:
        cmd += ["-D", f'fa_probe="{probe}"']
    if target.suffix == ".png":
        cmd += ["--render", "--imgsize=1400,1000",
                "--camera=52,-51,-8,72,0,148,120"]
    cmd += ["-o", str(target), str(CAD)]
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=120)


def inspect_volume(path: Path) -> dict:
    run = subprocess.run(["python3", str(INSPECT), str(path), "--json"],
                         cwd=ROOT, text=True, capture_output=True, timeout=30)
    if run.returncode:
        return {"error": (run.stdout + run.stderr)[-900:]}
    row = json.loads(run.stdout)
    return {"volume_mm3": round(row["volume"], 6),
            "bounds_mm": row["bounds"]}


def run_probe(case: tuple[str, float, float, float]) -> tuple[str, dict]:
    kind, shift, angle, feed = case
    name = f"{kind}-s{shift:+g}-a{angle:+g}-t{feed:g}"
    path = OUT / "probes" / f"{name}.stl"
    run = command(path, part="probe", probe=kind, shift=shift,
                  angle=angle, feed=feed)
    log = run.stdout + run.stderr
    if run.returncode == 1 and "Current top level object is empty" in log \
            and "WARNING:" not in log and "ERROR:" not in log:
        return name, {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log or not path.is_file():
        return name, {"error": log[-900:]}
    row = inspect_volume(path)
    row["occupied"] = row.get("volume_mm3", 0) > 1e-5
    return name, row


def main() -> int:
    trigger = json.loads(TRIGGER.read_text())
    integration = json.loads(INTEGRATION.read_text())
    if trigger["status"] != "TRIGGER_CANDIDATE_GEOMETRY_PASS_UNRELEASED" \
            or integration["status"] != "SELECTED_TRIGGER_GEOMETRY_PASS_UNRELEASED" \
            or integration["trigger_geometry_review_sha256"] != sha(TRIGGER):
        raise RuntimeError("Selected trigger predecessor is missing or stale")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probes").mkdir(exist_ok=True)
    sources = source_closure(CAD) | {Path(__file__).resolve()}
    before = {str(p.relative_to(ROOT)): sha(p) for p in sorted(sources)}
    cases = [(kind, shift, 0, 0) for shift in SHIFTS for kind in STATIC]
    cases += [(kind, shift, angle, 0) for shift in SHIFTS
              for angle in ANGLES for kind in LEVER]
    cases += [(kind, shift, 0, feed) for shift in SHIFTS
              for feed in FEED for kind in MOVING]
    cases += [(kind, 0, 0, 0)
              for kind in ("head-self-control", "washer-self-control")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        probes = dict(pool.map(run_probe, cases))
    failures = [name for name, row in probes.items()
                if "error" in row or row.get("occupied") !=
                name.startswith(("head-self-control", "washer-self-control"))]
    image = OUT / "fastener-access.png"
    run = command(image, part="context")
    if run.returncode or "WARNING:" in run.stdout + run.stderr \
            or "ERROR:" in run.stdout + run.stderr or not image.is_file():
        failures.append("context-render")
    after = {str(p.relative_to(ROOT)): sha(p) for p in sorted(sources)}
    if after != before:
        failures.append("source-changed-during-review")
    trigger_source = TRIGGER_CAD.read_text()
    fastener_source = CAD.read_text()
    slot_d = scalar(trigger_source, "et_switch_slot_d")
    washer_od = scalar(fastener_source, "fa_washer_od")
    washer_thickness = round(scalar(fastener_source, "fa_plate_rear_y")
                             - scalar(fastener_source, "fa_shank_start_y"), 3)
    head_height = round(scalar(fastener_source, "fa_shank_start_y")
                        - scalar(fastener_source, "fa_head_top_y"), 3)
    if (abs(washer_thickness-.9) > 1e-6 or head_height != 2
            or washer_od != 7 or slot_d != 2.8):
        failures.append("slot-or-washer-departed-from-reviewed-candidate")
    screw_x = (scalar(trigger_source, "et_switch_x")
               + scalar(trigger_source, "et_switch_hole_x_offset"))
    slot_x_min = scalar(trigger_source, "et_switch_slot_x_min")
    slot_x_max = scalar(trigger_source, "et_switch_slot_x_max")
    supported_area = {
        f"switch_shift_{shift:+g}_mm": washer_supported_area_mm2(
            screw_x=screw_x+shift, slot_x_min=slot_x_min,
            slot_x_max=slot_x_max, slot_d=slot_d,
            washer_od=WIDE_WASHER_MIN_OD_MM)
        for shift in SHIFTS}
    # Under-head length includes the washer's actual modeled 0.9-mm thickness.
    # Catalog case tolerance alone reduces protrusion by up to 0.15 mm;
    # screw, washer, nut, and FDM tolerances are not yet bounded.
    stack_mm = round(washer_thickness + 4
                     + SWITCH_CASE_THICKNESS_NOMINAL_MM + 1.6, 3)
    catalog_case_max_stack_mm = (stack_mm
                                 + SWITCH_CASE_THICKNESS_CATALOG_TOLERANCE_MM)
    report = {
        "status": ("TRIGGER_M2_ACCESS_NOMINAL_ONLY" if not failures
                   else "TRIGGER_M2_ACCESS_SCREEN_FAILED"),
        "source_sha256": before,
        "predecessor_sha256": {
            str(TRIGGER.relative_to(ROOT)): sha(TRIGGER),
            str(INTEGRATION.relative_to(ROOT)): sha(INTEGRATION)},
        "switch": "OMRON D2F-01FL30-D3 catalog proxy",
        "fastener_candidate": {
            "M2_under_head_length_mm": 14,
            "screw_reference": "Accu SSCF-M2-14-A2, ISO 4762 socket head",
            "screw_reference_url":
                "https://www.accu.co.uk/metric-cap-head-screws/3796-SSCF-M2-14-A2",
            "plate_thickness_mm": 4,
            "switch_to_plate_nominal_gap_mm": 0,
            "switch_case_through_thickness_mm": SWITCH_CASE_THICKNESS_NOMINAL_MM,
            "switch_case_catalog_tolerance_mm": SWITCH_CASE_THICKNESS_CATALOG_TOLERANCE_MM,
            "switch_catalog_url": SWITCH_CATALOG_URL,
            "full_nut_proxy_thickness_mm": 1.6,
            "nominal_stack_with_one_rear_washer_mm": stack_mm,
            "shank_projection_past_nut_nominal_mm": round(14-stack_mm, 3),
            "shank_projection_past_nut_case_max_only_mm":
                round(14-catalog_case_max_stack_mm, 3),
            "rear_washer_proxy_thickness_mm": washer_thickness,
            "head_proxy_diameter_mm": 3.8,
            "head_proxy_height_mm": head_height,
            "rear_washer_proxy_diameter_mm": washer_od,
            "rear_washer_proxy_inner_diameter_mm": 2.2,
            "rear_washer_catalog_min_od_mm": WIDE_WASHER_MIN_OD_MM,
            "rear_washer_reference": "Accu HPW-M2-V2-A4, DIN 9021 wide washer",
            "rear_washer_reference_url":
                "https://www.accu.co.uk/metric-flat-washers/406769-HPW-M2-V2-A4",
            "nut_proxy_af_mm": 4,
            "nut_tool_proxy_diameter_mm": 6,
            "driver_shaft_proxy_diameter_mm": 4,
            "real_screw_nut_and_tool_sizes_verified": False},
        "switch_slot_fit": {
            "printed_slot_width_nominal_mm": slot_d,
            "catalog_switch_hole_pitch_tolerance_mm":
                SWITCH_HOLE_PITCH_CATALOG_TOLERANCE_MM,
            "screw_shank_proxy_diameter_mm": 2,
            "radial_allowance_after_half_pitch_error_before_print_mm":
                round((slot_d-2)/2
                      - SWITCH_HOLE_PITCH_CATALOG_TOLERANCE_MM/2, 3),
            "wide_washer_supported_area_at_catalog_min_od_mm2":
                supported_area,
            "real_printed_slot_and_clamping_verified": False},
        "tested_switch_shifts_mm": list(SHIFTS),
        "tested_trigger_angles_deg": list(ANGLES),
        "tested_feeder_fractions": list(FEED),
        "empty_probe_count": len(cases)-2,
        "positive_control_count": 2,
        "probes": probes,
        "image_sha256": sha(image) if image.is_file() else None,
        "selected_beam_unchanged": True,
        "actual_switch_hole_and_terminal_fit_verified": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": failures,
    }
    target = OUT / "review.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{report['status']} {len(cases)-2} empty + 2 controls; "
          f"failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
