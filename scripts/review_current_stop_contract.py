#!/usr/bin/env python3
"""Current conditional stop budget; no CAD mutation or physical authorization.

Run with bundled FreeCAD Python (mpmath interval arithmetic). Frozen historical
reports are inputs, never overwritten. --bounds consumes explicitly supplied
external bounds and still does not certify those declarations.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from mpmath import iv

ROOT = Path(__file__).resolve().parents[1]
GATE = 'output/current-joint-tolerance/gate-ball-joint-review/report.json'
GATE_SHA = '4e47c6a6b8ac09c1a4220517e877c45783be4115e39f0065c8ab2821d6ab8205'
CURRENT = {
    'cad/cable-trigger-input.scad': 'cf2dc90ecea43e0bb5bf3b6fe68f9cf7adb8d47145b4b15577e5dd40f1679d8d',
    'cad/cable-housing-route.scad': 'b5b335abe0b6fa4790c1331ad849c36827c2ef39711eaaf60e655ebd0d82cfaa',
    'cad/cable-scene-export.scad': 'f13b272bed1b9f0928d75f0897615c898d85ba1b986a73872cce2c736be0b42b',
}
D = Decimal


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError('Expected a declared finite number')
    v = D(str(value))
    if not v.is_finite():
        raise ValueError('Non-finite bound')
    return v


def interval(value):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError('Expected two interval endpoints')
    lo, hi = map(number, value)
    if lo > hi:
        raise ValueError('Reversed interval')
    return lo, hi


def solve(data, p):
    f = number(data['functional_output_upper_mm'])
    h = number(data['earliest_hard_stop_mm'])
    l0, l1 = interval(data['net_loss_mm'])
    e0, e1 = interval(data['other_input_stop_error_mm'])
    if f < 0 or h <= 0:
        raise ValueError('Invalid output domain')
    lo = max(D(16), f+l1-e0, -e0)
    hi = min(D(22), h+l0-e1-p, D(20)-e1-p, D(20)+l0-e1-p)
    result = {
        'declared_bounds': data,
        'strict_setting_interval_mm': [lo, hi],
        'interval_width_mm': hi-lo,
        'strict_interval_nonempty': hi > lo,
        'nominal_polygon_delay_upper_mm': p,
        'physical_setting_authorized': False,
    }
    if hi > lo:
        c = (lo+hi)/2
        result.update(conditional_midpoint_mm=c,
                      conditional_output_interval_mm=[c+e0-l1, c+p+e1-l0],
                      release_margin_mm=c+e0-l1-f,
                      hard_stop_margin_mm=h-(c+p+e1-l0))
    return result


def endpoint_fraction(raw):
    sign, mantissa, exponent, _ = raw
    numerator = int(-mantissa if sign else mantissa)
    return Fraction(numerator * 2**exponent) if exponent >= 0 else Fraction(numerator, 2**(-exponent))


def rounded_endpoint(value, upper, places=12):
    q = endpoint_fraction(value._mpi_[1 if upper else 0])
    with localcontext() as ctx:
        ctx.prec = 90
        return (D(q.numerator)/D(q.denominator)).quantize(
            D(1).scaleb(-places), rounding=ROUND_CEILING if upper else ROUND_FLOOR)


def local_delay():
    iv.dps = 60

    def takeup(angle_degrees):
        a = iv.mpf(str(angle_degrees))*iv.pi/180
        x, y = 24+60*iv.sin(a), 60*iv.cos(a)
        tangent = iv.sqrt(x*x+y*y-3600)
        phi = iv.atan2(x, y)-iv.atan2(tangent, iv.mpf(60))
        return 60*phi+tangent-24

    def angle_enclosure(u):
        target = Fraction(str(u))
        lo, hi = D(0), D(30)
        # The direct geometry has 0<=phi<=theta on this branch, so
        # dU/dtheta=60*cos(theta-phi)>=60*cos(30deg)>0.
        assert endpoint_fraction(takeup(hi)._mpi_[0]) > target
        for _ in range(65):
            mid = (lo+hi)/2
            value = takeup(mid)
            low, high = map(endpoint_fraction, value._mpi_)
            if high < target:
                lo = mid
            elif low > target:
                hi = mid
            else:
                break
        return iv.mpf([str(lo), str(hi)])

    a0, a1 = angle_enclosure(16), angle_enclosure('22.1')
    theta_max = a1*iv.pi/180
    minimum_slope = (26*iv.cos(theta_max)-4*iv.sin(theta_max))/60
    deficit = iv.mpf('5.5')*(1-iv.cos(iv.pi/72))
    raw_delay = deficit/minimum_slope
    p = rounded_endpoint(raw_delay, True, 9)
    assert D(22)+p < D('22.1')
    # Knuckle Y is increasing on this interval. Both endpoint intervals bound
    # its continuous range; the screw end at Z=2 contains Y[-25.5,-22.5].
    def centre_y(a):
        theta = a*iv.pi/180
        return 4*iv.sin(theta)-26*iv.cos(theta)
    ys = [rounded_endpoint(centre_y(a0), False), rounded_endpoint(centre_y(a1), True)]
    band_margin = D('1.5')-max(abs(y+24) for y in ys)
    vertex_y = rounded_endpoint(iv.mpf('5.5')*iv.sin(iv.pi/72), True)
    assert band_margin > vertex_y
    return {
        'source_configuration_domain_mm': [16, 22],
        'local_analytic_extension_mm': [16, D('22.1')],
        'theta_max_upper_deg': rounded_endpoint(a1, True),
        'continuous_abs_dx_du_lower': rounded_endpoint(minimum_slope, False),
        'web_radial_deficit_upper_mm': rounded_endpoint(deficit, True),
        'delay_upper_mm': p,
        'end_face_band_margin_lower_mm': band_margin,
        'supporting_vertex_y_offset_upper_mm': vertex_y,
        'supporting_vertex_band_surplus_lower_mm': band_margin-vertex_y,
        'delay_extension_closed': True,
        'scope': 'Local nominal lever web versus D3 stop only; no added permitted CAD input or assembled output travel.',
        'monotonicity': '0<=phi<=theta<=30deg implies 0<dU/dtheta<=60. The circular left reach derivative uses the worst angle through22.1, including the delayed contact.',
        'local_shape_scope': 'At localZ2 the two negativeY webs retain the exact old shapes. HubR12, restlugR22 and upperarmY>=-7 cannot enter the stopY<=-22.5 band. New hex opening circumradius<7.16 cannot cut that band. Below atan(5/16), the distalR5 web extends toward+X; above it, its clipped left reach is bounded by5.208094, below the main72gon reach5.494765. This is nominal local geometry, not a physical axis-centre or whole-assembly certificate.',
    }


def current_evidence():
    assert sha(ROOT/GATE) == GATE_SHA, 'Changed gate theorem: explicit review required'
    gate = json.loads((ROOT/GATE).read_text())
    evidence = {GATE: GATE_SHA, str(Path(__file__).resolve().relative_to(ROOT)): sha(Path(__file__).resolve())}
    excluded = []
    for name, digest in gate['source_hashes'].items():
        actual = sha(ROOT/name)
        if actual != digest:
            assert name in CURRENT and actual == CURRENT[name], ('Unreviewed dependency change', name)
            excluded.append({'file': name, 'historical_sha256': digest, 'current_sha256': actual})
        evidence[name] = actual
    assert {x['file'] for x in excluded} == set(CURRENT)
    # Only the conditional static feeder theorem transfers: feeder/guide/ball/
    # cam geometry and analytic dependencies match. The changed input geometry
    # is separately re-evaluated above; housing routing and scene display are
    # not premises of the static split-guide ball enclosure. No whole-scene,
    # tolerance, force, mass, or as-built certificate is transferred.
    row = gate['static_sufficient_geometry']['rows'][-1]
    assert row['Bx_required_upper_mm'] == 1 and not row['Bx_currently_certified']
    e = number(row['E_max_upper_mm'])
    f = (D(12)+(D(20)+D('2.5')+e+D(1)-D(21))/D('.625')).quantize(D('.000000000001'), rounding=ROUND_CEILING)
    assert f == number(gate['stop_contract_boundary']['conditional_functional_release_u_upper_mm'])
    return f, evidence, excluded


def serial(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, list):
        return [serial(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bounds', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    f, evidence, excluded = current_evidence()
    delay = local_delay()
    p = delay['delay_upper_mm']
    if args.bounds:
        data = json.loads(args.bounds.read_text(), parse_float=Decimal)
        print(json.dumps(serial(solve(data, p)), ensure_ascii=False, indent=2))
        return
    base = {'functional_output_upper_mm': f, 'earliest_hard_stop_mm': D(20),
            'net_loss_mm': [D(0), D(0)], 'other_input_stop_error_mm': [D(0), D(0)]}
    ideal = solve(base, p)
    width = D(20)-f-p
    controls = {
        'exact_zero_width_rejected': not solve({**base, 'net_loss_mm': [D(0), width]}, p)['strict_interval_nonempty'],
        'constant_two_mm_loss_rejected': not solve({**base, 'net_loss_mm': [D(2), D(2)]}, p)['strict_interval_nonempty'],
        'old_example_threshold_18_5_not_in_new_interval': not (ideal['strict_setting_interval_mm'][0] < D('18.5') < ideal['strict_setting_interval_mm'][1]),
    }
    for label, bad in [('missing', {k:v for k,v in base.items() if k != 'net_loss_mm'}),
                       ('nan', {**base, 'earliest_hard_stop_mm': 'NaN'}),
                       ('reversed', {**base, 'net_loss_mm': [1, 0]})]:
        try:
            solve(bad, p)
        except (KeyError, ValueError):
            controls[label+'_rejected'] = True
        else:
            controls[label+'_rejected'] = False
    assert all(controls.values())
    report = {
        'status': 'CURRENT_CONDITIONAL_STOP_EXAMPLE_CORRECTED_ACTUAL_JOINT_AND_LOAD_BOUNDS_OPEN',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256': evidence,
        'scoped_source_transfer': {'matched_unchanged_gate_dependencies': len(json.loads((ROOT/GATE).read_text())['source_hashes'])-len(excluded),
                                  'changed_dependencies_not_used_as_gate_geometry': excluded,
                                  'scope': 'Only conditional static feeder theorem; all nonlisted proof dependencies unchanged. Current input local stop is freshly calculated. No transfer of old whole-source certification.'},
        'conditional_functional_threshold_mm': f,
        'conditional_gate_premises': ['Common four-finger Bx<=1mm throughout the same u domain; NOT currently proved.',
                                     'Inherited split-shell guide, finite contact/engagement and normal assembly branch.',
                                     'Ball radius20..20.5mm, guide/side-hole envelopes, retained V and cam constraints; no as-built precision or load guarantee.'],
        'local_polygon_delay': delay,
        'nominal_example_NOT_installation': ideal,
        'example_phase_alignment_assumption': 'Example ONLY: common analytical u equals displacement from the actual output release zero. This reference mapping has not been certified for the joint assembly domain.',
        'phase_reference_alignment_certified': False,
        'synthetic_controls': controls,
        'strict_conditions': ['C > F + loss_max - error_min', 'C < H + loss_min - error_max - p',
                              'Also keep actual input and output within the previously considered0..20 domain; this is not a two-axis collision certificate.'],
        'actual_bound_inputs': {k: None for k in base},
        'actual_joint_domain_certified': False,
        'physical_setting_authorized': False,
        'manufacturing_release': False, 'physical_acceptance': False, 'sent_to_printer': False,
    }
    assert all(sha(ROOT/name) == digest for name, digest in evidence.items())
    out = args.output or ROOT/'output/current-stop-contract/runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True, exist_ok=False)
    (out/'report.json').write_text(json.dumps(serial(report), ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(serial({'directory': str(out), 'threshold_mm': f, 'delay': delay, 'example': ideal, 'controls': controls}), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    with localcontext() as context:
        context.prec = 70
        main()
