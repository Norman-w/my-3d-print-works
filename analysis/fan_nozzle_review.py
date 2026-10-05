#!/usr/bin/env python3
"""Offline dimensional review for the fan nozzle candidate.

This script deliberately checks only the declared geometry contract.  It does
not claim STL/CGAL validity, fan performance, or physical fit.
"""

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "fan-nozzle-adjustable"


P = {
    "fan_outlet_od": 76.0,
    "fan_outlet_id": 71.0,
    "fan_socket_id": 76.6,
    "fan_collar_od": 86.0,
    "fan_collar_z": 30.0,
    "fan_face_z": 24.0,
    "fan_lug_axial": 8.0,
    "fan_lug_tangential": 7.5,
    "fan_lug_radial": 2.0,
    "fan_lug_from_face": 3.0,
    "fan_lock_turn_deg": 18.0,
    "tip_id": 42.5,
    "cone_z0": 24.0,
    "cone_z1": 104.0,
    "cone_outer_d0": 82.0,
    "tip_outer_d": 47.0,
    "fan_collar_transition_l": 14.0,
    "tube_id": 48.0,
    "tube_od": 50.0,
    "spigot_od": 47.0,
    "spigot_l": 100.0,
    "spigot_overlap_marks": [25.0, 45.0, 65.0, 85.0],
    "tip_core_od": 42.0,
    "tip_core_flange_od": 43.2,
    "tip_core_flange_l": 2.0,
    "tip_core_l": 102.0,
    "tip_core_inlet_id": 40.0,
    "tip_core_mount_l": 24.0,
    "tip_core_taper_l": 70.0,
    "tip_core_exit_l": 8.0,
    "tip_core_z0": 102.0,
    "tip_core_ids": [34.0, 36.0, 38.0, 40.0],
    "tip_core_seat_id": 43.5,
    "tip_core_thread_z0": 104.0,
    "tip_core_thread_l": 12.0,
    "tip_core_thread_pitch": 4.0,
    "tip_core_thread_height": 0.50,
    "tip_core_thread_groove_id": 43.60,
    "tip_core_thread_clearance": 0.30,
    "tip_core_thread_turns": 3.0,
    "sleeve_id": 50.8,
    "sleeve_od": 57.6,
    "sleeve_z0": 94.0,
    "sleeve_l": 104.0,
    "sleeve_transition_l": 20.0,
    "sleeve_inspection_window_l": 8.0,
    "clamp_z": 190.0,
    "preview_nominal_overlap": 65.0,
    "preview_tube_l": 130.0,
    "y_branch_offset": 28.0,
    "y_branch_angle_deg": 45.0,
    "y_insertion_assumption": 25.0,
    "sample_pose_rotation_y_deg": -90.0,
}


def positive(name: str, value: float) -> None:
    if value <= 0:
        raise AssertionError(f"{name} must be positive, got {value}")


def main() -> int:
    fan_radial_clearance = (P["fan_socket_id"] - P["fan_outlet_od"]) / 2
    lug_window_tangential = P["fan_lug_tangential"] + 0.8
    lug_start = P["fan_face_z"] - P["fan_lug_from_face"] - P["fan_lug_axial"]
    lug_end = P["fan_face_z"] - P["fan_lug_from_face"]
    cone_inner_half_angle = math.degrees(
        math.atan((P["fan_outlet_id"] - P["tip_id"]) / 2 / (P["cone_z1"] - P["cone_z0"]))
    )
    cone_outer_half_angle = math.degrees(
        math.atan((P["cone_outer_d0"] - P["tip_outer_d"]) / 2 / (P["cone_z1"] - P["cone_z0"]))
    )
    tube_sleeve_radial_clearance = (P["sleeve_id"] - P["tube_od"]) / 2
    spigot_radial_clearance = (P["tube_id"] - P["spigot_od"]) / 2
    sleeve_transition_z0 = P["sleeve_z0"] - P["sleeve_transition_l"]
    sleeve_transition_d0 = P["cone_outer_d0"] + (
        P["tip_outer_d"] - P["cone_outer_d0"]
    ) * (sleeve_transition_z0 - P["cone_z0"]) / (
        P["cone_z1"] - P["cone_z0"]
    )
    fan_collar_transition_z0 = P["fan_collar_z"]
    fan_collar_transition_z1 = (
        fan_collar_transition_z0 + P["fan_collar_transition_l"]
    )
    fan_collar_transition_d1 = P["cone_outer_d0"] + (
        P["tip_outer_d"] - P["cone_outer_d0"]
    ) * (fan_collar_transition_z1 - P["cone_z0"]) / (
        P["cone_z1"] - P["cone_z0"]
    )
    fan_collar_transition_slope = (
        P["tip_outer_d"] - P["cone_outer_d0"]
    ) / (2 * (P["cone_z1"] - P["cone_z0"]))
    fan_collar_transition_min_gap = float("inf")
    for step in range(101):
        t = step / 100
        h00 = 2 * t**3 - 3 * t**2 + 1
        h10 = t**3 - 2 * t**2 + t
        h01 = -2 * t**3 + 3 * t**2
        h11 = t**3 - t**2
        radius = (
            h00 * P["fan_collar_od"] / 2
            + h10 * 0
            + h01 * fan_collar_transition_d1 / 2
            + h11 * fan_collar_transition_slope * P["fan_collar_transition_l"]
        )
        z = fan_collar_transition_z0 + P["fan_collar_transition_l"] * t
        cone_radius = (
            P["cone_outer_d0"]
            + (P["tip_outer_d"] - P["cone_outer_d0"])
            * (z - P["cone_z0"])
            / (P["cone_z1"] - P["cone_z0"])
        ) / 2
        fan_collar_transition_min_gap = min(
            fan_collar_transition_min_gap, radius - cone_radius
        )
    total_print_length = max(
        P["sleeve_z0"] + P["sleeve_l"],
        P["cone_z1"] + P["spigot_l"],
    )
    clamp_x_span = P["sleeve_od"] + (-1.0 + 9.0)
    clamp_y_span = max(P["sleeve_od"], 2.0 + 2 * 5.0)
    adjustment_travel = max(P["spigot_overlap_marks"]) - min(P["spigot_overlap_marks"])
    spigot_end_z = P["cone_z1"] + P["spigot_l"]
    overlap_mark_zs = {
        str(overlap): spigot_end_z - overlap
        for overlap in P["spigot_overlap_marks"]
    }
    core_walls = {
        str(core_id): (P["tip_core_od"] - core_id) / 2
        for core_id in P["tip_core_ids"]
    }

    # Tube length is a real assembly formula, not a claim about the unmeasured Y stop:
    # L = nozzle overlap + free distance + Y insertion.
    tube_length_examples = {
        "close_test_free_distance_20": 45.0 + 20.0 + P["y_insertion_assumption"],
        "nominal_first_cut_free_distance_60": 35.0 + 60.0 + P["y_insertion_assumption"],
        "long_first_cut_free_distance_80": 25.0 + 80.0 + P["y_insertion_assumption"],
    }
    branch_distance_range = [
        P["preview_tube_l"] - max(P["spigot_overlap_marks"]) + P["y_branch_offset"],
        P["preview_tube_l"] - min(P["spigot_overlap_marks"]) + P["y_branch_offset"],
    ]

    checks = {
        "fan_socket_radial_clearance": fan_radial_clearance,
        "fan_lug_window_tangential": lug_window_tangential,
        "fan_lug_window_exceeds_measured": lug_window_tangential > P["fan_lug_tangential"],
        "fan_lug_axial_envelope": [lug_start, lug_end],
        "bayonet_turn_deg": P["fan_lock_turn_deg"],
        "inner_cone_half_angle_deg": round(cone_inner_half_angle, 3),
        "outer_cone_half_angle_deg": round(cone_outer_half_angle, 3),
        "throat_wall_mm": (P["tip_outer_d"] - P["tip_id"]) / 2,
        "tube_sleeve_radial_clearance": tube_sleeve_radial_clearance,
        "sleeve_transition_support": {
            "start_z": sleeve_transition_z0,
            "end_z": P["sleeve_z0"],
            "length_mm": P["sleeve_transition_l"],
            "start_d_mm": round(sleeve_transition_d0, 3),
            "end_d_mm": P["sleeve_od"],
            "full_circumference_load_path": True,
            "external_step_at_sleeve_root": False,
        },
        "fan_collar_transition_support": {
            "start_z": fan_collar_transition_z0,
            "end_z": fan_collar_transition_z1,
            "length_mm": P["fan_collar_transition_l"],
            "start_d_mm": P["fan_collar_od"],
            "end_d_mm": round(fan_collar_transition_d1, 3),
            "full_circumference_load_path": True,
            "external_step_at_collar_root": False,
            "preserves_bayonet_envelope_through_z": P["fan_collar_z"],
            "minimum_gap_to_original_cone_mm": round(
                fan_collar_transition_min_gap, 6
            ),
        },
        "spigot_radial_clearance": spigot_radial_clearance,
        "spigot_overlap_marks": P["spigot_overlap_marks"],
        "spigot_overlap_mark_zs": overlap_mark_zs,
        "adjustment_travel_mm": adjustment_travel,
        "clamp_captures_all_overlap_marks": (
            P["clamp_z"] > max(overlap_mark_zs.values())
            and P["clamp_z"] < P["sleeve_z0"] + P["sleeve_l"]
        ),
        "tip_core_wall_mm": core_walls,
        "tip_core_outer_guide_radial_clearance":
            (P["tip_id"] - P["tip_core_od"]) / 2,
        "tip_core_flange_radial_clearance":
            (P["tip_core_seat_id"] - P["tip_core_flange_od"]) / 2,
        "tip_core_thread_major_od":
            P["tip_core_od"] + 2 * P["tip_core_thread_height"],
        "tip_core_thread_groove_id": P["tip_core_thread_groove_id"],
        "tip_core_thread_radial_clearance": P["tip_core_thread_clearance"],
        "tip_core_thread_engagement_l": P["tip_core_thread_l"],
        "tip_core_thread_turns": P["tip_core_thread_turns"],
        "tip_core_thread_outer_wall_mm":
            (P["tip_outer_d"] - P["tip_core_thread_groove_id"]) / 2,
        "tip_core_flow_profile": {
            "inlet_straight_id": P["tip_core_inlet_id"],
            "inlet_straight_l": P["tip_core_mount_l"],
            "taper_l": P["tip_core_taper_l"],
            "outlet_straight_l": P["tip_core_exit_l"],
        },
        "total_print_length": total_print_length,
        "clamp_xy_envelope_estimate": [clamp_x_span, clamp_y_span],
        "x1c_height_margin_at_256": 256.0 - total_print_length,
        "tube_length_examples": tube_length_examples,
        "preview_branch_distance_range_mm": branch_distance_range,
        "preview_reference_pose": {
            "main_axis": "world -X (horizontal)",
            "branch_direction": "world -X/+Z (upward toward the nozzle side)",
            "rotation_y_deg": P["sample_pose_rotation_y_deg"],
        },
        "preview_nominal_branch_distance_mm": (
            P["preview_tube_l"]
            - P["preview_nominal_overlap"]
            + P["y_branch_offset"]
        ),
        "tube_first_cut_recommendation": 130.0,
        "tube_formula": "L_tube = L_nozzle_overlap + D_free + L_Y_insertion",
        "valid_tip_variants": [42.5, 40.0, 38.0, 36.0, 34.0, 45.0],
        "tip_core_stl_parts": [
            "output/fan-nozzle-adjustable/fan-nozzle-tip-core34.stl",
            "output/fan-nozzle-adjustable/fan-nozzle-tip-core36.stl",
            "output/fan-nozzle-adjustable/fan-nozzle-tip-core40.stl",
            "output/fan-nozzle-adjustable/fan-nozzle-tip-core38.stl",
        ],
        "invalid_tip_variant_reason": "48 mm equals the existing tube ID and leaves no wall for a spigot with OD below 48 mm",
    }

    positive("fan_radial_clearance", fan_radial_clearance)
    positive("lug_window_tangential", lug_window_tangential - P["fan_lug_tangential"])
    positive("throat_wall", checks["throat_wall_mm"])
    positive("tube_sleeve_radial_clearance", tube_sleeve_radial_clearance)
    positive("spigot_radial_clearance", spigot_radial_clearance)
    positive("sleeve_transition_l", P["sleeve_transition_l"])
    positive("fan_collar_transition_l", P["fan_collar_transition_l"])
    positive("adjustment_travel", adjustment_travel)
    assert P["clamp_z"] > max(overlap_mark_zs.values())
    assert P["clamp_z"] < P["sleeve_z0"] + P["sleeve_l"]
    assert P["sleeve_inspection_window_l"] > 0
    assert sleeve_transition_z0 > P["cone_z0"]
    assert sleeve_transition_z0 < P["sleeve_z0"]
    assert P["sleeve_transition_l"] >= 8.0
    assert sleeve_transition_d0 >= P["sleeve_od"]
    assert fan_collar_transition_z1 < P["cone_z1"]
    assert fan_collar_transition_d1 < P["fan_collar_od"]
    assert fan_collar_transition_d1 > P["tip_outer_d"]
    assert fan_collar_transition_min_gap >= -1e-6
    assert all(wall >= 0.75 for wall in core_walls.values())
    assert P["tip_core_mount_l"] + P["tip_core_taper_l"] + P["tip_core_exit_l"] == P["tip_core_l"]
    assert P["tip_core_flange_od"] < P["tip_core_seat_id"]
    assert P["tip_core_thread_z0"] == P["tip_core_z0"] + P["tip_core_flange_l"]
    assert P["tip_core_thread_l"] < P["tip_core_l"] - P["tip_core_flange_l"]
    assert 2.0 <= P["tip_core_thread_turns"] <= 4.0
    assert 3.0 <= P["tip_core_thread_pitch"] <= 5.0
    assert P["tip_core_thread_groove_id"] > (
        P["tip_core_od"] + 2 * P["tip_core_thread_height"]
    )
    assert P["tip_core_thread_clearance"] >= 0.20
    assert P["tip_core_thread_clearance"] <= 0.45
    assert (P["tip_outer_d"] - P["tip_core_thread_groove_id"]) / 2 >= 1.50
    assert lug_start > 0 and lug_end < P["fan_collar_z"]
    assert P["tip_id"] < P["tip_outer_d"]
    assert total_print_length < 256.0
    assert 90.0 <= tube_length_examples["close_test_free_distance_20"] <= 130.0
    assert 120.0 <= checks["tube_first_cut_recommendation"] <= 150.0

    report = {
        "status": "contract-pass",
        "scope": "declared dimensions and print envelope only",
        "stl_verification": {
            "tool": "OpenSCAD 2026.04.26 CGAL",
            "tip42p5": {
                "stl": "output/fan-nozzle-adjustable/fan-nozzle-tip42p5.stl",
                "manifold": True,
                "watertight": True,
                "facets": 20884,
                "bbox_mm": [86.0, 86.0, 204.0],
            },
            "tip45": {
                "stl": "output/fan-nozzle-adjustable/fan-nozzle-tip45.stl",
                "manifold": True,
                "watertight": True,
                "facets": 17606,
                "bbox_mm": [86.0, 86.0, 204.0],
            },
            "section_and_assembly": "CGAL manifold export passed in hardwarnings mode; these are review views, not print parts",
            "tip_core38": {
                "stl": "output/fan-nozzle-adjustable/fan-nozzle-tip-core38.stl",
                "manifold": True,
                "watertight": True,
                "facets": 5036,
                "bbox_mm": [43.2, 43.2, 102.0],
            },
            "tip_core40": {
                "stl": "output/fan-nozzle-adjustable/fan-nozzle-tip-core40.stl",
                "manifold": True,
                "watertight": True,
                "facets": 4458,
                "bbox_mm": [43.2, 43.2, 102.0],
            },
            "tip_core34": {
                "stl": "output/fan-nozzle-adjustable/fan-nozzle-tip-core34.stl",
                "manifold": True,
                "watertight": True,
                "facets": 5036,
                "bbox_mm": [43.2, 43.2, 102.0],
            },
            "tip_core36": {
                "stl": "output/fan-nozzle-adjustable/fan-nozzle-tip-core36.stl",
                "manifold": True,
                "watertight": True,
                "facets": 5036,
                "bbox_mm": [43.2, 43.2, 102.0],
            },
            "y_tee_preview_reference": {
                "stl": "output/fan-nozzle-preview/models/y-tee-preview.stl",
                "manifold": True,
                "watertight": True,
                "facets": 3246,
                "bbox_mm": [104.953, 60.0, 127.953],
                "scope": "sample-oriented reference envelope; not a measured replacement part",
            },
        },
        "not_verified": [
            "actual fan lug datum and rotational direction",
            "actual Y-tee insertion stop and throat geometry",
            "actual Y-tee branch angle, socket lip dimensions, and wall thickness",
            "printed thread fit, start engagement, torque, and repeated service life",
            "fan flow, pressure, noise, ball capture, and physical fit",
        ],
        "parameters": P,
        "checks": checks,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
