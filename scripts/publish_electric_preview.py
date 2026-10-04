#!/usr/bin/env python3
"""Publish the selected non-Bowden printed parts to the existing LAN viewer.

The older Bowden motion scene remains available as explicitly historical.
This publication does not claim a motor mount, print release, or physical test.
"""

from __future__ import annotations

import copy
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "output/revision-review"
OLD_REPORT = ROOT / "output/cable-scene-export/20260927T153058669616Z/report.json"
CURRENT_REPORT = ROOT / "output/electric-feeder/review.json"
TRIGGER_REPORT = ROOT / "output/electronic-trigger-candidate/review.json"
TRIGGER_SLICE = ROOT / "output/electronic-trigger-candidate/slice-review.json"
TRIGGER_RENDER = ROOT / "output/electronic-trigger-candidate/render-report.json"
TRIGGER_RELEASE = ROOT / "output/electronic-trigger-candidate/release-margin.json"
TRIGGER_FSM = ROOT / "output/electronic-trigger-candidate/point-shot-fsm.json"
TRIGGER_CORE = ROOT / "output/electronic-trigger-candidate/point-shot-core-review.json"
TRIGGER_CORE_DOC = ROOT / "firmware/README.md"
TRIGGER_INTEGRATION = ROOT / "output/electric-trigger-integration/review.json"
WIRE_RELIEF_ROOT = ROOT / "output/electronic-trigger-wire-relief"
WIRE_RELIEF_REPORT = WIRE_RELIEF_ROOT / "review.json"
WIRE_RELIEF_SLICE = WIRE_RELIEF_ROOT / "slice-review.json"
TRIGGER_FASTENER_ROOT = ROOT / "output/electronic-trigger-fastener-access"
TRIGGER_FASTENER_REPORT = TRIGGER_FASTENER_ROOT / "review.json"
OPTICAL_BUDGET = ROOT / "output/optical-home-candidate/transition-budget.json"
OPTICAL_REVIEW = ROOT / "output/optical-home-candidate/review.json"
PARTIAL_RETURN = ROOT / "output/analysis/point-shot-interlock.json"
DRIVE_REPORT = ROOT / "output/electric-drive-feasibility/report.json"
BY141_LIVE_SKU_AUDIT = ROOT / "output/procurement/reciprocating-20261001/live-sku-interface-audit.json"
DRIVER_SCREEN = ROOT / "output/electric-drive-feasibility/driver-screen.json"
ROUTE_REPORT = ROOT / "output/electric-drive-route/review.json"
ENVELOPE_REPORT = ROOT / "output/by141-envelope-screen/review.json"
ENVELOPE_IMAGE = ROOT / "output/by141-envelope-screen/context.png"
HOME_SWITCH_REPORT = ROOT / "output/electric-home-switch-screen/review.json"
HOME_SWITCH_HOME_IMAGE = ROOT / "output/electric-home-switch-screen/home-context.png"
HOME_SWITCH_U1_IMAGE = ROOT / "output/electric-home-switch-screen/one-mm-context.png"
FULL_SWITCH_REPORT = ROOT / "output/electric-full-stroke-switch-screen/review.json"
FULL_SWITCH_FULL_IMAGE = ROOT / "output/electric-full-stroke-switch-screen/full-context.png"
FULL_SWITCH_BEFORE_IMAGE = ROOT / "output/electric-full-stroke-switch-screen/one-mm-before-context.png"
FRONT_SWITCH_REJECTED_REPORT = ROOT / "output/electric-end-switch-cap-candidate/review.json"
SIDE_SWITCH_ROOT = ROOT / "output/electric-end-switch-side-cap"
SIDE_SWITCH_REPORT = SIDE_SWITCH_ROOT / "review.json"
SIDE_SWITCH_SLICE = SIDE_SWITCH_ROOT / "slice-review.json"
ENDPOINT_SIGNAL = SIDE_SWITCH_ROOT / "signal-window.json"
SIDE_SWITCH_IMAGES = (
    "at-home.png", "at-full.png", "at-home-detail.png", "at-full-detail.png",
)
SIDE_SWITCH_MESHES = ("cap", "carriage")
SIDE_SWITCH_3MF = (
    "slices/cap-tree-support/slice-review.3mf",
    "slices/carriage-tree-support/slice-review.3mf",
)
ROCKER_BRIDGE_ROOT = ROOT / "output/electric-rocker-bridge-screen"
ROCKER_BRIDGE_REPORT = ROCKER_BRIDGE_ROOT / "review.json"
ROCKER_BRIDGE_IMAGES = ("r75-y62-home.png", "r75-y62-full.png")
ROCKER_PIVOT_ROOT = ROOT / "output/electric-rocker-pivot-mount-screen"
ROCKER_PIVOT_REPORT = ROCKER_PIVOT_ROOT / "review.json"
ROCKER_PIVOT_IMAGES = ("pivot-home.png", "pivot-full.png")
ROCKER_JOINT_ROOT = ROOT / "output/electric-rocker-pivot-joint-screen"
ROCKER_JOINT_REPORT = ROCKER_JOINT_ROOT / "review.json"
ROCKER_JOINT_IMAGES = ("joint-y62-mid.png", "joint-y65-mid.png")
ROCKER_PIN_ROOT = ROOT / "output/electric-rocker-pin-retention-screen"
ROCKER_PIN_REPORT = ROCKER_PIN_ROOT / "review.json"
ROCKER_PIN_IMAGE = ROCKER_PIN_ROOT / "front-head-rear-ring-mid.png"
ROCKER_CLAMP_ROOT = ROOT / "output/electric-rocker-clamped-fork-screen"
ROCKER_CLAMP_REPORT = ROCKER_CLAMP_ROOT / "review.json"
ROCKER_CLAMP_IMAGES = ("home.png", "mid.png", "full.png", "detail.png")
OUTPUT_CROSSHEAD_ROOT = ROOT / "output/electric-output-crosshead-screen"
OUTPUT_CROSSHEAD_REPORT = OUTPUT_CROSSHEAD_ROOT / "review.json"
OUTPUT_CROSSHEAD_SLICE = OUTPUT_CROSSHEAD_ROOT / "slice-review.json"
OUTPUT_CROSSHEAD_ASSEMBLY = OUTPUT_CROSSHEAD_ROOT / "assembly-review.json"
OUTPUT_PIN_LOAD = OUTPUT_CROSSHEAD_ROOT / "pin-retention-load-screen.json"
OUTPUT_CROSSHEAD_3MF = OUTPUT_CROSSHEAD_ROOT / "slices/carriage-x-plus-90-tree/slice-review.3mf"
OUTPUT_CROSSHEAD_SLICE_IMAGE = OUTPUT_CROSSHEAD_ROOT / "slices/carriage-x-plus-90-tree/plate-preview.png"
OUTPUT_CROSSHEAD_IMAGES = (
    "home.png", "mid.png", "full.png", "crosshead-front.png",
    "crosshead-top.png", "crosshead-iso.png",
)
SERVICE_FORK_ROOT = ROOT / "output/electric-rocker-service-fork-screen"
SERVICE_FORK_REPORT = SERVICE_FORK_ROOT / "review.json"
SERVICE_FORK_SLICE = SERVICE_FORK_ROOT / "slice-review.json"
SERVICE_FORK_LOAD = SERVICE_FORK_ROOT / "load-screen.json"
SERVICE_FORK_ORIENTATION = SERVICE_FORK_ROOT / "orientation-screen.json"
SERVICE_FORK_REINFORCEMENT_ROOT = ROOT / "output/electric-rocker-service-fork-reinforcement-screen"
SERVICE_FORK_REINFORCEMENT_REPORT = SERVICE_FORK_REINFORCEMENT_ROOT / "review.json"
SERVICE_FORK_ROOT_SECTION = SERVICE_FORK_REINFORCEMENT_ROOT / "root-section-screen.json"
SERVICE_FORK_ROOT_WEB_ROOT = ROOT / "output/electric-rocker-root-gusset-screen"
SERVICE_FORK_ROOT_WEB_REPORT = SERVICE_FORK_ROOT_WEB_ROOT / "review.json"
SERVICE_FORK_ROOT_WEB_SECTION = SERVICE_FORK_ROOT_WEB_ROOT / "root-web-section.json"
SERVICE_FORK_ROOT_WEB_ORIENTATION = SERVICE_FORK_ROOT_WEB_ROOT / "orientation-screen.json"
SERVICE_FORK_ROOT_WEB_X55 = (SERVICE_FORK_ROOT_WEB_ROOT / "slice-screen"
                             / "orientation-screen/base-x-plus-55-tree")
SERVICE_FORK_X40_PREVIEW = SERVICE_FORK_ROOT / "orientation-screen/base-x-plus-40-tree/plate-preview.png"
SERVICE_FORK_IMAGES = (
    "rocker-entry.png", "rocker-seated.png", "rear-seated.png",
    "base-front.png", "base-nut-face.png", "base-top.png", "base-iso.png",
    "rear-front.png", "rear-top.png", "rear-iso.png",
)
ROCKER_PLANE_REPORT = ROOT / "output/electric-rocker-plane-screen/review.json"
ROCKER_PLANE_IMAGE = ROOT / "output/electric-rocker-plane-screen/outer-plane-context.png"
SPRING_REPORT = ROOT / "output/feeder-return-spring/feeder-return-spring-service-report.json"
INVENTORY = ROOT / "docs/electric-assembly-inventory.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_sources(hashes: dict[str, str]) -> None:
    for name, expected in hashes.items():
        if sha(ROOT / name) != expected:
            raise RuntimeError(f"Source changed since geometry review: {name}")


def scad_scalar(source: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(-?\d+(?:\.\d+)?);", source, re.M)
    if not match:
        raise RuntimeError(f"Electronic trigger scene parameter is missing: {name}")
    return float(match.group(1))


def trigger_scene_parameters() -> dict:
    cad = ROOT / "cad/electronic-trigger-candidate.scad"
    source = cad.read_text()
    pivot_match = re.search(r"^et_pivot\s*=\s*(\[[^\]]+\]);", source, re.M)
    if not pivot_match:
        raise RuntimeError("Electronic trigger pivot is missing")
    pivot = json.loads(pivot_match.group(1))
    if len(pivot) != 3 or pivot != [58, -52, -10]:
        raise RuntimeError("Electronic trigger pivot needs a new scene review")
    if "et_switch_z+12.8" not in source:
        raise RuntimeError("Electronic trigger switch height needs a new scene review")
    names = (
        "et_switch_x", "et_switch_y", "et_switch_z",
        "et_switch_case_depth_x", "et_switch_case_depth_y",
        "et_switch_terminal_length_x", "et_switch_terminal_width_z",
        "et_switch_terminal_thickness_y", "et_switch_terminal_first_z_offset",
        "et_switch_terminal_pitch_z", "et_switch_actuator_op",
        "et_switch_actuator_z", "et_spring_od", "et_spring_center_y",
        "et_spring_center_z", "et_spring_fixed_seat_x",
        "et_spring_moving_seat_x", "et_pivot_spacer_od",
        "et_pivot_spacer_length",
    )
    return {"pivot_mm": pivot, "switch_case_height_z_mm": 12.8,
            **{name: scad_scalar(source, name) for name in names}}


def main() -> int:
    old = json.loads(OLD_REPORT.read_text())
    current = json.loads(CURRENT_REPORT.read_text())
    trigger = json.loads(TRIGGER_REPORT.read_text())
    trigger_slice = json.loads(TRIGGER_SLICE.read_text())
    trigger_render = json.loads(TRIGGER_RENDER.read_text())
    trigger_release = json.loads(TRIGGER_RELEASE.read_text())
    trigger_fsm = json.loads(TRIGGER_FSM.read_text())
    trigger_core = json.loads(TRIGGER_CORE.read_text())
    integration = json.loads(TRIGGER_INTEGRATION.read_text())
    wire_relief = json.loads(WIRE_RELIEF_REPORT.read_text())
    wire_relief_slice = json.loads(WIRE_RELIEF_SLICE.read_text())
    trigger_fastener = json.loads(TRIGGER_FASTENER_REPORT.read_text())
    optical_budget = json.loads(OPTICAL_BUDGET.read_text())
    drive = json.loads(DRIVE_REPORT.read_text())
    driver_screen = json.loads(DRIVER_SCREEN.read_text())
    route = json.loads(ROUTE_REPORT.read_text())
    envelope = json.loads(ENVELOPE_REPORT.read_text())
    home_switch = json.loads(HOME_SWITCH_REPORT.read_text())
    full_switch = json.loads(FULL_SWITCH_REPORT.read_text())
    front_switch_rejected = json.loads(FRONT_SWITCH_REJECTED_REPORT.read_text())
    side_switch = json.loads(SIDE_SWITCH_REPORT.read_text())
    side_switch_slice = json.loads(SIDE_SWITCH_SLICE.read_text())
    endpoint_signal = json.loads(ENDPOINT_SIGNAL.read_text())
    rocker_bridge = json.loads(ROCKER_BRIDGE_REPORT.read_text())
    rocker_pivot = json.loads(ROCKER_PIVOT_REPORT.read_text())
    rocker_joint = json.loads(ROCKER_JOINT_REPORT.read_text())
    rocker_pin = json.loads(ROCKER_PIN_REPORT.read_text())
    rocker_clamp = json.loads(ROCKER_CLAMP_REPORT.read_text())
    output_crosshead = json.loads(OUTPUT_CROSSHEAD_REPORT.read_text())
    output_crosshead_slice = json.loads(OUTPUT_CROSSHEAD_SLICE.read_text())
    output_crosshead_assembly = json.loads(OUTPUT_CROSSHEAD_ASSEMBLY.read_text())
    output_pin_load = json.loads(OUTPUT_PIN_LOAD.read_text())
    service_fork = json.loads(SERVICE_FORK_REPORT.read_text())
    service_fork_slice = json.loads(SERVICE_FORK_SLICE.read_text())
    service_fork_load = json.loads(SERVICE_FORK_LOAD.read_text())
    service_fork_orientation = json.loads(SERVICE_FORK_ORIENTATION.read_text())
    service_fork_reinforcement = json.loads(SERVICE_FORK_REINFORCEMENT_REPORT.read_text())
    service_fork_root_section = json.loads(SERVICE_FORK_ROOT_SECTION.read_text())
    service_fork_root_web = json.loads(SERVICE_FORK_ROOT_WEB_REPORT.read_text())
    service_fork_root_web_section = json.loads(SERVICE_FORK_ROOT_WEB_SECTION.read_text())
    service_fork_root_web_orientation = json.loads(
        SERVICE_FORK_ROOT_WEB_ORIENTATION.read_text())
    rocker_plane = json.loads(ROCKER_PLANE_REPORT.read_text())
    inventory = json.loads(INVENTORY.read_text())
    if old["status"] != "CURRENT_SCENE_EXPORT_PASS" or not old["sources_stable"]:
        raise RuntimeError("Historical common-part mesh export is not a passed snapshot")
    if not current["geometry_review_pass"] or current["probe_count"] != 71:
        raise RuntimeError("Electric feeder geometry review is not current and passed")
    if trigger["status"] != "TRIGGER_CANDIDATE_GEOMETRY_PASS_UNRELEASED" \
            or trigger["probe_count"] != 79 or not trigger["current_inventory_promoted"]:
        raise RuntimeError("Selected electronic trigger has not passed unreleased review")
    trigger_scad = (ROOT / "cad/electronic-trigger-candidate.scad").read_text()
    if scad_scalar(trigger_scad, "et_switch_y") != scad_scalar(
            trigger_scad, "et_backplate_front_y"):
        raise RuntimeError("Electronic trigger switch does not seat on its backplate")
    if integration["status"] != "SELECTED_TRIGGER_GEOMETRY_PASS_UNRELEASED" \
            or integration["probe_count"] != 16 \
            or integration["trigger_geometry_review_sha256"] != sha(TRIGGER_REPORT) \
            or not integration["old_beam_replaced_not_coinstalled"] \
            or integration["manufacturing_release"]:
        raise RuntimeError("Integrated electronic trigger review is missing or stale")
    if integration["assembly_image"]["sha256"] != sha(
            ROOT / "output/electric-trigger-integration/current-assembly.png"):
        raise RuntimeError("Integrated assembly image is stale")
    if wire_relief["status"] != "WIRE_RELIEF_NOMINAL_GEOMETRY_ONLY" \
            or wire_relief["predecessor_sha256"] != {
                "output/electronic-trigger-candidate/review.json": sha(TRIGGER_REPORT),
                "output/electric-trigger-integration/review.json": sha(TRIGGER_INTEGRATION),
            } \
            or wire_relief["empty_probe_count"] != 27 \
            or wire_relief["positive_control_count"] != 2 \
            or wire_relief["failures"] \
            or not wire_relief["part"]["watertight"] \
            or wire_relief["part"]["connected_components"] != 1 \
            or wire_relief["part"]["sha256"] != sha(WIRE_RELIEF_ROOT / "beam-candidate.stl") \
            or wire_relief["promoted_to_selected_beam"] is not True \
            or wire_relief["manufacturing_release"] \
            or wire_relief["physical_acceptance"]:
        raise RuntimeError("Wire-relief replacement beam is missing, stale, or overstated")
    checked_sources(wire_relief["source_sha256"])
    for row in wire_relief["images"].values():
        if row["sha256"] != sha(ROOT / row["file"]):
            raise RuntimeError(f"Wire-relief image changed: {row['file']}")
    if wire_relief_slice["status"] != "WIRE_RELIEF_SLICED_UNRELEASED" \
            or wire_relief_slice["geometry_review_sha256"] != sha(WIRE_RELIEF_REPORT) \
            or wire_relief_slice["source_stl_sha256"] != wire_relief["part"]["sha256"] \
            or wire_relief_slice["native_warnings"] \
            or not wire_relief_slice["archive_integrity_pass"] \
            or any(wire_relief_slice[
                "support_extrusion_segments_crossing_tie_holes_with_0p25mm_margin"].values()) \
            or wire_relief_slice["slice_3mf_sha256"] != sha(
                WIRE_RELIEF_ROOT / "slice-x-minus-90-tree/slice-review.3mf") \
            or wire_relief_slice["preview_sha256"] != sha(
                WIRE_RELIEF_ROOT / "slice-x-minus-90-tree/plate-preview.png") \
            or wire_relief_slice["promoted_to_selected_beam"] is not True \
            or wire_relief_slice["printer_sent"] \
            or wire_relief_slice["manufacturing_release"] \
            or wire_relief_slice["physical_acceptance"]:
        raise RuntimeError("Wire-relief offline slice is missing, stale, or overstated")
    checked_sources(wire_relief_slice["source_sha256"])
    if trigger_fastener["status"] != "TRIGGER_M2_ACCESS_NOMINAL_ONLY" \
            or trigger_fastener["predecessor_sha256"] != {
                "output/electronic-trigger-candidate/review.json": sha(TRIGGER_REPORT),
                "output/electric-trigger-integration/review.json": sha(TRIGGER_INTEGRATION),
            } \
            or trigger_fastener["empty_probe_count"] != 102 \
            or trigger_fastener["positive_control_count"] != 2 \
            or trigger_fastener["failures"] \
            or trigger_fastener["image_sha256"] != sha(
                TRIGGER_FASTENER_ROOT / "fastener-access.png") \
            or trigger_fastener["fastener_candidate"]["shank_projection_past_nut_nominal_mm"] != 1.7 \
            or trigger_fastener["fastener_candidate"]["shank_projection_past_nut_case_max_only_mm"] != 1.55 \
            or trigger_fastener["fastener_candidate"]["rear_washer_proxy_diameter_mm"] != 7 \
            or trigger_fastener["fastener_candidate"]["head_proxy_height_mm"] != 2 \
            or trigger_fastener["switch_slot_fit"]["printed_slot_width_nominal_mm"] != 2.8 \
            or trigger_fastener["switch_slot_fit"]["radial_allowance_after_half_pitch_error_before_print_mm"] != .325 \
            or not trigger_fastener["selected_beam_unchanged"] \
            or trigger_fastener["manufacturing_release"] \
            or trigger_fastener["physical_acceptance"]:
        raise RuntimeError("Electronic trigger M2 access review is missing or stale")
    checked_sources(trigger_fastener["source_sha256"])
    if trigger_slice["status"] != "CANDIDATE_SLICED_UNRELEASED" \
            or trigger_slice["printer_sent"] or any(
                not trigger_slice["parts"][name]["slice_generated"]
                or trigger_slice["parts"][name]["source_stl_sha256"]
                != trigger["parts"][name]["sha256"]
                for name in ("beam", "lever")) \
            or trigger_slice["parts"]["beam"]["support_extrusion_segments_crossing_m2_slot_cores_with_0p25mm_margin"] != {
                "lower_m2_slot_core": 0, "upper_m2_slot_core": 0}:
        raise RuntimeError("Electronic trigger slice is missing or does not match reviewed meshes")
    checked_sources(trigger_slice["source_sha256"])
    if trigger_render["status"] != "TRIGGER_CANDIDATE_RENDER_MATCHES_GEOMETRY_REVIEW" \
            or trigger_render["geometry_review_sha256"] != sha(TRIGGER_REPORT) \
            or trigger_render["integration_review_sha256"] != sha(TRIGGER_INTEGRATION):
        raise RuntimeError("Electronic trigger images do not match the current geometry review")
    for image_name, row in trigger_render["images"].items():
        if sha(ROOT / "output/electronic-trigger-candidate" / image_name) != row["sha256"]:
            raise RuntimeError(f"Electronic trigger image changed: {image_name}")
    if trigger_release["status"] != "NOMINAL_RELEASE_MARGIN_PASS_REAL_LEVER_UNVERIFIED" \
            or trigger_release["source"]["cad_sha256"] != sha(ROOT / "cad/electronic-trigger-candidate.scad") \
            or trigger_release["source"]["geometry_review_sha256"] != sha(TRIGGER_REPORT) \
            or trigger_release["source"]["analysis_script_sha256"] \
            != sha(ROOT / "analysis/electronic_trigger_release_margin.py") \
            or trigger_release["manufacturing_release"]:
        raise RuntimeError("Electronic trigger released-state margin is missing or stale")
    if trigger_fsm["status"] != "REFERENCE_CONTROLLER_CONTRACT_ONLY_MISSING_REAL_INPUTS" \
            or trigger_fsm["exhaustive_boolean_input_review"]["checked_transitions"] < 900 \
            or trigger_fsm["optical_blocked_aliased_as_verified_zero"] \
            or trigger_fsm["mcu_firmware_implemented"] \
            or trigger_fsm["power_stage_selected"] \
            or trigger_fsm["manufacturing_release"]:
        raise RuntimeError("Electronic trigger control contract is missing or overstated")
    checked_sources(trigger_fsm["source_sha256"])
    if trigger_core["status"] != "PORTABLE_CORE_MATCHES_REFERENCE_UNRELEASED" \
            or trigger_core["cross_language_boolean_transition_count"] != 3584 \
            or trigger_core["mismatches"] \
            or trigger_core["hardware_adapter_implemented"] \
            or trigger_core["motor_driver_selected"] \
            or trigger_core["manufacturing_release"]:
        raise RuntimeError("Portable point-shot core review is missing or overstated")
    checked_sources(trigger_core["source_sha256"])
    if optical_budget["status"] != "GEOMETRIC_NEAR_HOME_ONLY_ZERO_UNPROVEN" \
            or optical_budget["source"]["analysis_script_sha256"] \
            != sha(ROOT / "analysis/optical_home_transition_budget.py") \
            or optical_budget["source"]["cad_sha256"] \
            != sha(ROOT / "cad/feeder-optical-home.scad") \
            or optical_budget["source"]["parameters_sha256"] \
            != sha(ROOT / "cad/parameters.scad") \
            or optical_budget["source"]["geometry_review_sha256"] != sha(OPTICAL_REVIEW) \
            or optical_budget["source"]["partial_return_counterexample_report_sha256"] \
            != sha(PARTIAL_RETURN) \
            or optical_budget["source"]["electric_carriage_cad_sha256"] \
            != sha(ROOT / "cad/electric-feeder-assembly.scad") \
            or optical_budget["partial_return_double_shot_observability"]["modelled_blocked_boolean_distinguishes_u0_from_unsafe_u"] \
            or optical_budget["optical_blocked_alone_confirms_mechanical_zero"] \
            or optical_budget["one_shot_rearm_from_optical_blocked_alone_permitted"] \
            or optical_budget["manufacturing_release"]:
        raise RuntimeError("Optical near-home budget is missing, stale, or overstated")
    if inventory["snapshot"] != "electric-drive-selected-unreleased":
        raise RuntimeError("Wrong selected-part inventory")
    if inventory["assembly_complete"] or inventory["manufacturing_release"]:
        raise RuntimeError("Preview cannot promote an incomplete assembly to release")
    if drive["status"] != "NECESSARY_LOAD_BOUND_ONLY_MOTOR_NOT_APPROVED" \
            or drive["inputs"]["analysis_script_sha256"] \
            != sha(ROOT / "analysis/electric_drive_feasibility.py") \
            or drive["inputs"]["inventory_sha256"] != sha(INVENTORY) \
            or drive["inputs"]["spring_report_sha256"] != sha(SPRING_REPORT) \
            or drive["motor_force_sufficient"] is not None \
            or drive["manufacturing_release"]:
        raise RuntimeError("Electric drive force bound is missing or stale")
    if driver_screen["status"] != "LOW_VOLTAGE_DRIVER_SCREEN_NO_FINAL_SELECTION" \
            or driver_screen["driver_selected"] \
            or driver_screen["power_stage_schematic_complete"] \
            or driver_screen["manufacturing_release"] \
            or driver_screen["comparisons"]["TI DRV8850"]["seller_upper_stall_claim_to_driver_peak_headroom_a"] != .5 \
            or driver_screen["seller_gallery_sha256"] != drive["archived_seller_gallery_unverified"]["product_evidence_sha256"]:
        raise RuntimeError("Low-voltage motor driver screen is missing or overstated")
    checked_sources(driver_screen["source_sha256"])
    gallery = drive["archived_seller_gallery_unverified"]
    gallery_root = ROOT / "output/procurement/reciprocating-20260930"
    if gallery["product_evidence_sha256"] != sha(gallery_root / "product-evidence.json") \
            or gallery["image_manifest_sha256"] != sha(gallery_root / "image-sources.json") \
            or any(sha(ROOT / row["path"]) != row["sha256"]
                   for row in gallery["source_images"].values()):
        raise RuntimeError("Archived motor seller pictures changed since force review")
    if route["status"] != "NOMINAL_ROUTE_CORRIDOR_PASS_NOT_A_MOUNT" \
            or route["probe_count"] != 52 or route["motor_mount_designed"] \
            or route["real_motor_envelope_placed"]:
        raise RuntimeError("Motor-free drive-route review is missing or overstated")
    if envelope["status"] != "SCHEMATIC_SELLER_ENVELOPE_SCREEN_ONLY" \
            or envelope["probe_count"] != 121 \
            or envelope["drive_report_sha256"] != sha(DRIVE_REPORT) \
            or envelope["integrated_trigger_review_sha256"] != sha(TRIGGER_INTEGRATION) \
            or envelope["context_image"]["sha256"] != sha(ENVELOPE_IMAGE) \
            or envelope["motor_mount_designed"] \
            or envelope["real_motor_mounted"] \
            or envelope["manufacturing_release"] \
            or any(not candidate["sampled_collision_free"]
                   for candidate in envelope["candidates"].values()) \
            or not envelope["probes"][envelope["positive_control"]]["occupied"]:
        raise RuntimeError("Motor envelope screen is missing, stale, or overstated")
    if home_switch["status"] != "HOME_SWITCH_PACKAGING_SCREEN_ONLY" \
            or home_switch["probe_count"] != 33 \
            or home_switch["integrated_trigger_review_sha256"] != sha(TRIGGER_INTEGRATION) \
            or home_switch["images"]["home-context.png"]["sha256"] != sha(HOME_SWITCH_HOME_IMAGE) \
            or home_switch["images"]["one-mm-context.png"]["sha256"] != sha(HOME_SWITCH_U1_IMAGE) \
            or home_switch["mounting_bracket_designed"] \
            or home_switch["manufacturing_release"] \
            or home_switch["failures"]:
        raise RuntimeError("Independent home-switch screen is missing, stale, or overstated")
    if full_switch["status"] != "FULL_STROKE_SWITCH_PACKAGING_SCREEN_ONLY" \
            or full_switch["probe_count"] != 34 \
            or full_switch["home_switch_review_sha256"] != sha(HOME_SWITCH_REPORT) \
            or full_switch["integrated_trigger_review_sha256"] != sha(TRIGGER_INTEGRATION) \
            or full_switch["images"]["full-context.png"]["sha256"] != sha(FULL_SWITCH_FULL_IMAGE) \
            or full_switch["images"]["one-mm-before-context.png"]["sha256"] != sha(FULL_SWITCH_BEFORE_IMAGE) \
            or full_switch["mounting_bracket_designed"] \
            or full_switch["moving_tab_promoted_to_selected_carriage"] \
            or full_switch["manufacturing_release"] \
            or full_switch["failures"]:
        raise RuntimeError("Full-stroke-switch screen is missing, stale, or overstated")
    if front_switch_rejected["status"] != "REJECTED_MOTOR_BLOCKS_SWITCH_ADJUSTMENT" \
            or front_switch_rejected["probe_count"] != 104 \
            or front_switch_rejected["service_access_pass"] \
            or front_switch_rejected["promoted_to_selected_parts"] \
            or front_switch_rejected["manufacturing_release"] \
            or front_switch_rejected["failures"]:
        raise RuntimeError("Rejected front-mounted switch candidate changed")
    if side_switch["status"] != "SIDE_BOLTED_ENDPOINT_CAP_GEOMETRY_PASS_UNRELEASED" \
            or side_switch["probe_count"] != 227 \
            or not side_switch["service_access_pass"] \
            or side_switch["rejected_front_bolt_review_sha256"] != sha(FRONT_SWITCH_REJECTED_REPORT) \
            or side_switch["home_switch_review_sha256"] != sha(HOME_SWITCH_REPORT) \
            or side_switch["full_switch_review_sha256"] != sha(FULL_SWITCH_REPORT) \
            or side_switch["motor_envelope_review_sha256"] != sha(ENVELOPE_REPORT) \
            or side_switch["promoted_to_selected_parts"] \
            or side_switch["manufacturing_release"] \
            or side_switch["physical_acceptance"] \
            or side_switch["failures"]:
        raise RuntimeError("Side-mounted endpoint candidate is missing or overstated")
    for name in SIDE_SWITCH_IMAGES:
        if side_switch["images"][name]["sha256"] != sha(SIDE_SWITCH_ROOT / name):
            raise RuntimeError(f"Side-mounted switch image changed: {name}")
    for name in SIDE_SWITCH_MESHES:
        mesh = side_switch["part_meshes"][name]
        if not mesh["watertight"] or mesh["stl_sha256"] != sha(SIDE_SWITCH_ROOT / f"{name}.stl"):
            raise RuntimeError(f"Side-mounted switch mesh changed: {name}")
    if side_switch_slice["status"] != "SIDE_CAP_AND_CARRIAGE_SLICED_UNRELEASED" \
            or side_switch_slice["geometry_review_sha256"] != sha(SIDE_SWITCH_REPORT) \
            or not side_switch_slice["unsupported_rejected_for_floating_regions"] \
            or side_switch_slice["printer_sent"] \
            or side_switch_slice["manufacturing_release"] \
            or side_switch_slice["physical_acceptance"] \
            or side_switch_slice["failures"]:
        raise RuntimeError("Side-mounted switch slice is missing or overstated")
    if endpoint_signal["status"] != "ILLUSTRATIVE_ENDPOINT_PULSE_SCREEN_REAL_TIMING_UNKNOWN" \
            or endpoint_signal["five_ms_stable_debounce_safe_from_this_evidence"] \
            or endpoint_signal["home_switch_closed_alone_proves_hard_stop"] \
            or endpoint_signal["full_switch_closed_alone_proves_full_travel"] \
            or endpoint_signal["endpoint_event_capture_and_noise_rejection_finalized"] \
            or endpoint_signal["manufacturing_release"]:
        raise RuntimeError("Endpoint signal timing screen is missing or overstated")
    checked_sources(endpoint_signal["source_sha256"])
    for name in ("cap-tree-support", "carriage-tree-support"):
        row = side_switch_slice["orientations"][name]
        mesh = side_switch["part_meshes"][row["part"]]
        if row["status"] != "SLICED_UNRELEASED" or row["native_warnings"] \
                or not row["archive_integrity_pass"] \
                or row["source_stl_sha256"] != mesh["stl_sha256"] \
                or row["slice_3mf_sha256"] != sha(SIDE_SWITCH_ROOT / "slices" / name / "slice-review.3mf"):
            raise RuntimeError(f"Side-mounted switch slice changed: {name}")
    screened_layout = next((row for row in rocker_bridge["candidates"]
                            if row["input_radius_mm"] == 75
                            and row["rocker_plane_y_mm"] == 62), None)
    if rocker_bridge["status"] != "OUTPUT_BRIDGE_LAYOUT_SCREEN_ONLY" \
            or rocker_bridge["side_switch_review_sha256"] != sha(SIDE_SWITCH_REPORT) \
            or rocker_bridge["motor_envelope_review_sha256"] != sha(ENVELOPE_REPORT) \
            or len(rocker_bridge["probes"]) != 540 \
            or len(rocker_bridge["selected_fine_probes"]) != 360 \
            or len(rocker_bridge["selected_end_clearance_probes"]) != 24 \
            or rocker_bridge["screen_contract"]["max_input_output_position_identity_residual_mm"] > 1e-10 \
            or screened_layout is None or not screened_layout["sampled_clearance"] \
            or rocker_bridge["screen_contract"]["selected_r75_y62_cap_top_to_bridge_bottom_nominal_mm"] != 2.7 \
            or rocker_bridge["screen_contract"]["selected_r75_y62_dilated_neighbor_clearance_screen_mm"] != 2 \
            or rocker_bridge["screen_contract"]["selected_r75_y62_motor_bridge_clearance_screen_mm"] != 5 \
            or not rocker_bridge["screen_contract"]["prior_z23_dilated_fixed_clearance_fails"] \
            or rocker_bridge["manufacturing_release"] \
            or rocker_bridge["physical_acceptance"] \
            or rocker_bridge["failures"] \
            or any(row.get("occupied") or row.get("error")
                   for row in rocker_bridge["selected_fine_probes"].values()) \
            or any(row.get("occupied") or row.get("error")
                   for row in rocker_bridge["selected_end_clearance_probes"].values()) \
            or not all(row.get("occupied")
                       for row in rocker_bridge["prior_z23_clearance_probe"].values()):
        raise RuntimeError("Rocker-bridge layout screen is missing or overstated")
    for name in ROCKER_BRIDGE_IMAGES:
        if rocker_bridge["images"][name]["sha256"] != sha(ROCKER_BRIDGE_ROOT / name):
            raise RuntimeError(f"Rocker-bridge image changed: {name}")
    if rocker_pivot["status"] != "PIVOT_MOUNT_LAYOUT_SCREEN_ONLY" \
            or len(rocker_pivot["probes"]) != 40 \
            or rocker_pivot["rocker_report_sha256"] != sha(ROCKER_BRIDGE_REPORT) \
            or not rocker_pivot["bracket_mesh"]["watertight"] \
            or rocker_pivot["manufacturing_release"] \
            or rocker_pivot["physical_acceptance"] \
            or rocker_pivot["failures"]:
        raise RuntimeError("Rocker pivot mount candidate is missing or overstated")
    pivot_phase = rocker_pivot["rocker_phase_witness"]
    if not 13 < pivot_phase["t1.00"]["bounds"]["max"][2] \
            - pivot_phase["t0.00"]["bounds"]["max"][2] < 14:
        raise RuntimeError("Pivot mount screen did not sweep the rocker")
    for name in ROCKER_PIVOT_IMAGES:
        if rocker_pivot["images"][name]["sha256"] != sha(ROCKER_PIVOT_ROOT / name):
            raise RuntimeError(f"Rocker pivot image changed: {name}")
    if rocker_joint["status"] != "Y62_RETAINER_COLLISION_Y65_LAYOUT_SCREEN_ONLY" \
            or len(rocker_joint["probes"]) != 160 \
            or len(rocker_joint["selected_y65_fine_probes"]) != 48 \
            or rocker_joint["mount_report_sha256"] != sha(ROCKER_PIVOT_REPORT) \
            or rocker_joint["bridge_report_sha256"] != sha(ROCKER_BRIDGE_REPORT) \
            or rocker_joint["plane_comparison"]["y65_promoted_to_selected_assembly"] \
            or rocker_joint["manufacturing_release"] \
            or rocker_joint["physical_acceptance"] \
            or rocker_joint["failures"]:
        raise RuntimeError("Retained rocker joint comparison is missing or overstated")
    joint_phase = rocker_joint["rocker_phase_witness"]
    if not 9 < joint_phase["t1.00"]["bounds"]["max"][2] \
            - joint_phase["t0.00"]["bounds"]["max"][2] < 12:
        raise RuntimeError("Retained joint screen did not sweep the rocker")
    for name in ROCKER_JOINT_IMAGES:
        key = "y62" if "y62" in name else "y65"
        if rocker_joint["images"][key]["sha256"] != sha(ROCKER_JOINT_ROOT / name):
            raise RuntimeError(f"Rocker joint image changed: {name}")
    for name in ("rocker", "bracket"):
        candidate = rocker_joint["candidate_meshes"][name]
        if not candidate["watertight"] \
                or candidate["sha256"] != sha(ROCKER_JOINT_ROOT / f"{name}-y65.stl"):
            raise RuntimeError(f"Rocker joint candidate mesh changed: {name}")
    if rocker_pin["status"] != "HCDG6_16_FRONT_HEAD_LAYOUT_CLEAR_FORK_FIT_OPEN" \
            or rocker_pin["predecessor_joint_report_sha256"] != sha(ROCKER_JOINT_REPORT) \
            or len(rocker_pin["coarse_probes"]) != 30 \
            or len(rocker_pin["fine_probes"]) != 32 \
            or len(rocker_pin["serviceability_screen"]["probe_results"]) != 15 \
            or rocker_pin["fork_bore_issue"]["qualified_bearing_or_finished_fork_hole_designed"] \
            or rocker_pin["selected_assembly_promoted"] \
            or rocker_pin["manufacturing_release"] \
            or rocker_pin["physical_acceptance"] \
            or rocker_pin["failures"]:
        raise RuntimeError("Rocker pin-retention screen is missing or overstated")
    if rocker_pin["image"]["sha256"] != sha(ROCKER_PIN_IMAGE):
        raise RuntimeError("Rocker pin-retention image changed")
    if rocker_clamp["status"] != "SPLIT_CLAMP_FORK_STATIC_SCREEN_ONLY" \
            or rocker_clamp["predecessor_pin_report_sha256"] != sha(ROCKER_PIN_REPORT) \
            or len(rocker_clamp["static_clearance_probes"]) != 110 \
            or any(rocker_clamp["static_clearance_probes"][
                f"fasteners-bracket-t{t:.2f}"]["occupied"]
                for t in (0, .25, .5, .75, 1)) \
            or len(rocker_clamp["service_axis"]["probes"]) != 50 \
            or len(rocker_clamp["service_axis"]["occupied_axes"]) != 8 \
            or not rocker_clamp["service_axis"]["driver_axes_clear_at_all_poses_nominal"] \
            or rocker_clamp["bracket_mesh"]["connected_components"] != 1 \
            or not rocker_clamp["bracket_mesh"]["watertight"] \
            or not rocker_clamp["real_rocker_bore_and_bushing_included_in_screen"] \
            or rocker_clamp["rocker_bushing_petg_fit_verified"] \
            or not 9 < rocker_clamp["through_bored_rocker_top_z_delta_mm"] < 12 \
            or rocker_clamp["drive_feasibility_report_sha256"] != sha(DRIVE_REPORT) \
            or rocker_clamp["bracket_mesh"]["bounds"]["min"][2] != -18 \
            or rocker_clamp["beam_load_scenario_only"]["deepened_section_modulus_mm3"] != 60.5 \
            or rocker_clamp["beam_load_scenario_only"]["structural_release"] \
            or rocker_clamp["bracket_mesh"]["sha256"] != sha(ROCKER_CLAMP_ROOT / "bracket.stl") \
            or rocker_clamp["selected_assembly_promoted"] \
            or rocker_clamp["manufacturing_release"] \
            or rocker_clamp["physical_acceptance"] \
            or rocker_clamp["failures"]:
        raise RuntimeError("Split-clamp fork is missing or overstated")
    if rocker_clamp["predecessor_joint_report_sha256"] != sha(ROCKER_JOINT_REPORT) \
            or any(not rocker_clamp["positive_controls"][
                f"raw-rocker-shaft-positive-control-t{t:.2f}"]["occupied"]
                for t in (0, .25, .5, .75, 1)):
        raise RuntimeError("Old solid-rocker false-positive control is missing")
    for name in ROCKER_CLAMP_IMAGES:
        if rocker_clamp["images"][name]["sha256"] != sha(ROCKER_CLAMP_ROOT / name):
            raise RuntimeError(f"Split-clamp image changed: {name}")
    if output_crosshead["status"] != "OUTPUT_CROSSHEAD_GEOMETRY_SCREEN_ONLY" \
            or output_crosshead["predecessor_sha256"] != {
                "side": sha(SIDE_SWITCH_REPORT), "bridge": sha(ROCKER_BRIDGE_REPORT),
                "fork": sha(ROCKER_CLAMP_REPORT)} \
            or output_crosshead["pose_count"] != 21 \
            or output_crosshead["clear_probe_count"] != 168 \
            or output_crosshead["positive_control_count"] != 10 \
            or output_crosshead["parameters_mm"]["pin_has_dedicated_axial_retention"] \
            or output_crosshead["promoted_to_selected_parts"] \
            or output_crosshead["print_or_strength_release"] \
            or output_crosshead["physical_acceptance"] \
            or output_crosshead["failures"]:
        raise RuntimeError("Output crosshead is missing or overstated")
    if any(row.get("occupied") or row.get("error")
           for row in output_crosshead["clear_probes"].values()) \
            or any(not row.get("occupied") or row.get("error")
                   for row in output_crosshead["positive_controls"].values()):
        raise RuntimeError("Output crosshead collision or contact probes changed")
    for name in ("crosshead", "carriage"):
        row = output_crosshead["parts"][name]
        if not row["watertight"] or row["connected_components"] != 1 \
                or row["sha256"] != sha(OUTPUT_CROSSHEAD_ROOT / f"{name}.stl"):
            raise RuntimeError(f"Output crosshead mesh changed: {name}")
    for name in OUTPUT_CROSSHEAD_IMAGES:
        if output_crosshead["images"][name.removesuffix(".png")]["sha256"] \
                != sha(OUTPUT_CROSSHEAD_ROOT / name):
            raise RuntimeError(f"Output crosshead image changed: {name}")
    checked_sources(output_crosshead["source_sha256"])
    if output_crosshead_slice["status"] != "OUTPUT_CARRIAGE_SLICED_UNRELEASED" \
            or output_crosshead_slice["geometry_review_sha256"] != sha(OUTPUT_CROSSHEAD_REPORT) \
            or output_crosshead_slice["source_stl_sha256"] != sha(OUTPUT_CROSSHEAD_ROOT / "carriage.stl") \
            or not output_crosshead_slice["slot_axis_vertical_after_rotation"] \
            or output_crosshead_slice["support_extrusion_segments_crossing_slot_with_0p25mm_margin"] != 0 \
            or output_crosshead_slice["native_warnings"] \
            or output_crosshead_slice["printer_sent"] \
            or output_crosshead_slice["manufacturing_release"] \
            or output_crosshead_slice["physical_acceptance"] \
            or output_crosshead_slice["failures"] \
            or output_crosshead_slice["slice_3mf_sha256"] != sha(OUTPUT_CROSSHEAD_3MF) \
            or output_crosshead_slice["preview_sha256"] != sha(OUTPUT_CROSSHEAD_SLICE_IMAGE):
        raise RuntimeError("Output crosshead slice is missing or overstated")
    checked_sources(output_crosshead_slice["source_sha256"])
    if output_crosshead_assembly["status"] != "SERVICE_PATH_PARTIAL_AXIAL_INSERTION_BLOCKED" \
            or output_crosshead_assembly["predecessor_sha256"] != {
                str(path.relative_to(ROOT)): sha(path) for path in (
                    OUTPUT_CROSSHEAD_REPORT, SIDE_SWITCH_REPORT, ROCKER_CLAMP_REPORT)} \
            or not output_crosshead_assembly["nominal_cap_removal_vs_new_crosshead_clear"] \
            or not output_crosshead_assembly["nominal_switch_tool_vs_new_crosshead_clear"] \
            or not output_crosshead_assembly["nominal_rocker_pin_axial_path_into_slot_clear_without_fork"] \
            or not output_crosshead_assembly["rocker_with_fixed_fork_axial_blocked_y_offset_mm"] \
            or output_crosshead_assembly["complete_rocker_assembly_path_proven"] \
            or output_crosshead_assembly["manufacturing_release"] \
            or output_crosshead_assembly["physical_acceptance"] \
            or output_crosshead_assembly["failures"]:
        raise RuntimeError("Output crosshead service path is missing or overstated")
    checked_sources(output_crosshead_assembly["source_sha256"])
    if output_pin_load["status"] != "OUTPUT_PIN_AXIAL_ENGAGEMENT_CONDITIONAL_LOAD_UNRELEASED" \
            or output_pin_load["source_sha256"][str(OUTPUT_CROSSHEAD_REPORT.relative_to(ROOT))] != sha(OUTPUT_CROSSHEAD_REPORT) \
            or output_pin_load["source_sha256"][str(SERVICE_FORK_REPORT.relative_to(ROOT))] != sha(SERVICE_FORK_REPORT) \
            or output_pin_load["axial_geometry_mm"]["nominal_pin_slot_engagement"] != 8.5 \
            or output_pin_load["axial_geometry_mm"]["remaining_engagement_at_that_translation"] != 7 \
            or not output_pin_load["conditional_retention"]["no_separate_output_pin_axial_clip_needed_if_fork_and_pivot_keep_rocker_between_its_inner_faces"] \
            or output_pin_load["conditional_retention"]["actual_fork_spacing_pin_retention_bushing_fit_and_flex_verified"] \
            or output_pin_load["conditional_retention"]["moving_slot_y_position_and_flex_verified"] \
            or output_pin_load["conditional_retention"]["printed_pin_attachment_and_wear_verified"] \
            or output_pin_load["manufacturing_release"] \
            or output_pin_load["physical_acceptance"]:
        raise RuntimeError("Output pin retention/load screen is missing or overstated")
    checked_sources(output_pin_load["source_sha256"])
    if service_fork["status"] != "SERVICE_FORK_NOMINAL_ASSEMBLY_PATH_ONLY" \
            or service_fork["predecessor_sha256"] != {
                str(path.relative_to(ROOT)): sha(path) for path in (
                    OUTPUT_CROSSHEAD_ASSEMBLY, OUTPUT_CROSSHEAD_REPORT,
                    ROCKER_CLAMP_REPORT)} \
            or service_fork["static_probe_count"] != 105 \
            or service_fork["assembly_probe_count"] != 264 \
            or service_fork["positive_control_count"] != 2 \
            or any(row.get("occupied") or row.get("error")
                   for row in service_fork["clear_probes"].values()) \
            or any(not row.get("occupied") or row.get("error")
                   for row in service_fork["positive_controls"].values()) \
            or service_fork["promoted_to_selected_assembly"] \
            or service_fork["rear_joint_strength_and_creep_verified"] \
            or service_fork["manufacturing_release"] \
            or service_fork["physical_acceptance"] \
            or service_fork["failures"]:
        raise RuntimeError("Service fork assembly path is missing or overstated")
    checked_sources(service_fork["source_sha256"])
    for name in ("base", "rear"):
        row = service_fork["parts"][name]
        if not row["watertight"] or row["connected_components"] != 1 \
                or row["sha256"] != sha(SERVICE_FORK_ROOT / f"{name}.stl"):
            raise RuntimeError(f"Service fork mesh changed: {name}")
    for name in SERVICE_FORK_IMAGES:
        if service_fork["images"][name.removesuffix(".png")]["sha256"] \
                != sha(SERVICE_FORK_ROOT / name):
            raise RuntimeError(f"Service fork image changed: {name}")
    if service_fork_slice["status"] != "SERVICE_FORK_SLICED_UNRELEASED" \
            or service_fork_slice["geometry_review_sha256"] != sha(SERVICE_FORK_REPORT) \
            or service_fork_slice["printer_sent"] \
            or service_fork_slice["manufacturing_release"] \
            or service_fork_slice["physical_acceptance"] \
            or service_fork_slice["failures"]:
        raise RuntimeError("Service fork slice is missing or overstated")
    checked_sources(service_fork_slice["source_sha256"])
    for label, part in (("base-x-plus-90-tree", "base"),
                        ("rear-x-minus-90-tree", "rear")):
        row = service_fork_slice["orientations"][label]
        folder = SERVICE_FORK_ROOT / "slices" / label
        if row["status"] != "SLICED_UNRELEASED" \
                or row["source_stl_sha256"] != service_fork["parts"][part]["sha256"] \
                or row["native_warnings"] \
                or not row["archive_integrity_pass"] \
                or not all(row["critical_pockets_open_upward_after_3mf_rotation"].values()) \
                or any(row["support_extrusion_segments_crossing_critical_feature_with_0p25mm_margin"].values()) \
                or row["slice_3mf_sha256"] != sha(folder / "slice-review.3mf") \
                or row["preview_sha256"] != sha(folder / "plate-preview.png"):
            raise RuntimeError(f"Service fork slice changed: {label}")
    if service_fork_load["status"] != "SERVICE_FORK_LOAD_PATH_UNRELEASED" \
            or service_fork_load["source_sha256"][str(SERVICE_FORK_REPORT.relative_to(ROOT))] != sha(SERVICE_FORK_REPORT) \
            or service_fork_load["source_sha256"][str(SERVICE_FORK_SLICE.relative_to(ROOT))] != sha(SERVICE_FORK_SLICE) \
            or service_fork_load["joint_nominal_play"]["first_shear_contact_determinable_from_nominal_cad"] \
            or service_fork_load["rear_joint_strength_verified"] \
            or service_fork_load["structural_release"] \
            or service_fork_load["manufacturing_release"] \
            or service_fork_load["physical_acceptance"]:
        raise RuntimeError("Service fork load path is missing or overstated")
    checked_sources(service_fork_load["source_sha256"])
    x40 = service_fork_orientation["orientations"]["x40"]
    x90 = service_fork_orientation["orientations"]["x90"]
    if service_fork_orientation["status"] != "ORIENTATION_COMPARISON_ONLY" \
            or service_fork_orientation["source_sha256"][str(SERVICE_FORK_REPORT.relative_to(ROOT))] != sha(SERVICE_FORK_REPORT) \
            or service_fork_orientation["source_sha256"][str(SERVICE_FORK_SLICE.relative_to(ROOT))] != sha(SERVICE_FORK_SLICE) \
            or len(service_fork_orientation["orientations"]) != 12 \
            or x40["status"] != "OFFLINE_SLICE_ONLY" \
            or x40["source_stl_sha256"] != service_fork["parts"]["base"]["sha256"] \
            or x40["native_warnings"] \
            or not x40["archive_integrity_pass"] \
            or any(x40["sampled_support_extrusion_segments_in_void_cores"].values()) \
            or x40["preview_sha256"] != sha(SERVICE_FORK_X40_PREVIEW) \
            or x90["slice_3mf_sha256"] != service_fork_slice["orientations"]["base-x-plus-90-tree"]["slice_3mf_sha256"] \
            or service_fork_orientation["best_orientation_selected"] \
            or service_fork_orientation["manufacturing_release"] \
            or service_fork_orientation["physical_acceptance"]:
        raise RuntimeError("Service fork orientation comparison is missing or overstated")
    checked_sources(service_fork_orientation["source_sha256"])
    if service_fork_reinforcement["status"] != "REINFORCED_BEAM_GEOMETRY_SCREEN_ONLY" \
            or service_fork_reinforcement["original_review_sha256"] != sha(SERVICE_FORK_REPORT) \
            or service_fork_reinforcement["original_load_review_sha256"] != sha(SERVICE_FORK_LOAD) \
            or service_fork_reinforcement["reinforced_base"]["sha256"] != sha(
                SERVICE_FORK_REINFORCEMENT_ROOT / "base-reinforced-screen.stl") \
            or service_fork_reinforcement["context_image"]["sha256"] != sha(
                SERVICE_FORK_REINFORCEMENT_ROOT / "beam-extension-context.png") \
            or service_fork_reinforcement["failures"] \
            or service_fork_reinforcement["moving_phase_control"]["min_max_z_shift_mm"] != [20.0, 20.0] \
            or service_fork_reinforcement["structural_release"] \
            or service_fork_reinforcement["manufacturing_release"]:
        raise RuntimeError("Reinforced service fork screen is missing or overstated")
    checked_sources(service_fork_reinforcement["source_sha256"])
    if service_fork_root_section["status"] != "ROOT_SECTION_UNCHANGED_REINFORCEMENT_UNRELEASED" \
            or not all(service_fork_root_section["checks"].values()) \
            or service_fork_root_section["structural_release"] \
            or service_fork_root_section["manufacturing_release"]:
        raise RuntimeError("Service fork root-section screen is missing or overstated")
    checked_sources(service_fork_root_section["source_sha256"])
    if service_fork_root_web["status"] != "ROOT_WEB_NOMINAL_GEOMETRY_ONLY_UNRELEASED" \
            or service_fork_root_web["predecessor_reinforcement_sha256"] != sha(SERVICE_FORK_REINFORCEMENT_REPORT) \
            or service_fork_root_web["predecessor_root_section_sha256"] != sha(SERVICE_FORK_ROOT_SECTION) \
            or len(service_fork_root_web["probes"]) != 131 \
            or service_fork_root_web["failures"] \
            or any(row["occupied"] != (name in ("positive", "margin-positive"))
                   for name, row in service_fork_root_web["probes"].items()) \
            or service_fork_root_web["added_only"]["bounds_mm"]["min"][0] != 8.0 \
            or service_fork_root_web["base"]["sha256"] != sha(
                SERVICE_FORK_ROOT_WEB_ROOT / "base-root-web-screen.stl") \
            or service_fork_root_web["added_only"]["sha256"] != sha(
                SERVICE_FORK_ROOT_WEB_ROOT / "added-root-web-screen.stl") \
            or service_fork_root_web["context_image"]["sha256"] != sha(
                SERVICE_FORK_ROOT_WEB_ROOT / "root-web-context.png") \
            or service_fork_root_web["structural_release"] \
            or service_fork_root_web["manufacturing_release"] \
            or service_fork_root_web["selected_for_printing"]:
        raise RuntimeError("Service fork root web screen is missing or overstated")
    checked_sources(service_fork_root_web["source_sha256"])
    if service_fork_root_web_section["status"] != "ROOT_WEB_LOBE_AREA_GAIN_ONLY_UNRELEASED" \
            or not all(service_fork_root_web_section["checks"].values()) \
            or service_fork_root_web_section["root_lower_lobe_area_ratio"] <= 3 \
            or service_fork_root_web_section["three_dimensional_stress_or_fatigue_verified"] \
            or service_fork_root_web_section["structural_release"] \
            or service_fork_root_web_section["manufacturing_release"]:
        raise RuntimeError("Service fork root web section is missing or overstated")
    checked_sources(service_fork_root_web_section["source_sha256"])
    root_web_angles = service_fork_root_web_orientation["orientations"]
    if service_fork_root_web_orientation["status"] != "ROOT_WEB_ORIENTATION_SCREEN_ONLY_UNRELEASED" \
            or len(root_web_angles) != 20 \
            or any(row["status"] != "OFFLINE_SLICE_ONLY"
                   or row["source_stl_sha256"] != service_fork_root_web["base"]["sha256"]
                   or row["native_warnings"] or not row["archive_integrity_pass"]
                   for row in root_web_angles.values()) \
            or any(any((*root_web_angles[name]["sampled_support_extrusion_segments_in_void_cores"].values(),
                        *root_web_angles[name]["shell_anchor_support_segments_in_void_cores"].values(),
                        *root_web_angles[name]["support_extrusion_segments_in_critical_feature_boxes"].values()))
                   for name in ("x40", "x55", "x90")) \
            or root_web_angles["x0"]["sampled_support_extrusion_segments_in_void_cores"]["nut_lower"] <= 0 \
            or root_web_angles["x55"]["slice_3mf_sha256"] != sha(
                SERVICE_FORK_ROOT_WEB_X55 / "slice-review.3mf") \
            or root_web_angles["x55"]["preview_sha256"] != sha(
                SERVICE_FORK_ROOT_WEB_X55 / "plate-preview.png") \
            or service_fork_root_web_orientation["no_support_x55"]["status"] != "NO_SUPPORT_FLOATING_REGIONS_WARNING_UNRELEASED" \
            or not any("floating regions" in warning for warning in
                       service_fork_root_web_orientation["no_support_x55"]["native_warnings"]) \
            or service_fork_root_web_orientation["no_support_x55"]["native_result_sha256"] != sha(
                SERVICE_FORK_ROOT_WEB_ROOT / "slice-screen/base-x-plus-55-no-support/result.json") \
            or service_fork_root_web_orientation["no_support_x55"]["manufacturing_release"] \
            or service_fork_root_web_orientation["best_orientation_selected"] \
            or service_fork_root_web_orientation["manufacturing_release"] \
            or service_fork_root_web_orientation["physical_acceptance"]:
        raise RuntimeError("Root-web X1C orientation screen is missing or overstated")
    checked_sources(service_fork_root_web_orientation["source_sha256"])
    if rocker_plane["status"] != "OUTER_ROCKER_PLANE_CLEARANCE_ONLY" \
            or rocker_plane["probe_count"] != 30 \
            or rocker_plane["integrated_trigger_review_sha256"] != sha(TRIGGER_INTEGRATION) \
            or rocker_plane["drive_report_sha256"] != sha(DRIVE_REPORT) \
            or rocker_plane["motor_envelope_report_sha256"] != sha(ENVELOPE_REPORT) \
            or rocker_plane["outer_plane_colliding_probes"] \
            or len(rocker_plane["inner_plane_colliding_probes"]) < 5 \
            or rocker_plane["context_image"]["sha256"] != sha(ROCKER_PLANE_IMAGE) \
            or rocker_plane["output_crosshead_and_bearing_mount_designed"] \
            or rocker_plane["manufacturing_release"] \
            or rocker_plane["failures"]:
        raise RuntimeError("Rocker-plane screen is missing, stale, or overstated")
    checked_sources(old["source_sha256"])
    checked_sources(current["source_sha256"])
    checked_sources(trigger["source_sha256"])
    checked_sources(integration["source_sha256"])
    checked_sources(route["source_sha256"])
    checked_sources(envelope["source_sha256"])
    checked_sources(home_switch["source_sha256"])
    checked_sources(full_switch["source_sha256"])
    checked_sources(front_switch_rejected["source_sha256"])
    checked_sources(side_switch["source_sha256"])
    checked_sources(side_switch_slice["source_sha256"])
    checked_sources(rocker_bridge["source_sha256"])
    checked_sources(rocker_pivot["source_sha256"])
    checked_sources(rocker_joint["source_sha256"])
    checked_sources(rocker_pin["source_sha256"])
    checked_sources(rocker_clamp["source_sha256"])
    checked_sources(rocker_plane["source_sha256"])
    checked_sources(inventory["source_sha256"])

    selected = inventory["printed_parts"]
    if len(selected) != 49 or any("cable" in p["id"] for p in selected) \
            or not inventory["electronic_trigger_selected"]:
        raise RuntimeError("Current selection must include 49 cable-free trigger parts")
    old_parts = {part["id"]: part for part in old["parts"]}
    replacements = {
        "feeder/beam-grip": (ROOT / "output/electric-trigger-integration/beam.stl",
                               integration["printed_parts"]["beam"]),
        "feeder/trigger-lever": (ROOT / "output/electric-trigger-integration/lever.stl",
                                integration["printed_parts"]["lever"]),
        "feeder/frame": (ROOT / "output/electric-feeder/electric-frame.stl",
                          current["beam_and_electric_frame"]["electric-frame"]),
        "feeder/moving-spacer": (ROOT / "output/electric-feeder/optical-moving-spacer.stl",
                                  current["replacement_parts"]["optical-moving-spacer"]),
        "feeder/y-cap-left": (ROOT / "output/electric-feeder/optical-left-cap.stl",
                               current["replacement_parts"]["optical-left-cap"]),
    }
    for path, record in replacements.values():
        if not record["watertight"] or sha(path) != record["sha256"]:
            raise RuntimeError(f"Changed or non-manifold electric replacement: {path}")

    stage = Path(tempfile.mkdtemp(prefix="electric-preview-", dir=ROOT / "output"))
    parts = []
    assets = []

    def stage_copy(source: Path, name: str) -> Path:
        destination = stage / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if sha(source) != sha(destination):
            raise RuntimeError(f"Staging altered {source}")
        assets.append({"file": name, "sha256": sha(destination)})
        return destination

    for row in selected:
        part_id = row["id"]
        historical = old_parts.get(part_id)
        if historical is not None and (not historical["passed"] or historical["role"] != "printed"):
            raise RuntimeError(f"Historical common part did not pass: {part_id}")
        if part_id in replacements:
            source, _ = replacements[part_id]
        else:
            if historical is None:
                raise RuntimeError(f"New part lacks a reviewed replacement: {part_id}")
            source = ROOT / historical["file"]
            if sha(source) != historical["sha256"]:
                raise RuntimeError(f"Historical common part changed: {part_id}")
        destination = f"electric-models/{part_id}.stl"
        copied = stage_copy(source, destination)
        name = {"feeder/beam-grip": "一体式电子扳机支座背梁",
                "feeder/trigger-lever": "电子信号扳机杠杆",
                "feeder/frame": "无手扣指环凸轮架",
                "feeder/moving-spacer": "带遮光片的弹簧运动端间隔套",
                "feeder/y-cap-left": "带光电座的左 Y 导向盖"}.get(
                    part_id, row.get("name", historical["name"] if historical else part_id))
        part = {key: copy.deepcopy(historical[key]) for key in
                ("id", "role", "group", "family", "motion", "display")
                if historical and key in historical}
        if historical is None:
            part.update(id=part_id, role="printed", group="feeder",
                        family="electronic-trigger", motion="finger-pull")
        part.update(name=name, file=destination, sha256=sha(copied),
                    bytes=copied.stat().st_size, mtime=sha(copied)[:12])
        if part_id == "spin/pad":
            part["color"] = "#73d7a5"
        parts.append(part)

    groups = [{"id": group, "name": title,
               "count": sum(p["group"] == group for p in parts)}
              for group, title in (("feeder", "当前无拉索送料结构"),
                                   ("spin", "可调旋转头 · 工作档"),
                                   ("hold", "保持叉 · 旁置附件"))]
    assert [g["count"] for g in groups] == [39, 9, 1]
    manifest = {
        "title": "往复电机版 · 已定义结构 49 件（电机座待定）",
        "snapshot": "electric-drive-selected-unreleased",
        "units": "mm", "up": "z", "parts": parts, "groups": groups,
        "partCount": len(parts), "groupCount": len(groups),
        "motor_mount_designed": False, "positive_two_way_coupling_designed": False,
        "electronic_trigger_candidate_reviewed": True,
        "electronic_trigger_selected": True,
        "electronic_trigger_physically_installed": False,
        "manufacturing_release": False, "physical_acceptance": False,
    }

    stage_copy(ROOT / "web/electric-index.html", "index.html")
    stage_copy(ROOT / "web/electronic-trigger-candidate.html",
               "electronic-trigger-candidate.html")
    stage_copy(ROOT / "web/models.html", "models.html")
    stage_copy(ROOT / "web/electric-models-app.mjs", "electric-models-app.mjs")
    stage_copy(ROOT / "web/feeder-motion.html", "feeder-motion.html")
    stage_copy(ROOT / "web/feeder-motion.mjs", "feeder-motion.mjs")
    stage_copy(ROOT / "output/electric-trigger-integration/current-assembly.png",
               "electric-models/current-assembly.png")
    stage_copy(INVENTORY, "electric-assembly-inventory.json")
    stage_copy(CURRENT_REPORT, "electric-review.json")
    core_doc = stage_copy(TRIGGER_CORE_DOC, "point-shot-core.md")
    core_doc.write_text(core_doc.read_text().replace(
        "../docs/by141-driver-selection.md", "by141-driver-selection.md").replace(
        "../docs/endpoint-signal-timing.md", "endpoint-signal-timing.md"))
    assets[-1]["sha256"] = sha(core_doc)
    status_doc = stage_copy(ROOT / "docs/current-status.md", "electric-status.md")
    status_doc.write_text(status_doc.read_text().replace(
        "../output/electronic-trigger-candidate/release-margin.json",
        "trigger-candidate/release-margin.json").replace(
        "../output/electronic-trigger-candidate/point-shot-fsm.json",
        "trigger-candidate/point-shot-fsm.json").replace(
        "../output/electronic-trigger-candidate/point-shot-core-review.json",
        "trigger-candidate/point-shot-core-review.json").replace(
        "../firmware/README.md",
        "point-shot-core.md").replace(
        "../output/electric-home-switch-screen/review.json",
        "home-switch/review.json").replace(
        "../output/electric-home-switch-screen/home-context.png",
        "home-switch/home-context.png").replace(
        "../output/electric-full-stroke-switch-screen/review.json",
        "full-switch/review.json").replace(
        "../output/electric-full-stroke-switch-screen/full-context.png",
        "full-switch/full-context.png").replace(
        "../output/by141-envelope-screen/context.png",
        "by141-envelope/context.png").replace(
        "../output/electric-rocker-plane-screen/review.json",
        "rocker-plane/review.json").replace(
        "../output/electric-rocker-plane-screen/outer-plane-context.png",
        "rocker-plane/outer-plane-context.png").replace(
        "../output/by141-envelope-screen/review.json",
        "by141-envelope/review.json").replace(
        "../output/optical-home-candidate/transition-budget.json",
        "optical-home/transition-budget.json").replace(
        "../output/electric-trigger-integration/review.json",
        "trigger-candidate/integration-review.json").replace(
        "../output/electric-rocker-pivot-joint-screen/review.json",
        "rocker-joint/review.json").replace(
        "../output/electric-rocker-pin-retention-screen/review.json",
        "rocker-pin/review.json").replace(
        "../output/electric-rocker-clamped-fork-screen/review.json",
        "rocker-clamp/review.json").replace(
        "../output/electric-rocker-service-fork-screen/load-screen.json",
        "service-fork/load-screen.json").replace(
        "../output/electric-rocker-service-fork-screen/orientation-screen.json",
        "service-fork/orientation-screen.json").replace(
        "../output/electric-output-crosshead-screen/pin-retention-load-screen.json",
        "output-crosshead/pin-retention-load-screen.json").replace(
        "../output/electric-output-crosshead-screen/assembly-review.json",
        "output-crosshead/assembly-review.json"))
    assets[-1]["sha256"] = sha(status_doc)
    trigger_doc = stage_copy(ROOT / "docs/electronic-trigger.md", "electronic-trigger.md")
    trigger_doc.write_text(trigger_doc.read_text().replace(
        "../output/electronic-trigger-candidate/", "trigger-candidate/").replace(
        "../firmware/README.md", "point-shot-core.md").replace(
        "../output/optical-home-candidate/transition-budget.json",
        "optical-home/transition-budget.json").replace(
        "../output/electric-trigger-integration/review.json",
        "trigger-candidate/integration-review.json").replace(
        "../output/electric-trigger-integration/current-assembly.png",
        "electric-models/current-assembly.png").replace(
        "../output/electric-home-switch-screen/review.json",
        "home-switch/review.json").replace(
        "../output/electric-home-switch-screen/home-context.png",
        "home-switch/home-context.png").replace(
        "../output/electric-home-switch-screen/one-mm-context.png",
        "home-switch/one-mm-context.png").replace(
        "../output/electric-full-stroke-switch-screen/review.json",
        "full-switch/review.json").replace(
        "../output/electric-full-stroke-switch-screen/full-context.png",
        "full-switch/full-context.png").replace(
        "../cad/electric-feeder-trigger-assembly.scad",
        "models.html?trigger=1"))
    assets[-1]["sha256"] = sha(trigger_doc)
    wire_relief_doc = stage_copy(ROOT / "docs/electronic-trigger-wire-relief-screen.md",
                                 "electronic-trigger-wire-relief-screen.md")
    wire_relief_doc.write_text(wire_relief_doc.read_text().replace(
        "../cad/electronic-trigger-wire-relief-screen.scad",
        "trigger-wire-relief/electronic-trigger-wire-relief-screen.scad").replace(
        "../output/electronic-trigger-candidate/beam.stl",
        "trigger-candidate/beam.stl").replace(
        "../output/electronic-trigger-wire-relief/", "trigger-wire-relief/"))
    assets[-1]["sha256"] = sha(wire_relief_doc)
    trigger_fastener_doc = stage_copy(ROOT / "docs/electronic-trigger-fastener-access.md",
                                      "electronic-trigger-fastener-access.md")
    trigger_fastener_doc.write_text(trigger_fastener_doc.read_text().replace(
        "../cad/electronic-trigger-fastener-access-screen.scad",
        "trigger-fastener/electronic-trigger-fastener-access-screen.scad").replace(
        "../output/electronic-trigger-fastener-access/", "trigger-fastener/"))
    assets[-1]["sha256"] = sha(trigger_fastener_doc)
    drive_doc = stage_copy(ROOT / "docs/electric-drive-feasibility.md",
                           "electric-drive-feasibility.md")
    local_report_link = "../output/electric-drive-feasibility/report.json"
    local_route_link = "../output/electric-drive-route/review.json"
    if local_report_link not in drive_doc.read_text() \
            or local_route_link not in drive_doc.read_text():
        raise RuntimeError("Electric drive report link changed")
    drive_doc.write_text(drive_doc.read_text().replace(
        local_report_link, "electric-drive-feasibility.json").replace(
        local_route_link, "electric-drive-route.json").replace(
        "../output/by141-envelope-screen/review.json",
        "by141-envelope/review.json").replace(
        "../output/by141-envelope-screen/context.png",
        "by141-envelope/context.png").replace(
        "../output/electric-rocker-plane-screen/review.json",
        "rocker-plane/review.json").replace(
        "../output/electric-rocker-plane-screen/outer-plane-context.png",
        "rocker-plane/outer-plane-context.png").replace(
        "../output/electric-trigger-integration/review.json",
        "trigger-candidate/integration-review.json"))
    assets[-1]["sha256"] = sha(drive_doc)
    preflight_doc = stage_copy(ROOT / "docs/by141-zero-print-preflight.md",
                               "by141-zero-print-preflight.md")
    preflight_doc.write_text(preflight_doc.read_text().replace(
        "../output/procurement/reciprocating-20260930/detail-07.png",
        "by141-seller/detail-07.png").replace(
        "../output/procurement/reciprocating-20261001/live-sku-interface-audit.json",
        "by141-live-sku-interface-audit.json"))
    assets[-1]["sha256"] = sha(preflight_doc)
    stage_copy(gallery_root / "detail-07.png", "by141-seller/detail-07.png")
    live_sku_audit = json.loads(BY141_LIVE_SKU_AUDIT.read_text())
    if live_sku_audit["status"] != "LIVE_SELECTED_SKU_READ_INTERFACE_INCOMPLETE" \
            or live_sku_audit["item_id"] != "988456349136" \
            or live_sku_audit["sku_id"] != "5952763100025":
        raise RuntimeError("Live selected motor SKU interface audit is missing or changed")
    stage_copy(BY141_LIVE_SKU_AUDIT, "by141-live-sku-interface-audit.json")
    endpoint_budget_doc = stage_copy(
        ROOT / "docs/endpoint-compliance-budget.md",
        "endpoint-compliance-budget.md")
    endpoint_budget_doc.write_text(endpoint_budget_doc.read_text().replace(
        "../analysis/endpoint_phase_budget.py", "endpoint-phase-budget.py"))
    assets[-1]["sha256"] = sha(endpoint_budget_doc)
    stage_copy(ROOT / "analysis/endpoint_phase_budget.py",
               "endpoint-phase-budget.py")
    driver_screen_doc = stage_copy(ROOT / "docs/by141-driver-selection.md",
                                   "by141-driver-selection.md")
    driver_screen_doc.write_text(driver_screen_doc.read_text().replace(
        "../output/electric-drive-feasibility/driver-screen.json",
        "by141-driver-screen.json").replace(
        "../firmware/README.md", "point-shot-core.md"))
    assets[-1]["sha256"] = sha(driver_screen_doc)
    stage_copy(DRIVER_SCREEN, "by141-driver-screen.json")
    stage_copy(DRIVE_REPORT, "electric-drive-feasibility.json")
    stage_copy(ROUTE_REPORT, "electric-drive-route.json")
    stage_copy(ENVELOPE_REPORT, "by141-envelope/review.json")
    stage_copy(ENVELOPE_IMAGE, "by141-envelope/context.png")
    stage_copy(HOME_SWITCH_REPORT, "home-switch/review.json")
    stage_copy(HOME_SWITCH_HOME_IMAGE, "home-switch/home-context.png")
    stage_copy(HOME_SWITCH_U1_IMAGE, "home-switch/one-mm-context.png")
    stage_copy(FULL_SWITCH_REPORT, "full-switch/review.json")
    stage_copy(FULL_SWITCH_FULL_IMAGE, "full-switch/full-context.png")
    stage_copy(FULL_SWITCH_BEFORE_IMAGE, "full-switch/one-mm-before-context.png")
    stage_copy(FRONT_SWITCH_REJECTED_REPORT, "endpoint-switch/front-rejected-review.json")
    stage_copy(SIDE_SWITCH_REPORT, "endpoint-switch/review.json")
    stage_copy(SIDE_SWITCH_SLICE, "endpoint-switch/slice-review.json")
    stage_copy(ENDPOINT_SIGNAL, "endpoint-switch/signal-window.json")
    stage_copy(ROOT / "cad/electric-end-switch-side-cap.scad",
               "endpoint-switch/electric-end-switch-side-cap.scad")
    for name in SIDE_SWITCH_IMAGES:
        stage_copy(SIDE_SWITCH_ROOT / name, f"endpoint-switch/{name}")
    for name in SIDE_SWITCH_MESHES:
        stage_copy(SIDE_SWITCH_ROOT / f"{name}.stl", f"endpoint-switch/{name}.stl")
    for name in SIDE_SWITCH_3MF:
        stage_copy(SIDE_SWITCH_ROOT / name, f"endpoint-switch/{name}")
    endpoint_doc = stage_copy(ROOT / "docs/endpoint-switch-integration.md",
                              "endpoint-switch-integration.md")
    endpoint_doc.write_text(endpoint_doc.read_text().replace(
        "../output/electric-end-switch-cap-candidate/review.json",
        "endpoint-switch/front-rejected-review.json").replace(
        "../cad/electric-end-switch-side-cap.scad",
        "endpoint-switch/electric-end-switch-side-cap.scad").replace(
        "../output/electric-end-switch-side-cap/",
        "endpoint-switch/").replace(
        "../output/electric-home-switch-screen/review.json",
        "home-switch/review.json"))
    assets[-1]["sha256"] = sha(endpoint_doc)
    signal_doc = stage_copy(ROOT / "docs/endpoint-signal-timing.md",
                            "endpoint-signal-timing.md")
    signal_doc.write_text(signal_doc.read_text().replace(
        "../output/electric-home-switch-screen/review.json",
        "home-switch/review.json").replace(
        "../output/electric-full-stroke-switch-screen/review.json",
        "full-switch/review.json").replace(
        "../output/electric-end-switch-side-cap/signal-window.json",
        "endpoint-switch/signal-window.json").replace(
        "../firmware/README.md", "point-shot-core.md"))
    assets[-1]["sha256"] = sha(signal_doc)
    stage_copy(ROCKER_BRIDGE_REPORT, "rocker-bridge/review.json")
    stage_copy(ROOT / "cad/electric-rocker-bridge-screen.scad",
               "rocker-bridge/electric-rocker-bridge-screen.scad")
    for name in ROCKER_BRIDGE_IMAGES:
        stage_copy(ROCKER_BRIDGE_ROOT / name, f"rocker-bridge/{name}")
    bridge_doc = stage_copy(ROOT / "docs/electric-rocker-bridge-screen.md",
                            "electric-rocker-bridge-screen.md")
    bridge_doc.write_text(bridge_doc.read_text().replace(
        "../cad/electric-rocker-bridge-screen.scad",
        "rocker-bridge/electric-rocker-bridge-screen.scad").replace(
        "../output/electric-rocker-bridge-screen/", "rocker-bridge/"))
    assets[-1]["sha256"] = sha(bridge_doc)
    stage_copy(ROCKER_PIVOT_REPORT, "rocker-pivot/review.json")
    stage_copy(ROOT / "cad/electric-rocker-pivot-mount-screen.scad",
               "rocker-pivot/electric-rocker-pivot-mount-screen.scad")
    for name in ROCKER_PIVOT_IMAGES:
        stage_copy(ROCKER_PIVOT_ROOT / name, f"rocker-pivot/{name}")
    pivot_doc = stage_copy(ROOT / "docs/electric-rocker-pivot-mount-screen.md",
                           "electric-rocker-pivot-mount-screen.md")
    pivot_doc.write_text(pivot_doc.read_text().replace(
        "../cad/electric-rocker-pivot-mount-screen.scad",
        "rocker-pivot/electric-rocker-pivot-mount-screen.scad").replace(
        "../output/electric-rocker-pivot-mount-screen/", "rocker-pivot/"))
    assets[-1]["sha256"] = sha(pivot_doc)
    stage_copy(ROCKER_JOINT_REPORT, "rocker-joint/review.json")
    stage_copy(ROOT / "cad/electric-rocker-pivot-joint-screen.scad",
               "rocker-joint/electric-rocker-pivot-joint-screen.scad")
    for name in ROCKER_JOINT_IMAGES:
        stage_copy(ROCKER_JOINT_ROOT / name, f"rocker-joint/{name}")
    joint_doc = stage_copy(ROOT / "docs/electric-rocker-pivot-joint-screen.md",
                           "electric-rocker-pivot-joint-screen.md")
    joint_doc.write_text(joint_doc.read_text().replace(
        "../output/electric-rocker-pivot-joint-screen/", "rocker-joint/"))
    assets[-1]["sha256"] = sha(joint_doc)
    stage_copy(ROCKER_PIN_REPORT, "rocker-pin/review.json")
    stage_copy(ROCKER_PIN_IMAGE, "rocker-pin/front-head-rear-ring-mid.png")
    stage_copy(ROOT / "cad/electric-rocker-pin-retention-screen.scad",
               "rocker-pin/electric-rocker-pin-retention-screen.scad")
    pin_doc = stage_copy(ROOT / "docs/electric-rocker-pin-retention-screen.md",
                         "electric-rocker-pin-retention-screen.md")
    pin_doc.write_text(pin_doc.read_text().replace(
        "../output/electric-rocker-pin-retention-screen/", "rocker-pin/"))
    assets[-1]["sha256"] = sha(pin_doc)
    stage_copy(ROCKER_CLAMP_REPORT, "rocker-clamp/review.json")
    stage_copy(ROCKER_CLAMP_ROOT / "bracket.stl", "rocker-clamp/bracket.stl")
    stage_copy(ROOT / "cad/electric-rocker-clamped-fork-screen.scad",
               "rocker-clamp/electric-rocker-clamped-fork-screen.scad")
    for name in ROCKER_CLAMP_IMAGES:
        stage_copy(ROCKER_CLAMP_ROOT / name, f"rocker-clamp/{name}")
    clamp_doc = stage_copy(ROOT / "docs/electric-rocker-clamped-fork-screen.md",
                           "electric-rocker-clamped-fork-screen.md")
    clamp_doc.write_text(clamp_doc.read_text().replace(
        "../cad/electric-rocker-clamped-fork-screen.scad",
        "rocker-clamp/electric-rocker-clamped-fork-screen.scad").replace(
        "../cad/electric-rocker-pivot-joint-screen.scad",
        "rocker-joint/electric-rocker-pivot-joint-screen.scad").replace(
        "../output/electric-rocker-clamped-fork-screen/", "rocker-clamp/"))
    assets[-1]["sha256"] = sha(clamp_doc)
    stage_copy(OUTPUT_CROSSHEAD_REPORT, "output-crosshead/review.json")
    stage_copy(OUTPUT_CROSSHEAD_SLICE, "output-crosshead/slice-review.json")
    stage_copy(OUTPUT_CROSSHEAD_ASSEMBLY, "output-crosshead/assembly-review.json")
    stage_copy(OUTPUT_PIN_LOAD, "output-crosshead/pin-retention-load-screen.json")
    stage_copy(OUTPUT_CROSSHEAD_3MF,
               "output-crosshead/slices/carriage-x-plus-90-tree/slice-review.3mf")
    stage_copy(OUTPUT_CROSSHEAD_SLICE_IMAGE,
               "output-crosshead/slices/carriage-x-plus-90-tree/plate-preview.png")
    stage_copy(ROOT / "cad/electric-output-crosshead-screen.scad",
               "output-crosshead/electric-output-crosshead-screen.scad")
    stage_copy(ROOT / "cad/electric-output-assembly-screen.scad",
               "output-crosshead/electric-output-assembly-screen.scad")
    for name in ("crosshead", "carriage"):
        stage_copy(OUTPUT_CROSSHEAD_ROOT / f"{name}.stl",
                   f"output-crosshead/{name}.stl")
    for name in OUTPUT_CROSSHEAD_IMAGES:
        stage_copy(OUTPUT_CROSSHEAD_ROOT / name, f"output-crosshead/{name}")
    crosshead_doc = stage_copy(ROOT / "docs/electric-output-crosshead-screen.md",
                               "electric-output-crosshead-screen.md")
    crosshead_doc.write_text(crosshead_doc.read_text().replace(
        "../cad/electric-output-crosshead-screen.scad",
        "output-crosshead/electric-output-crosshead-screen.scad").replace(
        "../output/electric-output-crosshead-screen/", "output-crosshead/"))
    assets[-1]["sha256"] = sha(crosshead_doc)
    stage_copy(SERVICE_FORK_REPORT, "service-fork/review.json")
    stage_copy(SERVICE_FORK_SLICE, "service-fork/slice-review.json")
    stage_copy(SERVICE_FORK_LOAD, "service-fork/load-screen.json")
    stage_copy(SERVICE_FORK_ORIENTATION, "service-fork/orientation-screen.json")
    stage_copy(SERVICE_FORK_X40_PREVIEW,
               "service-fork/orientation-screen/base-x-plus-40-tree/plate-preview.png")
    stage_copy(ROOT / "cad/electric-rocker-service-fork-screen.scad",
               "service-fork/electric-rocker-service-fork-screen.scad")
    for name in ("base", "rear"):
        stage_copy(SERVICE_FORK_ROOT / f"{name}.stl", f"service-fork/{name}.stl")
    for name in SERVICE_FORK_IMAGES:
        stage_copy(SERVICE_FORK_ROOT / name, f"service-fork/{name}")
    for label in ("base-x-plus-90-tree", "rear-x-minus-90-tree"):
        folder = SERVICE_FORK_ROOT / "slices" / label
        for name in ("slice-review.3mf", "plate-preview.png"):
            stage_copy(folder / name, f"service-fork/slices/{label}/{name}")
    service_fork_doc = stage_copy(ROOT / "docs/electric-rocker-service-fork-screen.md",
                                  "electric-rocker-service-fork-screen.md")
    service_fork_doc.write_text(service_fork_doc.read_text().replace(
        "../cad/electric-rocker-service-fork-screen.scad",
        "service-fork/electric-rocker-service-fork-screen.scad").replace(
        "../output/electric-rocker-service-fork-screen/", "service-fork/").replace(
        "../output/electric-output-crosshead-screen/assembly-review.json",
        "output-crosshead/assembly-review.json"))
    assets[-1]["sha256"] = sha(service_fork_doc)
    stage_copy(SERVICE_FORK_REINFORCEMENT_REPORT,
               "service-fork-reinforcement/review.json")
    stage_copy(SERVICE_FORK_ROOT_SECTION,
               "service-fork-reinforcement/root-section-screen.json")
    stage_copy(ROOT / "analysis/service_fork_root_section_screen.py",
               "service-fork-reinforcement/root-section-screen.py")
    stage_copy(ROOT / "analysis/service_fork_section_requirements.txt",
               "service-fork-reinforcement/section-requirements.txt")
    stage_copy(SERVICE_FORK_REINFORCEMENT_ROOT / "base-reinforced-screen.stl",
               "service-fork-reinforcement/base-reinforced-screen.stl")
    stage_copy(SERVICE_FORK_REINFORCEMENT_ROOT / "beam-extension-context.png",
               "service-fork-reinforcement/beam-extension-context.png")
    stage_copy(ROOT / "cad/electric-rocker-service-fork-reinforcement-screen.scad",
               "service-fork-reinforcement/candidate.scad")
    reinforcement_doc = stage_copy(
        ROOT / "docs/electric-rocker-service-fork-reinforcement-screen.md",
        "electric-rocker-service-fork-reinforcement-screen.md")
    reinforcement_doc.write_text(reinforcement_doc.read_text().replace(
        "../cad/electric-rocker-service-fork-reinforcement-screen.scad",
        "service-fork-reinforcement/candidate.scad").replace(
        "../output/electric-rocker-service-fork-reinforcement-screen/",
        "service-fork-reinforcement/").replace(
        "../analysis/service_fork_root_section_screen.py",
        "service-fork-reinforcement/root-section-screen.py").replace(
        "../analysis/service_fork_section_requirements.txt",
        "service-fork-reinforcement/section-requirements.txt").replace(
        "../output/electric-rocker-service-fork-screen/load-screen.json",
        "service-fork/load-screen.json"))
    assets[-1]["sha256"] = sha(reinforcement_doc)
    stage_copy(SERVICE_FORK_ROOT_WEB_REPORT, "service-fork-root-web/review.json")
    stage_copy(SERVICE_FORK_ROOT_WEB_SECTION,
               "service-fork-root-web/root-web-section.json")
    stage_copy(SERVICE_FORK_ROOT_WEB_ORIENTATION,
               "service-fork-root-web/orientation-screen.json")
    stage_copy(ROOT / "analysis/service_fork_root_web_section.py",
               "service-fork-root-web/root-web-section.py")
    stage_copy(ROOT / "scripts/screen_electric_rocker_root_gusset_orientation.py",
               "service-fork-root-web/orientation-screen.py")
    for name in ("slice-review.3mf", "plate-preview.png"):
        stage_copy(SERVICE_FORK_ROOT_WEB_X55 / name,
                   f"service-fork-root-web/slice-screen/orientation-screen/base-x-plus-55-tree/{name}")
    stage_copy(SERVICE_FORK_ROOT_WEB_ROOT / "slice-screen/base-x-plus-55-no-support/result.json",
               "service-fork-root-web/slice-screen/base-x-plus-55-no-support/result.json")
    for name in ("base-root-web-screen.stl", "added-root-web-screen.stl",
                 "root-web-context.png"):
        stage_copy(SERVICE_FORK_ROOT_WEB_ROOT / name, f"service-fork-root-web/{name}")
    stage_copy(ROOT / "cad/electric-rocker-root-gusset-screen.scad",
               "service-fork-root-web/candidate.scad")
    root_web_doc = stage_copy(
        ROOT / "docs/electric-rocker-root-gusset-screen.md",
        "electric-rocker-root-gusset-screen.md")
    root_web_doc.write_text(root_web_doc.read_text().replace(
        "../cad/electric-rocker-root-gusset-screen.scad",
        "service-fork-root-web/candidate.scad").replace(
        "../output/electric-rocker-root-gusset-screen/",
        "service-fork-root-web/").replace(
        "../analysis/service_fork_root_web_section.py",
        "service-fork-root-web/root-web-section.py").replace(
        "../scripts/screen_electric_rocker_root_gusset_orientation.py",
        "service-fork-root-web/orientation-screen.py").replace(
        "../analysis/service_fork_section_requirements.txt",
        "service-fork-reinforcement/section-requirements.txt"))
    assets[-1]["sha256"] = sha(root_web_doc)
    stage_copy(ROCKER_PLANE_REPORT, "rocker-plane/review.json")
    stage_copy(ROCKER_PLANE_IMAGE, "rocker-plane/outer-plane-context.png")
    optical_doc = stage_copy(ROOT / "docs/optical-home-candidate.md",
                             "optical-home-candidate.md")
    optical_doc.write_text(optical_doc.read_text().replace(
        "../output/optical-home-candidate/transition-budget.json",
        "optical-home/transition-budget.json").replace(
        "../output/analysis/point-shot-interlock.json",
        "optical-home/partial-return-counterexample.json").replace(
        "../output/electric-trigger-integration/review.json",
        "trigger-candidate/integration-review.json").replace(
        "../cad/electric-feeder-trigger-assembly.scad",
        "models.html?trigger=1"))
    assets[-1]["sha256"] = sha(optical_doc)
    stage_copy(OPTICAL_BUDGET, "optical-home/transition-budget.json")
    stage_copy(PARTIAL_RETURN, "optical-home/partial-return-counterexample.json")
    for source, destination in (
        ("overall-pulled.png", "overall.png"),
        ("mechanism-rest.png", "rest.png"),
        ("mechanism-pulled.png", "pulled.png"),
    ):
        stage_copy(ROOT / "output/electronic-trigger-candidate" / source,
                   "trigger-candidate/" + destination)
    stage_copy(TRIGGER_REPORT, "trigger-candidate/review.json")
    stage_copy(TRIGGER_SLICE, "trigger-candidate/slice-review.json")
    stage_copy(TRIGGER_RENDER, "trigger-candidate/render-report.json")
    stage_copy(TRIGGER_RELEASE, "trigger-candidate/release-margin.json")
    stage_copy(TRIGGER_FSM, "trigger-candidate/point-shot-fsm.json")
    stage_copy(TRIGGER_CORE, "trigger-candidate/point-shot-core-review.json")
    stage_copy(TRIGGER_INTEGRATION, "trigger-candidate/integration-review.json")
    stage_copy(WIRE_RELIEF_REPORT, "trigger-wire-relief/review.json")
    stage_copy(WIRE_RELIEF_SLICE, "trigger-wire-relief/slice-review.json")
    stage_copy(TRIGGER_FASTENER_REPORT, "trigger-fastener/review.json")
    stage_copy(TRIGGER_FASTENER_ROOT / "fastener-access.png",
               "trigger-fastener/fastener-access.png")
    stage_copy(ROOT / "cad/electronic-trigger-fastener-access-screen.scad",
               "trigger-fastener/electronic-trigger-fastener-access-screen.scad")
    stage_copy(WIRE_RELIEF_ROOT / "beam-candidate.stl", "trigger-wire-relief/beam-candidate.stl")
    stage_copy(ROOT / "cad/electronic-trigger-wire-relief-screen.scad",
               "trigger-wire-relief/electronic-trigger-wire-relief-screen.scad")
    for name in ("released.png", "pulled.png", "front.png"):
        stage_copy(WIRE_RELIEF_ROOT / name, f"trigger-wire-relief/{name}")
    for name in ("slice-review.3mf", "plate-preview.png"):
        stage_copy(WIRE_RELIEF_ROOT / "slice-x-minus-90-tree" / name,
                   f"trigger-wire-relief/slice-x-minus-90-tree/{name}")
    trigger_meshes = {}
    for name in ("beam", "lever"):
        source = ROOT / "output/electronic-trigger-candidate" / f"{name}.stl"
        if sha(source) != trigger["parts"][name]["sha256"]:
            raise RuntimeError(f"Electronic trigger scene mesh changed: {name}")
        path = f"trigger-candidate/{name}.stl"
        stage_copy(source, path)
        trigger_meshes[name] = {"file": path, "sha256": sha(source)}
    trigger_geometry = trigger_scene_parameters()
    pivot_x, _, pivot_z = trigger_geometry["pivot_mm"]
    angle = math.radians(-8)
    moving_x_at_pull = pivot_x + (
        trigger_geometry["et_spring_moving_seat_x"] - pivot_x
    ) * math.cos(angle) + (
        trigger_geometry["et_spring_center_z"] - pivot_z
    ) * math.sin(angle)
    spring_rest = trigger_geometry["et_spring_fixed_seat_x"] \
        - trigger_geometry["et_spring_moving_seat_x"]
    spring_pulled = trigger_geometry["et_spring_fixed_seat_x"] - moving_x_at_pull
    spring_contract = trigger["spring_catalog_contract"]
    if abs(spring_rest - spring_contract["rest_installed_length_mm"]) > 0.001 \
            or abs(spring_pulled - spring_contract["pulled_installed_length_mm"]) > 0.001:
        raise RuntimeError("Trigger animation differs from the reviewed spring endpoints")
    trigger_scene = {
        "status": "NOMINAL_TRIGGER_CANDIDATE_VIEW_ONLY",
        "source_sha256": sha(ROOT / "cad/electronic-trigger-candidate.scad"),
        "review_sha256": sha(TRIGGER_REPORT),
        "replacement_for": "feeder/beam-grip",
        "meshes": trigger_meshes,
        "geometry": trigger_geometry,
        "pull_angle_deg": -8,
        "spring_installed_lengths_mm": {"released": spring_rest,
                                         "pulled": round(spring_pulled, 3)},
        "selected_inventory_promoted": True,
        "real_switch_spring_and_motor_verified": False,
        "hardware_refs_are_proxies": True,
    }
    scene_path = stage / "trigger-candidate/scene.json"
    scene_path.write_text(json.dumps(trigger_scene, ensure_ascii=False, indent=2) + "\n")
    assets.append({"file": "trigger-candidate/scene.json", "sha256": sha(scene_path)})

    with (stage / "printed-parts.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["编号", "名称", "材料候选", "3D路径", "状态"])
        for part in parts:
            writer.writerow([part["id"], part["name"],
                             "Bambu TPU 95A HF" if part["id"] == "spin/pad" else "PETG",
                             part["file"], "结构候选，电动版未放行"])
    assets.append({"file": "printed-parts.csv", "sha256": sha(stage / "printed-parts.csv")})
    (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    evidence = {
        "snapshot": manifest["snapshot"], "printed_instances": 49,
        "selected_inventory_sha256": sha(INVENTORY),
        "geometry_review_sha256": sha(CURRENT_REPORT),
        "electronic_trigger_candidate_review_sha256": sha(TRIGGER_REPORT),
        "electronic_trigger_candidate_slice_sha256": sha(TRIGGER_SLICE),
        "electronic_trigger_candidate_render_sha256": sha(TRIGGER_RENDER),
        "electronic_trigger_release_margin_sha256": sha(TRIGGER_RELEASE),
        "electronic_trigger_point_shot_fsm_sha256": sha(TRIGGER_FSM),
        "electronic_trigger_point_shot_core_review_sha256": sha(TRIGGER_CORE),
        "electronic_trigger_point_shot_core_doc_sha256": sha(core_doc),
        "electronic_trigger_integration_sha256": sha(TRIGGER_INTEGRATION),
        "electronic_trigger_wire_relief_review_sha256": sha(WIRE_RELIEF_REPORT),
        "electronic_trigger_wire_relief_slice_sha256": sha(WIRE_RELIEF_SLICE),
        "electronic_trigger_wire_relief_doc_sha256": sha(wire_relief_doc),
        "electronic_trigger_fastener_review_sha256": sha(TRIGGER_FASTENER_REPORT),
        "electronic_trigger_fastener_doc_sha256": sha(trigger_fastener_doc),
        "optical_home_transition_budget_sha256": sha(OPTICAL_BUDGET),
        "electronic_trigger_scene_sha256": sha(scene_path),
        "electric_drive_feasibility_sha256": sha(DRIVE_REPORT),
        "by141_driver_screen_sha256": sha(DRIVER_SCREEN),
        "by141_driver_doc_sha256": sha(driver_screen_doc),
        "electric_drive_route_sha256": sha(ROUTE_REPORT),
        "by141_envelope_screen_sha256": sha(ENVELOPE_REPORT),
        "home_switch_screen_sha256": sha(HOME_SWITCH_REPORT),
        "full_stroke_switch_screen_sha256": sha(FULL_SWITCH_REPORT),
        "front_switch_rejected_sha256": sha(FRONT_SWITCH_REJECTED_REPORT),
        "side_switch_candidate_sha256": sha(SIDE_SWITCH_REPORT),
        "side_switch_slice_sha256": sha(SIDE_SWITCH_SLICE),
        "endpoint_signal_window_sha256": sha(ENDPOINT_SIGNAL),
        "endpoint_signal_doc_sha256": sha(signal_doc),
        "rocker_bridge_screen_sha256": sha(ROCKER_BRIDGE_REPORT),
        "rocker_pivot_mount_screen_sha256": sha(ROCKER_PIVOT_REPORT),
        "rocker_pivot_joint_screen_sha256": sha(ROCKER_JOINT_REPORT),
        "rocker_pin_retention_screen_sha256": sha(ROCKER_PIN_REPORT),
        "rocker_clamped_fork_screen_sha256": sha(ROCKER_CLAMP_REPORT),
        "output_crosshead_screen_sha256": sha(OUTPUT_CROSSHEAD_REPORT),
        "output_crosshead_slice_sha256": sha(OUTPUT_CROSSHEAD_SLICE),
        "output_crosshead_assembly_sha256": sha(OUTPUT_CROSSHEAD_ASSEMBLY),
        "service_fork_screen_sha256": sha(SERVICE_FORK_REPORT),
        "service_fork_slice_sha256": sha(SERVICE_FORK_SLICE),
        "service_fork_load_sha256": sha(SERVICE_FORK_LOAD),
        "service_fork_orientation_sha256": sha(SERVICE_FORK_ORIENTATION),
        "service_fork_reinforcement_sha256": sha(SERVICE_FORK_REINFORCEMENT_REPORT),
        "service_fork_root_section_sha256": sha(SERVICE_FORK_ROOT_SECTION),
        "service_fork_reinforcement_doc_sha256": sha(reinforcement_doc),
        "service_fork_root_web_sha256": sha(SERVICE_FORK_ROOT_WEB_REPORT),
        "service_fork_root_web_section_sha256": sha(SERVICE_FORK_ROOT_WEB_SECTION),
        "service_fork_root_web_orientation_sha256": sha(SERVICE_FORK_ROOT_WEB_ORIENTATION),
        "service_fork_root_web_doc_sha256": sha(root_web_doc),
        "output_pin_load_sha256": sha(OUTPUT_PIN_LOAD),
        "service_fork_doc_sha256": sha(service_fork_doc),
        "output_crosshead_doc_sha256": sha(crosshead_doc),
        "rocker_plane_screen_sha256": sha(ROCKER_PLANE_REPORT),
        "reused_common_mesh_report": str(OLD_REPORT.relative_to(ROOT)),
        "reused_common_mesh_report_sha256": sha(OLD_REPORT),
        "parts": {p["id"]: p["sha256"] for p in parts}, "assets": assets,
        "historical_motion_page": "feeder-motion.html",
        "motor_mount_designed": False, "manufacturing_release": False,
        "electronic_trigger_selected": True,
        "electronic_trigger_physically_installed": False,
        "physical_acceptance": False,
    }
    (stage / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    (stage / "revision-status.json").write_text(json.dumps({
        "status": "ELECTRIC_STRUCTURE_PREVIEW_MOTOR_INTERFACE_OPEN",
        "snapshot": manifest["snapshot"], "printed_instances": 49,
        "motor_mount_designed": False, "manufacturing_release": False,
        "electronic_trigger_candidate_reviewed": True,
        "electronic_trigger_selected": True,
        "electronic_trigger_physically_installed": False,
        "physical_acceptance": False,
    }, ensure_ascii=False, indent=2) + "\n")

    checked_sources(old["source_sha256"])
    checked_sources(current["source_sha256"])
    checked_sources(trigger["source_sha256"])
    checked_sources(integration["source_sha256"])
    checked_sources(wire_relief["source_sha256"])
    checked_sources(wire_relief_slice["source_sha256"])
    checked_sources(trigger_fastener["source_sha256"])
    checked_sources(route["source_sha256"])
    checked_sources(envelope["source_sha256"])
    checked_sources(full_switch["source_sha256"])
    checked_sources(front_switch_rejected["source_sha256"])
    checked_sources(side_switch["source_sha256"])
    checked_sources(side_switch_slice["source_sha256"])
    checked_sources(rocker_bridge["source_sha256"])
    checked_sources(rocker_pivot["source_sha256"])
    checked_sources(rocker_joint["source_sha256"])
    checked_sources(rocker_pin["source_sha256"])
    checked_sources(rocker_clamp["source_sha256"])
    checked_sources(trigger_fsm["source_sha256"])
    checked_sources(inventory["source_sha256"])
    for asset in assets:
        if sha(stage / asset["file"]) != asset["sha256"]:
            raise RuntimeError(f"Staged preview asset changed: {asset['file']}")
    previous = json.loads((PUBLIC / "manifest.json").read_text())
    if previous.get("snapshot") != manifest["snapshot"]:
        backup = ROOT / "output/preview-history" / (
            "before-electric-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        backup.mkdir(parents=True, exist_ok=True)
        for name in ("index.html", "models.html", "manifest.json", "evidence.json",
                     "revision-status.json", "printed-parts.csv", "feeder-motion.html",
                     "feeder-motion.mjs"):
            source = PUBLIC / name
            if source.exists():
                shutil.copy2(source, backup / name)
    else:
        backup = None
    # Give the old page its new historical label before promoting the home page.
    entries = [p for p in stage.rglob("*") if p.is_file()]
    last = {"manifest.json", "revision-status.json", "evidence.json", "index.html"}
    entries.sort(key=lambda p: (p.name in last, p.name == "index.html", str(p)))
    for source in entries:
        target = PUBLIC / source.relative_to(stage)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.replace(target)
    for stale in ("rocker-bridge/r75-y55-home.png",
                  "rocker-bridge/r75-y55-full.png"):
        (PUBLIC / stale).unlink(missing_ok=True)
    shutil.rmtree(stage)
    receipt = {"status": "ELECTRIC_PREVIEW_PUBLISHED", "parts": 49,
               "manifest_sha256": sha(PUBLIC / "manifest.json"),
               "backup": str(backup.relative_to(ROOT)) if backup else None,
               "manufacturing_release": False, "physical_acceptance": False}
    target = ROOT / "output/electric-feeder/publication.json"
    target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(f"Current electric structure published: 49 selected printed parts; {PUBLIC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
