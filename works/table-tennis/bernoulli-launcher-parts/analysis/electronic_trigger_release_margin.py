#!/usr/bin/env python3
"""Bound a calibrated D2F-L30 trigger's released state from catalog FP/OP.

The catalog gives FP Max., not a guaranteed free-lever shape. This analytic
check does not certify the printed pivot, actual roller, click, or wiring.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electronic-trigger-candidate.scad"
GEOMETRY_REVIEW = ROOT / "output/electronic-trigger-candidate/review.json"
OUT = ROOT / "output/electronic-trigger-candidate/release-margin.json"
CATALOG_URL = "https://omronfs.omron.com/en_US/ecb/products/pdf/en-d2f.pdf"
# OMRON D2F-01FL30-D3, simulated roller lever R2.5, catalog page 4.
CATALOG_FP_MAX_MM = 12.6


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def scalar(source: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(-?\d+(?:\.\d+)?)\s*;",
                      source, re.M)
    if not match:
        raise RuntimeError(f"Missing trigger scalar: {name}")
    return float(match.group(1))


def main() -> int:
    source = CAD.read_text()
    review = json.loads(GEOMETRY_REVIEW.read_text())
    if review["status"] != "TRIGGER_CANDIDATE_GEOMETRY_PASS_UNRELEASED" \
            or review["source_sha256"]["cad/electronic-trigger-candidate.scad"] != digest(CAD):
        raise RuntimeError("Trigger CAD and nominal geometry review differ")
    pivot_match = re.search(r"^et_pivot\s*=\s*(\[[^\]]+\]);", source, re.M)
    if not pivot_match:
        raise RuntimeError("Missing trigger pivot")
    pivot_x, _, pivot_z = json.loads(pivot_match.group(1))
    value = lambda name: scalar(source, name)

    def nose_left_x(degrees: float) -> float:
        angle = math.radians(degrees)
        return pivot_x + (value("et_nose_x")-pivot_x)*math.cos(angle) \
            + (value("et_nose_z")-pivot_z)*math.sin(angle) \
            - value("et_nose_d")/2

    click_angle = value("et_switch_click_calibration_angle")
    stop_angle = review["switch_calibration_contract"]["hard_stop_nominal_angle_deg"]
    rest_x = nose_left_x(0)
    click_x = nose_left_x(click_angle)
    stop_x = nose_left_x(stop_angle)
    op = value("et_switch_actuator_op")
    op_tolerance = value("et_switch_op_tolerance")
    md_max = value("et_switch_md_max")
    shift_middle = click_x - (value("et_switch_x")+op)
    shift_min = shift_middle-op_tolerance
    shift_max = shift_middle+op_tolerance
    free_tip_farthest_x = value("et_switch_x") + shift_max + CATALOG_FP_MAX_MM
    rest_to_click = rest_x-click_x
    release_reserve = rest_to_click-md_max
    max_rest_predeflection = max(0.0, free_tip_farthest_x-rest_x)
    checks = {
        "calibrated_switch_fits_slots":
            shift_min > -review["switch_calibration_contract"]["available_negative_switch_shift_mm"]
            and shift_max < review["switch_calibration_contract"]["available_positive_switch_shift_mm"],
        "released_position_exceeds_catalog_max_movement_differential":
            release_reserve > 0,
        "hard_stop_adds_less_than_catalog_minimum_overtravel":
            0 < click_x-stop_x < value("et_switch_ot_min"),
        "catalog_fp_max_is_beyond_released_nose_in_worst_shift":
            max_rest_predeflection > 0,
    }
    report = {
        "status": "NOMINAL_RELEASE_MARGIN_PASS_REAL_LEVER_UNVERIFIED"
                  if all(checks.values()) else "NOMINAL_RELEASE_MARGIN_FAIL",
        "source": {
            "catalog_url": CATALOG_URL,
            "catalog_model": "OMRON D2F-01FL30-D3",
            "catalog_page": 4,
            "analysis_script_sha256": digest(Path(__file__)),
            "cad_sha256": digest(CAD),
            "geometry_review_sha256": digest(GEOMETRY_REVIEW),
        },
        "catalog_fp_max_mm": CATALOG_FP_MAX_MM,
        "catalog_op_nominal_mm": op,
        "catalog_op_tolerance_mm": op_tolerance,
        "catalog_md_max_mm": md_max,
        "switch_case_calibration_shift_mm": [round(shift_min, 4), round(shift_max, 4)],
        "nose_left_x_mm": {"released": round(rest_x, 4),
                           "click": round(click_x, 4),
                           "hard_stop": round(stop_x, 4)},
        "released_to_click_travel_mm": round(rest_to_click, 4),
        "nominal_release_reserve_after_catalog_md_mm": round(release_reserve, 4),
        "free_tip_farthest_x_mm_after_calibration": round(free_tip_farthest_x, 4),
        "maximum_possible_roller_predeflection_at_rest_mm":
            round(max_rest_predeflection, 4),
        "interpretation": (
            "FP is a maximum position, not the actual free-lever position. "
            "The lever may already be deflected when the finger trigger is "
            "released; the drawn OP point alone is not a free-position model. "
            f"The {release_reserve:.3f} mm release reserve is nominal and has no allowance "
            "for printed pivot play, actual lever shape, wear or wiring."
        ),
        "checks": checks,
        "real_switch_click_and_release_tested": False,
        "real_roller_shape_fitted": False,
        "manufacturing_release": False,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Nominal release reserve after MD max: {release_reserve:.3f} mm; "
          f"maximum possible released predeflection: {max_rest_predeflection:.3f} mm")
    if not all(checks.values()):
        raise SystemExit("Electronic trigger release contract failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
