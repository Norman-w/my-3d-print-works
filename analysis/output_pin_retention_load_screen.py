#!/usr/bin/env python3
"""Check output-pin axial engagement and idealized bending before part selection."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROCKER = ROOT / "cad/electric-rocker-bridge-screen.scad"
CROSSHEAD = ROOT / "cad/electric-output-crosshead-screen.scad"
JOINT = ROOT / "cad/electric-rocker-pivot-joint-screen.scad"
SERVICE = ROOT / "cad/electric-rocker-service-fork-screen.scad"
GEOMETRY = ROOT / "output/electric-output-crosshead-screen/review.json"
ASSEMBLY = ROOT / "output/electric-rocker-service-fork-screen/review.json"
OUT = ROOT / "output/electric-output-crosshead-screen/pin-retention-load-screen.json"


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def require(source: str, fragment: str) -> None:
    if fragment not in source:
        raise ValueError(f"Geometry contract changed: {fragment}")


def main() -> None:
    rocker = ROCKER.read_text()
    crosshead = CROSSHEAD.read_text()
    joint = JOINT.read_text()
    service = SERVICE.read_text()
    geometry = json.loads(GEOMETRY.read_text())
    assembly = json.loads(ASSEMBLY.read_text())
    if geometry["status"] != "OUTPUT_CROSSHEAD_GEOMETRY_SCREEN_ONLY" \
            or assembly["status"] != "SERVICE_FORK_NOMINAL_ASSEMBLY_PATH_ONLY":
        raise ValueError("Output crosshead or fork assembly review is not current")
    for source, fragment in ((rocker, "rb_plane_y = 62;"),
                             (rocker, "rb_rocker_thickness_y = 5;"),
                             (rocker, "translate([0,-5,0])rb_ycyl(rb_output_r,0,rb_pin_d,14);"),
                             (crosshead, "rb_plane_y = 65;"),
                             (crosshead, "oc_outer_y0 = 50;"),
                             (crosshead, "oc_outer_y1 = rb_plane_y-3.5;"),
                             (crosshead, "oc_pin_d = 7;"),
                             (joint, "pj_bracket_front_inner_y = pj_y-4;"),
                             (joint, "pj_bracket_rear_inner_y = pj_y+4;"),
                             (joint, "pj_rocker_thickness = 5;"),
                             (service, "sf_part = \"probe\";")):
        require(source, fragment)

    rocker_center_y = 65.0
    plate_near_face_y = rocker_center_y - 5/2
    plate_far_face_y = rocker_center_y + 5/2
    pin_low_y = rocker_center_y - 5 - 14/2
    pin_high_y = rocker_center_y - 5 + 14/2
    slot_low_y = 50.0
    slot_high_y = rocker_center_y - 3.5
    fork_inner_low_y = rocker_center_y - 4
    fork_inner_high_y = rocker_center_y + 4
    engagement_nominal = min(slot_high_y, pin_high_y)-max(slot_low_y, pin_low_y)
    max_rear_shift_if_rocker_only = fork_inner_high_y-plate_far_face_y
    min_engagement_if_rocker_only = engagement_nominal-max_rear_shift_if_rocker_only
    pin_bending_section = math.pi*7**3/32
    bearing_centroid_y = (max(slot_low_y, pin_low_y)+min(slot_high_y, pin_high_y))/2
    nominal_moment_arm = plate_near_face_y-bearing_centroid_y
    extreme_moment_arm = plate_near_face_y-max(slot_low_y, pin_low_y)
    cases = []
    for kgf in (4, 5):
        input_n = kgf*9.80665
        output_n = input_n*75/50
        cases.append({
            "seller_claim_kgf": kgf,
            "ideal_output_force_n": round(output_n, 3),
            "printed_pin_nominal_bending_stress_at_uniform_bearing_centroid_mpa":
                round(output_n*nominal_moment_arm/pin_bending_section, 3),
            "printed_pin_one_edge_bearing_sensitivity_mpa":
                round(output_n*extreme_moment_arm/pin_bending_section, 3),
        })
    report = {
        "status": "OUTPUT_PIN_AXIAL_ENGAGEMENT_CONDITIONAL_LOAD_UNRELEASED",
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                          (Path(__file__), ROCKER, CROSSHEAD, JOINT, SERVICE,
                           GEOMETRY, ASSEMBLY)},
        "axial_geometry_mm": {
            "slot_y": [slot_low_y, slot_high_y],
            "integral_printed_pin_y": [pin_low_y, pin_high_y],
            "rocker_plate_y": [plate_near_face_y, plate_far_face_y],
            "fork_inner_faces_y": [fork_inner_low_y, fork_inner_high_y],
            "nominal_pin_slot_engagement": engagement_nominal,
            "maximum_rearward_rocker_translation_if_retained_between_fork_faces":
                max_rear_shift_if_rocker_only,
            "remaining_engagement_at_that_translation": min_engagement_if_rocker_only,
            "rearward_translation_needed_for_full_pin_withdrawal": engagement_nominal,
        },
        "conditional_retention": {
            "no_separate_output_pin_axial_clip_needed_if_fork_and_pivot_keep_rocker_between_its_inner_faces":
                min_engagement_if_rocker_only > 0,
            "also_requires_moving_slot_to_remain_within_modeled_y_envelope": True,
            "actual_fork_spacing_pin_retention_bushing_fit_and_flex_verified": False,
            "moving_slot_y_position_and_flex_verified": False,
            "pin_integral_with_printed_rocker_in_nominal_cad": True,
            "printed_pin_attachment_and_wear_verified": False,
        },
        "idealized_printed_pin_load_scenario_only": {
            "pin_nominal_d_mm": 7,
            "circular_section_modulus_mm3": round(pin_bending_section, 3),
            "plate_face_to_bearing_centroid_mm": round(nominal_moment_arm, 3),
            "plate_face_to_far_engagement_edge_mm": round(extreme_moment_arm, 3),
            "cases": cases,
            "seller_force_claim_matches_purchased_sku_verified": False,
            "stress_concentration_print_layer_orientation_impact_and_wear_included": False,
            "material_allowable_or_safety_factor_asserted": False,
        },
        "manufacturing_release": False,
        "physical_acceptance": False,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{report['status']}: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
