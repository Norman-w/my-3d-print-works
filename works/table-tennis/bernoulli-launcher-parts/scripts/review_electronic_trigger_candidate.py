#!/usr/bin/env python3
"""Review the selected but unreleased signal-trigger printed geometry."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electronic-trigger-candidate.scad"
OUT = ROOT / "output/electronic-trigger-candidate"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
POSES = (0, -2, -4, -6, -8)
FEED_POSES = (0, .25, .5, .75, 1)
# OP varies +/-1.0 mm; sample an additional 0.4 mm drawing envelope.
CALIBRATION_SHIFTS = (-1.4, 1.4)
SPRING_SOURCE = "https://jp.misumi-ec.com/vona2/detail/110100184630/"
SPACER_SOURCE = "https://jp.misumi-ec.com/vona2/detail/221006204265/"


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


def run_stl(name: str, part: str, probe: str = "", angle: float = 0,
            feed: float = 0, switch_shift: float = 0) -> dict:
    target = OUT / f"{name}.stl"
    target.unlink(missing_ok=True)
    command = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
               "-o", str(target), "-D", f'et_part="{part}"',
               "-D", f"et_angle={angle}", "-D", f"et_feed_t={feed}",
               "-D", f"et_switch_shift={switch_shift}"]
    if probe:
        command += ["-D", f'et_probe="{probe}"']
    command.append(str(CAD))
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                            timeout=120)
    log = result.stdout + result.stderr
    if (result.returncode == 1 and "Current top level object is empty" in log
            and "WARNING:" not in log and "ERROR:" not in log):
        return {"empty": True, "volume_mm3": 0}
    if result.returncode or "WARNING:" in log or "ERROR:" in log:
        return {"error": log[-1500:]}
    inspected = subprocess.run([sys.executable, str(INSPECT), str(target),
                                "--json", "--require-watertight"],
                               cwd=ROOT, capture_output=True, text=True)
    if inspected.returncode:
        return {"error": "mesh inspection failed", "inspection": inspected.stdout[-1500:]}
    mesh = json.loads(inspected.stdout)
    # Exact seating surfaces can export a zero-volume manifold; they are
    # contact, not material penetration. Occupancy is positive volume only.
    return {"empty": abs(mesh["volume"]) <= 1e-6,
            "volume_mm3": mesh["volume"],
            "watertight": mesh["watertightByEdgeTopology"],
            "bounds": mesh["bounds"], "triangle_count": mesh["triangleCount"],
            "sha256": sha(target), "file": str(target.relative_to(ROOT))}


def run_probe(row: tuple[str, float, float, bool]) -> tuple[str, dict, bool]:
    probe, angle, feed, occupied = row
    tag = f"{probe}-a{angle:+.2f}-t{feed:.2f}"
    return tag, run_stl("probe-" + tag, "probe", probe, angle, feed), occupied


def scad_scalar(scad: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(-?\d+(?:\.\d+)?)\s*;",
                      scad, re.M)
    if not match:
        raise ValueError(f"Missing literal trigger contract scalar: {name}")
    return float(match.group(1))


def pivot_xz(scad: str) -> tuple[float, float]:
    pivot = re.search(r"^et_pivot\s*=\s*\[\s*(-?\d+(?:\.\d+)?)\s*,\s*"
                      r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]", scad, re.M)
    if not pivot:
        raise ValueError("Missing literal trigger pivot")
    return float(pivot.group(1)), float(pivot.group(3))


def print_fit_contract() -> dict:
    scad = CAD.read_text()
    value = lambda name: scad_scalar(scad, name)
    paddle_gap = value("et_paddle_back_y")-value("et_paddle_relief_front_y")
    pivot_span = value("et_pivot_cheek_back_y")-value("et_backplate_front_y")
    smallest_sleeve_axial_clearance = value("et_pivot_spacer_length") \
        -value("et_pivot_spacer_length_tolerance")-value("et_lever_pivot_width")
    smallest_sleeve_diametral_clearance = value("et_lever_pivot_bore_d") \
        -value("et_pivot_spacer_od")-value("et_pivot_spacer_od_tolerance")
    checks = {
        "lower_paddle_has_at_least_0_4mm_nominal_back_clearance": paddle_gap >= .4,
        "pivot_cheek_span_matches_metal_sleeve": abs(pivot_span-value("et_pivot_spacer_length")) < 1e-6,
        "short_spacer_leaves_lever_axial_play": smallest_sleeve_axial_clearance >= .5,
        "large_spacer_enters_nominal_lever_bore": smallest_sleeve_diametral_clearance > 0,
        "relief_is_local_to_front_skin": 0 < value("et_backplate_front_y")
        -value("et_paddle_relief_front_y") < 1,
    }
    return {
        "lower_paddle_nominal_back_clearance_mm": round(paddle_gap, 3),
        "pivot_cheek_span_mm": round(pivot_span, 3),
        "metal_sleeve_nominal_length_mm": value("et_pivot_spacer_length"),
        "metal_sleeve_candidate": "HIROSUGI CB-306-5E",
        "metal_sleeve_catalog_url": SPACER_SOURCE,
        "minimum_sleeve_to_lever_axial_play_before_print_mm":
        round(smallest_sleeve_axial_clearance, 3),
        "minimum_sleeve_to_bore_diametral_clearance_before_print_mm":
        round(smallest_sleeve_diametral_clearance, 3),
        "checks": checks, "passed": all(checks.values()),
        "printed_clearance_measured": False,
    }


def switch_calibration_contract() -> dict:
    """Check whether the adjustable switch can click before the finger stop.

    The selected switch must still be set by its real click point at assembly;
    the drawn actuation target is only a position reference.
    """
    scad = CAD.read_text()
    value = lambda name: scad_scalar(scad, name)
    pivot_x, pivot_z = pivot_xz(scad)

    def nose_left_x(angle: float) -> float:
        rad = math.radians(angle)
        center_x = pivot_x + (value("et_nose_x")-pivot_x)*math.cos(rad) \
            + (value("et_nose_z")-pivot_z)*math.sin(rad)
        return center_x-value("et_nose_d")/2

    hard_stop_angle = min(POSES)
    click_angle = value("et_switch_click_calibration_angle")
    reference_tip = value("et_switch_x")+value("et_switch_actuator_op")
    rest_gap = nose_left_x(0)-reference_tip
    reference_full_overtravel = reference_tip-nose_left_x(hard_stop_angle)
    post_click_travel = nose_left_x(click_angle)-nose_left_x(hard_stop_angle)
    mount_hole_x = value("et_switch_x")+value("et_switch_hole_x_offset")
    available_negative_shift = mount_hole_x-value("et_switch_slot_x_min")
    available_positive_shift = value("et_switch_slot_x_max")-mount_hole_x
    nominal_click_error = reference_tip-nose_left_x(click_angle)
    # OP is the absolute actuation height from the case bottom. A real
    # switch is calibrated to click at the chosen angle by shifting its case
    # against that OP variation. PT must not be added to OP again.
    op_tolerance = value("et_switch_op_tolerance")
    shift_min = nose_left_x(click_angle)-reference_tip-op_tolerance
    shift_max = nose_left_x(click_angle)-reference_tip+op_tolerance
    smallest_case_to_cheek_gap = value("et_switch_cheek_start_x") \
        -(value("et_switch_x")+value("et_switch_case_depth_x")+shift_max)
    minimum_nose_to_case_at_stop = nose_left_x(hard_stop_angle) \
        -(value("et_switch_x")+value("et_switch_case_depth_x")
          +CALIBRATION_SHIFTS[1]+.4)
    spring = spring_catalog_contract()
    spring_rest_torque = spring["minimum_rest_preload_n"] \
        *abs(value("et_spring_center_z")-pivot_z)
    max_switch_rest_torque = value("et_switch_of_max") \
        *abs(value("et_switch_actuator_z")-pivot_z)
    checks = {
        "click_angle_precedes_finger_stop": click_angle > hard_stop_angle,
        "postclick_motion_below_catalog_min_overtravel":
        0 < post_click_travel < value("et_switch_ot_min"),
        "rest_separation_exceeds_catalog_max_differential":
        rest_gap > value("et_switch_md_max"),
        "drawn_position_is_nominally_calibrated":
        abs(nominal_click_error) < .02,
        "catalog_case_and_mount_axis_dimensions_match":
        value("et_switch_case_depth_x") == 6.5
        and value("et_switch_case_depth_y") == 5.8
        and value("et_switch_hole_x_offset") == 1.5
        and value("et_switch_hole_z_offset") == 3.15
        and abs(value("et_switch_actuator_z")
                -(value("et_switch_z")+value("et_switch_actuator_z_offset"))) < 1e-6,
        "catalog_roller_l30_characteristics_match":
        value("et_switch_actuator_op") == 9.5
        and value("et_switch_op_tolerance") == 1.0
        and value("et_switch_ot_min") == .5
        and value("et_switch_md_max") == .5
        and value("et_switch_of_max") == .3,
        "catalog_d3_solder_tabs_fit_case_width":
        value("et_switch_terminal_length_x") == 3.5
        and value("et_switch_terminal_width_z") == 2.2
        and value("et_switch_terminal_thickness_y") == .4
        and value("et_switch_terminal_pitch_z") == 5.08
        and value("et_switch_terminal_first_z_offset")
            > value("et_switch_terminal_width_z")/2
        and value("et_switch_terminal_first_z_offset")
            +2*value("et_switch_terminal_pitch_z")
            +value("et_switch_terminal_width_z")/2 < 12.8,
        "catalog_op_range_reachable_by_slots":
        -available_negative_shift < shift_min
        and shift_max < available_positive_shift,
        "catalog_op_range_covered_by_clearance_probes":
        CALIBRATION_SHIFTS[0] < shift_min
        and shift_max < CALIBRATION_SHIFTS[1],
        "calibration_range_clears_pivot_cheek":
        smallest_case_to_cheek_gap >= 1,
        "worst_sampled_case_clears_nose_at_stop_with_0_4mm_drawing_allowance":
        minimum_nose_to_case_at_stop >= .75,
        "return_spring_rest_torque_exceeds_switch_max_torque":
        spring_rest_torque > max_switch_rest_torque,
    }
    return {
        "switch": "OMRON D2F-01FL30-D3",
        "catalog_url": "https://components.omron.com/sites/default/files/datasheet_pdf/B036-E1.pdf",
        "hard_stop_nominal_angle_deg": hard_stop_angle,
        "target_click_angle_deg": click_angle,
        "postclick_nose_motion_mm": round(post_click_travel, 3),
        "catalog_min_overtravel_mm": value("et_switch_ot_min"),
        "drawn_reference_rest_gap_mm": round(rest_gap, 3),
        "catalog_max_movement_differential_mm": value("et_switch_md_max"),
        "drawn_reference_full_overtravel_mm": round(reference_full_overtravel, 3),
        "drawn_reference_click_error_mm": round(nominal_click_error, 3),
        "catalog_op_tolerance_mm": op_tolerance,
        "nominal_required_switch_shift_range_mm":
        [round(shift_min, 3), round(shift_max, 3)],
        "available_negative_switch_shift_mm": round(available_negative_shift, 3),
        "available_positive_switch_shift_mm": round(available_positive_shift, 3),
        "minimum_case_to_pivot_cheek_gap_over_calibration_range_mm":
        round(smallest_case_to_cheek_gap, 3),
        "minimum_nose_to_case_gap_at_stop_over_sampled_shifts_mm":
        round(minimum_nose_to_case_at_stop, 3),
        "minimum_rest_spring_torque_nmm": round(spring_rest_torque, 3),
        "maximum_switch_torque_nmm": round(max_switch_rest_torque, 3),
        "requires_adjustment_to_real_click_before_use": True,
        "real_switch_adjusted_and_overtravel_measured": False,
        "checks": checks, "passed": all(checks.values()),
    }


def spring_catalog_contract() -> dict:
    """Check both length/force tolerance ends against the modeled spring seats.

    WR4-15 values come from MISUMI's product table. This is a catalog check,
    not a measured spring, friction test, or assembly release.
    """
    scad = CAD.read_text()
    scalar = lambda name: scad_scalar(scad, name)

    pivot_x, pivot_z = pivot_xz(scad)
    fixed_x = scalar("et_spring_fixed_seat_x")
    moving_x = scalar("et_spring_moving_seat_x")
    moving_z = scalar("et_spring_center_z")
    free = scalar("et_spring_free")
    length_tolerance = scalar("et_spring_length_tolerance")
    k = scalar("et_spring_k_nominal")
    k_tolerance = scalar("et_spring_k_tolerance")
    max_deflection_fraction = scalar("et_spring_max_deflection_fraction")
    max_catalog_load = scalar("et_spring_catalog_max_load")
    angle = min(POSES)
    pulled_x = pivot_x + (moving_x-pivot_x)*math.cos(math.radians(angle)) \
        + (moving_z-pivot_z)*math.sin(math.radians(angle))
    rest_length = fixed_x-moving_x
    pulled_length = fixed_x-pulled_x
    shortest = free-length_tolerance
    longest = free+length_tolerance
    min_preload = (shortest-rest_length)*k*(1-k_tolerance)
    max_pulled_force = (longest-pulled_length)*k*(1+k_tolerance)
    worst_deflection = longest-pulled_length
    # Use the catalog's nominal 60% stroke, stricter than scaling with a
    # long-tolerance spring, so the tolerance check remains conservative.
    allowed_deflection = free*max_deflection_fraction
    checks = {
        "spring_od_fits_pockets": scalar("et_spring_od") < scalar("et_spring_pocket_d"),
        "short_spring_has_preload_at_rest": min_preload > 0,
        "long_spring_stays_within_nominal_catalog_stroke": worst_deflection < allowed_deflection,
        "high_rate_long_spring_stays_below_catalog_load": max_pulled_force < max_catalog_load,
        "both_seats_compress_on_pull": 0 < pulled_length < rest_length,
    }
    return {
        "catalog_part": "MISUMI WR4-15", "catalog_url": SPRING_SOURCE,
        "rest_installed_length_mm": round(rest_length, 3),
        "pulled_installed_length_mm": round(pulled_length, 3),
        "free_length_range_mm": [shortest, longest],
        "minimum_rest_preload_n": round(min_preload, 3),
        "maximum_pulled_force_n": round(max_pulled_force, 3),
        "worst_deflection_mm": round(worst_deflection, 3),
        "nominal_catalog_max_deflection_mm": allowed_deflection,
        "catalog_max_load_n": max_catalog_load,
        "checks": checks, "passed": all(checks.values()),
        "physical_spring_and_friction_tested": False,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    spring = spring_catalog_contract()
    print_fit = print_fit_contract()
    switch = switch_calibration_contract()
    before = {str(p.relative_to(ROOT)): sha(p)
              for p in sorted(source_tree(CAD) | {Path(__file__).resolve()})}
    parts = {name: run_stl(name, name) for name in ("beam", "lever", "mount")}
    probes = []
    for angle in POSES:
        probes += [(kind, angle, 0, False) for kind in
                   ("lever-mount", "lever-switch-body", "lever-beam")]
    probes += [(kind, 0, 0, False) for kind in
               ("switch-beam", "switch-terminals-fixed",
                "mount-other-fixed", "switch-other-fixed")]
    for feed in FEED_POSES:
        probes.append(("mount-moving", 0, feed, False))
        probes.append(("switch-terminals-moving", 0, feed, False))
        for angle in (0, -4, -8):
            probes.append(("lever-moving", angle, feed, False))
    for feed in (0, .5, 1):
        for angle in (0, -4, -8):
            probes.append(("lever-original-hardware", angle, feed, False))
    # Deliberate penetration confirms each mechanical stop and the switch
    # actuation target are on the actual lever path.
    probes += [("lever-mount", .5, 0, True),
               ("lever-mount", -9, 0, True),
               ("lever-switch-actuation-target", 0, 0, False),
               ("lever-switch-actuation-target", -8, 0, True)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        checked = list(pool.map(run_probe, probes))
        calibration_rows = []
        for shift in CALIBRATION_SHIFTS:
            calibration_rows.extend((kind, angle, feed, shift) for kind, angle, feed in
                                    (("lever-switch-body", a, 0) for a in (0, -4, -8)))
            calibration_rows.extend((kind, 0, 0, shift) for kind in
                                    ("switch-beam", "switch-other-fixed",
                                     "switch-terminals-fixed"))
            calibration_rows.extend(("switch-terminals-moving", 0, feed, shift)
                                    for feed in FEED_POSES)
        def calibration_probe(row: tuple[str, float, float, float]) -> tuple[str, dict, bool]:
            kind, angle, feed, shift = row
            tag = f"{kind}-a{angle:+.2f}-t{feed:.2f}-sx{shift:+.2f}"
            result = run_stl("probe-" + tag, "probe", kind, angle, feed, shift)
            return tag, result, False
        checked += list(pool.map(calibration_probe, calibration_rows))
    failures = []
    if not spring["passed"]:
        failures.append("spring catalog tolerance contract failed")
    if not print_fit["passed"]:
        failures.append("trigger print-fit contract failed")
    if not switch["passed"]:
        failures.append("trigger switch calibration geometry failed")
    for name, row in parts.items():
        if row.get("error") or row.get("empty") or not row.get("watertight"):
            failures.append(f"{name}: not a closed printable candidate")
    for tag, row, occupied in checked:
        if row.get("error") or row.get("empty") == occupied:
            failures.append(f"{tag}: wrong occupancy")
    after = {str(p.relative_to(ROOT)): sha(p)
             for p in sorted(source_tree(CAD) | {Path(__file__).resolve()})}
    if before != after:
        failures.append("source tree changed during review")
    report = {
        "status": "TRIGGER_CANDIDATE_GEOMETRY_PASS_UNRELEASED" if not failures else "FAIL",
        "source_sha256": before,
        "parts": parts,
        "probe_count": len(checked),
        "calibration_clearance_shift_samples_mm": list(CALIBRATION_SHIFTS),
        "spring_catalog_contract": spring,
        "print_fit_contract": print_fit,
        "switch_calibration_contract": switch,
        "probes": {tag: row for tag, row, _ in checked},
        "failures": failures,
        "scope": "Nominal signal-trigger mount, lever, switch-body/terminal proxies and hard-stop path on current fixed grip",
        "switch_roller_lever_exact_3d_verified": False,
        "omron_terminal_and_wire_envelope_verified": False,
        "spring_supplier_and_force_verified": False,
        "pivot_spacer_and_fastener_fit_verified": False,
        "motor_interface_reviewed": False,
        "current_inventory_promoted": True,
        "manufacturing_release": False,
        "physical_acceptance": False,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"electronic trigger candidate: {'PASS' if not failures else 'FAIL'}; "
          f"{len(checked)} probes")
    for failure in failures:
        print("  " + failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
