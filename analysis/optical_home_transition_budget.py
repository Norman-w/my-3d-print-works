#!/usr/bin/env python3
"""Bound the optical return edge against the feeder's mechanical zero.

This uses the currently reviewed CAD window as a geometric envelope. An
optical switching point, motor braking distance, and physical return are not
inferred from that envelope.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/feeder-optical-home.scad"
PARAMETERS = ROOT / "cad/parameters.scad"
REVIEW = ROOT / "output/optical-home-candidate/review.json"
POINT_SHOT = ROOT / "output/analysis/point-shot-interlock.json"
ELECTRIC_CAD = ROOT / "cad/electric-feeder-assembly.scad"
OUT = ROOT / "output/optical-home-candidate/transition-budget.json"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def scalar(source: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(-?\d+(?:\.\d+)?)\s*;",
                      source, re.M)
    if not match:
        raise RuntimeError(f"Missing CAD parameter: {name}")
    return float(match.group(1))


def main() -> int:
    source = CAD.read_text()
    review = json.loads(REVIEW.read_text())
    point_shot = json.loads(POINT_SHOT.read_text())
    electric_source = ELECTRIC_CAD.read_text()
    if not review["geometry_review_pass"] or review["source_sha256"] != digest(CAD):
        raise RuntimeError("Optical-home CAD and geometry review differ")
    if point_shot["status"] != "CONDITIONAL_INTERLOCK_CONTRACT_NOT_IMPLEMENTED_IN_CAD" \
            or any(digest(ROOT / name) != expected
                   for name, expected in point_shot["source_sha256"].items()) \
            or "feeder_carriage(t)" not in electric_source:
        raise RuntimeError("Partial-return counterexample is stale or electric carriage changed")
    second_shot = next((row for row in point_shot["existing_mechanism_counterexamples"]
                        if row["name"] == "second discharge without full reset"), None)
    if not second_shot or second_shot["output_count"] != 2 \
            or second_shot["partial_return_u_mm"] <= 0:
        raise RuntimeError("Missing partial-return second-shot counterexample")
    for name, row in review["printed_parts"].items():
        if not row["watertight"] or row["volume_mm3"] <= 0:
            raise RuntimeError(f"Unreviewed optical printed part: {name}")

    flag = re.search(
        r"oh_box\(oh_sensor_x-oh_flag_thickness/2,\s*"
        r"oh_sensor_x\+oh_flag_thickness/2,\s*"
        r"oh_flag_y0,oh_flag_y1,\s*(-?\d+(?:\.\d+)?),"
        r"(-?\d+(?:\.\d+)?)\);", source,
    )
    adjustment = re.search(r"for\(dz=\[(-?\d+),(-?\d+)\]\)", source)
    window = re.search(
        r"oh_optical_z\+oh_sensor_dz-(\d+(?:\.\d+)?),\s*"
        r"oh_optical_z\+oh_sensor_dz\+(\d+(?:\.\d+)?)\);", source,
    )
    if not flag or not adjustment or not window:
        raise RuntimeError("Optical flag, adjustment, or window changed; review the budget")
    flag_bottom, flag_top = map(float, flag.groups())
    adjust_lo, adjust_hi = map(int, adjustment.groups())
    below, above = map(float, window.groups())
    optical_z = scalar(source, "oh_optical_z")
    feeder_stroke = scalar(PARAMETERS.read_text(), "cam_stroke")
    if (adjust_lo, adjust_hi, below, above) != (0, 2, 1, 1) \
            or feeder_stroke != 20 or flag_top - flag_bottom < 2:
        raise RuntimeError("Unexpected sensor adjustment, window, or feeder travel")

    rows = []
    for dz in range(adjust_lo, adjust_hi + 1):
        window_low = optical_z + dz - below
        center = optical_z + dz
        window_high = optical_z + dz + above
        # On return from 20 mm: partial window overlap begins just below
        # upper edge, the centre is covered next, then the entire modelled
        # 2 mm target window is covered. Boundary equality has zero volume.
        full = window_low - flag_bottom
        centre = center - flag_bottom
        partial = window_high - flag_bottom
        if not (0 < full < centre < partial < feeder_stroke):
            raise RuntimeError("Optical transition envelope is outside the stroke")
        rows.append({
            "sensor_upward_adjustment_mm": dz,
            "modelled_window_z_mm": [window_low, window_high],
            "return_window_first_overlap_below_feeder_displacement_mm": partial,
            "return_window_centre_covered_at_feeder_displacement_mm": centre,
            "return_entire_window_covered_at_or_below_feeder_displacement_mm": full,
            "modelled_transition_band_above_mechanical_zero_mm": [full, partial],
        })

    unsafe_u = second_shot["partial_return_u_mm"]
    blocked_at_unsafe_u = [
        unsafe_u <= row["return_entire_window_covered_at_or_below_feeder_displacement_mm"]
        for row in rows
    ]
    if unsafe_u >= feeder_stroke or not all(blocked_at_unsafe_u):
        raise RuntimeError("The modelled partial-return observation changed")

    report = {
        "status": "GEOMETRIC_NEAR_HOME_ONLY_ZERO_UNPROVEN",
        "source": {
            "analysis_script_sha256": digest(Path(__file__)),
            "cad_sha256": digest(CAD),
            "parameters_sha256": digest(PARAMETERS),
            "geometry_review_sha256": digest(REVIEW),
            "partial_return_counterexample_report_sha256": digest(POINT_SHOT),
            "electric_carriage_cad_sha256": digest(ELECTRIC_CAD),
        },
        "feeder_displacement_zero_definition": "mechanical return stop, u=0 mm",
        "feeder_stroke_mm": feeder_stroke,
        "flag_vertical_extent_at_zero_mm": [flag_bottom, flag_top],
        "optical_window_is_cad_probe_not_sensor_switching_spec": True,
        "adjustment_rows": rows,
        "all_adjustments_modelled_transition_band_above_zero_mm":
            [rows[0]["modelled_transition_band_above_mechanical_zero_mm"][0],
             rows[-1]["modelled_transition_band_above_mechanical_zero_mm"][1]],
        "partial_return_double_shot_observability": {
            "counterexample_feeder_displacement_mm": unsafe_u,
            "counterexample_output_count_if_retriggered_before_true_zero": 2,
            "modelled_entire_optical_window_covered_at_unsafe_u_by_sensor_adjustment":
                {str(row["sensor_upward_adjustment_mm"]): blocked
                 for row, blocked in zip(rows, blocked_at_unsafe_u)},
            "modelled_blocked_boolean_distinguishes_u0_from_unsafe_u": False,
            "interpretation": "The current electric carriage retains the same gate motion. In the CAD 2 mm optical-window proxy, both true zero and the previously identified u=1 mm partial return appear covered for every allowed sensor height. Actual optical switching is unmeasured; this is a counterexample to accepting blocked alone, not a measured double shot.",
        },
        "actual_switching_displacement_mm": None,
        "actual_motor_braking_distance_mm": None,
        "actual_motor_cycle_home_behavior": None,
        "optical_blocked_alone_confirms_mechanical_zero": False,
        "one_shot_rearm_from_optical_blocked_alone_permitted": False,
        "required_closure": (
            "Prove the actual motor reaches and remains at the mechanical "
            "return position after the optical edge, using measured braking "
            "and cycle behavior or an independent home confirmation."
        ),
        "manufacturing_release": False,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("Optical return envelope above mechanical zero: "
          f"{rows[0]['modelled_transition_band_above_mechanical_zero_mm'][0]:g}–"
          f"{rows[-1]['modelled_transition_band_above_mechanical_zero_mm'][1]:g} mm; "
          "zero not confirmed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
