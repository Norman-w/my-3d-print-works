#!/usr/bin/env python3
"""Conditional robust stop-setting domain. No CAD mutation or physical acceptance."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'output/current-assembly-budget/report.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number')
    return float(value)


def interval(value, label):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f'{label} requires two endpoints')
    lo, hi = [finite(x, label) for x in value]
    if lo > hi:
        raise ValueError(f'{label} endpoints are reversed')
    return lo, hi


def solve(data, polygon_delay):
    # All quantities share the real released-output zero. Missing bounds are errors.
    f = finite(data['functional_output_upper_mm'], 'functional_output_upper_mm')
    h = finite(data['earliest_hard_stop_mm'], 'earliest_hard_stop_mm')
    l0, l1 = interval(data['net_loss_mm'], 'net_loss_mm')
    e0, e1 = interval(data['other_input_stop_error_mm'], 'other_input_stop_error_mm')
    if f < 0 or h <= 0:
        raise ValueError('output bounds must describe a nonnegative work stroke')
    # Actual takeup = C + nominal polygon delay + residual stop error.
    # Nominal polygon delay lies in [0, polygon_delay] for C in [16,22].
    raw_lo = f + l1 - e0
    raw_hi = h + l0 - e1 - polygon_delay
    # Restrict actual input/output to the existing0..20 system review extent.
    # The local16..22 formula does not prove whole-machine extended travel.
    input_lo = -e0
    input_hi = 20.0 - e1 - polygon_delay
    output_hi = 20.0 + l0 - e1 - polygon_delay
    lo = max(16.0, raw_lo, input_lo)
    hi = min(22.0, raw_hi, input_hi, output_hi)
    feasible = hi > lo
    result = {
        'scope': 'Sufficient robust box domain; input bounds are declarations, not verified manufacturing capabilities.',
        'functional_output_upper_mm': f,
        'earliest_hard_stop_mm': h,
        'net_loss_mm': [l0, l1],
        'other_input_stop_error_mm': [e0, e1],
        'nominal_polygon_delay_mm': [0.0, polygon_delay],
        'strict_unclipped_setting_interval_mm': [raw_lo, raw_hi],
        'current_input_domain_setting_limits_mm': [input_lo, input_hi],
        'current_output_domain_setting_upper_mm': output_hi,
        'current_system_domain_scope': 'Restricts input/output to the existing0..20 nominal review extent; no continuous or decoupled two-axis clearance proof.',
        'setting_domain_intersection_mm': [lo, hi],
        'robust_box_interval_nonempty': feasible,
        'unclipped_width_mm': raw_hi - raw_lo,
        'physical_setting_authorized': False,
    }
    if feasible:
        c = (lo + hi) / 2
        u_min = c + e0 - l1
        u_max = c + polygon_delay + e1 - l0
        result.update({
            'conditional_midpoint_mm': c,
            'conditional_input_range_mm': [c + e0, c + polygon_delay + e1],
            'conditional_output_range_mm': [u_min, u_max],
            'release_margin_mm': u_min - f,
            'hard_stop_margin_mm': h - u_max,
        })
        assert u_min > f and u_max < h
        assert 0 < c + e0 <= c + polygon_delay + e1 < 20
        assert 0 <= u_min <= u_max < 20
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bounds', type=Path, help='Explicit externally justified bounds; no defaults for missing values')
    args = parser.parse_args()
    prior = json.loads(SOURCE.read_text())
    source_hashes = prior['source_sha256']
    for name, digest in source_hashes.items():
        p = Path(name)
        p = p if p.is_absolute() else ROOT / p
        if sha(p) != digest:
            raise ValueError(f'Stale assembly budget source: {name}')
    stop = prior['stroke_and_stops']
    f = stop['functional_window_Bx1_mm'][0]
    p = stop['input_stop_circular_vs_polygon']['additional_contact_delay_u_upper_mm']
    if args.bounds:
        print(json.dumps(solve(json.loads(args.bounds.read_text()), p), ensure_ascii=False, indent=2))
        return

    # Synthetic controls demonstrate strict boundaries; none is a measured installation.
    base = {'functional_output_upper_mm': f, 'earliest_hard_stop_mm': 20,
            'net_loss_mm': [0, 0], 'other_input_stop_error_mm': [0, 0]}
    ideal = solve(base, p)
    loss_width_limit = 20 - f - p
    equality = solve({**base, 'net_loss_mm': [0, loss_width_limit + 1e-12]}, p)
    excess = solve({**base, 'net_loss_mm': [0, loss_width_limit + .1]}, p)
    shift = solve({**base, 'net_loss_mm': [.3, .3]}, p)
    large_bias = solve({**base, 'net_loss_mm': [2, 2]}, p)
    drift = solve({**base, 'other_input_stop_error_mm': [-.1, .1]}, p)
    assert not equality['robust_box_interval_nonempty']
    assert not excess['robust_box_interval_nonempty']
    assert abs(shift['strict_unclipped_setting_interval_mm'][0] - ideal['strict_unclipped_setting_interval_mm'][0] - .3) < 1e-12
    assert abs(shift['unclipped_width_mm'] - ideal['unclipped_width_mm']) < 1e-12
    assert not large_bias['robust_box_interval_nonempty']
    assert abs(drift['unclipped_width_mm'] - ideal['unclipped_width_mm'] + .2) < 1e-12
    # Existing ideal20 default cannot provide positive clearance even with zero losses.
    assert 20 + p >= base['earliest_hard_stop_mm']
    rejected = []
    for label, invalid in [('missing loss', {k:v for k,v in base.items() if k != 'net_loss_mm'}),
                           ('reversed range', {**base, 'net_loss_mm': [1, 0]}),
                           ('nan', {**base, 'earliest_hard_stop_mm': float('nan')})]:
        try:
            solve(invalid, p)
        except (KeyError, ValueError):
            rejected.append(label)
        else:
            raise AssertionError(label)
    result = {
        'status': 'PARAMETRIC_STOP_DOMAIN_COMPLETE_ACTUAL_BOUNDS_OPEN',
        'review_script_sha256': sha(Path(__file__).resolve()),
        'source_sha256': {'output/current-assembly-budget/report.json': sha(SOURCE), **source_hashes},
        'existing_source_identities_verified': len(source_hashes),
        'definitions': {
            'C': 'nominal circular-equivalent input setting, within16..22 mm; NOT permitted output overtravel',
            'U': 'actual full-pull input takeup C+b+e',
            'b': 'nominal72-gon delay in[0,p], counted only here',
            'e': 'all remaining stop setting/contact/lock/loaded errors expressed as equivalent takeup; no duplicate b',
            'ell': 'actual input takeup minus actual output displacement; full-pull lost motion and zero difference, no duplicate stop error',
            'F': 'guaranteed sufficient open threshold, expressed from actual output released zero, with gate pose/shape errors already included',
            'H': 'earliest output hard stop from same actual released zero',
        },
        'derivation': [
            'u_out = C+b+e-ell',
            'min(u_out) >= C+e_min-ell_max; max(u_out) <= C+p+e_max-ell_min',
            'C > F+ell_max-e_min AND C < H+ell_min-e_max-p',
            '(ell_max-ell_min)+(e_max-e_min)+p < H-F is required for this unclipped robust box interval',
            'Intersect with C in[16,22]; equality provides no positive margin',
            'Also require C+e_min>0, C+p+e_max<20 and C+p+e_max-ell_min<20, retaining the current input/output review extent',
        ],
        'correlation_scope': 'The box may be conservative. A failed sufficient box is not an attainable collision witness. Joint-state bounds can replace F,H and losses when proved.',
        'endpoint_slot_gate': 'This scalar stroke test does not replace the separate0.239165 mm pin/slot endpoint-fit condition; F/H must come from a domain that maintains positive cam constraint.',
        'nominal_example_NOT_installation': ideal,
        'synthetic_controls': {'boundary_roundoff_guard_mm': 1e-12, 'equality_or_beyond_rejected': equality,
            'excess_loss_rejected': excess, 'constant_loss_shift_before_domain_clipping': shift,
            'constant2mm_loss_exceeds_current_input_domain': large_bias,
            'symmetric_stop_error': drift, 'invalid_inputs_rejected': rejected,
            'default20_has_no_positive_clearance': True},
        'actual_bound_inputs': {'functional_output_upper_mm': None, 'earliest_hard_stop_mm': None,
            'net_loss_mm': None, 'other_input_stop_error_mm': None},
        'actual_joint_domain_certified': False,
        'manufacturing_release': False, 'physical_acceptance': False, 'sent_to_printer': False,
    }
    for name, digest in result['source_sha256'].items():
        path = Path(name)
        assert sha(path if path.is_absolute() else ROOT/path) == digest, name
    (OUT/'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'conditional_example': ideal,
                      'missing_actual_bounds': list(result['actual_bound_inputs'])}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
