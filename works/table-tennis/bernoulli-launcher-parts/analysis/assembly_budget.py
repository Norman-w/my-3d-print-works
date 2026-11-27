#!/usr/bin/env python3
"""Cross-check cam free play against the independent gate-position assumption.

This intentionally fails when a nominal CAD study cannot use the current gate
geometry report's error envelope. Unknown friction and deflection are not zero.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import sys

from gate_geometry import read_parameters

ROOT = Path(__file__).resolve().parents[1]


def literal(source, key):
    values = re.findall(rf'^\s*{re.escape(key)}\s*=\s*([-+0-9.]+)\s*;', source, re.M)
    if len(values) != 1:
        raise ValueError(f'Expected one literal {key}')
    return float(values[0])


def main():
    p, raw = read_parameters(ROOT / 'cad/parameters.scad')
    cam_path = ROOT / 'cad/cam-study.scad'
    cam_raw = cam_path.read_bytes()
    cam_source = cam_raw.decode()
    pin_d = literal(cam_source, 'cam_pin_d')
    # These expressions are the current CAD contract. Refuse silently drifting
    # formula changes; parsing arbitrary SCAD as Python would not be appropriate.
    compact = re.sub(r'\s+', '', cam_source)
    if 'cam_slot_d=cam_pin_d+2*radial_print_clearance;' not in compact:
        raise ValueError('Cam slot formula changed; review this independent budget model')
    shoulder_bore = ('cam_y_cylinder([cam_follower_offset,0],cam_pin_shoulder_start_y,'
                     'cam_carrier_width/2-cam_pin_shoulder_start_y+cam_eps,'
                     'cam_pin_d+2*radial_print_clearance);')
    if shoulder_bore not in compact:
        raise ValueError('Stepped shoulder-bore geometry changed; review the CAD load path')
    half_slot_gap = p['radial_print_clearance']
    carrier_hole_half_gap = p['radial_print_clearance']
    moving_length = p['cam_stroke'] * (1-p['gate_overlap_fraction']) / 2
    slope = (p['finger_open_center_r']-p['finger_closed_center_r']) / moving_length
    slot_radial_free_play = half_slot_gap * math.sqrt(1+slope*slope)
    aligned_baseline = slot_radial_free_play + carrier_hole_half_gap
    support_path = ROOT / 'cad/feeder-supports.scad'
    support_raw = support_path.read_bytes()
    support_source = support_raw.decode()
    radial_gap = literal(support_source, 'support_radial_clearance')
    axial_gap = literal(support_source, 'support_axial_clearance')
    guide_z0 = literal(support_source, 'support_guide_z0')
    guide_z1 = literal(support_source, 'support_guide_z1')
    guide_length = guide_z1-guide_z0
    # A rigid tongue can contact opposite sides at its guide endpoints.
    # Extrapolate the resulting lateral offset to each fixed follower station.
    follower_stations = [0, -p['gate_spacing']]
    overhang = max(max(guide_z0-z,z-guide_z1,0) for z in follower_stations)
    carriage_lateral_half_play = axial_gap*(1+2*overhang/guide_length)
    # This subtotal deliberately leaves angular radial-slider coupling OPEN.
    nominal_subtotal = aligned_baseline + carriage_lateral_half_play + slope*radial_gap
    adopted = p['gate_position_budget']
    usable = nominal_subtotal <= adopted
    counterexample_path = ROOT/'output/analysis/feeder-tolerance.json'
    counterexample_current = False
    if counterexample_path.exists():
        witness_report = json.loads(counterexample_path.read_text())
        witness_sources = witness_report.get('source_sha256',{})
        counterexample_current = (
            witness_report.get('status') == 'RIGID_CSG_COUNTEREXAMPLE_VERIFIED'
            and witness_report.get('whole_assembly_counterexample_verified') is True
            and bool(witness_sources)
            and all((ROOT/name).exists() and
                    hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest
                    for name,digest in witness_sources.items()))
    report = {
        'analysis_kind': 'nominal_cam_to_gate_error_budget_integration',
        'source_sha256': {
            'cad/parameters.scad': hashlib.sha256(raw).hexdigest(),
            'cad/cam-study.scad': hashlib.sha256(cam_raw).hexdigest(),
            'cad/feeder-supports.scad': hashlib.sha256(support_raw).hexdigest(),
        },
        'status': 'PARTIAL_BUDGET_FITS_UNKNOWNS_OPEN' if usable else 'FAIL_PARTIAL_BUDGET_EXCEEDS_GATE_ASSUMPTION',
        'units': 'mm unless dimensionless',
        'nominal_pin_d': pin_d,
        'nominal_slot_width': pin_d+2*half_slot_gap,
        'nominal_carrier_pin_hole_d': pin_d+2*carrier_hole_half_gap,
        'cam_slope_dr_du': slope,
        'slot_normal_half_gap': half_slot_gap,
        'slot_radial_half_play_on_linear_ramp': slot_radial_free_play,
        'carrier_hole_radial_half_play': carrier_hole_half_gap,
        'conservative_aligned_baseline_radial_half_play': aligned_baseline,
        'axial_carriage_guide_length': guide_length,
        'follower_max_overhang_from_axial_guide': overhang,
        'axial_carriage_lateral_half_play_at_follower': carriage_lateral_half_play,
        'radial_slider_axial_translation_coupled_through_cam_slope': slope*radial_gap,
        'conservative_partial_radial_half_play': nominal_subtotal,
        'gate_report_assumed_finger_radial_error_budget': adopted,
        'budget_shortfall_before_other_errors': max(0, nominal_subtotal-adopted),
        'assumptions': [
            'Nominal rigid circular follower pin inside the CAD through-slot, with local linear ramp and fixed axial station.',
            'The shoulder screw seats on a carrier step; bore clearance remains an unknown installed radial offset even after tightening.',
            'Worst aligned clearances are combined as a conservative independent bound, not an observed motion.',
            'Slot projection is normal half-clearance times sqrt(1+slope**2); no dynamic or contact-force simulation.',
            'Axial tongue lateral play is extrapolated from the two ends of its finite fixed guide to the follower station.',
            'This is an intentionally incomplete upper-bound subtotal, not a complete tolerance simulation or a measured error.',
        ],
        'additional_terms_not_measured_or_designed': [
            'printed profile and pin-bore position/shape error',
            'fixed radial-guide angular play, follower-tip axial mismatch and resulting cam coupling',
            'axial-carriage three-dimensional twist beyond the in-plane bound above',
            'cap size/shape error, load-dependent deflection and wear',
        ],
        'consequence': 'Nominal empty CAD intersections do not establish the actual-position gate invariant. The gate geometry result cannot certify this cam assembly with a smaller assumed error budget.',
        'physical_acceptance': 'OPEN',
    }
    report['full_gate_position_assumption'] = (
        'CONTRADICTED_BY_CURRENT_NOMINAL_CAD_WITNESS' if counterexample_current else 'UNPROVEN')
    if counterexample_current:
        report['status'] = 'FAIL_ASSUMED_GATE_BUDGET_CURRENT_CSG_COUNTEREXAMPLE'
        report['source_sha256']['output/analysis/feeder-tolerance.json'] = hashlib.sha256(
            counterexample_path.read_bytes()).hexdigest()
        report['consequence'] = ('The partial subtotal fits, but a separately verified current-CAD '
            'rigid configuration exceeds the assumed finger-position budget. Do not use this '
            'subtotal as acceptance or increase the budget merely to hide the counterexample.')
    out = ROOT / 'output/analysis/assembly-budget.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(report['status'])
    print(f'Partial nominal half-play: {nominal_subtotal:.6f} mm; adopted budget: {adopted:.6f} mm')
    print(out)
    return 0 if usable and not counterexample_current else 1


if __name__ == '__main__':
    sys.exit(main())
