#!/usr/bin/env python3
"""Bounded parameter feasibility screen; not mechanism/tolerance acceptance.

Two necessary parked-pair conditions for the SAME closed radius at both gates
give W(c) = h(c) + P - 3 H(c) - 4 B. A positive robust spacing window needs
W(c)>0. Decimal outward-rounded bounds cover every c in a finite partition;
midpoint values are diagnostics only, never the nonexistence certificate.

Only this script's JSON is written. CAD and existing reports are unchanged.
"""
from __future__ import annotations

from decimal import Context, Decimal as D, ROUND_CEILING, ROUND_FLOOR, localcontext
import hashlib
import json
import math
from pathlib import Path

from gate_geometry import read_parameters
from guide_openings import center_offset_bound

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/analysis/gate-budget-feasibility.json'
SOURCES = ['cad/parameters.scad', 'analysis/gate_geometry.py',
           'analysis/guide_openings.py', 'analysis/gate_budget_feasibility.py']
UP = Context(prec=70, rounding=ROUND_CEILING)
DOWN = Context(prec=70, rounding=ROUND_FLOOR)
ZERO, TWO, THREE, FOUR = D(0), D(2), D(3), D(4)


def sqrt_upper(value: D) -> D:
    # Decimal.sqrt is correctly rounded to nearest. One next_plus makes its
    # result an upper enclosure, irrespective of Context's rounding setting.
    return UP.next_plus(UP.sqrt(max(ZERO, value)))


def sqrt_lower(value: D) -> D:
    return max(ZERO, DOWN.next_minus(DOWN.sqrt(max(ZERO, value))))


def hashes() -> dict[str, str]:
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in SOURCES}


def necessary_certificate(p: dict[str, float], budget: float,
                          segments: int = 10000) -> dict:
    # Keep finite-decimal input combinations exact before directed 70-digit
    # bounds are applied. This also avoids depending on an importer's context.
    with localcontext() as context:
        context.prec = 140
        return _necessary_certificate(p, budget, segments)


def _necessary_certificate(p: dict[str, float], budget: float,
                           segments: int) -> dict:
    """Certify only whether these two necessary conditions have any room.

    The domain starts at B+e0, slightly BELOW the current side-hole-expanded
    model's B+Emax lower limit, so it includes every admissible closed radius.
    Its upper endpoint is rounded UP from the intact-bore blocking limit.
    """
    r0, r1 = D(str(p['ball_min_d']))/TWO, D(str(p['ball_max_d']))/TWO
    tip = D(str(p['finger_tip_radius']))
    a = D(str(p['guide_id']))/TWO+D(str(p['guide_clearance_budget']))
    b = D(str(budget))
    e0, e1 = a-r0, a-r1
    # Current inputs are finite short decimal literals; these combinations
    # are exact decimal values (also checked by requiring modest digit count).
    assert all(len(x.as_tuple().digits) < 15 and abs(x.as_tuple().exponent) < 15
               for x in [r0, r1, tip, a, b])
    a2, z2 = (r0+tip)**2-e0**2, (r1+tip)**2
    pitch2 = (r0+r1)**2-e0**2-e1**2
    assert 0 <= e1 <= e0 and a2 > 0 and pitch2 > 0
    c0 = b+e0
    c1 = UP.subtract(sqrt_upper(a2), b)
    assert c1 > c0
    # H decreases over this entire domain: c-B-e1 >= e0-e1 >= 0.
    # Its radicand must remain nonnegative for the chosen witness family.
    y_hi = UP.subtract(UP.subtract(c1, b), e1)
    assert DOWN.subtract(z2, UP.multiply(y_hi, y_hi)) > 0
    pitch_hi = sqrt_upper(pitch2)

    def h_hi(c: D) -> D:
        x_lo = DOWN.add(c, b)
        square_lo = DOWN.multiply(x_lo, x_lo)
        return sqrt_upper(UP.subtract(a2, square_lo))

    def hdeep_lo(c: D) -> D:
        y_hi = UP.subtract(UP.subtract(c, b), e1)
        square_hi = UP.multiply(y_hi, y_hi)
        return sqrt_lower(DOWN.subtract(z2, square_hi))

    def interval_upper(left: D, right: D) -> D:
        # h(c)<=h(left), H(c)>=H(right), P<=P_upper on [left,right].
        result = UP.add(h_hi(left), pitch_hi)
        result = UP.subtract(result, DOWN.multiply(THREE, hdeep_lo(right)))
        return UP.subtract(result, FOUR*b)

    span = UP.subtract(c1, c0)
    # Grid points are exact represented decimals, reused as adjoining bounds;
    # their construction need not itself approximate a special ideal grid.
    edges = [c0] + [DOWN.add(c0, DOWN.multiply(span, D(i)/D(segments)))
                    for i in range(1, segments)] + [c1]
    assert all(l < r for l, r in zip(edges, edges[1:]))
    bounds = [interval_upper(l, r) for l, r in zip(edges, edges[1:])]
    index = max(range(segments), key=lambda i: bounds[i])
    upper = bounds[index]
    mid = float((edges[index]+edges[index+1])/TWO)
    h = math.sqrt(max(0, float(a2)-(mid+budget)**2))
    deep = math.sqrt(float(z2)-(mid-budget-float(e1))**2)
    pitch = math.sqrt(float(pitch2))
    lo, hi = 2*deep+2*budget, h+pitch-deep-2*budget
    return {
        'uniform_budget_mm': budget,
        'result': 'NO_COMMON_ROBUST_SPACING_WITHIN_DECLARED_MODEL'
                  if upper < 0 else 'NOT_EXCLUDED_BY_THESE_NECESSARY_CONDITIONS',
        'closed_radius_domain_mm': [str(c0), str(c1)],
        'domain_reason': 'B+e0 through intact-bore blocking limit sqrt((R0+t)^2-e0^2)-B; includes the narrower admissible domain c-B>Emax of gate_geometry.py.',
        'partition_segments': segments,
        'all_intervals_have_negative_upper_bound': all(x < 0 for x in bounds),
        'maximum_certified_window_width_upper_bound_mm': str(upper),
        'max_upper_bound_interval_mm': [str(edges[index]), str(edges[index+1])],
        'rounded_arithmetic': '70-digit Decimal; directed elementary operations; sqrt expanded by next_plus/next_minus; adjacent intervals share exact stored endpoints.',
        'diagnostic_midpoint_not_an_optimum_proof': {
            'closed_radius_mm': mid,
            'necessary_nominal_spacing_interval_mm': [lo, hi],
            'width_mm': hi-lo,
        },
        'witness_family': {
            'guide_radius_mm': str(a), 'ball_radii_mm': [str(r0), str(r1)],
            'intact_bore_center_offsets_mm': [str(e0), str(e1)],
            'lower_spacing_state': {
                'ball_diameters_mm': [float(TWO*r1), float(TWO*r1)],
                'first_lateral_xy_mm': [float(e1), 0],
                'second_lateral_xy_mm': [float(e1), 0],
                'front_and_rear_finger_radii': 'c-B',
                'actual_spacing': 'L-2B',
                'necessary_condition': 'L >= 2H(c)+2B',
            },
            'upper_spacing_state': {
                'ball_diameters_mm': [float(TWO*r0), float(TWO*r1)],
                'first_lateral_xy_mm': [0, float(e0)],
                'second_lateral_xy_mm': [float(e1), 0],
                'front_finger_radii': 'c+B', 'rear_finger_radii': 'c-B',
                'actual_spacing': 'L+2B',
                'necessary_condition': 'L <= h(c)+P-H(c)-2B',
            },
        },
    }


def sufficient_control(p: dict[str, float], budget: float,
                       closed: float, opened: float, spacing: float) -> dict:
    """Existing conservative continuous envelope, no sampled ball search."""
    r0, r1 = p['ball_min_d']/2, p['ball_max_d']/2
    tip = p['finger_tip_radius']
    a = p['guide_id']/2+p['guide_clearance_budget']
    hole = tip+p['radial_print_clearance']
    eccentricity = lambda radius: center_offset_bound(a, radius, hole)
    e = eccentricity(r0)
    hmin = math.sqrt(max(0, (r0+tip)**2-(closed+budget)**2-e**2))
    hmax = max(math.sqrt(max(0, (r+tip)**2-(closed-budget-eccentricity(r))**2))
               for r in [r0, r1])
    pitch = math.sqrt((2*r0)**2-(2*e)**2)
    lo, hi = 2*hmax+2*budget, hmin+pitch-hmax-2*budget
    return {
        'uniform_budget_mm': budget, 'closed_radius_mm': closed,
        'open_radius_mm': opened, 'nominal_spacing_mm': spacing,
        'sufficient_nominal_spacing_interval_mm': [lo, hi],
        'minimum_spacing_margin_mm': min(spacing-lo, hi-spacing),
        'closed_blocking_margin_mm': r0+tip-math.hypot(closed+budget, e),
        'open_clearance_mm': opened-budget-r0-tip-e,
        'scope': 'Formula-only control of the existing ideal static envelope, not assembled CAD, complete error proof, dynamics or manufacturing acceptance.',
    }


def main() -> int:
    before = hashes()
    p, _ = read_parameters(ROOT/'cad/parameters.scad')
    cases = [necessary_certificate(p, b) for b in [1.0, 1.1, 1.5, 2.0]]
    controls = [sufficient_control(p, 1.0, p['finger_closed_center_r'],
                                  p['finger_open_center_r'], p['gate_spacing']),
                sufficient_control(p, 1.1, 20.72, 26, 29.34)]
    stable = before == hashes()
    report = {
        'status': 'BOUNDED_STATIC_PARAMETER_FEASIBILITY_ONLY' if stable else 'STALE_INPUTS',
        'source_sha256': before, 'sources_stable': stable,
        'parameters_read': p, 'cases': cases, 'sufficient_controls': controls,
        'formula': {
            'symbols': 'R0/R1=min/max ball radii; t=tip radius; A=largest allowed guide radius; e0=A-R0, e1=A-R1; c=common nominal closed radius; L=nominal gate spacing; B=independent +/- radial finger budget AND +/- axial budget per gate.',
            'H': 'sqrt((R1+t)^2-(c-B-e1)^2)',
            'h': 'sqrt((R0+t)^2-(c+B)^2-e0^2)',
            'P': 'sqrt((R0+R1)^2-e0^2-e1^2)',
            'necessary_window': '[2H+2B, h+P-H-2B]',
            'width': 'W(c)=h+P-3H-4B',
            'continuous_interval_bound': 'For c in [l,r], h is decreasing and H is decreasing on the declared domain, hence W(c)<=h(l)+P-3H(r)-4B. Every adjacent interval is bounded, not only its midpoint.',
        },
        'limits': [
            'Applies to the same nominal closed radius at both gates, opposed equal-radius tips coplanar within each gate, and the current monotone radial capsule model; it is not a theorem about every two-gate mechanism.',
            'The two necessary witness families use offsets inside the INTACT round-bore disk, not arbitrary points of the larger side-hole enclosing disk.',
            'Requires arbitrary declared parked touching pairs, including mixed sizes and lateral offsets, to admit a rear finger between the first and second balls without moving or deforming them. It does not prove loaded dynamic reachability of every such state.',
            'Negative maximum interval upper bound means no single L works for both necessary state families over this static uncertainty envelope. It does not predict a real double shot or condemn a narrower measured envelope.',
            'The open radius cannot repair a missing CLOSED insertion window; it only changes open passage and required stroke.',
            'This script does not establish guide-end containment or dynamic transitions for altered designs. Violating those requirements is not accepted as an escape from the declared static model.',
            'A found X-error lower bound such as 0.930586mm is neither an axial-error bound nor a full-vector error certificate. A split radial/axial budget needs independent justification and a revised model.',
            'No CAD/parameters/existing reports are changed. No whole-mechanism error, force, friction, deformation, seal, print or physical-function acceptance is issued.',
        ],
        'manufacturing_release': False, 'physical_acceptance': 'OPEN',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(report['status'])
    for row in cases:
        print('B=', row['uniform_budget_mm'], row['result'],
              'window_width_upper_mm=', row['maximum_certified_window_width_upper_bound_mm'])
    for row in controls:
        print('control B=', row['uniform_budget_mm'], 'spacing_margin=', row['minimum_spacing_margin_mm'])
    return 0 if stable else 1


if __name__ == '__main__':
    raise SystemExit(main())
