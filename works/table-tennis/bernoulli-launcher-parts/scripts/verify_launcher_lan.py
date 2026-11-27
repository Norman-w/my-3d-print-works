#!/usr/bin/env python3
"""Verify the exact published candidate through this Mac's LAN interface."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'output/revision-review'


def main():
    ip = subprocess.check_output(['ipconfig', 'getifaddr', 'en0'], text=True).strip()
    base = f'http://{ip}:8877/'
    client = build_opener(ProxyHandler({}))
    def fetch(name):
        with client.open(base + quote(name, safe='/'), timeout=30) as response:
            return response.read(), dict(response.headers)
    manifest = json.loads((PUBLIC / 'manifest.json').read_text())
    evidence = json.loads((PUBLIC / 'evidence.json').read_text())
    electric = manifest.get('snapshot') == 'electric-drive-selected-unreleased'
    api = json.loads(fetch('api/parts')[0])
    assert api['parts'] == manifest['parts'], 'Live API differs from published manifest'
    if electric:
        assert api['count'] == 49 and evidence['snapshot'] == manifest['snapshot']
        assert not any('cable' in part['id'] for part in api['parts'])
        assert evidence['parts'] == {part['id']: part['sha256'] for part in api['parts']}
        assert not evidence['motor_mount_designed'] and not manifest['motor_mount_designed']
        assert manifest.get('electronic_trigger_candidate_reviewed') is True
        assert manifest.get('electronic_trigger_selected') is True
        assert manifest.get('electronic_trigger_physically_installed') is False
        assert evidence.get('electronic_trigger_selected') is True
        assert evidence.get('electronic_trigger_physically_installed') is False
        assert sha256((ROOT/'docs/electric-assembly-inventory.json').read_bytes()).hexdigest() == evidence['selected_inventory_sha256']
        assert sha256((ROOT/'output/electric-feeder/review.json').read_bytes()).hexdigest() == evidence['geometry_review_sha256']
        assert sha256((ROOT/'output/electronic-trigger-candidate/review.json').read_bytes()).hexdigest() == evidence['electronic_trigger_candidate_review_sha256']
        assert sha256((ROOT/'output/electronic-trigger-candidate/slice-review.json').read_bytes()).hexdigest() == evidence['electronic_trigger_candidate_slice_sha256']
        trigger_slice = json.loads((PUBLIC/'trigger-candidate/slice-review.json').read_text())
        assert trigger_slice['status'] == 'CANDIDATE_SLICED_UNRELEASED'
        assert trigger_slice['parts']['beam']['support_extrusion_segments_crossing_m2_slot_cores_with_0p25mm_margin'] == {
            'lower_m2_slot_core': 0, 'upper_m2_slot_core': 0}
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in trigger_slice['source_sha256'].items())
        assert sha256((ROOT/'output/electronic-trigger-candidate/render-report.json').read_bytes()).hexdigest() == evidence['electronic_trigger_candidate_render_sha256']
        trigger_source = (ROOT/'cad/electronic-trigger-candidate.scad').read_text()
        switch_y = re.search(r'^et_switch_y\s*=\s*(-?\d+(?:\.\d+)?)\s*;', trigger_source, re.M)
        plate_y = re.search(r'^et_backplate_front_y\s*=\s*(-?\d+(?:\.\d+)?)\s*;', trigger_source, re.M)
        assert switch_y and plate_y and float(switch_y.group(1)) == float(plate_y.group(1))
        release_report = json.loads((PUBLIC/'trigger-candidate/release-margin.json').read_text())
        assert release_report['status'] == 'NOMINAL_RELEASE_MARGIN_PASS_REAL_LEVER_UNVERIFIED'
        assert release_report['manufacturing_release'] is False
        assert release_report['source']['cad_sha256'] == sha256((ROOT/'cad/electronic-trigger-candidate.scad').read_bytes()).hexdigest()
        assert release_report['source']['analysis_script_sha256'] == sha256((ROOT/'analysis/electronic_trigger_release_margin.py').read_bytes()).hexdigest()
        assert release_report['source']['geometry_review_sha256'] == evidence['electronic_trigger_candidate_review_sha256']
        integration = json.loads((PUBLIC/'trigger-candidate/integration-review.json').read_text())
        assert integration['status'] == 'SELECTED_TRIGGER_GEOMETRY_PASS_UNRELEASED'
        assert integration['trigger_geometry_review_sha256'] == evidence['electronic_trigger_candidate_review_sha256']
        assert integration['old_beam_replaced_not_coinstalled'] is True
        assert integration['manufacturing_release'] is False
        assert integration['assembly_image']['sha256'] == sha256((PUBLIC/'electric-models/current-assembly.png').read_bytes()).hexdigest()
        assert sha256((PUBLIC/'trigger-candidate/integration-review.json').read_bytes()).hexdigest() == evidence['electronic_trigger_integration_sha256']
        assert sha256((PUBLIC/'trigger-candidate/release-margin.json').read_bytes()).hexdigest() == evidence['electronic_trigger_release_margin_sha256']
        wire_relief = json.loads((PUBLIC/'trigger-wire-relief/review.json').read_text())
        assert wire_relief['status'] == 'WIRE_RELIEF_NOMINAL_GEOMETRY_ONLY'
        assert wire_relief['predecessor_sha256'] == {
            'output/electronic-trigger-candidate/review.json': evidence['electronic_trigger_candidate_review_sha256'],
            'output/electric-trigger-integration/review.json': evidence['electronic_trigger_integration_sha256']}
        assert wire_relief['empty_probe_count'] == 27
        assert wire_relief['positive_control_count'] == 2 and wire_relief['failures'] == []
        assert wire_relief['part']['watertight'] is True
        assert wire_relief['part']['connected_components'] == 1
        assert wire_relief['promoted_to_selected_beam'] is True
        assert wire_relief['manufacturing_release'] is False
        assert wire_relief['physical_acceptance'] is False
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in wire_relief['source_sha256'].items())
        assert sha256((PUBLIC/'trigger-wire-relief/review.json').read_bytes()).hexdigest() == evidence['electronic_trigger_wire_relief_review_sha256']
        assert sha256((PUBLIC/'trigger-wire-relief/beam-candidate.stl').read_bytes()).hexdigest() == wire_relief['part']['sha256']
        assert sha256((PUBLIC/'trigger-wire-relief/electronic-trigger-wire-relief-screen.scad').read_bytes()).hexdigest() == wire_relief['source_sha256']['cad/electronic-trigger-wire-relief-screen.scad']
        for row in wire_relief['images'].values():
            assert sha256((PUBLIC/'trigger-wire-relief'/Path(row['file']).name).read_bytes()).hexdigest() == row['sha256']
        wire_relief_slice = json.loads((PUBLIC/'trigger-wire-relief/slice-review.json').read_text())
        assert wire_relief_slice['status'] == 'WIRE_RELIEF_SLICED_UNRELEASED'
        assert wire_relief_slice['geometry_review_sha256'] == evidence['electronic_trigger_wire_relief_review_sha256']
        assert wire_relief_slice['source_stl_sha256'] == wire_relief['part']['sha256']
        assert wire_relief_slice['native_warnings'] == []
        assert wire_relief_slice['archive_integrity_pass'] is True
        assert all(v == 0 for v in wire_relief_slice['support_extrusion_segments_crossing_tie_holes_with_0p25mm_margin'].values())
        assert wire_relief_slice['promoted_to_selected_beam'] is True
        assert wire_relief_slice['printer_sent'] is False
        assert wire_relief_slice['manufacturing_release'] is False
        assert wire_relief_slice['physical_acceptance'] is False
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in wire_relief_slice['source_sha256'].items())
        assert sha256((PUBLIC/'trigger-wire-relief/slice-review.json').read_bytes()).hexdigest() == evidence['electronic_trigger_wire_relief_slice_sha256']
        assert sha256((PUBLIC/'trigger-wire-relief/slice-x-minus-90-tree/slice-review.3mf').read_bytes()).hexdigest() == wire_relief_slice['slice_3mf_sha256']
        assert sha256((PUBLIC/'trigger-wire-relief/slice-x-minus-90-tree/plate-preview.png').read_bytes()).hexdigest() == wire_relief_slice['preview_sha256']
        assert sha256((PUBLIC/'electronic-trigger-wire-relief-screen.md').read_bytes()).hexdigest() == evidence['electronic_trigger_wire_relief_doc_sha256']
        assert b'electronic-trigger-wire-relief-screen.md' in (PUBLIC/'electronic-trigger.md').read_bytes()
        assert b'electronic-trigger-wire-relief-screen.md' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'trigger-wire-relief/released.png' in (PUBLIC/'electronic-trigger-wire-relief-screen.md').read_bytes()
        fastener = json.loads((PUBLIC/'trigger-fastener/review.json').read_text())
        assert fastener['status'] == 'TRIGGER_M2_ACCESS_NOMINAL_ONLY'
        assert fastener['predecessor_sha256'] == {
            'output/electronic-trigger-candidate/review.json': evidence['electronic_trigger_candidate_review_sha256'],
            'output/electric-trigger-integration/review.json': evidence['electronic_trigger_integration_sha256']}
        assert fastener['empty_probe_count'] == 102
        assert fastener['positive_control_count'] == 2 and fastener['failures'] == []
        assert fastener['fastener_candidate']['shank_projection_past_nut_nominal_mm'] == 1.7
        assert fastener['fastener_candidate']['shank_projection_past_nut_case_max_only_mm'] == 1.55
        assert fastener['fastener_candidate']['rear_washer_proxy_diameter_mm'] == 7
        assert fastener['fastener_candidate']['head_proxy_height_mm'] == 2
        assert fastener['switch_slot_fit']['printed_slot_width_nominal_mm'] == 2.8
        assert fastener['switch_slot_fit']['radial_allowance_after_half_pitch_error_before_print_mm'] == .325
        assert fastener['selected_beam_unchanged'] is True
        assert fastener['actual_switch_hole_and_terminal_fit_verified'] is False
        assert fastener['manufacturing_release'] is False
        assert fastener['physical_acceptance'] is False
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in fastener['source_sha256'].items())
        assert sha256((PUBLIC/'trigger-fastener/review.json').read_bytes()).hexdigest() == evidence['electronic_trigger_fastener_review_sha256']
        assert sha256((PUBLIC/'trigger-fastener/fastener-access.png').read_bytes()).hexdigest() == fastener['image_sha256']
        assert sha256((PUBLIC/'trigger-fastener/electronic-trigger-fastener-access-screen.scad').read_bytes()).hexdigest() == fastener['source_sha256']['cad/electronic-trigger-fastener-access-screen.scad']
        assert sha256((PUBLIC/'electronic-trigger-fastener-access.md').read_bytes()).hexdigest() == evidence['electronic_trigger_fastener_doc_sha256']
        assert b'electronic-trigger-fastener-access.md' in (PUBLIC/'electronic-trigger.md').read_bytes()
        assert b'electronic-trigger-fastener-access.md' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'trigger-fastener/fastener-access.png' in (PUBLIC/'electronic-trigger-fastener-access.md').read_bytes()
        trigger_fsm = json.loads((PUBLIC/'trigger-candidate/point-shot-fsm.json').read_text())
        assert trigger_fsm['status'] == 'REFERENCE_CONTROLLER_CONTRACT_ONLY_MISSING_REAL_INPUTS'
        assert trigger_fsm['exhaustive_boolean_input_review']['checked_transitions'] >= 900
        assert trigger_fsm['normal_cycle']['rows'][4]['after'] == 'RETURN'
        assert trigger_fsm['partial_return_timeout']['final_state'] == 'FAULT'
        assert trigger_fsm['coast_past_zero_after_drive_cut']['final_state'] == 'FAULT'
        assert trigger_fsm['coast_past_zero_after_drive_cut']['completed_cycle_count'] == 0
        assert trigger_fsm['mcu_firmware_implemented'] is False
        assert sha256((ROOT/'output/electronic-trigger-candidate/point-shot-fsm.json').read_bytes()).hexdigest() == evidence['electronic_trigger_point_shot_fsm_sha256']
        core = json.loads((PUBLIC/'trigger-candidate/point-shot-core-review.json').read_text())
        assert core['status'] == 'PORTABLE_CORE_MATCHES_REFERENCE_UNRELEASED'
        assert core['cross_language_boolean_transition_count'] == 3584
        assert core['mismatches'] == [] and core['invalid_state_fails_closed'] is True
        assert core['hardware_adapter_implemented'] is False
        assert core['motor_driver_selected'] is False
        assert core['manufacturing_release'] is False
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in core['source_sha256'].items())
        assert sha256((PUBLIC/'trigger-candidate/point-shot-core-review.json').read_bytes()).hexdigest() == evidence['electronic_trigger_point_shot_core_review_sha256']
        assert sha256((PUBLIC/'point-shot-core.md').read_bytes()).hexdigest() == evidence['electronic_trigger_point_shot_core_doc_sha256']
        assert b'trigger-candidate/point-shot-fsm.json' in (PUBLIC/'electronic-trigger.md').read_bytes()
        assert b'point-shot-core.md' in (PUBLIC/'electronic-trigger.md').read_bytes()
        assert b'trigger-candidate/point-shot-core-review.json' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'trigger-candidate/release-margin.json' in (PUBLIC/'electronic-trigger.md').read_bytes()
        optical_budget = json.loads((PUBLIC/'optical-home/transition-budget.json').read_text())
        assert optical_budget['status'] == 'GEOMETRIC_NEAR_HOME_ONLY_ZERO_UNPROVEN'
        assert optical_budget['optical_blocked_alone_confirms_mechanical_zero'] is False
        assert optical_budget['one_shot_rearm_from_optical_blocked_alone_permitted'] is False
        ambiguity = optical_budget['partial_return_double_shot_observability']
        assert ambiguity['counterexample_feeder_displacement_mm'] == 1.0
        assert ambiguity['counterexample_output_count_if_retriggered_before_true_zero'] == 2
        assert ambiguity['modelled_blocked_boolean_distinguishes_u0_from_unsafe_u'] is False
        assert all(ambiguity['modelled_entire_optical_window_covered_at_unsafe_u_by_sensor_adjustment'].values())
        assert optical_budget['source']['partial_return_counterexample_report_sha256'] == sha256((PUBLIC/'optical-home/partial-return-counterexample.json').read_bytes()).hexdigest()
        assert optical_budget['source']['partial_return_counterexample_report_sha256'] == sha256((ROOT/'output/analysis/point-shot-interlock.json').read_bytes()).hexdigest()
        assert optical_budget['source']['cad_sha256'] == sha256((ROOT/'cad/feeder-optical-home.scad').read_bytes()).hexdigest()
        assert optical_budget['source']['analysis_script_sha256'] == sha256((ROOT/'analysis/optical_home_transition_budget.py').read_bytes()).hexdigest()
        assert sha256((PUBLIC/'optical-home/transition-budget.json').read_bytes()).hexdigest() == evidence['optical_home_transition_budget_sha256']
        for document in ('electronic-trigger.md', 'optical-home-candidate.md', 'electric-status.md'):
            assert b'optical-home/transition-budget.json' in (PUBLIC/document).read_bytes()
        assert b'optical-home/partial-return-counterexample.json' in (PUBLIC/'optical-home-candidate.md').read_bytes()
        trigger_scene = json.loads((PUBLIC/'trigger-candidate/scene.json').read_text())
        assert trigger_scene['status'] == 'NOMINAL_TRIGGER_CANDIDATE_VIEW_ONLY'
        assert trigger_scene['replacement_for'] == 'feeder/beam-grip'
        assert trigger_scene['selected_inventory_promoted'] is True
        assert trigger_scene['real_switch_spring_and_motor_verified'] is False
        assert sha256((ROOT/'cad/electronic-trigger-candidate.scad').read_bytes()).hexdigest() == trigger_scene['source_sha256']
        assert trigger_scene['review_sha256'] == evidence['electronic_trigger_candidate_review_sha256']
        assert sha256((PUBLIC/'trigger-candidate/scene.json').read_bytes()).hexdigest() == evidence['electronic_trigger_scene_sha256']
        trigger_review = json.loads((ROOT/'output/electronic-trigger-candidate/review.json').read_text())
        for name in ('beam', 'lever'):
            row = trigger_scene['meshes'][name]
            assert row['sha256'] == trigger_review['parts'][name]['sha256']
            assert row['sha256'] == integration['printed_parts'][name]['sha256']
            assert sha256((PUBLIC/row['file']).read_bytes()).hexdigest() == row['sha256']
        selected_parts = {part['id']: part for part in api['parts']}
        assert selected_parts['feeder/beam-grip']['sha256'] == integration['printed_parts']['beam']['sha256']
        assert selected_parts['feeder/trigger-lever']['sha256'] == integration['printed_parts']['lever']['sha256']
        assert b'electric-models-app.mjs' in (PUBLIC/'models.html').read_bytes()
        assert b'trigger-candidate/scene.json' in (PUBLIC/'electric-models-app.mjs').read_bytes()
        assert sha256((ROOT/'output/electric-drive-feasibility/report.json').read_bytes()).hexdigest() == evidence['electric_drive_feasibility_sha256']
        driver_screen = json.loads((PUBLIC/'by141-driver-screen.json').read_text())
        assert driver_screen['status'] == 'LOW_VOLTAGE_DRIVER_SCREEN_NO_FINAL_SELECTION'
        assert driver_screen['driver_selected'] is False
        assert driver_screen['power_stage_schematic_complete'] is False
        assert driver_screen['comparisons']['TI DRV8850']['seller_upper_stall_claim_to_driver_peak_headroom_a'] == .5
        assert driver_screen['comparisons']['TI DRV8850']['seller_stall_upper_inside_feedback_spec'] is False
        assert driver_screen['seller_gallery_sha256'] == sha256((ROOT/'output/procurement/reciprocating-20260930/product-evidence.json').read_bytes()).hexdigest()
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in driver_screen['source_sha256'].items())
        assert sha256((ROOT/'output/electric-drive-feasibility/driver-screen.json').read_bytes()).hexdigest() == evidence['by141_driver_screen_sha256']
        assert sha256((PUBLIC/'by141-driver-selection.md').read_bytes()).hexdigest() == evidence['by141_driver_doc_sha256']
        assert b'by141-driver-selection.md' in (PUBLIC/'index.html').read_bytes()
        assert b'by141-driver-screen.json' in (PUBLIC/'by141-driver-selection.md').read_bytes()
        assert b'by141-driver-selection.md' in (PUBLIC/'point-shot-core.md').read_bytes()
        assert sha256((ROOT/'output/electric-drive-route/review.json').read_bytes()).hexdigest() == evidence['electric_drive_route_sha256']
        envelope = json.loads((PUBLIC/'by141-envelope/review.json').read_text())
        assert envelope['status'] == 'SCHEMATIC_SELLER_ENVELOPE_SCREEN_ONLY'
        assert envelope['probe_count'] == 121
        assert envelope['candidates']['d29-x85-y63']['sampled_collision_free'] is True
        assert envelope['probes'][envelope['positive_control']]['occupied'] is True
        assert all(row['sampled_collision_free'] for row in envelope['candidates'].values())
        assert envelope['real_motor_mounted'] is False and envelope['motor_mount_designed'] is False
        assert envelope['context_image']['sha256'] == sha256((PUBLIC/'by141-envelope/context.png').read_bytes()).hexdigest()
        assert sha256((ROOT/'output/by141-envelope-screen/review.json').read_bytes()).hexdigest() == evidence['by141_envelope_screen_sha256']
        assert b'by141-envelope/review.json' in (PUBLIC/'electric-drive-feasibility.md').read_bytes()
        assert b'by141-envelope/context.png' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'by141-zero-print-preflight.md' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'by141-zero-print-preflight.md' in (PUBLIC/'index.html').read_bytes()
        assert (PUBLIC/'by141-zero-print-preflight.md').is_file()
        assert b'by141-seller/detail-07.png' in (PUBLIC/'by141-zero-print-preflight.md').read_bytes()
        assert sha256((PUBLIC/'by141-seller/detail-07.png').read_bytes()).hexdigest() == sha256(
            (ROOT/'output/procurement/reciprocating-20260930/detail-07.png').read_bytes()).hexdigest()
        assert b'by141-live-sku-interface-audit.json' in (PUBLIC/'by141-zero-print-preflight.md').read_bytes()
        live_sku_audit = json.loads((PUBLIC/'by141-live-sku-interface-audit.json').read_text())
        assert live_sku_audit['status'] == 'LIVE_SELECTED_SKU_READ_INTERFACE_INCOMPLETE'
        assert (live_sku_audit['item_id'], live_sku_audit['sku_id']) == ('988456349136', '5952763100025')
        assert sha256((PUBLIC/'by141-live-sku-interface-audit.json').read_bytes()).hexdigest() == sha256(
            (ROOT/'output/procurement/reciprocating-20261001/live-sku-interface-audit.json').read_bytes()).hexdigest()
        assert b'endpoint-compliance-budget.md' in (PUBLIC/'by141-zero-print-preflight.md').read_bytes()
        assert b'endpoint-compliance-budget.md' in (PUBLIC/'electric-drive-feasibility.md').read_bytes()
        assert b'endpoint-compliance-budget.md' in (PUBLIC/'electric-rocker-bridge-screen.md').read_bytes()
        assert b'endpoint-phase-budget.py' in (PUBLIC/'endpoint-compliance-budget.md').read_bytes()
        assert sha256((PUBLIC/'endpoint-phase-budget.py').read_bytes()).hexdigest() == sha256(
            (ROOT/'analysis/endpoint_phase_budget.py').read_bytes()).hexdigest()
        rocker = json.loads((PUBLIC/'rocker-plane/review.json').read_text())
        assert rocker['status'] == 'OUTER_ROCKER_PLANE_CLEARANCE_ONLY'
        assert rocker['probe_count'] == 30 and not rocker['failures']
        assert len(rocker['inner_plane_colliding_probes']) >= 5
        assert rocker['outer_plane_colliding_probes'] == []
        assert rocker['output_crosshead_and_bearing_mount_designed'] is False
        assert rocker['motor_to_input_pin_connection_designed'] is False
        assert rocker['context_image']['sha256'] == sha256((PUBLIC/'rocker-plane/outer-plane-context.png').read_bytes()).hexdigest()
        assert sha256((ROOT/'output/electric-rocker-plane-screen/review.json').read_bytes()).hexdigest() == evidence['rocker_plane_screen_sha256']
        assert b'rocker-plane/review.json' in (PUBLIC/'electric-drive-feasibility.md').read_bytes()
        home_switch = json.loads((PUBLIC/'home-switch/review.json').read_text())
        assert home_switch['status'] == 'HOME_SWITCH_PACKAGING_SCREEN_ONLY'
        assert home_switch['probe_count'] == 33 and not home_switch['failures']
        assert home_switch['integrated_trigger_review_sha256'] == evidence['electronic_trigger_integration_sha256']
        assert home_switch['catalogue_only_calibration_window']['one_mm_return_nominal_release_gap_min_mm'] == .3
        assert home_switch['mounting_bracket_designed'] is False
        assert home_switch['manufacturing_release'] is False
        for name in ('home-context.png', 'one-mm-context.png'):
            assert home_switch['images'][name]['sha256'] == sha256((PUBLIC/'home-switch'/name).read_bytes()).hexdigest()
        assert sha256((ROOT/'output/electric-home-switch-screen/review.json').read_bytes()).hexdigest() == evidence['home_switch_screen_sha256']
        assert b'home-switch/review.json' in (PUBLIC/'electronic-trigger.md').read_bytes()
        assert b'home-switch/home-context.png' in (PUBLIC/'electric-status.md').read_bytes()
        full_switch = json.loads((PUBLIC/'full-switch/review.json').read_text())
        assert full_switch['status'] == 'FULL_STROKE_SWITCH_PACKAGING_SCREEN_ONLY'
        assert full_switch['probe_count'] == 34 and not full_switch['failures']
        assert full_switch['home_switch_review_sha256'] == evidence['home_switch_screen_sha256']
        assert full_switch['integrated_trigger_review_sha256'] == evidence['electronic_trigger_integration_sha256']
        assert full_switch['catalogue_only_calibration_window']['one_mm_before_full_nominal_release_gap_min_mm'] == .3
        assert full_switch['candidate_geometry']['lower_shoulder_and_fixed_guide_continue_to_carry_stop_load'] is True
        assert full_switch['mounting_bracket_designed'] is False
        assert full_switch['moving_tab_promoted_to_selected_carriage'] is False
        assert full_switch['switches_electrically_wired'] is False
        assert full_switch['manufacturing_release'] is False
        for name in ('full-context.png', 'one-mm-before-context.png'):
            assert full_switch['images'][name]['sha256'] == sha256((PUBLIC/'full-switch'/name).read_bytes()).hexdigest()
        assert sha256((ROOT/'output/electric-full-stroke-switch-screen/review.json').read_bytes()).hexdigest() == evidence['full_stroke_switch_screen_sha256']
        assert b'full-switch/review.json' in (PUBLIC/'electronic-trigger.md').read_bytes()
        assert b'full-switch/full-context.png' in (PUBLIC/'electric-status.md').read_bytes()
        rejected = json.loads((PUBLIC/'endpoint-switch/front-rejected-review.json').read_text())
        assert rejected['status'] == 'REJECTED_MOTOR_BLOCKS_SWITCH_ADJUSTMENT'
        assert rejected['service_access_pass'] is False
        assert rejected['promoted_to_selected_parts'] is False
        assert sha256((ROOT/'output/electric-end-switch-cap-candidate/review.json').read_bytes()).hexdigest() == evidence['front_switch_rejected_sha256']
        side = json.loads((PUBLIC/'endpoint-switch/review.json').read_text())
        assert side['status'] == 'SIDE_BOLTED_ENDPOINT_CAP_GEOMETRY_PASS_UNRELEASED'
        assert side['probe_count'] == 227 and not side['failures']
        assert side['service_access_pass'] is True
        assert side['rejected_front_bolt_review_sha256'] == evidence['front_switch_rejected_sha256']
        assert side['promoted_to_selected_parts'] is False
        assert side['manufacturing_release'] is False
        assert side['physical_acceptance'] is False
        assert sha256((ROOT/'output/electric-end-switch-side-cap/review.json').read_bytes()).hexdigest() == evidence['side_switch_candidate_sha256']
        for name, row in side['images'].items():
            assert sha256((PUBLIC/'endpoint-switch'/name).read_bytes()).hexdigest() == row['sha256']
        for name in ('cap', 'carriage'):
            row = side['part_meshes'][name]
            assert row['watertight'] is True
            assert sha256((PUBLIC/'endpoint-switch'/f'{name}.stl').read_bytes()).hexdigest() == row['stl_sha256']
        side_slice = json.loads((PUBLIC/'endpoint-switch/slice-review.json').read_text())
        assert side_slice['status'] == 'SIDE_CAP_AND_CARRIAGE_SLICED_UNRELEASED'
        assert side_slice['geometry_review_sha256'] == evidence['side_switch_candidate_sha256']
        assert side_slice['unsupported_rejected_for_floating_regions'] is True
        assert side_slice['printer_sent'] is False
        assert side_slice['manufacturing_release'] is False
        assert side_slice['physical_acceptance'] is False
        assert not side_slice['failures']
        for name in ('cap-tree-support', 'carriage-tree-support'):
            row = side_slice['orientations'][name]
            assert row['status'] == 'SLICED_UNRELEASED'
            assert row['native_warnings'] == []
            assert row['source_stl_sha256'] == side['part_meshes'][row['part']]['stl_sha256']
            path = PUBLIC/'endpoint-switch/slices'/name/'slice-review.3mf'
            assert sha256(path.read_bytes()).hexdigest() == row['slice_3mf_sha256']
        assert sha256((ROOT/'output/electric-end-switch-side-cap/slice-review.json').read_bytes()).hexdigest() == evidence['side_switch_slice_sha256']
        signal = json.loads((PUBLIC/'endpoint-switch/signal-window.json').read_text())
        assert signal['status'] == 'ILLUSTRATIVE_ENDPOINT_PULSE_SCREEN_REAL_TIMING_UNKNOWN'
        assert signal['five_ms_stable_debounce_safe_from_this_evidence'] is False
        assert signal['home_switch_closed_alone_proves_hard_stop'] is False
        assert signal['full_switch_closed_alone_proves_full_travel'] is False
        assert signal['endpoint_event_capture_and_noise_rejection_finalized'] is False
        assert signal['manufacturing_release'] is False
        assert signal['illustration_only']['cases'][0]['constant_speed_illustration']['total_pressed_window_ms'] == 2.5
        assert sha256((ROOT/'output/electric-end-switch-side-cap/signal-window.json').read_bytes()).hexdigest() == evidence['endpoint_signal_window_sha256']
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in signal['source_sha256'].items())
        assert sha256((PUBLIC/'endpoint-signal-timing.md').read_bytes()).hexdigest() == evidence['endpoint_signal_doc_sha256']
        assert b'endpoint-switch/signal-window.json' in (PUBLIC/'endpoint-signal-timing.md').read_bytes()
        assert b'endpoint-signal-timing.md' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'endpoint-signal-timing.md' in (PUBLIC/'index.html').read_bytes()
        assert b'endpoint-switch-integration.md' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'endpoint-switch-integration.md' in (PUBLIC/'electronic-trigger.md').read_bytes()
        assert b'endpoint-switch/at-home-detail.png' in (PUBLIC/'index.html').read_bytes()
        assert b'endpoint-switch/at-full-detail.png' in (PUBLIC/'index.html').read_bytes()
        endpoint_doc = (PUBLIC/'endpoint-switch-integration.md').read_bytes()
        for name in (b'endpoint-switch/front-rejected-review.json',
                     b'endpoint-switch/review.json', b'endpoint-switch/slice-review.json',
                     b'endpoint-switch/slices/cap-tree-support/slice-review.3mf',
                     b'endpoint-switch/slices/carriage-tree-support/slice-review.3mf'):
            assert name in endpoint_doc
        bridge = json.loads((PUBLIC/'rocker-bridge/review.json').read_text())
        assert bridge['status'] == 'OUTPUT_BRIDGE_LAYOUT_SCREEN_ONLY'
        assert bridge['side_switch_review_sha256'] == evidence['side_switch_candidate_sha256']
        assert bridge['motor_envelope_review_sha256'] == evidence['by141_envelope_screen_sha256']
        assert len(bridge['probes']) == 540
        assert len(bridge['selected_fine_probes']) == 360
        assert len(bridge['selected_end_clearance_probes']) == 24
        assert bridge['screen_contract']['max_input_output_position_identity_residual_mm'] < 1e-10
        assert not bridge['failures']
        assert all(not row.get('occupied') and not row.get('error')
                   for row in bridge['selected_fine_probes'].values())
        assert all(not row.get('occupied') and not row.get('error')
                   for row in bridge['selected_end_clearance_probes'].values())
        assert all(row.get('occupied') for row in bridge['prior_z23_clearance_probe'].values())
        assert bridge['screen_contract']['selected_r75_y62_cap_top_to_bridge_bottom_nominal_mm'] == 2.7
        assert bridge['screen_contract']['selected_r75_y62_dilated_neighbor_clearance_screen_mm'] == 2
        assert bridge['screen_contract']['selected_r75_y62_motor_bridge_clearance_screen_mm'] == 5
        assert bridge['screen_contract']['mount_pivot_motor_clevis_and_pin_retention_designed'] is False
        assert bridge['manufacturing_release'] is False
        assert bridge['physical_acceptance'] is False
        assert sha256((ROOT/'output/electric-rocker-bridge-screen/review.json').read_bytes()).hexdigest() == evidence['rocker_bridge_screen_sha256']
        for name, row in bridge['images'].items():
            assert sha256((PUBLIC/'rocker-bridge'/name).read_bytes()).hexdigest() == row['sha256']
        assert b'electric-rocker-bridge-screen.md' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'electric-rocker-bridge-screen.md' in (PUBLIC/'electric-drive-feasibility.md').read_bytes()
        assert b'electric-rocker-bridge-screen.md' in (PUBLIC/'index.html').read_bytes()
        bridge_doc = (PUBLIC/'electric-rocker-bridge-screen.md').read_bytes()
        for name in (b'rocker-bridge/review.json', b'rocker-bridge/r75-y62-home.png',
                     b'rocker-bridge/r75-y62-full.png',
                     b'rocker-bridge/electric-rocker-bridge-screen.scad'):
            assert name in bridge_doc
        pivot = json.loads((PUBLIC/'rocker-pivot/review.json').read_text())
        assert pivot['status'] == 'PIVOT_MOUNT_LAYOUT_SCREEN_ONLY'
        assert pivot['rocker_report_sha256'] == evidence['rocker_bridge_screen_sha256']
        assert len(pivot['probes']) == 40 and not pivot['failures']
        assert pivot['bracket_mesh']['watertight'] is True
        pivot_phase = pivot['rocker_phase_witness']
        assert 13 < pivot_phase['t1.00']['bounds']['max'][2] - pivot_phase['t0.00']['bounds']['max'][2] < 14
        assert pivot['probes']['screw-tool-with-cap-t0.00']['occupied'] is True
        assert pivot['probes']['screw-tool-cap-off-t0.00']['occupied'] is False
        assert all(not row['occupied'] for key, row in pivot['probes'].items()
                   if 'clearance-1mm' in key)
        assert pivot['manufacturing_release'] is False
        assert pivot['physical_acceptance'] is False
        assert sha256((ROOT/'output/electric-rocker-pivot-mount-screen/review.json').read_bytes()).hexdigest() == evidence['rocker_pivot_mount_screen_sha256']
        for name, row in pivot['images'].items():
            assert row['sha256'] == sha256((PUBLIC/'rocker-pivot'/name).read_bytes()).hexdigest()
        pivot_doc = (PUBLIC/'electric-rocker-pivot-mount-screen.md').read_bytes()
        for name in (b'rocker-pivot/review.json', b'rocker-pivot/pivot-home.png',
                     b'rocker-pivot/pivot-full.png',
                     b'rocker-pivot/electric-rocker-pivot-mount-screen.scad'):
            assert name in pivot_doc
        assert b'electric-rocker-pivot-mount-screen.md' in (PUBLIC/'electric-status.md').read_bytes()
        joint = json.loads((PUBLIC/'rocker-joint/review.json').read_text())
        assert joint['status'] == 'Y62_RETAINER_COLLISION_Y65_LAYOUT_SCREEN_ONLY'
        assert len(joint['probes']) == 160 and len(joint['selected_y65_fine_probes']) == 48
        joint_phase = joint['rocker_phase_witness']
        assert 9 < joint_phase['t1.00']['bounds']['max'][2] - joint_phase['t0.00']['bounds']['max'][2] < 12
        assert not joint['failures'] and joint['manufacturing_release'] is False
        assert joint['plane_comparison']['y65_promoted_to_selected_assembly'] is False
        assert joint['mount_report_sha256'] == evidence['rocker_pivot_mount_screen_sha256']
        assert joint['bridge_report_sha256'] == evidence['rocker_bridge_screen_sha256']
        assert sha256((ROOT/'output/electric-rocker-pivot-joint-screen/review.json').read_bytes()).hexdigest() == evidence['rocker_pivot_joint_screen_sha256']
        for travel in (0.25, 0.50, 0.75, 1.00):
            assert joint['probes'][f'y62-t{travel:.2f}-front-retainer-moving']['occupied'] is True
            assert joint['probes'][f'y65-t{travel:.2f}-front-retainer-moving']['occupied'] is False
        for plane in (62, 65):
            name = f'joint-y{plane}-mid.png'
            assert joint['images'][f'y{plane}']['sha256'] == sha256((PUBLIC/'rocker-joint'/name).read_bytes()).hexdigest()
        joint_doc = (PUBLIC/'electric-rocker-pivot-joint-screen.md').read_bytes()
        for name in (b'rocker-joint/review.json', b'rocker-joint/joint-y62-mid.png',
                     b'rocker-joint/joint-y65-mid.png'):
            assert name in joint_doc
        assert b'electric-rocker-pivot-joint-screen.md' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'electric-rocker-pivot-joint-screen.md' in (PUBLIC/'index.html').read_bytes()
        pin = json.loads((PUBLIC/'rocker-pin/review.json').read_text())
        assert pin['status'] == 'HCDG6_16_FRONT_HEAD_LAYOUT_CLEAR_FORK_FIT_OPEN'
        assert not pin['failures'] and pin['manufacturing_release'] is False
        assert pin['predecessor_joint_report_sha256'] == evidence['rocker_pivot_joint_screen_sha256']
        assert len(pin['coarse_probes']) == 30 and len(pin['fine_probes']) == 32
        assert len(pin['serviceability_screen']['probe_results']) == 15
        assert pin['fork_bore_issue']['qualified_bearing_or_finished_fork_hole_designed'] is False
        assert pin['serviceability_screen']['carriage_can_be_safely_parked_at_full_stroke_verified'] is False
        assert pin['serviceability_screen']['probe_results']['mount-tool-bridge-t0.00']['occupied'] is True
        assert pin['serviceability_screen']['probe_results']['mount-tool-bridge-t1.00']['occupied'] is False
        assert pin['image']['sha256'] == sha256((PUBLIC/'rocker-pin/front-head-rear-ring-mid.png').read_bytes()).hexdigest()
        assert sha256((ROOT/'output/electric-rocker-pin-retention-screen/review.json').read_bytes()).hexdigest() == evidence['rocker_pin_retention_screen_sha256']
        pin_doc = (PUBLIC/'electric-rocker-pin-retention-screen.md').read_bytes()
        for name in (b'rocker-pin/review.json', b'rocker-pin/front-head-rear-ring-mid.png'):
            assert name in pin_doc
        assert b'electric-rocker-pin-retention-screen.md' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'electric-rocker-pin-retention-screen.md' in joint_doc
        assert b'electric-rocker-pin-retention-screen.md' in (PUBLIC/'index.html').read_bytes()
        clamp = json.loads((PUBLIC/'rocker-clamp/review.json').read_text())
        assert clamp['status'] == 'SPLIT_CLAMP_FORK_STATIC_SCREEN_ONLY'
        assert len(clamp['static_clearance_probes']) == 110
        assert all(clamp['static_clearance_probes'][f'fasteners-bracket-t{t:.2f}']['occupied'] is False
                   for t in (0, .25, .5, .75, 1))
        assert len(clamp['service_axis']['probes']) == 50
        assert len(clamp['service_axis']['occupied_axes']) == 8
        assert clamp['service_axis']['driver_axes_clear_at_all_poses_nominal'] is True
        assert clamp['service_axis']['nut_wrench_axis_clear_at_all_poses_nominal'] is False
        assert clamp['bracket_mesh']['connected_components'] == 1
        assert clamp['bracket_mesh']['watertight'] is True
        assert clamp['bracket_mesh']['bounds']['min'][2] == -18
        assert clamp['drive_feasibility_report_sha256'] == evidence['electric_drive_feasibility_sha256']
        assert clamp['beam_load_scenario_only']['deepened_section_modulus_mm3'] == 60.5
        assert clamp['beam_load_scenario_only']['structural_release'] is False
        assert clamp['real_rocker_bore_and_bushing_included_in_screen'] is True
        assert clamp['rocker_bushing_petg_fit_verified'] is False
        assert 9 < clamp['through_bored_rocker_top_z_delta_mm'] < 12
        assert clamp['manufacturing_release'] is False
        assert clamp['selected_assembly_promoted'] is False
        assert not clamp['failures']
        assert clamp['predecessor_pin_report_sha256'] == evidence['rocker_pin_retention_screen_sha256']
        assert clamp['predecessor_joint_report_sha256'] == evidence['rocker_pivot_joint_screen_sha256']
        assert clamp['positive_controls']['raw-rocker-shaft-positive-control-t0.00']['occupied'] is True
        assert clamp['static_clearance_probes']['rocker-shaft-t0.00']['occupied'] is False
        assert clamp['bracket_mesh']['sha256'] == sha256((PUBLIC/'rocker-clamp/bracket.stl').read_bytes()).hexdigest()
        assert sha256((ROOT/'output/electric-rocker-clamped-fork-screen/review.json').read_bytes()).hexdigest() == evidence['rocker_clamped_fork_screen_sha256']
        for name, row in clamp['images'].items():
            assert row['sha256'] == sha256((PUBLIC/'rocker-clamp'/name).read_bytes()).hexdigest()
        clamp_doc = (PUBLIC/'electric-rocker-clamped-fork-screen.md').read_bytes()
        for name in (b'rocker-clamp/review.json', b'rocker-clamp/mid.png',
                     b'rocker-clamp/detail.png',
                     b'rocker-joint/electric-rocker-pivot-joint-screen.scad',
                     b'rocker-clamp/electric-rocker-clamped-fork-screen.scad'):
            assert name in clamp_doc
        assert b'electric-rocker-clamped-fork-screen.md' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'electric-rocker-clamped-fork-screen.md' in (PUBLIC/'index.html').read_bytes()
        crosshead = json.loads((PUBLIC/'output-crosshead/review.json').read_text())
        assert crosshead['status'] == 'OUTPUT_CROSSHEAD_GEOMETRY_SCREEN_ONLY'
        assert crosshead['pose_count'] == 21
        assert crosshead['clear_probe_count'] == 168
        assert crosshead['positive_control_count'] == 10
        assert crosshead['predecessor_sha256'] == {
            'side': evidence['side_switch_candidate_sha256'],
            'bridge': evidence['rocker_bridge_screen_sha256'],
            'fork': evidence['rocker_clamped_fork_screen_sha256']}
        assert crosshead['parameters_mm']['pin_has_dedicated_axial_retention'] is False
        assert crosshead['promoted_to_selected_parts'] is False
        assert crosshead['print_or_strength_release'] is False
        assert crosshead['physical_acceptance'] is False
        assert not crosshead['failures']
        assert all(not row.get('occupied') and not row.get('error')
                   for row in crosshead['clear_probes'].values())
        assert all(row.get('occupied') and not row.get('error')
                   for row in crosshead['positive_controls'].values())
        assert sha256((ROOT/'output/electric-output-crosshead-screen/review.json').read_bytes()).hexdigest() == evidence['output_crosshead_screen_sha256']
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in crosshead['source_sha256'].items())
        for name, row in crosshead['parts'].items():
            assert row['watertight'] is True and row['connected_components'] == 1
            assert sha256((PUBLIC/'output-crosshead'/f'{name}.stl').read_bytes()).hexdigest() == row['sha256']
        for name, row in crosshead['images'].items():
            assert sha256((PUBLIC/'output-crosshead'/f'{name}.png').read_bytes()).hexdigest() == row['sha256']
        crosshead_slice = json.loads((PUBLIC/'output-crosshead/slice-review.json').read_text())
        assert crosshead_slice['status'] == 'OUTPUT_CARRIAGE_SLICED_UNRELEASED'
        assert crosshead_slice['geometry_review_sha256'] == evidence['output_crosshead_screen_sha256']
        assert crosshead_slice['source_stl_sha256'] == crosshead['parts']['carriage']['sha256']
        assert crosshead_slice['native_warnings'] == []
        assert crosshead_slice['slot_axis_vertical_after_rotation'] is True
        assert crosshead_slice['support_extrusion_segments_crossing_slot_with_0p25mm_margin'] == 0
        assert crosshead_slice['printer_sent'] is False
        assert crosshead_slice['manufacturing_release'] is False
        assert crosshead_slice['physical_acceptance'] is False
        assert not crosshead_slice['failures']
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in crosshead_slice['source_sha256'].items())
        assert sha256((ROOT/'output/electric-output-crosshead-screen/slice-review.json').read_bytes()).hexdigest() == evidence['output_crosshead_slice_sha256']
        assembly = json.loads((PUBLIC/'output-crosshead/assembly-review.json').read_text())
        assert assembly['status'] == 'SERVICE_PATH_PARTIAL_AXIAL_INSERTION_BLOCKED'
        assert assembly['predecessor_sha256'] == {
            'output/electric-output-crosshead-screen/review.json': evidence['output_crosshead_screen_sha256'],
            'output/electric-end-switch-side-cap/review.json': evidence['side_switch_candidate_sha256'],
            'output/electric-rocker-clamped-fork-screen/review.json': evidence['rocker_clamped_fork_screen_sha256']}
        assert assembly['nominal_cap_removal_vs_new_crosshead_clear'] is True
        assert assembly['nominal_switch_tool_vs_new_crosshead_clear'] is True
        assert assembly['nominal_rocker_pin_axial_path_into_slot_clear_without_fork'] is True
        assert assembly['rocker_with_fixed_fork_axial_blocked_y_offset_mm'] == [2.5, 5, 7.5, 10]
        assert assembly['complete_rocker_assembly_path_proven'] is False
        assert assembly['manufacturing_release'] is False and assembly['physical_acceptance'] is False
        assert assembly['failures'] == []
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in assembly['source_sha256'].items())
        assert sha256((ROOT/'output/electric-output-crosshead-screen/assembly-review.json').read_bytes()).hexdigest() == evidence['output_crosshead_assembly_sha256']
        pin_load = json.loads((PUBLIC/'output-crosshead/pin-retention-load-screen.json').read_text())
        assert pin_load['status'] == 'OUTPUT_PIN_AXIAL_ENGAGEMENT_CONDITIONAL_LOAD_UNRELEASED'
        assert pin_load['source_sha256']['output/electric-output-crosshead-screen/review.json'] == evidence['output_crosshead_screen_sha256']
        assert pin_load['source_sha256']['output/electric-rocker-service-fork-screen/review.json'] == evidence['service_fork_screen_sha256']
        assert pin_load['axial_geometry_mm']['nominal_pin_slot_engagement'] == 8.5
        assert pin_load['axial_geometry_mm']['remaining_engagement_at_that_translation'] == 7
        assert pin_load['conditional_retention']['no_separate_output_pin_axial_clip_needed_if_fork_and_pivot_keep_rocker_between_its_inner_faces'] is True
        assert pin_load['conditional_retention']['actual_fork_spacing_pin_retention_bushing_fit_and_flex_verified'] is False
        assert pin_load['conditional_retention']['moving_slot_y_position_and_flex_verified'] is False
        assert pin_load['conditional_retention']['printed_pin_attachment_and_wear_verified'] is False
        assert pin_load['manufacturing_release'] is False
        assert pin_load['physical_acceptance'] is False
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in pin_load['source_sha256'].items())
        assert sha256((ROOT/'output/electric-output-crosshead-screen/pin-retention-load-screen.json').read_bytes()).hexdigest() == evidence['output_pin_load_sha256']
        assert b'output-crosshead/pin-retention-load-screen.json' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'output-crosshead/pin-retention-load-screen.json' in (PUBLIC/'electric-output-crosshead-screen.md').read_bytes()
        assert b'output-crosshead/assembly-review.json' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'output-crosshead/assembly-review.json' in (PUBLIC/'electric-output-crosshead-screen.md').read_bytes()
        slice_dir = PUBLIC/'output-crosshead/slices/carriage-x-plus-90-tree'
        assert sha256((slice_dir/'slice-review.3mf').read_bytes()).hexdigest() == crosshead_slice['slice_3mf_sha256']
        assert sha256((slice_dir/'plate-preview.png').read_bytes()).hexdigest() == crosshead_slice['preview_sha256']
        assert sha256((PUBLIC/'electric-output-crosshead-screen.md').read_bytes()).hexdigest() == evidence['output_crosshead_doc_sha256']
        assert b'electric-output-crosshead-screen.md' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'electric-output-crosshead-screen.md' in (PUBLIC/'index.html').read_bytes()
        assert b'output-crosshead/home.png' in (PUBLIC/'index.html').read_bytes()
        service_fork = json.loads((PUBLIC/'service-fork/review.json').read_text())
        assert service_fork['status'] == 'SERVICE_FORK_NOMINAL_ASSEMBLY_PATH_ONLY'
        assert service_fork['predecessor_sha256'] == {
            'output/electric-output-crosshead-screen/assembly-review.json': evidence['output_crosshead_assembly_sha256'],
            'output/electric-output-crosshead-screen/review.json': evidence['output_crosshead_screen_sha256'],
            'output/electric-rocker-clamped-fork-screen/review.json': evidence['rocker_clamped_fork_screen_sha256']}
        assert service_fork['static_probe_count'] == 105
        assert service_fork['assembly_probe_count'] == 264
        assert service_fork['positive_control_count'] == 2
        assert all(not row.get('occupied') and not row.get('error')
                   for row in service_fork['clear_probes'].values())
        assert all(row.get('occupied') and not row.get('error')
                   for row in service_fork['positive_controls'].values())
        assert service_fork['promoted_to_selected_assembly'] is False
        assert service_fork['manufacturing_release'] is False
        assert service_fork['physical_acceptance'] is False
        assert not service_fork['failures']
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in service_fork['source_sha256'].items())
        assert sha256((ROOT/'output/electric-rocker-service-fork-screen/review.json').read_bytes()).hexdigest() == evidence['service_fork_screen_sha256']
        for name, row in service_fork['parts'].items():
            assert row['watertight'] and row['connected_components'] == 1
            assert sha256((PUBLIC/'service-fork'/f'{name}.stl').read_bytes()).hexdigest() == row['sha256']
        for name, row in service_fork['images'].items():
            assert sha256((PUBLIC/'service-fork'/f'{name}.png').read_bytes()).hexdigest() == row['sha256']
        service_fork_slice = json.loads((PUBLIC/'service-fork/slice-review.json').read_text())
        assert service_fork_slice['status'] == 'SERVICE_FORK_SLICED_UNRELEASED'
        assert service_fork_slice['geometry_review_sha256'] == evidence['service_fork_screen_sha256']
        assert service_fork_slice['printer_sent'] is False
        assert service_fork_slice['manufacturing_release'] is False
        assert service_fork_slice['physical_acceptance'] is False
        assert service_fork_slice['failures'] == []
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in service_fork_slice['source_sha256'].items())
        assert sha256((ROOT/'output/electric-rocker-service-fork-screen/slice-review.json').read_bytes()).hexdigest() == evidence['service_fork_slice_sha256']
        service_fork_load = json.loads((PUBLIC/'service-fork/load-screen.json').read_text())
        assert service_fork_load['status'] == 'SERVICE_FORK_LOAD_PATH_UNRELEASED'
        assert service_fork_load['source_sha256']['output/electric-rocker-service-fork-screen/review.json'] == evidence['service_fork_screen_sha256']
        assert service_fork_load['source_sha256']['output/electric-rocker-service-fork-screen/slice-review.json'] == evidence['service_fork_slice_sha256']
        assert service_fork_load['joint_nominal_play']['first_shear_contact_determinable_from_nominal_cad'] is False
        assert service_fork_load['rear_joint_strength_verified'] is False
        assert service_fork_load['structural_release'] is False
        assert service_fork_load['manufacturing_release'] is False
        assert service_fork_load['physical_acceptance'] is False
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in service_fork_load['source_sha256'].items())
        assert sha256((ROOT/'output/electric-rocker-service-fork-screen/load-screen.json').read_bytes()).hexdigest() == evidence['service_fork_load_sha256']
        service_fork_orientation = json.loads((PUBLIC/'service-fork/orientation-screen.json').read_text())
        assert service_fork_orientation['status'] == 'ORIENTATION_COMPARISON_ONLY'
        assert len(service_fork_orientation['orientations']) == 12
        assert service_fork_orientation['source_sha256']['output/electric-rocker-service-fork-screen/review.json'] == evidence['service_fork_screen_sha256']
        assert service_fork_orientation['source_sha256']['output/electric-rocker-service-fork-screen/slice-review.json'] == evidence['service_fork_slice_sha256']
        x40 = service_fork_orientation['orientations']['x40']
        assert x40['status'] == 'OFFLINE_SLICE_ONLY'
        assert x40['source_stl_sha256'] == service_fork['parts']['base']['sha256']
        assert x40['native_warnings'] == []
        assert x40['archive_integrity_pass'] is True
        assert all(v == 0 for v in x40['sampled_support_extrusion_segments_in_void_cores'].values())
        x40_preview = PUBLIC/'service-fork/orientation-screen/base-x-plus-40-tree/plate-preview.png'
        assert sha256(x40_preview.read_bytes()).hexdigest() == x40['preview_sha256']
        assert service_fork_orientation['orientations']['x90']['slice_3mf_sha256'] == service_fork_slice['orientations']['base-x-plus-90-tree']['slice_3mf_sha256']
        assert service_fork_orientation['best_orientation_selected'] is False
        assert service_fork_orientation['manufacturing_release'] is False
        assert service_fork_orientation['physical_acceptance'] is False
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in service_fork_orientation['source_sha256'].items())
        assert sha256((ROOT/'output/electric-rocker-service-fork-screen/orientation-screen.json').read_bytes()).hexdigest() == evidence['service_fork_orientation_sha256']
        for label, part in (('base-x-plus-90-tree', 'base'),
                            ('rear-x-minus-90-tree', 'rear')):
            row = service_fork_slice['orientations'][label]
            folder = PUBLIC/'service-fork/slices'/label
            assert row['status'] == 'SLICED_UNRELEASED'
            assert row['source_stl_sha256'] == service_fork['parts'][part]['sha256']
            assert row['native_warnings'] == []
            assert row['archive_integrity_pass'] is True
            assert all(row['critical_pockets_open_upward_after_3mf_rotation'].values())
            assert all(v == 0 for v in row['support_extrusion_segments_crossing_critical_feature_with_0p25mm_margin'].values())
            assert sha256((folder/'slice-review.3mf').read_bytes()).hexdigest() == row['slice_3mf_sha256']
            assert sha256((folder/'plate-preview.png').read_bytes()).hexdigest() == row['preview_sha256']
        assert sha256((PUBLIC/'electric-rocker-service-fork-screen.md').read_bytes()).hexdigest() == evidence['service_fork_doc_sha256']
        assert b'electric-rocker-service-fork-screen.md' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'electric-rocker-service-fork-screen.md' in (PUBLIC/'index.html').read_bytes()
        assert b'service-fork/rear-seated.png' in (PUBLIC/'electric-rocker-service-fork-screen.md').read_bytes()
        assert b'service-fork/load-screen.json' in (PUBLIC/'electric-rocker-service-fork-screen.md').read_bytes()
        assert b'service-fork/load-screen.json' in (PUBLIC/'electric-status.md').read_bytes()
        assert b'service-fork/orientation-screen.json' in (PUBLIC/'electric-rocker-service-fork-screen.md').read_bytes()
        assert b'service-fork/orientation-screen.json' in (PUBLIC/'electric-status.md').read_bytes()
        reinforcement = json.loads((PUBLIC/'service-fork-reinforcement/review.json').read_text())
        assert reinforcement['status'] == 'REINFORCED_BEAM_GEOMETRY_SCREEN_ONLY'
        assert reinforcement['original_review_sha256'] == evidence['service_fork_screen_sha256']
        assert reinforcement['original_load_review_sha256'] == evidence['service_fork_load_sha256']
        assert len(reinforcement['probes']) == 27 and not reinforcement['failures']
        assert reinforcement['moving_phase_control']['min_max_z_shift_mm'] == [20.0, 20.0]
        assert all(row['occupied'] == name.startswith('added-positive-control')
                   for name, row in reinforcement['probes'].items())
        assert reinforcement['structural_release'] is False
        assert reinforcement['manufacturing_release'] is False
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in reinforcement['source_sha256'].items())
        assert sha256((PUBLIC/'service-fork-reinforcement/review.json').read_bytes()).hexdigest() == evidence['service_fork_reinforcement_sha256']
        root_section = json.loads((PUBLIC/'service-fork-reinforcement/root-section-screen.json').read_text())
        assert root_section['status'] == 'ROOT_SECTION_UNCHANGED_REINFORCEMENT_UNRELEASED'
        assert all(root_section['checks'].values())
        assert root_section['structural_release'] is False
        assert root_section['manufacturing_release'] is False
        assert sha256((PUBLIC/'service-fork-reinforcement/root-section-screen.json').read_bytes()).hexdigest() == evidence['service_fork_root_section_sha256']
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in root_section['source_sha256'].items())
        assert sha256((PUBLIC/'service-fork-reinforcement/base-reinforced-screen.stl').read_bytes()).hexdigest() == reinforcement['reinforced_base']['sha256']
        assert sha256((PUBLIC/'service-fork-reinforcement/beam-extension-context.png').read_bytes()).hexdigest() == reinforcement['context_image']['sha256']
        assert b'electric-rocker-service-fork-reinforcement-screen.md' in (PUBLIC/'electric-rocker-service-fork-screen.md').read_bytes()
        reinforcement_doc = (PUBLIC/'electric-rocker-service-fork-reinforcement-screen.md').read_bytes()
        assert sha256(reinforcement_doc).hexdigest() == evidence['service_fork_reinforcement_doc_sha256']
        assert b'service-fork-reinforcement/beam-extension-context.png' in reinforcement_doc
        assert b'service-fork-reinforcement/root-section-screen.json' in reinforcement_doc
        assert b'service-fork-reinforcement/root-section-screen.py' in reinforcement_doc
        assert b'service-fork-reinforcement/section-requirements.txt' in reinforcement_doc
        assert sha256((PUBLIC/'service-fork-reinforcement/root-section-screen.py').read_bytes()).hexdigest() == root_section['source_sha256']['analysis/service_fork_root_section_screen.py']
        assert sha256((PUBLIC/'service-fork-reinforcement/section-requirements.txt').read_bytes()).hexdigest() == root_section['source_sha256']['analysis/service_fork_section_requirements.txt']
        assert b'service-fork-reinforcement/candidate.scad' in reinforcement_doc
        root_web = json.loads((PUBLIC/'service-fork-root-web/review.json').read_text())
        assert root_web['status'] == 'ROOT_WEB_NOMINAL_GEOMETRY_ONLY_UNRELEASED'
        assert root_web['predecessor_reinforcement_sha256'] == evidence['service_fork_reinforcement_sha256']
        assert root_web['predecessor_root_section_sha256'] == evidence['service_fork_root_section_sha256']
        assert len(root_web['probes']) == 131 and not root_web['failures']
        assert all(row['occupied'] == (name in ('positive', 'margin-positive'))
                   for name, row in root_web['probes'].items())
        assert root_web['added_only']['bounds_mm']['min'][0] == 8.0
        assert root_web['structural_release'] is False
        assert root_web['manufacturing_release'] is False
        assert root_web['selected_for_printing'] is False
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in root_web['source_sha256'].items())
        assert sha256((PUBLIC/'service-fork-root-web/review.json').read_bytes()).hexdigest() == evidence['service_fork_root_web_sha256']
        for name, part in (('base-root-web-screen.stl', root_web['base']),
                           ('added-root-web-screen.stl', root_web['added_only']),
                           ('root-web-context.png', root_web['context_image'])):
            assert sha256((PUBLIC/'service-fork-root-web'/name).read_bytes()).hexdigest() == part['sha256']
        assert sha256((PUBLIC/'service-fork-root-web/candidate.scad').read_bytes()).hexdigest() == root_web['source_sha256']['cad/electric-rocker-root-gusset-screen.scad']
        root_web_section = json.loads((PUBLIC/'service-fork-root-web/root-web-section.json').read_text())
        assert root_web_section['status'] == 'ROOT_WEB_LOBE_AREA_GAIN_ONLY_UNRELEASED'
        assert all(root_web_section['checks'].values())
        assert root_web_section['root_lower_lobe_area_ratio'] > 3
        assert root_web_section['three_dimensional_stress_or_fatigue_verified'] is False
        assert root_web_section['structural_release'] is False
        assert root_web_section['manufacturing_release'] is False
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in root_web_section['source_sha256'].items())
        assert sha256((PUBLIC/'service-fork-root-web/root-web-section.json').read_bytes()).hexdigest() == evidence['service_fork_root_web_section_sha256']
        assert sha256((PUBLIC/'service-fork-root-web/root-web-section.py').read_bytes()).hexdigest() == root_web_section['source_sha256']['analysis/service_fork_root_web_section.py']
        root_web_orientation = json.loads((PUBLIC/'service-fork-root-web/orientation-screen.json').read_text())
        assert root_web_orientation['status'] == 'ROOT_WEB_ORIENTATION_SCREEN_ONLY_UNRELEASED'
        assert len(root_web_orientation['orientations']) == 20
        assert all(row['status'] == 'OFFLINE_SLICE_ONLY'
                   and row['source_stl_sha256'] == root_web['base']['sha256']
                   and not row['native_warnings'] and row['archive_integrity_pass']
                   for row in root_web_orientation['orientations'].values())
        for name in ('x40', 'x55', 'x90'):
            row = root_web_orientation['orientations'][name]
            assert not any((*row['sampled_support_extrusion_segments_in_void_cores'].values(),
                            *row['shell_anchor_support_segments_in_void_cores'].values(),
                            *row['support_extrusion_segments_in_critical_feature_boxes'].values()))
        assert root_web_orientation['orientations']['x0']['sampled_support_extrusion_segments_in_void_cores']['nut_lower'] > 0
        assert root_web_orientation['best_orientation_selected'] is False
        assert root_web_orientation['manufacturing_release'] is False
        assert root_web_orientation['physical_acceptance'] is False
        assert all(sha256((ROOT/name).read_bytes()).hexdigest() == digest
                   for name, digest in root_web_orientation['source_sha256'].items())
        assert sha256((PUBLIC/'service-fork-root-web/orientation-screen.json').read_bytes()).hexdigest() == evidence['service_fork_root_web_orientation_sha256']
        assert sha256((PUBLIC/'service-fork-root-web/orientation-screen.py').read_bytes()).hexdigest() == root_web_orientation['source_sha256']['scripts/screen_electric_rocker_root_gusset_orientation.py']
        root_web_x55 = PUBLIC/'service-fork-root-web/slice-screen/orientation-screen/base-x-plus-55-tree'
        for name, key in (('slice-review.3mf', 'slice_3mf_sha256'),
                          ('plate-preview.png', 'preview_sha256')):
            assert sha256((root_web_x55/name).read_bytes()).hexdigest() == root_web_orientation['orientations']['x55'][key]
        no_support_x55 = root_web_orientation['no_support_x55']
        assert no_support_x55['status'] == 'NO_SUPPORT_FLOATING_REGIONS_WARNING_UNRELEASED'
        assert any('floating regions' in warning for warning in no_support_x55['native_warnings'])
        assert no_support_x55['manufacturing_release'] is False
        assert sha256((PUBLIC/'service-fork-root-web/slice-screen/base-x-plus-55-no-support/result.json').read_bytes()).hexdigest() == no_support_x55['native_result_sha256']
        assert b'electric-rocker-root-gusset-screen.md' in reinforcement_doc
        assert b'electric-rocker-root-gusset-screen.md' in (PUBLIC/'electric-status.md').read_bytes()
        root_web_doc = (PUBLIC/'electric-rocker-root-gusset-screen.md').read_bytes()
        assert sha256(root_web_doc).hexdigest() == evidence['service_fork_root_web_doc_sha256']
        assert b'service-fork-root-web/root-web-context.png' in root_web_doc
        assert b'service-fork-root-web/root-web-section.json' in root_web_doc
        assert b'service-fork-root-web/orientation-screen.json' in root_web_doc
        assert b'service-fork-root-web/orientation-screen.py' in root_web_doc
        assert b'service-fork-root-web/slice-screen/orientation-screen/base-x-plus-55-tree/plate-preview.png' in root_web_doc
        assert b'service-fork-root-web/slice-screen/base-x-plus-55-no-support/result.json' in root_web_doc
        assert b'service-fork-root-web/candidate.scad' in root_web_doc
    names = {'index.html', 'models.html', 'app.js', 'manifest.json',
             'evidence.json', 'printed-parts.csv'}
    if (PUBLIC/'revision-status.json').exists():
        revision=json.loads((PUBLIC/'revision-status.json').read_text())
        assert revision['printed_instances']==evidence['printed_instances']
        names.add('revision-status.json')
    names.update(row['file'] for row in evidence['assets'])
    if (PUBLIC/'motion-manifest.json').exists() and not electric:
        motion=json.loads((PUBLIC/'motion-manifest.json').read_text())
        names.update(['motion-manifest.json','feeder-motion.html','feeder-motion.mjs','feeder-motion-kinematics.mjs'])
        for part in motion['parts']:
            assert sha256((PUBLIC/part['file']).read_bytes()).hexdigest()==part['sha256']
            names.add(part['file'])
        for path,expected in motion['web_sources'].items():
            assert sha256((PUBLIC/Path(path).name).read_bytes()).hexdigest()==expected
        for part in motion.get('assembly_catalog',[]):
            assert sha256((PUBLIC/part['file']).read_bytes()).hexdigest()==part['sha256']
            names.add(part['file'])
            for piece in part.get('subparts',[]):
                assert sha256((PUBLIC/piece['file']).read_bytes()).hexdigest()==piece['sha256']
                names.add(piece['file'])
    elif electric:
        # The former motion model is retained for history, with updated on-page
        # labels. Its old source-hash contract is not the current selection.
        names.update(['feeder-motion.html', 'feeder-motion.mjs', 'motion-manifest.json'])
    rows = []
    for name in sorted(names):
        expected = (PUBLIC / name).read_bytes()
        actual, headers = fetch(name)
        assert actual == expected, name
        assert 'no-store' in headers.get('Cache-Control', ''), name + ' is cacheable'
        rows.append({'file': name, 'bytes': len(actual), 'sha256': sha256(actual).hexdigest(),
                     'cache_control': headers.get('Cache-Control')})
    listener = subprocess.check_output(
        ['lsof', '-nP', '-iTCP:8877', '-sTCP:LISTEN'], text=True)
    pid = listener.splitlines()[1].split()[1]
    cwd = subprocess.check_output(['lsof', '-a', '-p', pid, '-d', 'cwd', '-Fn'], text=True)
    assert f'n{PUBLIC}\n' in cwd, cwd
    result = {'status': 'PUBLISHED_LAN_BYTES_AND_API_MATCH',
              'verified_at_utc': datetime.now(timezone.utc).isoformat(),
              'base_url': base,
              'verified_from': 'same Mac via LAN IPv4; second device untested',
              'listener': listener, 'process_cwd': cwd,
              'part_count': api['count'],
              'printed_instances': evidence['printed_instances'],
              'groups': api['groups'], 'files': rows,
              'manufacturing_release': False, 'physical_acceptance': False}
    target = ROOT / 'output/preview-service/lan-verification.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'Verified {len(rows)} files and {api["count"]} entries at {base}')


if __name__ == '__main__':
    main()
