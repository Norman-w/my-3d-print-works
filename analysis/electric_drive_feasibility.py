#!/usr/bin/env python3
"""Bound the selected reciprocating motor against the current feeder spring.

This is a necessary-load check, not an actuator approval or a motor mount.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs/electric-assembly-inventory.json"
SPRING_REVIEW = ROOT / "output/feeder-return-spring/feeder-return-spring-service-report.json"
LISTING_DIR = ROOT / "output/procurement/reciprocating-20260930"
LISTING_EVIDENCE = LISTING_DIR / "product-evidence.json"
LISTING_IMAGES = LISTING_DIR / "image-sources.json"
OUT = ROOT / "output/electric-drive-feasibility/report.json"
SPRING_SOURCES = (
    "cad/feeder-return-spring.scad",
    "cad/feeder-supports.scad",
    "cad/cam-study.scad",
    "cad/parameters.scad",
)
# Manual readings of the archived seller gallery, deliberately bound to the
# exact image bytes. The gallery is shared by product variants, not a signed
# engineering drawing for the selected SKU.
LISTING_IMAGE_SHA256 = {
    2: "a759d9bf0c51e70563b44f72b6128f4471e16b8b7da545ce3511e2e32863f348",
    6: "5db3bd8ff9b52599dea08a5aecb6c2b5f135fa55abc7af2bf44e6bcece11e615",
}
MAIN_05_SHA256 = "e16b8644c2877841251974b45b4ffc78b7af2178d68d48f696e626622e24c0d6"
MAIN_03_SHA256 = "77eb8b1fafab491b03e396f2c895d18a0b67658359a617bc98b280534fe8ca43"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def seller_gallery_claims() -> dict:
    captured = json.loads(LISTING_EVIDENCE.read_text())
    matching = [row for row in captured["candidates"]
                if row.get("itemId") == "988456349136"
                and row.get("skuId") == "5952763100025"]
    if len(matching) != 1:
        raise RuntimeError("Selected BY141-3 listing evidence changed")
    candidate = matching[0]
    images = {row["image"]: row for row in json.loads(LISTING_IMAGES.read_text())}
    sources = {}
    for number, expected_sha in LISTING_IMAGE_SHA256.items():
        name = f"detail-{number:02}.png"
        path = LISTING_DIR / name
        row = images[number]
        if Path(row["path"]) != path or row["sourceUrl"] not in candidate["imageUrls"] \
                or row["bytes"] != path.stat().st_size or digest(path) != expected_sha:
            raise RuntimeError(f"Archived seller image changed: {name}")
        sources[name] = {"path": str(path.relative_to(ROOT)),
                         "sha256": expected_sha, "source_url": row["sourceUrl"]}
    main_05 = LISTING_DIR / "main-05.webp"
    main_03 = LISTING_DIR / "main-03.webp"
    # The archived main images match the selected product page's URL order;
    # neither is a variant-specific engineering specification.
    if digest(main_03) != MAIN_03_SHA256 or len(candidate["imageUrls"]) < 5 \
            or "O1CN01tOlaFg1FU0m7fLv6Q" not in candidate["imageUrls"][2]:
        raise RuntimeError("Archived third main seller image changed")
    if digest(main_05) != MAIN_05_SHA256 or len(candidate["imageUrls"]) < 5 \
            or "O1CN013vS0gZ1FU0lyFh2iR" not in candidate["imageUrls"][4]:
        raise RuntimeError("Archived fifth main seller image changed")
    sources["main-03.webp"] = {
        "path": str(main_03.relative_to(ROOT)),
        "sha256": MAIN_03_SHA256,
        "source_url": candidate["imageUrls"][2],
    }
    sources["main-05.webp"] = {
        "path": str(main_05.relative_to(ROOT)),
        "sha256": MAIN_05_SHA256,
        "source_url": candidate["imageUrls"][4],
    }
    return {
        "seller_listing_item_id": candidate["itemId"],
        "selected_sku_id": candidate["skuId"],
        "product_evidence_sha256": digest(LISTING_EVIDENCE),
        "image_manifest_sha256": digest(LISTING_IMAGES),
        "source_images": sources,
        "scope": "Shared seller gallery captured on the selected item's page; not a variant-specific maker drawing or measured delivered part",
        "image_02_claims": {"model_text": "Y141#", "outside_diameter_mm": 20.5,
                            "overall_length_mm": 99, "stroke_mm": 30,
                            "nominal_voltage_v": 3.7},
        "image_06_claims": {"model_text": "141#", "drawing_length_mm": 96.5,
                            "stroke_mm": 30, "voltage_range_v": [2.5, 4.5],
                            "rated_current_upper_a": 0.36,
                            "stall_current_a": [6.5, 7.5],
                            "push_claim_kgf": [4, 5],
                            "speed_claim_times_per_min": 120,
                            "speed_unit_or_load_condition_defined": False,
                            "motor_rotation_label": "CW"},
        "main_05_claims": {
            "retracted_total_length_mm": 99,
            "extended_total_length_mm": 129,
            "stroke_mm": 30,
            "white_end_outside_diameter_mm": 22,
            "metal_motor_outside_diameter_mm": 21,
            "yellow_protective_sleeve_outside_diameter_mm": 29,
            "yellow_protective_sleeve_length_mm": 68,
            "protective_sleeve_in_selected_sku_confirmed": False,
        },
        "main_03_claims": {
            "speed_value": 225,
            "speed_unit_shown": False,
            "nominal_voltage_v": 3.7,
            "stroke_mm": 30,
            "push_claim_kgf": 4,
            "model_variant_identified": False,
        },
        "speed_claims_reconciled": False,
        "length_disagreement_mm": 2.5,
        "mounting_holes_and_depth_dimensioned": False,
        "movable_output_retention_dimensioned": False,
        "loaded_retraction_force_dimensioned": False,
        "motor_phase_or_stop_behavior_documented": False,
        "exact_selected_sku_identity_proven_by_images": False,
    }


def main() -> int:
    selected = json.loads(INVENTORY.read_text())
    spring = json.loads(SPRING_REVIEW.read_text())
    assert selected["snapshot"] == "electric-drive-selected-unreleased"
    assert selected["assembly_complete"] is False
    assert spring["sources_stable_during_run"] is True
    for name in SPRING_SOURCES:
        if spring["source_sha256"][name] != digest(ROOT / name):
            raise RuntimeError(f"Spring force source changed: {name}")

    feeder_stroke = selected["feeder_stroke_mm"]
    motor_nominal_stroke = selected["motor_nominal_stroke_mm"]
    assert feeder_stroke == 20 and motor_nominal_stroke == 30
    rows = spring["catalog_force_rows"]
    assert [row["stroke_mm"] for row in rows] == [0, 5, 10, 15, 20]
    forces = [row["catalog_nominal_force_N"] for row in rows]
    assert all(left < right for left, right in zip(forces, forces[1:]))
    ratio = feeder_stroke / motor_nominal_stroke
    # This pointwise force mapping only applies to a constant 2:3 ratio.
    # An actual linkage may trade force differently over its travel.
    ideal_input_forces = [force * ratio for force in forces]
    # Area under the catalogue spring-force curve over the 20 mm feed stroke.
    spring_work_j = sum(
        (forces[i] + forces[i + 1]) / 2
        * (rows[i + 1]["stroke_mm"] - rows[i]["stroke_mm"]) / 1000
        for i in range(len(rows) - 1)
    )
    motor = next(row for row in selected["external_components"]
                 if row["id"] == "motor/BY141-3")
    listed_power_w = motor["visible_listing"]["rated_power_w"]
    gallery = seller_gallery_claims()
    seller_push_low_n = gallery["image_06_claims"]["push_claim_kgf"][0] * 9.80665
    seller_full_stroke_work_j = seller_push_low_n * motor_nominal_stroke / 1000
    seller_cycle_frequency_hz = gallery["image_06_claims"]["speed_claim_times_per_min"] / 60
    # Only a conditional inconsistency check: neither 4 kgf nor 120 "times"
    # has a specified force-speed operating point in the seller picture.
    seller_forward_time_if_symmetric_full_cycle_s = 1 / (2 * seller_cycle_frequency_hz)
    seller_forward_power_if_full_force_w = seller_full_stroke_work_j \
        / seller_forward_time_if_symmetric_full_cycle_s
    # A same-side rocker with captured horizontal pin slots has an exact
    # vertical travel ratio R_out/R_in for any angle, not merely a small-angle
    # approximation. This defines a possible 30:20 converter but no motor
    # mounting interface, pin sizing, follower attachment or stop compliance.
    rocker_input_arm_mm = 45.0
    rocker_output_arm_mm = 30.0
    rocker_half_swing_rad = math.asin(motor_nominal_stroke / (2 * rocker_input_arm_mm))
    rocker_endpoint_cos = math.cos(rocker_half_swing_rad)
    rocker_input_lateral_mm = rocker_input_arm_mm * (1-rocker_endpoint_cos)
    rocker_output_lateral_mm = rocker_output_arm_mm * (1-rocker_endpoint_cos)
    rocker_output_stroke_mm = 2*rocker_output_arm_mm*math.sin(rocker_half_swing_rad)
    assert abs(rocker_output_stroke_mm-feeder_stroke) < 1e-9
    rocker_samples = []
    for fraction in (0, .25, .5, .75, 1):
        angle = (2*fraction-1)*rocker_half_swing_rad
        input_z = rocker_input_arm_mm*(math.sin(angle)+math.sin(rocker_half_swing_rad))
        output_z = rocker_output_arm_mm*(math.sin(angle)+math.sin(rocker_half_swing_rad))
        rocker_samples.append({
            "phase": fraction,
            "input_travel_mm": round(input_z, 4),
            "output_travel_mm": round(output_z, 4),
            "input_pin_lateral_offset_from_end_mm": round(
                rocker_input_arm_mm*(math.cos(angle)-rocker_endpoint_cos), 4),
            "output_pin_lateral_offset_from_end_mm": round(
                rocker_output_arm_mm*(math.cos(angle)-rocker_endpoint_cos), 4),
        })
        assert abs(output_z-ratio*input_z) < 1e-9
    # A fixed-ratio, hard-coupled drive cannot both reach a 20 mm feeder stop
    # at the shortest possible motor stroke and avoid loading that stop at a
    # longer stroke. These are hypothetical intervals, not BY141-3 tolerances.
    endpoint_examples = []
    for half_spread in (.25, .5, 1.0):
        shortest = motor_nominal_stroke-half_spread
        longest = motor_nominal_stroke+half_spread
        ratio_to_reach_at_shortest = feeder_stroke/shortest
        full_end_excess = ratio_to_reach_at_shortest*longest-feeder_stroke
        assert shortest < longest and full_end_excess > 0
        assert ratio_to_reach_at_shortest*shortest >= feeder_stroke
        endpoint_examples.append({
            "hypothetical_motor_stroke_interval_mm": [shortest, longest],
            "nominal_two_thirds_output_at_shortest_mm": round(ratio*shortest, 4),
            "nominal_two_thirds_output_at_longest_mm": round(ratio*longest, 4),
            "minimum_ratio_to_reach_20mm_at_shortest": round(ratio_to_reach_at_shortest, 6),
            "minimum_full_stop_compliance_if_ratio_is_tuned_to_shortest_mm":
                round(full_end_excess, 4),
        })
    report = {
        "status": "NECESSARY_LOAD_BOUND_ONLY_MOTOR_NOT_APPROVED",
        "inputs": {
            "analysis_script_sha256": digest(Path(__file__)),
            "inventory_sha256": digest(INVENTORY),
            "spring_report_sha256": digest(SPRING_REVIEW),
            "checked_spring_source_sha256": {
                name: digest(ROOT / name) for name in SPRING_SOURCES
            },
            "motor": motor["id"],
            "motor_nominal_stroke_mm": motor_nominal_stroke,
            "feeder_stroke_mm": feeder_stroke,
            "spring_force_basis": "catalogue nominal; not measured on current assembly",
        },
        "necessary_conditions": {
            "nominal_constant_output_to_input_travel_ratio": round(ratio, 6),
            "spring_force_n_at_feeder_strokes_mm_for_constant_ratio": [
                {"stroke_mm": row["stroke_mm"],
                 "spring_force_n": round(force, 3),
                 "ideal_constant_ratio_input_force_n": round(input_force, 3)}
                for row, force, input_force in zip(rows, forces, ideal_input_forces)
            ],
            "ideal_constant_ratio_input_force_n_at_full_feed":
                round(ideal_input_forces[-1], 3),
            "spring_work_j_per_forward_stroke": round(spring_work_j, 4),
            "minimum_average_input_force_n_over_nominal_30mm_if_lossless":
                round(spring_work_j * 1000 / motor_nominal_stroke, 3),
            "listed_electrical_power_w_unverified": listed_power_w,
            "energy_time_s_at_listed_power_if_100pct_efficient_and_no_storage":
                round(spring_work_j / listed_power_w, 4),
            "real_motor_force_requirement":
                "depends on the actual linkage Jacobian plus loss, feeder friction, "
                "ball load, gravity, acceleration and margin",
        },
        "archived_seller_gallery_unverified": gallery,
        "seller_claims_cannot_be_combined_as_one_operating_point": {
            "if_4kgf_holds_through_full_30mm_work_j": round(seller_full_stroke_work_j, 4),
            "if_120_means_symmetric_full_cycles_per_min_forward_time_s":
                round(seller_forward_time_if_symmetric_full_cycle_s, 4),
            "mechanical_power_then_required_w": round(seller_forward_power_if_full_force_w, 3),
            "listed_rated_electrical_power_w": listed_power_w,
            "simultaneous_full_force_and_full_speed_possible_at_rated_power":
                seller_forward_power_if_full_force_w <= listed_power_w,
            "stall_input_w_if_3_7v_is_maintained_at_seller_current_range":
                [round(3.7 * current, 2)
                 for current in gallery["image_06_claims"]["stall_current_a"]],
            "spring_only_average_mechanical_power_w_if_symmetric_120_full_cycles_per_min":
                round(spring_work_j / seller_forward_time_if_symmetric_full_cycle_s, 3),
            "spring_only_minimum_electrical_to_mechanical_efficiency_at_that_speed":
                round(spring_work_j / seller_forward_time_if_symmetric_full_cycle_s
                      / listed_power_w, 3),
            "interpretation": "Conditional energy check only: seller force may be peak/static and '120 times' may not mean full cycles. Neither a loaded force-speed curve nor driver current rating follows from these claims.",
        },
        "rocker_ratio_candidate_not_packaged": {
            "principle": "same-side two-arm rocker, fixed pivot, captured horizontal slots in both vertical crossheads",
            "input_arm_radius_mm": rocker_input_arm_mm,
            "output_arm_radius_mm": rocker_output_arm_mm,
            "swing_from_minus_to_plus_deg": round(math.degrees(rocker_half_swing_rad), 4),
            "input_vertical_stroke_mm": motor_nominal_stroke,
            "output_vertical_stroke_mm": round(rocker_output_stroke_mm, 4),
            "maximum_input_pin_lateral_excursion_mm": round(rocker_input_lateral_mm, 4),
            "maximum_output_pin_lateral_excursion_mm": round(rocker_output_lateral_mm, 4),
            "minimum_pin_center_slot_travel_mm": {
                "input": round(rocker_input_lateral_mm, 4),
                "output": round(rocker_output_lateral_mm, 4),
            },
            "pin_diameter_end_margin_and_friction_not_included": True,
            "sampled_positions": rocker_samples,
            "ideal_full_feed_spring_only_motor_force_n": round(ideal_input_forces[-1], 3),
            "ideal_full_feed_spring_only_pivot_vertical_reaction_n":
                round(forces[-1]-ideal_input_forces[-1], 3),
            "real_actuator_case_and_rod_end_fitted": False,
            "carriage_rocker_pivot_and_overtravel_fitted": False,
            "loaded_force_and_friction_verified": False,
        },
        "endpoint_interval_contract": {
            "scope": "Mathematical requirement for an affine input/output map when each cycle consumes the entire motor stroke without precise feedback stopping; examples are not measured BY141-3 tolerance",
            "rigid_exact_both_endpoints_for_nonzero_stroke_spread_possible": False,
            "proof": "To reach feeder travel F at minimum motor stroke Smin, ratio r >= F/Smin. To avoid forcing the full stop at maximum stroke Smax with a rigid coupling, r <= F/Smax. For Smax > Smin both inequalities cannot hold simultaneously.",
            "minimum_full_stop_compliance_formula_if_shortest_stroke_must_reach":
                "F*(Smax/Smin-1), excluding phase, motor coast, print clearance, spring deflection and ball load",
            "hypothetical_examples": endpoint_examples,
            "actual_selected_sku_stroke_interval_measured": False,
            "actual_motor_stop_distance_measured": False,
            "compliance_or_adjustable_lost_motion_designed": False,
        },
        "missing_for_one_pass_design": [
            "Actual motor extension and retraction travel extrema, including tolerance and stop phase",
            "Whether powered motion is self-cycling or direction-commanded, and whether rod drives both ways",
            "Rated and starting/blocked rod force versus speed over the whole travel",
            "Case mounting datum and holes, rod axis, retained rod-end interface",
            "Stall current and safe braking/coast behavior at the chosen supply",
            "Confirm whether the shared Y141#/141# gallery applies to selected BY141-3, including 96.5 versus 99 mm length",
            "Measured assembled feeder force versus position with ball, airflow and intended grip orientation",
            "Actual near-home sensor transition and motor stopping distance",
        ],
        "motor_mount_designed": False,
        "positive_two_way_coupling_designed": False,
        "motor_force_sufficient": None,
        "full_stroke_no_overrun": None,
        "manufacturing_release": False,
        "physical_acceptance": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"spring-only constant-ratio input at full feed: {ideal_input_forces[-1]:.3f} N; "
          f"motor approval OPEN; {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
